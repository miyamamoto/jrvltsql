"""Official current HS physical and storage contract."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager, create_all_tables
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    validate_import_record_header,
    verify_hs_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.hs_parser import HSParser
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
MANIFEST = json.loads((FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8"))
HISTORY = json.loads((FIXTURES / "jvdata_layout_history.json").read_text(encoding="utf-8"))
HS_CONTRACT = json.loads((FIXTURES / "hs_contract_4901.json").read_text(encoding="utf-8"))
HS_KEY = ("KettoNum", "SaleCode", "FromDate")
HS_LAYOUT = (
    ("RecordSpec", 0, 2),
    ("DataKubun", 2, 1),
    ("MakeDate", 3, 8),
    ("KettoNum", 11, 10),
    ("HansyokuFNum", 21, 10),
    ("HansyokuMNum", 31, 10),
    ("BirthYear", 41, 4),
    ("SaleCode", 45, 6),
    ("SaleHostName", 51, 40),
    ("SaleName", 91, 80),
    ("FromDate", 171, 8),
    ("ToDate", 179, 8),
    ("Barei", 187, 1),
    ("Price", 188, 10),
    ("RecordDelimiter", 198, 2),
)
HS_PREVIOUS_LAYOUT = (
    ("RecordSpec", 0, 2),
    ("DataKubun", 2, 1),
    ("MakeDate", 3, 8),
    ("KettoNum", 11, 10),
    ("HansyokuFNum", 21, 8),
    ("HansyokuMNum", 29, 8),
    ("BirthYear", 37, 4),
    ("SaleCode", 41, 6),
    ("SaleHostName", 47, 40),
    ("SaleName", 87, 80),
    ("FromDate", 167, 8),
    ("ToDate", 175, 8),
    ("Barei", 183, 1),
    ("Price", 184, 10),
    ("RecordDelimiter", 194, 2),
)

PRE_2_0_NATIVE_HS_SCHEMA = """
CREATE TABLE NL_HS (
    RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, KettoNum TEXT,
    HansyokuFNum TEXT, HansyokuMNum TEXT, BirthYear INTEGER,
    SaleCode TEXT, SaleHostName TEXT, SaleName TEXT, FromDate TEXT,
    ToDate TEXT, Barei INTEGER, Price BIGINT, Field15 TEXT,
    PRIMARY KEY (KettoNum, SaleCode, FromDate)
)
"""
PRE_2_0_STANDARD_HS_SCHEMA = """
CREATE TABLE SALE (
    RecordSpec CHAR(2), DataKubun CHAR(1), MakeDate DATE,
    KettoNum VARCHAR(10), HansyokuFNum VARCHAR(255),
    HansyokuMNum VARCHAR(255), BirthYear VARCHAR(255),
    SaleCode VARCHAR(255), SaleHostName VARCHAR(40), SaleName VARCHAR(80),
    FromDate VARCHAR(255), ToDate VARCHAR(255), Barei SMALLINT,
    Price VARCHAR(10)
)
"""


def hs_schema_missing_marker_with_extra_check() -> str:
    schema = SCHEMAS["NL_HS"].replace(
        "            CurrentLayoutVersion SMALLINT NOT NULL "
        "CHECK (CurrentLayoutVersion = 200),\n",
        "",
    )
    return schema.replace(
        "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        "CHECK (Price <= 100), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        1,
    )


def hs_table_columns(database) -> set[str]:
    if database.get_db_type() == "sqlite":
        return {
            str(row["name"])
            for row in database.fetch_all('PRAGMA table_info("NL_HS")')
        }
    return {
        str(row["column_name"])
        for row in database.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'nl_hs'"
        )
    }


def _put(raw: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    raw[start : start + width] = encoded.ljust(width, b" ")


def build_hs_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260818",
    ketto_num: str = "2022100105",
    hansyoku_f_num: str = "12345678",
    hansyoku_m_num: str = "0000000000",
    birth_year: str = "2022",
    sale_code: str = "011001",
    sale_host_name: str = "主催者",
    sale_name: str = "市場名",
    from_date: str = "20260818",
    to_date: str = "20260819",
    barei: str = "4",
    price: str = "1234567890",
) -> bytes:
    raw = bytearray(b" " * 200)
    for start, width, value in (
        (0, 2, "HS"),
        (2, 1, data_kubun),
        (3, 8, make_date),
        (11, 10, ketto_num),
        (21, 10, hansyoku_f_num),
        (31, 10, hansyoku_m_num),
        (41, 4, birth_year),
        (45, 6, sale_code),
        (51, 40, sale_host_name),
        (91, 80, sale_name),
        (171, 8, from_date),
        (179, 8, to_date),
        (187, 1, barei),
        (188, 10, price),
    ):
        _put(raw, start, width, value)
    raw[-2:] = b"\r\n"
    return bytes(raw)


def build_previous_hs_record() -> bytes:
    """Build one real 4.8.0.2 HOSE-layout record, including its own CRLF."""

    values = {
        "RecordSpec": "HS",
        "DataKubun": "1",
        "MakeDate": "20230807",
        "KettoNum": "2022100105",
        "HansyokuFNum": "12345678",
        "HansyokuMNum": "87654321",
        "BirthYear": "2022",
        "SaleCode": "011001",
        "SaleHostName": "主催者",
        "SaleName": "旧市場名",
        "FromDate": "20230807",
        "ToDate": "20230807",
        "Barei": "1",
        "Price": "0000000100",
    }
    raw = bytearray(b" " * 196)
    for field_name, start, width in HS_PREVIOUS_LAYOUT:
        if field_name == "RecordDelimiter":
            raw[start : start + width] = b"\r\n"
        else:
            _put(raw, start, width, values[field_name])
    return bytes(raw)


def parsed_hs(**overrides) -> dict:
    parsed = HSParser().parse(build_hs_record(**overrides))
    assert parsed is not None
    return parsed


def _import(
    database,
    entrypoint: str,
    records: list[dict],
    *,
    standard: bool,
    auto_commit: bool = True,
) -> dict:
    if entrypoint == "data":
        stats = DataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    elif entrypoint == "optimized":
        stats = OptimizedDataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    else:
        importer = DataImporter(database, use_jravan_schema=standard)
        assert all(
            importer.import_single_record(record, auto_commit=auto_commit) for record in records
        )
        stats = importer.get_statistics()
    if not auto_commit:
        database.commit()
    return stats


def _assert_hs_failure_transaction_boundary(
    database,
    entrypoint: str,
    *,
    standard: bool,
    auto_commit: bool,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    good = parsed_hs()
    malformed = parsed_hs(ketto_num="2022100106")
    malformed["Price"] = "9X"
    importer = (
        OptimizedDataImporter(database, batch_size=1, use_jravan_schema=standard)
        if entrypoint == "optimized"
        else DataImporter(database, batch_size=1, use_jravan_schema=standard)
    )
    with pytest.raises(SchemaMigrationError):
        if entrypoint == "single":
            assert importer.import_single_record(good, auto_commit=auto_commit)
            importer.import_single_record(malformed, auto_commit=auto_commit)
        else:
            importer.import_records(iter([good, malformed]), auto_commit=auto_commit)
    expected = 1 if auto_commit else 0
    assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": expected}
    stats = importer.get_statistics()
    assert stats["records_imported"] == expected
    assert stats["records_failed"] == 0


def test_hs_sdk500_layout_and_current_only_boundary() -> None:
    assert HS_CONTRACT["primary_key"] == list(HS_KEY)
    assert HS_CONTRACT["current_data_kubun"] == ["0", "1"]
    assert (
        tuple((name, start - 1, width) for name, start, width in HS_CONTRACT["current_fields"])
        == HS_LAYOUT
    )
    assert (
        tuple((name, start - 1, width) for name, start, width in HS_CONTRACT["previous_fields"])
        == HS_PREVIOUS_LAYOUT
    )
    assert HS_CONTRACT["current_setup_policy"]["accept_lengths"] == [200]
    assert HS_CONTRACT["current_setup_policy"]["reject_lengths"] == [196]
    assert HS_CONTRACT["current_setup_policy"]["old_dates_are_returned_in_current_size"] is True
    assert HS_CONTRACT["current_setup_policy"]["mixed_old_and_current_stores_supported"] is False
    assert MANIFEST["root_records"]["HS"] == {
        "struct": "JV_HS_SALE",
        "length": 200,
    }
    change = next(
        item for item in HISTORY["physical_length_changes"] if item["record_type"] == "HS"
    )
    assert (change["before_length"], change["after_length"]) == (196, 200)
    sdk_fields = []
    for field in MANIFEST["structures"]["JV_HS_SALE"]["fields"]:
        if field["name"] == "head":
            for header in MANIFEST["structures"][field["struct"]]["fields"]:
                sdk_fields.append(
                    (
                        header["name"],
                        field["start"] + header["start"] - 2,
                        header["width"],
                    )
                )
        else:
            sdk_fields.append(
                (
                    "RecordDelimiter" if field["name"] == "crlf" else field["name"],
                    field["start"] - 1,
                    field["width"],
                )
            )
    assert tuple(sdk_fields) == HS_LAYOUT
    assert MANIFEST["structures"]["JV_HS_SALE"]["expanded_leaf_count"] == 21
    assert tuple((field.name, field.start, field.length) for field in HSParser()._fields) == (
        HS_LAYOUT
    )
    assert parsed_hs()["RecordDelimiter"] == ""
    assert HSParser().parse(build_hs_record(make_date="20200101")) is not None
    previous = build_previous_hs_record()
    assert len(previous) == 196
    assert previous[-2:] == b"\r\n"
    assert HSParser().parse(previous) is None


def test_hs_historical_barei_is_preserved_without_make_date_reinterpretation() -> None:
    semantics = HS_CONTRACT["historical_semantics"]
    assert semantics["barei_is_unified_to_post_2001_method"] is True
    assert semantics["sale_name_keeps_historical_notation"] is True
    parsed = parsed_hs(
        make_date="19991231",
        sale_name="当時市場名",
        from_date="19991231",
        to_date="20000101",
        barei="3",
    )
    assert parsed["Barei"] == "3"
    assert parsed["SaleName"] == "当時市場名"


def test_hs_status_zero_non_key_bytes_are_opaque_project_policy() -> None:
    raw = bytearray(build_hs_record(data_kubun="0"))
    for offset in (60, 120):
        raw[offset : offset + 2] = b"\x81 "
    parsed = HSParser().parse(bytes(raw))
    assert parsed is not None
    assert tuple(parsed[column] for column in HS_KEY) == (
        "2022100105",
        "011001",
        "20260818",
    )
    raw[11:21] = b"20221A0105"
    assert HSParser().parse(bytes(raw)) is None


def test_hs_official_zero_and_parent_registration_initial_values() -> None:
    parsed = parsed_hs(
        make_date="00000000",
        ketto_num="0000000000",
        hansyoku_f_num="00000000",
        hansyoku_m_num="0000000000",
        birth_year="0000",
        sale_code="000000",
        from_date="00000000",
        to_date="00000000",
        barei="0",
        price="0",
    )
    assert parsed["HansyokuFNum"] == "00000000"
    assert parsed["HansyokuMNum"] == "0000000000"


def test_hs_status_zero_caller_body_is_opaque_but_aliases_remain_strict(
    tmp_path: Path,
) -> None:
    class ExplodingBody:
        def __str__(self) -> str:
            raise RuntimeError("opaque HS body was inspected")

    erase = parsed_hs(data_kubun="0")
    erase.update(
        {
            "Price": ExplodingBody(),
            "SaleHostName": ExplodingBody(),
            "headDataKubun": "0",
        }
    )
    assert validate_import_record_header(erase) == ("HS", "0")
    erase["headDataKubun"] = "1"
    with pytest.raises(SchemaMigrationError, match="conflicting DataKubun"):
        validate_import_record_header(erase)

    erase["headDataKubun"] = "0"
    database = SQLiteDatabase({"path": str(tmp_path / "opaque-delete.db")})
    with database:
        database.execute(SCHEMAS["NL_HS"])
        database.commit()
        importer = DataImporter(database)
        assert importer.import_single_record(parsed_hs())
        assert importer.import_single_record(erase)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 0}


@pytest.mark.parametrize(
    "changes",
    (
        {"Price": "90A0000"},
        {"KettoNum": "20221A0105"},
        {"FromDate": "20241399"},
        {"HansyokuFNum": ""},
        {"SaleHostName": "あ" * 21},
        {"MakeDate": date(2026, 8, 18)},
    ),
)
def test_hs_caller_values_are_rejected_before_coercion(changes: dict) -> None:
    record = parsed_hs()
    record.update(changes)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_hs_executable_schemas_publish_the_exact_identity() -> None:
    for table_name in ("NL_HS", "SALE"):
        assert tuple(get_table_primary_key_columns(table_name)) == HS_KEY
        nullability = get_table_column_nullability(table_name)
        assert all(nullability[column] is False for column in HS_KEY)
        assert nullability["RecordSpec"] is False
        assert nullability["DataKubun"] is False
        assert nullability["MakeDate"] is False
        assert nullability["CurrentLayoutVersion"] is False
        assert all(
            nullability[column] is False
            for column in (
                "HansyokuFNum",
                "HansyokuMNum",
                "BirthYear",
                "ToDate",
                "Barei",
                "Price",
            )
        )
    assert "Field15" not in SCHEMAS["NL_HS"]
    assert "RecordDelimiter" in SCHEMAS["NL_HS"]


@pytest.mark.parametrize("table_name", ("NL_HS", "SALE"))
@pytest.mark.parametrize(
    "defect",
    (
        "wrong-type",
        "nullable-key",
        "nullable-body",
        "short-text",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
        "missing-marker-check",
    ),
)
def test_hs_schema_verifier_rejects_unsafe_storage(
    tmp_path: Path,
    table_name: str,
    defect: str,
) -> None:
    schema = JRAVAN_SCHEMAS[table_name] if table_name == "SALE" else SCHEMAS[table_name]
    if defect == "wrong-type":
        schema = schema.replace("BIGINT", "TEXT", 1)
    elif defect == "nullable-key":
        schema = schema.replace("VARCHAR(10) NOT NULL", "VARCHAR(10)", 1)
    elif defect == "nullable-body":
        schema = re.sub(
            r"(HansyokuFNum\s+VARCHAR\(10\)) NOT NULL",
            r"\1",
            schema,
            count=1,
        )
    elif defect == "short-text":
        schema = schema.replace("VARCHAR(80)", "VARCHAR(79)", 1)
    elif defect == "extra-unique":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-check":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "CHECK (Price <= 100), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-foreign-key":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "FOREIGN KEY (SaleCode) REFERENCES HS_PARENT(SaleCode) "
            "ON DELETE CASCADE, PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-required-column":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "ExternalRequired TEXT NOT NULL, "
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    else:
        schema = schema.replace(" CHECK (CurrentLayoutVersion = 200)", "", 1)
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{defect}.db")})
    with database:
        if defect == "extra-foreign-key":
            database.execute("CREATE TABLE HS_PARENT (SaleCode VARCHAR(6) PRIMARY KEY)")
        database.execute(schema)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            verify_hs_storage_schema(database, table_name)


def test_hs_nonempty_unmarked_store_requires_rebuild_before_any_migration(
    tmp_path: Path,
) -> None:
    old_schema = SCHEMAS["NL_HS"].replace(
        "            CurrentLayoutVersion SMALLINT NOT NULL CHECK (CurrentLayoutVersion = 200),\n",
        "",
    )
    assert old_schema != SCHEMAS["NL_HS"]
    database = SQLiteDatabase({"path": str(tmp_path / "unmarked.db")})
    with database:
        database.execute(old_schema)
        database.execute(
            "INSERT INTO NL_HS "
            "(RecordSpec, DataKubun, MakeDate, KettoNum, HansyokuFNum, HansyokuMNum, "
            "BirthYear, SaleCode, FromDate, ToDate, Barei, Price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "HS",
                "1",
                "20260818",
                "2022100105",
                "12345678",
                "0000000000",
                2022,
                "011001",
                "20260818",
                "20260819",
                4,
                100,
            ),
        )
        database.commit()
        before_tables = database.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        with pytest.raises(SchemaMigrationError, match="rebuild"):
            create_all_tables(database)
        assert (
            database.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            == before_tables
        )
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 1}


@pytest.mark.parametrize(
    "missing_columns",
    (
        ("CurrentLayoutVersion",),
        ("RecordDelimiter",),
        ("CurrentLayoutVersion", "RecordDelimiter"),
    ),
)
def test_hs_empty_current_compatible_native_store_missing_only_allowed_columns(
    tmp_path: Path,
    missing_columns: tuple[str, ...],
) -> None:
    old_schema = SCHEMAS["NL_HS"]
    if "CurrentLayoutVersion" in missing_columns:
        old_schema = old_schema.replace(
            "            CurrentLayoutVersion SMALLINT NOT NULL "
            "CHECK (CurrentLayoutVersion = 200),\n",
            "",
        )
    if "RecordDelimiter" in missing_columns:
        old_schema = old_schema.replace("            RecordDelimiter CHAR(2),\n", "")
    database = SQLiteDatabase({"path": str(tmp_path / "empty-unmarked.db")})
    with database:
        database.execute(old_schema)
        database.commit()
        assert SchemaManager(database).create_table("NL_HS") is True
        verify_hs_storage_schema(database, "NL_HS")
        columns = {row["name"] for row in database.fetch_all('PRAGMA table_info("NL_HS")')}
        assert "CurrentLayoutVersion" in columns
        assert "RecordDelimiter" in columns


@pytest.mark.parametrize("missing_column", ("HansyokuFNum", "SaleName"))
def test_hs_empty_native_store_missing_body_column_requires_rebuild(
    tmp_path: Path,
    missing_column: str,
) -> None:
    schema = "\n".join(
        line
        for line in SCHEMAS["NL_HS"].splitlines()
        if not re.match(rf"\s*{missing_column}\s+", line)
    )
    database = SQLiteDatabase({"path": str(tmp_path / f"missing-{missing_column}.db")})
    with database:
        database.execute(schema)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("NL_HS")')
        assert SchemaManager(database).create_table("NL_HS") is False
        assert database.fetch_all('PRAGMA table_info("NL_HS")') == before


def test_hs_empty_native_missing_marker_with_extra_check_rejects_before_migration(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "marker-extra-check.db")})
    with database:
        database.execute(hs_schema_missing_marker_with_extra_check())
        database.commit()
        before = hs_table_columns(database)
        assert "CurrentLayoutVersion" not in before
        assert SchemaManager(database).create_table("NL_HS") is False
        assert hs_table_columns(database) == before


@pytest.mark.parametrize(
    ("table_name", "legacy_schema"),
    (("NL_HS", PRE_2_0_NATIVE_HS_SCHEMA), ("SALE", PRE_2_0_STANDARD_HS_SCHEMA)),
)
def test_hs_actual_pre_2_0_empty_storage_requires_explicit_rebuild(
    tmp_path: Path,
    table_name: str,
    legacy_schema: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"legacy-{table_name}.db")})
    with database:
        database.execute(legacy_schema)
        database.commit()
        before = database.fetch_all(f'PRAGMA table_info("{table_name}")')
        with pytest.raises(SchemaMigrationError):
            verify_hs_storage_schema(database, table_name, allow_missing_columns=True)
        assert database.fetch_all(f'PRAGMA table_info("{table_name}")') == before
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}


@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
def test_hs_invalid_first_record_precedes_standard_additive_migration(
    tmp_path: Path,
    entrypoint: str,
) -> None:
    race_without_youbi = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    assert race_without_youbi != JRAVAN_SCHEMAS["RACE"]
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{entrypoint}.db")})
    with database:
        database.execute(race_without_youbi)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        malformed = parsed_hs()
        malformed["Price"] = "9X"
        with pytest.raises(SchemaMigrationError):
            if entrypoint == "data":
                DataImporter(database, use_jravan_schema=True).import_records(iter([malformed]))
            elif entrypoint == "optimized":
                OptimizedDataImporter(database, use_jravan_schema=True).import_records(
                    iter([malformed])
                )
            else:
                DataImporter(database, use_jravan_schema=True).import_single_record(malformed)
        assert database.fetch_all('PRAGMA table_info("RACE")') == before


def test_hs_unsupported_realtime_raw_does_not_write_cache(tmp_path: Path) -> None:
    class CacheProbe:
        def __init__(self) -> None:
            self.calls = 0

        def write_rt_record(self, *_args) -> None:
            self.calls += 1

    cache = CacheProbe()
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    updater = RealtimeUpdater(database, cache_manager=cache)
    assert updater.process_record(build_hs_record()) is None
    assert cache.calls == 0


def test_hs_dual_rejects_one_unsafe_target_before_either_changes(tmp_path: Path) -> None:
    unsafe = SCHEMAS["NL_HS"].replace(
        "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        1,
    )
    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    with primary, secondary:
        primary.execute(SCHEMAS["NL_HS"])
        secondary.execute(unsafe)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_hs()]))
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 0}


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
def test_hs_all_current_fields_round_trip(
    tmp_path: Path,
    standard: bool,
    entrypoint: str,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"roundtrip-{table_name}.db")})
    with database:
        database.execute(schema)
        database.commit()
        _import(database, entrypoint, [parsed_hs()], standard=standard)
        row = database.fetch_one(
            f"SELECT RecordSpec, DataKubun, MakeDate, CurrentLayoutVersion, "
            f"KettoNum, HansyokuFNum, HansyokuMNum, BirthYear, SaleCode, "
            f"SaleHostName, SaleName, FromDate, ToDate, Barei, Price FROM {table_name}"
        )
    assert row == {
        "RecordSpec": "HS",
        "DataKubun": "1",
        "MakeDate": "20260818",
        "CurrentLayoutVersion": 200,
        "KettoNum": "2022100105",
        "HansyokuFNum": "12345678",
        "HansyokuMNum": "0000000000",
        "BirthYear": 2022,
        "SaleCode": "011001",
        "SaleHostName": "主催者",
        "SaleName": "市場名",
        "FromDate": "20260818",
        "ToDate": "20260819",
        "Barei": 4,
        "Price": 1234567890,
    }


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hs_provider_order_exact_erase_and_operation_statistics(
    tmp_path: Path,
    standard: bool,
    entrypoint: str,
    auto_commit: bool,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{entrypoint}.db")})
    with database:
        database.execute(schema)
        database.commit()
        first = parsed_hs(price="100")
        revision = parsed_hs(make_date="20260819", price="200")
        survivor = parsed_hs(from_date="20260820", to_date="20260821", price="300")
        erase = parsed_hs(data_kubun="0")
        stats = _import(
            database,
            entrypoint,
            [first, revision, survivor, erase],
            standard=standard,
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(f"SELECT KettoNum, SaleCode, FromDate, Price FROM {table_name}")
    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert rows == [
        {
            "KettoNum": "2022100105",
            "SaleCode": "011001",
            "FromDate": "20260820",
            "Price": 300,
        }
    ]


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hs_sqlite_failure_rollback_and_incremental_commit_statistics(
    tmp_path: Path,
    standard: bool,
    entrypoint: str,
    auto_commit: bool,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / "failure.db")})
    with database:
        database.execute(schema)
        database.commit()
        _assert_hs_failure_transaction_boundary(
            database,
            entrypoint,
            standard=standard,
            auto_commit=auto_commit,
        )


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_hs_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            try:
                database.rollback()
            except Exception:
                pass
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hs_postgresql_provider_order_exact_erase_and_operation_statistics(
    postgresql_db,
    standard: bool,
    entrypoint: str,
    auto_commit: bool,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    stats = _import(
        postgresql_db,
        entrypoint,
        [
            parsed_hs(price="100"),
            parsed_hs(make_date="20260819", price="200"),
            parsed_hs(from_date="20260820", to_date="20260821", price="300"),
            parsed_hs(data_kubun="0"),
        ],
        standard=standard,
        auto_commit=auto_commit,
    )
    rows = postgresql_db.fetch_all(f'SELECT kettonum AS "KettoNum" FROM {table_name}')
    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert rows == [{"KettoNum": "2022100105"}]


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hs_postgresql_failure_rollback_and_incremental_commit_statistics(
    postgresql_db,
    standard: bool,
    entrypoint: str,
    auto_commit: bool,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    _assert_hs_failure_transaction_boundary(
        postgresql_db,
        entrypoint,
        standard=standard,
        auto_commit=auto_commit,
    )


@pytest.mark.parametrize("table_name", ("NL_HS", "SALE"))
@pytest.mark.parametrize(
    "defect",
    (
        "wrong-type",
        "nullable-body",
        "short-text",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
        "deferrable-pk",
        "missing-marker-check",
    ),
)
def test_hs_postgresql_schema_verifier_rejects_unusable_or_untrusted_storage(
    postgresql_db,
    table_name: str,
    defect: str,
) -> None:
    schema = JRAVAN_SCHEMAS[table_name] if table_name == "SALE" else SCHEMAS[table_name]
    if defect == "wrong-type":
        schema = schema.replace("BIGINT", "TEXT", 1)
    elif defect == "nullable-body":
        schema = re.sub(
            r"(HansyokuFNum\s+VARCHAR\(10\)) NOT NULL",
            r"\1",
            schema,
            count=1,
        )
    elif defect == "short-text":
        schema = schema.replace("VARCHAR(80)", "VARCHAR(79)", 1)
    elif defect == "extra-unique":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-check":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "CHECK (Price <= 100), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-foreign-key":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "FOREIGN KEY (SaleCode) REFERENCES HS_PARENT(SaleCode) "
            "ON DELETE CASCADE, PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "extra-required-column":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "ExternalRequired TEXT NOT NULL, "
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            1,
        )
    elif defect == "deferrable-pk":
        schema = schema.replace(
            "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
            "PRIMARY KEY (KettoNum, SaleCode, FromDate) DEFERRABLE INITIALLY DEFERRED",
            1,
        )
    else:
        schema = schema.replace(" CHECK (CurrentLayoutVersion = 200)", "", 1)
    if defect == "extra-foreign-key":
        postgresql_db.execute("CREATE TABLE HS_PARENT (SaleCode VARCHAR(6) PRIMARY KEY)")
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_hs_storage_schema(postgresql_db, table_name)


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data", "optimized", "single"))
def test_hs_postgresql_idle_schema_rejection_closes_implicit_transaction(
    postgresql_db,
    standard: bool,
    entrypoint: str,
) -> None:
    table_name = "SALE" if standard else "NL_HS"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    unsafe = schema.replace(
        "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        1,
    )
    postgresql_db.execute(unsafe)
    postgresql_db.commit()
    importer = (
        OptimizedDataImporter(postgresql_db, use_jravan_schema=standard)
        if entrypoint == "optimized"
        else DataImporter(postgresql_db, use_jravan_schema=standard)
    )
    assert postgresql_db.has_pending_transaction() is False
    with pytest.raises(SchemaMigrationError):
        if entrypoint == "single":
            importer.import_single_record(parsed_hs(), auto_commit=True)
        else:
            importer.import_records(iter([parsed_hs()]), auto_commit=True)
    # Check ownership before the diagnostic SELECT below starts a new lazy
    # PostgreSQL read transaction.
    assert postgresql_db.has_pending_transaction() is False
    assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}
    assert importer.get_statistics()["records_imported"] == 0
    postgresql_db.rollback()


def test_hs_postgresql_schema_rejection_preserves_existing_caller_transaction(
    postgresql_db,
) -> None:
    unsafe = SCHEMAS["NL_HS"].replace(
        "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        1,
    )
    postgresql_db.execute(unsafe)
    postgresql_db.execute("CREATE TEMP TABLE hs_caller_marker (value INTEGER)")
    postgresql_db.commit()
    postgresql_db.execute("INSERT INTO hs_caller_marker (value) VALUES (?)", (1,))
    assert postgresql_db.has_pending_transaction() is True
    with pytest.raises(SchemaMigrationError):
        verify_hs_storage_schema(postgresql_db, "NL_HS")
    assert postgresql_db.has_pending_transaction() is True
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM hs_caller_marker") == {"count": 1}
    postgresql_db.rollback()


def test_hs_dual_postgresql_schema_rejection_closes_only_call_created_transactions(
    postgresql_db,
    tmp_path: Path,
) -> None:
    unsafe = SCHEMAS["NL_HS"].replace(
        "PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        "UNIQUE (SaleCode), PRIMARY KEY (KettoNum, SaleCode, FromDate)",
        1,
    )
    primary = SQLiteDatabase({"path": str(tmp_path / "dual-pg-primary.db")})
    with primary:
        primary.execute(SCHEMAS["NL_HS"])
        primary.commit()
        postgresql_db.execute(unsafe)
        postgresql_db.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, postgresql_db)).import_records(
                iter([parsed_hs()]), auto_commit=True
            )
        # Check ownership before the diagnostic SELECT below starts a new lazy
        # PostgreSQL read transaction.
        assert primary.has_pending_transaction() is False
        assert postgresql_db.has_pending_transaction() is False
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 0}
        assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_HS") == {"count": 0}
        assert primary.has_pending_transaction() is False
        postgresql_db.rollback()


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller-mode"))
def test_hs_postgresql_empty_standard_import_respects_transaction_mode(
    postgresql_db,
    importer_class,
    auto_commit: bool,
) -> None:
    postgresql_db.execute(JRAVAN_SCHEMAS["SALE"])
    postgresql_db.commit()
    importer = importer_class(postgresql_db, use_jravan_schema=True)
    stats = importer.import_records(iter(()), auto_commit=auto_commit)
    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 0
    assert postgresql_db.has_pending_transaction() is (not auto_commit)
    if not auto_commit:
        postgresql_db.rollback()


def test_hs_postgresql_empty_standard_import_preserves_existing_caller_transaction(
    postgresql_db,
) -> None:
    postgresql_db.execute(JRAVAN_SCHEMAS["SALE"])
    postgresql_db.execute("CREATE TEMP TABLE hs_empty_marker (value INTEGER)")
    postgresql_db.commit()
    postgresql_db.execute("INSERT INTO hs_empty_marker (value) VALUES (?)", (1,))
    assert postgresql_db.has_pending_transaction() is True
    stats = DataImporter(postgresql_db, use_jravan_schema=True).import_records(iter(()))
    assert stats["records_imported"] == 0
    assert postgresql_db.has_pending_transaction() is True
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM hs_empty_marker") == {
        "count": 1
    }
    postgresql_db.rollback()


def test_hs_dual_empty_standard_import_does_not_start_backend_transactions(
    postgresql_db,
    tmp_path: Path,
) -> None:
    primary = SQLiteDatabase({"path": str(tmp_path / "dual-empty.db")})
    with primary:
        primary.execute(JRAVAN_SCHEMAS["SALE"])
        primary.commit()
        postgresql_db.execute(JRAVAN_SCHEMAS["SALE"])
        postgresql_db.commit()
        stats = DataImporter(
            DualDatabase(primary, postgresql_db),
            use_jravan_schema=True,
        ).import_records(iter(()))
        assert stats["records_imported"] == 0
        assert primary.has_pending_transaction() is False
        assert postgresql_db.has_pending_transaction() is False


def test_hs_postgresql_missing_marker_with_extra_check_rejects_before_migration(
    postgresql_db,
) -> None:
    postgresql_db.execute(hs_schema_missing_marker_with_extra_check())
    postgresql_db.commit()
    before = hs_table_columns(postgresql_db)
    assert "currentlayoutversion" not in before
    assert SchemaManager(postgresql_db).create_table("NL_HS") is False
    assert hs_table_columns(postgresql_db) == before


@pytest.mark.parametrize("postgresql_primary", (False, True), ids=("sqlite-primary", "pg-primary"))
def test_hs_dual_missing_marker_with_extra_check_rejects_before_either_migration(
    postgresql_db,
    tmp_path: Path,
    postgresql_primary: bool,
) -> None:
    sqlite = SQLiteDatabase({"path": str(tmp_path / f"dual-marker-{postgresql_primary}.db")})
    with sqlite:
        sqlite.execute(
            SCHEMAS["NL_HS"]
            if postgresql_primary
            else hs_schema_missing_marker_with_extra_check()
        )
        sqlite.commit()
        postgresql_db.execute(
            hs_schema_missing_marker_with_extra_check()
            if postgresql_primary
            else SCHEMAS["NL_HS"]
        )
        postgresql_db.commit()
        before_sqlite = hs_table_columns(sqlite)
        before_postgresql = hs_table_columns(postgresql_db)
        database = (
            DualDatabase(postgresql_db, sqlite)
            if postgresql_primary
            else DualDatabase(sqlite, postgresql_db)
        )
        assert SchemaManager(database).create_table("NL_HS") is False
        assert hs_table_columns(sqlite) == before_sqlite
        assert hs_table_columns(postgresql_db) == before_postgresql
