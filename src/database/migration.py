"""Schema migration utilities.

Detects schema mismatches in existing tables and applies safe migrations.

The production PostgreSQL database is used by near-real-time collectors, so
``quickstart`` must never wipe tables implicitly. Migrations are additive only:
missing columns are added with ``ALTER TABLE`` and extra/renamed columns are
preserved. Primary-key changes always fail closed during ordinary startup.
The PostgreSQL TS_SOKUHO capture-key correction is available only through the
explicit operator command; SQLite requires an operator-managed rebuild.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from uuid import uuid4

from src.database.base import BaseDatabase
from src.database.timeseries_capture import (
    capture_timestamp_epoch_microseconds,
    unqualified_table_name,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SchemaMigrationError(RuntimeError):
    """Raised when a table cannot satisfy its required schema safely."""


SOKUHO_CAPTURE_TABLES = tuple(f"TS_SOKUHO_O{number}" for number in range(1, 7))
_SOKUHO_CAPTURE_TABLE_SET = frozenset(SOKUHO_CAPTURE_TABLES)
SOKUHO_CAPTURE_IDENTITY_MIGRATION_COMMAND = "jltsql db migrate-sokuho-capture-identity"


@dataclass(frozen=True)
class SokuhoCaptureIdentityMigrationReport:
    """One table's deterministic operator migration report."""

    table_name: str
    status: str
    primary_key: tuple[str, ...]
    total_rows: int
    distinct_publication_groups: int
    rows_to_delete: int
    collected_at_rewrite_groups: int
    applied: bool = False


def _migration_targets(
    db: BaseDatabase,
    *,
    include_disconnected_sokuho_targets: bool = False,
) -> tuple[BaseDatabase, ...]:
    """Return concrete databases that must be migrated independently."""
    getter = None
    if include_disconnected_sokuho_targets:
        getter = getattr(db, "get_sokuho_guard_targets", None)
    if getter is None:
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


def _sqlite_table_info_pragma(table_name: str) -> str:
    """Return a quoted PRAGMA that preserves an optional SQLite schema."""

    def quote(identifier: str) -> str:
        normalized = identifier.strip('`"[]')
        escaped = normalized.replace('"', '""')
        return f'"{escaped}"'

    if "." in table_name:
        schema_name, unqualified_name = table_name.rsplit(".", 1)
        return f"PRAGMA {quote(schema_name)}.table_info({quote(unqualified_name)})"
    return f"PRAGMA table_info({quote(table_name)})"


def _sokuho_table_exists_strict(db: BaseDatabase, table_name: str) -> bool:
    """Check a Sokuho table without losing an SQLite schema qualifier."""
    if db.get_db_type() == "sqlite":
        return bool(db.fetch_all(_sqlite_table_info_pragma(table_name)))
    return db.table_exists_strict(table_name)


def _get_existing_columns(db: BaseDatabase, table_name: str) -> Set[str]:
    """Get existing column names for a table."""
    if db.get_db_type() == "postgresql":
        existing_info = db.fetch_all(
            "SELECT a.attname AS name FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 AND NOT a.attisdropped",
            (table_name.lower(),),
        )
    else:
        existing_info = db.fetch_all(_sqlite_table_info_pragma(table_name))
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
        rows = db.fetch_all(_sqlite_table_info_pragma(table_name))
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

    rows = db.fetch_all(_sqlite_table_info_pragma(table_name))

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
    if unqualified_table_name(table_name).upper() not in _SOKUHO_CAPTURE_TABLE_SET:
        return False
    existing = [column.lower() for column in existing_pk]
    expected = [column.lower() for column in expected_pk]
    return existing == [*expected, "collectedat"]


def sokuho_capture_identity_operator_command(
    table_name: str,
    database_type: str = "postgresql",
) -> str:
    """Return the exact read-only dry-run command named by write guards."""
    normalized = _normalize_sokuho_table_reference(table_name)
    schema_option = ""
    if "." in normalized:
        schema_name, normalized = normalized.rsplit(".", 1)
        schema_option = f"--schema {schema_name} "
    return (
        f"{SOKUHO_CAPTURE_IDENTITY_MIGRATION_COMMAND} --db {database_type} "
        f"{schema_option}--table {normalized}"
    )


