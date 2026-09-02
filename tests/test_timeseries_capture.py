"""Decision-time provenance contracts for time-series odds writes."""

import os
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


def _raw_insert(database, table_name: str, row: dict) -> None:
    """Seed legacy schemas without passing through the guarded writer."""
    columns = list(row)
    placeholders = ", ".join("?" for _ in columns)
    database.execute(
        f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(row[column] for column in columns),
    )


def _legacy_sokuho_schema(table_name: str) -> str:
    return SCHEMAS[table_name].replace(
        "HassoTime, SourceSpec)",
        "HassoTime, SourceSpec, CollectedAt)",
    )


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
    from src.database.migration import (
        SchemaMigrationError,
        apply_sokuho_capture_identity_migration,
        preview_sokuho_capture_identity_migration,
    )

    database = SQLiteDatabase({"path": str(tmp_path / "legacy-sokuho.db")})
    database.connect()
    try:
        current_schema = SCHEMAS["TS_SOKUHO_O2"]
        legacy_schema = _legacy_sokuho_schema("TS_SOKUHO_O2").replace(
            "Odds REAL,", "Odds REAL CHECK (Odds >= 0),"
        )
        database.create_table("TS_SOKUHO_O2", legacy_schema)
        _raw_insert(
            database,
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
        )
        _raw_insert(
            database,
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
        )
        database.commit()
        schema_before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE name = 'TS_SOKUHO_O2'"
        )["sql"]

        with pytest.raises(SchemaMigrationError) as startup_error:
            prepare_time_series_odds_table(database, "TS_SOKUHO_O2")
        assert "TS_SOKUHO_O2 uses the legacy primary key ending in CollectedAt" in str(
            startup_error.value
        )
        assert "backup and rebuild" in str(startup_error.value)
        assert "migrate-sokuho-capture-identity" not in str(startup_error.value)
        assert "--apply" not in str(startup_error.value)

        with pytest.raises(SchemaMigrationError) as write_error:
            database.insert(
                "TS_SOKUHO_O2",
                _sokuho_o2_row(
                    collected_at="2026-09-01T02:00:00+00:00",
                    odds=15.0,
                ),
            )
        assert str(write_error.value) == str(startup_error.value)

        for operator_function in (
            preview_sokuho_capture_identity_migration,
            apply_sokuho_capture_identity_migration,
        ):
            with pytest.raises(
                SchemaMigrationError,
                match="SQLite migration refused.*back up.*rebuild",
            ):
                operator_function(database, ["TS_SOKUHO_O2"])

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


def test_dual_write_preflights_legacy_secondary_before_primary_mutation(tmp_path):
    from src.database.dual_handler import DualDatabase
    from src.database.migration import SchemaMigrationError

    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    database = DualDatabase(primary, secondary)
    database.connect()
    try:
        primary.execute(SCHEMAS["TS_SOKUHO_O2"])
        secondary.execute(_legacy_sokuho_schema("TS_SOKUHO_O2"))
        _raw_insert(
            secondary,
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00"),
        )
        primary.commit()
        secondary.commit()

        with pytest.raises(
            SchemaMigrationError,
            match="TS_SOKUHO_O2.*backup and rebuild",
        ) as error:
            database.insert(
                "TS_SOKUHO_O2",
                _sokuho_o2_row(collected_at="2026-09-01T02:00:00+00:00"),
            )

        assert "migrate-sokuho-capture-identity" not in str(error.value)
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM TS_SOKUHO_O2") == {"count": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS count FROM TS_SOKUHO_O2") == {"count": 1}
    finally:
        database.disconnect()


def test_dual_write_names_postgresql_override_for_legacy_postgresql_target(tmp_path):
    from src.database.dual_handler import DualDatabase
    from src.database.migration import (
        SchemaMigrationError,
        _extract_primary_key_columns,
    )
    from src.database.postgresql_handler import PostgreSQLDatabase

    primary = SQLiteDatabase({"path": str(tmp_path / "dual-primary.db")})
    primary.connect()
    primary.execute(SCHEMAS["TS_SOKUHO_O2"])
    primary.commit()
    secondary = PostgreSQLDatabase({})
    secondary._connection = object()
    expected_pk = _extract_primary_key_columns(SCHEMAS["TS_SOKUHO_O2"])
    assert expected_pk is not None
    secondary.fetch_all = MagicMock(  # type: ignore[method-assign]
        return_value=[{"name": column.lower()} for column in [*expected_pk, "CollectedAt"]]
    )
    database = DualDatabase(primary, secondary)

    try:
        with pytest.raises(SchemaMigrationError) as error:
            database.insert(
                "TS_SOKUHO_O2",
                _sokuho_o2_row(collected_at="2026-09-01T02:00:00+00:00"),
            )

        assert (
            "jltsql db migrate-sokuho-capture-identity --db postgresql " "--table TS_SOKUHO_O2."
        ) in str(error.value)
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM TS_SOKUHO_O2") == {"count": 0}
    finally:
        primary.disconnect()
        secondary._connection = None


