"""Schema migration utilities.

Detects schema mismatches in existing tables and applies safe migrations.

The production PostgreSQL database is used by near-real-time collectors, so
``quickstart`` must never wipe tables implicitly. Migrations are additive only:
missing columns are added with ``ALTER TABLE`` and extra/renamed columns are
preserved. Primary-key changes fail closed except for the exact PostgreSQL
TS_SOKUHO capture-key correction implemented below. Legacy SQLite Sokuho keys
are rejected without mutation and require an operator-managed rebuild.
"""

import re
from typing import Dict, List, Optional, Set
from uuid import uuid4

from src.database.base import BaseDatabase
from src.database.timeseries_capture import capture_timestamp_epoch_microseconds
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaMigrationError(RuntimeError):
    """Raised when a table cannot satisfy its required schema safely."""


_SOKUHO_CAPTURE_TABLES = frozenset(f"TS_SOKUHO_O{number}" for number in range(1, 7))


def _migration_targets(db: BaseDatabase) -> tuple[BaseDatabase, ...]:
    """Return concrete databases that must be migrated independently."""
    getter = getattr(db, "get_migration_targets", None)
    if getter is None:
        return (db,)
    targets = tuple(getter())
    return targets or (db,)


def _strip_sql_line_comments(sql: str) -> str:
    """Strip ``--`` comments without touching quoted SQL text."""
    result: List[str] = []
    quote_end: Optional[str] = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote_end is not None:
            result.append(char)
            if char == quote_end:
                if quote_end != "]" and index + 1 < len(sql) and sql[index + 1] == quote_end:
                    result.append(sql[index + 1])
                    index += 2
                    continue
                quote_end = None
            index += 1
            continue

        if char in {"'", '"', "`"}:
            quote_end = char
            result.append(char)
            index += 1
            continue
        if char == "[":
            quote_end = "]"
            result.append(char)
            index += 1
            continue
        if char == "-" and index + 1 < len(sql) and sql[index + 1] == "-":
            index += 2
            while index < len(sql) and sql[index] not in "\r\n":
                index += 1
            continue

        result.append(char)
        index += 1
    return "".join(result)


def _schema_body(create_sql: str) -> Optional[str]:
    """Return the body inside the CREATE TABLE parentheses."""
    # Generated schemas use trailing ``--`` comments.  They must not become
    # part of an ALTER TABLE column definition during additive migration.
    sql_without_line_comments = _strip_sql_line_comments(create_sql)
    match = re.search(r"\((.+)\)", sql_without_line_comments, re.DOTALL)
    if not match:
        return None
    return match.group(1)


def _split_schema_items(body: str) -> List[str]:
    """Split a CREATE TABLE body by top-level commas."""
    items: List[str] = []
    current: List[str] = []
    depth = 0
    quote_end: Optional[str] = None
    index = 0
    while index < len(body):
        char = body[index]
        if quote_end is not None:
            current.append(char)
            if char == quote_end:
                if quote_end != "]" and index + 1 < len(body) and body[index + 1] == quote_end:
                    current.append(body[index + 1])
                    index += 2
                    continue
                quote_end = None
            index += 1
            continue

        if char in {"'", '"', "`"}:
            quote_end = char
            current.append(char)
            index += 1
            continue
        if char == "[":
            quote_end = "]"
            current.append(char)
            index += 1
            continue
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
        index += 1
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
            r"(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY\s*\(([^)]*)\)",
            item,
            re.IGNORECASE,
        )
        if match:
            return [column.strip().strip('`"[]') for column in match.group(1).split(",")]

        upper = item.upper()
        if upper.startswith(("UNIQUE", "FOREIGN KEY", "CONSTRAINT", "CHECK")):
            continue
        if re.search(r"\bPRIMARY\s+KEY\b", item, re.IGNORECASE):
            token = item.split()[0].strip('`"[]')
            if token:
                inline_pk.append(token)

    return inline_pk