def legacy_sokuho_capture_identity_message(db: BaseDatabase, table_name: str) -> str:
    """Build the shared actionable refusal for startup and write paths."""
    normalized = _normalize_sokuho_table_reference(table_name)
    refusal = (
        f"{normalized} uses the legacy primary key ending in CollectedAt; "
        "startup and time-series odds writes are blocked."
    )
    if db.get_db_type() == "sqlite":
        return (
            f"{refusal} SQLite cannot migrate this key in place; create a "
            "backup and rebuild the table with the current schema"
        )
    return (
        f"{refusal} First run this read-only "
        "dry run (the default; it does not change data): "
        f"{sokuho_capture_identity_operator_command(normalized, db.get_db_type())}. "
        "Review the report, stop all collectors, then rerun the same command with "
        "--apply; --apply mutates the table"
    )


def _expected_sokuho_primary_key(table_name: str) -> List[str]:
    from src.database.schema import SCHEMAS

    normalized = unqualified_table_name(table_name).upper()
    if normalized not in _SOKUHO_CAPTURE_TABLE_SET:
        raise SchemaMigrationError(f"Unsupported Sokuho migration table: {table_name}")
    expected_pk = _extract_primary_key_columns(SCHEMAS[normalized])
    if not expected_pk:
        raise SchemaMigrationError(f"Expected primary key is unavailable for {normalized}")
    return expected_pk


def _unavailable_sokuho_target_message(db: BaseDatabase, table_name: str) -> str:
    normalized = _normalize_sokuho_table_reference(table_name)
    return (
        f"Cannot verify {normalized} capture identity on the configured "
        f"{db.get_db_type()} database because it is not connected; reconnect "
        "it and rerun startup before collecting"
    )


def ensure_sokuho_capture_identity_for_write(
    db: BaseDatabase,
    table_name: str,
    existing_pk: Optional[List[str]] = None,
) -> None:
    """Fail before a Sokuho write can preserve legacy poll identity."""
    normalized = unqualified_table_name(table_name).upper()
    if normalized not in _SOKUHO_CAPTURE_TABLE_SET:
        return
    if existing_pk is None and not db.is_connected():
        raise SchemaMigrationError(_unavailable_sokuho_target_message(db, table_name))
    expected_pk = _expected_sokuho_primary_key(normalized)
    primary_key = (
        existing_pk
        if existing_pk is not None
        else _get_existing_primary_key_columns(db, table_name)
    )
    if _is_legacy_sokuho_capture_identity(normalized, primary_key, expected_pk):
        raise SchemaMigrationError(legacy_sokuho_capture_identity_message(db, table_name))


def _normalize_sokuho_table_reference(table_name: str) -> str:
    """Validate and canonicalize an optional unquoted schema plus Sokuho table."""
    raw_name = str(table_name).strip()
    if raw_name.count(".") > 1:
        raise SchemaMigrationError(f"Unsupported Sokuho migration table: {table_name}")
    schema_name = ""
    if "." in raw_name:
        schema_name, raw_name = raw_name.rsplit(".", 1)
        schema_name = schema_name.strip('`"[]').lower()
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema_name):
            raise SchemaMigrationError(
                f"Unsupported PostgreSQL schema for Sokuho migration: {schema_name!r}"
            )
    normalized = raw_name.strip('`"[]').upper()
    if normalized not in _SOKUHO_CAPTURE_TABLE_SET:
        raise SchemaMigrationError(f"Unsupported Sokuho migration table: {table_name}")
    return f"{schema_name}.{normalized}" if schema_name else normalized


def normalize_sokuho_capture_identity_tables(
    table_names: Optional[List[str] | tuple[str, ...]],
) -> tuple[str, ...]:
    """Return validated, deterministic operator table references."""
    if not table_names:
        return SOKUHO_CAPTURE_TABLES
    requested = {_normalize_sokuho_table_reference(name) for name in table_names}
    order = {name: index for index, name in enumerate(SOKUHO_CAPTURE_TABLES)}
    return tuple(
        sorted(
            requested,
            key=lambda name: (order[unqualified_table_name(name).upper()], name.lower()),
        )
    )


def validate_sokuho_capture_identity_operator_backend(
    database_type: str,
    table_names: tuple[str, ...],
) -> None:
    """Refuse unsupported backends before a maintenance connection is opened."""
    normalized_type = str(database_type).lower()
    if normalized_type == "postgresql":
        return
    names = ", ".join(table_names)
    if normalized_type == "sqlite":
        raise SchemaMigrationError(
            f"SQLite migration refused for {names}: legacy primary keys cannot be "
            "changed safely in place; back up the database and rebuild each table "
            "with the current schema before polling"
        )
    raise SchemaMigrationError(
        f"Sokuho capture-identity migration requires PostgreSQL, got {database_type}"
    )