@pytest.mark.parametrize("write_method", ["insert", "insert_many"])
def test_dual_sokuho_startup_and_write_refuse_disconnected_secondary(
    tmp_path,
    write_method,
):
    from src.database.dual_handler import DualDatabase
    from src.database.migration import SchemaMigrationError

    primary = SQLiteDatabase({"path": str(tmp_path / f"primary-{write_method}.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / f"secondary-{write_method}.db")})
    primary.connect()
    primary.execute(SCHEMAS["TS_SOKUHO_O2"].replace("            Odds REAL,\n", ""))
    primary.commit()
    database = DualDatabase(primary, secondary)

    try:
        with pytest.raises(SchemaMigrationError, match="not connected"):
            prepare_time_series_odds_table(database, "TS_SOKUHO_O2")
        columns_after_refusal = {
            row["name"].lower() for row in primary.fetch_all('PRAGMA table_info("TS_SOKUHO_O2")')
        }
        assert "odds" not in columns_after_refusal

        row = _sokuho_o2_row(collected_at="2026-09-01T02:00:00+00:00")
        payload = [row] if write_method == "insert_many" else row
        with pytest.raises(SchemaMigrationError, match="not connected"):
            getattr(database, write_method)("TS_SOKUHO_O2", payload)

        assert primary.fetch_one("SELECT COUNT(*) AS count FROM TS_SOKUHO_O2") == {"count": 0}
    finally:
        primary.disconnect()


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


@pytest.mark.parametrize("write_method", ["insert", "insert_many"])
def test_schema_qualified_sqlite_sokuho_write_fails_closed(tmp_path, write_method):
    from src.database.migration import SchemaMigrationError

    database = SQLiteDatabase({"path": str(tmp_path / f"qualified-{write_method}.db")})
    database.connect()
    try:
        database.execute(_legacy_sokuho_schema("TS_SOKUHO_O2"))
        row = _sokuho_o2_row(collected_at="2026-09-01T03:00:00+00:00")
        payload = [row] if write_method == "insert_many" else row

        with pytest.raises(SchemaMigrationError, match="legacy primary key") as startup_error:
            prepare_time_series_odds_table(database, "main.TS_SOKUHO_O2")
        with pytest.raises(SchemaMigrationError, match="legacy primary key") as error:
            getattr(database, write_method)("main.TS_SOKUHO_O2", payload)

        assert str(error.value) == str(startup_error.value)
        assert "main.TS_SOKUHO_O2 uses the legacy primary key" in str(error.value)
        assert "backup and rebuild" in str(error.value)
        assert "migrate-sokuho-capture-identity" not in str(error.value)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM TS_SOKUHO_O2") == {"count": 0}
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


def test_postgresql_sokuho_write_fails_closed_when_primary_key_catalog_is_unreadable():
    from src.database.base import DatabaseError
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase({})
    database.fetch_all = MagicMock(  # type: ignore[method-assign]
        side_effect=DatabaseError("catalog unavailable")
    )
    database.execute = MagicMock(return_value=1)  # type: ignore[method-assign]

    with pytest.raises(DatabaseError, match="catalog unavailable"):
        database.insert(
            "TS_SOKUHO_O2",
            _sokuho_o2_row(collected_at="2026-09-01T03:00:00+00:00"),
        )

    database.execute.assert_not_called()


def test_postgresql_schema_qualified_legacy_message_preserves_schema():
    from src.database.migration import legacy_sokuho_capture_identity_message
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase({})
    message = legacy_sokuho_capture_identity_message(database, "archive.TS_SOKUHO_O2")

    assert "archive.TS_SOKUHO_O2 uses the legacy primary key" in message
    assert (
        "jltsql db migrate-sokuho-capture-identity --db postgresql "
        "--schema archive --table TS_SOKUHO_O2."
    ) in message
    assert "read-only dry run (the default; it does not change data)" in message
    assert "--apply mutates the table" in message


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


def _create_postgresql_legacy_sokuho(database, table_name: str) -> None:
    odds_number = int(table_name.rsplit("O", 1)[1])

    def row(*, collected_at: str, odds: float) -> dict:
        record = _sokuho_o2_row(collected_at=collected_at, odds=odds)
        record["RecordSpec"] = f"O{odds_number}"
        record["SourceSpec"] = f"0B3{odds_number}"
        if odds_number == 3:
            record["OddsLow"] = record.pop("Odds")
            record["OddsHigh"] = odds + 1.0
        return record

    database.execute(_legacy_sokuho_schema(table_name))
    _raw_insert(
        database,
        table_name,
        row(
            collected_at="2026-09-01T09:30:00+09:00",
            odds=10.0,
        ),
    )
    _raw_insert(
        database,
        table_name,
        row(
            collected_at="2026-09-01T01:00:00+00:00",
            odds=12.5,
        ),
    )
    database.commit()


def test_postgresql_sokuho_startup_and_write_fail_closed_then_explicit_migration(
    postgresql_timeseries_db,
):
    from src.database.migration import (
        SchemaMigrationError,
        apply_sokuho_capture_identity_migration,
        preview_sokuho_capture_identity_migration,
    )

    database = postgresql_timeseries_db
    table_name = "TS_SOKUHO_O2"
    _create_postgresql_legacy_sokuho(database, table_name)
    before_rows = database.fetch_all(
        f"SELECT odds, collectedat FROM {table_name} ORDER BY collectedat"
    )
    database.rollback()

    with pytest.raises(SchemaMigrationError) as startup_error:
        prepare_time_series_odds_table(database, table_name)
    assert (
        "jltsql db migrate-sokuho-capture-identity --db postgresql " "--table TS_SOKUHO_O2."
    ) in str(startup_error.value)
    database.rollback()

    with pytest.raises(SchemaMigrationError) as write_error:
        database.insert(
            table_name,
            _sokuho_o2_row(
                collected_at="2026-09-01T03:10:00+00:00",
                odds=15.0,
            ),
        )
    assert str(write_error.value) == str(startup_error.value)
    database.rollback()

    executed_sql = []
    original_execute = database.execute

    def tracked_execute(sql, parameters=None):
        executed_sql.append(sql)
        return original_execute(sql, parameters)

    database.execute = tracked_execute  # type: ignore[method-assign]
    try:
        reports = preview_sokuho_capture_identity_migration(database, [table_name])
    finally:
        database.execute = original_execute  # type: ignore[method-assign]

    assert len(reports) == 1
    report = reports[0]
    assert report.status == "legacy"
    assert report.total_rows == 2
    assert report.distinct_publication_groups == 1
    assert report.rows_to_delete == 1
    assert report.collected_at_rewrite_groups == 1
    assert any("REPEATABLE READ READ ONLY" in sql for sql in executed_sql)
    assert not any("ACCESS EXCLUSIVE" in sql for sql in executed_sql)
    assert (
        database.fetch_all(f"SELECT odds, collectedat FROM {table_name} ORDER BY collectedat")
        == before_rows
    )
    assert database._get_primary_key_columns(table_name)[-1] == "collectedat"
    database.rollback()

    executed_sql = []
    database.execute = tracked_execute  # type: ignore[method-assign]
    try:
        applied_reports = apply_sokuho_capture_identity_migration(database, [table_name])
    finally:
        database.execute = original_execute  # type: ignore[method-assign]

    assert applied_reports[0].applied is True
    lock_index = next(
        index for index, sql in enumerate(executed_sql) if sql.startswith("LOCK TABLE")
    )
    snapshot_index = next(
        index for index, sql in enumerate(executed_sql) if sql.startswith("CREATE TEMP TABLE")
    )
    assert lock_index < snapshot_index
    assert database.fetch_all(f"SELECT odds, collectedat FROM {table_name}") == [
        {"odds": 12.5, "collectedat": "2026-09-01T09:30:00+09:00"}
    ]
    assert database._get_primary_key_columns(table_name)[-1] == "sourcespec"
    assert (
        database.fetch_all(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND tablename LIKE '__jltsql_%'"
        )
        == []
    )
    database.rollback()

    database.insert(
        table_name,
        _sokuho_o2_row(
            collected_at="2026-09-01T03:10:00+00:00",
            odds=15.0,
        ),
    )
    database.commit()
    assert database.fetch_all(f"SELECT odds, collectedat FROM {table_name}") == [
        {"odds": 15.0, "collectedat": "2026-09-01T09:30:00+09:00"}
    ]


def test_postgresql_sokuho_migration_table_restriction(postgresql_timeseries_db):
    from src.database.migration import apply_sokuho_capture_identity_migration

    database = postgresql_timeseries_db
    _create_postgresql_legacy_sokuho(database, "TS_SOKUHO_O3")
    _create_postgresql_legacy_sokuho(database, "TS_SOKUHO_O4")

    reports = apply_sokuho_capture_identity_migration(
        database,
        ["TS_SOKUHO_O3"],
    )

    assert [report.table_name for report in reports] == ["TS_SOKUHO_O3"]
    assert database._get_primary_key_columns("TS_SOKUHO_O3")[-1] == "sourcespec"
    assert database._get_primary_key_columns("TS_SOKUHO_O4")[-1] == "collectedat"


def test_postgresql_sokuho_migration_preserves_schema_qualified_target(
    postgresql_timeseries_db,
):
    from src.database.migration import (
        apply_sokuho_capture_identity_migration,
        preview_sokuho_capture_identity_migration,
    )

    database = postgresql_timeseries_db
    schema_name = f"jltsql_sokuho_{uuid4().hex}"
    table_name = f"{schema_name}.TS_SOKUHO_O2"
    legacy_schema = _legacy_sokuho_schema("TS_SOKUHO_O2").replace(
        "CREATE TABLE IF NOT EXISTS TS_SOKUHO_O2",
        f"CREATE TABLE IF NOT EXISTS {table_name}",
        1,
    )
    database.execute(f"CREATE SCHEMA {schema_name}")
    database.execute(legacy_schema)
    _raw_insert(
        database,
        table_name,
        _sokuho_o2_row(collected_at="2026-09-01T09:30:00+09:00", odds=10.0),
    )
    _raw_insert(
        database,
        table_name,
        _sokuho_o2_row(collected_at="2026-09-01T01:00:00+00:00", odds=12.5),
    )
    database.commit()

    try:
        preview = preview_sokuho_capture_identity_migration(database, [table_name])
        assert preview[0].table_name == table_name
        assert preview[0].rows_to_delete == 1

        applied = apply_sokuho_capture_identity_migration(database, [table_name])
        assert applied[0].table_name == table_name
        assert database._get_primary_key_columns(table_name)[-1] == "sourcespec"
        assert database.fetch_all(f"SELECT odds, collectedat FROM {table_name}") == [
            {"odds": 12.5, "collectedat": "2026-09-01T09:30:00+09:00"}
        ]
    finally:
        database.rollback()
        database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        database.commit()


def test_sokuho_apply_rolls_back_if_unlocked_table_becomes_legacy(monkeypatch):
    import src.database.migration as migration

    database = MagicMock()
    database.get_db_type.return_value = "postgresql"
    database.has_pending_transaction.return_value = False
    expected_pk = migration._expected_sokuho_primary_key("TS_SOKUHO_O2")
    classifications = iter(
        [
            ("current", expected_pk, expected_pk),
            ("legacy", [*expected_pk, "CollectedAt"], expected_pk),
        ]
    )
    monkeypatch.setattr(
        migration,
        "_classify_sokuho_table",
        lambda _database, _table_name: next(classifications),
    )

    with pytest.raises(
        migration.SchemaMigrationError,
        match="before an ACCESS EXCLUSIVE lock was acquired",
    ):
        migration.apply_sokuho_capture_identity_migration(database, ["TS_SOKUHO_O2"])

    database.rollback.assert_called_once_with()
    database.commit.assert_not_called()


def test_postgresql_sokuho_migration_rolls_back_every_table_on_failure(
    postgresql_timeseries_db,
):
    from src.database.migration import (
        SchemaMigrationError,
        apply_sokuho_capture_identity_migration,
    )

    database = postgresql_timeseries_db
    table_names = ["TS_SOKUHO_O5", "TS_SOKUHO_O6"]
    for table_name in table_names:
        _create_postgresql_legacy_sokuho(database, table_name)

    original_execute = database.execute

    def injected_failure(sql, parameters=None):
        if sql.startswith("ALTER TABLE ts_sokuho_o6 DROP CONSTRAINT"):
            raise RuntimeError("injected migration failure")
        return original_execute(sql, parameters)

    database.execute = injected_failure  # type: ignore[method-assign]
    try:
        with pytest.raises(SchemaMigrationError, match="injected migration failure"):
            apply_sokuho_capture_identity_migration(database, table_names)
    finally:
        database.execute = original_execute  # type: ignore[method-assign]

    for table_name in table_names:
        assert database._get_primary_key_columns(table_name)[-1] == "collectedat"
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 2}
    assert (
        database.fetch_all(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND tablename LIKE '__jltsql_%'"
        )
        == []
    )


def test_postgresql_sokuho_migration_rejects_invalid_collected_at(
    postgresql_timeseries_db,
):
    from src.database.migration import (
        SchemaMigrationError,
        apply_sokuho_capture_identity_migration,
        preview_sokuho_capture_identity_migration,
    )

    database = postgresql_timeseries_db
    table_name = "TS_SOKUHO_O2"
    database.execute(_legacy_sokuho_schema(table_name))
    _raw_insert(
        database,
        table_name,
        _sokuho_o2_row(collected_at="not-an-offset-timestamp"),
    )
    database.commit()

    for operator_function in (
        preview_sokuho_capture_identity_migration,
        apply_sokuho_capture_identity_migration,
    ):
        with pytest.raises(
            SchemaMigrationError,
            match="invalid offset-aware CollectedAt",
        ):
            operator_function(database, [table_name])

    assert database._get_primary_key_columns(table_name)[-1] == "collectedat"
    assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 1}
