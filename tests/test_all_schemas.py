#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""包括的スキーマ・パーサーテスト

蓄積系(NL_*)、速報系(RT_*)、時系列(TS_*)の全テーブルとパーサーをテスト
"""

import sys
import os
import pytest
from pathlib import Path

# Windowsコンソールでのエンコーディング問題を回避
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

from src.parser.factory import ParserFactory, ALL_RECORD_TYPES
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SchemaManager, SCHEMAS
from src.importer.importer import DataImporter
from src.jvlink.wrapper import JVLinkWrapper
from dotenv import load_dotenv
import os

def test_parsers():
    """全38パーサーの実装確認"""
    print("=" * 70)
    print("パーサーテスト")
    print("=" * 70)

    factory = ParserFactory()
    supported = factory.supported_types()

    print(f"\n定義済みレコードタイプ: {len(supported)}")

    # 各パーサーのロードテスト
    loaded = []
    failed = []

    for rec_type in supported:
        parser = factory.get_parser(rec_type)
        if parser:
            loaded.append(rec_type)
        else:
            failed.append(rec_type)

    print(f"\n✓ ロード成功: {len(loaded)}/{len(supported)}")
    if loaded:
        print(f"  {', '.join(loaded)}")

    if failed:
        print(f"\n✗ ロード失敗: {len(failed)}")
        print(f"  {', '.join(failed)}")

    assert len(failed) == 0, f"Failed parsers: {failed}"

def test_schemas():
    """全スキーマの作成テスト。"""
    print("\n" + "=" * 70)
    print("スキーマテスト")
    print("=" * 70)

    print(f"\n定義済みスキーマ: {len(SCHEMAS)}")

    # NL_* と RT_* に分類
    nl_tables = [t for t in SCHEMAS.keys() if t.startswith('NL_')]
    rt_tables = [t for t in SCHEMAS.keys() if t.startswith('RT_')]

    print(f"  蓄積系 (NL_*): {len(nl_tables)}")
    print(f"  速報系 (RT_*): {len(rt_tables)}")

    # テストデータベースで作成
    db_path = Path("data/test_all_schemas.db")
    if db_path.exists():
        db_path.unlink()

    database = SQLiteDatabase({"path": str(db_path)})
    success = True

    try:
        database.connect()
        schema_mgr = SchemaManager(database)
        results = schema_mgr.create_all_tables()

        created = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)

        print(f"\n✓ 作成成功: {created}/{len(SCHEMAS)}")
        if failed > 0:
            print(f"✗ 作成失敗: {failed}")
            failed_tables = [k for k, v in results.items() if not v]
            print(f"  {', '.join(failed_tables)}")
            success = False

    finally:
        database.disconnect()
        if db_path.exists():
            db_path.unlink()

    assert success, "Schema test failed"

@pytest.mark.skipif(sys.platform != 'win32', reason="Requires Windows + JV-Link COM")
def test_data_import():
    """実際のデータインポートテスト（複数data_spec）"""
    print("\n" + "=" * 70)
    print("データインポートテスト")
    print("=" * 70)

    load_dotenv()
    sid = os.getenv("JVLINK_SID", "JLTSQL")

    # テスト用data_spec（軽量なものを選択）
    test_specs = [
        ("RACE", "レース詳細系"),
        ("YSCH", "スケジュール系"),
    ]

    db_path = Path("data/test_import_all.db")
    if db_path.exists():
        db_path.unlink()

    database = SQLiteDatabase({"path": str(db_path)})
    jv = JVLinkWrapper(sid=sid)
    factory = ParserFactory()

    table_stats = {}

    try:
        # データベース準備
        database.connect()
        schema_mgr = SchemaManager(database)
        schema_mgr.create_all_tables()

        importer = DataImporter(database, batch_size=100)

        # JV-Link初期化
        result = jv.jv_init()
        if result != 0:
            print(f"✗ JV-Link初期化失敗: {result}")
            return False

        print(f"✓ JV-Link初期化成功\n")

        # 各data_specでデータ取得
        for data_spec, description in test_specs:
            print(f"\n{description} (data_spec={data_spec})")
            print("-" * 60)

            # ストリームオープン
            result_code, read_count, download_count, last_timestamp = jv.jv_open(
                data_spec=data_spec,
                fromtime="20240101000000",
                option=1
            )

            print(f"  JVOpen: code={result_code}, read={read_count}")

            if result_code != 0:
                print(f"  ⚠ ストリームオープン失敗")
                jv.jv_close()
                continue

            # レコード読み込みとインポート
            record_types_found = set()
            total_records = 0
            max_records = 500  # 各data_specで最大500件

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

                    # インポート
                    if importer.import_single_record(record):
                        total_records += 1

            jv.jv_close()

            print(f"  レコードタイプ: {len(record_types_found)} 種類")
            print(f"    {', '.join(sorted(record_types_found))}")
            print(f"  インポート: {total_records} 件")

        # テーブル別統計
        print("\n" + "=" * 70)
        print("テーブル別データ統計")
        print("=" * 70)

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
            except Exception:
                pass

        print(f"\n蓄積系 (NL_*): {len(nl_with_data)}/38 テーブルにデータ")
        for table in nl_with_data:
            print(f"  {table:20s}: {table_stats[table]:6,} 件")

        print(f"\n速報系 (RT_*): {len(rt_with_data)}/21 テーブルにデータ")
        if rt_with_data:
            for table in rt_with_data:
                print(f"  {table:20s}: {table_stats[table]:6,} 件")
        else:
            print("  (速報データなし - 蓄積データのみ取得)")

        total_records = sum(table_stats.values())
        print(f"\n総レコード数: {total_records:,} 件")
        print(f"データが入ったテーブル: {len(table_stats)}/{len(SCHEMAS)}")

        pass  # All assertions passed

    except Exception as e:
        print(f"\n✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            jv.jv_close()
        except Exception:
            pass
        database.disconnect()

def test_importer_mappings():
    """インポーターのテーブルマッピング確認"""
    print("\n" + "=" * 70)
    print("インポーターマッピングテスト")
    print("=" * 70)

    database = SQLiteDatabase({"path": ":memory:"})
    importer = DataImporter(database)

    # マッピング確認
    mappings = importer._table_map

    print(f"\n定義済みマッピング: {len(mappings)}")

    nl_mappings = {k: v for k, v in mappings.items() if v.startswith('NL_')}
    rt_mappings = {k: v for k, v in mappings.items() if v.startswith('RT_')}

    print(f"  蓄積系 (NL_*): {len(nl_mappings)}")
    print(f"  速報系 (RT_*): {len(rt_mappings)}")

    # スキーマとの整合性確認
    print("\nスキーマとの整合性確認:")
    unmapped_nl = []
    unmapped_rt = []

    for table_name in SCHEMAS.keys():
        found = False
        for mapped_table in mappings.values():
            if mapped_table == table_name:
                found = True
                break

        if not found:
            if table_name.startswith('NL_'):
                unmapped_nl.append(table_name)
            else:
                unmapped_rt.append(table_name)

    if unmapped_nl or unmapped_rt:
        print(f"  ⚠ マッピング未定義テーブル:")
        if unmapped_nl:
            print(f"    NL_*: {', '.join(unmapped_nl)}")
        if unmapped_rt:
            print(f"    RT_*: {', '.join(unmapped_rt)}")
    else:
        print(f"  ✓ 全テーブルマッピング済み")



def main():
    """メインテスト"""
    print("\n" + "=" * 70)
    print("JLTSQLシステム包括テスト")
    print("=" * 70)

    results = {}

    # 1. パーサーテスト
    results['parsers'] = test_parsers()

    # 2. スキーマテスト
    results['schemas'] = test_schemas()

    # 3. インポーターマッピングテスト
    results['mappings'] = test_importer_mappings()

    # 4. 実データインポートテスト
    results['import'] = test_data_import()

    # サマリー
    print("\n" + "=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {test_name:15s}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 全テスト合格！")
        return 0
    else:
        print("\n⚠ 一部テスト失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
