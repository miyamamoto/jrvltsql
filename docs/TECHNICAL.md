# 技術詳細

## Python環境

**32-bit Pythonが必須です。**

JV-Link / NV-Link のCOM DLLは32-bitのため、32-bit Pythonから直接呼び出す必要があります。

### なぜ64-bitを採用しないか

DLL Surrogateを設定すれば64-bit Pythonからも利用可能ですが、以下の問題があります：

- `option=3/4`（セットアップモード）がアウトプロセス通信でハングする
- 取得できるデータに差はない（32-bitと同一）
- 追加のレジストリ設定が必要で運用が複雑になる

**32-bitで全機能が利用可能**なため、64-bit対応は不要です。

## NV-Link (地方競馬DATA)

### 初期化キー

NV-Linkの初期化キーは `"UNKNOWN"` を使用してください。他のキーでは `-301` 認証エラーが発生します。

`config/config.yaml` に設定：

```yaml
nvlink:
  initialization_key: "UNKNOWN"
```

### ProgID

- 正しい ProgID: `NVDTLabLib.NVLink`（`NVDTLab.NVLink` ではない）

### データ読み取り: NVGets vs NVRead

NV-Linkのデータ読み取りには **NVGets** を使用してください（NVReadではなく）。

```python
# NVGets: バイト配列で読み取り（推奨）
buf = bytearray(110000)
result = link.NVGets(buf, 110000, "")
# result[0]: 戻り値, result[1]: データ(bytes), result[2]: ファイル名

# NVRead: 文字列で読み取り（JV-Link互換、非推奨）
result = link.NVRead("", 110000, "")
# result[0]: 戻り値, result[1]: データ(str), result[3]: ファイル名
```

**バッファサイズ**: `110000` が必須です。H1レコードは28,955バイトあり、50000以下では `-3` エラーになります。

> **参考**: kmy-keiba（NV-Link利用の競馬ソフト）もNVGetsをバッファサイズ110000で使用しています。

### NVRead/NVGets 戻り値

| 値 | 意味 |
|----|------|
| > 0 | データあり（データ長） |
| 0 | 読み取り完了 |
| -1 | ファイル切り替え（読み続ける） |
| -3 | ダウンロード中（該当ファイルが未DL） |
| -116 | 未提供データスペック |
| -301 | 認証エラー（初期化キーが不正） |
| -402/-403 | ファイル破損（NVFiledeleteで削除して続行） |
| -502 | ダウンロード失敗 |

> **注意**: `-3` は「ファイル未検出」ではなく「**ダウンロード中**」を意味します。該当ファイルがまだサーバーからダウンロードされていない状態です。

### NVStatus 戻り値

| 値 | 意味 |
|----|------|
| 0 | ダウンロード完了（または未開始） |
| > 0 | ダウンロード進行中（DL済みファイル数） |
| -502 | ダウンロード失敗 |

### ダウンロード手順

NV-Linkのデータ取得は **ダウンロードフェーズ** と **読み取りフェーズ** の2段階で行います。

#### 1. ダウンロードフェーズ（option=3）

```python
import win32com.client
import pythoncom

link = win32com.client.Dispatch("NVDTLabLib.NVLink")
link.NVInit("UNKNOWN")
link.ParentHWnd = hwnd  # ウィンドウハンドル（必須）

# option=3（セットアップ）でダウンロード開始
result = link.NVOpen("RACE", fromtime, 3)
# result: (rc, read_count, download_count, timestamp)
```

#### 2. ダウンロード完了待ち

```python
while True:
    pythoncom.PumpWaitingMessages()  # COMメッセージポンプ（必須）
    status = link.NVStatus()
    if status < 0:   # エラー (-502等)
        break
    if status >= download_count:  # 完了
        break
    time.sleep(0.08)
```

#### 3. -502 リトライ戦略

NV-Linkのダウンロードサーバーは不安定で、15〜20ファイル程度ダウンロードすると `-502`（ダウンロード失敗）が発生することがあります。これはNV-Link側の既知の問題です。

**対策**: リトライにより着実にファイルがキャッシュされるため、繰り返し実行することで全ファイルのダウンロードが完了します。

