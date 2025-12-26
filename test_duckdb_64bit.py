#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DuckDB 64-bit動作確認テスト

64-bit Python環境でDuckDB、JV-Link、NV-Linkが正常に動作することを確認します。
一般ユーザ権限で実行可能です（レジストリの読み取りのみ）。

レジストリ設定が不足している場合は、管理者権限で以下を実行してください：
    python scripts/check_dll_surrogate.py --fix
"""

import sys
import struct
import tempfile
from pathlib import Path

# =============================================================================
# アーキテクチャ確認
# =============================================================================
arch = struct.calcsize("P") * 8
print(f"Python architecture: {arch}-bit")
print(f"Python version: {sys.version}")

if arch != 64:
    print("ERROR: This test requires 64-bit Python")
    sys.exit(1)

# Add project path
sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# DLL Surrogate レジストリ確認（管理者権限不要）
# =============================================================================
print("\n" + "=" * 60)
print("DLL Surrogate Registry Check (read-only)")
print("=" * 60)

# COM コンポーネント定義
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


def check_registry_value(root, subkey, value_name=None):
    """レジストリ値を確認（読み取りのみ、管理者権限不要）"""
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


def check_dll_surrogate_status(name, clsid):
    """DLL Surrogate設定状態を確認"""
    import winreg

    print(f"\n--- {name} ({clsid}) ---")

    all_ok = True
    issues = []

    # 必要なレジストリ設定
    checks = [
        (f"Wow6432Node\\CLSID\\{clsid}", "AppID", clsid, "32bit CLSID AppID"),
        (f"Wow6432Node\\AppID\\{clsid}", "DllSurrogate", "", "32bit AppID DllSurrogate"),
        (f"AppID\\{clsid}", "DllSurrogate", "", "64bit AppID DllSurrogate"),
        (f"CLSID\\{clsid}", "AppID", clsid, "64bit CLSID AppID"),
    ]

    for path, value_name, expected, desc in checks:
        exists, value = check_registry_value(winreg.HKEY_CLASSES_ROOT, path, value_name)

        if exists and value == expected:
            print(f"  [OK] {desc}")
        else:
            all_ok = False
            if exists:
                print(f"  [NG] {desc}: got={value!r}, expected={expected!r}")
            else:
                print(f"  [NG] {desc}: 未設定")
            issues.append(desc)

    # RunAs 競合チェック
    for prefix in ["", "Wow6432Node\\"]:
        path = f"{prefix}AppID\\{clsid}"
        exists, value = check_registry_value(winreg.HKEY_CLASSES_ROOT, path, "RunAs")
        if exists:
            print(f"  [WARN] {path} に RunAs={value!r} あり（DllSurrogateと競合）")
            issues.append(f"RunAs conflict in {path}")
            all_ok = False

    return all_ok, issues


# レジストリ確認実行
registry_ok = True
all_issues = []

for name, info in COM_COMPONENTS.items():
    ok, issues = check_dll_surrogate_status(name, info["clsid"])
    registry_ok = registry_ok and ok
    all_issues.extend(issues)

if not registry_ok:
    print("\n" + "-" * 60)
    print("[WARNING] DLL Surrogate設定に問題があります")
    print("管理者権限で以下を実行してください:")
    print("  python scripts/check_dll_surrogate.py --fix")
    print("-" * 60)


# =============================================================================
# COM 接続テスト（管理者権限不要）
# =============================================================================
print("\n" + "=" * 60)
print("COM Connection Test")
print("=" * 60)

com_ok = True

try:
    import win32com.client

    for name, info in COM_COMPONENTS.items():
        progid = info["progid"]
        print(f"\n--- {name} ({progid}) ---")

        try:
            obj = win32com.client.Dispatch(progid)
            print(f"  [OK] COM接続成功")

            # 初期化テスト
            if name == "JV-Link":
                # JVInit は SID が必要なのでスキップ
                print(f"  [OK] オブジェクト生成確認")
            elif name == "NV-Link":
                rc = obj.NVInit("UNKNOWN")
                print(f"  [OK] NVInit: {rc}")
                obj.NVClose()
                print(f"  [OK] NVClose: 正常終了")

        except Exception as e:
            print(f"  [NG] エラー: {e}")
            com_ok = False

except ImportError:
    print("[SKIP] win32com not available")
    com_ok = False


# =============================================================================
# DuckDB テスト
# =============================================================================
print("\n" + "=" * 60)
print("DuckDB Test")
print("=" * 60)

print("\n--- Import Test ---")
try:
    import duckdb
    print(f"  [OK] DuckDB version: {duckdb.__version__}")
except ImportError as e:
    print(f"  [NG] Cannot import duckdb: {e}")
    sys.exit(1)

print("\n--- DuckDBDatabase Handler Test ---")
try:
    from src.database.duckdb_handler import DuckDBDatabase
    print("  [OK] DuckDBDatabase imported")
except ImportError as e:
    print(f"  [NG] Cannot import DuckDBDatabase: {e}")
    sys.exit(1)

print("\n--- Database Operations Test ---")
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "test.duckdb"

    config = {"path": str(db_path)}
    db = DuckDBDatabase(config)

    try:
        db.connect()
        print(f"  [OK] Connected to: {db_path.name}")

        # Create test table
        db.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100),
                value DOUBLE
            )
        """)
        print("  [OK] Created test table")

        # Insert data
        db.execute("INSERT INTO test_table VALUES (1, 'Alice', 100.5)")
        db.execute("INSERT INTO test_table VALUES (2, 'Bob', 200.75)")
        db.execute("INSERT INTO test_table VALUES (3, 'Charlie', 300.25)")
        print("  [OK] Inserted 3 rows")

        # Query data
        result = db.fetch_all("SELECT * FROM test_table ORDER BY id")
        print(f"  [OK] Query returned {len(result)} rows")

        # Aggregate query
        result = db.fetch_one("SELECT COUNT(*) as cnt, SUM(value) as total FROM test_table")
        cnt = result.get('cnt', result.get('count'))
        total = result.get('total')
        print(f"  [OK] Aggregate: count={cnt}, total={total}")

        db.disconnect()
        print("  [OK] Disconnected")

    except Exception as e:
        print(f"  [NG] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n--- Schema Import Test ---")
try:
    from src.database.schema_jravan import JRAVAN_SCHEMAS
    print(f"  [OK] JRA-VAN tables defined: {len(JRAVAN_SCHEMAS)}")
except Exception as e:
    print(f"  [NG] ERROR: {e}")
    sys.exit(1)


# =============================================================================
# 結果サマリー
# =============================================================================
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

print(f"  Registry:  {'OK' if registry_ok else 'NG (要修正)'}")
print(f"  COM:       {'OK' if com_ok else 'NG'}")
print(f"  DuckDB:    OK")

if registry_ok and com_ok:
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
else:
    print("\n" + "-" * 60)
    if not registry_ok:
        print("レジストリ設定を修正するには、管理者権限で実行:")
        print("  python scripts/check_dll_surrogate.py --fix")
    print("-" * 60)
    sys.exit(1)
