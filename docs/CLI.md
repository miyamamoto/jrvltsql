# JRVLTSQL CLI リファレンス

JRVLTSQLコマンドラインインターフェース（CLI）の完全なリファレンスガイド

## 目次

1. [概要](#概要)
2. [グローバルオプション](#グローバルオプション)
3. [コマンド一覧](#コマンド一覧)
4. [データベース選択](#データベース選択)
5. [データ種別コード](#データ種別コード)
6. [使用例](#使用例)

---

## 概要

JRVLTSQLは、JRA-VAN DataLab（中央競馬）/ 地方競馬DATA（地方競馬）の競馬データをSQLite/PostgreSQLにインポートするためのコマンドラインツールです。

### 基本的な使い方

```bash
jltsql [グローバルオプション] <コマンド> [コマンドオプション]
```

### クイックスタート

```bash
# 1. 初期化
jltsql init

# 2. 設定ファイルを編集 (config/config.yaml)
# サービスキーを設定してください

# 3. データ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# 4. リアルタイム監視
jltsql monitor
```

---

## グローバルオプション

すべてのコマンドで使用できるオプション：

### `--config`, `-c`

設定ファイルのパスを指定します。

```bash
jltsql --config /path/to/config.yaml fetch --spec RACE --from 20240101 --to 20241231
```

- デフォルト: `config/config.yaml`
- 設定ファイルが存在しない場合は `jltsql init` を実行してください

### `--verbose`, `-v`

詳細なログ出力を有効にします（DEBUGレベル）。

```bash
jltsql --verbose fetch --spec RACE --from 20240101 --to 20241231
```

### `--version`

バージョン情報を表示します。

```bash
jltsql --version
```

### `--help`

ヘルプメッセージを表示します。

```bash
jltsql --help
jltsql fetch --help  # 特定のコマンドのヘルプ
```

---

## コマンド一覧

### `init` - プロジェクト初期化

プロジェクトの初期化を行い、設定ファイルとディレクトリを作成します。

```bash
jltsql init [OPTIONS]
```

**オプション:**

- `--force`: 既存の設定ファイルを上書きします

**使用例:**

```bash
# 初期化
jltsql init

# 強制的に再初期化
jltsql init --force
```

**実行内容:**

1. `config/`, `data/`, `logs/` ディレクトリの作成
2. `config/config.yaml.example` から `config/config.yaml` をコピー

**次のステップ:**

1. `config/config.yaml` を編集してJV-Linkサービスキーを設定
2. `jltsql fetch --help` でデータ取得方法を確認

---

### `fetch` - 過去データ取得

JRA-VAN DataLabから過去のデータを取得してデータベースにインポートします。

```bash
jltsql fetch --from YYYYMMDD --to YYYYMMDD --spec DATA_SPEC [OPTIONS]
```

**必須オプション:**

- `--from`: 開始日（YYYYMMDD形式）
- `--to`: 終了日（YYYYMMDD形式）※この日付までのレコードをフィルタリング
- `--spec`: データ種別（RACE, DIFF, O1-O6など）

**オプション:**

- `--option`: JVOpenオプション（デフォルト: 1）
  - `1`: 通常データ（差分データ取得、蓄積系メンテナンス用）
  - `2`: 今週データ（直近のレースのみ）
  - `3`: セットアップ（全データ取得、ダイアログ表示あり）
  - `4`: 分割セットアップ（全データ取得、初回のみダイアログ）
- `--db`: データベースタイプ（sqlite/postgresql）
- `--batch-size`: バッチサイズ（デフォルト: 1000）
- `--progress/--no-progress`: プログレス表示の有無（デフォルト: 有効）

**使用例:**

```bash
# レースデータを取得（通常データ）
jltsql fetch --from 20240101 --to 20241231 --spec RACE --option 1

# 今週のレースデータのみ取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE --option 2

# セットアップ（全データ取得）
jltsql fetch --from 20240101 --to 20241231 --spec DIFF --option 3

# マスタデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec DIFF

# オッズデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec O1

# PostgreSQLに保存
jltsql fetch --from 20240101 --to 20241231 --spec RACE --db postgresql

# バッチサイズを変更
jltsql fetch --from 20240101 --to 20241231 --spec RACE --batch-size 500
```

**注意事項:**

- `--to` パラメータはクライアント側でレコードをフィルタリングします
- セットアップモード（option=3, 4）を使用すると、ダイアログが表示されます
- データ種別とoptionの組み合わせには制限があります（下記参照）

**データ種別とoptionの対応:**

| option | 使用可能なデータ種別 |
|--------|-------------------|
| 1 | TOKU, RACE, DIFF, DIFN, BLOD, BLDN, MING, SLOP, WOOD, YSCH, HOSE, HOSN, HOYU, COMM, SNAP, O1-O6 |
| 2 | TOKU, RACE, TCVN, RCVN |
| 3, 4 | option 1と同じ |

---

### `monitor` - リアルタイム監視

リアルタイムでデータを監視し、自動的にデータベースに取り込みます。

```bash
jltsql monitor [OPTIONS]
```

**オプション:**

- `--daemon`: バックグラウンドで実行
- `--spec`: データ種別（デフォルト: RACE）
- `--interval`: ポーリング間隔（秒、デフォルト: 60）
- `--db`: データベースタイプ（sqlite/postgresql）

**使用例:**

```bash
# フォアグラウンドで監視
jltsql monitor

# バックグラウンドで監視
jltsql monitor --daemon

# 特定のデータ種別を監視
jltsql monitor --spec RACE --interval 30

# PostgreSQLに保存
jltsql monitor --db postgresql
```

**注意事項:**

- フォアグラウンドモードでは Ctrl+C で停止できます
- デーモンモードでは別途停止コマンドが必要です（現在未実装）

---

### `realtime` - リアルタイムデータコマンド

JV-Linkリアルタイムデータストリームを管理するコマンド群です。

#### `realtime start` - リアルタイム監視開始

リアルタイムデータの監視サービスを開始します。

```bash
jltsql realtime start [OPTIONS]
```

**オプション:**

- `--specs`: 監視するデータ種別（カンマ区切り、デフォルト: 0B12）
- `--db`: データベースタイプ（sqlite/postgresql）
- `--batch-size`: バッチサイズ（デフォルト: 100）
- `--no-create-tables`: テーブル自動作成を無効化

**使用例:**

```bash
# レース結果を監視
jltsql realtime start

# 複数のデータ種別を監視
jltsql realtime start --specs 0B12,0B15

# バッチサイズを変更
jltsql realtime start --specs 0B12 --batch-size 50
```

**主なデータ種別コード:**

- `0B12`: レース結果（デフォルト）
- `0B15`: 払戻
- `0B31`: オッズ
- `0B33`: 馬番号
- `0B35`: 天候・馬場状態

#### `realtime status` - ステータス確認

リアルタイム監視サービスのステータスを表示します（現在未実装）。

```bash
jltsql realtime status
```

#### `realtime stop` - リアルタイム監視停止

リアルタイム監視サービスを停止します（現在未実装）。

```bash
jltsql realtime stop
```

現在は Ctrl+C で監視プロセスを停止してください。

#### `realtime timeseries` - 時系列オッズデータ取得

過去の時系列オッズデータを取得します。JV-Linkは最大1年分の履歴データを提供します。

```bash
jltsql realtime timeseries [OPTIONS]
```

**オプション:**

- `--spec`, `-s`: データ種別コード（デフォルト: 0B30）
- `--from-date`, `-f`: 開始日（YYYYMMDD形式、デフォルト: 1年前）
- `--to-date`, `-t`: 終了日（YYYYMMDD形式、デフォルト: 今日）
- `--db`: データベースタイプ
- `--db-path`: SQLiteデータベースのパス

**使用例:**

```bash
# 単勝オッズを取得
jltsql realtime timeseries

# 特定の期間の複勝・枠連オッズを取得
jltsql realtime timeseries --spec 0B31 --from-date 20241201

# 複数のオッズ種別を取得
jltsql realtime timeseries --spec 0B31,0B32 --db-path data/keiba.db
```

**オッズデータ種別:**

- `0B30`: 単勝オッズ
- `0B31`: 複勝・枠連オッズ
- `0B32`: 馬連オッズ
- `0B33`: ワイドオッズ
- `0B34`: 馬単オッズ
- `0B35`: 3連複オッズ
- `0B36`: 3連単オッズ

#### `realtime specs` - 利用可能なデータ種別一覧

JV-Linkリアルタイムデータの全種別を表示します。

```bash
jltsql realtime specs
```

**出力カテゴリ:**

- Race Data: レースデータ、払戻など
- Odds Data: オッズデータ
- Master Data: マスタデータ
- Other Data: その他のデータ

---

### `create-tables` - テーブル作成

データベースにテーブルを作成します。

```bash
jltsql create-tables [OPTIONS]
```

**オプション:**

- `--db`: データベースタイプ（sqlite/postgresql）
- `--all`: すべてのテーブルを作成（NL_とRT_）
- `--nl-only`: NL_（Normal Load）テーブルのみ作成
- `--rt-only`: RT_（Real-Time）テーブルのみ作成

**使用例:**

```bash
# すべてのテーブルを作成
jltsql create-tables

# SQLiteにすべてのテーブルを作成
jltsql create-tables --db sqlite

# NL_テーブルのみ作成
jltsql create-tables --nl-only

# RT_テーブルのみ作成
jltsql create-tables --rt-only
```

**テーブルの種類:**

- **NL_テーブル**: 蓄積系データ（レース、馬、騎手、調教師など）
- **RT_テーブル**: 速報系データ（リアルタイムオッズ、レース結果など）
- **TS_テーブル**: 時系列オッズデータ

---

### `create-indexes` - インデックス作成

クエリパフォーマンス向上のためのインデックスを作成します。

```bash
jltsql create-indexes [OPTIONS]
```

**オプション:**

- `--db`: データベースタイプ（sqlite/postgresql）
- `--table`: 特定のテーブルのみインデックスを作成

**使用例:**

```bash
# すべてのテーブルにインデックスを作成
jltsql create-indexes

# SQLiteにインデックスを作成
jltsql create-indexes --db sqlite

# 特定のテーブルのみ
jltsql create-indexes --table NL_RA
```

**作成されるインデックス:**

- 日付フィールド（開催年月日、データ作成年月日）
- 競馬場・レース番号フィールド
- リアルタイムデータの発表時刻
- JOIN最適化のための複合インデックス

---

### `export` - データエクスポート

データベースからデータをファイルにエクスポートします。

```bash
jltsql export --table TABLE_NAME --output FILE_PATH [OPTIONS]
```

**必須オプション:**

- `--table`: エクスポートするテーブル名
- `--output`, `-o`: 出力ファイルパス

**オプション:**

- `--format`: 出力形式（csv/json/parquet、デフォルト: csv）
- `--where`: SQL WHERE句（例: '開催年月日 >= 20240101'）
- `--db`: データベースタイプ（sqlite/postgresql）

**使用例:**

```bash
# レースデータをCSVでエクスポート
jltsql export --table NL_RA --output races.csv

# 馬データをJSONでエクスポート
jltsql export --table NL_SE --format json --output horses.json

# 条件を指定してエクスポート
jltsql export --table NL_RA --where "開催年月日 >= 20240101" --output 2024_races.csv

# Parquet形式でエクスポート
jltsql export --table NL_HR --format parquet --output payouts.parquet
```

**対応フォーマット:**

- **CSV**: カンマ区切りテキスト（デフォルト）
- **JSON**: JSON配列形式
- **Parquet**: Apache Parquet列指向形式（pandas、pyarrow必須）

**注意事項:**

- WHERE句はパラメータ化されていないため、信頼できる入力のみ使用してください
- Parquet形式を使用する場合は `pip install pandas pyarrow` が必要です

---

### `config` - 設定管理

設定ファイルの内容を表示・管理します。

```bash
jltsql config [OPTIONS]
```

**オプション:**

- `--show`: 現在の設定を表示
- `--get KEY`: 特定の設定値を取得
- `--set KEY=VALUE`: 設定値を変更（現在未実装）

**使用例:**

```bash
# すべての設定を表示
jltsql config --show

# 特定の設定値を取得
jltsql config --get database.type

# 設定値を変更（未実装）
jltsql config --set database.type=sqlite
```

**設定項目:**

- `jvlink.sid`: JV-Link SID
- `jvlink.service_key`: JV-Linkサービスキー
- `database.type`: データベースタイプ
- `database.path`: データベースパス
- `logging.level`: ログレベル
- `logging.file`: ログファイルパス

---

### `status` - ステータス表示

JRVLTSQLの現在のステータスを表示します。

```bash
jltsql status
```

**表示内容:**

- バージョン情報
- 稼働状態

---

### `version` - バージョン情報

バージョン情報を表示します。

```bash
jltsql version
```

---

## データベース選択

JRVLTSQLは2種類のデータベースをサポートしています。

### SQLite（デフォルト）

**特徴:**

- ファイルベースの軽量データベース
- セットアップ不要
- 個人利用に最適

**使用方法:**

```bash
jltsql fetch --db sqlite --from 20240101 --to 20241231 --spec RACE
```

**設定例（config/config.yaml）:**

```yaml
database:
  type: sqlite

databases:
  sqlite:
    path: data/keiba.db
```

### PostgreSQL

**特徴:**

- 本格的なリレーショナルデータベース
- 複数ユーザー対応
- 大規模データに最適

**使用方法:**

```bash
jltsql fetch --db postgresql --from 20240101 --to 20241231 --spec RACE
```

**設定例（config/config.yaml）:**

```yaml
database:
  type: postgresql

databases:
  postgresql:
    host: localhost
    port: 5432
    database: keiba
    user: postgres
    password: your_password
```

---

## データ種別コード

### JVOpen データ種別（蓄積系データ）

#### 主要データ種別

| コード | 名称 | 説明 | 含まれるレコード |
|--------|------|------|----------------|
| RACE | レースデータ | レース情報と成績 | RA, SE, HR, WF, JG |
| DIFF | マスタデータ | 各種マスタ情報 | UM, KS, CH, BR, BN, HN, SK, RC, HC |
| DIFN | マスタデータ | DIFFの別名 | DIFFと同じ |

#### 追加データ種別

| コード | 名称 | 説明 |
|--------|------|------|
| YSCH | 開催スケジュール | レース開催予定 |
| TOKU | 特別登録馬 | 特別レース登録情報 |
| SNAP | 出馬表 | 出走馬一覧 |
| SLOP | 坂路調教 | 坂路調教データ |
| BLOD | 血統情報 | 馬の血統データ |
| BLDN | 血統情報 | BLODの別名 |
| HOYU | 馬名の意味由来 | 馬名の由来情報 |
| HOSE | 競走馬市場取引価格 | 市場価格データ |
| HOSN | 競走馬市場取引価格 | HOSEの別名 |
| MING | データマイニング予想 | 予想データ |
| WOOD | ウッドチップ調教 | ウッド調教データ |
| COMM | コメント情報 | 各種コメント |

#### 変更情報（option=2のみ）

| コード | 名称 | 説明 |
|--------|------|------|
| TCVN | 調教師変更情報 | 調教師の変更履歴 |
| RCVN | 騎手変更情報 | 騎手の変更履歴 |

#### オッズデータ

| コード | 名称 | 説明 |
|--------|------|------|
| O1 | 単勝・複勝・枠連オッズ | 確定オッズ |
| O2 | 馬連オッズ | 確定オッズ |
| O3 | ワイドオッズ | 確定オッズ |
| O4 | 馬単オッズ | 確定オッズ |
| O5 | 3連複オッズ | 確定オッズ |
| O6 | 3連単オッズ | 確定オッズ |

### JVRTOpen データ種別（リアルタイムデータ）

#### 速報系データ（0B1x系）

日付単位（YYYYMMDD形式）でデータを取得します。

| コード | 名称 | 説明 |
|--------|------|------|
| 0B11 | 速報馬体重 | 馬体重情報（WH） |
| 0B12 | 速報レース情報・払戻 | レース結果と払戻（RA, SE, HR） |
| 0B13 | データマイニング予想 | タイム型予想（DM） |
| 0B14 | 速報開催情報・一括 | 開催日情報（WE, AV, JC, TC, CC） |
| 0B15 | 速報レース情報 | 出走馬名表以降（RA, SE, HR） |
| 0B16 | 速報開催情報・変更 | 騎手変更等（WE, AV, JC, TC, CC） |
| 0B17 | 対戦型データマイニング予想 | 対戦型予想（TM） |
| 0B41 | 騎手変更情報 | 騎手変更（RC） |
| 0B42 | 調教師変更情報 | 調教師変更（TC） |
| 0B51 | コース情報 | コース情報（CS） |

#### 時系列データ（0B2x-0B3x系）

レース単位（YYYYMMDDJJRR形式）でデータを取得します。過去1年分が公式提供期間です。

| コード | 名称 | 説明 |
|--------|------|------|
| 0B20 | 票数情報 | 投票数（H1, H6） |
| 0B30 | 単勝オッズ | 単勝時系列オッズ（O1） |
| 0B31 | 複勝・枠連オッズ | 複勝・枠連時系列（O1, O2） |
| 0B32 | 馬連オッズ | 馬連時系列（O2） |
| 0B33 | ワイドオッズ | ワイド時系列（O3） |
| 0B34 | 馬単オッズ | 馬単時系列（O4） |
| 0B35 | 3連複オッズ | 3連複時系列（O5） |
| 0B36 | 3連単オッズ | 3連単時系列（O6） |

**注意:** 時系列データは過去1年間が公式提供期間ですが、実際には2003年10月4日まで遡及可能です（保証外）。

### レコード種別

データベーステーブルに格納されるレコードの種別です。

#### レースデータ

| コード | テーブル | 説明 |
|--------|---------|------|
| RA | NL_RA | レース詳細情報 |
| SE | NL_SE | 馬毎レース情報 |
| HR | NL_HR | 払戻情報 |
| WE | NL_WE | 天候・馬場状態 |
| WH | RT_WH | 馬体重（リアルタイム） |
| WF | NL_WF | WIN5 |
| JG | NL_JG | 競走除外馬 |

#### マスタデータ

| コード | テーブル | 説明 |
|--------|---------|------|
| UM | NL_UM | 競走馬マスタ |
| KS | NL_KS | 騎手マスタ |
| CH | NL_CH | 調教師マスタ |
| BR | NL_BR | 生産者マスタ |
| BN | NL_BN | 馬主マスタ |
| HN | NL_HN | 繁殖馬マスタ |
| SK | NL_SK | 産駒マスタ |
| RC | NL_RC | レコードマスタ |
| HC | NL_HC | 配当マスタ |

#### オッズデータ

| コード | テーブル | 説明 |
|--------|---------|------|
| O1 | NL_O1 / TS_O1 | 単勝・複勝・枠連オッズ |
| O2 | NL_O2 / TS_O2 | 馬連・枠連オッズ |
| O3 | NL_O3 / TS_O3 | ワイドオッズ |
| O4 | NL_O4 / TS_O4 | 馬単オッズ |
| O5 | NL_O5 / TS_O5 | 3連複オッズ |
| O6 | NL_O6 / TS_O6 | 3連単オッズ |

---

## 使用例

### 基本的なワークフロー

#### 1. 初回セットアップ

```bash
# プロジェクト初期化
jltsql init

# 設定ファイルを編集（サービスキーを設定）
notepad config\config.yaml

# テーブル作成
jltsql create-tables

# インデックス作成
jltsql create-indexes
```

#### 2. 過去データの取得

```bash
# 2024年のレースデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE

# マスタデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec DIFF

# オッズデータを取得（時間がかかる場合があります）
jltsql fetch --from 20240101 --to 20241231 --spec O1
jltsql fetch --from 20240101 --to 20241231 --spec O2
```

#### 3. リアルタイム監視

```bash
# レース結果をリアルタイムで取得
jltsql realtime start --specs 0B12

# レース結果と払戻を取得
jltsql realtime start --specs 0B12,0B15
```

### データ分析ワークフロー

#### データエクスポートして分析

```bash
# 2024年の全レースをCSVでエクスポート
jltsql export --table NL_RA --where "開催年月日 >= 20240101 AND 開催年月日 <= 20241231" --output 2024_races.csv

# 馬情報をJSONでエクスポート
jltsql export --table NL_SE --format json --output horses.json

# PostgreSQLで高速分析
jltsql export --table NL_RA --format parquet --output races.parquet --db postgresql
```

### 複数年のデータ取得

```bash
# 過去5年分のレースデータを取得
jltsql fetch --from 20200101 --to 20241231 --spec RACE --option 4

# 過去5年分のマスタデータを取得
jltsql fetch --from 20200101 --to 20241231 --spec DIFF --option 4
```

### オッズデータの取得

```bash
# 確定オッズを取得
jltsql fetch --from 20240101 --to 20241231 --spec O1  # 単勝・複勝・枠連
jltsql fetch --from 20240101 --to 20241231 --spec O2  # 馬連
jltsql fetch --from 20240101 --to 20241231 --spec O3  # ワイド

# 時系列オッズを取得（過去1年分）
jltsql realtime timeseries --spec 0B30 --from-date 20240101  # 単勝
jltsql realtime timeseries --spec 0B31 --from-date 20240101  # 複勝・枠連
jltsql realtime timeseries --spec 0B32 --from-date 20240101  # 馬連
```

### バックアップとリストア

```bash
# SQLiteデータベースをバックアップ
copy data\keiba.db backup\keiba_backup_%date%.db

# 特定のテーブルをエクスポート
jltsql export --table NL_RA --format json --output backup\races.json
jltsql export --table NL_SE --format json --output backup\horses.json
```

### トラブルシューティング

```bash
# 詳細ログを有効にして実行
jltsql --verbose fetch --from 20240101 --to 20241231 --spec RACE

# 設定を確認
jltsql config --show

# データベース接続を確認
jltsql status
```

---

## 付録

### 競馬場コード

| コード | 競馬場名 |
|--------|---------|
| 01 | 札幌 |
| 02 | 函館 |
| 03 | 福島 |
| 04 | 新潟 |
| 05 | 東京 |
| 06 | 中山 |
| 07 | 中京 |
| 08 | 京都 |
| 09 | 阪神 |
| 10 | 小倉 |

### グレードコード

| コード | グレード |
|--------|---------|
| A | G1 |
| B | G2 |
| C | G3 |
| D | リステッド |
| E | オープン |
| F | 1600万下 |
| G | 1000万下 |
| H | 500万下 |
| I | 未勝利 |
| J | 新馬 |

### 馬場状態コード

| コード | 状態 |
|--------|-----|
| 1 | 良 |
| 2 | 稍重 |
| 3 | 重 |
| 4 | 不良 |

### トラック種別コード

| コード | 種別 |
|--------|-----|
| 1 | 芝 |
| 2 | ダート |
| 3 | 障害芝 |
| 4 | 障害ダート |

### JVOpenオプション詳細

| option | 名称 | 説明 | ダイアログ | 用途 |
|--------|------|------|-----------|------|
| 1 | 通常データ | 差分データ取得 | なし | 日次更新 |
| 2 | 今週データ | 直近レースのみ | なし | 速報用途 |
| 3 | セットアップ | 全データ取得 | あり | 初回構築 |
| 4 | 分割セットアップ | 全データ取得（分割） | 初回のみ | 大量データ |

### エラーコード

| コード | 意味 |
|--------|------|
| 0 | 成功 |
| -1 | 失敗 |
| -2 | データなし |
| -100 | サービスキー未設定 |
| -101 | サービスキーが無効 |
| -111 | 契約外データ種別 |
| -114 | 契約外データ種別（警告） |
| -201 | データベースエラー |
| -301 | ダウンロード中 |

---

## 参考資料

- [JRA-VAN公式サイト](https://jra-van.jp/)
- [JV-Data仕様書](https://jra-van.jp/dlb/sdk/index.html)
- [プロジェクトリポジトリ](https://github.com/miyamamoto/jrvltsql)
- [ライセンス情報](../README.md#ライセンス)

---

## お問い合わせ

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得したデータは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってご利用ください。

---

**最終更新:** 2025-12-06
**バージョン:** 0.1.0-alpha
