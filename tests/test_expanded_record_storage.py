#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SQLite/PostgreSQL storage tests for expanded JV-Data parser rows."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer import importer as importer_module
from src.importer.importer import DataImporter, ImporterError
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.av_parser import AVParser
from src.parser.o1_parser import O1Parser
from src.parser.o2_parser import O2Parser
from src.realtime.updater import RealtimeUpdater


def _pad(value: str, length: int) -> bytes:
    return str(value).encode("cp932").ljust(length, b" ")[:length]


def _odds_header(record_type: str, race_num: str = "11", data_kubun: str = "4") -> bytes:
    return (
        record_type.encode("ascii")
        + data_kubun.encode("ascii")
        + b"20260419"
        + b"2026"
        + b"0419"
        + b"06"
        + b"03"
        + b"08"
        + race_num.encode("ascii")
        + b"04191549"
        + b"18"
        + b"18"
    )


def _make_o1_record(data_kubun: str = "4") -> bytes:
    header = _odds_header("O1", data_kubun=data_kubun) + b"7773"
    tan = b"01012301" + b"02045602" + b"0" * (26 * 8)
    fuku = b"010010002001" + b"020030004002" + b"0" * (26 * 12)
    wakuren = b"120123401" + b"130567802" + b"0" * (34 * 9)
    votes = b"000000001230000000045600000000789\r\n"
    raw = header + tan + fuku + wakuren + votes
    assert len(raw) == O1Parser.RECORD_LENGTH
    return raw


def _make_o1_erase_record() -> bytes:
    header = _odds_header("O1", data_kubun="0") + b"0000"
    raw = header + b" " * (O1Parser.RECORD_LENGTH - len(header) - 2) + b"\r\n"
    assert len(raw) == O1Parser.RECORD_LENGTH
    return raw


def _make_empty_o2_record() -> bytes:
    raw = _odds_header("O2") + b"7" + b"0" * (153 * 13) + b"00000000999\r\n"
    assert len(raw) == O2Parser.RECORD_LENGTH
    return raw


def _make_av_record(data_kubun: str = "1") -> bytes:
    raw = (
        b"AV"
        + data_kubun.encode("ascii")
        + b"20260419"
        + b"2026"
        + b"0419"
        + b"06"
        + b"03"
        + b"08"
        + b"11"
        + b"04190930"
        + b"05"
        + _pad("テストホース", 36)
        + b"001"
        + b"\r\n"
    )
    assert len(raw) == AVParser.RECORD_LENGTH
    return raw


def _flatten(parsed):
    return parsed if isinstance(parsed, list) else [parsed]


def _create_tables(db, table_names):
    for table_name in table_names:
        db.execute(SCHEMAS[table_name])
    db.commit()


def _create_jravan_tables(db, table_names):
    for table_name in table_names:
        db.execute(JRAVAN_SCHEMAS[table_name])
    db.commit()


@pytest.fixture
def sqlite_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = SQLiteDatabase({"path": str(Path(tmpdir) / "storage.db")})
        db.connect()
        try:
            yield db
        finally:
            db.disconnect()


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL storage tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    config = {
        "host": os.getenv("POSTGRES_HOST") or os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT") or os.getenv("PGPORT", "5432")),
        "database": os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "jltsql_test"),
        "user": os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "jltsql"),
        "password": os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", ""),
        "connect_timeout": 5,
    }
    db = PostgreSQLDatabase(config)
    schema_name = f"jlt_storage_{uuid4().hex[:12]}"
    db.connect()
    try:
        db.execute(f"CREATE SCHEMA {schema_name}")
        db.execute(f"SET search_path TO {schema_name}")
        db.commit()
        yield db
    finally:
        try:
            db.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            db.commit()
        finally:
            db.disconnect()


def _assert_o1_storage(db, table_name: str):
    rows = db.fetch_all(
        f"""
        SELECT
            Umaban AS umaban,
            Kumi AS kumi,
            TanOdds AS tanodds,
            FukuOddsHigh AS fukuoddshigh,
            WakurenOdds AS wakurenodds
        FROM {table_name}
        ORDER BY Umaban, Kumi
        """
    )
    assert len(rows) == 4
    wakuren_rows = [row for row in rows if row["umaban"] == 0]
    assert [(row["kumi"], row["wakurenodds"]) for row in wakuren_rows] == [
        ("12", 123.4),
        ("13", 567.8),
    ]


