#!/usr/bin/env python
"""HN parser contract for the current 251-byte JV-Data layout."""

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
from src.parser.hn_parser import HNParser

ZENKAKU_SPACE = b"\x81\x40"


def _pad(value, size, zenkaku=False):
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    filler = ZENKAKU_SPACE if zenkaku else b" "
    remainder = size - len(encoded)
    assert remainder % len(filler) == 0
    return encoded + filler * (remainder // len(filler))


# (native parser field, official one-based position, byte length, sentinel)
FIELDS = [
    ("RecordSpec", 1, 2, b"HN"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260815"),
    ("HansyokuNum", 12, 10, b"1234567890"),
    ("reserved", 22, 8, b"RSV00022"),
    ("KettoNum", 30, 10, b"2019900002"),
    ("DelKubun", 40, 1, b"2"),
    ("Bamei", 41, 36, _pad("テスト繁殖馬", 36, zenkaku=True)),
    ("BameiKana", 77, 40, _pad("ﾃｽﾄﾊﾝｼｮｸﾊﾞ", 40)),
    ("BameiEng", 117, 80, _pad("Distinct Breeding Horse Sentinel", 80)),
    ("BirthYear", 197, 4, b"2019"),
    ("SexCD", 201, 1, b"3"),
    ("HinsyuCD", 202, 1, b"4"),
    ("KeiroCD", 203, 2, b"05"),
    ("MochiKubun", 205, 1, b"6"),
    ("ImportYear", 206, 4, b"2025"),
    ("SanchiName", 210, 20, _pad("テスト産地", 20, zenkaku=True)),
    ("FHansyokuNum", 230, 10, b"1111111111"),
    ("MHansyokuNum", 240, 10, b"2222222222"),
    ("RecordDelimiter", 250, 2, b"\r\n"),
]

EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
STORED_NATIVE = set(EXPECTED) - {"RecordDelimiter"}
STANDARD_ALIASES = {
    "MochiKubun": "HansyokuMochiKubun",
    "FHansyokuNum": "HansyokuFNum",
    "MHansyokuNum": "HansyokuMNum",
}
STORED_STANDARD = {STANDARD_ALIASES.get(name, name) for name in STORED_NATIVE}


def build_record():
    record = bytearray()
    for name, position, size, value in FIELDS:
        assert len(value) == size, f"{name}: {len(value)} != {size}"
        assert len(record) == position - 1, f"{name}: gap at {len(record)} (want {position - 1})"
        record += value
    assert len(record) == HNParser.RECORD_LENGTH
    return bytes(record)


class TestHNParserCurrentLayout:
    def setup_method(self):
        self.parser = HNParser()
        self.record = build_record()

    def test_record_length_and_delimiter_match_current_spec(self):
        assert HNParser.RECORD_LENGTH == 251
        assert self.record[249:251] == b"\r\n"

    def test_every_field_uses_a_distinct_decoded_sentinel(self):
        assert len(set(EXPECTED.values())) == len(EXPECTED)

    @pytest.mark.parametrize("field_name", sorted(EXPECTED))
    def test_every_field_is_read_from_its_current_spec_position(self, field_name):
        row = self.parser.parse(self.record)
        assert row[field_name] == EXPECTED[field_name]

    def test_parser_emits_exactly_the_current_fields(self):
        assert set(self.parser.parse(self.record)) == set(EXPECTED)


class TestHNParserExactLayoutEnforcement:
    def setup_method(self):
        self.parser = HNParser()
        self.record = build_record()

    def test_exact_current_record_is_accepted(self):
        assert self.parser.parse(self.record)["HansyokuNum"] == "1234567890"

    @pytest.mark.parametrize(
        "mutate",
        [
            pytest.param(lambda r: r[:243] + b"\r\n", id="legacy-245-crlf"),
            pytest.param(lambda r: r[:250], id="short-250"),
            pytest.param(lambda r: r + b" ", id="long-252"),
            pytest.param(lambda r: r[:249] + b"\n\r", id="delimiter-lfcr"),
            pytest.param(lambda r: r[:249] + b"  ", id="delimiter-spaces"),
        ],
    )
    def test_unsupported_record_returns_none(self, mutate):
        assert self.parser.parse(mutate(self.record)) is None


def test_native_schema_matches_the_current_parser_contract():
    assert set(get_table_column_types("NL_HN")) == set(EXPECTED)
    assert get_table_primary_key_columns("NL_HN") == ["HansyokuNum"]
    assert "Reserved_197" not in SCHEMAS["NL_HN"]


def test_standard_schema_matches_the_current_sdk_contract():
    assert set(get_table_column_types("HANSYOKU")) == STORED_STANDARD
    assert get_table_primary_key_columns("HANSYOKU") == ["HansyokuNum"]


def test_standard_import_refuses_the_obsolete_keyless_schema(tmp_path):
    current_schema = JRAVAN_SCHEMAS["HANSYOKU"]
    obsolete_schema = (
        current_schema.replace(
            "            HansyokuNum                    VARCHAR(10)         ,  -- 繁殖登録番号\n",
            "",
        )
        .replace(
            "            HansyokuFNum                   VARCHAR(10)         ,  -- 父馬繁殖登録番号\n",
            "            HansyokuFNum                   VARCHAR(255)          -- テキスト\n",
        )
        .replace(
            "            HansyokuMNum                   VARCHAR(10)         ,  -- 母馬繁殖登録番号\n"
            "            PRIMARY KEY (HansyokuNum)\n",
            "",
        )
    )
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-hansyoku.db")})
    with database:
        database.execute(obsolete_schema)
        with pytest.raises(SchemaMigrationError, match="primary key"):
            DataImporter(database, use_jravan_schema=True).import_records(
                iter([HNParser().parse(build_record())])
            )

        columns = {row["name"] for row in database.fetch_all("PRAGMA table_info(HANSYOKU)")}

    assert "HansyokuNum" not in columns
    assert "HansyokuMNum" not in columns


@pytest.mark.parametrize(
    (
        "importer_class",
        "table_name",
        "use_jravan_schema",
        "father_column",
        "mother_column",
    ),
    [
        pytest.param(
            importer_class,
            table_name,
            use_jravan_schema,
            father_column,
            mother_column,
            id=f"{importer_class.__name__}-{table_name}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, use_jravan_schema, father_column, mother_column in (
            ("NL_HN", False, "FHansyokuNum", "MHansyokuNum"),
            ("HANSYOKU", True, "HansyokuFNum", "HansyokuMNum"),
        )
    ],
)
def test_current_record_round_trips_through_supported_storage(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
    father_column,
    mother_column,
):
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        record = HNParser().parse(build_record())
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([record]))
        row = database.fetch_one(
            f"SELECT HansyokuNum, BameiEng, {father_column}, {mother_column} " f"FROM {table_name}"
        )

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert stats["batches_processed"] == 1
    assert row["HansyokuNum"] == "1234567890"
    assert row["BameiEng"] == "Distinct Breeding Horse Sentinel"
    assert row[father_column] == "1111111111"
    assert row[mother_column] == "2222222222"
