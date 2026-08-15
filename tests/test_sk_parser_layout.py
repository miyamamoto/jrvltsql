#!/usr/bin/env python
"""SK parser contract for the current 208-byte JV-Data layout."""

import pytest

from scripts.extract_fixtures_from_db import extract_parser_info
from src.database.migration import SchemaMigrationError
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
from src.parser.sk_parser import SKParser

ZENKAKU_SPACE = b"\x81\x40"


def _pad(value, size, zenkaku=False):
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    filler = ZENKAKU_SPACE if zenkaku else b" "
    remainder = size - len(encoded)
    assert remainder % len(filler) == 0
    return encoded + filler * (remainder // len(filler))


PEDIGREE_FIELDS = (
    "FNum",
    "MNum",
    "FFNum",
    "FMNum",
    "MFNum",
    "MMNum",
    "FFFNum",
    "FFMNum",
    "FMFNum",
    "FMMNum",
    "MFFNum",
    "MFMNum",
    "MMFNum",
    "MMMNum",
)

# (parser field, official one-based position, byte length, sentinel)
FIELDS = [
    ("RecordSpec", 1, 2, b"SK"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260815"),
    ("KettoNum", 12, 10, b"2024100001"),
    ("BirthDate", 22, 8, b"20240401"),
    ("SexCD", 30, 1, b"3"),
    ("HinsyuCD", 31, 1, b"2"),
    ("KeiroCD", 32, 2, b"04"),
    ("SankuMochiKubun", 34, 1, b"0"),
    ("ImportYear", 35, 4, b"2025"),
    ("BreederCode", 39, 8, b"BR000039"),
    ("SanchiName", 47, 20, _pad("テスト産地", 20, zenkaku=True)),
]
FIELDS.extend(
    (field_name, 67 + 10 * index, 10, f"{11 + index:02d}000000{index + 1:02d}".encode())
    for index, field_name in enumerate(PEDIGREE_FIELDS)
)
FIELDS.append(("RecordDelimiter", 207, 2, b"\r\n"))

EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
STORED_CURRENT = set(EXPECTED) - {"RecordDelimiter"}


def build_current_record():
    record = bytearray()
    for name, position, size, value in FIELDS:
        assert len(value) == size, f"{name}: {len(value)} != {size}"
        assert len(record) == position - 1, f"{name}: gap at {len(record)}"
        record += value
    assert len(record) == 208
    return bytes(record)


def build_legacy_record():
    """Build the complete official 4.8.0.2 physical SK layout."""
    record = bytearray()
    record += b"SK1" + b"20260815"
    record += b"2024100001" + b"20240401"
    record += b"3" + b"2" + b"04" + b"0" + b"2025"
    record += b"BR0039"
    record += _pad("旧仕様産地", 20, zenkaku=True)
    for index in range(14):
        record += f"{index + 1:08d}".encode()
    record += b"\r\n"
    assert len(record) == 178
    return bytes(record)


class TestSKParserCurrentLayout:
    def setup_method(self):
        self.parser = SKParser()
        self.record = build_current_record()

    def test_record_length_and_delimiter_match_current_spec(self):
        assert SKParser.RECORD_LENGTH == 208
        assert self.record[206:208] == b"\r\n"

    def test_every_field_uses_a_distinct_decoded_sentinel(self):
        assert len(set(EXPECTED.values())) == len(EXPECTED)

    @pytest.mark.parametrize("field_name", sorted(EXPECTED))
    def test_every_field_is_read_from_its_current_spec_position(self, field_name):
        row = self.parser.parse(self.record)
        assert row[field_name] == EXPECTED[field_name]

    def test_parser_emits_exactly_the_current_fields(self):
        assert set(self.parser.parse(self.record)) == set(EXPECTED)


class TestSKParserExactLayoutEnforcement:
    def setup_method(self):
        self.parser = SKParser()
        self.record = build_current_record()

    def test_exact_current_record_is_accepted(self):
        assert self.parser.parse(self.record)["MMMNum"] == EXPECTED["MMMNum"]

    @pytest.mark.parametrize(
        "record",
        [
            pytest.param(build_legacy_record(), id="official-legacy-178"),
            pytest.param(build_current_record()[:207], id="short-207"),
            pytest.param(build_current_record() + b" ", id="long-209"),
            pytest.param(build_current_record()[:206] + b"\n\r", id="delimiter-lfcr"),
            pytest.param(build_current_record()[:206] + b"  ", id="delimiter-spaces"),
        ],
    )
    def test_unsupported_record_returns_none(self, record):
        assert self.parser.parse(record) is None


def test_native_schema_matches_the_current_parser_contract():
    assert set(get_table_column_types("NL_SK")) == set(EXPECTED)
    assert get_table_primary_key_columns("NL_SK") == ["KettoNum"]


def test_standard_mapping_and_schema_match_the_current_contract():
    assert JRAVAN_TO_JLTSQL["SANKU"] == "NL_SK"
    assert JLTSQL_TO_JRAVAN["NL_SK"] == "SANKU"
    assert set(get_table_column_types("SANKU")) == STORED_CURRENT
    assert get_table_primary_key_columns("SANKU") == ["KettoNum"]


def test_standard_import_refuses_the_obsolete_keyless_schema(tmp_path):
    obsolete_schema = """
        CREATE TABLE IF NOT EXISTS SANKU (
            RecordSpec CHAR(2), DataKubun CHAR(1), MakeDate DATE,
            BirthDate DATE, SexCD VARCHAR(1), HinsyuCD VARCHAR(1),
            KeiroCD VARCHAR(2), SankuMochiKubun VARCHAR(1),
            ImportYear VARCHAR(4), BreederCode VARCHAR(8),
            SanchiName VARCHAR(20), FNum VARCHAR(10), MNum VARCHAR(10),
            FFNum VARCHAR(10), FMNum VARCHAR(10), MFNum VARCHAR(10),
            MMNum VARCHAR(10), FFFNum VARCHAR(10), FFMNum VARCHAR(10),
            FMFNum VARCHAR(10), FMMNum VARCHAR(10), MFFNum VARCHAR(10),
            MFMNum VARCHAR(10), MMFNum VARCHAR(10)
        )
    """
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-sanku.db")})
    with database:
        database.execute(obsolete_schema)
        with pytest.raises(SchemaMigrationError, match="primary key"):
            DataImporter(database, use_jravan_schema=True).import_records(
                iter([SKParser().parse(build_current_record())])
            )
        columns = {row["name"] for row in database.fetch_all("PRAGMA table_info(SANKU)")}

    assert "KettoNum" not in columns
    assert "MMMNum" not in columns


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_standard_import_refuses_a_legacy_alias_only_database(tmp_path, importer_class):
    legacy_schema = SCHEMAS["NL_SK"].replace("NL_SK", "HANSYOKU_UMA", 1)
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-alias-only.db")})
    with database:
        database.execute(legacy_schema)
        with pytest.raises(
            SchemaMigrationError,
            match=r"HANSYOKU_UMA.*SANKU|SANKU.*HANSYOKU_UMA",
        ):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([SKParser().parse(build_current_record())])
            )
        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM HANSYOKU_UMA")

    assert row_count["count"] == 0


def test_fixture_extractor_discovers_every_current_sk_field():
    parser_path = "src/parser/sk_parser.py"
    fields, record_length = extract_parser_info(parser_path)
    discovered = {name: (start, end) for name, start, end in fields}

    assert record_length == SKParser.RECORD_LENGTH
    assert set(discovered) == set(EXPECTED)
    for index, field_name in enumerate(PEDIGREE_FIELDS):
        start = 66 + 10 * index
        assert discovered[field_name] == (start, start + 10)


@pytest.mark.parametrize(
    ("importer_class", "table_name", "use_jravan_schema"),
    [
        pytest.param(
            importer_class,
            table_name,
            use_jravan_schema,
            id=f"{importer_class.__name__}-{table_name}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, use_jravan_schema in (("NL_SK", False), ("SANKU", True))
    ],
)
def test_current_record_round_trips_through_supported_storage(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
):
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        record = SKParser().parse(build_current_record())
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([record]))
        row = database.fetch_one(f"SELECT KettoNum, FNum, MMMNum FROM {table_name}")

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 1
    assert row["KettoNum"] == EXPECTED["KettoNum"]
    assert row["FNum"] == EXPECTED["FNum"]
    assert row["MMMNum"] == EXPECTED["MMMNum"]
