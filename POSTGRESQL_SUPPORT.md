# PostgreSQL対応調査レポート

日付: 2025-11-17
作業者: Claude Code

## 結論

✅ **PostgreSQLへの格納は完全に対応済み**

JLTSQLは既にPostgreSQLをフルサポートしており、本番環境での利用が可能です。

---

## 実装状況

### 完全実装されている機能

#### 1. PostgreSQLDatabase クラス (`src/database/postgresql_handler.py`)

**対応ドライバー (自動選択)**:
- `pg8000` (純Python実装、Win32完全対応、推奨)
- `psycopg` (C拡張、高性能、libpq必要)

**実装済みメソッド**:
- ✅ `connect()` - 接続確立
- ✅ `disconnect()` - 接続終了
- ✅ `execute()` - SQL実行
- ✅ `executemany()` - バッチ実行
- ✅ `fetch_one()` - 単一行取得
- ✅ `fetch_all()` - 全行取得
- ✅ `create_table()` - テーブル作成
- ✅ `table_exists()` - テーブル存在確認
- ✅ `get_table_columns()` - カラム情報取得
- ✅ `analyze()` - 統計更新
- ✅ `vacuum()` - 領域回収
- ✅ `commit()` - トランザクションコミット
- ✅ `rollback()` - トランザクションロールバック

#### 2. BaseDatabase抽象クラス (`src/database/base.py`)

統一インターフェース:
- `insert()` - 単一行挿入
- `insert_many()` - 複数行バッチ挿入
- コンテキストマネージャー (`with` 文対応)

#### 3. ドライバー互換性レイヤー

**プレースホルダー自動変換**:
- DuckDB/SQLite形式 `?` → PostgreSQL形式 (`%s` or `:param1`)
- pg8000: `?` → `:param1, :param2, ...` (named parameters)
- psycopg: `?` → `%s` (positional parameters)

**識別子の正規化**:
- PostgreSQLは識別子を小文字化 (`_quote_identifier()`)
- DuckDBとの互換性を維持

---

## セットアップ手順

### 1. PostgreSQLドライバーのインストール

#### Windows環境 (推奨: pg8000)

```bash
pip install pg8000
```

**利点**:
- 純Python実装 (libpq不要)
- Win32/Win64完全対応
- インストールが簡単

#### Linux/Unix環境 (推奨: psycopg)

```bash
pip install psycopg
```

**利点**:
- C拡張による高性能
- PostgreSQL公式推奨

### 2. PostgreSQLサーバーのセットアップ

#### Dockerを使用する場合 (推奨)

```bash
# PostgreSQL 16コンテナを起動
docker run -d \
  --name postgres-keiba \
  -e POSTGRES_DB=keiba \
  -e POSTGRES_USER=jltsql \
  -e POSTGRES_PASSWORD=your_password_here \
  -p 5432:5432 \
  postgres:16-alpine

# データベース作成を確認
docker exec -it postgres-keiba psql -U jltsql -d keiba -c '\dt'
```

#### ローカルインストール

