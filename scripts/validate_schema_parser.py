#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Schema/Parser Validation Script

スキーマとパーサーの整合性を自動検証するスクリプト。
全38パーサーのフィールド出力と全58テーブルのカラム定義を比較し、
不一致を検出してレポートを生成します。

Usage:
    python scripts/validate_schema_parser.py
    python scripts/validate_schema_parser.py --json
    python scripts/validate_schema_parser.py --verbose
"""

import argparse
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.parser.factory import ALL_RECORD_TYPES
from src.database.schema import SCHEMAS


class SchemaParserValidator:
    """スキーマとパーサーの整合性を検証するクラス"""

    def __init__(self):
        self.all_record_types = ALL_RECORD_TYPES
        self.schemas = SCHEMAS
        self.verbose = False

        # レコードタイプからテーブル名へのマッピング
        self.record_type_to_table_map = self._build_table_mapping()

    def _build_table_mapping(self) -> Dict[str, str]:
        """レコードタイプとテーブル名のマッピングを構築"""
        mapping = {}

        # NL_ tables (基本は "NL_" + record_type)
        for record_type in self.all_record_types:
            table_name = f"NL_{record_type}"
            if table_name in self.schemas:
                mapping[record_type] = table_name

        # RT_ tables (速報データ)
        # Note: RT_RC is intentionally different format (騎手変更情報) from NL_RC (コースレコード)
        # So we exclude RT_RC from validation since it uses a different schema by design
        rt_types = ['RA', 'SE', 'HR', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6',
                    'H1', 'H6', 'WE', 'WH', 'JC', 'CC', 'TC', 'TM', 'DM', 'AV']
        # RT_RC excluded: uses different format (騎手変更情報 via JVRTOpen 0B41)
        for record_type in rt_types:
            rt_table_name = f"RT_{record_type}"
            rt_record_type = f"RT_{record_type}"
            if rt_table_name in self.schemas:
                mapping[rt_record_type] = rt_table_name

        return mapping

    def get_parser_fields(self, record_type: str) -> Set[str]:
        """パーサーから出力フィールドのリストを取得

        Args:
            record_type: レコードタイプ（例: "RA", "SE"）

        Returns:
            パーサーが出力するフィールド名のセット
        """
        try:
            # RT_プレフィックスがある場合は除去してパーサーを取得
            parser_type = record_type.replace("RT_", "")

            # パーサーモジュールを動的にインポート
            module_name = f"src.parser.{parser_type.lower()}_parser"
            class_name = f"{parser_type.upper()}Parser"

            module = importlib.import_module(module_name)
            parser_class = getattr(module, class_name)

            # パーサーのインスタンスを作成
            parser = parser_class()
            fields = set()

            # パターン1: BaseParserを継承している場合
            # _define_fields()メソッドを持つかチェック
            if hasattr(parser, '_define_fields'):
                field_defs = parser._define_fields()
                for field_def in field_defs:
                    # FieldDefオブジェクトからフィールド名を取得
                    if hasattr(field_def, 'name'):
                        fields.add(field_def.name)
                    elif hasattr(field_def, '__iter__') and len(field_def) > 0:
                        # タプルの場合は最初の要素がフィールド名
                        fields.add(field_def[0])

            # パターン2: parse()メソッドに直接フィールド定義がある場合
            elif hasattr(parser, 'parse'):
                # parse()メソッドのソースコードを取得してフィールド名を抽出
                source = inspect.getsource(parser.parse)

                # コメント行を除去（#で始まる部分を除去）
                lines = source.split('\n')
                non_comment_lines = []
                for line in lines:
                    # インラインコメントも含めて除去
                    comment_pos = line.find('#')
                    if comment_pos >= 0:
                        line = line[:comment_pos]
                    non_comment_lines.append(line)
                source = '\n'.join(non_comment_lines)

                # result["FieldName"] = ... のパターンを検索
                pattern = r'result\["([^"]+)"\]'
                matches = re.findall(pattern, source)
                fields.update(matches)

                # f-string パターンも検索: result[f"...{i}..."]
                # 例: result[f"Ketto3InfoHansyokuNum{i}"]
                fstring_pattern = r'result\[f"([^"]+)\{([^}]+)\}([^"]*)"\]'
                fstring_matches = re.findall(fstring_pattern, source)
                for prefix, var, suffix in fstring_matches:
                    # ループ変数の範囲を推定（一般的なパターン）
                    # for i in range(1, 15): などを検出
                    range_pattern = rf'for\s+{var}\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
                    range_match = re.search(range_pattern, source)
                    if range_match:
                        start = int(range_match.group(1))
                        end = int(range_match.group(2))
                        for idx in range(start, end):
                            fields.add(f"{prefix}{idx}{suffix}")

            return fields

        except Exception as e:
            if self.verbose:
                print(f"Warning: Failed to load parser for {record_type}: {e}")
            return set()

    def get_schema_columns(self, table_name: str) -> Set[str]:
        """スキーマからカラム名のリストを取得

        Args:
            table_name: テーブル名（例: "NL_RA", "RT_SE"）

        Returns:
            スキーマに定義されたカラム名のセット
        """
        if table_name not in self.schemas:
            return set()

        schema_sql = self.schemas[table_name]
        columns = set()

        # CREATE TABLE文からカラム名を抽出
        # パターン: カラム名 TYPE形式を検索
        # PRIMARY KEY, CREATE TABLE等の予約語は除外
        lines = schema_sql.split('\n')
        for line in lines:
            line = line.strip()

            # コメント行やCREATE TABLE行、PRIMARY KEY行はスキップ
            if (not line or
                line.startswith('--') or
                'CREATE TABLE' in line or
                'PRIMARY KEY' in line or
                line == ')'):
                continue

            # カラム定義行を解析
            # 形式: ColumnName TYPE [constraints],
            match = re.match(r'(\w+)\s+(TEXT|INTEGER|REAL)', line)
            if match:
                column_name = match.group(1)
                columns.add(column_name)

        return columns

    def compare_parser_schema(self, record_type: str) -> Dict:
        """パーサーとスキーマを比較

        Args:
            record_type: レコードタイプ

        Returns:
            比較結果の辞書
        """
        # テーブル名を取得
        table_name = self.record_type_to_table_map.get(record_type)
        if not table_name:
            return {
                'record_type': record_type,
                'status': 'NO_TABLE_MAPPING',
                'message': f'No table mapping found for {record_type}'
            }

        # パーサーフィールドとスキーマカラムを取得
        parser_fields = self.get_parser_fields(record_type)
        schema_columns = self.get_schema_columns(table_name)

        if not parser_fields:
            return {
                'record_type': record_type,
                'table_name': table_name,
                'status': 'NO_PARSER',
                'message': f'Failed to load parser for {record_type}'
            }

        if not schema_columns:
            return {
                'record_type': record_type,
                'table_name': table_name,
                'status': 'NO_SCHEMA',
                'message': f'No schema found for table {table_name}'
            }

        # 大文字小文字を無視して比較
        parser_fields_lower = {f.lower(): f for f in parser_fields}
        schema_columns_lower = {c.lower(): c for c in schema_columns}

        # 差分を計算
        extra_in_parser = []
        missing_in_parser = []

        for field_lower, field_original in parser_fields_lower.items():
            if field_lower not in schema_columns_lower:
                extra_in_parser.append(field_original)

        for column_lower, column_original in schema_columns_lower.items():
            if column_lower not in parser_fields_lower:
                missing_in_parser.append(column_original)

        # ステータス判定
        if extra_in_parser or missing_in_parser:
            status = 'MISMATCH'
        else:
            status = 'MATCH'

        return {
            'record_type': record_type,
            'table_name': table_name,
            'status': status,
            'parser_fields_count': len(parser_fields),
            'schema_columns_count': len(schema_columns),
            'extra_in_parser': sorted(extra_in_parser),
            'missing_in_parser': sorted(missing_in_parser),
        }

    def validate_all(self) -> Dict:
        """全パーサーとスキーマを検証

        Returns:
            検証結果の辞書
        """
        results = []
        total_parsers = 0
        total_tables = 0
        matched = 0
        mismatched = 0
        no_mapping = 0
        errors = 0

        # 全レコードタイプを検証
        all_types_to_check = set(self.all_record_types)

        # RT_タイプも追加
        # Note: RT_RC excluded - uses different format (騎手変更情報 via JVRTOpen 0B41)
        rt_types = ['RA', 'SE', 'HR', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6',
                    'H1', 'H6', 'WE', 'WH', 'JC', 'CC', 'TC', 'TM', 'DM', 'AV']
        for rt_type in rt_types:
            all_types_to_check.add(f"RT_{rt_type}")

        for record_type in sorted(all_types_to_check):
            result = self.compare_parser_schema(record_type)
            results.append(result)

            if result['status'] == 'MATCH':
                matched += 1
                total_parsers += 1
            elif result['status'] == 'MISMATCH':
                mismatched += 1
                total_parsers += 1
            elif result['status'] == 'NO_TABLE_MAPPING':
                no_mapping += 1
            else:
                errors += 1

        total_tables = len(self.schemas)

        return {
            'summary': {
                'total_parsers': total_parsers,
                'total_tables': total_tables,
                'matched': matched,
                'mismatched': mismatched,
                'no_mapping': no_mapping,
                'errors': errors,
            },
            'details': results,
        }

    def print_report(self, validation_result: Dict, show_all: bool = False):
        """検証結果を表示

        Args:
            validation_result: validate_all()の戻り値
            show_all: 一致したパーサーも含めて全て表示
        """
        summary = validation_result['summary']
        details = validation_result['details']

        print("=" * 60)
        print("Schema/Parser Validation Report")
        print("=" * 60)
        print(f"Total Parsers:  {summary['total_parsers']}")
        print(f"Total Tables:   {summary['total_tables']}")
        print(f"Matched:        {summary['matched']}")
        print(f"Mismatched:     {summary['mismatched']}")
        print(f"No Mapping:     {summary['no_mapping']}")
        print(f"Errors:         {summary['errors']}")
        print("=" * 60)
        print()

        # 不一致の詳細を表示
        mismatch_count = 0
        for result in details:
            if result['status'] == 'MISMATCH':
                mismatch_count += 1
                self._print_mismatch_detail(result)

        if mismatch_count == 0:
            print("No mismatches found!")
            print()

        # 全て表示モードの場合は一致したパーサーも表示
        if show_all:
            print("\n" + "=" * 60)
            print("Matched Parsers")
            print("=" * 60)
            for result in details:
                if result['status'] == 'MATCH':
                    print(f"[MATCH] {result['record_type']}:")
                    print(f"  Table: {result['table_name']}")
                    print(f"  Fields: {result['parser_fields_count']}")
                    print()

        # エラーやマッピングなしの場合も表示
        if summary['errors'] > 0 or summary['no_mapping'] > 0:
            print("\n" + "=" * 60)
            print("Warnings")
            print("=" * 60)
            for result in details:
                if result['status'] in ['NO_PARSER', 'NO_SCHEMA', 'NO_TABLE_MAPPING']:
                    print(f"[{result['status']}] {result['record_type']}")
                    if 'table_name' in result:
                        print(f"  Table: {result['table_name']}")
                    print(f"  Message: {result.get('message', 'N/A')}")
                    print()

    def _print_mismatch_detail(self, result: Dict):
        """不一致の詳細を表示"""
        print(f"[MISMATCH] {result['record_type']}:")
        print(f"  Table:          {result['table_name']}")
        print(f"  Parser fields:  {result['parser_fields_count']}")
        print(f"  Schema columns: {result['schema_columns_count']}")

        if result['extra_in_parser']:
            print(f"  Extra in parser ({len(result['extra_in_parser'])}):")
            for field in result['extra_in_parser']:
                print(f"    - {field}")

        if result['missing_in_parser']:
            print(f"  Missing in parser ({len(result['missing_in_parser'])}):")
            for field in result['missing_in_parser']:
                print(f"    - {field}")

        print()

    def export_json(self, validation_result: Dict, output_path: str):
        """検証結果をJSONで出力

        Args:
            validation_result: validate_all()の戻り値
            output_path: 出力ファイルパス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(validation_result, f, ensure_ascii=False, indent=2)
        print(f"Validation results exported to: {output_path}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='Validate schema and parser consistency'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Export results to JSON file'
    )
    parser.add_argument(
        '--output',
        default='validation_report.json',
        help='JSON output file path (default: validation_report.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose output including all matched parsers'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Show all parsers including matched ones'
    )

    args = parser.parse_args()

    # 検証実行
    validator = SchemaParserValidator()
    validator.verbose = args.verbose

    print("Validating schema and parser consistency...")
    print()

    result = validator.validate_all()

    # レポート表示
    validator.print_report(result, show_all=args.all)

    # JSON出力
    if args.json:
        validator.export_json(result, args.output)

    # 終了コード
    if result['summary']['mismatched'] > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