def test_sqlite_importer_stores_heterogeneous_o1_rows(sqlite_db):
    _create_tables(sqlite_db, ["NL_O1"])
    rows = _flatten(O1Parser().parse(_make_o1_record()))

    stats = DataImporter(sqlite_db, batch_size=100).import_records(iter(rows))

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    _assert_o1_storage(sqlite_db, "NL_O1")


def test_sqlite_realtime_batch_stores_heterogeneous_o1_rows(sqlite_db):
    _create_tables(sqlite_db, ["RT_O1"])
    rows = _flatten(O1Parser().parse(_make_o1_record()))

    result = RealtimeUpdater(sqlite_db).process_parsed_records_batch(rows)

    assert result["success"] is True
    assert result["inserted"] == 4
    _assert_o1_storage(sqlite_db, "RT_O1")


def test_sqlite_importer_skips_empty_expanded_o2_header_row(sqlite_db):
    _create_tables(sqlite_db, ["NL_O2"])
    rows = _flatten(O2Parser().parse(_make_empty_o2_record()))

    stats = DataImporter(sqlite_db, batch_size=100).import_records(iter(rows))

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    count = sqlite_db.fetch_one("SELECT COUNT(*) AS cnt FROM NL_O2")
    assert count["cnt"] == 0


def test_sqlite_realtime_delete_removes_expanded_o1_record(sqlite_db):
    _create_tables(sqlite_db, ["RT_O1"])
    updater = RealtimeUpdater(sqlite_db)
    rows = _flatten(O1Parser().parse(_make_o1_record()))
    assert updater.process_parsed_records_batch(rows)["inserted"] == 4

    delete_rows = _flatten(O1Parser().parse(_make_o1_record(data_kubun="0")))
    result = updater.process_parsed_record(delete_rows[0])

    assert result["success"] is True
    count = sqlite_db.fetch_one("SELECT COUNT(*) AS cnt FROM RT_O1")
    assert count["cnt"] == 0


def _assert_realtime_batch_retains_cancellation_then_applies_zero_erase(db):
    _create_tables(db, ["RT_O1"])
    updater = RealtimeUpdater(db)

    initial = _flatten(O1Parser().parse(_make_o1_record(data_kubun="4")))
    erase = _flatten(O1Parser().parse(_make_o1_erase_record()))
    cancelled = _flatten(O1Parser().parse(_make_o1_record(data_kubun="9")))
    result = updater.process_parsed_records_batch([*initial, *erase, *cancelled])
    assert result["success"] is True
    assert result["inserted"] == 9
    statuses = db.fetch_all("SELECT DISTINCT DataKubun AS status FROM RT_O1")
    assert statuses == [{"status": "9"}]

    result = updater.process_parsed_records_batch(erase)
    assert result["success"] is True
    count = db.fetch_one("SELECT COUNT(*) AS cnt FROM RT_O1")
    assert count["cnt"] == 0


def test_sqlite_realtime_batch_retains_cancellation_then_applies_zero_erase(sqlite_db):
    _assert_realtime_batch_retains_cancellation_then_applies_zero_erase(sqlite_db)