```python
for attempt in range(MAX_RETRIES):
    link = win32com.client.Dispatch("NVDTLabLib.NVLink")
    link.NVInit("UNKNOWN")
    link.ParentHWnd = hwnd

    result = link.NVOpen("RACE", "20250101000000", 3)
    rc, read_count, dl_count, ts = result

    if dl_count == 0:
        # ダウンロード完了！読み取りフェーズへ
        break

    # NVStatusをポーリング
    while True:
        pythoncom.PumpWaitingMessages()
        st = link.NVStatus()
        if st < 0:  # -502等
            break
        if st >= dl_count:
            break
        time.sleep(0.08)

    link.NVClose()

    if st == -502:
        time.sleep(10)  # 待機してリトライ
        continue
```

**ポイント**:
- 各リトライで `dl_count`（残りDL数）が減少していく
- `dl_count == 0` になればダウンロード完了
- `ParentHWnd` の設定が必須（未設定だと `-100` エラー）
- `pythoncom.PumpWaitingMessages()` の呼び出しが必須（COMの非同期DLに必要）
- `-421`（サーバーエラー）の場合は30秒以上待機してからリトライ

#### 4. 読み取りフェーズ

ダウンロード完了後、NVGetsでレコードを読み取ります：

```python
result = link.NVOpen("RACE", fromtime, 2)  # option=2で差分読み取り

while True:
    rd = link.NVGets(buf, 110000, "")
    rc = rd[0]
    if rc > 0:
        data = rd[1]       # bytes (CP932)
        filename = rd[2]   # ファイル名
        rec_type = data[:2].decode('cp932')  # "RA", "SE", "HR" 等
        # レコードをパースしてDBに保存
    elif rc == -1:
        continue  # ファイル切り替え
    elif rc == 0:
        break     # 読み取り完了
    elif rc == -3:
        continue  # DL中のファイル（スキップ）
```

### NVDファイル構造

NVDファイルはZIPアーカイブで、以下のパスに保存されます：

- セットアップデータ: `C:\UmaConn\chiho.k-ba\data\data\YYYY\`
- キャッシュデータ: `C:\UmaConn\chiho.k-ba\data\cache\YYYY\`

#### ファイルプレフィックスとレコードタイプ

| プレフィックス | レコードタイプ | 内容 |
|---------------|---------------|------|
| `RANV` | RA | レース情報 |
| `SENV` | SE | 出走馬情報 |
| `HRNV` | HR | 払戻情報 |
| `HANV` | HA | 払戻情報（NAR独自） |
| `H1NV` | H1 | 票数情報 |
| `H6NV` | H6 | 票数情報（3連単） |
| `O1NV`〜`O6NV` | O1〜O6 | オッズ |
| `OANV` | OA | オッズ（NAR独自） |
| `WFNV` | WF | 重勝式 |
| `BNWV` | BN | 馬主マスタ |
| `CHWV` | CH | 調教師マスタ |
| `KSWV` | KS | 騎手マスタ |
| `NCWV` | NC | 競馬場マスタ |

各NVDファイルはZIP内に `DD.txt`（日付）というテキストファイルを含み、Shift-JIS (CP932) でエンコードされています。

#### リアルタイムデータ

速報データ（0B15等）は `.rtd` 拡張子でキャッシュに保存されます。

### NVOpen option パラメータ

| option | 動作 | 備考 |
|--------|------|------|
| 1 | 通常取得 | ローカルにあるデータを取得 |
| 2 | 未読データ取得 | 既読データは返さない |
| 3 | セットアップ（全データDL） | 初回 or 12ヶ月以上前のデータ取得時 |
| 4 | 分割セットアップ | 初回のみ |

> **注意**: option=1/2 はローカルにダウンロード済みのデータのみ返します。未ダウンロードのレコードタイプは取得できません。初回は必ず option=3 でデータをダウンロードしてください。

## トラブルシューティング

### -203 エラー（初回セットアップ未完了）

NVDTLab設定ツールを起動し、初回セットアップ（全データダウンロード）を実行してください。

### -3 エラー（ダウンロード中）

該当ファイルがまだサーバーからダウンロードされていません。option=3 でセットアップダウンロードを完了してから再度 option=1/2 で読み取ってください。

### -502 エラー（ダウンロード失敗）

NV-Linkのダウンロードサーバーが不安定で、15〜20ファイル程度で接続が切断されます。**リトライにより着実にファイルがキャッシュされる**ため、自動リトライで対処してください（上記「-502 リトライ戦略」参照）。

### -116 エラー（未提供データスペック）

NV-Linkで未対応のデータスペック（例: DIFN option=2）を指定した場合に発生します。

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
