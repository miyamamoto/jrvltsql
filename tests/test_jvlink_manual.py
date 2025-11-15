#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""手動JV-Linkテストスクリプト

このスクリプトはJV-Linkの動作を段階的にテストします。
サービスキーなしでも一部の機能テストが可能です。
"""

import sys
import os
import traceback

# Windows環境でのUTF-8出力設定
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("=" * 70)
print("JV-Link 手動テストスクリプト")
print("=" * 70)
print()

# Step 1: pywin32のインポート確認
print("Step 1: pywin32モジュールの確認...")
try:
    import win32com.client
    print("[OK] pywin32モジュールが正常にインポートされました")
except ImportError as e:
    print(f"[ERROR] pywin32がインストールされていません: {e}")
    sys.exit(1)
print()

# Step 2: JV-Link COMオブジェクトの作成
print("Step 2: JV-Link COMオブジェクトの作成...")
try:
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
    print("[OK] JV-Link COMオブジェクトが正常に作成されました")
    print(f"  オブジェクト: {jvlink}")
except Exception as e:
    print(f"[ERROR] JV-Link COMオブジェクトの作成に失敗: {e}")
    print()
    print("【対処方法】")
    print("1. JV-Linkがインストールされているか確認してください")
    print("2. JRA-VAN DataLabソフトウェアを起動してみてください")
    print("3. Windowsのプログラム一覧で「JV-Link」を探してください")
    sys.exit(1)
print()

# Step 3: JV-Link初期化テスト
print("Step 3: JV-Link初期化テスト...")
print("  注意: サービスキーが必要な場合があります")
print()

# サービスキー入力
import os
service_key = os.environ.get("JVLINK_SERVICE_KEY", "")

if not service_key:
    print("環境変数 JVLINK_SERVICE_KEY が設定されていません。")
    print()
    choice = input("サービスキーを入力しますか？ (y/n): ").strip().lower()

    if choice == 'y':
        from getpass import getpass
        service_key = getpass("JV-Linkサービスキーを入力してください: ").strip()
        if service_key:
            print("[OK] サービスキーを取得しました")
        else:
            print("サービスキーが入力されませんでした。初期化テストをスキップします。")
    else:
        print("サービスキーなしで初期化を試みます（失敗する可能性があります）")
        service_key = ""
else:
    print(f"[OK] 環境変数からサービスキーを取得: {service_key[:4]}***")

print()

# JV_Init呼び出し
print("JV_Init() を呼び出しています...")
try:
    ret = jvlink.JVInit(service_key)
    print(f"[OK] JV_Init() 実行成功")
    print(f"  戻り値: {ret}")

    # 戻り値の解釈
    if ret == 0:
        print("  -> 0: 正常終了")
    elif ret == -1:
        print("  -> -1: JV-Link未起動エラー（JV-Linkを起動してください）")
    elif ret == -2:
        print("  -> -2: サービスキーが設定されていません")
    elif ret == -3:
        print("  -> -3: サービスキーが不正です")
    elif ret == -4:
        print("  -> -4: サーバーエラー")
    else:
        print(f"  -> {ret}: その他のエラー")

    if ret == 0:
        print()
        print("[SUCCESS] JV-Link初期化成功！")
        print()
        print("次のステップ:")
        print("1. 統合テストを実行:")
        print("   export JVLINK_SERVICE_KEY='あなたのキー'")
        print("   python run_integration_tests.py")
        print()
        print("2. または個別にテスト:")
        print("   pytest tests/integration/test_jvlink_real.py -v -s")

except Exception as e:
    print(f"[ERROR] JV_Init()の呼び出しに失敗: {e}")
    print()
    print("詳細なエラー情報:")
    traceback.print_exc()
    print()
    print("【よくあるエラーと対処方法】")
    print("1. 'JVInit' のアトリビュート取得エラー")
    print("   → JV-Linkのバージョンが古い可能性があります")
    print()
    print("2. タイムアウトエラー")
    print("   → インターネット接続を確認してください")
    print()
    print("3. サービスキーエラー")
    print("   → JRA-VANの契約状況を確認してください")

print()
print("=" * 70)
print("テスト完了")
print("=" * 70)
