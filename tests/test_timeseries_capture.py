"""Decision-time provenance contracts for time-series odds writes."""

import os
from threading import Event, Thread
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.database.timeseries_capture import prepare_time_series_odds_table


def _o2_row(*, collected_at, odds: float = 10.0, kumi: str = "0102") -> dict:
    return {
        "RecordSpec": "O2",
        "DataKubun": "1",
        "Year": 2026,
        "MonthDay": 901,
        "JyoCD": "05",
        "Kaiji": 3,
        "Nichiji": 4,
        "RaceNum": 1,
        "HassoTime": "09011200",
        "Kumi": kumi,
        "Odds": odds,
        "CollectedAt": collected_at,
    }


def _sqlite_ts_o2(tmp_path) -> SQLiteDatabase:
    database = SQLiteDatabase({"path": str(tmp_path / "timeseries.db")})
    database.connect()
    database.create_table("TS_O2", SCHEMAS["TS_O2"])
    return database


def _sokuho_o2_row(*, collected_at, odds: float = 10.0, kumi: str = "0102") -> dict:
    return {
        **_o2_row(collected_at=collected_at, odds=odds, kumi=kumi),
        "SourceSpec": "0B32",
    }


def test_prepare_time_series_odds_table_creates_and_verifies_current_schema(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "prepared.db")})
    database.connect()
    try:
        prepare_time_series_odds_table(database, "TS_O2")

        assert database.table_exists("TS_O2") is True
        database.insert("TS_O2", _o2_row(collected_at="2026-09-01T03:00:00+00:00"))
        assert database.fetch_one("SELECT CollectedAt FROM TS_O2") == {
            "CollectedAt": "2026-09-01T03:00:00+00:00"
        }
    finally:
        database.disconnect()


def test_sqlite_later_recapture_keeps_first_stamp_and_corrected_price_wins(tmp_path):
    database = _sqlite_ts_o2(tmp_path)
    try:
        database.insert_many(
            "TS_O2",
            [_o2_row(collected_at="2026-09-01T03:00:00+00:00", odds=10.0)],
        )
        database.insert_many(
            "TS_O2",
            [_o2_row(collected_at="2026-09-01T03:05:00+00:00", odds=12.5)],
        )

        row = database.fetch_one("SELECT Odds, CollectedAt FROM TS_O2")
        assert row == {
            "Odds": 12.5,
            "CollectedAt": "2026-09-01T03:00:00+00:00",
        }
    finally:
        database.disconnect()


def test_sqlite_earlier_recapture_moves_stamp_back(tmp_path):
    database = _sqlite_ts_o2(tmp_path)
    try:
        database.insert("TS_O2", _o2_row(collected_at="2026-09-01T03:05:00+00:00"))
        database.insert("TS_O2", _o2_row(collected_at="2026-09-01T03:00:00+00:00"))

        assert database.fetch_one("SELECT CollectedAt FROM TS_O2") == {
            "CollectedAt": "2026-09-01T03:00:00+00:00"
        }
    finally:
        database.disconnect()


@pytest.mark.parametrize(
    ("stored", "incoming", "expected"),
    [
        (
            "2026-09-01T03:00:00+00:00",
            None,
            "2026-09-01T03:00:00+00:00",
        ),
        (
            None,
            "2026-09-01T03:00:00+00:00",
            "2026-09-01T03:00:00+00:00",
        ),
        (None, None, None),
    ],
    ids=["incoming-null", "stored-null", "both-null"],
)
def test_sqlite_capture_stamp_is_null_safe(tmp_path, stored, incoming, expected):
    database = _sqlite_ts_o2(tmp_path)
    try:
        database.insert("TS_O2", _o2_row(collected_at=stored))
        database.insert("TS_O2", _o2_row(collected_at=incoming))

        assert database.fetch_one("SELECT CollectedAt FROM TS_O2") == {"CollectedAt": expected}
    finally:
        database.disconnect()