def _assert_historical_importer_retains_cancellation_then_applies_zero_erase(
    db,
    importer_class,
):
    _create_tables(db, ["NL_RA", "NL_O1"])
    importer = importer_class(db, batch_size=100)
    race_key = {
        "RecordSpec": "RA",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
    }

    stats = importer.import_records(
        iter(
            [
                {**race_key, "DataKubun": "1"},
                {**race_key, "DataKubun": "0"},
                {**race_key, "headDataKubun": "9"},
            ]
        )
    )
    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 3
    race = db.fetch_one("SELECT DataKubun AS status FROM NL_RA")
    assert race == {"status": "9"}

    initial_odds = _flatten(O1Parser().parse(_make_o1_record(data_kubun="4")))
    erase = _flatten(O1Parser().parse(_make_o1_erase_record()))
    cancelled_odds = _flatten(O1Parser().parse(_make_o1_record(data_kubun="9")))
    stats = importer.import_records(iter([*initial_odds, *erase, *cancelled_odds]))
    assert stats["records_imported"] == 9
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 3
    statuses = db.fetch_all("SELECT DISTINCT DataKubun AS status FROM NL_O1")
    assert statuses == [{"status": "9"}]

    stats = importer.import_records(
        iter([{**race_key, "headDataKubun": "0"}, *erase])
    )
    assert stats["records_imported"] == 2
    assert stats["records_failed"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM NL_RA")["cnt"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM NL_O1")["cnt"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_historical_importers_retain_cancellation_then_apply_zero_erase(
    sqlite_db,
    importer_class,
):
    _assert_historical_importer_retains_cancellation_then_applies_zero_erase(
        sqlite_db,
        importer_class,
    )


def test_postgresql_realtime_batch_retains_cancellation_then_applies_zero_erase(
    postgresql_db,
):
    _assert_realtime_batch_retains_cancellation_then_applies_zero_erase(postgresql_db)


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_postgresql_historical_importers_retain_cancellation_then_apply_zero_erase(
    postgresql_db,
    importer_class,
):
    _assert_historical_importer_retains_cancellation_then_applies_zero_erase(
        postgresql_db,
        importer_class,
    )


def _assert_standard_race_retains_legacy_cancellation_then_applies_current_erase(
    db,
    importer_class,
):
    _create_jravan_tables(db, ["RACE"])
    importer = importer_class(db, use_jravan_schema=True)
    race_key = {
        "RecordSpec": "RA",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
    }

    stats = importer.import_records(iter([{**race_key, "headDataKubun": "9"}]))
    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert db.fetch_one("SELECT DataKubun AS status FROM RACE") == {"status": "9"}

    stats = importer.import_records(iter([{**race_key, "DataKubun": "0"}]))
    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM RACE")["cnt"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_race_cancellation_and_erase(sqlite_db, importer_class):
    _assert_standard_race_retains_legacy_cancellation_then_applies_current_erase(
        sqlite_db,
        importer_class,
    )


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_postgresql_standard_race_cancellation_and_erase(postgresql_db, importer_class):
    _assert_standard_race_retains_legacy_cancellation_then_applies_current_erase(
        postgresql_db,
        importer_class,
    )


def _assert_standard_o1_preserves_header_and_split_children(db, importer_class):
    _create_jravan_tables(
        db,
        ["ODDS_TANPUKUWAKU_HEAD", "ODDS_TANPUKU", "ODDS_WAKU"],
    )
    # The horse and bracket portions cross a flush boundary, so a later
    # partial header must not erase vote totals from the earlier portion.
    importer = importer_class(db, use_jravan_schema=True, batch_size=2)
    cancelled = _flatten(O1Parser().parse(_make_o1_record(data_kubun="9")))

    stats = importer.import_records(iter(cancelled))

    assert stats["records_failed"] == 0
    header = db.fetch_one(
        "SELECT COUNT(*) AS cnt, MAX(HappyoTime) AS happyo_time, "
        "MAX(TotalHyosuTansyo) AS tan_votes, "
        "MAX(TotalHyosuFukusyo) AS fuku_votes, "
        "MAX(TotalHyosuWakuren) AS waku_votes "
        "FROM ODDS_TANPUKUWAKU_HEAD "
        "WHERE DataKubun = '9'"
    )
    assert header == {
        "cnt": 1,
        "happyo_time": "04191549",
        "tan_votes": "00000000123",
        "fuku_votes": "00000000456",
        "waku_votes": "00000000789",
    }
    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM ODDS_TANPUKU")["cnt"] == 2
    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM ODDS_WAKU")["cnt"] == 2

    stats = importer.import_records(
        iter(_flatten(O1Parser().parse(_make_o1_erase_record())))
    )
    assert stats["records_failed"] == 0
    for table_name in (
        "ODDS_TANPUKUWAKU_HEAD",
        "ODDS_TANPUKU",
        "ODDS_WAKU",
    ):
        assert db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table_name}")["cnt"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_o1_preserves_header_and_split_children(
    sqlite_db,
    importer_class,
):
    _assert_standard_o1_preserves_header_and_split_children(sqlite_db, importer_class)


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_postgresql_standard_o1_preserves_header_and_split_children(
    postgresql_db,
    importer_class,
):
    _assert_standard_o1_preserves_header_and_split_children(
        postgresql_db,
        importer_class,
    )


