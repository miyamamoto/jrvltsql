"""Database compatibility helpers for cross-DB queries.

This module provides helper functions for writing database-agnostic code
that works across SQLite, PostgreSQL, and DuckDB.
"""

from typing import Any, Dict, List, Union


def safe_row_access(row: Union[Dict[str, Any], tuple, list], index_or_key: Union[int, str]) -> Any:
    """Database-agnostic row access.

    This function provides a unified interface for accessing row data
    regardless of whether the database returns dictionaries or tuples.

    Args:
        row: Row data (dict, tuple, or list)
        index_or_key: Column index (int) or column name (str)

    Returns:
        Value from the row

    Raises:
        TypeError: If row type is unsupported
        KeyError: If key doesn't exist in dictionary
        IndexError: If index is out of range

    Examples:
        >>> # Works with dict (SQLite, PostgreSQL)
        >>> row = {'table_name': 'nl_bn', 'count': 100}
        >>> safe_row_access(row, 'table_name')
        'nl_bn'
        >>> safe_row_access(row, 0)
        'nl_bn'

        >>> # Works with tuple (raw database cursors)
        >>> row = ('nl_bn', 100)
        >>> safe_row_access(row, 0)
        'nl_bn'
    """
    if isinstance(row, dict):
        if isinstance(index_or_key, int):
            # Access dict by integer index (get nth value)
            values = list(row.values())
            return values[index_or_key]
        else:
            # Access dict by key
            return row[index_or_key]

    elif isinstance(row, (tuple, list)):
        if isinstance(index_or_key, int):
            # Access tuple/list by index
            return row[index_or_key]
        else:
            # Cannot access tuple/list with string key
            raise TypeError(
                f"Cannot access tuple/list with key: {index_or_key}. "
                f"Use integer index instead."
            )
    else:
        raise TypeError(f"Unsupported row type: {type(row).__name__}")


def normalize_column_names(columns: List[str]) -> List[str]:
    """Normalize column names to lowercase for cross-DB compatibility.

    PostgreSQL automatically converts unquoted identifiers to lowercase.
    This function ensures consistent behavior across all databases.

    Args:
        columns: List of column names

    Returns:
        List of lowercase column names

    Examples:
        >>> normalize_column_names(['RecordSpec', 'DataKubun', 'MakeDate'])
        ['recordspec', 'datakubun', 'makedate']
    """
    return [col.lower() for col in columns]


def rows_to_dicts(rows: List[tuple], columns: List[str]) -> List[Dict[str, Any]]:
    """Convert list of tuples to list of dictionaries.

    Useful for databases that return raw tuples instead of dicts.

    Args:
        rows: List of row tuples
        columns: List of column names

    Returns:
        List of dictionaries

    Examples:
        >>> rows = [('nl_bn', 100), ('nl_br', 200)]
        >>> columns = ['table_name', 'count']
        >>> rows_to_dicts(rows, columns)
        [{'table_name': 'nl_bn', 'count': 100}, {'table_name': 'nl_br', 'count': 200}]
    """
    if not rows:
        return []

    # Normalize column names for PostgreSQL compatibility
    normalized_columns = normalize_column_names(columns)

    return [dict(zip(normalized_columns, row)) for row in rows]


def extract_column(rows: List[Dict[str, Any]], column: str, default: Any = None) -> List[Any]:
    """Extract single column from list of row dictionaries.

    Args:
        rows: List of row dictionaries
        column: Column name to extract
        default: Default value if column doesn't exist

    Returns:
        List of column values

    Examples:
        >>> rows = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
        >>> extract_column(rows, 'name')
        ['Alice', 'Bob']
        >>> extract_column(rows, 'missing', default='N/A')
        ['N/A', 'N/A']
    """
    column_lower = column.lower()
    result = []

    for row in rows:
        # Try lowercase key first (PostgreSQL compatibility)
        if column_lower in row:
            result.append(row[column_lower])
        # Try original key
        elif column in row:
            result.append(row[column])
        # Use default
        else:
            result.append(default)

    return result