def test_sqlite_capture_comparison_normalizes_iso_offsets(tmp_path):
    database = _sqlite_ts_o2(tmp_path)
    try:
        # 09:30 +09:00 is 00:30 UTC and therefore earlier than 01:00 UTC,
        # even though the raw strings sort in the opposite order.
        database.insert("TS_O2", _o2_row(collected_at="2026-09-01T09:30:00+09:00"))
        database.insert("TS_O2", _o2_row(collected_at="2026-09-01T01:00:00+00:00"))

        assert database.fetch_one("SELECT CollectedAt FROM TS_O2") == {
            "CollectedAt": "2026-09-01T09:30:00+09:00"
        }
    finally:
        database.disconnect()


def test_sqlite_sokuho_uses_publication_identity_and_keeps_earliest_capture(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "sokuho.db")})
    database.connect()
    try:
        database.create_table("TS_SOKUHO_O2", SCHEMAS["TS_SOKUHO_O2"])
        database.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T03:05:00+00:00", odds=10.0),
        )
        database.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T03:00:00+00:00", odds=12.5),
        )

        assert database.fetch_all("SELECT Odds, CollectedAt FROM TS_SOKUHO_O2") == [
            {"Odds": 12.5, "CollectedAt": "2026-09-01T03:00:00+00:00"}
        ]
    finally:
        database.disconnect()


def test_sqlite_legacy_sokuho_key_fails_closed_without_schema_or_row_changes(tmp_path):
    from src.database.migration import SchemaMigrationError, migrate_table_if_needed

    database = SQLiteDatabase({"path": str(tmp_path / "legacy-sokuho.db")})
    database.connect()
    try:
        current_schema = SCHEMAS["TS_SOKUHO_O2"]
        legacy_schema = current_schema.replace(
            "HassoTime, SourceSpec)",
            "HassoTime, SourceSpec, CollectedAt)",
        ).replace("Odds REAL,", "Odds REAL CHECK (Odds >= 0),")
        database.create_table("TS_SOKUHO_O2", legacy_schema)
        database.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
        )
        database.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
        )
        database.commit()
        schema_before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE name = 'TS_SOKUHO_O2'"
        )["sql"]

        with pytest.raises(SchemaMigrationError, match="TS_SOKUHO_O2.*back up and rebuild"):
            migrate_table_if_needed(database, "TS_SOKUHO_O2", current_schema)

        assert (
            database.fetch_one("SELECT sql FROM sqlite_master WHERE name = 'TS_SOKUHO_O2'")["sql"]
            == schema_before
        )
        assert database.fetch_all(
            "SELECT Odds, CollectedAt FROM TS_SOKUHO_O2 ORDER BY CollectedAt"
        ) == [
            {"Odds": 12.5, "CollectedAt": "2026-09-01T01:00:00+00:00"},
            {"Odds": 10.0, "CollectedAt": "2026-09-01T09:30:00+09:00"},
        ]
        primary_key_rows = [
            row for row in database.fetch_all('PRAGMA table_info("TS_SOKUHO_O2")') if row["pk"]
        ]
        primary_key = [row["name"] for row in sorted(primary_key_rows, key=lambda row: row["pk"])]
        assert primary_key[-1] == "CollectedAt"
    finally:
        database.disconnect()


def test_schema_qualified_sqlite_timeseries_upsert_uses_unqualified_row_name(tmp_path):
    database = _sqlite_ts_o2(tmp_path)
    try:
        database.insert("main.TS_O2", _o2_row(collected_at="2026-09-01T03:05:00+00:00"))
        database.insert("main.TS_O2", _o2_row(collected_at="2026-09-01T03:00:00+00:00"))
        assert database.fetch_one("SELECT CollectedAt FROM TS_O2") == {
            "CollectedAt": "2026-09-01T03:00:00+00:00"
        }
    finally:
        database.disconnect()


@pytest.mark.parametrize("table_name", ["TS_O2", "TS_SOKUHO_O2"])
def test_postgresql_timeseries_upsert_normalizes_offsets_and_is_null_safe(table_name):
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase({})
    database._get_primary_key_columns = MagicMock(  # type: ignore[method-assign]
        return_value=[
            "year",
            "monthday",
            "jyocd",
            "kaiji",
            "nichiji",
            "racenum",
            "kumi",
            "hassotime",
            *(("sourcespec",) if table_name.startswith("TS_SOKUHO_") else ()),
        ]
    )
    database.execute = MagicMock(return_value=1)  # type: ignore[method-assign]
    row = _o2_row(collected_at="2026-09-01T03:00:00+00:00", odds=12.5)
    if table_name.startswith("TS_SOKUHO_"):
        row["SourceSpec"] = "0B32"

    database.insert(table_name, row)

    sql = database.execute.call_args.args[0].lower()
    assert "excluded.collectedat is null" in sql
    assert f"{table_name.lower()}.collectedat is null" in sql
    assert "excluded.collectedat::timestamptz" in sql
    assert f"{table_name.lower()}.collectedat::timestamptz" in sql
    assert "odds = excluded.odds" in sql


