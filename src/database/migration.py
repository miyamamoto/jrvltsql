"""Schema migration utilities.

Detects schema mismatches in existing tables and applies safe migrations.

The production PostgreSQL database is used by near-real-time collectors, so
``quickstart`` must never wipe tables implicitly.  The default migration policy
is therefore additive only: missing columns are added with ``ALTER TABLE`` and
extra/renamed columns are preserved with a warning.  Destructive DROP+recreate
is available only when ``JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS=1`` is set.
"""

import os
import re
from typing import Dict, List, Optional, Set

from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _schema_body(create_sql: str) -> Optional[str]:
    """Return the body inside the CREATE TABLE parentheses."""
    match = re.search(r'\((.+)\)', create_sql, re.DOTALL)
    if not match:
        return None
    return match.group(1)


def _split_schema_items(body: str) -> List[str]:
    """Split a CREATE TABLE body by top-level commas."""
    items: List[str] = []
    current: List[str] = []
    depth = 0
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        if char == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _extract_column_definitions(create_sql: str) -> Optional[Dict[str, str]]:
    """Extract column-name -> column-definition from CREATE TABLE SQL."""
    body = _schema_body(create_sql)
    if body is None:
        return None

    definitions: Dict[str, str] = {}
    for item in _split_schema_items(body):
        upper = item.upper()
        if upper.startswith(("PRIMARY KEY", "UNIQUE", "FOREIGN KEY", "CONSTRAINT", "CHECK")):
            continue
        token = item.split()[0].strip('`"[]')
        if token:
            definitions[token] = item
    return definitions


def _extract_columns_from_sql(create_sql: str) -> Optional[Set[str]]:
    """Extract column names from a CREATE TABLE SQL statement.

    Args:
        create_sql: SQL CREATE TABLE statement

    Returns:
        Set of column names, or None if parsing fails
    """
    definitions = _extract_column_definitions(create_sql)
    if definitions is None:
        return None
    return set(definitions)


def _extract_primary_key_columns(create_sql: str) -> Optional[List[str]]:
    """Extract PRIMARY KEY columns from CREATE TABLE SQL."""
    body = _schema_body(create_sql)
    if body is None:
        return None

    inline_pk: List[str] = []
    for item in _split_schema_items(body):
        match = re.match(
            r'(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY\s*\(([^)]*)\)',
            item,
            re.IGNORECASE,
        )
        if match:
            return [column.strip().strip('`"[]') for column in match.group(1).split(",")]

        upper = item.upper()
        if upper.startswith(("UNIQUE", "FOREIGN KEY", "CONSTRAINT", "CHECK")):
            continue
        if re.search(r'\bPRIMARY\s+KEY\b', item, re.IGNORECASE):
            token = item.split()[0].strip('`"[]')
            if token:
                inline_pk.append(token)

    return inline_pk


