#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""実データ取得テスト

サービスキーが既に設定されている環境で、実際にJRA-VANからデータを取得するテスト
"""

import sys
from datetime import datetime, timedelta

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.fetcher.historical import HistoricalFetcher

print("=" * 70)
print("JRA-VAN 実データ取得テスト")
print("=" * 70)
print()

# 確実にデータが存在する過去の日付を使用（2024年11月3日）
from_date = "20241103"  # 2024年11月3日
to_date = from_date

print(f"取得日付: {from_date} ({from_date[:4]}年{from_date[4:6]}月{from_date[6:8]}日)")
print(f"データ仕様: RACE（レース情報）")
print(f"制限: 最大10件のレコード")
print()

# HistoricalFetcherを作成
print("HistoricalFetcher を初期化しています...")
fetcher = HistoricalFetcher()  # sid="UNKNOWN"
print("[OK] 初期化完了")
print()

# データ取得開始
print("=" * 70)
print("データ取得開始...")
print("=" * 70)
print()

try:
    record_count = 0
    record_types = {}

    for record in fetcher.fetch("RACE", from_date, to_date):
        record_count += 1

        # レコード種別をカウント
        rec_type = record.get("headRecordSpec", "Unknown")
        record_types[rec_type] = record_types.get(rec_type, 0) + 1

        # 最初のレコードの詳細を表示
        if record_count == 1:
            print("[サンプルレコード #1]")
            print(f"  レコード種別: {rec_type}")

            # 主要フィールドを表示
            if rec_type == "RA":
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  月日: {record.get('idMonthDay', 'N/A')}")
                print(f"  競馬場: {record.get('idJyoCD', 'N/A')}")
                print(f"  レース番号: {record.get('idRaceNum', 'N/A')}")
                print(f"  レース名: {record.get('RaceName', 'N/A')}")
                print(f"  距離: {record.get('Kyori', 'N/A')}m")
            elif rec_type == "SE":
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  馬番: {record.get('Umaban', 'N/A')}")
                print(f"  馬名: {record.get('Bamei', 'N/A')}")
                print(f"  血統登録番号: {record.get('KettoNum', 'N/A')}")
            elif rec_type == "HR":
                print(f"  年度: {record.get('idYear', 'N/A')}")
                print(f"  レース番号: {record.get('idRaceNum', 'N/A')}")
                print(f"  単勝馬番: {record.get('TansyoUmaban1', 'N/A')}")

            print(f"  フィールド数: {len(record)}")
            print()

        # 10件で制限
        if record_count >= 10:
            print(f"[制限] 10件に達したため、取得を停止します")
            break

    # 統計情報を表示
    print()
    print("=" * 70)
    print("取得結果")
    print("=" * 70)

    stats = fetcher.get_statistics()
    print(f"取得レコード数: {stats['records_fetched']}")
    print(f"パース成功数:   {stats['records_parsed']}")
    print(f"パース失敗数:   {stats['records_failed']}")
    print()

    print("レコード種別内訳:")
    for rec_type, count in sorted(record_types.items()):
        print(f"  {rec_type}: {count}件")
    print()

    if record_count > 0:
        print("[SUCCESS] データ取得成功！")
        print()
        print("JLTSQLは正常に動作しています。")
        print("完全なワークフロー（取得→パース→DB保存）のテストを実行できます。")
    else:
        print("[WARNING] データが取得できませんでした")
        print()
        print("考えられる原因:")
        print("1. 指定日付にデータが存在しない")
        print("2. JV-Linkサービスが起動していない")
        print("3. ネットワーク接続の問題")

except Exception as e:
    print(f"[ERROR] エラーが発生しました: {e}")
    print()
    import traceback
    traceback.print_exc()
    print()
    print("【トラブルシューティング】")
    print("1. JV-Linkサービスが起動しているか確認してください")
    print("2. インターネット接続を確認してください")
    print("3. JRA-VANの契約状況を確認してください")

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
