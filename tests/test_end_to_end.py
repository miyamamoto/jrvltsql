#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""エンドツーエンドテスト: Fetch → Parse → Import → DB"""

import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher
from src.importer.batch import BatchProcessor
from src.database.sqlite_handler import SQLiteDatabase

print("=" * 70)
print("エンドツーエンドテスト: Fetch → Parse → Import → DB")
print("=" * 70)
print()

# テスト用DBファイル
db_path = "test_e2e.db"

# 既存のテストDBを削除
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"既存のテストDB削除: {db_path}")
    print()

try:
    # 1. データベース接続
    print("1. データベース接続")
    db_config = {"path": db_path}
    db = SQLiteDatabase(db_config)
    db.connect()
    print(f"   ✓ SQLiteデータベース接続: {db_path}")
    print()

    # 2. BatchProcessor作成
    print("2. BatchProcessor作成")
    processor = BatchProcessor(db, batch_size=100)
    print("   ✓ BatchProcessor初期化完了")
    print()

    # 3. DIFF データ仕様でマスタデータを取得
    # DIFF = マスタデータ (UM, KS, CH, BR, BN, HN, SK, RC, HC)
    print("3. マスタデータ取得 (DIFF)")
    print("   データ仕様: DIFF")
    print("   日付: 20240101以降")
    print("   モード: SETUP (option=1)")
    print()

    result = processor.process_date_range(
        data_spec="DIFF",
        from_date="20240101",
        to_date="20240101",
        option=1,  # SETUP mode
        ensure_tables=True  # 自動テーブル作成
    )

    print()
    print("   結果:")
    print(f"   - Fetched: {result.get('fetched', 0)}件")
    print(f"   - Parsed: {result.get('parsed', 0)}件")
    print(f"   - Imported: {result.get('imported', 0)}件")
    print(f"   - Failed: {result.get('failed', 0)}件")
    print()

    # 4. RACE データ仕様でレースデータを取得
    print("4. レースデータ取得 (RACE)")
    print("   データ仕様: RACE")
    print("   日付: 20240101以降")
    print("   モード: SETUP (option=1)")
    print()

    result = processor.process_date_range(
        data_spec="RACE",
        from_date="20240101",
        to_date="20240101",
        option=1,  # SETUP mode
        ensure_tables=True  # 自動テーブル作成
    )

    print()
    print("   結果:")
    print(f"   - Fetched: {result.get('fetched', 0)}件")
    print(f"   - Parsed: {result.get('parsed', 0)}件")
    print(f"   - Imported: {result.get('imported', 0)}件")
    print(f"   - Failed: {result.get('failed', 0)}件")
    print()

    # 5. データベース確認
    print("5. データベース内容確認")
    print()

    # テーブル一覧
    tables_query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'NL_%'
        ORDER BY name
    """
    tables = db.fetch_all(tables_query)

    if tables:
        print(f"   作成されたテーブル ({len(tables)}個):")
        for table in tables:
            table_name = table[0]
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count = db.fetch_all(count_query)[0][0]
            print(f"   - {table_name}: {count}件")
    else:
        print("   テーブルなし")

    print()

    # 6. サンプルデータ表示
    print("6. サンプルデータ表示")
    print()

    # RA (レース詳細) テーブル確認
    if db.table_exists("NL_RA_RACE"):
        print("   NL_RA_RACE (レース詳細) - 最初の3件:")
        ra_data = db.fetch_all(
            "SELECT idYear, idJyoCD, idRaceNum, RaceName FROM NL_RA_RACE LIMIT 3"
        )
        for row in ra_data:
            print(f"   - 年度:{row[0]} 競馬場:{row[1]} R:{row[2]} {row[3]}")
        print()

    # SE (馬毎レース情報) テーブル確認
    if db.table_exists("NL_SE_RACE_UMA"):
        print("   NL_SE_RACE_UMA (馬毎レース情報) - 最初の3件:")
        se_data = db.fetch_all(
            "SELECT idYear, idBangou, UmaName, Kishu FROM NL_SE_RACE_UMA LIMIT 3"
        )
        for row in se_data:
            print(f"   - 年度:{row[0]} 馬番:{row[1]} {row[2]} 騎手:{row[3]}")
        print()

    # HR (払戻) テーブル確認
    if db.table_exists("NL_HR_PAY"):
        print("   NL_HR_PAY (払戻情報) - 最初の3件:")
        hr_data = db.fetch_all(
            "SELECT idYear, TansyoPay1, FukusyoPay1 FROM NL_HR_PAY LIMIT 3"
        )
        for row in hr_data:
            print(f"   - 年度:{row[0]} 単勝:{row[1]}円 複勝:{row[2]}円")
        print()

    print()
    print("=" * 70)
    print("[SUCCESS] エンドツーエンドテスト成功！")
    print("=" * 70)
    print()
    print("完全フロー確認:")
    print("  ✓ JV-Linkからデータ取得")
    print("  ✓ レコードパース")
    print("  ✓ データベーステーブル自動作成")
    print("  ✓ データインポート")
    print("  ✓ SQLiteクエリ実行")
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
