#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
残り9個の空テーブルについて包括的調査
- 各レコードタイプがどのデータスペックで取得できるか
- 過去の成功実装を参照
- 実際にJV-Linkで取得を試行
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.database.duckdb_handler import DuckDBDatabase
from collections import defaultdict
import time

def main():
    print("=" * 80)
    print("残り9個の空テーブルの包括的調査と取得")
    print("=" * 80)

    # 空テーブルのリスト
    empty_tables = {
        'NL_AV': '市場取引（セリ）',
        'NL_BT': '繁殖牝馬',
        'NL_CC': '距離変更',
        'NL_CS': '馬主名義変更',
        'NL_HS': '異常配当',
        'NL_JC': '騎手変更',
        'NL_TC': '発走時刻変更',
        'NL_WE': '天候変更',
        'NL_WH': '天候・馬場状態変更',
    }

    # レコードタイプとデータスペックのマッピング
    record_to_spec = {
        'AV': ['HOSN', 'HOYU'],  # 市場取引（セリ）
        'BT': ['BLDN'],          # 繁殖牝馬
        'CC': ['SNAP', 'MING'],  # 距離変更（速報）
        'CS': ['DIFN'],          # 馬主名義変更
        'HS': ['SNAP', 'MING'],  # 異常配当（速報）
        'JC': ['SNAP', 'MING'],  # 騎手変更（速報）
        'TC': ['SNAP', 'MING'],  # 発走時刻変更（速報）
        'WE': ['SNAP', 'MING'],  # 天候変更（速報）
        'WH': ['SNAP', 'MING'],  # 天候・馬場状態変更（速報）
    }

    # 各データスペックの推奨設定
    spec_configs = {
        # 速報系: より最近のデータ、option=2
        'SNAP': [
            ('20241110000000', 2),  # 最近の速報
            ('20241101000000', 2),  # 11月全体
            ('20241001000000', 2),  # 10月全体
        ],
        'MING': [
            ('20241110000000', 2),
            ('20241101000000', 2),
            ('20241001000000', 2),
        ],
        # 市場取引: 長期間、option=2
        'HOSN': [
            ('20240101000000', 2),  # 2024年全体
            ('20230101000000', 2),  # 2023年全体
        ],
        'HOYU': [
            ('20240101000000', 2),
            ('20230101000000', 2),
        ],
        # 血統・マスタ: 長期間、option=1
        'BLDN': [
            ('20240101000000', 1),  # 2024年
            ('20230101000000', 1),  # 2023年
            ('20220101000000', 1),  # 2022年
        ],
        'DIFN': [
            ('20240101000000', 1),
            ('20230101000000', 1),
        ],
    }

    jvlink = None
    db = None
    factory = ParserFactory()

    try:
        print("\n[1/4] JV-Link初期化")
        print("-" * 80)
        jvlink = JVLinkWrapper()
        jvlink.jv_init()
        print("  OK JV-Link初期化完了")

        print("\n[2/4] データベース接続")
        print("-" * 80)
        db_config = {"path": project_root / "data" / "keiba.duckdb"}
        db = DuckDBDatabase(db_config)
        db.connect()
        print("  OK データベース接続完了")

        print("\n[3/4] 各データスペックで取得試行")
        print("-" * 80)

        results = defaultdict(list)

        # 空テーブルごとに処理
        for table_name, table_desc in empty_tables.items():
            record_type = table_name.replace('NL_', '')
            specs = record_to_spec.get(record_type, [])

            print(f"\n{table_name} ({table_desc}) - レコードタイプ: {record_type}")

            if not specs:
                print("  !! データスペック不明")
                continue

            # 各データスペックを試行
            for spec in specs:
                if spec not in spec_configs:
                    print(f"  !! {spec}: 設定なし")
                    continue

                configs = spec_configs[spec]

                for fromtime, option in configs:
                    try:
                        print(f"  [{spec}] {fromtime} (option={option}) ... ", end='', flush=True)

                        result, read_count, download_count, last_file = jvlink.jv_open(
                            spec, fromtime, option
                        )

                        if result == -1 or read_count == 0:
                            print(f"データなし (result={result}, count={read_count})")
                            jvlink.jv_close()
                            continue

                        if result == -111:
                            print(f"エラー-111 (option不適合)")
                            jvlink.jv_close()
                            continue

                        if result < 0:
                            print(f"エラー{result}")
                            jvlink.jv_close()
                            continue

                        print(f"OK (予定: {read_count}件, DL: {download_count}件)")

                        # ダウンロード待機
                        if download_count > 0:
                            print(f"    ダウンロード待機中...", end='', flush=True)
                            start_time = time.time()
                            while True:
                                status = jvlink.jv_status()
                                if status == 0:
                                    print(" 完了")
                                    break
                                elif status < 0:
                                    print(f" エラー{status}")
                                    break
                                if time.time() - start_time > 120:
                                    print(" タイムアウト")
                                    break
                                time.sleep(1)

                        # レコード取得
                        found_records = defaultdict(int)
                        total_read = 0
                        inserted = 0

                        while total_read < read_count and total_read < 10000:
                            ret_code, read_size, data = jvlink.jv_read()

                            if ret_code == 0:  # Success
                                total_read += 1
                                if data and len(data) > 2:
                                    rec_type = data[0:2].decode('utf-8', errors='ignore')
                                    found_records[rec_type] += 1

                                    # ターゲットレコードタイプなら挿入
                                    if rec_type == record_type:
                                        parser = factory.get_parser(rec_type)
                                        if parser:
                                            try:
                                                parsed = parser.parse(data)
                                                db.insert_records(f"NL_{rec_type}", [parsed])
                                                inserted += 1
                                            except Exception as e:
                                                pass

                            elif ret_code == -1:  # No more data
                                break
                            else:
                                break

                        jvlink.jv_close()

                        if found_records:
                            print(f"    取得レコード: {dict(found_records)}")
                            if record_type in found_records:
                                print(f"    {record_type}レコード: {found_records[record_type]}件 (DB挿入: {inserted}件)")
                                results[table_name].append({
                                    'spec': spec,
                                    'fromtime': fromtime,
                                    'option': option,
                                    'count': found_records[record_type],
                                    'inserted': inserted
                                })
                                # 成功したら次のテーブルへ
                                if inserted > 0:
                                    break
                        else:
                            print(f"    ターゲットレコード ({record_type}) なし")

                    except Exception as e:
                        print(f"エラー: {e}")
                        try:
                            jvlink.jv_close()
                        except:
                            pass

                # このデータスペックで成功したら次のテーブルへ
                if table_name in results and results[table_name]:
                    break

        print("\n[4/4] 最終結果")
        print("=" * 80)

        # データベースの最新統計
        tables_with_data = []
        still_empty = []
        total_records = 0

        for table_name in empty_tables.keys():
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = db.execute_query(query)
            count = result[0][0] if result else 0
            total_records += count

            if count > 0:
                tables_with_data.append((table_name, count))
            else:
                still_empty.append(table_name)

        if tables_with_data:
            print("\n新たにデータが入ったテーブル:")
            for table, count in sorted(tables_with_data, key=lambda x: x[1], reverse=True):
                desc = empty_tables[table]
                success_specs = results.get(table, [])
                if success_specs:
                    spec_info = success_specs[0]
                    print(f"  {table}: {count:,}件 - {desc}")
                    print(f"    データスペック: {spec_info['spec']} (fromtime={spec_info['fromtime']}, option={spec_info['option']})")

        if still_empty:
            print(f"\nまだ空のテーブル ({len(still_empty)}個):")
            for table in still_empty:
                print(f"  - {table}: {empty_tables[table]}")

        print("\n" + "=" * 80)
        if len(still_empty) == 0:
            print("OK 全38テーブルに実データが格納されました！")
        else:
            print(f"OK {len(tables_with_data)}/9テーブルに新規データ格納")
            print(f"   残り{len(still_empty)}テーブルは契約プラン外または期間外の可能性")
        print("=" * 80)

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if jvlink:
            try:
                jvlink.jv_close()
            except:
                pass
        if db:
            db.disconnect()

if __name__ == '__main__':
    main()
