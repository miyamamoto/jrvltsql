#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RT_テーブル（リアルタイム用）をschema.pyに追加するスクリプト
"""
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.schema import SCHEMAS

# RT_テーブルのマッピング（src/realtime/updater.py:41-72 から）
RT_TABLE_MAPPINGS = {
    "RT_RA": "NL_RA",  # レース詳細
    "RT_SE": "NL_SE",  # 馬毎レース情報
    "RT_HR": "NL_HR",  # 払戻
    "RT_O1": "NL_O1",  # オッズ（単勝・複勝）
    "RT_O2": "NL_O2",  # オッズ（枠連）
    "RT_O3": "NL_O3",  # オッズ（馬連）
    "RT_O4": "NL_O4",  # オッズ（ワイド）
    "RT_O5": "NL_O5",  # オッズ（馬単）
    "RT_O6": "NL_O6",  # オッズ（３連複・３連単）
    "RT_H1": "NL_H1",  # 票数（単勝・複勝等）
    "RT_H6": "NL_H6",  # 票数（３連単）
    "RT_WH": "NL_WH",  # 馬場状態
    "RT_WE": "NL_WE",  # 開催情報
    "RT_DM": "NL_DM",  # データマイニング（タイム型）
    "RT_TM": "NL_TM",  # データマイニング（対戦型）
    "RT_AV": "NL_AV",  # 場外発売情報
    "RT_JC": "NL_JC",  # 騎手成績
    "RT_TC": "NL_TC",  # 調教師成績
    "RT_CC": "NL_CC",  # 競走馬成績
}


def generate_rt_tables():
    """RT_テーブルのスキーマを生成"""
    rt_schemas = {}

    for rt_table, nl_table in RT_TABLE_MAPPINGS.items():
        if nl_table not in SCHEMAS:
            print(f"Warning: {nl_table} not found in SCHEMAS")
            continue

        # NL_テーブルのスキーマをコピーしてRT_に変更
        nl_schema = SCHEMAS[nl_table]
        rt_schema = nl_schema.replace(f"CREATE TABLE IF NOT EXISTS {nl_table}",
                                       f"CREATE TABLE IF NOT EXISTS {rt_table}")

        rt_schemas[rt_table] = rt_schema
        print(f"OK Generated {rt_table} from {nl_table}")

    return rt_schemas


def append_to_schema_file(rt_schemas):
    """schema.pyにRT_テーブルを追加"""
    schema_file = project_root / "src" / "database" / "schema.py"

    # schema.pyを読み込む
    with open(schema_file, "r", encoding="utf-8") as f:
        content = f.read()

    # SCHEMAS辞書の最後を見つける（"}" の前）
    # 最後の "}" を見つける
    last_brace_pos = content.rfind("}")

    if last_brace_pos == -1:
        print("Error: Could not find SCHEMAS dictionary closing brace")
        return False

    # RT_テーブルを追加
    rt_entries = []
    for rt_table in sorted(RT_TABLE_MAPPINGS.keys()):
        if rt_table in rt_schemas:
            # スキーマを整形
            schema_lines = rt_schemas[rt_table].strip().split('\n')
            indented_schema = '\n'.join('        ' + line for line in schema_lines)
            rt_entries.append(f'    "{rt_table}": """\n{indented_schema}\n    """')

    # 新しいコンテンツを構築
    new_content = content[:last_brace_pos].rstrip()
    new_content += ",\n\n    # RT_ tables (Real-time data)\n"
    new_content += ",\n".join(rt_entries)
    new_content += "\n}\n"

    # ファイルに書き込む
    with open(schema_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nOK Added {len(rt_schemas)} RT_ tables to {schema_file}")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("RT_テーブル追加スクリプト")
    print("=" * 80)
    print()

    # RT_テーブルを生成
    rt_schemas = generate_rt_tables()
    print(f"\nGenerated {len(rt_schemas)} RT_ table schemas")
    print()

    # schema.pyに追加
    if append_to_schema_file(rt_schemas):
        print("\n" + "=" * 80)
        print("OK RT_テーブルの追加が完了しました")
        print("=" * 80)

        # 確認
        print("\n確認:")
        from importlib import reload
        import src.database.schema as schema_module
        reload(schema_module)

        total_tables = len(schema_module.SCHEMAS)
        rt_count = len([t for t in schema_module.SCHEMAS.keys() if t.startswith("RT_")])
        nl_count = len([t for t in schema_module.SCHEMAS.keys() if t.startswith("NL_")])

        print(f"  NL_テーブル: {nl_count}個")
        print(f"  RT_テーブル: {rt_count}個")
        print(f"  合計: {total_tables}個")
    else:
        print("\nNG RT_テーブルの追加に失敗しました")
        sys.exit(1)