def _table_identifier(db: BaseDatabase, table_name: str) -> str:
    if db.get_db_type() == "postgresql":
        return table_name.lower()
    return f'"{table_name}"'


def _get_existing_columns(db: BaseDatabase, table_name: str) -> Set[str]:
    """Get existing column names for a table."""
    if db.get_db_type() == "postgresql":
        existing_info = db.fetch_all(
            "SELECT a.attname AS name FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 AND NOT a.attisdropped",
            (table_name.lower(),),
        )
    else:
        existing_info = db.fetch_all(f'PRAGMA table_info("{table_name}")')
    return {row["name"] for row in existing_info}


def _is_lossless_text_type(declared_type: str) -> bool:
    """Return whether a declared SQL type preserves an eight-digit string."""
    normalized = re.sub(r"\s+", " ", declared_type.strip().upper())
    return any(marker in normalized for marker in ("CHAR", "CLOB", "TEXT"))


def _definition_type(column_definition: str) -> str:
    """Extract the declared type token(s) from a parsed column definition."""
    tokens = column_definition.split()
    if len(tokens) < 2:
        return ""
    if len(tokens) >= 3 and tokens[1].upper() in {"CHARACTER", "DOUBLE"}:
        return f"{tokens[1]} {tokens[2]}"
    return tokens[1]


def _bounded_text_capacity(declared_type: str) -> Optional[int]:
    """Return a declared text limit, None if unbounded, or -1 if unknown."""
    normalized = re.sub(r"\s+", " ", declared_type.strip().upper())
    if not _is_lossless_text_type(normalized) or "(" not in normalized:
        return None
    match = re.search(r"\(\s*(\d+)(?:\s+(?:BYTE|CHAR))?\s*\)\s*$", normalized)
    return int(match.group(1)) if match else -1


def _get_existing_column_types(db: BaseDatabase, table_name: str) -> Dict[str, str]:
    """Return actual declared types keyed by lower-cased column name."""
    if db.get_db_type() == "postgresql":
        rows = db.fetch_all(
            "SELECT a.attname AS name, "
            "format_type(a.atttypid, a.atttypmod) AS type "
            "FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 AND NOT a.attisdropped",
            (table_name.lower(),),
        )
    else:
        rows = db.fetch_all(f'PRAGMA table_info("{table_name}")')
    return {str(row["name"]).lower(): str(row.get("type") or "") for row in rows}


def _get_existing_primary_key_columns(db: BaseDatabase, table_name: str) -> List[str]:
    """Get existing primary key columns in key order."""
    if db.get_db_type() == "postgresql":
        rows = db.fetch_all(
            """
            SELECT a.attname AS name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = to_regclass(?)
            AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """,
            (table_name.lower(),),
        )
        return [row["name"] for row in rows]

    rows = db.fetch_all(f'PRAGMA table_info("{table_name}")')

    def pk_position(row) -> int:
        try:
            return int(row["pk"] or 0)
        except (KeyError, TypeError, ValueError):
            return 0

    pk_rows = [row for row in rows if pk_position(row)]
    pk_rows.sort(key=pk_position)
    return [row["name"] for row in pk_rows]


def _add_missing_columns(
    db: BaseDatabase,
    table_name: str,
    expected_definitions: Dict[str, str],
    missing_columns: List[str],
    *,
    commit: bool,
) -> int:
    """Add missing columns without touching existing data."""
    if missing_columns and not commit:
        if db.get_db_type() == "sqlite":
            connection = getattr(db, "_connection", None)
            if connection is None:
                raise SchemaMigrationError("SQLite migration requires a connected database")
            if not connection.in_transaction:
                db.execute("BEGIN")
        else:
            db.begin_transaction()

    table_identifier = _table_identifier(db, table_name)
    added = 0
    for column_name in missing_columns:
        definition = expected_definitions[column_name]
        logger.warning(f"Adding missing column to {table_name}: {definition}")
        db.execute(f"ALTER TABLE {table_identifier} ADD COLUMN {definition}")
        added += 1
    if added and commit:
        db.commit()
    return added


