# PostgreSQL クイックスタートガイド

JLTSQLをPostgreSQLで使用するための最短手順です。

## 5分で始める

### 1. PostgreSQLドライバーのインストール

```bash
pip install pg8000
```

### 2. PostgreSQLサーバーの起動 (Docker)

```bash
docker run -d \
  --name postgres-keiba \
  -e POSTGRES_DB=keiba \
  -e POSTGRES_USER=jltsql \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16-alpine
```

### 3. 接続テスト

```bash
python scripts/test_postgresql_connection.py
```

期待される出力:
```
✅ 全テスト成功
PostgreSQLは完全にサポートされています！
```

### 4. データベース初期化

```python
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SCHEMAS
from src.database.indexes import INDEXES

# 接続
config = {
    "host": "localhost",
    "database": "keiba",
    "user": "jltsql",
    "password": "password"
}

with PostgreSQLDatabase(config) as db:
    # テーブル作成 (38テーブル)
    for table_name, schema in SCHEMAS.items():
        if not db.table_exists(table_name):
            db.create_table(table_name, schema)

    # インデックス作成
    for index_name, index_sql in INDEXES.items():
        db.execute(index_sql)

    # 統計更新
    db.analyze()

print("初期化完了！")
```

### 5. JV-Linkデータを格納

JLTSQLの既存コードをそのまま使用可能:

```python
from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.database.postgresql_handler import PostgreSQLDatabase

# PostgreSQL設定に変更するだけ
db = PostgreSQLDatabase(config)
db.connect()

# 以降は通常通り
jvlink = JVLinkWrapper()
jvlink.jv_init()
# ... データ取得・パース・挿入

db.disconnect()
```

## DuckDBから移行する場合

```bash
python scripts/migrate_duckdb_to_postgresql.py
```

対話式で設定を入力すると、全データが自動的に移行されます。

## トラブルシューティング

### 接続できない

```bash
# PostgreSQLが起動しているか確認
docker ps | grep postgres

# ログを確認
docker logs postgres-keiba

# 再起動
docker restart postgres-keiba
```

### パフォーマンスが遅い

```python
with PostgreSQLDatabase(config) as db:
    # 統計を更新
    db.analyze()

    # 不要な領域を回収
    db.vacuum()
```

## 詳細ドキュメント

完全な情報は `POSTGRESQL_SUPPORT.md` を参照してください:
- ドライバー比較
- セキュリティ設定
- パフォーマンス最適化
- マイグレーション詳細
