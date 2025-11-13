# JLTSQL - JRA-VAN Link To SQL

JRA-VAN DataLabの競馬データをSQLite/DuckDB/PostgreSQLにリアルタイムインポートするPythonツール

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

## 概要

JLTSQLは、JRA-VAN DataLabが提供する競馬データ（JV-Data）を、SQLite、DuckDB、PostgreSQLなどの一般的なデータベースにインポートするためのツールです。リアルタイムでのオッズ更新や馬体重情報の取得にも対応しています。

### 主な機能

- **複数データベース対応**: SQLite、DuckDB、PostgreSQL
- **過去データ一括取得**: 1986年以降の全競馬データ
- **リアルタイム更新**: オッズ、馬体重、レース結果の即時取得
- **豊富なデータ**: レース情報、馬情報、騎手情報、血統情報、オッズなど
- **高速インポート**: バッチ処理による効率的なデータ挿入
- **使いやすいCLI**: シンプルなコマンドラインインターフェース

## 動作環境

- **OS**: Windows 10/11 (JV-Link COM APIはWindows専用)
- **Python**: 3.9以上
- **必須**: JRA-VAN DataLab会員登録（月額2,090円）

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

### 1. データベースの初期化

```bash
python -m src.cli.main init
```

### 2. 過去データの取得

```bash
# 2024年のレースデータを取得
python -m src.cli.main fetch --from 2024-01-01 --to 2024-12-31 --data-spec RACE
```

### 3. リアルタイム監視の開始

```bash
# バックグラウンドでリアルタイムデータ取得開始
python -m src.cli.main monitor --daemon
```

### 4. ステータスの確認

```bash
python -m src.cli.main status
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

JLTSQLは、JV-Dataの構造を忠実に再現したテーブル構造を使用します。

主なテーブル:
- **NL_RA_RACE**: レース詳細情報
- **NL_SE_RACE_UMA**: 馬別レース情報
- **NL_UM_UMA**: 競走馬マスタ
- **NL_KS_KISYU**: 騎手マスタ
- **NL_HR_PAY**: 払戻情報
- **NL_O1～O6**: オッズ情報（単勝、馬連、3連単など）

詳細は[データベーススキーマドキュメント](docs/database_schema.md)を参照してください。

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

```bash
# 初期化
jltsql init [--config CONFIG]

# データ取得
jltsql fetch --from DATE --to DATE --data-spec SPEC [--db DB]

# リアルタイム監視
jltsql monitor [--daemon] [--interval SECONDS]

# ステータス確認
jltsql status

# 監視停止
jltsql stop

# テーブル作成
jltsql create-tables --db DB

# データエクスポート
jltsql export --format FORMAT --output PATH
```

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

**Note**: このプロジェクトは開発中です（v0.1.0-alpha）。APIやデータ構造は予告なく変更される可能性があります。