def _require_postgresql_operator_migration(
    db: BaseDatabase,
    table_names: tuple[str, ...],
) -> None:
    validate_sokuho_capture_identity_operator_backend(db.get_db_type(), table_names)


def _classify_sokuho_table(
    db: BaseDatabase,
    table_name: str,
) -> tuple[str, List[str], List[str]]:
    expected_pk = _expected_sokuho_primary_key(table_name)
    if not db.table_exists_strict(table_name):
        return "missing", [], expected_pk
    existing_pk = _get_existing_primary_key_columns(db, table_name)
    if [column.lower() for column in existing_pk] == [column.lower() for column in expected_pk]:
        return "current", existing_pk, expected_pk
    if _is_legacy_sokuho_capture_identity(table_name, existing_pk, expected_pk):
        return "legacy", existing_pk, expected_pk
    raise SchemaMigrationError(
        f"Cannot migrate {table_name}: unsupported primary key "
        f"existing={existing_pk}, expected={expected_pk}"
    )


def _current_or_missing_sokuho_report(
    db: BaseDatabase,
    table_name: str,
    status: str,
    existing_pk: List[str],
) -> SokuhoCaptureIdentityMigrationReport:
    total_rows = 0
    if status == "current":
        row = db.fetch_one(
            f"SELECT COUNT(*) AS total_rows FROM {_table_identifier(db, table_name)}"
        )
        total_rows = int((row or {}).get("total_rows") or 0)
    return SokuhoCaptureIdentityMigrationReport(
        table_name=table_name,
        status=status,
        primary_key=tuple(existing_pk),
        total_rows=total_rows,
        distinct_publication_groups=total_rows,
        rows_to_delete=0,
        collected_at_rewrite_groups=0,
    )


def _legacy_sokuho_stats(
    db: BaseDatabase,
    table_name: str,
    expected_pk: List[str],
) -> tuple[int, int, int, int]:
    table_identifier = _table_identifier(db, table_name)
    partition = ", ".join(column.lower() for column in expected_pk)
    row = (
        db.fetch_one(
            "WITH publication_groups AS ("
            "SELECT COUNT(*) AS group_size, "
            "(ARRAY_AGG(collectedat ORDER BY (collectedat IS NULL), "
            "collectedat::timestamptz DESC, ctid DESC))[1] AS latest_collectedat, "
            "(ARRAY_AGG(collectedat ORDER BY (collectedat IS NULL), "
            "collectedat::timestamptz ASC, ctid ASC))[1] AS earliest_collectedat "
            f"FROM {table_identifier} GROUP BY {partition}"
            ") SELECT COALESCE(SUM(group_size), 0) AS total_rows, "
            "COUNT(*) AS publication_groups, "
            "COALESCE(SUM(group_size - 1), 0) AS rows_to_delete, "
            "COUNT(*) FILTER (WHERE latest_collectedat IS DISTINCT FROM "
            "earliest_collectedat) AS rewrite_groups FROM publication_groups"
        )
        or {}
    )
    return (
        int(row.get("total_rows") or 0),
        int(row.get("publication_groups") or 0),
        int(row.get("rows_to_delete") or 0),
        int(row.get("rewrite_groups") or 0),
    )


def _legacy_sokuho_report(
    db: BaseDatabase,
    table_name: str,
    existing_pk: List[str],
    expected_pk: List[str],
) -> SokuhoCaptureIdentityMigrationReport:
    _validate_existing_capture_stamps(db, table_name)
    total_rows, publication_groups, rows_to_delete, rewrite_groups = _legacy_sokuho_stats(
        db, table_name, expected_pk
    )
    return SokuhoCaptureIdentityMigrationReport(
        table_name=table_name,
        status="legacy",
        primary_key=tuple(existing_pk),
        total_rows=total_rows,
        distinct_publication_groups=publication_groups,
        rows_to_delete=rows_to_delete,
        collected_at_rewrite_groups=rewrite_groups,
    )


