#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""拡張データインポートテスト

より多くのdata_specで、多数のテーブルにデータが入ることを確認
"""

import sys
import os
from pathlib import Path

# Windowsコンソールでのエンコーディング問題を回避
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

from src.parser.factory import ParserFactory
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SchemaManager, SCHEMAS
from src.importer.importer import DataImporter
from src.jvlink.wrapper import JVLinkWrapper
from dotenv import load_dotenv
import os

def main():
    """拡張データインポートテスト"""
    print("=" * 70)
    print("拡張データインポートテスト")
    print("=" * 70)

    load_dotenv()
    sid = os.getenv("JVLINK_SID", "JLTSQL")

    # より多くのdata_specをテスト
    test_specs = [
        ("RACE", "レース詳細系", 1000),
        ("YSCH", "スケジュール系", 500),
        ("DIFF", "マスター差分系", 2000),
    ]

    db_path = Path("data/test_extended.db")
    if db_path.exists():
        db_path.unlink()

    database = SQLiteDatabase({"path": str(db_path)})
    jv = JVLinkWrapper(sid=sid)
    factory = ParserFactory()

    try:
        # データベース準備
        database.connect()
        schema_mgr = SchemaManager(database)
        schema_mgr.create_all_tables()
        print("✓ 全57テーブル作成完了\n")

        importer = DataImporter(database, batch_size=100)

        # JV-Link初期化
        result = jv.jv_init()
        if result != 0:
            print(f"✗ JV-Link初期化失敗: {result}")
            return False

        print("✓ JV-Link初期化成功\n")

        # 各data_specでデータ取得
        all_record_types = set()
        total_imported = 0

        for data_spec, description, max_records in test_specs:
            print(f"{description} (data_spec={data_spec})")
            print("-" * 60)

            # ストリームオープン
            result_code, read_count, download_count, last_timestamp = jv.jv_open(
                data_spec=data_spec,
                fromtime="20240101000000",
                option=1
            )

            print(f"  JVOpen: code={result_code}, read={read_count}")

            if result_code != 0:
                print(f"  ⚠ ストリームオープン失敗\n")
                jv.jv_close()
                continue

            # レコード読み込みとインポート
            record_types_found = set()
            imported = 0

            for i in range(max_records):
                result_code, data_bytes, filename = jv.jv_read()

                if result_code <= 0:
                    break

                # パース
                record = factory.parse(data_bytes)
                if record:
                    rec_type = record.get('レコード種別ID') or record.get('headRecordSpec')
                    if rec_type:
                        record_types_found.add(rec_type)
                        all_record_types.add(rec_type)

                    # インポート
                    if importer.import_single_record(record):
                        imported += 1

            jv.jv_close()

            print(f"  レコードタイプ: {len(record_types_found)} 種類")
            print(f"    {', '.join(sorted(record_types_found))}")
            print(f"  インポート: {imported:,} 件\n")
            total_imported += imported

        # テーブル別統計
        print("=" * 70)
        print("テーブル別データ統計")
        print("=" * 70)

        table_stats = {}
        nl_with_data = []
        rt_with_data = []

        for table_name in sorted(SCHEMAS.keys()):
            try:
                rows = database.fetch_all(f"SELECT COUNT(*) as cnt FROM {table_name}")
                count = rows[0]['cnt'] if rows else 0

                if count > 0:
                    table_stats[table_name] = count
                    if table_name.startswith('NL_'):
                        nl_with_data.append(table_name)
                    else:
                        rt_with_data.append(table_name)
            except:
                pass

        print(f"\n蓄積系 (NL_*): {len(nl_with_data)}/38 テーブルにデータ")
        for table in nl_with_data:
            print(f"  {table:20s}: {table_stats[table]:8,} 件")

        print(f"\n速報系 (RT_*): {len(rt_with_data)}/19 テーブルにデータ")
        if rt_with_data:
            for table in rt_with_data:
                print(f"  {table:20s}: {table_stats[table]:8,} 件")
        else:
            print("  (速報データなし - 蓄積データのみ取得)")

        print("\n" + "=" * 70)
        print(f"検出されたレコードタイプ: {len(all_record_types)}/38")
        print(f"  {', '.join(sorted(all_record_types))}")
        print(f"\n総インポート数: {total_imported:,} 件")
        print(f"データが入ったテーブル: {len(table_stats)}/57")

        # パーサーカバレッジ確認
        print("\n" + "=" * 70)
        print("パーサーカバレッジ")
        print("=" * 70)

        from src.parser.factory import ALL_RECORD_TYPES
        tested_types = all_record_types
        untested_types = set(ALL_RECORD_TYPES) - tested_types

        print(f"テスト済み: {len(tested_types)}/38 ({len(tested_types)*100//38}%)")
        if untested_types:
            print(f"未テスト: {len(untested_types)}")
            print(f"  {', '.join(sorted(untested_types))}")

        return True

    except Exception as e:
        print(f"\n✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            jv.jv_close()
        except:
            pass
        database.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
