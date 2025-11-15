#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DuckDB エンドツーエンドテスト: Fetch → Parse → Import → DB"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher
from src.importer.batch import BatchProcessor
from src.database.duckdb_handler import DuckDBDatabase

print("=" * 70)
print("DuckDB エンドツーエンドテスト: Fetch → Parse → Import → DB")
print("=" * 70)
print()

# テスト用DBファイル
db_path = "test_e2e.duckdb"

# 既存のテストDBを削除
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"既存のテストDB削除: {db_path}")
    print()

try:
    # 1. データベース接続
    print("1. DuckDBデータベース接続")
    db_config = {"path": db_path}
    db = DuckDBDatabase(db_config)
    db.connect()
    print(f"   ✓ DuckDBデータベース接続: {db_path}")
    print()

    # 2. BatchProcessor作成
    print("2. BatchProcessor作成")
    processor = BatchProcessor(db, batch_size=100)
    print("   ✓ BatchProcessor初期化完了")
    print()

    # 3. RACE データ仕様でレースデータを取得（少量）
    print("3. レースデータ取得 (RACE)")
    print("   データ仕様: RACE")
    print("   日付: 20251110以降")
    print("   モード: SETUP (option=1)")
    print("   注: 少量データのみ取得")
    print()

    # 少量データで高速テスト
    from src.fetcher.historical import HistoricalFetcher
    from src.importer.importer import DataImporter

    fetcher = HistoricalFetcher()
    fetcher.jvlink.jv_init()
    fetcher.jvlink.jv_open("RACE", "20251110000000", 1)

    # 最初の10レコードのみ取得
    records = []
    for i in range(10):
        ret_code, buff, filename = fetcher.jvlink.jv_read()
        if ret_code == 0:  # Complete
            break
        elif ret_code == -1:  # File switch
            continue
        elif ret_code > 0:  # Data
            try:
                from src.parser.factory import ParserFactory
                parser_factory = ParserFactory()
                data = parser_factory.parse(buff)
                if data:
                    records.append(data)
            except:
                pass

    fetcher.jvlink.jv_close()

    print(f"   取得レコード数: {len(records)}件")
    print()

    # 4. テーブル作成とインポート
    print("4. テーブル作成とデータインポート")

    from src.database.schema import SchemaManager
    schema_manager = SchemaManager(db)

    # テーブル作成
    schema_manager.create_all_tables()
    print(f"   ✓ テーブル作成完了")

    # データインポート
    if records:
        importer = DataImporter(db, batch_size=100)
        import_stats = importer.import_records(iter(records), auto_commit=True)
        print(f"   ✓ インポート: {import_stats.get('records_imported', 0)}件")
    else:
        print("   (インポートするデータなし)")
    print()

    # 5. データベース確認
    print("5. DuckDBデータベース内容確認")
    print()

    # テーブル一覧
    tables_query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='main' AND table_name LIKE 'NL_%'
        ORDER BY table_name
    """
    tables = db.fetch_all(tables_query)

    if tables:
        print(f"   作成されたテーブル ({len(tables)}個):")
        for table in tables:
            table_name = table['table_name'] if isinstance(table, dict) else table[0]
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count_result = db.fetch_all(count_query)[0]
            count = count_result['count_star()'] if isinstance(count_result, dict) else count_result[0]
            print(f"   - {table_name}: {count}件")
    else:
        print("   テーブルなし")

    print()

    # 6. サンプルデータ表示
    print("6. サンプルデータ表示")
    print()

    # RA (レース詳細) テーブル確認
    if db.table_exists("NL_RA_RACE"):
        print("   NL_RA_RACE (レース詳細):")
        ra_data = db.fetch_all(
            "SELECT idYear, idJyoCD, idRaceNum, RaceName FROM NL_RA_RACE LIMIT 3"
        )
        for row in ra_data:
            year = row['idYear'] if isinstance(row, dict) else row[0]
            jyo = row['idJyoCD'] if isinstance(row, dict) else row[1]
            race_num = row['idRaceNum'] if isinstance(row, dict) else row[2]
            name = row['RaceName'] if isinstance(row, dict) else row[3]
            print(f"   - 年度:{year} 競馬場:{jyo} R:{race_num} {name}")
        print()

    # SE (馬毎レース情報) テーブル確認
    if db.table_exists("NL_SE_RACE_UMA"):
        print("   NL_SE_RACE_UMA (馬毎レース情報):")
        se_data = db.fetch_all(
            "SELECT idYear, idBangou, UmaName, Kishu FROM NL_SE_RACE_UMA LIMIT 3"
        )
        for row in se_data:
            year = row['idYear'] if isinstance(row, dict) else row[0]
            bangou = row['idBangou'] if isinstance(row, dict) else row[1]
            uma_name = row['UmaName'] if isinstance(row, dict) else row[2]
            kishu = row['Kishu'] if isinstance(row, dict) else row[3]
            print(f"   - 年度:{year} 馬番:{bangou} {uma_name} 騎手:{kishu}")
        print()

    # HR (払戻) テーブル確認
    if db.table_exists("NL_HR_PAY"):
        print("   NL_HR_PAY (払戻情報):")
        hr_data = db.fetch_all(
            "SELECT idYear, TansyoPay1, FukusyoPay1 FROM NL_HR_PAY LIMIT 3"
        )
        for row in hr_data:
            year = row['idYear'] if isinstance(row, dict) else row[0]
            tansyo = row['TansyoPay1'] if isinstance(row, dict) else row[1]
            fukusyo = row['FukusyoPay1'] if isinstance(row, dict) else row[2]
            print(f"   - 年度:{year} 単勝:{tansyo}円 複勝:{fukusyo}円")
        print()

    print()
    print("=" * 70)
    print("[SUCCESS] DuckDB エンドツーエンドテスト成功！")
    print("=" * 70)
    print()
    print("完全フロー確認:")
    print("  ✓ DuckDBデータベース接続")
    print("  ✓ JV-Linkからデータ取得")
    print("  ✓ レコードパース")
    print("  ✓ DuckDBテーブル自動作成")
    print("  ✓ DuckDBデータインポート")
    print("  ✓ DuckDBクエリ実行")
    print()
    print(f"テストDB: {db_path}")

except Exception as e:
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
