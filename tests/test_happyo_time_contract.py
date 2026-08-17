"""Official MDHM announcement-time contracts for change records."""

import os
import re
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError, verify_table_schema
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.av_parser import AVParser
from src.parser.cc_parser import CCParser
from src.parser.jc_parser import JCParser
from src.parser.tc_parser import TCParser
from src.parser.we_parser import WEParser

# SDK 5.0.0 and the historical 4.8.0.2 specification both define these
# values as MDHM: four two-byte strings for month, day, hour, and minute.
CHANGE_RECORDS = (
    ("AV", AVParser, 78, 27, "TORIKESI_JYOGAI", "NL_AV"),
    ("WE", WEParser, 42, 25, "TENKO_BABA", "NL_WE"),
    ("CC", CCParser, 50, 27, "COURSE_CHANGE", "NL_CC"),
    ("JC", JCParser, 161, 27, "KISYU_CHANGE", "NL_JC"),
    ("TC", TCParser, 45, 27, "HASSOU_JIKOKU_CHANGE", "NL_TC"),
)

STANDARD_MDHM_TABLES = (
    "BATAIJYU",
    "COURSE_CHANGE",
    "HASSOU_JIKOKU_CHANGE",
    "KISYU_CHANGE",
    "ODDS_SANRENTAN_HEAD",
    "ODDS_SANREN_HEAD",
    "ODDS_TANPUKUWAKU_HEAD",
    "ODDS_UMAREN_HEAD",
    "ODDS_UMATAN_HEAD",
    "ODDS_WIDE_HEAD",
    "TENKO_BABA",
    "TORIKESI_JYOGAI",
)


def _record(record_type: str, length: int, announcement_start: int) -> bytes:
    record = bytearray(b" " * length)
    record[0:2] = record_type.encode("ascii")
    record[2:3] = b"1"
    record[3:11] = b"20260815"
    record[11:15] = b"2026"
    record[15:19] = b"0815"
    record[19:21] = b"05"
    record[21:23] = b"03"
    record[23:25] = b"08"
    if announcement_start == 27:
        record[25:27] = b"11"
    record[announcement_start : announcement_start + 8] = b"06150930"
    if record_type in {"AV", "JC"}:
        record[35:37] = b"01"
    if record_type == "JC":
        record[73:76] = b"550"
        record[76:81] = b"01234"
        record[115:116] = b"0"
        record[116:119] = b"560"
        record[119:124] = b"05678"
        record[158:159] = b"9"
    if record_type == "WE":
        record[33:40] = b"1111000"
    record[-2:] = b"\r\n"
    return bytes(record)


def _parsed_records():
    for record_type, parser_class, length, start, table_name, _ in CHANGE_RECORDS:
        yield table_name, parser_class().parse(_record(record_type, length, start))


@pytest.mark.parametrize(
    "record_type,parser_class,length,start,table_name,native_name",
    CHANGE_RECORDS,
    ids=[row[0] for row in CHANGE_RECORDS],
)
def test_change_parsers_preserve_official_mdhm_text(
    record_type, parser_class, length, start, table_name, native_name
) -> None:
    parsed = parser_class().parse(_record(record_type, length, start))

    assert parsed["HappyoTime"] == "06150930"


@pytest.mark.parametrize(
    "record_type,parser_class,length,start,table_name,native_name",
    CHANGE_RECORDS,
    ids=[row[0] for row in CHANGE_RECORDS],
)
def test_standard_change_schema_uses_lossless_mdhm_text(
    record_type, parser_class, length, start, table_name, native_name
) -> None:
    ddl = JRAVAN_SCHEMAS[table_name]

    assert re.search(r"^\s*HappyoTime\s+VARCHAR\(8\)(?:\s|,)", ddl, re.MULTILINE)


def test_all_standard_mdhm_columns_use_lossless_text() -> None:
    assert {
        table_name
        for table_name, ddl in JRAVAN_SCHEMAS.items()
        if re.search(r"^\s*HappyoTime\s+", ddl, re.MULTILINE)
    } == set(STANDARD_MDHM_TABLES)
    for table_name in STANDARD_MDHM_TABLES:
        assert re.search(
            r"^\s*HappyoTime\s+VARCHAR\(8\)(?:\s|,)",
            JRAVAN_SCHEMAS[table_name],
            re.MULTILINE,
        )


@pytest.mark.parametrize(
    "record_type,parser_class,length,start,table_name,native_name",
    CHANGE_RECORDS,
    ids=[row[0] for row in CHANGE_RECORDS],
)
def test_native_tables_map_to_official_change_table_names(
    record_type, parser_class, length, start, table_name, native_name
) -> None:
    assert JLTSQL_TO_JRAVAN[native_name] == table_name


