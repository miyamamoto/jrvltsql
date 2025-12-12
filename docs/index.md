# JRVLTSQL

JRA-VAN DataLabの競馬データをSQLite/PostgreSQL/DuckDBにインポートするツール

## 概要

JRVLTSQLは、JRA-VAN DataLabから提供される競馬データを効率的にデータベースに取り込むためのPythonツールです。

### 主な機能

- **マルチデータベース対応**: SQLite、PostgreSQL、DuckDBに対応
- **高速インポート**: バッチ処理による効率的なデータ取り込み
- **リアルタイム更新**: レース当日のオッズやレース結果をリアルタイムで取得
- **64テーブル対応**: JV-Data仕様に準拠した完全なスキーマ
- **CLIとAPI**: コマンドラインツールとPython APIの両方を提供

### データベース選択ガイド

| データベース | 用途 | 特徴 |
|-------------|------|------|
| **SQLite** | 軽量・開発 | ファイルベース、セットアップ不要 |
| **DuckDB** | 分析・OLAP | 高速な分析クエリ、列指向 |
| **PostgreSQL** | 本番運用 | マルチユーザー、高信頼性 |

## クイックスタート

### インストール

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

### 基本的な使い方

```bash
# quickstartで対話形式のセットアップ
python scripts/quickstart.py

# または個別コマンド
jltsql init                           # 初期化
jltsql create-tables                  # テーブル作成
jltsql fetch --from 20240101 --to 20241231 --spec RACE  # データ取得
```

## テーブル構成

JRVLTSQLは64テーブルを管理します：

- **NL_テーブル (38)**: 蓄積系データ（レース、馬、騎手など）
- **RT_テーブル (20)**: 速報系データ（リアルタイムオッズなど）
- **TS_テーブル (6)**: 時系列オッズデータ

詳細は[テーブル一覧](reference/tables.md)を参照してください。

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
