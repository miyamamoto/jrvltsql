"""Shared capture-time rules for odds publication time-series tables."""

from datetime import UTC, datetime
from typing import Any

TIME_SERIES_ODDS_CAPTURE_TABLES = frozenset(
    {
        *(f"TS_O{number}" for number in range(1, 7)),
        *(f"TS_SOKUHO_O{number}" for number in range(1, 7)),
    }
)
SOKUHO_TIME_SERIES_ODDS_CAPTURE_TABLES = frozenset(f"TS_SOKUHO_O{number}" for number in range(1, 7))


def is_time_series_odds_capture_table(table_name: str) -> bool:
    """Return whether CollectedAt is evidence of first possession in this table."""
    unqualified = table_name.rsplit(".", 1)[-1].strip('"`').upper()
    return unqualified in TIME_SERIES_ODDS_CAPTURE_TABLES


def is_sokuho_time_series_odds_capture_table(table_name: str) -> bool:
    """Return whether a write targets a dedicated Sokuho capture table."""
    unqualified = table_name.rsplit(".", 1)[-1].strip('"`').upper()
    return unqualified in SOKUHO_TIME_SERIES_ODDS_CAPTURE_TABLES


def unqualified_table_name(table_name: str) -> str:
    """Return a schema-free table identifier for row qualification."""
    return table_name.rsplit(".", 1)[-1].strip('"`')


def capture_timestamp_epoch_microseconds(value: Any) -> int:
    """Normalize an offset-aware ISO timestamp for exact instant comparison.

    CollectedAt is TEXT in the live schema. Comparing its raw ISO strings is
    incorrect when two equivalent representations use different UTC offsets.
    Returning integer UTC microseconds also avoids SQLite julianday precision
    loss for collector stamps that include microseconds.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.strip())
    else:
        raise ValueError(f"CollectedAt must be an ISO-8601 timestamp, got {value!r}")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"CollectedAt must include a UTC offset, got {value!r}")

    normalized = parsed.astimezone(UTC)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = normalized - epoch
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def earliest_capture_value(first: Any, second: Any) -> Any:
    """Return the earlier real capture, retaining the non-NULL side."""
    if first is None:
        return second
    if second is None:
        return first
    if capture_timestamp_epoch_microseconds(second) < capture_timestamp_epoch_microseconds(first):
        return second
    return first


def prepare_time_series_odds_table(database: Any, table_name: str) -> None:
    """Migrate, create, and verify one capture-evidence table before polling."""
    if not is_time_series_odds_capture_table(table_name):
        raise ValueError(f"Not a time-series odds capture table: {table_name}")

    from src.database.migration import migrate_table_if_needed, verify_table_schema
    from src.database.schema import SCHEMAS

    schema_sql = SCHEMAS[unqualified_table_name(table_name).upper()]
    migrate_table_if_needed(database, table_name, schema_sql)
    database.execute(schema_sql)
    verify_table_schema(database, table_name, schema_sql)
