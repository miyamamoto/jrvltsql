# データベースAPI

JRVLTSQLのデータベースハンドラーAPIリファレンスです。

## BaseDatabase

すべてのデータベースハンドラーの基底クラスです。

### 初期化

```python
from src.database.sqlite_handler import SQLiteDatabase
from src.database.duckdb_handler import DuckDBDatabase

# SQLite
db = SQLiteDatabase({
    "path": "data/keiba.db",
    "timeout": 30.0
})

# DuckDB
db = DuckDBDatabase({
    "path": "data/keiba.duckdb",
    "memory_limit": "2GB",
    "threads": 4
})
```

### 接続管理

#### connect()

データベースに接続します。

```python
db.connect()
```

#### disconnect()

データベース接続を閉じます。

```python
db.disconnect()
```

#### コンテキストマネージャー

`with`文で自動的に接続・切断を管理できます。

```python
with db:
    # 自動接続
    db.execute("SELECT * FROM NL_RA")
    # 正常終了時: 自動コミット
    # 例外発生時: 自動ロールバック
# 自動切断
```

### クエリ実行

#### execute(sql, parameters=None)

SQLを実行します。

```python
# パラメータなし
db.execute("CREATE TABLE test (id INTEGER)")

# パラメータあり
db.execute("INSERT INTO test VALUES (?)", (1,))

# 名前付きパラメータ
db.execute("INSERT INTO test VALUES (:id)", {"id": 1})
```

#### executemany(sql, parameters_list)

複数のパラメータセットでSQLを実行します。

```python
db.executemany(
    "INSERT INTO test VALUES (?)",
    [(1,), (2,), (3,)]
)
```

### データ取得

#### fetch_one(sql, parameters=None)

1行を辞書形式で取得します。

```python
row = db.fetch_one(
    "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
    (2024, 11)
)
print(row["Hondai"])  # レース名
```

#### fetch_all(sql, parameters=None)

全行を辞書のリストで取得します。

```python
rows = db.fetch_all(
    "SELECT * FROM NL_RA WHERE Year = ?",
    (2024,)
)
for row in rows:
    print(row["RaceNum"], row["Hondai"])
```

### データ挿入

#### insert(table_name, data, use_replace=True)

1行を挿入します。

```python
db.insert("NL_RA", {
    "Year": 2024,
    "MonthDay": 601,
    "JyoCD": "05",
    "Kaiji": 1,
    "Nichiji": 1,
    "RaceNum": 11,
    "Hondai": "テストレース"
})
```

| パラメータ | 型 | 説明 |
|-----------|------|------|
| table_name | str | テーブル名 |
| data | dict | 挿入データ |
| use_replace | bool | TrueでINSERT OR REPLACE |

#### insert_many(table_name, data_list, use_replace=True)

複数行をバッチ挿入します。

```python
db.insert_many("NL_SE", [
    {"Year": 2024, "MonthDay": 601, "Umaban": 1, ...},
    {"Year": 2024, "MonthDay": 601, "Umaban": 2, ...},
])
```

### トランザクション

#### commit()

トランザクションをコミットします。

```python
db.execute("INSERT INTO ...")
db.commit()
```

#### rollback()

トランザクションをロールバックします。

```python
try:
    db.execute("INSERT INTO ...")
    db.commit()
except Exception:
    db.rollback()
    raise
```

### ユーティリティ

#### table_exists(table_name)

テーブルの存在確認をします。

```python
if db.table_exists("NL_RA"):
    print("テーブルが存在します")
```

#### get_db_type()

データベースタイプを取得します。

```python
db_type = db.get_db_type()  # "sqlite", "duckdb", "postgresql"
```

#### is_connected()

接続状態を確認します。

```python
if db.is_connected():
    print("接続中")
```

## SQLiteDatabase

SQLite固有の機能です。

### PRAGMA設定

接続時に自動設定されるPRAGMA：

| PRAGMA | 値 | 説明 |
|--------|---|------|
| journal_mode | WAL | Write-Ahead Logging |
| synchronous | NORMAL | バランス型同期 |
| cache_size | -64000 | 64MBキャッシュ |
| temp_store | MEMORY | メモリ内一時テーブル |

### vacuum()

データベースを最適化します。

```python
db.vacuum()
```

### analyze()

統計情報を更新します。

```python
db.analyze()
```

## DuckDBDatabase

DuckDB固有の機能です。

### 設定オプション

```python
db = DuckDBDatabase({
    "path": "data/keiba.duckdb",
    "memory_limit": "4GB",    # メモリ制限
    "threads": 8,             # スレッド数
    "read_only": False        # 読み取り専用
})
```

### 分析クエリの最適化

DuckDBは列指向ストレージのため、以下のクエリが高速です：

```python
# 集計クエリ
rows = db.fetch_all("""
    SELECT Year, COUNT(*) as cnt
    FROM NL_RA
    GROUP BY Year
    ORDER BY Year
""")

# 大量データのスキャン
rows = db.fetch_all("""
    SELECT *
    FROM NL_SE
    WHERE Year = 2024
""")
```

## エラーハンドリング

### DatabaseError

すべてのデータベースエラーの基底例外です。

```python
from src.database.base import DatabaseError

try:
    db.execute("INVALID SQL")
except DatabaseError as e:
    print(f"データベースエラー: {e}")
```

### エラー処理パターン

```python
from src.database.base import DatabaseError

try:
    with db:
        db.execute("INSERT INTO ...")
        # 何か処理
        db.execute("UPDATE ...")
except DatabaseError as e:
    # ロールバックは自動
    logger.error(f"データベースエラー: {e}")
    raise
```

## 使用例

### 完全なワークフロー

```python
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import create_all_tables

# データベース初期化
db = SQLiteDatabase({"path": "data/keiba.db"})

with db:
    # テーブル作成
    create_all_tables(db)

    # データ挿入
    db.insert("NL_RA", {
        "Year": 2024,
        "MonthDay": 601,
        "JyoCD": "05",
        "Kaiji": 1,
        "Nichiji": 1,
        "RaceNum": 11
    })

    # データ取得
    race = db.fetch_one(
        "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
        (2024, 11)
    )
    print(race)

    # 集計
    stats = db.fetch_all("""
        SELECT Year, COUNT(*) as cnt
        FROM NL_RA
        GROUP BY Year
    """)
    for row in stats:
        print(f"{row['Year']}: {row['cnt']}件")
```

詳細なAPIドキュメントは[API.md](https://github.com/miyamamoto/jrvltsql/blob/master/docs/API.md)を参照してください。