def build_where_clause(conditions: Dict[str, Any], placeholder: str = "?") -> tuple:
    """Build SQL WHERE clause from dictionary of conditions.

    Args:
        conditions: Dictionary of column-value pairs
        placeholder: SQL placeholder style ('?' or '%s')

    Returns:
        Tuple of (where_clause, parameters)

    Examples:
        >>> conditions = {'DataKubun': '1', 'MakeDate': '20241101'}
        >>> build_where_clause(conditions)
        ('WHERE DataKubun = ? AND MakeDate = ?', ('1', '20241101'))

        >>> build_where_clause(conditions, placeholder='%s')
        ('WHERE DataKubun = %s AND MakeDate = %s', ('1', '20241101'))
    """
    if not conditions:
        return ("", ())

    clauses = []
    parameters = []

    for column, value in conditions.items():
        clauses.append(f"{column} = {placeholder}")
        parameters.append(value)

    where_clause = "WHERE " + " AND ".join(clauses)
    return (where_clause, tuple(parameters))


def get_table_record_count(db, table_name: str) -> int:
    """Get record count for a table (database-agnostic).

    Args:
        db: Database handler instance
        table_name: Name of table

    Returns:
        Number of records in table

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({'path': 'test.db'})
        >>> with db:
        ...     count = get_table_record_count(db, 'nl_bn')
        ...     print(f"Table has {count} records")
    """
    sql = f"SELECT COUNT(*) as count FROM {table_name}"
    result = db.fetch_one(sql)

    if result:
        # Try both 'count' and 'COUNT' (case-insensitive)
        return result.get('count', result.get('COUNT', 0))
    return 0


def get_all_tables(db, schema: str = None) -> List[str]:
    """Get list of all tables (database-agnostic).

    Args:
        db: Database handler instance
        schema: Optional schema name (PostgreSQL only)

    Returns:
        List of table names

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({'path': 'test.db'})
        >>> with db:
        ...     tables = get_all_tables(db)
        ...     print(f"Found {len(tables)} tables")
    """
    db_type = type(db).__name__

    if db_type == 'SQLiteDatabase':
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        result = db.fetch_all(sql)
        return extract_column(result, 'name')

    elif db_type == 'PostgreSQLDatabase':
        if schema:
            sql = "SELECT tablename FROM pg_tables WHERE schemaname = ?"
            result = db.fetch_all(sql, (schema,))
        else:
            sql = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            result = db.fetch_all(sql)
        return extract_column(result, 'tablename')

    elif db_type in ('DuckDBDatabase', 'OptimizedDuckDBDatabase'):
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        result = db.fetch_all(sql)
        return extract_column(result, 'table_name')

    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def format_table_stats(stats: Dict[str, int], max_tables: int = None) -> str:
    """Format table statistics as readable string.

    Args:
        stats: Dictionary mapping table names to record counts
        max_tables: Maximum number of tables to display (None = all)

    Returns:
        Formatted string

    Examples:
        >>> stats = {'nl_bn': 100, 'nl_br': 200, 'nl_ck': 1041}
        >>> print(format_table_stats(stats, max_tables=2))
        Table                             Records
        ================================================================================
        nl_ck                               1,041
        nl_br                                 200
        ... (1 more table)
    """
    if not stats:
        return "No tables found."

    # Sort by record count (descending)
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

    # Limit number of tables if specified
    if max_tables:
        displayed = sorted_stats[:max_tables]
        remaining = len(sorted_stats) - max_tables
    else:
        displayed = sorted_stats
        remaining = 0

    # Calculate total
    total_records = sum(stats.values())

    # Format output
    lines = []
    lines.append("Table                             Records")
    lines.append("=" * 80)

    for table, count in displayed:
        lines.append(f"{table:<30} {count:>12,}")

    if remaining > 0:
        lines.append(f"... ({remaining} more tables)")

    lines.append("=" * 80)
    lines.append(f"Total: {len(stats)} tables, {total_records:,} records")

    return "\n".join(lines)
