#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""正しいJVRead()呼び出しテスト"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import win32com.client

print("=" * 70)
print("正しいJVRead()呼び出しテスト")
print("=" * 70)
print()

print("参考: https://zenn.dev/nozele/articles/c64e456d0c77e4")
print("JVRead(\"\", 102890, \"\") の形式で呼び出します")
print()

jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

try:
    # 1. Initialize
    print("1. JV_Init()")
    result = jvlink.JVInit("UNKNOWN")
    print(f"   [OK] result={result}")
    print()

    # 2. Open
    print("2. JVOpen()")
    jv_result = jvlink.JVOpen("RACE", "20241101000000", 1)
    result, read_count, download_count, timestamp = jv_result
    print(f"   [OK] result={result}, read_count={read_count}")
    print()

    # 3. JVRead with correct signature
    print("3. JVRead(\"\", 102890, \"\")")
    print("   (第1引数: 空文字列, 第2引数: バッファサイズ, 第3引数: 空文字列)")
    sys.stdout.flush()

    returnval = jvlink.JVRead("", 102890, "")

    print(f"   [SUCCESS] JVRead成功!")
    print(f"   返り値の型: {type(returnval)}")
    print(f"   返り値の長さ: {len(returnval) if isinstance(returnval, (list, tuple)) else 'N/A'}")

    if isinstance(returnval, (list, tuple)):
        print(f"   returnval[0] (エラーコード): {returnval[0]}")
        print(f"   returnval[1] (バッファ)の長さ: {len(returnval[1]) if len(returnval) > 1 else 'N/A'}")
        if len(returnval) > 1 and returnval[1]:
            print(f"   returnval[1] (バッファ)の最初の100文字: {returnval[1][:100]}")
        print(f"   returnval[2] (ファイル名): {returnval[2] if len(returnval) > 2 else 'N/A'}")

    print()

    # Read a few more records
    print("4. 追加で数レコード読み込みテスト")
    for i in range(5):
        returnval = jvlink.JVRead("", 102890, "")
        error_code = returnval[0]

        if error_code == 0:
            print(f"   レコード{i+2}: 完了 (error_code=0)")
            break
        elif error_code == -1:
            print(f"   レコード{i+2}: ファイル切り替わり (error_code=-1)")
        elif error_code < -1:
            print(f"   レコード{i+2}: エラー (error_code={error_code})")
            break
        else:
            buff = returnval[1]
            filename = returnval[2]
            rec_id = buff[0:2] if buff else "??"
            print(f"   レコード{i+2}: 読み込み成功 (error_code={error_code}, rec_id={rec_id}, filename={filename})")

    # 4. Close
    print()
    print("5. JVClose()")
    jvlink.JVClose()
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
