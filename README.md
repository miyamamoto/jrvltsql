# JLTSQL - JRA-VAN Link To SQL

JRA-VAN DataLabの競馬データをSQLite/DuckDB/PostgreSQLにリアルタイムインポートするPythonツール

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Version](https://img.shields.io/badge/version-1.0.0--rc1-orange.svg)](https://github.com/miyamamoto/jltsql/releases)

## 概要

JLTSQLは、JRA-VAN DataLabが提供する競馬データ（JV-Data）を、SQLite、DuckDB、PostgreSQLなどの一般的なデータベースにインポートするためのツールです。リアルタイムでのオッズ更新や馬体重情報の取得にも対応しています。

### 主な機能

- **複数データベース対応**: SQLite、DuckDB、PostgreSQL
- **過去データ一括取得**: 1986年以降の全競馬データ（全38レコードタイプ対応）
- **リアルタイム更新**: オッズ、馬体重、レース結果の即時取得
- **豊富なデータ**: レース情報、馬情報、騎手情報、血統情報、オッズなど（57テーブル）
- **高速インポート**: バッチ処理による効率的なデータ挿入（1000件/バッチ）
- **使いやすいCLI**: 10個のコマンドで簡単操作
- **柔軟なエクスポート**: CSV、JSON、Parquet形式でデータエクスポート
- **設定管理**: CLIから設定の確認・変更が可能

## 動作環境

- **OS**: Windows 10/11 (JV-Link COM APIはWindows専用)
- **Python**: 3.10以上
- **必須**: JRA-VAN DataLab会員登録（月額2,090円）
- **推奨メモリ**: 4GB以上
- **推奨ストレージ**: 10GB以上の空き容量

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/jltsql.git
cd jltsql
```

### 2. 仮想環境の作成

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 設定ファイルの作成

```bash
copy config\config.yaml.example config\config.yaml
```

`config\config.yaml`を編集し、JRA-VANのサービスキーを設定してください。

## クイックスタート

### 1. プロジェクトの初期化

```bash
jltsql init
```

これにより、`config/config.yaml`、`data/`、`logs/` ディレクトリが作成されます。

### 2. 設定ファイルの編集

`config/config.yaml` を編集し、JRA-VANのサービスキーを設定してください：

```yaml
jvlink:
  sid: "JLTSQL"
  service_key: "YOUR_SERVICE_KEY_HERE"
```

### 3. データベーステーブルの作成

```bash
jltsql create-tables
```

全57テーブル（NL_* 38テーブル + RT_* 19テーブル）が作成されます。

### 4. 過去データの取得

```bash
# 2024年のレースデータを取得
jltsql fetch --from 20240101 --to 20241231 --spec RACE
```

### 5. リアルタイム監視の開始

```bash
# バックグラウンドでリアルタイムデータ取得開始
jltsql monitor --daemon
```

### 6. ステータスの確認

```bash
jltsql status
```

## 使用例

### マスタデータの取得

```bash
# 競走馬、騎手、調教師などのマスタデータを取得
python -m src.cli.main fetch --data-spec DIFF
```

### オッズデータの取得

```bash
# 単勝・複勝・枠連オッズを取得
python -m src.cli.main fetch --from 2024-01-01 --to 2024-12-31 --data-spec O1
```

### データベース切り替え

```bash
# PostgreSQLを使用
python -m src.cli.main --config config/postgres.yaml fetch --data-spec RACE
```

## データベーススキーマ

JLTSQLは、JV-Dataの構造を忠実に再現した**57テーブル**を使用します。

### 蓄積系テーブル (NL_*): 38テーブル

主なテーブル:
- **NL_RA**: レース詳細情報
- **NL_SE**: 馬毎レース情報（出走馬情報）
- **NL_HR**: 払戻情報
- **NL_UM**: 競走馬マスタ
- **NL_KS**: 騎手マスタ
- **NL_CH**: 調教師マスタ
- **NL_BN**: 繁殖馬マスタ
- **NL_HN**: 血統情報
- **NL_O1～O6**: オッズ情報（単勝、馬連、ワイド、枠連、馬単、3連複・3連単）
- **NL_YS**: スケジュール情報
- **NL_JG**: 除外馬情報

### 速報系テーブル (RT_*): 19テーブル

リアルタイム更新用のテーブル:
- **RT_RA**: レース詳細（速報）
- **RT_SE**: 馬毎レース情報（速報）
- **RT_HR**: 払戻情報（速報）
- **RT_O1～O6**: オッズ情報（速報）

### 全38レコードタイプ対応

```
AV, BN, BR, BT, CC, CH, CK, CS, DM,
H1, H6, HC, HN, HR, HS, HY,
JC, JG, KS,
O1, O2, O3, O4, O5, O6,
RA, RC, SE, SK,
TC, TK, TM,
UM,
WC, WE, WF, WH,
YS
```

詳細は[データベーススキーマドキュメント](docs/api_reference.md#database-schema)を参照してください。

## 設定

`config/config.yaml`で以下の設定が可能です:

```yaml
jvlink:
  service_key: "YOUR_SERVICE_KEY"  # JRA-VANサービスキー

databases:
  sqlite:
    enabled: true
    path: "./data/keiba.db"

  duckdb:
    enabled: true
    path: "./data/keiba.duckdb"

  postgresql:
    enabled: false
    host: "localhost"
    database: "keiba"
    user: "keiba_user"
    password: "password"

data_fetch:
  initial:
    date_from: "2020-01-01"
    date_to: "2024-12-31"
    data_specs: ["RACE", "DIFF", "O1", "O2"]

  realtime:
    enabled: true
    interval_seconds: 60
```

## コマンドリファレンス

### グローバルオプション

```bash
jltsql [--config FILE] [--verbose] [--version] COMMAND
```

- `--config, -c FILE` : 設定ファイル指定（デフォルト: `config/config.yaml`）
- `--verbose, -v` : 詳細ログ出力（DEBUGレベル）
- `--version` : バージョン情報表示

### コマンド一覧

#### 1. `jltsql init` - プロジェクト初期化

```bash
jltsql init [--force]
```

プロジェクトディレクトリと設定ファイルを作成します。

**オプション**:
- `--force` : 既存の設定ファイルを上書き

#### 2. `jltsql create-tables` - テーブル作成

```bash
jltsql create-tables [--db TYPE] [--all | --nl-only | --rt-only]
```

データベーステーブルを作成します（全57テーブル）。

**オプション**:
- `--db TYPE` : データベースタイプ（sqlite, duckdb, postgresql）
- `--all` : 全テーブル作成（デフォルト）
- `--nl-only` : 蓄積系テーブル（NL_*）のみ作成
- `--rt-only` : 速報系テーブル（RT_*）のみ作成

#### 3. `jltsql create-indexes` - インデックス作成

```bash
jltsql create-indexes [--db TYPE] [--table TABLE]
```

データベースインデックスを作成します（120+インデックス）。

**オプション**:
- `--db TYPE` : データベースタイプ
- `--table TABLE` : 特定テーブルのみインデックス作成

#### 4. `jltsql fetch` - 蓄積データ取得

```bash
jltsql fetch --from YYYYMMDD --to YYYYMMDD --spec SPEC [--db TYPE] [--batch-size N]
```

JRA-VANから蓄積データを取得します。

**オプション**:
- `--from DATE` : 開始日（YYYYMMDD形式、必須）
- `--to DATE` : 終了日（YYYYMMDD形式、必須）
- `--spec SPEC` : データ仕様（RACE, DIFF, YSCH, O1-O6など、必須）
- `--db TYPE` : データベースタイプ
- `--batch-size N` : バッチサイズ（デフォルト: 1000）

**データ仕様の例**:
- `RACE` : レース詳細データ
- `DIFF` : マスタ差分データ
- `YSCH` : スケジュールデータ
- `O1` : 単勝・複勝オッズ
- `O2` : 馬連オッズ
- `O3` : ワイドオッズ
- `O4` : 枠連オッズ
- `O5` : 馬単オッズ
- `O6` : 3連複・3連単オッズ

#### 5. `jltsql monitor` - リアルタイム監視

```bash
jltsql monitor [--daemon] [--spec SPEC] [--interval SECONDS] [--db TYPE]
```

リアルタイムでデータを監視・取得します。

**オプション**:
- `--daemon` : バックグラウンド実行
- `--spec SPEC` : データ仕様（デフォルト: RACE）
- `--interval N` : ポーリング間隔（秒、デフォルト: 60）
- `--db TYPE` : データベースタイプ

#### 6. `jltsql export` - データエクスポート

```bash
jltsql export --table TABLE --output FILE [--format FORMAT] [--where CLAUSE] [--db TYPE]
```

データベースからデータをエクスポートします。

**オプション**:
- `--table TABLE` : テーブル名（必須）
- `--output, -o FILE` : 出力ファイルパス（必須）
- `--format FORMAT` : 出力フォーマット（csv, json, parquet、デフォルト: csv）
- `--where CLAUSE` : SQL WHERE句
- `--db TYPE` : データベースタイプ

**例**:
```bash
# CSV形式でエクスポート
jltsql export --table NL_RA --output races.csv

# JSON形式でエクスポート
jltsql export --table NL_SE --format json --output horses.json

# WHERE句付きエクスポート
jltsql export --table NL_RA --where "開催年月日 >= 20240101" --output 2024_races.csv

# Parquet形式でエクスポート
jltsql export --table NL_HR --format parquet --output payouts.parquet
```

#### 7. `jltsql config` - 設定管理

```bash
jltsql config [--show] [--get KEY] [--set KEY=VALUE]
```

設定ファイルの確認・変更を行います。

**オプション**:
- `--show` : 全設定表示（デフォルト）
- `--get KEY` : 特定値取得（ドット記法: `database.type`）
- `--set KEY=VALUE` : 設定変更（未実装）

**例**:
```bash
# 全設定表示
jltsql config

# データベースタイプ取得
jltsql config --get database.type

# 設定変更（未実装）
jltsql config --set database.type=duckdb
```

#### 8. `jltsql status` - ステータス確認

```bash
jltsql status
```

JLTSQLのバージョンとステータスを表示します。

#### 9. `jltsql version` - バージョン情報

```bash
jltsql version
```

JLTSQLとPythonのバージョン情報を表示します。

#### 10. `jltsql stop` - 監視停止

```bash
jltsql stop
```

実行中のリアルタイム監視を停止します（スタブ実装）。

## 開発

### 開発環境のセットアップ

```bash
pip install -r requirements-dev.txt
pre-commit install
```

### テストの実行

```bash
pytest
```

### コードフォーマット

```bash
black src tests
ruff check src tests
```

## ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

### JRA-VAN Data Lab利用規約

本ツールはJRA-VAN DataLabのデータを使用します。以下の点にご注意ください:

- データの再配布は禁止されています
- 個人利用または自社内利用に限定されます
- 商用利用の場合は別途契約が必要です
- 詳細: https://jra-van.jp/dlb/about/rule.html

## 参考リンク

- [JRA-VAN DataLab公式サイト](https://jra-van.jp/dlb/)
- [JRA-VAN開発者コミュニティ](https://developer.jra-van.jp/)
- [JVLinkToSQLite](https://github.com/urasandesu/JVLinkToSQLite) - 参考実装（C#）

## コントリビューション

コントリビューションを歓迎します！詳細は[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。

## サポート

- バグ報告・機能要望: [GitHub Issues](https://github.com/yourusername/jltsql/issues)
- 質問・ディスカッション: [GitHub Discussions](https://github.com/yourusername/jltsql/discussions)

## 作者

JLTSQL Contributors

## 変更履歴

詳細は[CHANGELOG.md](CHANGELOG.md)を参照してください。

---

**Note**: このプロジェクトはリリース候補版です（v1.0.0-rc1）。正式リリースに向けて最終調整中です。

## プロジェクトステータス

- ✅ Phase 1: プロジェクト基盤構築 (100%)
- ✅ Phase 2: JV-Link COM API統合 (100%)
- ✅ Phase 3: JV-Dataパーサー実装 (100%)
- ✅ Phase 4: データベース層実装 (100%)
- ✅ Phase 5: データ取得・インポート実装 (100%)
- ✅ Phase 6: リアルタイム監視実装 (100%)
- ✅ Phase 7: CLI実装 (100%)
- 🔵 Phase 8: ドキュメント・リリース準備 (進行中)

**全体進捗**: 87.5% (7/8フェーズ完了)