def test_native_av_identity_does_not_include_announcement_time(tmp_path) -> None:
    """A later AV announcement revises the same official seven-part key."""

    database = SQLiteDatabase({"path": str(tmp_path / "av-official-key.db")})
    first = AVParser().parse(_record("AV", 78, 27))
    revised_raw = bytearray(_record("AV", 78, 27))
    revised_raw[27:35] = b"06151000"
    revised = AVParser().parse(bytes(revised_raw))
    with database:
        database.execute(SCHEMAS["NL_AV"])
        database.commit()
        result = DataImporter(database).import_records(iter([first, revised]))
        rows = database.fetch_all("SELECT HappyoTime FROM NL_AV")

    assert result["records_imported"] == 2
    assert result["records_failed"] == 0
    assert rows == [{"HappyoTime": "06151000"}]


def _assert_standard_storage(database, importer_class=DataImporter) -> None:
    for _, _, _, _, table_name, _ in CHANGE_RECORDS:
        database.execute(JRAVAN_SCHEMAS[table_name])
    database.commit()

    importer = importer_class(database, batch_size=1, use_jravan_schema=True)
    for _, parsed in _parsed_records():
        stats = importer.import_records(iter([parsed]))
        assert stats["records_failed"] == 0

    for _, _, _, _, table_name, _ in CHANGE_RECORDS:
        row = database.fetch_one(f"SELECT HappyoTime AS value FROM {table_name}")
        assert row is not None
        assert row["value"] == "06150930"

    weather = database.fetch_one(
        "SELECT AtoTenkoCD, AtoSibaBabaCD, AtoDirtBabaCD, "
        "MaeTenkoCD, MaeSibaBabaCD, MaeDirtBabaCD FROM TENKO_BABA"
    )
    assert weather is not None
    assert tuple(weather.values()) == ("1", "1", "1", "0", "0", "0")


@pytest.mark.parametrize(
    "importer_class",
    [DataImporter, OptimizedDataImporter],
    ids=["regular", "optimized"],
)
def test_sqlite_standard_storage_preserves_official_mdhm_text(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "change-records.db")})
    database.connect()
    try:
        _assert_standard_storage(database, importer_class)
    finally:
        database.disconnect()


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(
        {
            "host": os.getenv("POSTGRES_HOST") or os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT") or os.getenv("PGPORT", "5432")),
            "database": os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "jltsql_test"),
            "user": os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "jltsql"),
            "password": os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", ""),
            "connect_timeout": 5,
        }
    )
    schema_name = f"jlt_happyo_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


def test_postgresql_standard_storage_preserves_official_mdhm_text(postgresql_db) -> None:
    _assert_standard_storage(postgresql_db)


def test_postgresql_schema_verification_rejects_legacy_temporal_column(
    postgresql_db,
) -> None:
    postgresql_db.execute("CREATE TABLE LEGACY_CHANGE (HappyoTime TIMESTAMP)")
    postgresql_db.commit()

    with pytest.raises(SchemaMigrationError, match="column types"):
        verify_table_schema(
            postgresql_db,
            "LEGACY_CHANGE",
            "CREATE TABLE LEGACY_CHANGE (HappyoTime VARCHAR(8))",
        )


def test_schema_verification_rejects_legacy_temporal_column(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy.db")})
    database.connect()
    try:
        database.execute("CREATE TABLE CHANGE_EVENT (HappyoTime TIMESTAMP)")
        database.commit()

        with pytest.raises(SchemaMigrationError, match="column types"):
            verify_table_schema(
                database,
                "CHANGE_EVENT",
                "CREATE TABLE CHANGE_EVENT (HappyoTime VARCHAR(8))",
            )
    finally:
        database.disconnect()


def test_schema_verification_accepts_lossless_legacy_text_column(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "lossless.db")})
    database.connect()
    try:
        database.execute("CREATE TABLE CHANGE_EVENT (HappyoTime TEXT)")
        database.commit()

        verify_table_schema(
            database,
            "CHANGE_EVENT",
            "CREATE TABLE CHANGE_EVENT (HappyoTime VARCHAR(8))",
        )
    finally:
        database.disconnect()


def test_schema_verification_rejects_unknown_required_text_type(tmp_path, monkeypatch) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "unknown.db")})
    database.connect()
    try:
        database.execute("CREATE TABLE CHANGE_EVENT (HappyoTime TEXT)")
        database.commit()
        monkeypatch.setattr("src.database.migration._get_existing_column_types", lambda *_: {})

        with pytest.raises(SchemaMigrationError, match="unknown column types"):
            verify_table_schema(
                database,
                "CHANGE_EVENT",
                "CREATE TABLE CHANGE_EVENT (HappyoTime VARCHAR(8))",
            )
    finally:
        database.disconnect()
