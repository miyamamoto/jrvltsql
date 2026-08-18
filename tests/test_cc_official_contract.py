"""Official CC course-change contract from pinned JRA-VAN sources."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema import SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_types,
    get_table_column_nullability,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, validate_import_record_header
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.cc_parser import CCParser
from src.parser.factory import ParserFactory
from src.parser.status_domain import CURRENT_ACCUMULATED_DATA_KUBUN
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
CONTRACT = json.loads((FIXTURES / "cc_contract_4901.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8"))

FIELDS = (
    ("RecordSpec", 1, 2, b"CC"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260818"),
    ("Year", 12, 4, b"2026"),
    ("MonthDay", 16, 4, b"0818"),
    ("JyoCD", 20, 2, b"05"),
    ("Kaiji", 22, 2, b"03"),
    ("Nichiji", 24, 2, b"08"),
    ("RaceNum", 26, 2, b"11"),
    ("HappyoTime", 28, 8, b"08181200"),
    ("AtoKyori", 36, 4, b"2000"),
    ("AtoTruckCD", 40, 2, b"18"),
    ("MaeKyori", 42, 4, b"1800"),
    ("MaeTruckCD", 46, 2, b"17"),
    ("JiyuCD", 48, 1, b"1"),
    ("RecordDelimiter", 49, 2, b"\r\n"),
)
OFFICIAL_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
STORAGE_FIELDS = {name for name, _, _, _ in FIELDS} - {"RecordDelimiter"}


def _put(record: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    record[start : start + width] = encoded.ljust(width, b" ")


def build_cc_record(**overrides: str) -> bytes:
    values = {name: default.decode("cp932") for name, _, _, default in FIELDS[:-1]}
    values.update(overrides)
    record = bytearray(b" " * CCParser.RECORD_LENGTH)
    for name, position, width, _ in FIELDS[:-1]:
        _put(record, position - 1, width, values[name])
    record[-2:] = b"\r\n"
    assert len(record) == 50
    return bytes(record)


def parsed_cc(**overrides: str) -> dict:
    parsed = CCParser().parse(build_cc_record(**overrides))
    assert parsed is not None
    return parsed


def test_cc_oracle_binds_both_workbooks_sdk_and_every_parser_span() -> None:
    assert CONTRACT["record_length"] == 50
    assert CONTRACT["fields"] == [[name, position, width] for name, position, width, _ in FIELDS]
    assert tuple(CONTRACT["primary_key"]) == OFFICIAL_KEY
    assert CONTRACT["current_data_kubun"] == ["1"]
    assert CURRENT_ACCUMULATED_DATA_KUBUN["CC"] == frozenset({"1"})
    assert CONTRACT["history"]["physical_layout_changed"] is False
    assert CONTRACT["current_provider_specs"] == ["0B14", "0B16"]
    assert CONTRACT["snapshot_provider_spec"] == "0B14"

    parser_spans = [(field.name, field.start + 1, field.length) for field in CCParser()._fields]
    assert parser_spans == [(name, position, width) for name, position, width, _ in FIELDS]
    direct = CCParser().parse(build_cc_record())
    assert direct == ParserFactory().parse(build_cc_record())
    assert direct is not None
    assert tuple(
        direct[name] for name in ("AtoKyori", "AtoTruckCD", "MaeKyori", "MaeTruckCD", "JiyuCD")
    ) == ("2000", "18", "1800", "17", "1")

    assert MANIFEST["root_records"]["CC"] == {"struct": "JV_CC_INFO", "length": 50}
    assert [
        (field["name"], field["start"], field["width"])
        for field in MANIFEST["structures"]["CC_INFO"]["fields"]
    ] == [("Kyori", 1, 4), ("TruckCd", 5, 2)]


@pytest.mark.parametrize(
    "overrides",
    [
        {"MakeDate": "20260230"},
        {"Year": "20A6"},
        {"MonthDay": "0230"},
        {"JyoCD": "ZZ"},
        {"Kaiji": "A1"},
        {"Nichiji": "0A"},
        {"RaceNum": "1X"},
        {"HappyoTime": "08189999"},
        {"HappyoTime": "8181200"},
        {"AtoKyori": "2X00"},
        {"AtoKyori": "200"},
        {"AtoTruckCD": "ZZ"},
        {"MaeKyori": "18Y0"},
        {"MaeTruckCD": "99"},
        {"JiyuCD": "9"},
    ],
)
def test_cc_parser_rejects_nonofficial_header_key_and_body_values(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        CCParser().parse(build_cc_record(**overrides))


def test_cc_explicit_initial_values_remain_accepted_and_lossless() -> None:
    parsed = parsed_cc(
        HappyoTime="00000000",
        AtoKyori="0000",
        AtoTruckCD="00",
        MaeKyori="0000",
        MaeTruckCD="00",
        JiyuCD="0",
    )
    assert tuple(
        parsed[name]
        for name in ("HappyoTime", "AtoKyori", "AtoTruckCD", "MaeKyori", "MaeTruckCD", "JiyuCD")
    ) == ("00000000", "0000", "00", "0000", "00", "0")


def test_cc_storage_schemas_encode_the_complete_official_identity() -> None:
    for table_name in ("NL_CC", "RT_CC", "COURSE_CHANGE"):
        assert tuple(get_table_primary_key_columns(table_name)) == OFFICIAL_KEY
        nullability = get_table_column_nullability(table_name)
        assert set(nullability) == STORAGE_FIELDS
        assert all(nullability[column] is False for column in STORAGE_FIELDS)
        assert set(get_table_column_types(table_name)) == STORAGE_FIELDS
    assert TABLE_METADATA["NL_CC"]["primary_key"] == list(OFFICIAL_KEY)


def _defective_schema(table_name: str, defect: str) -> str:
    schema = SCHEMAS[table_name] if table_name == "NL_CC" else JRAVAN_SCHEMAS[table_name]
    key = "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    replacements = {
        "wrong-key": (key, "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji)"),
        "nullable-body": (
            "AtoTruckCD TEXT NOT NULL",
            "AtoTruckCD TEXT",
        ),
        "wrong-type": (
            "Year INTEGER NOT NULL",
            "Year TEXT NOT NULL",
        ),
        "short-text": (
            "HappyoTime TEXT NOT NULL",
            "HappyoTime VARCHAR(7) NOT NULL",
        ),
    }
    standard_replacements = {
        "nullable-body": (
            "AtoTruckCD                     VARCHAR(2) NOT NULL",
            "AtoTruckCD                     VARCHAR(2)         ",
        ),
        "wrong-type": (
            "Year                           SMALLINT NOT NULL",
            "Year                           VARCHAR(4) NOT NULL",
        ),
        "short-text": (
            "HappyoTime                     VARCHAR(8) NOT NULL",
            "HappyoTime                     VARCHAR(7) NOT NULL",
        ),
    }
    if table_name != "NL_CC" and defect in standard_replacements:
        old, new = standard_replacements[defect]
    elif defect in replacements:
        old, new = replacements[defect]
    else:
        body, close = schema.rsplit(")", 1)
        additions = {
            "extra-unique": "UNIQUE (HappyoTime)",
            "extra-check": "CHECK (JiyuCD = '0')",
            "extra-foreign-key": (
                f"FOREIGN KEY ({', '.join(OFFICIAL_KEY)}) REFERENCES {table_name} "
                f"({', '.join(OFFICIAL_KEY)}) ON DELETE CASCADE"
            ),
            "extra-required-column": "ExternalRequired TEXT NOT NULL",
        }
        return f"{body}, {additions[defect]}\n        ){close}"
    mutated = schema.replace(old, new)
    assert mutated != schema
    return mutated


@pytest.mark.parametrize("table_name,standard", [("NL_CC", False), ("COURSE_CHANGE", True)])
@pytest.mark.parametrize(
    "defect",
    [
        "wrong-key",
        "nullable-body",
        "wrong-type",
        "short-text",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
    ],
)
def test_cc_schema_defects_fail_before_any_row_or_schema_mutation(
    tmp_path, table_name: str, standard: bool, defect: str
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{defect}.db")})
    with database:
        database.execute(_defective_schema(table_name, defect))
        database.commit()
        before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_cc()]))
        assert (
            database.fetch_one(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            )
            == before
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_cc_schema_manager_does_not_mutate_an_unsafe_existing_table(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "manager-unsafe.db")})
    with database:
        database.execute(_defective_schema("NL_CC", "extra-unique"))
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_CC")')
        assert SchemaManager(database).create_table("NL_CC") is False
        assert database.fetch_all('PRAGMA table_xinfo("NL_CC")') == before


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
@pytest.mark.parametrize("table_name,standard", [("NL_CC", False), ("COURSE_CHANGE", True)])
def test_cc_provider_revision_replaces_one_official_identity(
    tmp_path, importer_class, auto_commit: bool, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"revision-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    first = parsed_cc()
    revised = parsed_cc(HappyoTime="08181205", AtoKyori="2200", AtoTruckCD="19")
    with database:
        database.execute(schema)
        database.commit()
        result = importer_class(database, batch_size=1, use_jravan_schema=standard).import_records(
            iter([first, revised]), auto_commit=auto_commit
        )
        rows = database.fetch_all(f"SELECT HappyoTime, AtoKyori, AtoTruckCD FROM {table_name}")
    assert result["records_imported"] == 2
    assert result["records_failed"] == 0
    assert rows == [
        {"HappyoTime": "08181205", "AtoKyori": 2200 if not standard else "2200", "AtoTruckCD": "19"}
    ]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
@pytest.mark.parametrize("table_name,standard", [("NL_CC", False), ("COURSE_CHANGE", True)])
def test_cc_caller_validation_precedes_coercion_and_mutation(
    tmp_path, importer_class, auto_commit: bool, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    invalid = parsed_cc()
    invalid["JiyuCD"] = "9"
    with database:
        database.execute(schema)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=standard).import_records(
                iter([invalid]), auto_commit=auto_commit
            )
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_cc_realtime_rejects_invalid_body_before_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_CC"])
        database.commit()
        invalid = parsed_cc()
        invalid["AtoTruckCD"] = "ZZ"
        result = RealtimeUpdater(database).process_parsed_records_batch([invalid])
        assert result["success"] is False
        assert result["inserted"] == 0
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_CC") == {"n": 0}


@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
@pytest.mark.parametrize("table_name,standard", [("NL_CC", False), ("COURSE_CHANGE", True)])
def test_cc_single_record_uses_the_same_fail_closed_contract(
    tmp_path, auto_commit: bool, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=standard)
        assert importer.import_single_record(parsed_cc(), auto_commit=auto_commit)
        invalid = parsed_cc()
        invalid["JiyuCD"] = "9"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid, auto_commit=auto_commit)
        expected = 1 if auto_commit else 0
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": expected}


def test_cc_date_snapshot_removes_only_stale_cc_rows(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "snapshot.db")})
    with database:
        for table_name in RealtimeUpdater.DATE_SNAPSHOT_TABLES:
            database.execute(SCHEMAS[table_name])
        database.commit()
        updater = RealtimeUpdater(database)
        seeded = updater.process_parsed_records_batch(
            [parsed_cc(RaceNum="10"), parsed_cc(RaceNum="11")]
        )
        updater.replace_date_snapshot("20260818")
        revised = updater.process_parsed_records_batch(
            [parsed_cc(RaceNum="11", HappyoTime="08181205", AtoKyori="2200")]
        )
        rows = database.fetch_all(
            "SELECT RaceNum, HappyoTime, AtoKyori FROM RT_CC ORDER BY RaceNum"
        )
    assert seeded["success"] is True
    assert revised["success"] is True
    assert rows == [{"RaceNum": 11, "HappyoTime": "08181205", "AtoKyori": 2200}]


def test_cc_header_validator_rejects_missing_blank_and_conflicting_aliases() -> None:
    valid = parsed_cc()
    assert validate_import_record_header(valid) == ("CC", "1")
    for row in (
        {key: value for key, value in valid.items() if key != "DataKubun"},
        {**valid, "DataKubun": ""},
        {**valid, "headDataKubun": "0"},
        {**valid, "headRecordSpec": "TC"},
    ):
        with pytest.raises(SchemaMigrationError):
            validate_import_record_header(row)