def preview_sokuho_capture_identity_migration(
    db: BaseDatabase,
    table_names: Optional[List[str] | tuple[str, ...]] = None,
) -> List[SokuhoCaptureIdentityMigrationReport]:
    """Report the migration under one read-only snapshot without table locks."""
    selected = normalize_sokuho_capture_identity_tables(table_names)
    _require_postgresql_operator_migration(db, selected)
    if db.has_pending_transaction():
        raise SchemaMigrationError(
            "Sokuho migration preview requires a fresh connection without a pending transaction"
        )

    db.begin_transaction()
    try:
        db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        reports = []
        for table_name in selected:
            status, existing_pk, expected_pk = _classify_sokuho_table(db, table_name)
            if status == "legacy":
                reports.append(_legacy_sokuho_report(db, table_name, existing_pk, expected_pk))
            else:
                reports.append(
                    _current_or_missing_sokuho_report(db, table_name, status, existing_pk)
                )
        db.rollback()
        return reports
    except Exception as exc:
        db.rollback()
        if isinstance(exc, SchemaMigrationError):
            raise
        raise SchemaMigrationError(f"Failed to preview Sokuho migration: {exc}") from exc


def _create_locked_sokuho_snapshot(
    db: BaseDatabase,
    table_name: str,
    expected_pk: List[str],
) -> tuple[str, str, SokuhoCaptureIdentityMigrationReport]:
    """Create one grouping snapshot after the caller holds ACCESS EXCLUSIVE."""
    table_identifier = _table_identifier(db, table_name)
    temp_name = f"__jltsql_{table_name.lower()}_capture_pk_{uuid4().hex}"
    temp_identifier = f'pg_temp."{temp_name}"'
    key_columns = [column.lower() for column in expected_pk]
    partition = ", ".join(key_columns)

    _validate_existing_capture_stamps(db, table_name)
    constraint = db.fetch_one(
        "SELECT conname FROM pg_constraint " "WHERE conrelid = to_regclass(?) AND contype = 'p'",
        (table_name.lower(),),
    )
    if not constraint or not constraint.get("conname"):
        raise SchemaMigrationError(f"Cannot migrate {table_name}: primary key constraint not found")
    constraint_identifier = '"' + str(constraint["conname"]).replace('"', '""') + '"'
    db.execute(
        f'CREATE TEMP TABLE "{temp_name}" ON COMMIT DROP AS '
        f"SELECT {partition}, COUNT(*) AS group_size, "
        "(ARRAY_AGG(ctid ORDER BY (collectedat IS NULL), "
        "collectedat::timestamptz DESC, ctid DESC))[1] AS keep_tid, "
        "(ARRAY_AGG(collectedat ORDER BY (collectedat IS NULL), "
        "collectedat::timestamptz DESC, ctid DESC))[1] AS latest_collectedat, "
        "(ARRAY_AGG(collectedat ORDER BY (collectedat IS NULL), "
        "collectedat::timestamptz ASC, ctid ASC))[1] AS earliest_collectedat "
        f"FROM {table_identifier} GROUP BY {partition}"
    )
    row = (
        db.fetch_one(
            f"SELECT COALESCE(SUM(group_size), 0) AS total_rows, "
            f"COUNT(*) AS publication_groups, "
            f"COALESCE(SUM(group_size - 1), 0) AS rows_to_delete, "
            f"COUNT(*) FILTER (WHERE latest_collectedat IS DISTINCT FROM "
            f"earliest_collectedat) AS rewrite_groups FROM {temp_identifier}"
        )
        or {}
    )
    existing_pk = _get_existing_primary_key_columns(db, table_name)
    report = SokuhoCaptureIdentityMigrationReport(
        table_name=table_name,
        status="migrated",
        primary_key=tuple(existing_pk),
        total_rows=int(row.get("total_rows") or 0),
        distinct_publication_groups=int(row.get("publication_groups") or 0),
        rows_to_delete=int(row.get("rows_to_delete") or 0),
        collected_at_rewrite_groups=int(row.get("rewrite_groups") or 0),
        applied=True,
    )
    return temp_identifier, constraint_identifier, report


def _apply_locked_sokuho_table_migration(
    db: BaseDatabase,
    table_name: str,
    expected_pk: List[str],
) -> SokuhoCaptureIdentityMigrationReport:
    table_identifier = _table_identifier(db, table_name)
    key_columns = [column.lower() for column in expected_pk]
    grouped_keys = " AND ".join(f"existing.{column} = grouped.{column}" for column in key_columns)
    temp_identifier, constraint_identifier, report = _create_locked_sokuho_snapshot(
        db, table_name, expected_pk
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
    remaining_row = db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_identifier}") or {}
    remaining = int(remaining_row.get("count") or 0)
    if remaining != report.distinct_publication_groups:
        raise SchemaMigrationError(
            f"Cannot migrate {table_name}: retained {remaining} of "
            f"{report.distinct_publication_groups} publication rows"
        )
    db.execute(f"DROP TABLE {temp_identifier}")
    return report


