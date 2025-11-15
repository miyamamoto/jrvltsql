#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DIFF データ取得テスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.jvlink.wrapper import JVLinkWrapper

print("=" * 70)
print("DIFF データ取得テスト (マスタデータ)")
print("=" * 70)
print()

wrapper = JVLinkWrapper()
print("1. JV_Init() を呼び出します...")
try:
    ret = wrapper.jv_init()
    print(f"   [OK] JV_Init() 成功: {ret}")
except Exception as e:
    print(f"   [ERROR] JV_Init() 失敗: {e}")
    sys.exit(1)

print()
print("2. JVOpen() を呼び出します...")
print("   データ仕様: DIFF (マスタデータ)")
print("   日時範囲: 20200101000000-20251231235959 (広い範囲)")
print("   オプション: 0 (NORMAL)")

try:
    result, read_count, download_count, timestamp = wrapper.jv_open(
        "DIFF",
        "20200101000000-20251231235959",
        option=0
    )
    print(f"   [OK] JVOpen() 成功!")
    print(f"   戻り値: {result}")
    print(f"   読み込み件数: {read_count}")
    print(f"   ダウンロード件数: {download_count}")
    print(f"   最終ファイルタイムスタンプ: {timestamp}")

    # Close the stream
    wrapper.jv_close()
    print("   [OK] JVClose() 成功")
    print()
    print("[SUCCESS] API呼び出しは正常に機能しています！")

except Exception as e:
    print(f"   [ERROR] JVOpen() 失敗: {e}")
    print()
    print("異なるデータ仕様やSETUPモードを試してみます...")
    print()

    # Try SETUP mode
    print("3. JVOpen() SETUP mode を試します...")
    print("   オプション: 1 (SETUP - データダウンロード)")
    try:
        result, read_count, download_count, timestamp = wrapper.jv_open(
            "DIFF",
            "20200101000000-20251231235959",
            option=1
        )
        print(f"   [OK] JVOpen() SETUP成功!")
        print(f"   戻り値: {result}")
        print(f"   読み込み件数: {read_count}")
        print(f"   ダウンロード件数: {download_count}")
        print(f"   最終ファイルタイムスタンプ: {timestamp}")

        wrapper.jv_close()
        print("   [OK] JVClose() 成功")
        print()
        print("[SUCCESS] SETUP modeで成功しました！")

    except Exception as e2:
        print(f"   [ERROR] SETUP mode も失敗: {e2}")
        import traceback
        traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
