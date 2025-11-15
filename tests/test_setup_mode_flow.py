#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SETUP mode での完全フローテスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher

print("=" * 70)
print("SETUP mode での完全フローテスト")
print("=" * 70)
print()

print("注意: SETUP mode (option=1) は初回データダウンロード用です")
print()

fetcher = HistoricalFetcher()

# 今日の日付
from_date = "20251110"  # 2025-11-10 (from setting.xml)
to_date = "20251110"

print(f"日付: {from_date} ({from_date[:4]}年{from_date[4:6]}月{from_date[6:8]}日以降)")
print(f"データ仕様: RACE")
print(f"モード: SETUP (option=1)")
print()

try:
    record_count = 0
    record_types = {}

    print("データ取得・パース中...")
    print()

    for record in fetcher.fetch("RACE", from_date, to_date, option=1):  # SETUP mode
        record_count += 1

        # レコード種別を集計
        rec_type = record.get('headRecordSpec', 'UNKNOWN')
        record_types[rec_type] = record_types.get(rec_type, 0) + 1

        # 最初の10件を表示
        if record_count <= 10:
            print(f"レコード {record_count}:")
            print(f"  レコード種別: {rec_type}")

            # レコード種別ごとに表示
            if rec_type == 'RA':
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  競馬場: {record.get('idJyoCD', 'N/A')}")
                print(f"  回: {record.get('idKaisuuCode', 'N/A')}")
                print(f"  日: {record.get('idNichiji', 'N/A')}")
                print(f"  レース番号: {record.get('idRaceNum', 'N/A')}")
                print(f"  レース名: {record.get('RaceName', 'N/A')}")
            elif rec_type == 'SE':
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  馬番: {record.get('idBangou', 'N/A')}")
                print(f"  馬名: {record.get('UmaName', 'N/A')}")
            elif rec_type == 'HR':
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  単勝: {record.get('TansyoPay1', 'N/A')}")
                print(f"  複勝1: {record.get('FukusyoPay1', 'N/A')}")
            elif rec_type == 'JG':
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  除外理由コード: {record.get('ExclusionCode', 'N/A')}")
                print(f"  馬名: {record.get('UmaName', 'N/A')}")
            else:
                # 最初のいくつかのフィールドを表示
                for key in list(record.keys())[:5]:
                    print(f"  {key}: {record.get(key, 'N/A')}")

            print()

        # 最大50件で制限
        if record_count >= 50:
            print(f"(最大50件で制限しました)")
            break

    print()
    print("=" * 70)
    print("結果")
    print("=" * 70)
    print(f"取得・パース成功: {record_count}件")
    print()
    print("レコード種別内訳:")
    for rec_type, count in sorted(record_types.items()):
        print(f"  {rec_type}: {count}件")

    # 統計情報
    stats = fetcher.get_statistics()
    print()
    print("統計情報:")
    print(f"  Fetched: {stats['records_fetched']}")
    print(f"  Parsed: {stats['records_parsed']}")
    print(f"  Failed: {stats['records_failed']}")

    print()
    if record_count > 0:
        print("[SUCCESS] SETUP mode で実際のJV-Dataを取得・パースできました！")
    else:
        print("[INFO] データなし")

except Exception as e:
    print(f"\n[ERROR] エラー発生: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