def _validate_existing_capture_stamps(db: BaseDatabase, table_name: str) -> None:
    """Reject a legacy Sokuho identity migration if a real stamp is invalid."""
    table_identifier = _table_identifier(db, table_name)
    rows = db.fetch_all(
        f"SELECT DISTINCT CollectedAt AS collectedat FROM {table_identifier} "
        "WHERE CollectedAt IS NOT NULL"
    )
    invalid = []
    for row in rows:
        value = row.get("collectedat")
        try:
            capture_timestamp_epoch_microseconds(value)
        except (TypeError, ValueError):
            invalid.append(repr(value))
    if invalid:
        examples = ", ".join(invalid[:5])
        suffix = " ..." if len(invalid) > 5 else ""
        raise SchemaMigrationError(
            f"Cannot migrate {table_name}: invalid offset-aware CollectedAt values "
            f"[{examples}{suffix}]"
        )


def _is_legacy_sokuho_capture_identity(
    table_name: str,
    existing_pk: List[str],
    expected_pk: List[str],
) -> bool:
    """Recognize only the shipped Sokuho key that ended in CollectedAt."""
    if table_name.upper() not in _SOKUHO_CAPTURE_TABLES:
        return False
    existing = [column.lower() for column in existing_pk]
    expected = [column.lower() for column in expected_pk]
    return existing == [*expected, "collectedat"]


def _postgresql_migrate_sokuho_capture_identity(
    db: BaseDatabase,
    table_name: str,
    expected_pk: List[str],
    *,
    commit: bool,
) -> None:
    """Collapse legacy PostgreSQL polls and replace the primary key atomically."""
    table_identifier = _table_identifier(db, table_name)
    temp_name = f"__jltsql_{table_name.lower()}_capture_pk_{uuid4().hex}"
    temp_create_identifier = f'"{temp_name}"'
    temp_identifier = f'pg_temp."{temp_name}"'
    key_columns = [column.lower() for column in expected_pk]
    partition = ", ".join(key_columns)
    grouped_keys = " AND ".join(f"existing.{column} = grouped.{column}" for column in key_columns)

    db.begin_transaction()
    try:
        # The DELETE must operate on the same population as the grouping
        # snapshot. Lock first so a concurrent collector cannot insert a
        # correction that the migration would then delete unseen.
        db.execute(f"LOCK TABLE {table_identifier} IN ACCESS EXCLUSIVE MODE")
        _validate_existing_capture_stamps(db, table_name)
        constraint = db.fetch_one(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = to_regclass(?) AND contype = 'p'",
            (table_name.lower(),),
        )
        if not constraint or not constraint.get("conname"):
            raise SchemaMigrationError(
                f"Cannot migrate {table_name}: primary key constraint not found"
            )
        constraint_identifier = '"' + str(constraint["conname"]).replace('"', '""') + '"'
        db.execute(
            f"CREATE TEMP TABLE {temp_create_identifier} ON COMMIT DROP AS "
            f"SELECT {partition}, "
            "(ARRAY_AGG(ctid ORDER BY (collectedat IS NULL), "
            "collectedat::timestamptz DESC, ctid DESC))[1] AS keep_tid, "
            "(ARRAY_AGG(collectedat ORDER BY (collectedat IS NULL), "
            "collectedat::timestamptz ASC, ctid ASC))[1] AS earliest_collectedat "
            f"FROM {table_identifier} GROUP BY {partition}"
        )
        db.execute(
            f"DELETE FROM {table_identifier} AS existing USING {temp_identifier} AS grouped "
            f"WHERE {grouped_keys} AND existing.ctid <> grouped.keep_tid"
        )
        db.execute(
            f"UPDATE {table_identifier} AS existing "
            f"SET collectedat = grouped.earliest_collectedat "
            f"FROM {temp_identifier} AS grouped WHERE existing.ctid = grouped.keep_tid"
        )
        db.execute(f"ALTER TABLE {table_identifier} DROP CONSTRAINT {constraint_identifier}")
        db.execute(f"ALTER TABLE {table_identifier} ALTER COLUMN collectedat DROP NOT NULL")
        db.execute(f"ALTER TABLE {table_identifier} ADD PRIMARY KEY ({', '.join(key_columns)})")
        remaining = db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_identifier}")["count"]
        grouped = db.fetch_one(f"SELECT COUNT(*) AS count FROM {temp_identifier}")["count"]
        if remaining != grouped:
            raise SchemaMigrationError(
                f"Cannot migrate {table_name}: retained {remaining} of {grouped} publication rows"
            )
        db.execute(f"DROP TABLE {temp_identifier}")
        if commit:
            db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc, SchemaMigrationError):
            raise
        raise SchemaMigrationError(f"Failed to migrate {table_name}: {exc}") from exc


