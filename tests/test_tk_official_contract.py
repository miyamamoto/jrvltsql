"""Official 21,657-byte TK parser and coupled-storage contract tests."""

from copy import deepcopy
import os
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.tk_parser import TKParser


TK_OFFICIAL_LENGTH = 21657
TK_RACE_KEY = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"]
TK_HEADER_LAYOUT = (
    ("RecordSpec", 0, 2),
    ("DataKubun", 2, 1),
    ("MakeDate", 3, 8),
    ("Year", 11, 4),
    ("MonthDay", 15, 4),
    ("JyoCD", 19, 2),
    ("Kaiji", 21, 2),
    ("Nichiji", 23, 2),
    ("RaceNum", 25, 2),
    ("YoubiCD", 27, 1),
    ("TokuNum", 28, 4),
    ("Hondai", 32, 60),
    ("Fukudai", 92, 60),
    ("Kakko", 152, 60),
    ("HondaiEng", 212, 120),
    ("FukudaiEng", 332, 120),
    ("KakkoEng", 452, 120),
    ("RaceRyakusyo10", 572, 20),
    ("RaceRyakusyo6", 592, 12),
    ("RaceRyakusyo3", 604, 6),
    ("RaceMeiKubun", 610, 1),
    ("JyusyoKaiji", 611, 3),
    ("GradeCD", 614, 1),
    ("SyubetuCD", 615, 2),
    ("KigoCD", 617, 3),
    ("JyuryoCD", 620, 1),
    ("JyokenCD2", 621, 3),
    ("JyokenCD3", 624, 3),
    ("JyokenCD4", 627, 3),
    ("JyokenCD5", 630, 3),
    ("JyokenCDYoung", 633, 3),
    ("Kyori", 636, 4),
    ("TrackCD", 640, 2),
    ("CourseKubun", 642, 2),
    ("HandeHappyoDate", 644, 8),
    ("TorokuTosu", 652, 3),
)
TK_HORSE_LAYOUT = (
    ("RenbanNum", 0, 3),
    ("KettoNum", 3, 10),
    ("Bamei", 13, 36),
    ("UmaKigoCD", 49, 2),
    ("SexCD", 51, 1),
    ("TozaiCD", 52, 1),
    ("ChokyosiCode", 53, 5),
    ("ChokyosiRyakusyo", 58, 8),
    ("Futan", 66, 3),
    ("Koryu", 69, 1),
)
TK_CHILD_FIELDS = {
    "MakeDate",
    *TK_RACE_KEY,
    *(name for name, _, _ in TK_HORSE_LAYOUT),
}


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
    schema_name = f"jlt_tk_{uuid4().hex[:12]}"
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


def _put(record: bytearray, start: int, size: int, value: str) -> None:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    record[start : start + size] = encoded.ljust(size, b" ")


def _header_values(
    *,
    data_kubun: str,
    horse_count: int,
    key_overrides: dict[str, str] | None,
    title: str,
) -> dict[str, str]:
    values = {
        "RecordSpec": "TK",
        "DataKubun": data_kubun,
        "MakeDate": "20260816",
        "Year": "2026",
        "MonthDay": "0822",
        "JyoCD": "05",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "YoubiCD": "7",
        "TokuNum": "1234",
        "Hondai": title,
        "Fukudai": "副題",
        "Kakko": "括弧内",
        "HondaiEng": "CURRENT SPECIAL",
        "FukudaiEng": "SUBTITLE",
        "KakkoEng": "PARENTHESIS",
        "RaceRyakusyo10": "現行特別",
        "RaceRyakusyo6": "現行",
        "RaceRyakusyo3": "現",
        "RaceMeiKubun": "1",
        "JyusyoKaiji": "012",
        "GradeCD": "A",
        "SyubetuCD": "11",
        "KigoCD": "A01",
        "JyuryoCD": "2",
        "JyokenCD2": "101",
        "JyokenCD3": "202",
        "JyokenCD4": "303",
        "JyokenCD5": "404",
        "JyokenCDYoung": "505",
        "Kyori": "2000",
        "TrackCD": "17",
        "CourseKubun": "A1",
        "HandeHappyoDate": "20260817",
        "TorokuTosu": f"{horse_count:03d}",
    }
    values.update(key_overrides or {})
    return values


