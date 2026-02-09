using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Runtime.InteropServices;

// JV/NV-Link COM Bridge for Python
// Wraps both JVDTLab.JVLink (JRA/中央競馬) and NVDTLabLib.NVLink (NAR/地方競馬)
// COM components via C# native interop.
// Communicates via stdin (JSON commands) / stdout (JSON responses).
//
// This eliminates the need for Python win32com, solving:
// - VARIANT BYREF marshaling issues (E_UNEXPECTED errors)
// - 32-bit Python requirement (C# handles COM bitness)
// - Delphi COM memory management issues

class Program
{
    static dynamic? link;          // JVLink or NVLink COM object
    static bool initialized = false;
    static IntPtr parentHwnd = IntPtr.Zero;
    static string linkType = "";   // "jra" or "nar"

    static void Main(string[] args)
    {
        // Register Shift-JIS encoding
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

        Console.OutputEncoding = Encoding.UTF8;
        Console.InputEncoding = Encoding.UTF8;

        // Signal ready
        WriteResponse(new { status = "ready", version = "2.0.0" });

        string? line;
        while ((line = Console.ReadLine()) != null)
        {
            line = line.Trim();
            if (string.IsNullOrEmpty(line)) continue;

            try
            {
                var doc = JsonDocument.Parse(line);
                var root = doc.RootElement;
                var cmd = root.GetProperty("cmd").GetString() ?? "";

                object result = cmd switch
                {
                    "init" => CmdInit(root),
                    "open" => CmdOpen(root),
                    "read" => CmdRead(root),
                    "gets" => CmdGets(root),
                    "status" => CmdStatus(),
                    "skip" => CmdSkip(),
                    "close" => CmdClose(),
                    "filedelete" => CmdFileDelete(root),
                    "rtopen" => CmdRTOpen(root),
                    "quit" => CmdQuit(),
                    _ => new { status = "error", error = $"Unknown command: {cmd}" }
                };

                WriteResponse(result);

                if (cmd == "quit") return;
            }
            catch (Exception ex)
            {
                WriteResponse(new { status = "error", error = ex.Message, type = ex.GetType().Name });
            }
        }
    }

    static object CmdInit(JsonElement root)
    {
        if (initialized)
        {
            try { link?.JVClose(); } catch { }
            try { link?.NVClose(); } catch { }
            link = null;
            initialized = false;
        }

        var key = root.TryGetProperty("key", out var k) ? k.GetString() ?? "UNKNOWN" : "UNKNOWN";
        linkType = root.TryGetProperty("type", out var t) ? t.GetString() ?? "nar" : "nar";

        Type? comType = null;

        if (linkType == "jra")
        {
            // JRA: JVDTLab.JVLink
            comType = Type.GetTypeFromProgID("JVDTLab.JVLink");
            if (comType == null)
            {
                return new { status = "error", error = "JV-Link COM not found. Is JRA-VAN Data Lab installed?" };
            }
        }
        else
        {
            // NAR: NVDTLabLib.NVLink
            comType = Type.GetTypeFromProgID("NVDTLabLib.NVLink");
            if (comType == null)
                comType = Type.GetTypeFromProgID("NVDTLab.NVLink");
            if (comType == null)
            {
                return new { status = "error", error = "NV-Link COM not found. Is UmaConn installed?" };
            }
        }

        link = Activator.CreateInstance(comType);
        if (link == null)
        {
            return new { status = "error", error = "Failed to create COM instance" };
        }

        // Set ParentHWnd (critical for NV-Link, optional but safe for JV-Link)
        parentHwnd = GetDesktopWindow();
        try { link.ParentHWnd = (int)parentHwnd; } catch { }

        // Initialize
        int result;
        if (linkType == "jra")
            result = link.JVInit(key);
        else
            result = link.NVInit(key);

        if (result != 0)
        {
            return new { status = "error", error = $"Init failed", code = result, linkType };
        }

        initialized = true;
        return new { status = "ok", hwnd = (long)parentHwnd, linkType };
    }

    static object CmdOpen(JsonElement root)
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        var dataspec = root.GetProperty("dataspec").GetString() ?? "";
        var fromtime = root.GetProperty("fromtime").GetString() ?? "";
        var option = root.TryGetProperty("option", out var o) ? o.GetInt32() : 1;
        var timeoutSec = root.TryGetProperty("timeout", out var t) ? t.GetInt32() : 300;

        int readcount = 0;
        int downloadcount = 0;
        string lastfiletimestamp = "";
        int result = -1;

        // NVOpen/JVOpen can block for minutes during download.
        // Run in a background thread with timeout to prevent hanging.
        var openTask = Task.Run(() =>
        {
            if (linkType == "jra")
            {
                result = link.JVOpen(dataspec, fromtime, option, ref readcount, ref downloadcount, out lastfiletimestamp);
            }
            else
            {
                result = link.NVOpen(dataspec, int.Parse(fromtime), option, ref readcount, ref downloadcount, out lastfiletimestamp);
            }
        });

        if (!openTask.Wait(TimeSpan.FromSeconds(timeoutSec)))
        {
            // Timeout — try to cancel and return error
            try { if (linkType == "jra") link.JVCancel(); else link.NVCancel(); } catch { }
            return new { status = "error", code = -502, error = $"Open timeout ({timeoutSec}s)", readcount = 0, downloadcount = 0, lastfiletimestamp = "" };
        }

