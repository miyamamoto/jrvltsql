# NVLinkBridge

C# console app that wraps the NV-Link (地方競馬DATA) COM API.
Communicates with jrvltsql's Python code via stdin/stdout JSON protocol.

## Why?

NV-Link is a Delphi-built COM component. Python's `win32com` has VARIANT BYREF
marshaling issues that cause `E_UNEXPECTED` errors during NVGets/NVRead.
C# has native COM interop that works correctly (same approach as kmy-keiba).

## Build

Requires .NET 8 SDK (x86):

```cmd
dotnet build -c Release
```

Output: `bin/x86/Release/net8.0-windows/NVLinkBridge.exe`

## Usage

The bridge reads JSON commands from stdin and writes JSON responses to stdout.

### Commands

| Command | Fields | Description |
|---------|--------|-------------|
| `init` | `key` (optional) | Initialize NV-Link COM |
| `open` | `dataspec`, `fromtime`, `option` | Open data stream |
| `gets` | `size` (optional, default 110000) | Read record (byte array) |
| `read` | `size` (optional) | Read record (string) |
| `status` | — | Get download progress |
| `skip` | — | Skip current record |
| `close` | — | Close data stream |
| `quit` | — | Exit process |

### Example

```json
{"cmd":"init","key":"UNKNOWN"}
→ {"status":"ok","hwnd":65548}

{"cmd":"open","dataspec":"RACE","fromtime":"20260201000000","option":1}
→ {"status":"ok","code":0,"readcount":11,"downloadcount":0,"lastfiletimestamp":""}

{"cmd":"gets","size":110000}
→ {"status":"ok","code":28955,"data":"<base64>","filename":"H1NV...nvd","size":28955}
```

## Note

NV-Link COM requires GUI context (shell notification icon). When running from SSH,
use `schtasks` to execute in the interactive console session.
