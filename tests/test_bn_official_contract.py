#!/usr/bin/env python
"""BN parser and storage contract for the official current 477-byte layout."""

from itertools import pairwise

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.bn_parser import BNParser


def _pad(value: str, size: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    return encoded.ljust(size, b" ")


# Native flattened field, official one-based position, byte length, sentinel.
FIELDS = [
    ("RecordSpec", 1, 2, b"BN"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260815"),
    ("BanusiCode", 12, 6, b"123456"),
    ("BanusiName_Co", 18, 64, _pad("Corporate Owner Sentinel", 64)),
    ("BanusiName", 82, 64, _pad("Plain Owner Sentinel", 64)),
    ("BanusiNameKana", 146, 50, _pad("ｵｰﾅｰｾﾝﾁﾈﾙ", 50)),
    ("BanusiNameEng", 196, 100, _pad("Distinct Owner English Sentinel", 100)),
    ("Fukusyoku", 296, 60, _pad("Blue Red Pattern Sentinel", 60)),
    ("H_SetYear", 356, 4, b"2026"),
    ("H_HonSyokinTotal", 360, 10, b"0000001001"),
    ("H_FukaSyokin", 370, 10, b"0000001002"),
    ("H_ChakuKaisu1", 380, 6, b"000101"),
    ("H_ChakuKaisu2", 386, 6, b"000102"),
    ("H_ChakuKaisu3", 392, 6, b"000103"),
    ("H_ChakuKaisu4", 398, 6, b"000104"),
    ("H_ChakuKaisu5", 404, 6, b"000105"),
    ("H_ChakuKaisu6", 410, 6, b"000106"),
    ("R_SetYear", 416, 4, b"1999"),
    ("R_HonSyokinTotal", 420, 10, b"0000002001"),
    ("R_FukaSyokin", 430, 10, b"0000002002"),
    ("R_ChakuKaisu1", 440, 6, b"000201"),
    ("R_ChakuKaisu2", 446, 6, b"000202"),
    ("R_ChakuKaisu3", 452, 6, b"000203"),
    ("R_ChakuKaisu4", 458, 6, b"000204"),
    ("R_ChakuKaisu5", 464, 6, b"000205"),
    ("R_ChakuKaisu6", 470, 6, b"000206"),
    ("RecordDelimiter", 476, 2, b"\r\n"),
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
    assert len(record) == 477
    return bytes(record)


def _legacy_413_record() -> bytes:
    """Reconstruct the pre-2003 official shape without BanusiName bytes."""
    current = build_record()
    legacy = current[:81] + current[145:]
    assert len(legacy) == 413
    assert legacy[-2:] == b"\r\n"
    return legacy


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_record())
    record[17:19] = b"\x81\x20"
    return bytes(record)


def test_bn_layout_is_gap_free_and_uses_distinct_sentinels() -> None:
    assert len(FIELDS) == 28
    assert FIELDS[0][:3] == ("RecordSpec", 1, 2)
    assert FIELDS[-1][:3] == ("RecordDelimiter", 476, 2)
    assert all(
        position + size == next_position
        for (_, position, size, _), (_, next_position, _, _) in pairwise(FIELDS)
    )
    sentinels = [(size, EXPECTED[name]) for name, _, size, _ in FIELDS[:-1]]
    assert len(sentinels) == len(set(sentinels))


@pytest.mark.parametrize("field_name", sorted(EXPECTED))
def test_bn_reads_every_official_field_at_its_exact_offset(field_name: str) -> None:
    row = BNParser().parse(build_record())

    assert row is not None
    assert row[field_name] == EXPECTED[field_name]


def test_bn_emits_exactly_the_official_flattened_fields() -> None:
    row = BNParser().parse(build_record())

    assert row is not None
    assert BNParser.RECORD_LENGTH == 477
    assert set(row) == set(EXPECTED)


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_legacy_413_record(), id="official-pre-2003-413"),
        pytest.param(build_record()[:385] + b"\r\n", id="repository-387"),
        pytest.param(build_record()[:-1], id="short-476"),
        pytest.param(build_record() + b" ", id="long-478"),
        pytest.param(b"XX" + build_record()[2:], id="wrong-record-type"),
        pytest.param(build_record()[:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_bn_rejects_unsupported_or_corrupt_physical_records(record: bytes) -> None:
    assert BNParser().parse(record) is None


def test_bn_native_and_standard_schemas_match_the_business_contract() -> None:
    for table_name in ("NL_BN", "BANUSI"):
        assert set(get_table_column_types(table_name)) == BUSINESS_FIELDS
        assert get_table_primary_key_columns(table_name) == ["BanusiCode"]


@pytest.mark.parametrize(
    "importer_class,table_name,use_jravan_schema",
    [
        pytest.param(
            importer_class, table_name, standard, id=f"{importer_class.__name__}-{table_name}"
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_BN", False), ("BANUSI", True))
    ],
)
def test_bn_round_trips_every_business_field(
    tmp_path, importer_class, table_name: str, use_jravan_schema: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        parsed = BNParser().parse(build_record())
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


OBSOLETE_STANDARD_SCHEMA = """
    CREATE TABLE IF NOT EXISTS BANUSI (
        RecordSpec TEXT,
        DataKubun TEXT,
        MakeDate TEXT,
        BanusiName TEXT,
        BanusiName_Co TEXT,
        BanusiNameKana TEXT,
        BanusiNameEng TEXT,
        Fukusyoku TEXT,
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
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-banusi.db")})
    with database:
        database.execute(OBSOLETE_STANDARD_SCHEMA)
        database.execute(
            "INSERT INTO BANUSI (RecordSpec, DataKubun, MakeDate, BanusiName) "
            "VALUES (?, ?, ?, ?)",
            ("ZZ", "9", "20000101", "preserve-me"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([BNParser().parse(build_record())])
            )

        rows = database.fetch_all("SELECT RecordSpec, BanusiName FROM BANUSI")

    assert rows == [{"RecordSpec": "ZZ", "BanusiName": "preserve-me"}]