def build_tk_record(
    *,
    data_kubun: str = "1",
    horse_count: int | None = None,
    key_overrides: dict[str, str] | None = None,
    title: str = "現行特別",
    horse_prefix: str = "HORSE",
) -> tuple[bytes, dict[str, str]]:
    if horse_count is None:
        horse_count = 0 if data_kubun == "0" else 2
    assert 0 <= horse_count <= 300
    values = _header_values(
        data_kubun=data_kubun,
        horse_count=horse_count,
        key_overrides=key_overrides,
        title=title,
    )
    record = bytearray(b" " * TK_OFFICIAL_LENGTH)
    for name, start, size in TK_HEADER_LAYOUT:
        _put(record, start, size, values[name])

    for index in range(1, horse_count + 1):
        slot_start = 655 + 70 * (index - 1)
        horse = {
            "RenbanNum": f"{index:03d}",
            "KettoNum": f"2026{index:06d}",
            "Bamei": f"{horse_prefix}{index:03d}",
            "UmaKigoCD": f"{index % 99:02d}",
            "SexCD": str(index % 4),
            "TozaiCD": str(index % 3),
            "ChokyosiCode": f"{index % 100000:05d}",
            "ChokyosiRyakusyo": f"TR{index:03d}",
            "Futan": f"{540 + index % 30:03d}",
            "Koryu": str(index % 3),
        }
        for name, relative, size in TK_HORSE_LAYOUT:
            _put(record, slot_start + relative, size, horse[name])
    record[21655:21657] = b"\r\n"
    return bytes(record), values


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_tk_record()[0])
    record[668:670] = b"\x81\x20"
    return bytes(record)


def _gapped_record() -> bytes:
    record = bytearray(build_tk_record(horse_count=2)[0])
    record[655:725] = b" " * 70
    return bytes(record)


def _count_mismatch_record() -> bytes:
    record = bytearray(build_tk_record(horse_count=2)[0])
    record[652:655] = b"003"
    return bytes(record)


def _create_current_tables(database, *, standard: bool) -> tuple[str, str]:
    if standard:
        header_table, child_table = "TOKU_RACE", "TOKU"
        schemas = JRAVAN_SCHEMAS
    else:
        header_table, child_table = "NL_TK_RACE", "NL_TK"
        schemas = SCHEMAS
    database.execute(schemas[header_table])
    database.execute(schemas[child_table])
    database.commit()
    return header_table, child_table


def _keyless_schema(schema: str) -> str:
    lines = [line for line in schema.splitlines() if "PRIMARY KEY" not in line]
    for index in range(len(lines) - 1, -1, -1):
        stripped = lines[index].rstrip()
        if stripped and not stripped.endswith(("(", ")")):
            lines[index] = stripped.rstrip(",")
            break
    return "\n".join(lines)


def test_tk_parses_complete_header_and_all_300_registered_horses() -> None:
    record, expected_header = build_tk_record(horse_count=300)

    parsed = TKParser().parse(record)

    assert parsed is not None
    assert TKParser.RECORD_LENGTH == TK_OFFICIAL_LENGTH
    assert {name: parsed[name] for name, _, _ in TK_HEADER_LAYOUT} == expected_header
    rows = parsed["_tk_registered_horse_rows"]
    assert len(rows) == 300
    assert set(rows[0]) == TK_CHILD_FIELDS
    assert rows[0]["RenbanNum"] == "001"
    assert rows[0]["Bamei"] == "HORSE001"
    assert rows[299]["RenbanNum"] == "300"
    assert rows[299]["KettoNum"] == "2026000300"
    assert rows[299]["Bamei"] == "HORSE300"
    assert rows[299]["Futan"] == "540"


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_tk_record()[0][:727], id="non-official-727"),
        pytest.param(build_tk_record()[0][:-1], id="short"),
        pytest.param(build_tk_record()[0] + b" ", id="long"),
        pytest.param(b"XX" + build_tk_record()[0][2:], id="wrong-record-type"),
        pytest.param(build_tk_record()[0][:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
        pytest.param(build_tk_record(data_kubun="9")[0], id="unsupported-status"),
        pytest.param(_gapped_record(), id="gapped-sequence"),
        pytest.param(_count_mismatch_record(), id="count-mismatch"),
    ],
)
def test_tk_rejects_non_official_or_internally_inconsistent_records(record: bytes) -> None:
    assert TKParser().parse(record) is None


