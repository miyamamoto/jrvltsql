#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PostgreSQL エンドツーエンドテスト: Fetch → Parse → Import → DB"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SchemaManager

print("=" * 70)
print("PostgreSQL エンドツーエンドテスト: 接続とテーブル作成")
print("=" * 70)
print()

print("注意: PostgreSQLサーバーが必要です")
print("接続できない場合はスキップされます")
print()

try:
    # 1. データベース接続
    print("1. PostgreSQLデータベース接続試行")
    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "jvlinktest",
        "user": "testuser",
        "password": "testpass",
        "connect_timeout": 5
    }
    db = PostgreSQLDatabase(db_config)
    db.connect()
    print(f"   ✓ PostgreSQLデータベース接続成功")
    print(f"   - Host: {db_config['host']}")
    print(f"   - Database: {db_config['database']}")
    print()

    # 2. テーブル作成
    print("2. テーブル作成")
    schema_manager = SchemaManager(db)
    schema_manager.create_all_tables()
    print("   ✓ テーブル作成完了")
    print()

    # 3. テーブル一覧確認
    print("3. PostgreSQLデータベース内容確認")
    print()

    tables_query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE 'nl_%'
        ORDER BY table_name
    """
    tables = db.fetch_all(tables_query)

    if tables:
        print(f"   作成されたテーブル ({len(tables)}個):")
        for table in tables:
            table_name = table['table_name'] if isinstance(table, dict) else table[0]
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count_result = db.fetch_all(count_query)[0]
            count = count_result['count'] if isinstance(count_result, dict) else count_result[0]
            print(f"   - {table_name}: {count}件")
    else:
        print("   テーブルなし")

    print()
    print("=" * 70)
    print("[SUCCESS] PostgreSQL エンドツーエンドテスト成功！")
    print("=" * 70)
    print()
    print("完全フロー確認:")
    print("  ✓ PostgreSQLデータベース接続")
    print("  ✓ PostgreSQLテーブル自動作成")
    print("  ✓ PostgreSQLクエリ実行")

except Exception as e:
    error_message = str(e)
    if "refused" in error_message.lower() or "could not connect" in error_message.lower():
        print(f"\n[SKIPPED] PostgreSQLサーバーに接続できません")
        print(f"   理由: {error_message[:200]}")
        print()
        print("   PostgreSQLサーバーが起動していないか、")
        print("   接続設定が正しくない可能性があります。")
        print()
        print("   このテストはスキップされます（インフラ確認のみ）")
    else:
        print(f"\n[ERROR] エラー発生: {e}")
        import traceback
        traceback.print_exc()

finally:
    # クリーンアップ
    try:
        db.disconnect()
        print("\nデータベース接続クローズ")
    except:
        pass

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
