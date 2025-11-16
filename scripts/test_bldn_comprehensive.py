#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BT (系統情報) 取得の包括的テスト

BLDNデータスペックで様々な条件を試してBTレコードを取得する。
パーサーが修正されたので、データが提供されれば正常に格納可能。
"""
import sys
import time
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.duckdb_handler import DuckDBDatabase
from src.database.schema import SCHEMAS
from src.parser.factory import ParserFactory
from src.jvlink.wrapper import JVLinkWrapper
from src.jvlink.constants import JV_READ_SUCCESS, JV_READ_NO_MORE_DATA

def wait_for_download(jvlink, max_wait_seconds=240):
    """ダウンロード完了を待機"""
    print('  ダウンロード待機中...', end='', flush=True)
    last_status = None

    for i in range(max_wait_seconds * 2):
        try:
            status = jvlink.jv_status()

            if status != last_status:
                last_status = status

            if status == 0:
                print(' OK 完了')
                time.sleep(1.0)
                return True
            elif status < 0:
                print(f' NG エラー (status: {status})')
                return False

            time.sleep(0.5)

        except Exception as e:
            print(f' NG 例外: {e}')
            return False

    print(f' NG タイムアウト ({max_wait_seconds}秒)')
    return False

def test_bldn_variants():
    """BLDNの様々な条件でBTレコード取得を試行"""

    print('=' * 80)
    print('BLDN データスペックでBT (系統情報) の包括的テスト')
    print('=' * 80)
    print()

    db = DuckDBDatabase({'path': './data/jltsql.duckdb'})
    db.connect()
    factory = ParserFactory()

    # テスト条件
    test_cases = [
        ('BLDN', '20000101000000', 1, 'option=1, 2000年から'),
        ('BLDN', '20100101000000', 1, 'option=1, 2010年から'),
        ('BLDN', '20150101000000', 1, 'option=1, 2015年から'),
        ('BLDN', '20200101000000', 1, 'option=1, 2020年から'),
        ('BLDN', '20230101000000', 1, 'option=1, 2023年から'),
        ('BLDN', '20000101000000', 2, 'option=2 (セットアップモード), 2000年から'),
        ('BLDN', '20000101000000', 3, 'option=3, 2000年から'),
        ('BLDN', '20000101000000', 4, 'option=4, 2000年から'),
    ]

    try:
        all_results = {}

        for data_spec, fromtime, option, description in test_cases:
            print(f'[{data_spec}] {description}...')

            try:
                jvlink = JVLinkWrapper(sid=f"TEST_{data_spec}_{option}")
                jvlink.jv_init()

                result, read_count, download_count, last_file_timestamp = jvlink.jv_open(
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option
                )

                if result < 0:
                    print(f'  NG 失敗 (code: {result})')
                    print()
                    continue

                print(f'  OK 接続成功 (予定: {read_count}件, DL: {download_count}件)')

                # ダウンロード待機
                if download_count > 0:
                    if not wait_for_download(jvlink, max_wait_seconds=240):
                        print(f'  !! ダウンロード未完了のためスキップ')
                        print()
                        continue
                else:
                    time.sleep(1.0)

                # データ読み込み
                stats = defaultdict(lambda: {'total': 0})
                record_count = 0
                max_records = 50000  # 十分な量を読む

                # 最初のレコードをデバッグ出力
                first_record = True

                while record_count < max_records:
                    ret_code, data, filename = jvlink.jv_read()

                    if ret_code == JV_READ_SUCCESS or ret_code == JV_READ_NO_MORE_DATA:
                        break
                    elif ret_code > 0:
                        if data:
                            try:
                                if first_record:
                                    print(f'  デバッグ: 先頭レコードID = "{data[:2].decode("shift-jis", errors="ignore")}", 長さ = {len(data)} バイト')
                                    first_record = False

                                parsed = factory.parse(data)
                                if parsed and 'RecordSpec' in parsed:
                                    record_type = parsed['RecordSpec']
                                    stats[record_type]['total'] += 1
                                    record_count += 1

                                    # BT レコードの詳細を表示
                                    if record_type == 'BT':
                                        print(f'  ★★★ BT レコード発見！ #{stats[record_type]["total"]}')
                                        print(f'      KeitoName: {parsed.get("KeitoName", "N/A")}')
                                        print(f'      MakeDate: {parsed.get("MakeDate", "N/A")}')
                            except Exception as e:
                                if record_count == 0:
                                    print(f'  !! パースエラー: {e}')
                    else:
                        break

                jvlink.jv_close()

                # 結果表示
                if stats:
                    print(f'  結果:')
                    for rt, counts in sorted(stats.items()):
                        print(f'    {rt}: {counts["total"]}件')

                    if 'BT' in stats:
                        print(f'  ✅✅✅ BT (系統情報) を {stats["BT"]["total"]}件 取得成功！')
                    else:
                        print(f'  ❌ BT レコードは取得できませんでした')
                        print(f'     取得できたレコード: {", ".join(sorted(stats.keys()))}')

                    all_results[description] = stats
                else:
                    print(f'  !! レコードが取得できませんでした')

                print()

            except Exception as e:
                print(f'  NG エラー: {e}')
                import traceback
                traceback.print_exc()
                print()

        # 最終サマリー
        print()
        print('=' * 80)
        print('最終結果サマリー')
        print('=' * 80)
        print()

        bt_found = False
        for description, stats in all_results.items():
            if 'BT' in stats:
                bt_found = True
                print(f'✅ {description}: BT {stats["BT"]["total"]}件')

        if not bt_found:
            print('❌ すべての条件で BT レコードは取得できませんでした')
            print()
            print('取得できたレコードタイプ:')
            all_record_types = set()
            for stats in all_results.values():
                all_record_types.update(stats.keys())
            for rt in sorted(all_record_types):
                print(f'  - {rt}')

        print()
        print('=' * 80)

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.disconnect()

if __name__ == '__main__':
    test_bldn_variants()
