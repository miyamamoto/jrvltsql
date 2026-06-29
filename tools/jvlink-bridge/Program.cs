// JVLinkBridge - JSON stdin/stdout bridge for JV-Link COM API.
// Hosts the JVDTLab.JVLink ActiveX control via AxHost in a hidden WinForms form.
// Works on Windows (native) and Linux (Wine).

using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Windows.Forms;

namespace JVLinkBridge;

class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        try { Console.InputEncoding = Encoding.UTF8; } catch { }
        try { Console.OutputEncoding = Encoding.UTF8; } catch { }

        var bridge = new BridgeForm();
        bridge.Show();
        bridge.Hide();
        Application.Run(bridge);
    }
}

// AxHost wrapper for JVDTLab.JVLink ActiveX control
// CLSID: {2AB1774D-0C41-11D7-916F-0003479BEB3F}
class JVLinkAxHost : AxHost
{
    private const string JVLINK_CLSID = "{2AB1774D-0C41-11D7-916F-0003479BEB3F}";

    public JVLinkAxHost() : base(JVLINK_CLSID) { }

    // Expose the underlying COM object for late-bound method calls
    public object? ActiveXInstance
    {
        get
        {
            try
            {
                // AxHost.GetOcx() is the proper way to get the OCX instance
                return base.GetOcx();
            }
            catch
            {
                return null;
            }
        }
    }
}

class BridgeForm : Form
{
    private JVLinkAxHost? _axHost;
    private dynamic? _jvlink;
    private bool _isOpen;
    private Thread? _readerThread;

    public BridgeForm()
    {
        this.Text = "JVLinkBridge";
        this.ShowInTaskbar = false;
        this.WindowState = FormWindowState.Minimized;
        this.FormBorderStyle = FormBorderStyle.None;
        this.Size = new System.Drawing.Size(1, 1);
    }

    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        this.Visible = false;

        // Host the JVLink ActiveX control - must happen after form handle is created
        try
        {
            _axHost = new JVLinkAxHost();
            _axHost.Visible = false;
            _axHost.Size = new System.Drawing.Size(1, 1);
            this.Controls.Add(_axHost);
            _jvlink = _axHost.ActiveXInstance;
        }
        catch (Exception ex)
        {
            // AxHost may fail; we'll fall back to CreateObject in HandleInit
            _jvlink = null;
        }

        WriteResponse(new { status = "ready", version = "cs-1.2", pid = Environment.ProcessId, axhost = (_jvlink != null) });