def _migrate_sokuho_capture_identity(
    db: BaseDatabase,
    table_name: str,
    expected_pk: List[str],
    *,
    commit: bool,
) -> None:
    """Apply the one approved primary-key correction for Sokuho tables."""
    if db.get_db_type() != "postgresql":
        raise SchemaMigrationError(
            f"Automatic SQLite migration refused for {table_name}: legacy primary key "
            "includes CollectedAt; back up and rebuild this table with the current "
            "schema before polling"
        )
    logger.warning(
        f"Migrating {table_name} from poll identity to publication identity; "
        "latest values and earliest real CollectedAt will be retained"
    )
    _postgresql_migrate_sokuho_capture_identity(
        db,
        table_name,
        expected_pk,
        commit=commit,
    )


def migrate_table_if_needed(
    db: BaseDatabase,
    table_name: str,
    schema_sql: str,
    *,
    commit: bool = True,
) -> bool:
    """Check if an existing table's columns match the expected schema.

    Only additive migrations are applied. Existing rows are preserved and
    tables are never dropped automatically.

    Args:
        db: Database instance (must be connected)
        table_name: Table name to check
        schema_sql: The CREATE TABLE SQL for the expected schema

    Returns:
        True if a schema change was applied, False otherwise
    """
    targets = _migration_targets(db)
    if targets != (db,):
        migrated = False
        for target in targets:
            migrated = (
                migrate_table_if_needed(target, table_name, schema_sql, commit=commit) or migrated
            )
        return migrated

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
    existing_columns_lower = {column.lower() for column in existing_columns}
    expected_columns_lower = {column.lower() for column in expected_columns}
    if existing_columns_lower == expected_columns_lower and _is_legacy_sokuho_capture_identity(
        table_name, existing_pk, expected_pk
    ):
        _migrate_sokuho_capture_identity(
            db,
            table_name,
            expected_pk,
            commit=commit,
        )
        return True
    if expected_pk_lower and existing_pk_lower != expected_pk_lower:
        logger.warning(
            f"Primary key mismatch for {table_name}: "
            f"existing={existing_pk}, expected={expected_pk}. "
            "Automatic migration refused; operator action is required."
        )
        return False
    if existing_pk_lower and not expected_pk_lower:
        logger.warning(
            f"Existing primary key for {table_name} is not declared by the "
            f"expected schema: existing={existing_pk}. Constraint is preserved."
        )

    # PostgreSQL lowercases all unquoted identifiers, so compare case-insensitively.
    # Without this, every PG run sees a "mismatch" between schema.py's CamelCase
    # column names and information_schema's lowercased names, triggering a DROP+
    # recreate on every call to create_all_tables() — which silently wipes data.
    existing_lower = existing_columns_lower
    expected_lower = expected_columns_lower
    if existing_lower == expected_lower:
        return False

    missing_columns = [
        column for column in expected_columns if column.lower() not in existing_lower
    ]
    extra_columns = sorted(
        column for column in existing_columns if column.lower() not in expected_lower
    )

    if missing_columns:
        added = _add_missing_columns(
            db,
            table_name,
            expected_definitions,
            missing_columns,
            commit=commit,
        )
        if extra_columns:
            logger.warning(f"Schema for {table_name} has extra columns preserved: {extra_columns}")
        return added > 0

    if not extra_columns:
        return False

    logger.warning(f"Schema for {table_name} has extra columns preserved: {extra_columns}")
    return False


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


