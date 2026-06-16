#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SQLite/PostgreSQL storage tests for expanded JV-Data parser rows."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
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
