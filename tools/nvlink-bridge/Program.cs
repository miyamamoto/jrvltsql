using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Runtime.InteropServices;

// NV-Link COM Bridge for Python
// Wraps NVDTLabLib.NVLink COM component via C# native interop.
// Communicates via stdin (JSON commands) / stdout (JSON responses).

class Program
{
    static dynamic? nvlink;
    static bool initialized = false;
    static IntPtr parentHwnd = IntPtr.Zero;

    static void Main(string[] args)
    {
        // Register Shift-JIS encoding
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

        Console.OutputEncoding = Encoding.UTF8;
        Console.InputEncoding = Encoding.UTF8;

        // Signal ready
        WriteResponse(new { status = "ready", version = "1.0.0" });

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
            // Re-init: close first
            try { nvlink?.NVClose(); } catch { }
            nvlink = null;
            initialized = false;
        }

        var key = root.TryGetProperty("key", out var k) ? k.GetString() ?? "UNKNOWN" : "UNKNOWN";

        // Create COM object
        var type = Type.GetTypeFromProgID("NVDTLabLib.NVLink");
        if (type == null)
        {
            // Fallback
            type = Type.GetTypeFromProgID("NVDTLab.NVLink");
        }
        if (type == null)
        {
            return new { status = "error", error = "NV-Link COM component not found. Is NV-Link installed?" };
        }

        nvlink = Activator.CreateInstance(type);
        if (nvlink == null)
        {
            return new { status = "error", error = "Failed to create NV-Link COM instance" };
        }

        // Set ParentHWnd (critical for NV-Link!)
        parentHwnd = GetDesktopWindow();
        nvlink.ParentHWnd = (int)parentHwnd;

        // Initialize
        int result = nvlink.NVInit(key);
        if (result != 0)
        {
            return new { status = "error", error = $"NVInit failed", code = result };
        }

        initialized = true;
        return new { status = "ok", hwnd = (long)parentHwnd };
    }

    static object CmdOpen(JsonElement root)
    {
        if (!initialized || nvlink == null)
            return new { status = "error", error = "Not initialized" };

        var dataspec = root.GetProperty("dataspec").GetString() ?? "";
        var fromtime = root.GetProperty("fromtime").GetString() ?? "";
        var option = root.TryGetProperty("option", out var o) ? o.GetInt32() : 1;

        int readcount = 0;
        int downloadcount = 0;
        string lastfiletimestamp = "";

        int result = nvlink.NVOpen(dataspec, fromtime, option, ref readcount, ref downloadcount, out lastfiletimestamp);

        return new
        {
            status = result >= 0 ? "ok" : "error",
            code = result,
            readcount,
            downloadcount,
            lastfiletimestamp = lastfiletimestamp ?? ""
        };
    }

    static object CmdGets(JsonElement root)
    {
        if (!initialized || nvlink == null)
            return new { status = "error", error = "Not initialized" };

        var size = root.TryGetProperty("size", out var s) ? s.GetInt32() : 110000;

        var buff = new byte[size];
        string filename = "";

        object obj = buff;
        int result = nvlink.NVGets(ref obj, size, out filename);
        buff = (byte[])obj;

        if (result > 0)
        {
            // Data available - encode as base64
            // NVGets returns Shift-JIS data in byte array
            var data = Convert.ToBase64String(buff, 0, result);

            // Free COM memory (kmy-keiba pattern)
            Array.Resize(ref buff, 0);

            return new
            {
                status = "ok",
                code = result,
                data,
                filename = filename ?? "",
                size = result
            };
        }
        else if (result == 0)
        {
            Array.Resize(ref buff, 0);
            return new { status = "ok", code = 0, data = (string?)null, filename = filename ?? "", size = 0 };
        }
        else if (result == -1)
        {
            Array.Resize(ref buff, 0);
            return new { status = "ok", code = -1, data = (string?)null, filename = filename ?? "", size = 0 };
        }
        else
        {
            Array.Resize(ref buff, 0);
            return new { status = "error", code = result, filename = filename ?? "" };
        }
    }

    static object CmdRead(JsonElement root)
    {
        if (!initialized || nvlink == null)
            return new { status = "error", error = "Not initialized" };

        var size = root.TryGetProperty("size", out var s) ? s.GetInt32() : 110000;

        string buff = "";
        string filename = "";

        int result = nvlink.NVRead(out buff, out size, out filename);

        if (result > 0)
        {
            // NVRead returns Unicode string, but NV-Link stuffs Shift-JIS bytes into it
            // Convert to byte array and base64 encode
            byte[] bytes;
            try
            {
                bytes = Encoding.GetEncoding(932).GetBytes(buff ?? "");
            }
            catch
            {
                bytes = Encoding.Unicode.GetBytes(buff ?? "");
            }
            var data = Convert.ToBase64String(bytes, 0, Math.Min(bytes.Length, result));

            return new
            {
                status = "ok",
                code = result,
                data,
                filename = filename ?? "",
                size = result
            };
        }
        else if (result == 0)
        {
            return new { status = "ok", code = 0, data = (string?)null, filename = filename ?? "", size = 0 };
        }
        else if (result == -1)
        {
            return new { status = "ok", code = -1, data = (string?)null, filename = filename ?? "", size = 0 };
        }
        else
        {
            return new { status = "error", code = result, filename = filename ?? "" };
        }
    }

    static object CmdStatus()
    {
        if (!initialized || nvlink == null)
            return new { status = "error", error = "Not initialized" };

        int result = nvlink.NVStatus();
        return new { status = "ok", code = result };
    }

    static object CmdSkip()
    {
        if (!initialized || nvlink == null)
            return new { status = "error", error = "Not initialized" };

        nvlink.NVSkip();
        return new { status = "ok" };
    }

    static object CmdClose()
    {
        if (!initialized || nvlink == null)
            return new { status = "ok" };

        try { nvlink.NVClose(); } catch { }
        return new { status = "ok" };
    }

    static object CmdQuit()
    {
        if (initialized && nvlink != null)
        {
            try { nvlink.NVClose(); } catch { }
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
