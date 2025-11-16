#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JV-Link COM オブジェクトの利用可能なメソッドを確認
"""
import win32com.client

try:
    # JV-Link COMオブジェクトを作成
    jvlink = win32com.client.Dispatch("JVDTLab.JVLink")

    print("=" * 80)
    print("JV-Link COM オブジェクトの利用可能なメソッド")
    print("=" * 80)
    print()

    # すべてのメソッドとプロパティを取得
    methods = [attr for attr in dir(jvlink) if not attr.startswith('_')]

    # カテゴリ別に分類
    jv_methods = [m for m in methods if m.startswith('JV')]
    other_methods = [m for m in methods if not m.startswith('JV')]

    print(f"JV- で始まるメソッド ({len(jv_methods)}個):")
    for method in sorted(jv_methods):
        print(f"  - {method}")

    print()
    print(f"その他のメソッド/プロパティ ({len(other_methods)}個):")
    for method in sorted(other_methods):
        print(f"  - {method}")

    print()
    print("=" * 80)
    print("重要なメソッドの確認")
    print("=" * 80)

    # 重要なメソッドの存在確認
    important_methods = [
        'JVInit',
        'JVSetServiceKey',
        'JVSetUIProperties',
        'JVOpen',
        'JVRead',
        'JVClose',
        'JVStatus',
    ]

    for method_name in important_methods:
        exists = hasattr(jvlink, method_name)
        status = "✓ 存在" if exists else "✗ 存在しない"
        print(f"  {method_name:20s}: {status}")

    print()
    print("=" * 80)

except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
