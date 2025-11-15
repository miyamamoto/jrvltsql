#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""JVRead COM呼び出しの各種パターンを試す"""

import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import win32com.client

print("=" * 70)
print("JVRead COM呼び出しパターンテスト")
print("=" * 70)
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
    print(f"   [OK] result={jv_result}")
    if isinstance(jv_result, tuple):
        result, read_count, download_count, timestamp = jv_result
        print(f"   - result: {result}")
        print(f"   - read_count: {read_count}")
        print(f"   - download_count: {download_count}")
        print(f"   - timestamp: {timestamp}")
    print()

    #3. Test different JVRead patterns
    print("3. JVRead()パターンテスト")
    print()

    # Pattern 1: No arguments (current approach)
    print("   Pattern 1: JVRead() - 引数なし")
    sys.stdout.flush()
    try:
        import threading
        import time

        result_holder = [None]
        exception_holder = [None]

        def call_jvread():
            try:
                result_holder[0] = jvlink.JVRead()
            except Exception as e:
                exception_holder[0] = e

        thread = threading.Thread(target=call_jvread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)

        if thread.is_alive():
            print("      [TIMEOUT] 5秒でタイムアウト（ハング）")
        elif exception_holder[0]:
            print(f"      [ERROR] {exception_holder[0]}")
        else:
            print(f"      [OK] result={result_holder[0]}")
    except Exception as e:
        print(f"      [ERROR] {e}")
    print()

    # Close and reopen for next test
    jvlink.JVClose()
    jvlink.JVOpen("RACE", "20241101000000", 1)

    # Pattern 2: Try with VARIANT parameters
    print("   Pattern 2: VARIANT parameters")
    sys.stdout.flush()
    try:
        import pythoncom

        result_holder = [None]
        exception_holder = [None]

        def call_jvread():
            try:
                # Try with VARIANT ByRef
                buff = pythoncom.Empty
                size = pythoncom.Empty
                filename = pythoncom.Empty
                result_holder[0] = jvlink.JVRead(buff, size, filename)
            except Exception as e:
                exception_holder[0] = e

        thread = threading.Thread(target=call_jvread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)

        if thread.is_alive():
            print("      [TIMEOUT] 5秒でタイムアウト（ハング）")
        elif exception_holder[0]:
            print(f"      [ERROR] {exception_holder[0]}")
        else:
            print(f"      [OK] result={result_holder[0]}")
    except Exception as e:
        print(f"      [ERROR] {e}")
    print()

    # Close and reopen for next test
    jvlink.JVClose()
    jvlink.JVOpen("RACE", "20241101000000", 1)

    # Pattern 3: Try accessing via GetIDsOfNames/Invoke
    print("   Pattern 3: IDispatch直接呼び出し")
    sys.stdout.flush()
    try:
        result_holder = [None]
        exception_holder = [None]

        def call_jvread():
            try:
                # Try dynamic dispatch
                import win32com.client
                disp = win32com.client.dynamic.Dispatch("JVDTLab.JVLink")
                disp.JVInit("UNKNOWN")
                disp.JVOpen("RACE", "20241101000000", 1)
                result_holder[0] = disp.JVRead()
            except Exception as e:
                exception_holder[0] = e

        thread = threading.Thread(target=call_jvread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)

        if thread.is_alive():
            print("      [TIMEOUT] 5秒でタイムアウト（ハング）")
        elif exception_holder[0]:
            print(f"      [ERROR] {exception_holder[0]}")
        else:
            print(f"      [OK] result={result_holder[0]}")
    except Exception as e:
        print(f"      [ERROR] {e}")
    print()

    # Clean up
    try:
        jvlink.JVClose()
    except:
        pass

except Exception as e:
    print(f"\n[ERROR] エラー発生: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