def test_unrelated_sqlite_table_keeps_replace_behavior(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "unrelated.db")})
    database.connect()
    try:
        database.execute(
            "CREATE TABLE OTHER_ODDS (Id INTEGER PRIMARY KEY, Price REAL, CollectedAt TEXT)"
        )
        database.insert("OTHER_ODDS", {"Id": 1, "Price": 10.0, "CollectedAt": "old"})
        database.insert("OTHER_ODDS", {"Id": 1, "Price": 12.5, "CollectedAt": None})

        assert database.fetch_one("SELECT Price, CollectedAt FROM OTHER_ODDS") == {
            "Price": 12.5,
            "CollectedAt": None,
        }
    finally:
        database.disconnect()


def test_postgresql_batch_dedupe_keeps_last_price_and_earliest_capture():
    from src.database.postgresql_handler import PostgreSQLDatabase

    rows = [
        _o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
        _o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
    ]

    deduped = PostgreSQLDatabase._dedupe_rows_by_primary_key(
        rows,
        ["year", "monthday", "jyocd", "kaiji", "nichiji", "racenum", "kumi", "hassotime"],
        preserve_earliest_collected_at=True,
    )

    assert deduped == [_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=12.5)]


@pytest.fixture
def postgresql_timeseries_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_ts_capture_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.rollback()
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("table_name", ["TS_O2", "TS_SOKUHO_O2"])
def test_postgresql_timeseries_capture_behavior(postgresql_timeseries_db, table_name):
    database = postgresql_timeseries_db
    database.execute(SCHEMAS[table_name])
    database.commit()
    row_factory = _sokuho_o2_row if table_name.startswith("TS_SOKUHO_") else _o2_row

    database.insert(table_name, row_factory(collected_at="2026-09-01T01:00:00+00:00"))
    database.insert(
        table_name,
        row_factory(collected_at="2026-09-01T03:05:00+00:00", odds=12.5),
    )
    database.insert(
        table_name,
        row_factory(collected_at="2026-09-01T09:30:00+09:00", odds=13.0),
    )
    database.insert(
        table_name,
        row_factory(collected_at=None, odds=14.0),
    )
    database.insert(
        table_name,
        row_factory(collected_at=None, kumi="0203"),
    )
    database.insert(
        table_name,
        row_factory(collected_at="2026-09-01T02:00:00+00:00", kumi="0203"),
    )
    database.insert(
        table_name,
        row_factory(collected_at=None, kumi="0304"),
    )
    database.insert(
        table_name,
        row_factory(collected_at=None, odds=15.0, kumi="0304"),
    )
    database.commit()

    assert database.fetch_all(
        f"SELECT kumi, odds, collectedat FROM {table_name} ORDER BY kumi"
    ) == [
        {
            "kumi": "0102",
            "odds": 14.0,
            "collectedat": "2026-09-01T09:30:00+09:00",
        },
        {
            "kumi": "0203",
            "odds": 10.0,
            "collectedat": "2026-09-01T02:00:00+00:00",
        },
        {"kumi": "0304", "odds": 15.0, "collectedat": None},
    ]


