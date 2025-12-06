# JRVLTSQL

JRA-VAN DataLabの競馬データをSQLite/PostgreSQL/DuckDBにインポートするツール

## インストール

### 必要要件

- Windows 10/11
- Python 3.10+
- JRA-VAN DataLab会員

### セットアップ

```bash
pip install git+https://github.com/miyamamoto/jrvltsql.git
```

**quickstart.bat をダブルクリック** で対話形式のセットアップが始まります。

### DuckDB対応

分析向け高速データベース **DuckDB** を使用する場合:

```bash
pip install jltsql[duckdb]
```

## 使い方

### quickstartオプション

```bash
python scripts/quickstart.py              # 対話形式
python scripts/quickstart.py --years 5    # 過去5年分
python scripts/quickstart.py --no-odds    # オッズ除外
python scripts/quickstart.py -y           # 確認スキップ
```

### CLIコマンド

```bash
jltsql status           # ステータス確認
jltsql fetch --spec RA  # 個別データ取得
jltsql monitor          # リアルタイム監視
```

### データベース選択

```bash
jltsql fetch --db sqlite   # SQLite（デフォルト）
jltsql fetch --db duckdb   # DuckDB（分析向け高速）
jltsql fetch --db postgres # PostgreSQL
```

## データ構造

- **NL_テーブル**: 蓄積系データ（レース、馬、騎手など）
- **RT_テーブル**: 速報系データ（リアルタイムオッズなど）
- **TS_テーブル**: 時系列オッズ

## ライセンス

- 非商用利用: Apache License 2.0
- 商用利用: 事前にお問い合わせください → oracle.datascientist@gmail.com

取得データは[JRA-VAN利用規約](https://jra-van.jp/info/rule.html)に従ってください。
