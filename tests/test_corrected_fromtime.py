#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修正されたfromtime（単一日時）でのテスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher

print("=" * 70)
print("fromtime修正後のデータ取得テスト")
print("=" * 70)
print()

print("fromtimeは「この日時以降のデータ」を取得します（範囲ではありません）")
print()

# テストケース
test_cases = [
    ("20251110", "20251110", "今日（最新）"),
    ("20241101", "20241101", "2024年11月1日以降"),
    ("20240101", "20240101", "2024年1月1日以降"),
    ("20230101", "20230101", "2023年1月1日以降"),
]

fetcher = HistoricalFetcher()

for from_date, to_date, description in test_cases:
    print(f"\n【{description}】")
    print(f"  fromtime: {from_date}000000 （{from_date[:4]}年{from_date[4:6]}月{from_date[6:8]}日 00:00:00以降）")
    print(f"  データ仕様: RACE")

    try:
        record_count = 0
        for record in fetcher.fetch("RACE", from_date, to_date):
            record_count += 1
            if record_count == 1:
                print(f"  ✓ データ取得成功！")
                print(f"    レコード種別: {record.get('headRecordSpec')}")
                if record.get('headRecordSpec') == 'RA':
                    print(f"    レース名: {record.get('RaceName', 'N/A')}")
                    print(f"    年度: {record.get('idYear', 'N/A')}")
                break

        if record_count == 0:
            print(f"  ✗ データなし（この日時以降に新しいデータがありません）")
        else:
            print(f"  → データ取得成功！この設定で使用できます")
            break  # 成功したら終了

    except Exception as e:
        print(f"  ✗ エラー: {e}")

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
