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
| 1 | 差分データ取得 | 通常使用 |
| 2 | 未読データ取得 | 既読データは返さない |
| 3 | セットアップ（ダイアログあり） | 初回のみ |
| 4 | 分割セットアップ | 初回のみ |

## トラブルシューティング

### -203 エラー（初回セットアップ未完了）

NVDTLab設定ツールを起動し、初回セットアップ（全データダウンロード）を実行してください。

### -3 エラー（ファイル未検出）

`option=2` で既読データを再取得しようとした場合に発生します。`fromtime` を新しいタイムスタンプに更新してください。

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