_STANDARD_ODDS_CASES = (
    (
        "O2",
        "ODDS_UMAREN_HEAD",
        "ODDS_UMAREN",
        {"UmarenFlag": "1", "Kumi": "0102", "Odds": "012340", "Ninki": "001"},
    ),
    (
        "O3",
        "ODDS_WIDE_HEAD",
        "ODDS_WIDE",
        {
            "WideFlag": "1",
            "Kumi": "0102",
            "OddsLow": "00123",
            "OddsHigh": "00456",
            "Ninki": "001",
        },
    ),
    (
        "O4",
        "ODDS_UMATAN_HEAD",
        "ODDS_UMATAN",
        {"UmatanFlag": "1", "Kumi": "0102", "Odds": "012340", "Ninki": "001"},
    ),
    (
        "O5",
        "ODDS_SANREN_HEAD",
        "ODDS_SANREN",
        {
            "SanrenpukuFlag": "1",
            "Kumi": "010203",
            "Odds": "012340",
            "Ninki": "001",
        },
    ),
    (
        "O6",
        "ODDS_SANRENTAN_HEAD",
        "ODDS_SANRENTAN",
        {
            "SanrentanFlag": "1",
            "Kumi": "010203",
            "Odds": "012340",
            "Ninki": "0001",
        },
    ),
)


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("record_type", "header_table", "child_table", "child_fields"),
    _STANDARD_ODDS_CASES,
)
def test_sqlite_standard_o2_o6_header_child_upsert_and_erase(
    sqlite_db,
    importer_class,
    record_type,
    header_table,
    child_table,
    child_fields,
):
    _create_jravan_tables(sqlite_db, [header_table, child_table])
    importer = importer_class(sqlite_db, use_jravan_schema=True, batch_size=100)
    base = {
        "RecordSpec": record_type,
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HassoTime": "04191549",
        "TorokuTosu": "18",
        "SyussoTosu": "18",
        "Vote": "00000123456",
        **child_fields,
    }

    assert importer.import_records(iter([{**base, "DataKubun": "9"}]))[
        "records_failed"
    ] == 0
    assert importer.import_records(iter([{**base, "DataKubun": "2"}]))[
        "records_failed"
    ] == 0
    header = sqlite_db.fetch_one(
        f"SELECT COUNT(*) AS cnt, MAX(DataKubun) AS status, "
        f"MAX(HappyoTime) AS happyo_time FROM {header_table}"
    )
    assert header == {"cnt": 1, "status": "2", "happyo_time": "04191549"}
    assert sqlite_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {child_table}")[
        "cnt"
    ] == 1

    erase = {
        key: value
        for key, value in base.items()
        if key
        in {
            "RecordSpec",
            "MakeDate",
            "Year",
            "MonthDay",
            "JyoCD",
            "Kaiji",
            "Nichiji",
            "RaceNum",
        }
    }
    erase["DataKubun"] = "0"
    assert importer.import_records(iter([erase]))["records_failed"] == 0
    assert sqlite_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {header_table}")[
        "cnt"
    ] == 0
    assert sqlite_db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {child_table}")[
        "cnt"
    ] == 0


def _assert_standard_odds_duplicate_existing_keys_fail_closed(db):
    _create_jravan_tables(db, ["ODDS_UMAREN_HEAD", "ODDS_UMAREN"])
    duplicate_key = (2026, 419, "06", 3, 8, 11)
    for status in ("1", "2"):
        db.execute(
            "INSERT INTO ODDS_UMAREN_HEAD "
            "(DataKubun, Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (status, *duplicate_key),
        )
    db.commit()
    record = {
        "RecordSpec": "O2",
        "DataKubun": "9",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
    }

    with pytest.raises(SchemaMigrationError, match="duplicate official keys"):
        DataImporter(db, use_jravan_schema=True).import_records(iter([record]))

    assert db.fetch_one("SELECT COUNT(*) AS cnt FROM ODDS_UMAREN_HEAD")["cnt"] == 2