def apply_sokuho_capture_identity_migration(
    db: BaseDatabase,
    table_names: Optional[List[str] | tuple[str, ...]] = None,
) -> List[SokuhoCaptureIdentityMigrationReport]:
    """Explicitly migrate selected PostgreSQL Sokuho tables in one transaction."""
    selected = normalize_sokuho_capture_identity_tables(table_names)
    _require_postgresql_operator_migration(db, selected)
    if db.has_pending_transaction():
        raise SchemaMigrationError(
            "Sokuho migration apply requires a fresh connection without a pending transaction"
        )

    db.begin_transaction()
    try:
        initial = {table_name: _classify_sokuho_table(db, table_name) for table_name in selected}
        legacy_tables = [
            table_name for table_name in selected if initial[table_name][0] == "legacy"
        ]
        if legacy_tables:
            lock_targets = ", ".join(
                _table_identifier(db, table_name) for table_name in legacy_tables
            )
            # All target locks precede every grouping snapshot. The canonical
            # table order also prevents two operator commands taking locks in
            # opposite orders.
            db.execute(f"LOCK TABLE {lock_targets} IN ACCESS EXCLUSIVE MODE")

        reports = []
        for table_name in selected:
            status, existing_pk, expected_pk = _classify_sokuho_table(db, table_name)
            if status == "legacy":
                if table_name not in legacy_tables:
                    raise SchemaMigrationError(
                        f"Cannot migrate {table_name}: it changed to a legacy primary key "
                        "before an ACCESS EXCLUSIVE lock was acquired; retry the command"
                    )
                logger.warning(
                    f"Explicitly migrating {table_name} from poll identity to "
                    "publication identity"
                )
                reports.append(_apply_locked_sokuho_table_migration(db, table_name, expected_pk))
            else:
                reports.append(
                    _current_or_missing_sokuho_report(db, table_name, status, existing_pk)
                )
        db.commit()
        return reports
    except Exception as exc:
        db.rollback()
        if isinstance(exc, SchemaMigrationError):
            raise
        raise SchemaMigrationError(f"Failed to apply Sokuho migration: {exc}") from exc


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
    is_sokuho_table = unqualified_table_name(table_name).upper() in _SOKUHO_CAPTURE_TABLE_SET
    targets = _migration_targets(
        db,
        include_disconnected_sokuho_targets=is_sokuho_table,
    )
    if targets != (db,):
        if is_sokuho_table:
            for target in targets:
                if not target.is_connected():
                    raise SchemaMigrationError(
                        _unavailable_sokuho_target_message(target, table_name)
                    )
        migrated = False
        for target in targets:
            migrated = (
                migrate_table_if_needed(target, table_name, schema_sql, commit=commit) or migrated
            )
        return migrated

    table_exists = (
        _sokuho_table_exists_strict(db, table_name)
        if is_sokuho_table
        else db.table_exists(table_name)
    )
    if not table_exists:
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
    if _is_legacy_sokuho_capture_identity(table_name, existing_pk, expected_pk):
        raise SchemaMigrationError(legacy_sokuho_capture_identity_message(db, table_name))
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
    is_sokuho_table = unqualified_table_name(table_name).upper() in _SOKUHO_CAPTURE_TABLE_SET
    targets = _migration_targets(
        db,
        include_disconnected_sokuho_targets=is_sokuho_table,
    )
    if targets != (db,):
        if is_sokuho_table:
            for target in targets:
                if not target.is_connected():
                    raise SchemaMigrationError(
                        _unavailable_sokuho_target_message(target, table_name)
                    )
        for target in targets:
            verify_table_schema(
                target,
                table_name,
                schema_sql,
                allow_missing_columns=allow_missing_columns,
                allow_primary_key_mismatch=allow_primary_key_mismatch,
            )
        return

    table_exists = (
        _sokuho_table_exists_strict(db, table_name)
        if is_sokuho_table
        else db.table_exists_strict(table_name)
    )
    if not table_exists:
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

    if _is_legacy_sokuho_capture_identity(table_name, existing_pk, expected_pk):
        raise SchemaMigrationError(legacy_sokuho_capture_identity_message(db, table_name))

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
