# JRVLTSQL

JRA-VAN DataLab / 地方競馬DATA の競馬データをSQLite・PostgreSQLにインポートするツール

## 特徴

- **中央競馬 (JRA)**: JRA-VAN DataLab (JV-Link) 対応
- **地方競馬 (NAR)**: 地方競馬DATA UmaConn (NV-Link) 対応
- **41種のパーサー**: レース・馬・騎手・オッズ・払戻など幅広いデータに対応
- **データベース**: SQLite（セットアップ不要）/ PostgreSQL 対応
- **リアルタイム監視**: オッズ・速報データの自動取得

## 必要要件

- Windows 10/11
- Python 3.12以上（32-bit必須 ※JV-Link/NV-LinkのCOM DLLが32-bitのため）

## インストール

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

## 中央競馬 (JRA) セットアップ

### 1. JRA-VAN DataLab会員登録

1. [JRA-VAN DataLab](https://jra-van.jp/) にアクセス
2. 会員登録を行い、サービスキーを取得（月額制）
3. JV-Linkソフトウェアをダウンロード・インストール

### 2. JV-Link初期設定

1. JV-Link設定ツールを起動（スタートメニュー → JRA-VAN → JV-Link設定）
2. サービスキーを入力（形式: `XXXX-XXXX-XXXX-XXXX-X`）
3. 初回データダウンロードを実行（全データ取得に数時間かかります）

### 3. 設定ファイル

`config/config.yaml` にサービスキーを設定：

```yaml
jvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"  # JRA-VANから取得したキー
```

または環境変数で設定：

```bash
set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X
```

### 4. データ取得

**quickstart.bat をダブルクリック** で対話形式のセットアップが始まります。

```bash
python scripts/quickstart.py              # 対話形式
python scripts/quickstart.py --years 5    # 過去5年分
python scripts/quickstart.py --no-odds    # オッズ除外
python scripts/quickstart.py -y           # 確認スキップ
```

## 地方競馬 (NAR) セットアップ

### 1. 地方競馬DATA会員登録

1. [地方競馬DATA](https://www.keiba-data.com/) にアクセス
2. 会員登録を行い、サービスキーを取得（月額制）
3. UmaConnソフトウェアをダウンロード・インストール

### 2. UmaConn初期設定

1. UmaConn設定ツールを起動（`C:\UmaConn\chiho.k-ba\data\UmaConn設定.exe`）
2. サービスキーを入力（形式: `XXXX-XXXX-XXXX-XXXX-X`）
3. 「全データダウンロード」を実行（初回のみ、数時間かかります）
4. ダウンロード完了後、NVDファイルが `C:\UmaConn\chiho.k-ba\data\` 以下に保存されます

### 3. 設定ファイル

`config/config.yaml` に以下を設定：

```yaml
nvlink:
  service_key: "XXXX-XXXX-XXXX-XXXX-X"  # 地方競馬DATAから取得したキー
  initialization_key: "UNKNOWN"           # 必ず "UNKNOWN" を指定
```

**重要**: `initialization_key` は必ず `"UNKNOWN"` にしてください。他の値では認証エラー（-301）が発生します。

### 4. データ取得

```bash
jltsql fetch --source nar --from 20240101 --to 20241231 --spec RACE
jltsql monitor --source nar
jltsql status --source all
```

## CLIコマンド

```bash
jltsql status           # ステータス確認
jltsql fetch --spec RA  # 個別データ取得
jltsql monitor          # リアルタイム監視
```

## データベース

```bash
jltsql fetch --db sqlite      # SQLite（デフォルト、セットアップ不要）
jltsql fetch --db postgresql  # PostgreSQL（pg8000ドライバ使用）
```

## 対応レコード

### 中央競馬 (JRA)

レース情報(RA)、馬情報(SE)、払戻(HR)、票数(H1/H6)、オッズ(O1-O6)、騎手(KS)、調教師(CH)、重勝式(WF)、他多数（38種）

### 地方競馬 (NAR)

レース情報(RA)、馬情報(SE)、払戻(HR/HA)、票数(H1/H6)、オッズ(O1-O6)、重勝式(WF)、馬主(BN)

地方競馬データは `_NAR` サフィックス付きのテーブルに保存されます（例: `NL_RA_NAR`）。

## ドキュメント

- [技術詳細](docs/TECHNICAL.md) - NV-Link設定、NVDファイル構造、トラブルシューティング
- [アーキテクチャ](docs/ARCHITECTURE_DESIGN.md) - 設計ドキュメント
- [CLI リファレンス](docs/CLI.md) - コマンド詳細
- [設定](docs/CONFIGURATION.md) - 設定ファイルの詳細

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
