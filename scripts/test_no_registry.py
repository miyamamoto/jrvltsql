#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
レジストリーを使わない実装のテスト
"""
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.jvlink.wrapper import JVLinkWrapper
from src.utils.config import load_config

def test_service_key_from_config():
    """設定ファイルからサービスキーを読み込んでテスト"""
    print("=" * 80)
    print("レジストリーを使わない実装のテスト")
    print("=" * 80)
    print()

    # 設定ファイルからサービスキーを読み込む
    config = load_config()
    service_key = config.get("jvlink.service_key")

    if not service_key:
        print("❌ エラー: config/config.yaml に service_key が設定されていません")
        print()
        print("設定方法:")
        print("  1. config/config.yaml を開く")
        print("  2. jvlink.service_key にサービスキーを設定")
        print()
        print("または環境変数で設定:")
        print("  set JVLINK_SERVICE_KEY=XXXX-XXXX-XXXX-XXXX-X")
        return False

    # 環境変数でオーバーライド可能
    if "${JVLINK_SERVICE_KEY}" in service_key:
        env_key = os.environ.get("JVLINK_SERVICE_KEY")
        if env_key:
            service_key = env_key
            print(f"✓ 環境変数からサービスキーを読み込みました")
        else:
            print("❌ エラー: JVLINK_SERVICE_KEY 環境変数が設定されていません")
            return False
    else:
        print(f"✓ 設定ファイルからサービスキーを読み込みました")

    print(f"  サービスキー: {service_key[:10]}...")
    print()

    # JVLinkWrapper をテスト
    try:
        print("[テスト 1] JVLinkWrapper の初期化")
        wrapper = JVLinkWrapper(sid="TEST")
        print("  ✓ JVLinkWrapper の作成成功")

        print()
        print("[テスト 2] JVSetServiceKey の呼び出し")
        result = wrapper.jv_set_service_key(service_key)
        if result == 0:
            print("  ✓ サービスキーの設定成功")
        else:
            print(f"  ❌ サービスキーの設定失敗 (code: {result})")
            return False

        print()
        print("[テスト 3] JVInit の呼び出し")
        result = wrapper.jv_init()
        if result == 0:
            print("  ✓ JV-Link初期化成功")
        else:
            print(f"  ❌ JV-Link初期化失敗 (code: {result})")
            return False

        print()
        print("=" * 80)
        print("✅ すべてのテストが成功しました！")
        print("=" * 80)
        print()
        print("レジストリーを使わずに、設定ファイルからサービスキーを設定できました。")
        print("この実装では、Windowsレジストリーへの依存を完全に排除しています。")
        print()
        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_key_parameter():
    """パラメータとしてサービスキーを渡すテスト"""
    print()
    print("=" * 80)
    print("[追加テスト] jv_init() にサービスキーを直接渡す")
    print("=" * 80)
    print()

    config = load_config()
    service_key = config.get("jvlink.service_key")

    if "${JVLINK_SERVICE_KEY}" in service_key:
        service_key = os.environ.get("JVLINK_SERVICE_KEY", service_key)

    try:
        wrapper = JVLinkWrapper(sid="TEST2")
        print("  ✓ JVLinkWrapper の作成成功")

        # jv_init() に直接サービスキーを渡す
        result = wrapper.jv_init(service_key=service_key)
        if result == 0:
            print("  ✓ サービスキーをパラメータとして渡して初期化成功")
        else:
            print(f"  ❌ 初期化失敗 (code: {result})")
            return False

        print()
        print("✅ パラメータ渡しのテストも成功しました！")
        return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

if __name__ == "__main__":
    success1 = test_service_key_from_config()
    success2 = test_service_key_parameter()

    if success1 and success2:
        print()
        print("=" * 80)
        print("🎉 レジストリーを使わない実装のテストがすべて成功しました！")
        print("=" * 80)
        sys.exit(0)
    else:
        print()
        print("=" * 80)
        print("❌ テストが失敗しました")
        print("=" * 80)
        sys.exit(1)