def _destructive_migrations_enabled() -> bool:
    return os.getenv("JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _table_identifier(db: BaseDatabase, table_name: str) -> str:
    if db.get_db_type() == "postgresql":
        return table_name.lower()
    return f'"{table_name}"'


def _get_existing_columns(db: BaseDatabase, table_name: str) -> Set[str]:
    """Get existing column names for a table."""
    if db.get_db_type() == "postgresql":
        existing_info = db.fetch_all(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_name = ? AND table_schema = 'public'",
            (table_name.lower(),),
        )
    else:
        existing_info = db.fetch_all(f'PRAGMA table_info("{table_name}")')
    return {row['name'] for row in existing_info}


def _get_existing_primary_key_columns(db: BaseDatabase, table_name: str) -> List[str]:
    """Get existing primary key columns in key order."""
    if db.get_db_type() == "postgresql":
        rows = db.fetch_all(
            """
            SELECT a.attname AS name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = ?::regclass
            AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """,
            (table_name.lower(),),
        )
        return [row["name"] for row in rows]

    rows = db.fetch_all(f'PRAGMA table_info("{table_name}")')
    pk_rows = [row for row in rows if row.get("pk", 0)]
    pk_rows.sort(key=lambda row: row.get("pk", 0))
    return [row["name"] for row in pk_rows]


def _add_missing_columns(
    db: BaseDatabase,
    table_name: str,
    expected_definitions: Dict[str, str],
    missing_columns: List[str],
) -> int:
    """Add missing columns without touching existing data."""
    table_identifier = _table_identifier(db, table_name)
    added = 0
    for column_name in missing_columns:
        definition = expected_definitions[column_name]
        logger.warning(
            f"Adding missing column to {table_name}: {definition}"
        )
        db.execute(f"ALTER TABLE {table_identifier} ADD COLUMN {definition}")
        added += 1
    if added:
        db.commit()
    return added


def migrate_table_if_needed(db: BaseDatabase, table_name: str, schema_sql: str) -> bool:
    """Check if an existing table's columns match the expected schema.

    By default, only additive migrations are applied.  Existing rows are
    preserved.  Destructive DROP+recreate is opt-in via
    ``JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS=1``.

    Args:
        db: Database instance (must be connected)
        table_name: Table name to check
        schema_sql: The CREATE TABLE SQL for the expected schema

    Returns:
        True if a schema change was applied, False otherwise
    """
    if not db.table_exists(table_name):
        return False

    expected_definitions = _extract_column_definitions(schema_sql)
    if expected_definitions is None:
        logger.warning(f"Could not parse schema SQL for {table_name}, skipping migration check")
        return False
    expected_columns = set(expected_definitions)
    expected_pk = _extract_primary_key_columns(schema_sql) or []

    existing_columns = _get_existing_columns(db, table_name)
    existing_pk = _get_existing_primary_key_columns(db, table_name)

    existing_pk_lower = [column.lower() for column in existing_pk]
    expected_pk_lower = [column.lower() for column in expected_pk]
    if existing_pk_lower != expected_pk_lower:
        if not _destructive_migrations_enabled():
            logger.warning(
                f"Primary key mismatch for {table_name}: "
                f"existing={existing_pk}, expected={expected_pk}. "
                "Destructive migration skipped. "
                "Set JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS=1 to allow DROP+recreate."
            )
            return False

        logger.warning(
            f"Primary key mismatch for {table_name}: "
            f"existing={existing_pk}, expected={expected_pk}. "
            "Dropping and recreating table."
        )
        db.execute(f"DROP TABLE IF EXISTS {_table_identifier(db, table_name)}")
        db.execute(schema_sql)
        db.commit()
        return True

    # PostgreSQL lowercases all unquoted identifiers, so compare case-insensitively.
    # Without this, every PG run sees a "mismatch" between schema.py's CamelCase
    # column names and information_schema's lowercased names, triggering a DROP+
    # recreate on every call to create_all_tables() — which silently wipes data.
    existing_lower = {c.lower() for c in existing_columns}
    expected_lower = {c.lower() for c in expected_columns}
    if existing_lower == expected_lower:
        return False

    missing_columns = [
        column for column in expected_columns
        if column.lower() not in existing_lower
    ]
    extra_columns = sorted(
        column for column in existing_columns
        if column.lower() not in expected_lower
    )

    if missing_columns:
        added = _add_missing_columns(db, table_name, expected_definitions, missing_columns)
        if extra_columns:
            logger.warning(
                f"Schema for {table_name} has extra columns preserved: {extra_columns}"
            )
        return added > 0

    if not extra_columns:
        return False

    if not _destructive_migrations_enabled():
        logger.warning(
            f"Schema mismatch for {table_name}: extra columns preserved and "
            f"destructive migration skipped. extra={extra_columns}. "
            "Set JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS=1 to allow DROP+recreate."
        )
        return False

    logger.warning(
        f"Schema mismatch for {table_name}: "
        f"existing={sorted(existing_columns)}, "
        f"expected={sorted(expected_columns)}. "
        f"Dropping and recreating table."
    )
    db.execute(f"DROP TABLE IF EXISTS {_table_identifier(db, table_name)}")
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
