#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DuckDB → PostgreSQL マイグレーションスクリプト

既存のDuckDBデータベースをPostgreSQLに移行します。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.duckdb_handler import DuckDBDatabase
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SCHEMAS
from src.database.indexes import INDEXES

def main():
    print("=" * 80)
    print("DuckDB → PostgreSQL マイグレーション")
    print("=" * 80)

    # DuckDB設定
    duckdb_config = {"path": project_root / "data" / "keiba.duckdb"}

    # PostgreSQL設定
    pg_config = {
        "host": "localhost",
        "port": 5432,
        "database": "keiba",
        "user": "jltsql",
        "password": input("PostgreSQLパスワードを入力: "),
    }

    print("\n接続情報:")
    print(f"  DuckDB: {duckdb_config['path']}")
    print(f"  PostgreSQL: {pg_config['host']}:{pg_config['port']}/{pg_config['database']}")

    # 確認
    response = input("\nマイグレーションを開始しますか? (yes/no): ")
    if response.lower() != "yes":
        print("キャンセルしました")
        return 0

    duckdb = None
    pg = None

    try:
        # DuckDB接続
        print("\n[1/5] DuckDB接続中...")
        duckdb = DuckDBDatabase(duckdb_config)
        duckdb.connect()
        print("  ✅ DuckDB接続完了")

        # PostgreSQL接続
        print("\n[2/5] PostgreSQL接続中...")
        pg = PostgreSQLDatabase(pg_config)
        pg.connect()
        print("  ✅ PostgreSQL接続完了")

        # テーブル作成
        print("\n[3/5] テーブル作成中...")
        for table_name, schema_sql in SCHEMAS.items():
            if not pg.table_exists(table_name):
                pg.create_table(table_name, schema_sql)
                print(f"  ✅ {table_name} 作成")
            else:
                print(f"  ⏭  {table_name} 既存")

        # データマイグレーション
        print("\n[4/5] データマイグレーション中...")
        total_migrated = 0
        tables_with_data = 0

        for table_name in SCHEMAS.keys():
            try:
                # DuckDBからデータ取得
                rows = duckdb.fetch_all(f"SELECT * FROM {table_name}")

                if rows:
                    # PostgreSQLに挿入
                    pg.insert_many(table_name, rows)
                    pg.commit()
                    total_migrated += len(rows)
                    tables_with_data += 1
                    print(f"  ✅ {table_name}: {len(rows):,}件マイグレーション")
                else:
                    print(f"  ⏭  {table_name}: データなし")

            except Exception as e:
                print(f"  ❌ {table_name}: エラー - {e}")
                pg.rollback()

        # インデックス作成
        print("\n[5/5] インデックス作成中...")
        for index_name, index_sql in INDEXES.items():
            try:
                pg.execute(index_sql)
                print(f"  ✅ {index_name}")
            except Exception as e:
                print(f"  ⚠️  {index_name}: {e}")

        # 統計更新
        print("\n統計更新中...")
        pg.analyze()
        print("  ✅ ANALYZE完了")

        # サマリー
        print("\n" + "=" * 80)
        print("マイグレーション完了")
        print("=" * 80)
        print(f"総テーブル数: {len(SCHEMAS)}")
        print(f"データ移行: {tables_with_data}テーブル")
        print(f"総レコード数: {total_migrated:,}件")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n❌ マイグレーションエラー: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if duckdb:
            duckdb.disconnect()
        if pg:
            pg.disconnect()


if __name__ == "__main__":
    sys.exit(main())
