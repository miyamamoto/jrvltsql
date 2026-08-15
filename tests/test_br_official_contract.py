#!/usr/bin/env python
"""BR parser and storage contract for the official current 545-byte layout."""

from itertools import pairwise

import pytest

from src.database.migration import SchemaMigrationError, migrate_table_if_needed
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.br_parser import BRParser


def _pad(value: str, size: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    return encoded.ljust(size, b" ")


# Native flattened field, official one-based position, byte length, sentinel.
FIELDS = [
    ("RecordSpec", 1, 2, b"BR"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260815"),
    ("BreederCode", 12, 8, b"12345678"),
    ("BreederName_Co", 20, 72, _pad("Corporate Breeder Sentinel", 72)),
    ("BreederName", 92, 72, _pad("Plain Breeder Sentinel", 72)),
    ("BreederNameKana", 164, 72, _pad("ﾌﾞﾘｰﾀﾞｰｾﾝﾁﾈﾙ", 72)),
    ("BreederNameEng", 236, 168, _pad("Distinct Breeder English Sentinel", 168)),
    ("Address", 404, 20, _pad("Hokkaido Sentinel", 20)),
    ("H_SetYear", 424, 4, b"2026"),
    ("H_HonSyokinTotal", 428, 10, b"0000001001"),
    ("H_FukaSyokin", 438, 10, b"0000001002"),
    ("H_ChakuKaisu1", 448, 6, b"000101"),
    ("H_ChakuKaisu2", 454, 6, b"000102"),
    ("H_ChakuKaisu3", 460, 6, b"000103"),
    ("H_ChakuKaisu4", 466, 6, b"000104"),
    ("H_ChakuKaisu5", 472, 6, b"000105"),
    ("H_ChakuKaisu6", 478, 6, b"000106"),
    ("R_SetYear", 484, 4, b"1999"),
    ("R_HonSyokinTotal", 488, 10, b"0000002001"),
    ("R_FukaSyokin", 498, 10, b"0000002002"),
    ("R_ChakuKaisu1", 508, 6, b"000201"),
    ("R_ChakuKaisu2", 514, 6, b"000202"),
    ("R_ChakuKaisu3", 520, 6, b"000203"),
    ("R_ChakuKaisu4", 526, 6, b"000204"),
    ("R_ChakuKaisu5", 532, 6, b"000205"),
    ("R_ChakuKaisu6", 538, 6, b"000206"),
    ("RecordDelimiter", 544, 2, b"\r\n"),
]

EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
BUSINESS_FIELDS = set(EXPECTED) - {"RecordDelimiter"}
NUMERIC_FIELDS = {
    "H_SetYear",
    "H_HonSyokinTotal",
    "H_FukaSyokin",
    *[f"H_ChakuKaisu{index}" for index in range(1, 7)],
    "R_SetYear",
    "R_HonSyokinTotal",
    "R_FukaSyokin",
    *[f"R_ChakuKaisu{index}" for index in range(1, 7)],
}


def build_record() -> bytes:
    record = bytearray()
    for name, position, size, value in FIELDS:
        assert len(value) == size, f"{name}: {len(value)} != {size}"
        assert len(record) == position - 1, f"{name}: gap at {len(record)}"
        record += value
    assert len(record) == 545
    return bytes(record)


def _official_pre_2023_record() -> bytes:
    """Reconstruct official 4.8.0.2 widths: code 6 and three names 70."""
    current = build_record()
    legacy = (
        current[:11]
        + current[11:17]
        + current[19:89]
        + current[91:161]
        + current[163:233]
        + current[235:]
    )
    assert len(legacy) == 537
    assert legacy[-2:] == b"\r\n"
    return legacy


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_record())
    record[19:21] = b"\x81\x20"
    return bytes(record)


def test_br_layout_is_gap_free_and_uses_distinct_sentinels() -> None:
    assert len(FIELDS) == 28
    assert FIELDS[0][:3] == ("RecordSpec", 1, 2)
    assert FIELDS[-1][:3] == ("RecordDelimiter", 544, 2)
    assert all(
        position + size == next_position
        for (_, position, size, _), (_, next_position, _, _) in pairwise(FIELDS)
    )
    sentinels = [(size, EXPECTED[name]) for name, _, size, _ in FIELDS[:-1]]
    assert len(sentinels) == len(set(sentinels))


@pytest.mark.parametrize("field_name", sorted(EXPECTED))
def test_br_reads_every_official_field_at_its_exact_offset(field_name: str) -> None:
    row = BRParser().parse(build_record())

    assert row is not None
    assert row[field_name] == EXPECTED[field_name]


def test_br_emits_exactly_the_official_flattened_fields() -> None:
    row = BRParser().parse(build_record())

    assert row is not None
    assert BRParser.RECORD_LENGTH == 545
    assert set(row) == set(EXPECTED)


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_official_pre_2023_record(), id="official-pre-2023-537"),
        pytest.param(build_record()[:453] + b"\r\n", id="repository-455"),
        pytest.param(build_record()[:-1], id="short-544"),
        pytest.param(build_record() + b" ", id="long-546"),
        pytest.param(b"XX" + build_record()[2:], id="wrong-record-type"),
        pytest.param(build_record()[:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_br_rejects_unsupported_or_corrupt_physical_records(record: bytes) -> None:
    assert BRParser().parse(record) is None


def test_br_standard_mapping_selects_canonical_seisan_and_keeps_alias() -> None:
    assert JLTSQL_TO_JRAVAN["NL_BR"] == "SEISAN"
    assert JRAVAN_TO_JLTSQL["SEISAN"] == "NL_BR"
    assert JRAVAN_TO_JLTSQL["BREEDER"] == "NL_BR"


def test_br_native_and_standard_schemas_match_the_business_contract() -> None:
    for table_name in ("NL_BR", "SEISAN"):
        assert set(get_table_column_types(table_name)) == BUSINESS_FIELDS
        assert get_table_primary_key_columns(table_name) == ["BreederCode"]


@pytest.mark.parametrize(
    "importer_class,table_name,use_jravan_schema",
    [
        pytest.param(
            importer_class, table_name, standard, id=f"{importer_class.__name__}-{table_name}"
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_BR", False), ("SEISAN", True))
    ],
)
def test_br_round_trips_every_business_field(
    tmp_path, importer_class, table_name: str, use_jravan_schema: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        parsed = BRParser().parse(build_record())
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([parsed]))
        row = database.fetch_one(f"SELECT * FROM {table_name}")

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert set(row) == BUSINESS_FIELDS
    assert all(row[field] is not None for field in BUSINESS_FIELDS)
    for field_name in NUMERIC_FIELDS:
        assert row[field_name] == int(EXPECTED[field_name])
    for field_name in BUSINESS_FIELDS - NUMERIC_FIELDS - {"MakeDate"}:
        assert row[field_name] == EXPECTED[field_name]
    assert str(row["MakeDate"]).replace("-", "") == EXPECTED["MakeDate"]


OBSOLETE_NATIVE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS NL_BR (
        RecordSpec TEXT,
        DataKubun TEXT,
        MakeDate TEXT,
        BreederCode TEXT,
        BreederName_Co TEXT,
        BreederName TEXT,
        BreederNameKana TEXT,
        BreederNameEng TEXT,
        Address TEXT,
        SetYear INTEGER,
        HonSyokinTotal BIGINT,
        FukaSyokin BIGINT,
        ChakuKaisu INTEGER,
        Reserved_454 TEXT,
        PRIMARY KEY (BreederCode)
    )
"""


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_native_migration_requires_and_supports_full_current_br_reimport(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-nl-br.db")})
    with database:
        database.execute(OBSOLETE_NATIVE_SCHEMA)
        database.execute(
            "INSERT INTO NL_BR "
            "(RecordSpec, DataKubun, MakeDate, BreederCode, BreederName, SetYear, "
            "Reserved_454) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("BR", "1", "20000101", "12345678", "legacy-breeder", 2000, "legacy-tail"),
        )
        database.commit()

        assert migrate_table_if_needed(database, "NL_BR", SCHEMAS["NL_BR"])
        migrated = database.fetch_one(
            "SELECT BreederCode, BreederName, SetYear, Reserved_454, "
            "H_SetYear, R_ChakuKaisu6 FROM NL_BR"
        )

        importer = importer_class(database)
        first_stats = importer.import_records(iter([BRParser().parse(build_record())]))
        second_stats = importer.import_records(iter([BRParser().parse(build_record())]))
        completed = database.fetch_one("SELECT * FROM NL_BR")
        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_BR")["count"]

    assert migrated == {
        "BreederCode": "12345678",
        "BreederName": "legacy-breeder",
        "SetYear": 2000,
        "Reserved_454": "legacy-tail",
        "H_SetYear": None,
        "R_ChakuKaisu6": None,
    }
    assert first_stats["records_imported"] == 1
    assert second_stats["records_imported"] == 1
    assert row_count == 1
    assert completed["BreederName"] == EXPECTED["BreederName"]
    assert completed["H_SetYear"] == int(EXPECTED["H_SetYear"])
    assert completed["R_ChakuKaisu6"] == int(EXPECTED["R_ChakuKaisu6"])


OBSOLETE_STANDARD_SCHEMA = """
    CREATE TABLE IF NOT EXISTS SEISAN (
        RecordSpec TEXT,
        DataKubun TEXT,
        MakeDate TEXT,
        BreederName_Co TEXT,
        BreederName TEXT,
        BreederNameKana TEXT,
        BreederNameEng TEXT,
        Address TEXT,
        H_SetYear TEXT,
        H_HonSyokinTotal TEXT,
        H_FukaSyokin TEXT,
        H_ChakuKaisu1 TEXT,
        H_ChakuKaisu2 TEXT,
        H_ChakuKaisu3 TEXT,
        H_ChakuKaisu4 TEXT,
        H_ChakuKaisu5 TEXT,
        H_ChakuKaisu6 TEXT,
        R_SetYear TEXT,
        R_HonSyokinTotal TEXT,
        R_FukaSyokin TEXT,
        R_ChakuKaisu1 TEXT,
        R_ChakuKaisu2 TEXT,
        R_ChakuKaisu3 TEXT,
        R_ChakuKaisu4 TEXT,
        R_ChakuKaisu5 TEXT
    )
"""


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_standard_import_refuses_keyless_obsolete_schema_without_row_loss(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-seisan.db")})
    with database:
        database.execute(OBSOLETE_STANDARD_SCHEMA)
        database.execute(
            "INSERT INTO SEISAN (RecordSpec, DataKubun, MakeDate, BreederName) "
            "VALUES (?, ?, ?, ?)",
            ("ZZ", "9", "20000101", "preserve-me"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([BRParser().parse(build_record())])
            )

        rows = database.fetch_all("SELECT RecordSpec, BreederName FROM SEISAN")

    assert rows == [{"RecordSpec": "ZZ", "BreederName": "preserve-me"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_standard_import_refuses_legacy_breeder_alias_without_row_loss(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-breeder.db")})
    with database:
        database.execute(
            "CREATE TABLE BREEDER "
            "(RecordSpec TEXT, BreederCode TEXT PRIMARY KEY, BreederName TEXT)"
        )
        database.execute(
            "INSERT INTO BREEDER VALUES (?, ?, ?)",
            ("ZZ", "87654321", "preserve-alias"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="BREEDER"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([BRParser().parse(build_record())])
            )

        rows = database.fetch_all("SELECT * FROM BREEDER")

    assert rows == [
        {
            "RecordSpec": "ZZ",
            "BreederCode": "87654321",
            "BreederName": "preserve-alias",
        }
    ]
