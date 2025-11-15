#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""広い日付範囲でのデータ取得テスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher

print("=" * 70)
print("広い日付範囲でのデータ取得テスト")
print("=" * 70)
print()

# 広い日付範囲を試す
date_ranges = [
    ("20240101", "20241231", "2024年全体"),
    ("20230101", "20231231", "2023年全体"),
    ("20220101", "20221231", "2022年全体"),
]

fetcher = HistoricalFetcher()

for from_date, to_date, description in date_ranges:
    print(f"\n【{description}】")
    print(f"  期間: {from_date} - {to_date}")
    print(f"  データ仕様: RACE")

    try:
        record_count = 0
        for record in fetcher.fetch("RACE", from_date, to_date):
            record_count += 1
            if record_count == 1:
                print(f"  ✓ データ取得成功！")
                print(f"    最初のレコード種別: {record.get('headRecordSpec')}")
                break

        if record_count == 0:
            print(f"  ✗ データなし")
        else:
            print(f"  → このデータ仕様と期間でデータが取得できます")
            break  # 成功したら終了

    except Exception as e:
        print(f"  ✗ エラー: {e}")

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
