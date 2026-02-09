# JV/NV-LinkBridge

C# console app that wraps both JV-Link (JRA/中央競馬) and NV-Link (NAR/地方競馬)
COM APIs. Communicates with jrvltsql's Python code via stdin/stdout JSON protocol.

## Why?

- **64-bit Python対応**: C# が COM を全部やるので、Python のビット数制約なし
- **COM安定性**: Python win32com の VARIANT BYREF マーシャリング問題を回避
- **統合ブリッジ**: JRA/NAR 両方を1つの実行ファイルで対応

## Build

Requires .NET 8 SDK (x86):

```cmd
dotnet build -c Release
```

Output: `bin/x86/Release/net8.0-windows/NVLinkBridge.exe`

## Usage

### Commands

| Command | Fields | Description |
|---------|--------|-------------|
| `init` | `type` ("jra"/"nar"), `key` | Initialize COM |
| `open` | `dataspec`, `fromtime`, `option` | Open data stream |
| `gets` | `size` (NAR only) | Read record (byte array) |
| `read` | `size` | Read record (string) |
| `status` | — | Get download progress |
| `skip` | — | Skip current record |
| `filedelete` | `filename` | Delete cached file |
| `rtopen` | `dataspec`, `key` | Open realtime stream |
| `close` | — | Close data stream |
| `quit` | — | Exit process |

### Example (JRA)

```json
{"cmd":"init","type":"jra","key":"UNKNOWN"}
→ {"status":"ok","hwnd":65548,"linkType":"jra"}

{"cmd":"open","dataspec":"RACE","fromtime":"20260201000000","option":1}
→ {"status":"ok","code":0,"readcount":500,"downloadcount":0,...}

{"cmd":"read","size":50000}
→ {"status":"ok","code":1340,"data":"<base64>","filename":"...","size":1340}
```

### Example (NAR)

```json
{"cmd":"init","type":"nar","key":"UNKNOWN"}
→ {"status":"ok","hwnd":65548,"linkType":"nar"}

{"cmd":"gets","size":110000}
→ {"status":"ok","code":28955,"data":"<base64>","filename":"H1NV...nvd","size":28955}
```

## Note

Both JV-Link and NV-Link COM require GUI context. When running from SSH,
use `schtasks` to execute in the interactive console session.