def test_postgresql_legacy_sokuho_key_migration(postgresql_timeseries_db):
    from src.database.migration import migrate_table_if_needed

    database = postgresql_timeseries_db
    current_schema = SCHEMAS["TS_SOKUHO_O2"]
    legacy_schema = current_schema.replace(
        "HassoTime, SourceSpec)",
        "HassoTime, SourceSpec, CollectedAt)",
    )
    database.execute(legacy_schema)
    database.commit()
    database.insert(
        "TS_SOKUHO_O2",
        _sokuho_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
    )
    database.insert(
        "TS_SOKUHO_O2",
        _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
    )
    database.commit()

    assert migrate_table_if_needed(database, "TS_SOKUHO_O2", current_schema) is True
    assert database.fetch_all("SELECT odds, collectedat FROM TS_SOKUHO_O2") == [
        {"odds": 12.5, "collectedat": "2026-09-01T09:30:00+09:00"}
    ]
    assert database._get_primary_key_columns("TS_SOKUHO_O2")[-1] == "sourcespec"
    assert (
        database.fetch_all(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND tablename LIKE '__jltsql_%'"
        )
        == []
    )


def test_postgresql_sokuho_migration_locks_out_concurrent_correction(
    postgresql_timeseries_db,
):
    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.migration import migrate_table_if_needed
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = postgresql_timeseries_db
    current_schema = database.fetch_one("SELECT current_schema() AS name")["name"]
    current_table_schema = SCHEMAS["TS_SOKUHO_O2"]
    legacy_schema = current_table_schema.replace(
        "HassoTime, SourceSpec)",
        "HassoTime, SourceSpec, CollectedAt)",
    )
    database.execute(legacy_schema)
    database.commit()
    database.insert(
        "TS_SOKUHO_O2",
        _sokuho_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
    )
    database.insert(
        "TS_SOKUHO_O2",
        _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
    )
    database.commit()

    collector = PostgreSQLDatabase(postgresql_test_config())
    collector.connect()
    collector.execute(f"SET search_path TO {current_schema}")
    collector.commit()
    lock_acquired = Event()
    release_migration = Event()
    correction_started = Event()
    correction_finished = Event()
    errors = []
    original_execute = database.execute

    def guarded_execute(sql, parameters=None):
        result = original_execute(sql, parameters)
        if sql.startswith("LOCK TABLE"):
            lock_acquired.set()
            if not release_migration.wait(5):
                raise AssertionError("test did not release PostgreSQL migration lock")
        return result

    def migrate():
        try:
            migrate_table_if_needed(database, "TS_SOKUHO_O2", current_table_schema)
        except Exception as exc:  # pragma: no cover - reported by assertion below
            errors.append(exc)

    def write_correction():
        correction_started.set()
        try:
            collector.insert(
                "TS_SOKUHO_O2",
                _sokuho_o2_row(collected_at="2026-09-01T03:10:00+00:00", odds=15.0),
            )
            collector.commit()
        except Exception as exc:  # pragma: no cover - reported by assertion below
            errors.append(exc)
        finally:
            correction_finished.set()

    database.execute = guarded_execute  # type: ignore[method-assign]
    migration_thread = Thread(target=migrate)
    correction_thread = Thread(target=write_correction)
    try:
        migration_thread.start()
        assert lock_acquired.wait(5)
        correction_thread.start()
        assert correction_started.wait(5)
        assert correction_finished.wait(0.25) is False
        release_migration.set()
        migration_thread.join(10)
        correction_thread.join(10)
        assert migration_thread.is_alive() is False
        assert correction_thread.is_alive() is False
        # This writer resolved the old PK before it blocked on the table lock,
        # so PostgreSQL rejects its now-stale ON CONFLICT target visibly after
        # the migration. The correction was not silently inserted and deleted.
        assert len(errors) == 1
        assert "no unique or exclusion constraint" in str(errors[0])
        assert database.fetch_all("SELECT odds, collectedat FROM TS_SOKUHO_O2") == [
            {"odds": 12.5, "collectedat": "2026-09-01T09:30:00+09:00"}
        ]

        # A normal retry resolves the new identity and applies the correction.
        collector.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T03:10:00+00:00", odds=15.0),
        )
        collector.commit()
        assert database.fetch_all("SELECT odds, collectedat FROM TS_SOKUHO_O2") == [
            {"odds": 15.0, "collectedat": "2026-09-01T09:30:00+09:00"}
        ]
    finally:
        release_migration.set()
        if migration_thread.ident is not None:
            migration_thread.join(10)
        if correction_thread.ident is not None:
            correction_thread.join(10)
        database.execute = original_execute  # type: ignore[method-assign]
        collector.disconnect()
