"""Schema migration utilities.

Detects schema mismatches in existing tables and recreates them when needed.
This handles cases where table schemas have changed (e.g., NL_H1/NL_H6 went
from flat schema to full struct schema in PR #34) and existing databases have
the old column layout.

Strategy: DROP and recreate. Data loss is acceptable because quickstart
re-fetches everything from scratch.
"""

import re
from typing import Dict, Optional, Set

from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_columns_from_sql(create_sql: str) -> Optional[Set[str]]:
    """Extract column names from a CREATE TABLE SQL statement.

    Args:
        create_sql: SQL CREATE TABLE statement

    Returns:
        Set of column names, or None if parsing fails
    """
    # Find content between first ( and last )
    match = re.search(r'\((.+)\)', create_sql, re.DOTALL)
    if not match:
        return None

    body = match.group(1)

    # Remove PRIMARY KEY(...) and similar constraints with nested parens
    # before splitting by comma
    body = re.sub(r'PRIMARY\s+KEY\s*\([^)]*\)', '', body, flags=re.IGNORECASE)
    body = re.sub(r'UNIQUE\s*\([^)]*\)', '', body, flags=re.IGNORECASE)
    body = re.sub(r'FOREIGN\s+KEY\s*\([^)]*\)\s*REFERENCES\s*[^,)]*', '', body, flags=re.IGNORECASE)

    columns = set()
    for line in body.split(','):
        line = line.strip()
        if not line:
            continue
        # Skip remaining constraint keywords
        if line.upper().startswith(('CONSTRAINT', 'CHECK')):
            continue
        # First token is the column name (possibly quoted)
        token = line.split()[0].strip('`"[]')
        if token:
            columns.add(token)
    return columns


def migrate_table_if_needed(db: BaseDatabase, table_name: str, schema_sql: str) -> bool:
    """Check if an existing table's columns match the expected schema.

    If the table exists but has different columns, DROP and recreate it.

    Args:
        db: Database instance (must be connected)
        table_name: Table name to check
        schema_sql: The CREATE TABLE SQL for the expected schema

    Returns:
        True if migration (DROP+recreate) was performed, False otherwise
    """
    if not db.table_exists(table_name):
        return False

    expected_columns = _extract_columns_from_sql(schema_sql)
    if expected_columns is None:
        logger.warning(f"Could not parse schema SQL for {table_name}, skipping migration check")
        return False

    # Get existing columns via PRAGMA
    existing_info = db.fetch_all(f"PRAGMA table_info({table_name})")
    existing_columns = {row['name'] for row in existing_info}

    if existing_columns == expected_columns:
        return False

    # Schema mismatch detected
    logger.warning(
        f"Schema mismatch for {table_name}: "
        f"existing={sorted(existing_columns)}, "
        f"expected={sorted(expected_columns)}. "
        f"Dropping and recreating table."
    )
    db.execute(f"DROP TABLE {table_name}")
    db.execute(schema_sql)
    db.commit()
    return True


def migrate_all_tables(db: BaseDatabase, schemas: Dict[str, str]) -> int:
    """Run migration check on all tables in the given schema dict.

    Args:
        db: Database instance (must be connected)
        schemas: Dict mapping table_name -> CREATE TABLE SQL

    Returns:
        Number of tables that were migrated (dropped and recreated)
    """
    migrated = 0
    for table_name, schema_sql in schemas.items():
        if migrate_table_if_needed(db, table_name, schema_sql):
            migrated += 1
    if migrated:
        logger.info(f"Migrated {migrated} table(s) due to schema changes")
    return migrated
