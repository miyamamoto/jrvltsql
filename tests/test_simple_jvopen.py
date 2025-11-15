#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple JVOpen test"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.jvlink.wrapper import JVLinkWrapper

print("=" * 70)
print("JVOpen シンプルテスト")
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
print("2. JVOpen() を呼び出します (SETUP mode)...")
print("   データ仕様: RACE")
print("   日時範囲: 20241103000000-20241103235959")
print("   オプション: 1 (SETUP - データダウンロード)")

try:
    result, read_count, download_count, timestamp = wrapper.jv_open(
        "RACE",
        "20241103000000-20241103235959",
        option=1  # SETUP mode
    )
    print(f"   [OK] JVOpen() 成功!")
    print(f"   戻り値: {result}")
    print(f"   読み込み件数: {read_count}")
    print(f"   ダウンロード件数: {download_count}")
    print(f"   最終ファイルタイムスタンプ: {timestamp}")

    # Close the stream
    wrapper.jv_close()
    print("   [OK] JVClose() 成功")

except Exception as e:
    print(f"   [ERROR] JVOpen() 失敗: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