def test_sqlite_standard_odds_duplicate_existing_keys_fail_closed(sqlite_db):
    _assert_standard_odds_duplicate_existing_keys_fail_closed(sqlite_db)


def test_postgresql_standard_odds_duplicate_existing_keys_fail_closed(postgresql_db):
    _assert_standard_odds_duplicate_existing_keys_fail_closed(postgresql_db)


def _assert_standard_odds_replaces_snapshot_and_reuses_verification(
    db, importer_class, monkeypatch
):
    _create_jravan_tables(db, ["ODDS_UMAREN_HEAD", "ODDS_UMAREN"])
    verification_calls = 0
    original_verify = importer_module.verify_standard_odds_tables

    def counted_verify(*args, **kwargs):
        nonlocal verification_calls
        verification_calls += 1
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(importer_module, "verify_standard_odds_tables", counted_verify)
    base = {
        "RecordSpec": "O2",
        "DataKubun": "2",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "UmarenFlag": "1",
        "Vote": "00000123456",
        "Odds": "012340",
        "Ninki": "001",
    }
    records = [
        {**base, "HassoTime": "04191549", "Kumi": "0102", "_raw": b"first"},
        {**base, "HassoTime": "04191549", "Kumi": "0103", "_raw": b"first"},
        {**base, "HassoTime": "04191550", "Kumi": "0102", "_raw": b"second"},
    ]

    stats = importer_class(
        db,
        use_jravan_schema=True,
        batch_size=1,
    ).import_records(iter(records))

    assert stats["records_failed"] == 0
    assert verification_calls == 1
    assert db.fetch_all(
        "SELECT Kumi AS kumi FROM ODDS_UMAREN ORDER BY Kumi"
    ) == [{"kumi": "0102"}]
    assert db.fetch_one(
        "SELECT HappyoTime AS happyo_time FROM ODDS_UMAREN_HEAD"
    ) == {"happyo_time": "04191550"}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_odds_replaces_snapshot_and_reuses_verification(
    sqlite_db, importer_class, monkeypatch
):
    _assert_standard_odds_replaces_snapshot_and_reuses_verification(
        sqlite_db, importer_class, monkeypatch
    )


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_postgresql_standard_odds_replaces_snapshot_and_reuses_verification(
    postgresql_db, importer_class, monkeypatch
):
    _assert_standard_odds_replaces_snapshot_and_reuses_verification(
        postgresql_db, importer_class, monkeypatch
    )


