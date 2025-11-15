#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SETUP mode でのデータ取得テスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher

print("=" * 70)
print("SETUP mode データ取得テスト")
print("=" * 70)
print()

print("SETUP mode (option=1) は初回データダウンロード用です")
print("注意: データ量により時間がかかる場合があります")
print()

fetcher = HistoricalFetcher()

# SETUP modeで最小限のデータ範囲を試す
from_date = "20241101"  # 2024年11月1日
to_date = "20241101"    # 同日

print(f"日付: {from_date} ({from_date[:4]}年{from_date[4:6]}月{from_date[6:8]}日)")
print(f"データ仕様: RACE")
print(f"モード: SETUP (option=1)")
print()

try:
    record_count = 0
    print("データ取得中...")

    for record in fetcher.fetch("RACE", from_date, to_date, option=1):  # option=1 for SETUP
        record_count += 1

        if record_count == 1:
            print()
            print(f"✓ データ取得成功！")
            print(f"  レコード種別: {record.get('headRecordSpec')}")

            if record.get('headRecordSpec') == 'RA':
                print(f"  レース名: {record.get('RaceName', 'N/A')}")
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  競馬場: {record.get('idJyoCD', 'N/A')}")

        # 最大10件で制限
        if record_count >= 10:
            print(f"\n  (最大10件で制限しました)")
            break

    print()
    if record_count == 0:
        print("✗ データなし")
        print()
        print("考えられる原因:")
        print("1. 指定日にレース開催がなかった")
        print("2. データへのアクセス権限がない")
        print("3. セットアップが必要")
    else:
        print(f"取得レコード数: {record_count}件")
        print()
        print("[SUCCESS] SETUP mode でデータ取得に成功しました！")

except Exception as e:
    print(f"\n[ERROR] エラー発生: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