**Windows**:
1. [PostgreSQL公式サイト](https://www.postgresql.org/download/windows/)からインストーラーをダウンロード
2. インストール時に以下を設定:
   - データベース名: `keiba`
   - ユーザー名: `jltsql`
   - パスワード: 任意
   - ポート: `5432` (デフォルト)

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb keiba
sudo -u postgres createuser jltsql
```

### 3. 設定ファイルの作成

`config/postgresql.yaml`:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: keiba
  user: jltsql
  password: your_password_here
  sslmode: prefer
  connect_timeout: 10
```

---

## 使用方法

### 基本的な使い方

```python
from src.database.postgresql_handler import PostgreSQLDatabase

# 設定
config = {
    "host": "localhost",
    "port": 5432,
    "database": "keiba",
    "user": "jltsql",
    "password": "your_password_here"
}

# 接続
db = PostgreSQLDatabase(config)
db.connect()

# テーブル作成 (既存スキーマを使用)
from src.database.schema import SCHEMAS
for table_name, schema_sql in SCHEMAS.items():
    if not db.table_exists(table_name):
        db.create_table(table_name, schema_sql)

# データ挿入
data = {
    "RecordSpec": "RA",
    "DataKubun": "1",
    "MakeDate": "20241117"
    # ... その他のフィールド
}
db.insert("NL_RA", data)

# クエリ実行
result = db.fetch_one("SELECT COUNT(*) as count FROM NL_RA")
print(f"NL_RAテーブル: {result['count']}件")

# 切断
db.disconnect()
```

### コンテキストマネージャーを使用

```python
from src.database.postgresql_handler import PostgreSQLDatabase

config = {
    "host": "localhost",
    "database": "keiba",
    "user": "jltsql",
    "password": "your_password"
}

with PostgreSQLDatabase(config) as db:
    # トランザクション内で実行
    db.insert("NL_RA", data)
    # with終了時に自動コミット (エラー時は自動ロールバック)
```

---

## DuckDB vs PostgreSQL 比較

| 特徴 | DuckDB | PostgreSQL |
|------|--------|-----------|
| **タイプ** | OLAP (分析用) | OLTP + OLAP (汎用) |
| **ファイル形式** | ローカルファイル (`.duckdb`) | クライアント/サーバー |
| **同時接続** | 限定的 | 高い並行性 |
| **データサイズ** | 〜100GB | 数TB以上 |
| **クエリ速度 (分析)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **トランザクション** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **複数ユーザー** | ❌ | ✅ |
| **バックアップ** | ファイルコピー | pg_dump, WAL |
| **レプリケーション** | ❌ | ✅ (ストリーミング、論理) |
| **運用コスト** | 低 | 中〜高 |
| **セットアップ** | 簡単 | 中程度 |

### 推奨用途

#### DuckDB を選択すべき場合
- ✅ 個人利用・開発環境
- ✅ 単一ユーザーの分析作業
- ✅ データサイズが100GB未満
- ✅ セットアップを簡単にしたい
- ✅ ファイルベースのポータビリティが必要

#### PostgreSQL を選択すべき場合
- ✅ 本番環境・チーム開発
- ✅ 複数ユーザーの同時アクセス
- ✅ データサイズが100GB以上
- ✅ トランザクション整合性が重要
- ✅ レプリケーション・バックアップが必要
- ✅ 既存のPostgreSQL環境がある

---

## 既存スキーマの互換性

### ✅ 完全互換

JLTSQLの全38テーブルのスキーマはPostgreSQLと完全互換:

```python
# src/database/schema.py の全スキーマがそのまま使用可能
from src.database.schema import SCHEMAS

# PostgreSQLで全テーブルを作成
with PostgreSQLDatabase(config) as db:
    for table_name, schema_sql in SCHEMAS.items():
        if not db.table_exists(table_name):
            db.create_table(table_name, schema_sql)
            print(f"Created: {table_name}")
```

### データ型マッピング

| JLTSQLスキーマ | DuckDB | PostgreSQL |
|---------------|--------|-----------|
| `TEXT` | VARCHAR | TEXT |
| `INTEGER` | INTEGER | INTEGER |
| `REAL` | DOUBLE | REAL |
| `BLOB` | BLOB | BYTEA |

すべてのデータ型が自動的に適切にマッピングされます。

---

## パフォーマンス最適化

### インデックス作成

```python
# 既存のインデックス定義を使用
from src.database.indexes import INDEXES

with PostgreSQLDatabase(config) as db:
    for index_name, index_sql in INDEXES.items():
        db.execute(index_sql)
        print(f"Created index: {index_name}")
```

### 統計更新

```python
with PostgreSQLDatabase(config) as db:
    # 全テーブルの統計を更新
    db.analyze()

    # 特定テーブルのみ
    db.analyze("NL_RA")
```

### VACUUM実行

```python
with PostgreSQLDatabase(config) as db:
    # 全テーブルのVACUUM
    db.vacuum()

    # 特定テーブルのみ
    db.vacuum("NL_RA")
```

---

## マイグレーション

### DuckDB → PostgreSQL

```python
from src.database.duckdb_handler import DuckDBDatabase
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SCHEMAS

# DuckDB接続
duckdb_config = {"path": "./data/keiba.duckdb"}
duckdb = DuckDBDatabase(duckdb_config)
duckdb.connect()

# PostgreSQL接続
pg_config = {
    "host": "localhost",
    "database": "keiba",
    "user": "jltsql",
    "password": "your_password"
}
pg = PostgreSQLDatabase(pg_config)
pg.connect()

# テーブルごとにマイグレーション
for table_name in SCHEMAS.keys():
    print(f"Migrating {table_name}...")

    # PostgreSQLにテーブル作成
    if not pg.table_exists(table_name):
        pg.create_table(table_name, SCHEMAS[table_name])

    # DuckDBからデータを読み込み
    rows = duckdb.fetch_all(f"SELECT * FROM {table_name}")

    if rows:
        # PostgreSQLにバッチ挿入
        pg.insert_many(table_name, rows)
        print(f"  Migrated {len(rows)} rows")
    else:
        print(f"  No data to migrate")

duckdb.disconnect()
pg.disconnect()
print("Migration completed!")
```

### PostgreSQL → Parquet → DuckDB

```python
# PostgreSQLからエクスポート
with PostgreSQLDatabase(pg_config) as pg:
    pg.execute("COPY NL_RA TO '/tmp/nl_ra.csv' CSV HEADER")

# DuckDBでインポート
with DuckDBDatabase(duckdb_config) as duck:
    duck.execute("COPY NL_RA FROM '/tmp/nl_ra.csv' CSV HEADER")
```

---

## テスト

テストスクリプトを実行してPostgreSQL接続を検証:

```bash
python scripts/test_postgresql_connection.py
```

期待される出力:
```
[INFO] Testing PostgreSQL connection...
[INFO] Connected to PostgreSQL database: localhost:5432/keiba
[INFO] Creating test table...
[INFO] Created table: test_table
[INFO] Inserting test data...
[INFO] Inserted 3 rows
[INFO] Querying test data...
[INFO] Retrieved 3 rows
[INFO] Cleaning up...
[INFO] Test completed successfully!
```

---

## トラブルシューティング

### 接続エラー

**問題**: `Failed to connect to PostgreSQL database`

**解決策**:
1. PostgreSQLサーバーが起動しているか確認
   ```bash
   # Windows
   sc query postgresql-x64-16

   # Linux
   sudo systemctl status postgresql

   # Docker
   docker ps | grep postgres
   ```

2. 接続情報を確認
   ```bash
   psql -h localhost -U jltsql -d keiba
   ```

3. ファイアウォール設定を確認 (ポート5432が開いているか)

### ドライバーエラー

**問題**: `No PostgreSQL driver available`

**解決策**:
```bash
# pg8000をインストール
pip install pg8000

# または psycopg
pip install psycopg
```

### SSL接続エラー

**問題**: `SSL connection error`

**解決策**:
設定でSSLモードを調整:
```python
config = {
    # ...
    "sslmode": "disable"  # または "require", "verify-full"
}
```

---

## セキュリティ

### パスワード管理

**環境変数を使用 (推奨)**:

```python
import os

config = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "database": os.environ.get("POSTGRES_DB", "keiba"),
    "user": os.environ.get("POSTGRES_USER", "jltsql"),
    "password": os.environ["POSTGRES_PASSWORD"],  # 必須
}
```

**.envファイル** (`.gitignore`に追加):
```
POSTGRES_HOST=localhost
POSTGRES_DB=keiba
POSTGRES_USER=jltsql
POSTGRES_PASSWORD=your_secret_password
```

### 接続制限

`pg_hba.conf`で接続元を制限:
```
# ローカルホストからのみ接続許可
host    keiba           jltsql          127.0.0.1/32            scram-sha-256
```

---

## 結論

### ✅ 完全対応

JLTSQLは**PostgreSQLに完全対応**しており、以下が可能:

1. **既存スキーマの完全互換性**: 全38テーブルがそのまま使用可能
2. **ドライバー自動選択**: pg8000/psycopgを自動判別
3. **統一API**: DuckDBと同じコードでPostgreSQLも操作可能
4. **本番環境対応**: トランザクション、VACUUM、ANALYZEなど完備
5. **マイグレーションツール**: DuckDB ⟷ PostgreSQL 相互変換可能

### 推奨アーキテクチャ

**開発環境**: DuckDB (簡単、高速)
**本番環境**: PostgreSQL (高性能、高可用性)
**データ交換**: Parquet形式

---

## 参照

- `src/database/postgresql_handler.py`: PostgreSQL実装
- `src/database/base.py`: 共通インターフェース
- `src/database/schema.py`: テーブルスキーマ定義
- `src/database/indexes.py`: インデックス定義
