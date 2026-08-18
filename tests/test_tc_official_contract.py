"""Official TC start-time-change contract from pinned JRA-VAN sources."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, validate_import_record_header
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.factory import ParserFactory
from src.parser.status_domain import CURRENT_ACCUMULATED_DATA_KUBUN
from src.parser.tc_parser import TCParser
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
CONTRACT = json.loads((FIXTURES / "tc_contract_4901.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8"))

FIELDS = (
    ("RecordSpec", 1, 2, b"TC"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260818"),
    ("Year", 12, 4, b"2026"),
    ("MonthDay", 16, 4, b"0818"),
    ("JyoCD", 20, 2, b"05"),
    ("Kaiji", 22, 2, b"03"),
    ("Nichiji", 24, 2, b"08"),
    ("RaceNum", 26, 2, b"11"),
    ("HappyoTime", 28, 8, b"08181200"),
    ("AtoJi", 36, 2, b"12"),
    ("AtoFun", 38, 2, b"10"),
    ("MaeJi", 40, 2, b"12"),
    ("MaeFun", 42, 2, b"00"),
    ("RecordDelimiter", 44, 2, b"\r\n"),
)
OFFICIAL_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
NATIVE_FIELDS = {name for name, _, _, _ in FIELDS} - {"RecordDelimiter"}
STANDARD_FIELDS = set(NATIVE_FIELDS)


def _put(record: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    record[start : start + width] = encoded.ljust(width, b" ")


def build_tc_record(**overrides: str) -> bytes:
    values = {name: default.decode("cp932") for name, _, _, default in FIELDS[:-1]}
    values.update(overrides)
    record = bytearray(b" " * TCParser.RECORD_LENGTH)
    for name, position, width, _ in FIELDS[:-1]:
        _put(record, position - 1, width, values[name])
    record[-2:] = b"\r\n"
    assert len(record) == 45
    return bytes(record)


def parsed_tc(**overrides: str) -> dict:
    parsed = TCParser().parse(build_tc_record(**overrides))
    assert parsed is not None
    return parsed


def import_tc_records(
    database,
    entrypoint: str,
    records: list[dict],
    *,
    standard: bool,
    auto_commit: bool,
) -> dict:
    if entrypoint == "single":
        importer = DataImporter(database, use_jravan_schema=standard)
        for record in records:
            assert importer.import_single_record(record, auto_commit=auto_commit)
        return importer.get_statistics()
    importer_class = DataImporter if entrypoint == "data-batch" else OptimizedDataImporter
    return importer_class(
        database,
        batch_size=1000,
        use_jravan_schema=standard,
    ).import_records(iter(records), auto_commit=auto_commit)


def test_tc_oracle_binds_both_workbooks_sdk_and_every_parser_span() -> None:
    assert CONTRACT["record_length"] == 45
    assert CONTRACT["format_sources"] == [
        {
            "artifact": "JV-Data4802.xlsx",
            "sha256": "6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7",
            "sheet": "フォーマット",
            "rows": "1509-1528",
        },
        {
            "artifact": "JV-Data4901.xlsx",
            "sha256": "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234",
            "sheet": "フォーマット",
            "rows": "1509-1528",
        },
    ]
    assert CONTRACT["fields"] == [[name, position, width] for name, position, width, _ in FIELDS]
    assert tuple(CONTRACT["primary_key"]) == OFFICIAL_KEY
    assert CONTRACT["current_data_kubun"] == ["1"]
    assert CURRENT_ACCUMULATED_DATA_KUBUN["TC"] == frozenset({"1"})
    assert CONTRACT["history"] == {
        "added": "2004-05-25",
        "version": "1.1.6",
        "physical_layout_changed": False,
        "sources": [
            "JV-Data4901.xlsx:変更履歴:216,220",
            "JV-Data4802.xlsx:変更履歴:173,177",
        ],
    }
    assert CONTRACT["current_provider_specs"] == ["0B14", "0B16"]
    assert CONTRACT["snapshot_provider_spec"] == "0B14"

    parser_spans = [(field.name, field.start + 1, field.length) for field in TCParser()._fields]
    assert parser_spans == [(name, position, width) for name, position, width, _ in FIELDS]
    direct = TCParser().parse(build_tc_record())
    factory = ParserFactory().parse(build_tc_record())
    assert direct == factory
    assert direct is not None
    assert direct["HappyoTime"] == "08181200"
    assert tuple(direct[name] for name in ("AtoJi", "AtoFun", "MaeJi", "MaeFun")) == (
        "12",
        "10",
        "12",
        "00",
    )

    assert MANIFEST["root_records"]["TC"] == {"struct": "JV_TC_INFO", "length": 45}
    structures = MANIFEST["structures"]
    assert [
        (field["name"], field["start"], field["width"], field.get("struct"))
        for field in structures["JV_TC_INFO"]["fields"]
    ] == [
        ("head", 1, 11, "RECORD_ID"),
        ("id", 12, 16, "RACE_ID"),
        ("HappyoTime", 28, 8, "MDHM"),
        ("TCInfoAfter", 36, 4, "TC_INFO"),
        ("TCInfoBefore", 40, 4, "TC_INFO"),
        ("crlf", 44, 2, None),
    ]
    assert [
        (field["name"], field["start"], field["width"]) for field in structures["TC_INFO"]["fields"]
    ] == [
        ("Ji", 1, 2),
        ("Fun", 3, 2),
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"DataKubun": "0"},
        {"MakeDate": "20260230"},
        {"Year": "20A6"},
        {"MonthDay": "0230"},
        {"JyoCD": "ZZ"},
        {"Kaiji": "A1"},
        {"Nichiji": "0A"},
        {"RaceNum": "1X"},
        {"HappyoTime": "08189999"},
        {"AtoJi": "24"},
        {"AtoFun": "60"},
        {"MaeJi": "25"},
        {"MaeFun": "61"},
    ],
)
def test_tc_parser_rejects_nonofficial_header_key_and_time_values(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        TCParser().parse(build_tc_record(**overrides))


def test_tc_zero_initialized_time_values_remain_lossless() -> None:
    parsed = parsed_tc(HappyoTime="00000000", AtoJi="00", AtoFun="00", MaeJi="00", MaeFun="00")
    assert parsed["HappyoTime"] == "00000000"
    assert tuple(parsed[name] for name in ("AtoJi", "AtoFun", "MaeJi", "MaeFun")) == (
        "00",
        "00",
        "00",
        "00",
    )


def test_tc_native_standard_and_realtime_schemas_encode_the_official_identity() -> None:
    for table_name in ("NL_TC", "RT_TC", "HASSOU_JIKOKU_CHANGE"):
        assert tuple(get_table_primary_key_columns(table_name)) == OFFICIAL_KEY
        nullability = get_table_column_nullability(table_name)
        assert all(nullability[column] is False for column in OFFICIAL_KEY)
    assert set(get_table_column_types("NL_TC")) == NATIVE_FIELDS
    assert set(get_table_column_types("RT_TC")) == NATIVE_FIELDS
    assert set(get_table_column_types("HASSOU_JIKOKU_CHANGE")) == STANDARD_FIELDS
    metadata = TABLE_METADATA["NL_TC"]
    assert metadata["primary_key"] == list(OFFICIAL_KEY)
    assert [(column["name"], column["type"]) for column in metadata["columns"]] == list(
        get_table_column_types("NL_TC").items()
    )


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard"),
    [
        (DataImporter, "NL_TC", False),
        (OptimizedDataImporter, "NL_TC", False),
        (DataImporter, "HASSOU_JIKOKU_CHANGE", True),
        (OptimizedDataImporter, "HASSOU_JIKOKU_CHANGE", True),
    ],
)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_tc_provider_revision_replaces_one_official_identity(
    tmp_path, importer_class, table_name: str, standard: bool, auto_commit: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"ordered-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    first = parsed_tc()
    revised = parsed_tc(HappyoTime="08181205", AtoJi="12", AtoFun="20")
    with database:
        database.execute(schema)
        database.commit()
        result = importer_class(database, batch_size=1, use_jravan_schema=standard).import_records(
            iter([first, revised]), auto_commit=auto_commit
        )
        rows = database.fetch_all(f"SELECT HappyoTime, AtoJi, AtoFun FROM {table_name}")
    assert result["records_imported"] == 2
    assert result["records_failed"] == 0
    assert rows == [{"HappyoTime": "08181205", "AtoJi": "12", "AtoFun": "20"}]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
def test_tc_caller_validation_precedes_coercion_and_mutation(
    tmp_path, importer_class, auto_commit: bool, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    invalid_rows = []
    for field_name, invalid_value in (
        ("MakeDate", "20260230"),
        ("Year", "20A6"),
        ("Year", 26),
        ("MonthDay", "0230"),
        ("JyoCD", "ZZ"),
        ("Kaiji", "A1"),
        ("HappyoTime", "08189999"),
        ("AtoJi", "24"),
        ("AtoFun", "60"),
        ("MaeJi", "25"),
        ("MaeFun", "61"),
    ):
        row = parsed_tc()
        row[field_name] = invalid_value
        invalid_rows.append(row)

    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, use_jravan_schema=standard)
        for invalid in invalid_rows:
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([invalid]), auto_commit=auto_commit)
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def _defective_schema(table_name: str, defect: str) -> str:
    schema = SCHEMAS[table_name] if table_name == "NL_TC" else JRAVAN_SCHEMAS[table_name]
    key = "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    if defect == "wrong-key":
        return schema.replace(key, "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji)")
    if defect == "nullable-key":
        return schema.replace("Year INTEGER NOT NULL", "Year INTEGER").replace(
            "Year                           SMALLINT NOT NULL",
            "Year                           SMALLINT         ",
        )
    if defect == "wrong-type":
        return schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL").replace(
            "Year                           SMALLINT NOT NULL",
            "Year                           VARCHAR(4) NOT NULL",
        )
    if defect == "short-text":
        return schema.replace("HappyoTime TEXT NOT NULL", "HappyoTime VARCHAR(7) NOT NULL").replace(
            "HappyoTime                     VARCHAR(8) NOT NULL",
            "HappyoTime                     VARCHAR(7) NOT NULL",
        )
    if defect == "extra-unique":
        body, close = schema.rsplit(")", 1)
        return f"{body}, UNIQUE (HappyoTime)\n        ){close}"
    if defect == "extra-check":
        body, close = schema.rsplit(")", 1)
        return f"{body}, CHECK (AtoJi = '00')\n        ){close}"
    if defect == "extra-foreign-key":
        body, close = schema.rsplit(")", 1)
        return (
            f"{body}, FOREIGN KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) "
            f"REFERENCES {table_name} "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) ON DELETE CASCADE\n"
            f"        ){close}"
        )
    if defect == "extra-required-column":
        if key in schema:
            return schema.replace(key, f"ExternalRequired TEXT NOT NULL, {key}")
        body, close = schema.rsplit(")", 1)
        return f"{body}, ExternalRequired TEXT NOT NULL\n        ){close}"
    if defect == "extra-generated-required-column":
        if key in schema:
            return schema.replace(
                key,
                "ExternalRequired TEXT GENERATED ALWAYS AS (NULL) " f"VIRTUAL NOT NULL, {key}",
            )
        body, close = schema.rsplit(")", 1)
        return (
            f"{body}, ExternalRequired TEXT GENERATED ALWAYS AS (NULL) "
            f"VIRTUAL NOT NULL\n        ){close}"
        )
    raise AssertionError(defect)


@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
@pytest.mark.parametrize(
    "defect",
    [
        "wrong-key",
        "nullable-key",
        "wrong-type",
        "short-text",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
        "extra-generated-required-column",
    ],
)
def test_tc_schema_defects_fail_before_any_row_mutation(
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
            DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_tc()]))
        assert (
            database.fetch_one(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            )
            == before
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_tc_schema_manager_preflights_before_an_additive_column_change(tmp_path) -> None:
    unsafe = _defective_schema("NL_TC", "extra-unique").replace("MaeFun TEXT NOT NULL,", "")
    database = SQLiteDatabase({"path": str(tmp_path / "manager-unsafe.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        before = database.fetch_all('PRAGMA table_xinfo("NL_TC")')
        assert SchemaManager(database).create_table("NL_TC") is False
        assert database.fetch_all('PRAGMA table_xinfo("NL_TC")') == before

    safe = SQLiteDatabase({"path": str(tmp_path / "manager-safe.db")})
    with safe:
        assert SchemaManager(safe).create_table("NL_TC") is True
        assert safe.fetch_one("SELECT COUNT(*) AS n FROM NL_TC") == {"n": 0}


@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
def test_tc_single_record_uses_the_same_fail_closed_validator(
    tmp_path, auto_commit: bool, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=standard)
        assert importer.import_single_record(parsed_tc(), auto_commit=auto_commit)
        invalid = parsed_tc()
        invalid["AtoFun"] = "60"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid, auto_commit=auto_commit)
        expected = 1 if auto_commit else 0
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": expected}


def test_tc_realtime_uses_the_same_fail_closed_validator(tmp_path) -> None:
    realtime = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with realtime:
        for table_name in RealtimeUpdater.DATE_SNAPSHOT_TABLES:
            realtime.execute(SCHEMAS[table_name])
        realtime.commit()
        updater = RealtimeUpdater(realtime)
        inserted = updater.process_parsed_records_batch([parsed_tc()])
        invalid = parsed_tc()
        invalid["HappyoTime"] = "08189999"
        rejected = updater.process_parsed_records_batch([invalid])
        updater.replace_date_snapshot("20260818")
        revised = updater.process_parsed_records_batch(
            [parsed_tc(HappyoTime="08181205", AtoJi="12", AtoFun="20")]
        )
        rows = realtime.fetch_all("SELECT HappyoTime, AtoFun FROM RT_TC")

    assert inserted["success"] is True
    assert rejected["success"] is False
    assert rejected["inserted"] == 0
    assert revised["success"] is True
    assert rows == [{"HappyoTime": "08181205", "AtoFun": "20"}]


def test_tc_header_validator_rejects_missing_blank_and_conflicting_aliases() -> None:
    valid = parsed_tc()
    assert validate_import_record_header(valid) == ("TC", "1")
    for row in (
        {key: value for key, value in valid.items() if key != "DataKubun"},
        {**valid, "DataKubun": ""},
        {**valid, "headDataKubun": "0"},
        {**valid, "headRecordSpec": "CC"},
    ):
        with pytest.raises(SchemaMigrationError):
            validate_import_record_header(row)


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_tc_{uuid4().hex[:12]}"
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


@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_tc_postgresql_all_entrypoints_preserve_provider_revision_order(
    postgresql_db,
    table_name: str,
    standard: bool,
    entrypoint: str,
    auto_commit: bool,
) -> None:
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    first = parsed_tc()
    revised = parsed_tc(HappyoTime="08181205", AtoJi="12", AtoFun="20")
    stats = import_tc_records(
        postgresql_db,
        entrypoint,
        [first, revised],
        standard=standard,
        auto_commit=auto_commit,
    )
    if not auto_commit:
        postgresql_db.commit()
    assert stats["records_imported"] == 2
    assert stats["records_failed"] == 0
    assert postgresql_db.fetch_all(
        f'SELECT HappyoTime AS "HappyoTime", AtoFun AS "AtoFun" FROM {table_name}'
    ) == [{"HappyoTime": "08181205", "AtoFun": "20"}]


@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
@pytest.mark.parametrize(
    "defect",
    [
        "wrong-key",
        "wrong-type",
        "short-text",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
        "deferrable-primary-key",
    ],
)
def test_tc_postgresql_schema_defects_fail_before_mutation(
    postgresql_db, table_name: str, standard: bool, defect: str
) -> None:
    if defect == "deferrable-primary-key":
        schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
        schema = schema.replace(
            "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)",
            "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) "
            "DEFERRABLE INITIALLY DEFERRED",
        )
    else:
        schema = _defective_schema(table_name, defect)
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        DataImporter(postgresql_db, use_jravan_schema=standard).import_records(iter([parsed_tc()]))
    assert postgresql_db.fetch_one(f'SELECT COUNT(*) AS "n" FROM {table_name}') == {"n": 0}


def test_tc_postgresql_realtime_gate(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["RT_TC"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    result = updater.process_parsed_records_batch(
        [parsed_tc(), parsed_tc(HappyoTime="08181205", AtoFun="20")]
    )
    invalid = parsed_tc()
    invalid["AtoFun"] = "60"
    rejected = updater.process_parsed_records_batch([invalid])
    assert result["success"] is True
    assert result["inserted"] == 2
    assert result["errors"] == 0
    assert result["tables"] == ["RT_TC"]
    assert rejected["success"] is False
    assert rejected["inserted"] == 0
    assert postgresql_db.fetch_all(
        'SELECT HappyoTime AS "HappyoTime", AtoFun AS "AtoFun" FROM RT_TC'
    ) == [{"HappyoTime": "08181205", "AtoFun": "20"}]


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
def test_tc_dual_rejects_an_unsafe_target_before_either_database_changes(
    postgresql_db,
    tmp_path,
    unsafe_target: str,
    table_name: str,
    standard: bool,
) -> None:
    safe = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    unsafe = _defective_schema(table_name, "extra-required-column")
    sqlite = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{unsafe_target}.db")})
    with sqlite:
        sqlite.execute(unsafe if unsafe_target == "primary" else safe)
        postgresql_db.execute(unsafe if unsafe_target == "secondary" else safe)
        sqlite.commit()
        postgresql_db.commit()
        primary, secondary = (
            (sqlite, postgresql_db) if unsafe_target == "primary" else (postgresql_db, sqlite)
        )
        with pytest.raises(SchemaMigrationError):
            DataImporter(
                DualDatabase(primary, secondary),
                use_jravan_schema=standard,
            ).import_records(iter([parsed_tc()]))
        assert sqlite.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}
        assert postgresql_db.fetch_one(f'SELECT COUNT(*) AS "n" FROM {table_name}') == {"n": 0}


@pytest.mark.parametrize("table_name,standard", [("NL_TC", False), ("HASSOU_JIKOKU_CHANGE", True)])
def test_tc_dual_preserves_one_provider_revision_on_both_targets(
    postgresql_db, tmp_path, table_name: str, standard: bool
) -> None:
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    sqlite = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-safe-dual.db")})
    with sqlite:
        sqlite.execute(schema)
        postgresql_db.execute(schema)
        sqlite.commit()
        postgresql_db.commit()
        dual = DualDatabase(sqlite, postgresql_db)
        stats = DataImporter(dual, use_jravan_schema=standard).import_records(
            iter([parsed_tc(), parsed_tc(HappyoTime="08181205", AtoFun="20")]),
            auto_commit=False,
        )
        dual.commit()
        assert stats["records_imported"] == 2
        expected = [{"HappyoTime": "08181205", "AtoFun": "20"}]
        assert sqlite.fetch_all(f"SELECT HappyoTime, AtoFun FROM {table_name}") == expected
        assert (
            postgresql_db.fetch_all(
                f'SELECT HappyoTime AS "HappyoTime", AtoFun AS "AtoFun" FROM {table_name}'
            )
            == expected
        )