        _readerThread = new Thread(ReaderLoop);
        _readerThread.IsBackground = true;
        _readerThread.Start();
    }

    private void ReaderLoop()
    {
        string? line;
        while ((line = Console.ReadLine()) != null)
        {
            line = line.Trim();
            if (string.IsNullOrEmpty(line)) continue;

            this.Invoke(new Action(() => ProcessCommand(line)));
        }
        this.Invoke(new Action(() => Application.Exit()));
    }

    private void ProcessCommand(string line)
    {
        try
        {
            var node = JsonNode.Parse(line);
            if (node == null) return;
            var cmd = node["cmd"]?.GetValue<string>() ?? "";

            switch (cmd)
            {
                case "init": HandleInit(node); break;
                case "setservicekey": HandleSetServiceKey(node); break;
                case "setsavepath": HandleSetSavePath(node); break;
                case "open": HandleOpen(node); break;
                case "rtopen": HandleRTOpen(node); break;
                case "read": HandleRead(node); break;
                case "skip": HandleSkip(node); break;
                case "close": HandleClose(); break;
                case "status": HandleStatus(); break;
                case "filedelete": HandleFileDelete(node); break;
                case "quit":
                    HandleClose();
                    WriteResponse(new { status = "ok", message = "bye" });
                    Application.Exit();
                    break;
                default:
                    WriteResponse(new { status = "error", error = $"Unknown command: {cmd}" });
                    break;
            }
        }
        catch (Exception ex)
        {
            WriteResponse(new { status = "error", error = ex.Message, type = ex.GetType().Name });
        }
    }

    private void HandleInit(JsonNode node)
    {
        try
        {
            if (_jvlink == null)
            {
                // Fallback: try creating via ProgID
                var comType = Type.GetTypeFromProgID("JVDTLab.JVLink");
                if (comType != null)
                    _jvlink = Activator.CreateInstance(comType);
            }

            if (_jvlink == null)
            {
                WriteResponse(new { status = "error", error = "JVLink COM object not available" });
                return;
            }

            var key = node["key"]?.GetValue<string>() ?? "UNKNOWN";
            int result = _jvlink.JVInit(key);
            WriteResponse(new { status = result == 0 ? "ok" : "error", code = result });
        }
        catch (Exception ex)
        {
            WriteResponse(new { status = "error", error = $"Init failed: {ex.Message}" });
        }
    }

    private void HandleSetServiceKey(JsonNode node)
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }
        var servicekey = node["servicekey"]?.GetValue<string>() ?? "";
        int code = _jvlink.JVSetServiceKey(servicekey);
        WriteResponse(new { status = code == 0 ? "ok" : "error", code });
    }

    private void HandleSetSavePath(JsonNode node)
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }
        var path = node["path"]?.GetValue<string>() ?? "C:\\JV-Data\\";
        int code = _jvlink.JVSetSavePath(path);
        WriteResponse(new { status = code == 0 ? "ok" : "error", code });
    }

    private void HandleOpen(JsonNode node)
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }

        var dataspec = node["dataspec"]?.GetValue<string>() ?? "";
        var fromtime = node["fromtime"]?.GetValue<string>() ?? "";
        var option = node["option"]?.GetValue<int>() ?? 1;

        int readcount = 0;
        int downloadcount = 0;
        string lastfiletimestamp = "";

        int code = _jvlink.JVOpen(dataspec, fromtime, option,
            ref readcount, ref downloadcount, ref lastfiletimestamp);

        if (code < -2)
            WriteResponse(new { status = "error", code, error = "JVOpen failed", readcount, downloadcount, lastfiletimestamp });
        else
        {
            _isOpen = true;
            WriteResponse(new { status = "ok", code, readcount, downloadcount, lastfiletimestamp });
        }
    }

    private void HandleRTOpen(JsonNode node)
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }

        var dataspec = node["dataspec"]?.GetValue<string>() ?? "";
        var key = node["key"]?.GetValue<string>() ?? "";

        int code = _jvlink.JVRTOpen(dataspec, key);

        if (code < 0)
            WriteResponse(new { status = "error", code, error = "JVRTOpen failed" });
        else
        {
            _isOpen = true;
            WriteResponse(new { status = "ok", code, readcount = (code >= 0 ? code : 0) });
        }
    }

    private void HandleRead(JsonNode node)
    {
        if (_jvlink == null || !_isOpen) { WriteResponse(new { status = "error", error = "Not open" }); return; }

        var size = node["size"]?.GetValue<int>() ?? 110000;
        string buff = "";
        string filename = "";

        int code = _jvlink.JVRead(ref buff, size, ref filename);

        if (code > 0 && !string.IsNullOrEmpty(buff))
        {
            var encoding = Encoding.GetEncoding(932);
            byte[] bytes = encoding.GetBytes(buff.Substring(0, Math.Min(buff.Length, code)));
            var b64 = Convert.ToBase64String(bytes);
            WriteResponse(new { status = "ok", code, data = b64, filename, size = bytes.Length });
        }
        else
        {
            WriteResponse(new { status = "ok", code, data = (string?)null, filename, size = 0 });
        }
    }

    private void HandleSkip(JsonNode node)
    {
        if (_jvlink == null || !_isOpen) { WriteResponse(new { status = "error", error = "Not open" }); return; }
        int code = _jvlink.JVSkip();
        WriteResponse(new { status = "ok", code });
    }

    private void HandleClose()
    {
        if (_jvlink != null && _isOpen)
        {
            try { _jvlink.JVClose(); } catch { }
            _isOpen = false;
        }
        WriteResponse(new { status = "ok" });
    }

    private void HandleStatus()
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }
        int code = _jvlink.JVStatus();
        WriteResponse(new { status = "ok", code });
    }

    private void HandleFileDelete(JsonNode node)
    {
        if (_jvlink == null) { WriteResponse(new { status = "error", error = "Not initialized" }); return; }
        var filename = node["filename"]?.GetValue<string>() ?? "";
        int code = _jvlink.JVFileDelete(filename);
        WriteResponse(new { status = "ok", code });
    }

    private static void WriteResponse(object obj)
    {
        var json = JsonSerializer.Serialize(obj, new JsonSerializerOptions { WriteIndented = false });
        Console.WriteLine(json);
        Console.Out.Flush();
    }
}
