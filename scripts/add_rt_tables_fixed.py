#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RT_テーブルをschema.pyに追加（修正版）
"""
import sys
import re
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema import SCHEMAS

# RT_テーブルマッピング
RT_MAPPINGS = {
    "RT_RA": "NL_RA", "RT_SE": "NL_SE", "RT_HR": "NL_HR",
    "RT_O1": "NL_O1", "RT_O2": "NL_O2", "RT_O3": "NL_O3",
    "RT_O4": "NL_O4", "RT_O5": "NL_O5", "RT_O6": "NL_O6",
    "RT_H1": "NL_H1", "RT_H6": "NL_H6",
    "RT_WH": "NL_WH", "RT_WE": "NL_WE",
    "RT_DM": "NL_DM", "RT_TM": "NL_TM",
    "RT_AV": "NL_AV", "RT_JC": "NL_JC", "RT_TC": "NL_TC", "RT_CC": "NL_CC"
}


def main():
    schema_file = project_root / "src" / "database" / "schema.py"

    print("Reading schema.py...")
    with open(schema_file, "r", encoding="utf-8") as f:
        content = f.read()

    # SCHEMAS = { で始まり、その後の } で終わる部分を見つける
    # パターン: SCHEMAS = { ... }
    pattern = r'(SCHEMAS\s*=\s*\{.*?)\n\}'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("NG: Could not find SCHEMAS dictionary")
        return 1

    # SCHEMAS辞書の内容（閉じ括弧の前まで）
    schemas_content = match.group(1)

    # RT_テーブルを生成
    rt_entries = []
    for rt_table in sorted(RT_MAPPINGS.keys()):
        nl_table = RT_MAPPINGS[rt_table]
        if nl_table not in SCHEMAS:
            print(f"Warning: {nl_table} not found")
            continue

        # NL_テーブルのスキーマをRT_に変換
        rt_schema = SCHEMAS[nl_table].replace(
            f"CREATE TABLE IF NOT EXISTS {nl_table}",
            f"CREATE TABLE IF NOT EXISTS {rt_table}"
        )

        # Python文字列リテラルとして整形
        rt_entries.append(f'    "{rt_table}": """{rt_schema}"""')
        print(f"OK: Generated {rt_table}")

    # 新しいSCHEMAS辞書を構築
    new_schemas = schemas_content + ",\n\n    # RT_ tables (Real-time data)\n"
    new_schemas += ",\n".join(rt_entries)
    new_schemas += "\n}"

    # ファイル全体を更新
    new_content = content[:match.start()] + new_schemas + content[match.end():]

    # 書き込む
    print("\nWriting updated schema.py...")
    with open(schema_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"OK: Added {len(rt_entries)} RT_ tables to schema.py")

    # 確認
    print("\nVerifying...")
    from importlib import reload
    import src.database.schema as schema_module
    reload(schema_module)

    total = len(schema_module.SCHEMAS)
    rt_count = len([t for t in schema_module.SCHEMAS if t.startswith("RT_")])
    nl_count = len([t for t in schema_module.SCHEMAS if t.startswith("NL_")])

    print(f"  NL_ tables: {nl_count}")
    print(f"  RT_ tables: {rt_count}")
    print(f"  Total: {total}")

    if rt_count == 19:
        print("\nOK: Successfully added all 19 RT_ tables!")
        return 0
    else:
        print(f"\nNG: Expected 19 RT_ tables, got {rt_count}")
        return 1


if __name__ == "__main__":
    print("=" * 80)
    print("RT_テーブル追加スクリプト（修正版）")
    print("=" * 80)
    print()

    sys.exit(main())
