"""Schema type extraction utilities for JRVLTSQL.

This module provides functions to extract column types from CREATE TABLE statements
defined in schema.py, enabling type-safe data processing.
"""

import re
from typing import Dict, Optional

from src.database.schema import SCHEMAS

# キャッシュ（テーブル名 → カラム型マッピング）
_table_column_types_cache: Dict[str, Dict[str, str]] = {}

# コンパイル済み正規表現パターン
_column_pattern = re.compile(r'^\s*(\w+)\s+(INTEGER|BIGINT|REAL|TEXT)\s*[,)]?\s*$', re.MULTILINE)


def get_table_column_types(table_name: str) -> Dict[str, str]:
    """Get column name to type mapping for a specific table.

    Parses the CREATE TABLE statement from SCHEMAS dictionary and extracts
    column definitions, returning a mapping of column names to their SQL types.

    Args:
        table_name: Name of the table (e.g., "NL_RA", "RT_SE")

    Returns:
        Dictionary mapping column names to types (e.g., {"Year": "INTEGER", "JyoCD": "TEXT"})
        Returns empty dict if table not found or parsing fails.

    Examples:
        >>> types = get_table_column_types("NL_RA")
        >>> types["Year"]
        'INTEGER'
        >>> types["JyoCD"]
        'TEXT'
        >>> types["Kyori"]
        'INTEGER'
    """
    # キャッシュから取得
    if table_name in _table_column_types_cache:
        return _table_column_types_cache[table_name]

    if table_name not in SCHEMAS:
        return {}

    create_statement = SCHEMAS[table_name]
    column_types = {}

    # Match column definitions: column_name TYPE
    # Pattern matches lines like:
    #   Year INTEGER,
    #   JyoCD TEXT,
    #   Kyori INTEGER,
    #   Honsyokin1 REAL,
    #   Vote BIGINT,
    # But excludes PRIMARY KEY constraints

    for line in create_statement.split('\n'):
        # Skip PRIMARY KEY constraints
        if 'PRIMARY KEY' in line.upper():
            continue

        match = _column_pattern.match(line)
        if match:
            column_name = match.group(1)
            column_type = match.group(2)
            column_types[column_name] = column_type

    # キャッシュに保存
    _table_column_types_cache[table_name] = column_types
    return column_types


def get_column_type(table_name: str, column_name: str) -> Optional[str]:
    """Get the SQL type of a specific column in a table.

    Args:
        table_name: Name of the table (e.g., "NL_RA")
        column_name: Name of the column (e.g., "Year")

    Returns:
        SQL type string ("INTEGER", "REAL", or "TEXT"), or None if not found

    Examples:
        >>> get_column_type("NL_RA", "Year")
        'INTEGER'
        >>> get_column_type("NL_RA", "JyoCD")
        'TEXT'
        >>> get_column_type("NL_RA", "Honsyokin1")
        'REAL'
        >>> get_column_type("NL_RA", "NonExistent")
        None
    """
    column_types = get_table_column_types(table_name)
    return column_types.get(column_name)


def is_numeric_column(table_name: str, column_name: str) -> bool:
    """Check if a column has a numeric type (INTEGER, BIGINT, or REAL).

    Args:
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        True if column type is INTEGER, BIGINT, or REAL, False otherwise

    Examples:
        >>> is_numeric_column("NL_RA", "Year")
        True
        >>> is_numeric_column("NL_RA", "Kyori")
        True
        >>> is_numeric_column("NL_RA", "Honsyokin1")
        True
        >>> is_numeric_column("NL_RA", "JyoCD")
        False
    """
    column_type = get_column_type(table_name, column_name)
    return column_type in ("INTEGER", "BIGINT", "REAL")


def is_text_column(table_name: str, column_name: str) -> bool:
    """Check if a column has TEXT type.

    Args:
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        True if column type is TEXT, False otherwise

    Examples:
        >>> is_text_column("NL_RA", "JyoCD")
        True
        >>> is_text_column("NL_RA", "Hondai")
        True
        >>> is_text_column("NL_RA", "Year")
        False
    """
    column_type = get_column_type(table_name, column_name)
    return column_type == "TEXT"


def get_all_tables() -> list[str]:
    """Get list of all table names defined in SCHEMAS.

    Returns:
        List of table names

    Examples:
        >>> tables = get_all_tables()
        >>> "NL_RA" in tables
        True
        >>> "RT_SE" in tables
        True
    """
    return list(SCHEMAS.keys())


if __name__ == "__main__":
    # Test code demonstrating functionality
    print("=" * 60)
    print("Schema Type Extraction Test")
    print("=" * 60)

    # Test 1: Get column types for NL_RA
    print("\n[Test 1] NL_RA table column types:")
    nl_ra_types = get_table_column_types("NL_RA")
    print(f"Total columns: {len(nl_ra_types)}")
    print("\nSample columns:")
    sample_columns = ["RecordSpec", "Year", "MonthDay", "JyoCD", "Kyori", "Honsyokin1"]
    for col in sample_columns:
        col_type = nl_ra_types.get(col, "NOT FOUND")
        print(f"  {col:20s}: {col_type}")

    # Test 2: Get column types for NL_SE
    print("\n[Test 2] NL_SE table column types:")
    nl_se_types = get_table_column_types("NL_SE")
    print(f"Total columns: {len(nl_se_types)}")
    print("\nSample columns:")
    sample_columns = ["Year", "Umaban", "KettoNum", "Bamei", "Barei", "Futan", "Time", "Odds"]
    for col in sample_columns:
        col_type = nl_se_types.get(col, "NOT FOUND")
        print(f"  {col:20s}: {col_type}")

    # Test 3: Test helper functions
    print("\n[Test 3] Helper function tests:")
    test_cases = [
        ("NL_RA", "Year", "INTEGER"),
        ("NL_RA", "JyoCD", "TEXT"),
        ("NL_RA", "Honsyokin1", "REAL"),
        ("NL_SE", "Umaban", "INTEGER"),
        ("NL_SE", "Time", "REAL"),
    ]

    for table, column, expected_type in test_cases:
        actual_type = get_column_type(table, column)
        is_numeric = is_numeric_column(table, column)
        is_text = is_text_column(table, column)
        status = "OK" if actual_type == expected_type else "FAIL"
        print(f"  {status}: {table}.{column}")
        print(f"       Type: {actual_type} (expected: {expected_type})")
        print(f"       Numeric: {is_numeric}, Text: {is_text}")

    # Test 4: Verify PRIMARY KEY is excluded
    print("\n[Test 4] Verify PRIMARY KEY is not included:")
    for table in ["NL_RA", "NL_SE", "NL_UM"]:
        types = get_table_column_types(table)
        has_primary_key = "PRIMARY" in types or "KEY" in types
        status = "OK" if not has_primary_key else "FAIL"
        print(f"  {status}: {table} - PRIMARY KEY excluded: {not has_primary_key}")

    # Test 5: Table count
    print("\n[Test 5] Total tables in SCHEMAS:")
    all_tables = get_all_tables()
    print(f"  Total: {len(all_tables)} tables")
    print(f"  NL_* tables: {len([t for t in all_tables if t.startswith('NL_')])}")
    print(f"  RT_* tables: {len([t for t in all_tables if t.startswith('RT_')])}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
