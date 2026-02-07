# 技術詳細

## DLL Surrogate (64-bit Python対応)

JV-Link / NV-Link のCOM DLLは32-bitですが、DLL Surrogateを設定することで64-bit Pythonから利用可能です。

### セットアップ

管理者権限のPowerShell/コマンドプロンプトで実行：

```bash
python docs/gists/check_dll_surrogate.py --fix
```

### CLSID

| API | CLSID | DLL |
|-----|-------|-----|
| JV-Link | `{2AB1774D-0C41-11D7-916F-0003479BEB3F}` | `C:\Windows\SysWow64\JVDTLAB\JVDTLab.dll` |
| NV-Link | `{F726BBA6-5784-4529-8C67-26E152D49D73}` | `C:\Windows\SysWow64\NVDTLab.dll` |

### 注意事項

- DLL Surrogate経由では `option=2`（未読データ取得）を推奨
- `option=3/4` はアウトプロセス通信でハングする場合があります
- 詳細は [docs/qiita_64bit_python_com.md](qiita_64bit_python_com.md) を参照

## NV-Link (地方競馬DATA)

### 初期化キー

NV-Linkの初期化キーは `"UNKNOWN"` を使用してください。他のキーでは `-301` 認証エラーが発生します。

`config/config.yaml` に設定：

```yaml
nar:
  initialization_key: "UNKNOWN"
```

### ProgID

- 正しい ProgID: `NVDTLabLib.NVLink`（`NVDTLab.NVLink` ではない）

### NVRead 戻り値

| 値 | 意味 |
|----|------|
| > 0 | データあり（データ長） |
| 0 | 読み取り完了 |
| -1 | ファイル切り替え（読み続ける） |
| -3 | ファイル未検出（リカバリ可能） |
| -116 | 未提供データスペック |
| -301 | 認証エラー（初期化キーが不正） |

### NVDファイル構造

- NVDファイルはZIPアーカイブ
- ファイル内: H1/BN/CH/KS/NC のみ
- HA/HR/SE等はライブCOMストリームから取得
- パス: `C:\UmaConn\chiho.k-ba\data\{data,cache}\YYYY\`

## トラブルシューティング

### -203 エラー（初回セットアップ未完了）

NVDTLab設定ツールを起動し、初回セットアップ（全データダウンロード）を実行してください。

### -3 エラー（ファイル未検出）

`option=2` で既読データを再取得しようとした場合に発生します。`fromtime` を新しいタイムスタンプに更新してください。

### -116 エラー（未提供データスペック）

NV-Linkで未対応のデータスペック（例: DIFF）を指定した場合に発生します。

### COM E_UNEXPECTED

読み取り完了のサイン。正常終了（return code 0）として処理されます。

### シェル通知アイコンエラー

NV-Linkはデスクトップセッションが必要です。SSHのみでは動作しません。Task Schedulerで `/it` フラグを使用してインタラクティブセッションで実行してください。

## パーサー一覧

### JRA (38種)

AV, BN, BR, BT, CC, CH, CK, CS, DM, H1, H6, HC, HN, HR, HS, HY, JC, JG, KS, O1, O2, O3, O4, O5, O6, RA, RC, SE, SK, TC, TK, TM, UM, WC, WE, WF, WH, YS

### NAR (3種)

HA (払戻情報), NU (成績情報), BN (馬主マスタ)

## データベース

### SQLite

セットアップ不要。デフォルトのデータベース。

### PostgreSQL

pg8000（純Python製ドライバ）を使用。32-bit Python環境でも動作。

```bash
# Docker でセットアップ
docker run -d --name jrvltsql-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15
```