def test_tk_delete_preserves_official_key_without_child_payload() -> None:
    parsed = TKParser().parse(build_tk_record(data_kubun="0")[0])

    assert parsed is not None
    assert parsed["DataKubun"] == "0"
    assert parsed["TorokuTosu"] == "000"
    assert parsed["_tk_registered_horse_rows"] == []
    assert all(parsed[column] for column in TK_RACE_KEY)


def test_tk_schemas_mappings_and_metadata_match_the_normalized_contract() -> None:
    header_fields = {name for name, _, _ in TK_HEADER_LAYOUT}

    assert set(get_table_column_types("NL_TK_RACE")) == header_fields
    assert set(get_table_column_types("NL_TK")) == TK_CHILD_FIELDS
    assert get_table_primary_key_columns("NL_TK_RACE") == TK_RACE_KEY
    assert get_table_primary_key_columns("NL_TK") == [*TK_RACE_KEY, "RenbanNum"]
    assert get_table_primary_key_columns("TOKU_RACE") == TK_RACE_KEY
    assert get_table_primary_key_columns("TOKU") == [*TK_RACE_KEY, "Num"]
    assert JLTSQL_TO_JRAVAN["NL_TK"] == "TOKU"
    assert JLTSQL_TO_JRAVAN["NL_TK_RACE"] == "TOKU_RACE"
    for table_name in ("NL_TK_RACE", "NL_TK"):
        assert [column["name"] for column in TABLE_METADATA[table_name]["columns"]] == list(
            get_table_column_types(table_name)
        )
        assert TABLE_METADATA[table_name]["primary_key"] == get_table_primary_key_columns(
            table_name
        )


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_tk_status_two_replaces_the_entire_snapshot_and_zero_deletes_it(
    tmp_path,
    importer_class,
    standard,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"status-{standard}.db")})
    first = TKParser().parse(build_tk_record(horse_count=3, title="BEFORE")[0])
    second = TKParser().parse(
        build_tk_record(data_kubun="2", horse_count=2, title="AFTER")[0]
    )
    other = TKParser().parse(
        build_tk_record(
            horse_count=1,
            key_overrides={"RaceNum": "12"},
            title="OTHER",
        )[0]
    )
    delete = TKParser().parse(build_tk_record(data_kubun="0")[0])
    assert all(record is not None for record in (first, second, other, delete))

    with database:
        header_table, child_table = _create_current_tables(database, standard=standard)
        importer = importer_class(database, use_jravan_schema=standard)
        update_stats = importer.import_records(iter([first, second]))
        updated_header = database.fetch_one(
            f"SELECT DataKubun, Hondai, TorokuTosu FROM {header_table}"
        )
        updated_children = database.fetch_all(
            f"SELECT * FROM {child_table} ORDER BY RaceNum, "
            f"{'Num' if standard else 'RenbanNum'}"
        )
        final_stats = importer.import_records(iter([other, delete]))
        final_headers = database.fetch_all(f"SELECT RaceNum, Hondai FROM {header_table}")
        final_children = database.fetch_all(
            f"SELECT RaceNum, Bamei FROM {child_table} ORDER BY RaceNum"
        )

    assert update_stats == {"records_imported": 2, "records_failed": 0, "batches_processed": 1}
    assert updated_header == {"DataKubun": "2", "Hondai": "AFTER", "TorokuTosu": 2}
    assert len(updated_children) == 2
    assert [row["Bamei"] for row in updated_children] == ["HORSE001", "HORSE002"]
    assert final_stats == {"records_imported": 2, "records_failed": 0, "batches_processed": 1}
    assert final_headers == [{"RaceNum": 12, "Hondai": "OTHER"}]
    assert final_children == [{"RaceNum": 12, "Bamei": "HORSE001"}]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_tk_importer_revalidates_private_snapshot_before_any_mutation(
    tmp_path,
    importer_class,
    standard,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{standard}.db")})
    original = TKParser().parse(build_tk_record(horse_count=2, title="ORIGINAL")[0])
    malformed = TKParser().parse(
        build_tk_record(data_kubun="2", horse_count=1, title="MALFORMED")[0]
    )
    assert original is not None and malformed is not None
    malformed = deepcopy(malformed)
    malformed["TorokuTosu"] = "002"

    with database:
        header_table, child_table = _create_current_tables(database, standard=standard)
        importer_class(database, use_jravan_schema=standard).import_records(iter([original]))
        with pytest.raises(SchemaMigrationError, match="count"):
            importer_class(database, use_jravan_schema=standard).import_records(iter([malformed]))

        header = database.fetch_one(f"SELECT DataKubun, Hondai FROM {header_table}")
        child_count = database.fetch_one(
            f"SELECT COUNT(*) AS count FROM {child_table}"
        )["count"]

    assert header == {"DataKubun": "1", "Hondai": "ORIGINAL"}
    assert child_count == 2


def test_tk_single_record_path_writes_both_tables_atomically(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single.db")})
    parsed = TKParser().parse(build_tk_record(horse_count=2)[0])
    assert parsed is not None

    with database:
        _create_current_tables(database, standard=False)
        assert DataImporter(database).import_single_record(parsed)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TK_RACE")["count"] == 1
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TK")["count"] == 2


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_obsolete_tk_storage_fails_closed_without_losing_existing_rows(
    tmp_path,
    importer_class,
    standard,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"obsolete-{standard}.db")})
    parsed = TKParser().parse(build_tk_record()[0])
    assert parsed is not None

    with database:
        if standard:
            database.execute(_keyless_schema(JRAVAN_SCHEMAS["TOKU_RACE"]))
            database.execute(_keyless_schema(JRAVAN_SCHEMAS["TOKU"]))
            child_table = "TOKU"
            sequence_column = "Num"
        else:
            database.execute(
                """
                CREATE TABLE NL_TK (
                    Year INTEGER, MonthDay INTEGER, JyoCD TEXT, Kaiji INTEGER,
                    Nichiji INTEGER, RaceNum INTEGER, RenbanNum INTEGER,
                    KettoNum TEXT,
                    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, KettoNum)
                )
                """
            )
            child_table = "NL_TK"
            sequence_column = "RenbanNum"
        database.execute(
            f"INSERT INTO {child_table} "
            f"(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, {sequence_column}, KettoNum) "
            "VALUES (2025, 101, '05', 1, 1, 11, 1, 'OLD')"
        )
        database.commit()

        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=standard).import_records(iter([parsed]))

        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {child_table}")["count"] == 1


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_obsolete_standard_tk_tables_do_not_block_an_unrelated_standard_import(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "unrelated.db")})
    unrelated = {
        "RecordSpec": "HN",
        "DataKubun": "1",
        "MakeDate": "20260816",
        "HansyokuNum": "1234567890",
        "Bamei": "UNRELATED",
    }

    with database:
        database.execute(_keyless_schema(JRAVAN_SCHEMAS["TOKU_RACE"]))
        database.execute(_keyless_schema(JRAVAN_SCHEMAS["TOKU"]))
        database.execute(JRAVAN_SCHEMAS["HANSYOKU"])
        database.commit()

        stats = importer_class(database, use_jravan_schema=True).import_records(iter([unrelated]))

        assert stats["records_imported"] == 1
        assert database.fetch_one("SELECT HansyokuNum, Bamei FROM HANSYOKU") == {
            "HansyokuNum": "1234567890",
            "Bamei": "UNRELATED",
        }


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_tk_postgresql_native_and_standard_preserve_snapshot_semantics(
    postgresql_db,
    importer_class,
) -> None:
    for standard in (False, True):
        _create_current_tables(postgresql_db, standard=standard)

    records = [
        TKParser().parse(build_tk_record(horse_count=3, title="BEFORE")[0]),
        TKParser().parse(build_tk_record(data_kubun="2", horse_count=2, title="AFTER")[0]),
        TKParser().parse(
            build_tk_record(
                horse_count=1,
                key_overrides={"RaceNum": "12"},
                title="OTHER",
            )[0]
        ),
        TKParser().parse(build_tk_record(data_kubun="0")[0]),
    ]
    assert all(record is not None for record in records)

    native = importer_class(postgresql_db).import_records(iter(records))
    standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(iter(records))

    assert native["records_imported"] == standard["records_imported"] == 4
    assert native["records_failed"] == standard["records_failed"] == 0
    for header_table, child_table in (("NL_TK_RACE", "NL_TK"), ("TOKU_RACE", "TOKU")):
        assert postgresql_db.fetch_one(
            f'SELECT COUNT(*) AS "count" FROM {header_table}'
        )["count"] == 1
        assert postgresql_db.fetch_one(
            f'SELECT COUNT(*) AS "count" FROM {child_table}'
        )["count"] == 1
        assert postgresql_db.fetch_one(
            f'SELECT RaceNum AS "RaceNum", Bamei AS "Bamei" FROM {child_table}'
        ) == {"RaceNum": 12, "Bamei": "HORSE001"}
