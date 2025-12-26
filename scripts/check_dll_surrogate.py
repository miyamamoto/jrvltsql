#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DLL Surrogate レジストリ設定チェック・設定スクリプト

64bit Pythonから32bit COM DLL (JV-Link, NV-Link)を使用するために必要な
レジストリ設定を確認・設定します。

使用方法:
    python check_dll_surrogate.py          # 確認のみ
    python check_dll_surrogate.py --fix    # 設定も行う（管理者権限必要）

参考:
    https://note.com/hraps/n/n86589e3c359c
    https://qiita.com/hraps/items/594936369b5f0c856a8f
"""

import sys
import struct
import argparse
import ctypes

# CLSIDとProgID
COM_COMPONENTS = {
    "JV-Link": {
        "clsid": "{2AB1774D-0C41-11D7-916F-0003479BEB3F}",
        "progid": "JVDTLab.JVLink",
    },
    "NV-Link": {
        "clsid": "{F726BBA6-5784-4529-8C67-26E152D49D73}",
        "progid": "NVDTLabLib.NVLink",
    },
}


def is_admin():
    """管理者権限で実行されているか確認"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def check_registry_key(root, subkey, value_name=None):
    """レジストリキーまたは値の存在を確認"""
    import winreg
    try:
        key = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ)
        if value_name:
            try:
                value, _ = winreg.QueryValueEx(key, value_name)
                winreg.CloseKey(key)
                return True, value
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False, None
        winreg.CloseKey(key)
        return True, None
    except FileNotFoundError:
        return False, None


def set_registry_value(root, subkey, value_name, value, value_type):
    """レジストリ値を設定"""
    import winreg
    try:
        key = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def check_dll_surrogate(name, clsid, fix=False):
    """DLL Surrogate設定を確認"""
    import winreg

    print(f"\n=== {name} ({clsid}) ===")

    all_ok = True

    # 確認するレジストリパス
    checks = [
        # 32bit CLSID - AppID
        {
            "path": f"Wow6432Node\\CLSID\\{clsid}",
            "value": "AppID",
            "expected": clsid,
            "desc": "32bit CLSID AppID",
        },
        # 32bit AppID - DllSurrogate
        {
            "path": f"Wow6432Node\\AppID\\{clsid}",
            "value": "DllSurrogate",
            "expected": "",
            "desc": "32bit AppID DllSurrogate",
        },
        # 64bit AppID - DllSurrogate
        {
            "path": f"AppID\\{clsid}",
            "value": "DllSurrogate",
            "expected": "",
            "desc": "64bit AppID DllSurrogate",
        },
        # 64bit CLSID - AppID
        {
            "path": f"CLSID\\{clsid}",
            "value": "AppID",
            "expected": clsid,
            "desc": "64bit CLSID AppID",
        },
    ]

    # RunAs設定がDllSurrogateと競合するため削除が必要
    runas_paths = [
        f"AppID\\{clsid}",
        f"Wow6432Node\\AppID\\{clsid}",
    ]

    for path in runas_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, "RunAs")
                print(f"  [WARN] {path} に RunAs={value!r} があります（DllSurrogateと競合）")
                if fix:
                    winreg.CloseKey(key)
                    key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "RunAs")
                    print(f"       -> RunAs を削除しました")
            except FileNotFoundError:
                pass  # RunAs doesn't exist, which is good
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass

    for check in checks:
        exists, value = check_registry_key(
            winreg.HKEY_CLASSES_ROOT,
            check["path"],
            check["value"]
        )

        if exists and value == check["expected"]:
            print(f"  [OK] {check['desc']}")
        else:
            all_ok = False
            if exists:
                print(f"  [NG] {check['desc']}: got={value!r}, expected={check['expected']!r}")
            else:
                print(f"  [NG] {check['desc']}: 未設定")

            if fix:
                print(f"       -> 修正中...")
                success = set_registry_value(
                    winreg.HKEY_CLASSES_ROOT,
                    check["path"],
                    check["value"],
                    check["expected"],
                    winreg.REG_SZ
                )
                if success:
                    print(f"       -> 修正完了")
                else:
                    print(f"       -> 修正失敗（管理者権限が必要）")

    return all_ok


def test_com_connection(progid):
    """COM接続テスト"""
    try:
        import win32com.client
        obj = win32com.client.Dispatch(progid)
        return True, obj
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="DLL Surrogate レジストリ設定チェック・設定"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="設定を修正する（管理者権限必要）"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="COM接続テストも実行"
    )
    args = parser.parse_args()

    # アーキテクチャ確認
    arch = struct.calcsize("P") * 8
    print(f"Python: {sys.version}")
    print(f"Architecture: {arch}-bit")

    if arch != 64:
        print("\n[INFO] 32-bit Pythonでは DLL Surrogate 設定は不要です")
        return 0

    if args.fix and not is_admin():
        print("\n[ERROR] --fix オプションには管理者権限が必要です")
        print("        管理者権限でコマンドプロンプトを開いて実行してください")
        return 1

    # レジストリ確認
    all_ok = True
    for name, info in COM_COMPONENTS.items():
        ok = check_dll_surrogate(name, info["clsid"], fix=args.fix)
        all_ok = all_ok and ok

    # COM接続テスト
    if args.test:
        print("\n=== COM接続テスト ===")
        for name, info in COM_COMPONENTS.items():
            success, result = test_com_connection(info["progid"])
            if success:
                print(f"  [OK] {name} ({info['progid']})")
            else:
                print(f"  [NG] {name}: {result}")

    # 結果サマリー
    print("\n" + "=" * 50)
    if all_ok:
        print("全ての DLL Surrogate 設定が正しく構成されています")
        return 0
    else:
        if args.fix:
            print("一部の設定を修正しました。再度確認してください。")
        else:
            print("DLL Surrogate 設定が不足しています。")
            print("--fix オプションで修正するか、.reg ファイルを実行してください。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