def verify_table_schema(
    db: BaseDatabase,
    table_name: str,
    schema_sql: str,
    *,
    allow_missing_columns: bool = False,
    allow_primary_key_mismatch: bool = False,
) -> None:
    """Verify required columns and primary key after migration/creation.

    Extra legacy columns are allowed because the default migration policy is
    additive. A primary-key mismatch, a temporal or numeric column where
    lossless text is required, or an insufficient declared text capacity are
    unsafe. ``allow_missing_columns`` and ``allow_primary_key_mismatch`` are
    reserved for a read-only preflight immediately before an additive
    migration; normal verification still requires every expected column and
    key. The latter permits legacy ordered masters whose additive migrator will
    refuse to alter a mismatched key and whose dedicated writer verifies the
    complete schema before storing a matching record.
    """
    targets = _migration_targets(db)
    if targets != (db,):
        for target in targets:
            verify_table_schema(
                target,
                table_name,
                schema_sql,
                allow_missing_columns=allow_missing_columns,
                allow_primary_key_mismatch=allow_primary_key_mismatch,
            )
        return

    if not db.table_exists_strict(table_name):
        raise SchemaMigrationError(f"Required table does not exist: {table_name}")

    expected_definitions = _extract_column_definitions(schema_sql)
    expected_pk = _extract_primary_key_columns(schema_sql)
    if expected_definitions is None or expected_pk is None:
        raise SchemaMigrationError(f"Could not parse expected schema for {table_name}")

    existing_columns = _get_existing_columns(db, table_name)
    existing_lower = {column.lower() for column in existing_columns}
    missing_columns = sorted(
        column for column in expected_definitions if column.lower() not in existing_lower
    )

    existing_pk = _get_existing_primary_key_columns(db, table_name)
    existing_pk_lower = [column.lower() for column in existing_pk]
    expected_pk_lower = [column.lower() for column in expected_pk]

    expected_text_types = {
        column.lower(): _definition_type(definition)
        for column, definition in expected_definitions.items()
        if _is_lossless_text_type(_definition_type(definition))
    }
    existing_types = _get_existing_column_types(db, table_name)
    unknown_text_types = sorted(
        column
        for column in expected_text_types
        if column in existing_lower and not existing_types.get(column)
    )
    incompatible_text_types = sorted(
        f"{column} existing={existing_types[column]} expected={expected_text_types[column]}"
        for column in expected_text_types
        if column in existing_lower
        and existing_types.get(column)
        and not _is_lossless_text_type(existing_types[column])
    )
    expected_capacities = {
        column.lower(): capacity
        for column, definition in expected_definitions.items()
        if (capacity := _bounded_text_capacity(_definition_type(definition))) is not None
    }
    insufficient_capacities = sorted(
        f"{column} existing={existing_types[column]} minimum={minimum}"
        for column, minimum in expected_capacities.items()
        if column in existing_lower
        and existing_types.get(column)
        and _is_lossless_text_type(existing_types[column])
        and (actual := _bounded_text_capacity(existing_types[column])) is not None
        and actual < minimum
    )

    problems = []
    if missing_columns and not allow_missing_columns:
        problems.append(f"missing columns={missing_columns}")
    if (
        expected_pk_lower
        and existing_pk_lower != expected_pk_lower
        and not allow_primary_key_mismatch
    ):
        problems.append(f"primary key existing={existing_pk}, expected={expected_pk}")
    if unknown_text_types:
        problems.append(f"unknown column types={unknown_text_types}")
    if incompatible_text_types:
        problems.append(f"incompatible column types={incompatible_text_types}")
    if insufficient_capacities:
        problems.append(f"insufficient column capacities={insufficient_capacities}")
    if problems:
        raise SchemaMigrationError(
            f"Schema verification failed for {table_name}: " + "; ".join(problems)
        )
