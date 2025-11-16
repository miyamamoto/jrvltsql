#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
プロジェクトから不要なファイルを削除
"""
import os
import shutil
from pathlib import Path

# プロジェクトルート
project_root = Path(__file__).parent.parent

# 削除対象のディレクトリ
dirs_to_remove = [
    "htmlcov",           # カバレッジレポート
    ".specify",          # 仕様メモリー
]

# 削除対象のファイル（パターン）
files_to_remove = [
    ".coverage",                     # カバレッジデータ
    "data/test_load.duckdb.wal",     # WALファイル
    "data/keiba_2024.duckdb",        # 古いDB
    "data/keiba_2025.duckdb",        # 古いDB
    "data/jltsql.duckdb",            # 古いDB（keiba.duckdbに統合）
    "FINAL_REPORT.md",               # 古いレポート
]

# ログファイル（古いテストログのみ）
log_files_to_remove = [
    "logs/fetch_corrected_test.log",
    "logs/fetch_diff_october.log",
    "logs/fetch_final_test.log",
    "logs/fetch_october.log",
    "logs/fetch_october_fixed.log",
    "logs/fetch_safe_schema_test.log",
    "logs/fetch_setup_october.log",
    "logs/fetch_test.log",
    "logs/fetch_test_minimal.log",
    "logs/ra_debug_output.txt",
    "logs/jltsql.log",               # 空
    "logs/jltsql_daily.log",         # 空
    "logs/jltsql_error.log",         # 空
    "logs/jltsql_error_daily.log",   # 空
]

# 一時スクリプト（不要なテストスクリプト）
temp_scripts = [
    "scripts/analyze_empty_tables.py",
    "scripts/comprehensive_data_load.py",
    "scripts/load_month_data.py",
    "scripts/load_year_data.py",
    "scripts/test_bldn_comprehensive.py",
    "scripts/run_integration_tests.py",
    "scripts/setup_full_data.py",
]

def main():
    print("=" * 80)
    print("プロジェクトクリーンアップ")
    print("=" * 80)

    total_size_saved = 0

    # ディレクトリ削除
    print("\n[ディレクトリ削除]")
    for dir_name in dirs_to_remove:
        dir_path = project_root / dir_name
        if dir_path.exists():
            size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            shutil.rmtree(dir_path)
            total_size_saved += size
            print(f"  ✓ {dir_name}/ を削除 ({size / 1024 / 1024:.2f} MB)")
        else:
            print(f"  - {dir_name}/ は存在しない")

    # ファイル削除
    print("\n[ファイル削除]")
    all_files = files_to_remove + log_files_to_remove + temp_scripts

    for file_path_str in all_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            size = file_path.stat().st_size
            file_path.unlink()
            total_size_saved += size
            print(f"  ✓ {file_path_str} を削除 ({size / 1024:.2f} KB)")
        else:
            print(f"  - {file_path_str} は存在しない")

    # .gitignoreに追加すべき項目を確認
    print("\n[.gitignore 確認]")
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            gitignore_content = f.read()

        needed_entries = [
            "htmlcov/",
            ".coverage",
            "*.duckdb.wal",
            "logs/*.log",
            ".specify/",
        ]

        missing_entries = [e for e in needed_entries if e not in gitignore_content]
        if missing_entries:
            print("  ! 以下を.gitignoreに追加することを推奨:")
            for entry in missing_entries:
                print(f"    - {entry}")
        else:
            print("  ✓ .gitignore は適切に設定されています")

    print("\n" + "=" * 80)
    print(f"✅ クリーンアップ完了！合計 {total_size_saved / 1024 / 1024:.2f} MB を削除")
    print("=" * 80)

    # 残りのファイルサイズを表示
    print("\n[残りのデータベースファイル]")
    db_files = list((project_root / "data").glob("*.duckdb"))
    for db_file in db_files:
        size = db_file.stat().st_size
        print(f"  {db_file.name}: {size / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