        // Check for task exception
        if (openTask.IsFaulted)
        {
            var ex = openTask.Exception?.InnerException ?? openTask.Exception;
            return new { status = "error", code = -1, error = ex?.Message ?? "Unknown error", readcount = 0, downloadcount = 0, lastfiletimestamp = "" };
        }

        return new
        {
            status = result >= -1 ? "ok" : "error",
            code = result,
            readcount,
            downloadcount,
            lastfiletimestamp = lastfiletimestamp ?? ""
        };
    }

    static object CmdRTOpen(JsonElement root)
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        var dataspec = root.GetProperty("dataspec").GetString() ?? "";
        var key = root.TryGetProperty("key", out var k) ? k.GetString() ?? "" : "";

        int readcount = 0;
        int result;

        if (linkType == "jra")
            result = link.JVRTOpen(dataspec, key);
        else
            result = link.NVRTOpen(dataspec, key);

        // Handle tuple return from COM
        // pywin32 returns tuple, but C# dynamic gets individual return + out params
        // For now, return the result code
        return new
        {
            status = result >= -1 ? "ok" : "error",
            code = result,
            readcount
        };
    }

    static object CmdGets(JsonElement root)
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        var size = root.TryGetProperty("size", out var s) ? s.GetInt32() : 110000;

        if (linkType == "jra")
        {
            // JV-Link doesn't have JVGets; use JVRead and convert
            return CmdRead(root);
        }

        // NAR: NVGets returns byte array
        var buff = new byte[size];
        string filename = "";

        object obj = buff;
        int result = link.NVGets(ref obj, size, out filename);
        buff = (byte[])obj;

        if (result > 0)
        {
            var data = Convert.ToBase64String(buff, 0, result);
            Array.Resize(ref buff, 0);
            return new { status = "ok", code = result, data, filename = filename ?? "", size = result };
        }
        else
        {
            Array.Resize(ref buff, 0);
            return new
            {
                status = result >= -1 ? "ok" : "error",
                code = result,
                data = (string?)null,
                filename = filename ?? "",
                size = 0
            };
        }
    }

    static object CmdRead(JsonElement root)
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        var size = root.TryGetProperty("size", out var s) ? s.GetInt32() : 110000;

        string buff = "";
        string filename = "";
        int result;

        if (linkType == "jra")
        {
            // JVRead(out buff, out size, out filename)
            result = link.JVRead(out buff, out size, out filename);
        }
        else
        {
            // NVRead(out buff, out size, out filename)
            result = link.NVRead(out buff, out size, out filename);
        }

        if (result > 0)
        {
            // Data returned as string. JV/NV-Link stuffs Shift-JIS bytes into BSTR.
            // Encode to Shift-JIS bytes, then base64.
            byte[] bytes;
            try
            {
                // Try Shift-JIS encoding first (most reliable for JV-Link data)
                bytes = Encoding.GetEncoding(932).GetBytes(buff ?? "");
            }
            catch
            {
                // Fallback: extract raw bytes via Latin-1 (1:1 byte mapping)
                try
                {
                    bytes = Encoding.GetEncoding(28591).GetBytes(buff ?? "");
                }
                catch
                {
                    bytes = Encoding.Unicode.GetBytes(buff ?? "");
                }
            }
            var data = Convert.ToBase64String(bytes, 0, Math.Min(bytes.Length, result));

            return new { status = "ok", code = result, data, filename = filename ?? "", size = result };
        }
        else
        {
            return new
            {
                status = result >= -1 ? "ok" : "error",
                code = result,
                data = (string?)null,
                filename = filename ?? "",
                size = 0
            };
        }
    }

    static object CmdStatus()
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        int result;
        if (linkType == "jra")
            result = link.JVStatus();
        else
            result = link.NVStatus();

        return new { status = "ok", code = result };
    }

    static object CmdSkip()
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        if (linkType == "jra")
            link.JVSkip();
        else
            link.NVSkip();

        return new { status = "ok" };
    }

    static object CmdFileDelete(JsonElement root)
    {
        if (!initialized || link == null)
            return new { status = "error", error = "Not initialized" };

        var filename = root.GetProperty("filename").GetString() ?? "";

        int result;
        if (linkType == "jra")
            result = link.JVFiledelete(filename);
        else
            result = link.NVFiledelete(filename);

        return new { status = "ok", code = result };
    }

    static object CmdClose()
    {
        if (!initialized || link == null)
            return new { status = "ok" };

        try
        {
            if (linkType == "jra")
                link.JVClose();
            else
                link.NVClose();
        }
        catch { }

        return new { status = "ok" };
    }

    static object CmdQuit()
    {
        if (initialized && link != null)
        {
            try
            {
                if (linkType == "jra")
                    link.JVClose();
                else
                    link.NVClose();
            }
            catch { }
        }
        return new { status = "ok", message = "bye" };
    }

    static void WriteResponse(object response)
    {
        var json = JsonSerializer.Serialize(response);
        Console.WriteLine(json);
        Console.Out.Flush();
    }

    [DllImport("user32.dll")]
    static extern IntPtr GetDesktopWindow();
}