def _assert_standard_odds_migrates_existing_child_columns(db, importer_class):
    _create_jravan_tables(db, ["ODDS_UMAREN_HEAD"])
    db.execute(
        "CREATE TABLE ODDS_UMAREN ("
        "MakeDate DATE, Year SMALLINT, MonthDay SMALLINT, JyoCD CHAR(2), "
        "Kaiji SMALLINT, Nichiji SMALLINT, RaceNum SMALLINT, "
        "Kumi VARCHAR(4), Odds DECIMAL(6,1))"
    )
    db.commit()
    record = {
        "RecordSpec": "O2",
        "DataKubun": "2",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HassoTime": "04191549",
        "UmarenFlag": "1",
        "Vote": "00000123456",
        "Kumi": "0102",
        "Odds": "012340",
        "Ninki": "001",
    }

    stats = importer_class(db, use_jravan_schema=True).import_records(
        iter([record])
    )

    assert stats["records_failed"] == 0
    assert db.fetch_one(
        "SELECT Ninki AS ninki FROM ODDS_UMAREN"
    ) == {"ninki": 1}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_odds_migrates_existing_child_columns(
    sqlite_db, importer_class
):
    _assert_standard_odds_migrates_existing_child_columns(sqlite_db, importer_class)


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_postgresql_standard_odds_migrates_existing_child_columns(
    postgresql_db, importer_class
):
    _assert_standard_odds_migrates_existing_child_columns(
        postgresql_db, importer_class
    )


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_o2_empty_snapshot_preserves_total_and_clears_children(
    sqlite_db,
    importer_class,
):
    _create_jravan_tables(sqlite_db, ["ODDS_UMAREN_HEAD", "ODDS_UMAREN"])
    importer = importer_class(sqlite_db, use_jravan_schema=True)
    populated = {
        "RecordSpec": "O2",
        "DataKubun": "2",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HassoTime": "04191548",
        "UmarenFlag": "1",
        "Vote": "00000123456",
        "Kumi": "0102",
        "Odds": "012340",
        "Ninki": "001",
    }
    assert importer.import_records(iter([populated]))["records_failed"] == 0
    empty_snapshot = _flatten(O2Parser().parse(_make_empty_o2_record()))

    assert importer.import_records(iter(empty_snapshot))["records_failed"] == 0

    assert sqlite_db.fetch_one(
        "SELECT DataKubun AS status, TotalHyosuUmaren AS total "
        "FROM ODDS_UMAREN_HEAD"
    ) == {"status": "4", "total": "00000000999"}
    assert sqlite_db.fetch_one("SELECT COUNT(*) AS cnt FROM ODDS_UMAREN")[
        "cnt"
    ] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_sqlite_standard_odds_child_failure_rolls_back_header(
    sqlite_db,
    importer_class,
):
    _create_jravan_tables(sqlite_db, ["ODDS_UMAREN_HEAD", "ODDS_UMAREN"])
    record = {
        "RecordSpec": "O2",
        "DataKubun": "2",
        "MakeDate": "20260419",
        "Year": "2026",
        "MonthDay": "0419",
        "JyoCD": "06",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HassoTime": "04191549",
        "UmarenFlag": "1",
        "Vote": "00000123456",
        "Kumi": "0102",
        "Odds": "012340",
        "Ninki": "001",
    }
    importer = importer_class(sqlite_db, use_jravan_schema=True)
    assert importer.import_records(iter([record]))["records_failed"] == 0
    sqlite_db.execute(
        "CREATE TRIGGER reject_standard_odds_child "
        "BEFORE INSERT ON ODDS_UMAREN "
        "BEGIN SELECT RAISE(ABORT, 'child rejected'); END"
    )
    sqlite_db.commit()
    replacement = {
        **record,
        "DataKubun": "9",
        "HassoTime": "04191550",
        "Kumi": "0103",
    }

    with pytest.raises(ImporterError, match="child rejected"):
        importer.import_records(iter([replacement]))

    assert sqlite_db.fetch_one(
        "SELECT DataKubun AS status, HappyoTime AS happyo_time "
        "FROM ODDS_UMAREN_HEAD"
    ) == {"status": "2", "happyo_time": "04191549"}
    assert sqlite_db.fetch_all(
        "SELECT Kumi AS kumi FROM ODDS_UMAREN"
    ) == [{"kumi": "0102"}]


def test_sqlite_importer_stores_official_av_record(sqlite_db):
    _create_tables(sqlite_db, ["NL_AV"])
    record = AVParser().parse(_make_av_record())

    assert DataImporter(sqlite_db).import_single_record(record) is True

    row = sqlite_db.fetch_one(
        """
        SELECT
            Year AS year,
            MonthDay AS monthday,
            RaceNum AS racenum,
            Umaban AS umaban,
            JiyuKubun AS jiyukubun
        FROM NL_AV
        """
    )
    assert row == {
        "year": 2026,
        "monthday": 419,
        "racenum": 11,
        "umaban": 5,
        "jiyukubun": "001",
    }


def test_postgresql_importer_stores_heterogeneous_o1_rows(postgresql_db):
    _create_tables(postgresql_db, ["NL_O1"])
    rows = _flatten(O1Parser().parse(_make_o1_record()))

    stats = DataImporter(postgresql_db, batch_size=100).import_records(iter(rows))

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    _assert_o1_storage(postgresql_db, "NL_O1")


def test_postgresql_importer_skips_empty_expanded_o2_header_row(postgresql_db):
    _create_tables(postgresql_db, ["NL_O2"])
    rows = _flatten(O2Parser().parse(_make_empty_o2_record()))

    stats = DataImporter(postgresql_db, batch_size=100).import_records(iter(rows))

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    count = postgresql_db.fetch_one("SELECT COUNT(*) AS cnt FROM NL_O2")
    assert count["cnt"] == 0
