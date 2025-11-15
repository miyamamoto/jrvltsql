#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JVRead 直接テスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.jvlink.wrapper import JVLinkWrapper

print("=" * 70)
print("JVRead 直接テスト")
print("=" * 70)
print()

wrapper = JVLinkWrapper()

try:
    # 1. Initialize
    print("1. JV_Init() を呼び出します...")
    wrapper.jv_init()
    print("   [OK] 初期化成功")
    print()

    # 2. Open
    print("2. JVOpen() を呼び出します (SETUP mode)...")
    print("   fromtime: 20241101000000")
    result, read_count, download_count, timestamp = wrapper.jv_open(
        "RACE",
        "20241101000000",
        option=1
    )
    print(f"   [OK] JVOpen成功")
    print(f"   - result: {result}")
    print(f"   - read_count: {read_count}")
    print(f"   - download_count: {download_count}")
    print(f"   - timestamp: {timestamp}")
    print()

    # 3. Read one record
    print("3. JVRead() を1回呼び出します...")
    print("   (この呼び出しでハングアップする可能性があります)")
    sys.stdout.flush()

    ret_code, buff, filename = wrapper.jv_read()

    print(f"   [OK] JVRead成功!")
    print(f"   - ret_code: {ret_code}")
    print(f"   - buff length: {len(buff) if buff else 0}")
    print(f"   - filename: {filename}")

    if buff and len(buff) > 0:
        print(f"   - データサンプル (最初の100バイト): {buff[:100]}")

    # 4. Close
    print()
    print("4. JVClose() を呼び出します...")
    wrapper.jv_close()
    print("   [OK] クローズ成功")

    print()
    print("[SUCCESS] すべての操作が成功しました！")

except Exception as e:
    print(f"\n[ERROR] エラー発生: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
