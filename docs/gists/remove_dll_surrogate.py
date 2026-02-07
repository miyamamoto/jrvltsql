#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DLL Surrogate レジストリ設定削除スクリプト

64bit Python用に追加したDLL Surrogate設定を削除します。
削除後は32-bit Pythonのみでの動作になります。

使用方法:
    python remove_dll_surrogate.py          # 確認のみ（dry-run）
    python remove_dll_surrogate.py --status # 現在の状態を表示
    python remove_dll_surrogate.py --force  # 実際に削除（管理者権限必要）

注意:
    - 管理者権限が必要です
    - 削除後は64-bit PythonからJV-Link/NV-Linkにアクセスできなくなります
    - 再度有効にするには check_dll_surrogate.py --fix を実行してください

Author: @your_username
License: MIT
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
    except Exception:
        return False


def check_registry_value(root, subkey, value_name=None):
    """レジストリ値を確認"""
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


def delete_registry_value(root, subkey, value_name):
    """レジストリ値を削除"""
    import winreg
    try:
        key = winreg.OpenKey(root, subkey, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, value_name)
        winreg.CloseKey(key)
        return True, None
    except FileNotFoundError:
        return False, "キーまたは値が存在しません"
    except PermissionError:
        return False, "管理者権限が必要です"
    except Exception as e:
        return False, str(e)


def show_current_status(name, clsid):
    """現在のレジストリ状態を表示"""
    import winreg

    print(f"\n=== {name} ({clsid}) ===")

    # DLL Surrogate設定の確認
    settings = [
        (f"Wow6432Node\\CLSID\\{clsid}", "AppID", "32bit CLSID AppID"),
        (f"Wow6432Node\\AppID\\{clsid}", "DllSurrogate", "32bit AppID DllSurrogate"),
        (f"AppID\\{clsid}", "DllSurrogate", "64bit AppID DllSurrogate"),
        (f"CLSID\\{clsid}", "AppID", "64bit CLSID AppID"),
    ]

    found_count = 0
    for path, value_name, desc in settings:
        exists, value = check_registry_value(winreg.HKEY_CLASSES_ROOT, path, value_name)
        if exists:
            print(f"  [EXISTS] {desc}: {value!r}")
            found_count += 1
        else:
            print(f"  [EMPTY]  {desc}")

    return found_count


def remove_dll_surrogate(name, clsid, force=False):
    """DLL Surrogate設定を削除"""
    import winreg

    print(f"\n=== {name} ({clsid}) ===")

    # 削除対象
    targets = [
        (f"CLSID\\{clsid}", "AppID", "64bit CLSID AppID"),
        (f"AppID\\{clsid}", "DllSurrogate", "64bit AppID DllSurrogate"),
        (f"Wow6432Node\\CLSID\\{clsid}", "AppID", "32bit CLSID AppID"),
        (f"Wow6432Node\\AppID\\{clsid}", "DllSurrogate", "32bit AppID DllSurrogate"),
    ]

    removed = 0
    errors = 0

    for path, value_name, desc in targets:
        exists, value = check_registry_value(winreg.HKEY_CLASSES_ROOT, path, value_name)

        if not exists:
            print(f"  [SKIP] {desc}: 存在しません")
            continue

        if force:
            success, error = delete_registry_value(
                winreg.HKEY_CLASSES_ROOT, path, value_name
            )
            if success:
                print(f"  [DELETED] {desc}")
                removed += 1
            else:
                print(f"  [ERROR] {desc}: {error}")
                errors += 1
        else:
            print(f"  [DRY-RUN] {desc}: {value!r} を削除予定")
            removed += 1

    return removed, errors


def main():
    parser = argparse.ArgumentParser(
        description="DLL Surrogate レジストリ設定削除",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
    python remove_dll_surrogate.py          # 確認のみ（削除しない）
    python remove_dll_surrogate.py --status # 現在の状態を表示
    python remove_dll_surrogate.py --force  # 実際に削除（管理者権限必要）

注意:
    削除後は64-bit PythonからJV-Link/NV-Linkにアクセスできなくなります。
    再度有効にするには check_dll_surrogate.py --fix を実行してください。
"""
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="実際に削除を実行（管理者権限必要）"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="現在の状態を表示のみ"
    )
    args = parser.parse_args()

    # アーキテクチャ確認
    arch = struct.calcsize("P") * 8
    print(f"Python: {sys.version}")
    print(f"Architecture: {arch}-bit")

    if args.status:
        print("\n" + "=" * 60)
        print("現在のレジストリ状態")
        print("=" * 60)

        total_found = 0
        for name, info in COM_COMPONENTS.items():
            found = show_current_status(name, info["clsid"])
            total_found += found

        print("\n" + "=" * 60)
        if total_found > 0:
            print(f"DLL Surrogate設定: {total_found}件 存在")
        else:
            print("DLL Surrogate設定: なし")
        return 0

    if args.force:
        if not is_admin():
            print("\n[ERROR] --force オプションには管理者権限が必要です")
            print("        管理者権限でコマンドプロンプトを開いて実行してください")
            return 1

        print("\n" + "=" * 60)
        print("DLL Surrogate設定を削除します")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("DLL Surrogate設定の削除プレビュー（dry-run）")
        print("実際に削除するには --force オプションを使用してください")
        print("=" * 60)

    total_removed = 0
    total_errors = 0

    for name, info in COM_COMPONENTS.items():
        removed, errors = remove_dll_surrogate(name, info["clsid"], force=args.force)
        total_removed += removed
        total_errors += errors

    # 結果サマリー
    print("\n" + "=" * 60)
    if args.force:
        print(f"削除完了: {total_removed}件")
        if total_errors > 0:
            print(f"エラー: {total_errors}件")
            return 1
        print("\n64-bit PythonからのCOMアクセスが無効になりました。")
        print("再度有効にするには:")
        print("  python check_dll_surrogate.py --fix")
    else:
        print(f"削除予定: {total_removed}件")
        print("\n実際に削除するには:")
        print("  python remove_dll_surrogate.py --force")

    return 0


if __name__ == "__main__":
    sys.exit(main())
