#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
64-bit Python COM接続テストスクリプト

64-bit Python から JV-Link / NV-Link に接続できるかテストします。
一般ユーザ権限で実行可能です（レジストリの読み取りのみ）。

使用方法:
    python test_64bit_com.py

レジストリ設定が不足している場合:
    python check_dll_surrogate.py --fix  # 管理者権限で実行

Author: @your_username
License: MIT
"""

import sys
import struct


def main():
    # アーキテクチャ確認
    arch = struct.calcsize("P") * 8
    print(f"Python: {sys.version}")
    print(f"Architecture: {arch}-bit")

    if arch != 64:
        print("\n[INFO] このテストは64-bit Python用です")
        print("32-bit Pythonでは DLL Surrogate 設定なしでCOM接続できます")
        return 0

    print("\n" + "=" * 60)
    print("DLL Surrogate Registry Check")
    print("=" * 60)

    import winreg

    COM_COMPONENTS = {
        "JV-Link": "{2AB1774D-0C41-11D7-916F-0003479BEB3F}",
        "NV-Link": "{F726BBA6-5784-4529-8C67-26E152D49D73}",
    }

    registry_ok = True

    for name, clsid in COM_COMPONENTS.items():
        print(f"\n--- {name} ---")

        checks = [
            (f"CLSID\\{clsid}", "AppID"),
            (f"AppID\\{clsid}", "DllSurrogate"),
        ]

        for path, value_name in checks:
            try:
                key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path, 0, winreg.KEY_READ)
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    print(f"  [OK] {value_name}")
                except FileNotFoundError:
                    print(f"  [NG] {value_name}: 未設定")
                    registry_ok = False
                winreg.CloseKey(key)
            except FileNotFoundError:
                print(f"  [NG] {path}: キーなし")
                registry_ok = False

        # RunAs 競合チェック
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                f"AppID\\{clsid}",
                0, winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "RunAs")
                print(f"  [WARN] RunAs={value!r} (競合)")
                registry_ok = False
            except FileNotFoundError:
                pass  # OK
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass

    if not registry_ok:
        print("\n" + "-" * 60)
        print("[WARNING] DLL Surrogate設定に問題があります")
        print("管理者権限で以下を実行してください:")
        print("  python check_dll_surrogate.py --fix")
        print("-" * 60)

    print("\n" + "=" * 60)
    print("COM Connection Test")
    print("=" * 60)

    try:
        import win32com.client
    except ImportError:
        print("\n[ERROR] pywin32 がインストールされていません")
        print("  pip install pywin32")
        return 1

    com_ok = True

    # JV-Link
    print("\n--- JV-Link (JVDTLab.JVLink) ---")
    try:
        jv = win32com.client.Dispatch("JVDTLab.JVLink")
        print("  [OK] COM接続成功")
    except Exception as e:
        print(f"  [NG] {e}")
        com_ok = False

    # NV-Link
    print("\n--- NV-Link (NVDTLabLib.NVLink) ---")
    try:
        nv = win32com.client.Dispatch("NVDTLabLib.NVLink")
        print("  [OK] COM接続成功")

        rc = nv.NVInit("UNKNOWN")
        print(f"  [OK] NVInit: {rc}")

        nv.NVClose()
        print("  [OK] NVClose: 正常終了")
    except Exception as e:
        print(f"  [NG] {e}")
        com_ok = False

    # 結果
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"  Registry: {'OK' if registry_ok else 'NG'}")
    print(f"  COM:      {'OK' if com_ok else 'NG'}")

    if registry_ok and com_ok:
        print("\n64-bit Python から JV-Link/NV-Link に正常接続できます!")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
