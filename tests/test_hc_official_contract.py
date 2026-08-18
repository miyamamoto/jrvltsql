"""HC hill-training contract from the pinned current official sources."""

from __future__ import annotations

import json
import os
from itertools import pairwise
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.hc_parser import HCParser
from src.realtime.updater import RealtimeUpdater

FIELDS = (
    ("RecordSpec", 1, 2, b"HC"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260818"),
    ("TresenKubun", 12, 1, b"0"),
    ("ChokyoDate", 13, 8, b"20260817"),
    ("ChokyoTime", 21, 4, b"0630"),
    ("KettoNum", 25, 10, b"2020100001"),
    ("HaronTime4", 35, 4, b"0480"),
    ("LapTime4", 39, 3, b"120"),
    ("HaronTime3", 42, 4, b"0360"),
    ("LapTime3", 46, 3, b"120"),
    ("HaronTime2", 49, 4, b"0240"),
    ("LapTime2", 53, 3, b"120"),
    ("LapTime1", 56, 3, b"120"),
    ("RecordDelimiter", 59, 2, b"\r\n"),
)
EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
# The physical CRLF is verified before extraction; the legacy BaseParser
# represents its stripped storage field as None.
EXPECTED["RecordDelimiter"] = None
OFFICIAL_KEY = ["TresenKubun", "ChokyoDate", "ChokyoTime", "KettoNum"]
TIME_FIELDS = tuple(
    (name, width) for name, _, width, _ in FIELDS if name.startswith(("HaronTime", "LapTime"))
)
NATIVE_FIELDS = set(EXPECTED)
STANDARD_FIELDS = NATIVE_FIELDS - {"RecordDelimiter"}
CONTRACT_PATH = Path("tests/fixtures/official_layout/hc_contract_4901.json")
MANIFEST_PATH = Path("tests/fixtures/official_layout/jvdata_sdk500_manifest.json")


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


def build_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260818",
    tresen_kubun: str = "0",
    chokyo_date: str = "20260817",
    chokyo_time: str = "0630",
    ketto_num: str = "2020100001",
    field_overrides: dict[str, str] | None = None,
) -> bytes:
    values = {
        "DataKubun": data_kubun,
        "MakeDate": make_date,
        "TresenKubun": tresen_kubun,
        "ChokyoDate": chokyo_date,
        "ChokyoTime": chokyo_time,
        "KettoNum": ketto_num,
    }
    if field_overrides:
        values.update(field_overrides)
    record = bytearray()
    for name, position, width, default in FIELDS:
        value = _pad(values[name], width) if name in values else default
        assert len(record) == position - 1
        assert len(value) == width
        record += value
    assert len(record) == HCParser.RECORD_LENGTH == 60
    return bytes(record)


def parsed_record(**kwargs) -> dict:
    parsed = HCParser().parse(build_record(**kwargs))
    assert parsed is not None
    return parsed


def provider_order_records() -> list[dict]:
    """Keep one survivor for every one-column difference from the delete key."""

    return [
        parsed_record(),
        parsed_record(tresen_kubun="1"),
        parsed_record(chokyo_date="20260816"),
        parsed_record(chokyo_time="0631"),
        parsed_record(ketto_num="2020100002"),
        parsed_record(field_overrides={"HaronTime4": "0510"}),
        parsed_record(
            data_kubun="0",
            field_overrides={"HaronTime4": "BAD!", "LapTime1": "A1B"},
        ),
    ]


EXPECTED_SURVIVORS = [
    {
        "TresenKubun": "0",
        "ChokyoDate": "20260816",
        "ChokyoTime": "0630",
        "KettoNum": "2020100001",
        "HaronTime4": 48.0,
        "LapTime1": 12.0,
    },
    {
        "TresenKubun": "0",
        "ChokyoDate": "20260817",
        "ChokyoTime": "0630",
        "KettoNum": "2020100002",
        "HaronTime4": 48.0,
        "LapTime1": 12.0,
    },
    {
        "TresenKubun": "0",
        "ChokyoDate": "20260817",
        "ChokyoTime": "0631",
        "KettoNum": "2020100001",
        "HaronTime4": 48.0,
        "LapTime1": 12.0,
    },
    {
        "TresenKubun": "1",
        "ChokyoDate": "20260817",
        "ChokyoTime": "0630",
        "KettoNum": "2020100001",
        "HaronTime4": 48.0,
        "LapTime1": 12.0,
    },
]


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
    schema_name = f"jlt_hc_{uuid4().hex[:12]}"
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


def test_hc_reviewed_oracle_binds_both_workbooks_sdk_and_every_parser_span() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["record_length"] == 60
    assert contract["format_sources"] == [
        {
            "artifact": "JV-Data4802.xlsx",
            "sha256": "6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7",
            "sheet": "フォーマット",
            "rows": "1142-1167",
        },
        {
            "artifact": "JV-Data4901.xlsx",
            "sha256": "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234",
            "sheet": "フォーマット",
            "rows": "1142-1167",
        },
    ]
    fixture_spans = [(name, position, width) for name, position, width, _ in FIELDS]
    assert contract["fields"] == [list(item) for item in fixture_spans]
    assert contract["primary_key"] == OFFICIAL_KEY
    assert contract["current_data_kubun"] == ["0", "1"]
    assert contract["measurement_fields"] == {
        name: {
            "width": width,
            "scale_seconds": 0.1,
            "failure_value": "0" * width,
        }
        for name, width in TIME_FIELDS
    }
    assert contract["history"] == {
        "physical_layout_changed": False,
        "data_available_from": "2003",
        "miho_measurement": {
            "through_2004_11_29": "600m",
            "from_2004_11_30": "800m",
        },
        "sources": [
            "JV-Data4901.xlsx:特記事項:195-198",
            "JV-Data4901.xlsx:変更履歴:170,174,344",
        ],
    }
    assert contract["delivery"] == {
        "frequency": "daily_irregular",
        "unit": "complete_training_center_day",
        "retention": "1 year",
        "source": "JV-Data4901.xlsx:データ提供タイミング・提供単位:26",
    }
    assert all(
        position + width == next_position
        for (_, position, width), (_, next_position, _) in pairwise(fixture_spans)
    )

    parser = HCParser()
    assert [
        (field.name, field.start + 1, field.length) for field in parser._fields
    ] == fixture_spans
    assert parser.parse(build_record()) == EXPECTED

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["root_records"]["HC"] == {"struct": "JV_HC_HANRO", "length": 60}
    structures = manifest["structures"]
    sdk_spans = []
    for field in structures["JV_HC_HANRO"]["fields"]:
        if field["name"] == "head":
            for header in structures[field["struct"]]["fields"]:
                sdk_spans.append(
                    (header["name"], field["start"] + header["start"] - 1, header["width"])
                )
        else:
            sdk_spans.append(
                (
                    "RecordDelimiter" if field["name"] == "crlf" else field["name"],
                    field["start"],
                    field["width"],
                )
            )
    assert sdk_spans == fixture_spans


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"make_date": "20260230"}, "MakeDate"),
        ({"tresen_kubun": "2"}, "TresenKubun"),
        ({"chokyo_date": "20260230"}, "ChokyoDate"),
        ({"chokyo_time": "1160"}, "ChokyoTime"),
        ({"ketto_num": "20201A0001"}, "KettoNum"),
        ({"field_overrides": {"HaronTime4": "ABCD"}}, "HaronTime4"),
        ({"field_overrides": {"HaronTime4": ""}}, "HaronTime4-blank"),
        ({"field_overrides": {"LapTime1": "1A0"}}, "LapTime1"),
    ],
)
def test_hc_parser_rejects_malformed_key_and_live_payload(kwargs, field_name: str) -> None:
    assert HCParser().parse(build_record(**kwargs)) is None, field_name


def test_hc_parser_keeps_documented_zero_measurements_and_delete_body_opaque() -> None:
    zero = parsed_record(field_overrides={name: "0" * width for name, width in TIME_FIELDS})
    assert all(zero[name] == "0" * width for name, width in TIME_FIELDS)

    opaque = bytearray(build_record(data_kubun="0"))
    opaque[34:36] = b"\x81 "  # deliberately invalid CP932 inside the unused body
    deleted = HCParser().parse(bytes(opaque))
    assert deleted is not None
    assert deleted["DataKubun"] == "0"
    assert [deleted[name] for name in OFFICIAL_KEY] == [
        "0",
        "20260817",
        "0630",
        "2020100001",
    ]
    assert all(deleted[name] == "" for name, _ in TIME_FIELDS)


def test_hc_native_and_standard_schemas_are_executable_official_contracts() -> None:
    assert set(get_table_column_types("NL_HC")) == NATIVE_FIELDS
    assert set(get_table_column_types("HANRO")) == STANDARD_FIELDS
    assert get_table_primary_key_columns("NL_HC") == OFFICIAL_KEY
    assert get_table_primary_key_columns("HANRO") == OFFICIAL_KEY
    for table_name in ("NL_HC", "HANRO"):
        nullability = get_table_column_nullability(table_name)
        required = set(get_table_column_types(table_name)) - {"RecordDelimiter"}
        assert all(not nullability[column] for column in required)
    metadata = TABLE_METADATA["NL_HC"]
    assert [(column["name"], column["type"]) for column in metadata["columns"]] == list(
        get_table_column_types("NL_HC").items()
    )
    assert metadata["primary_key"] == OFFICIAL_KEY


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard", "auto_commit"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            auto_commit,
            id=f"{importer_class.__name__}-{table_name}-{auto_commit}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_HC", False), ("HANRO", True))
        for auto_commit in (True, False)
    ],
)
def test_hc_provider_order_update_exact_delete_and_durable_units(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"ordered-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, use_jravan_schema=standard)
        stats = importer.import_records(iter(provider_order_records()), auto_commit=auto_commit)
        assert {
            key: stats[key] for key in ("records_imported", "records_failed", "batches_processed")
        } == {"records_imported": 7, "records_failed": 0, "batches_processed": 2}
        rows = database.fetch_all(
            "SELECT TresenKubun, ChokyoDate, ChokyoTime, KettoNum, "
            f"HaronTime4, LapTime1 FROM {table_name} "
            "ORDER BY TresenKubun, ChokyoDate, ChokyoTime, KettoNum"
        )
        assert rows == EXPECTED_SURVIVORS
        if not auto_commit:
            database.commit()


@pytest.mark.parametrize("table_name,standard", [("NL_HC", False), ("HANRO", True)])
def test_hc_caller_validation_precedes_coercion_and_mutation(
    tmp_path, table_name: str, standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    invalid_records = []
    for field_name, invalid in (
        ("MakeDate", "20260230"),
        ("TresenKubun", "2"),
        ("ChokyoDate", "20260230"),
        ("ChokyoTime", "1160"),
        ("KettoNum", "20201A0001"),
        ("HaronTime4", "ABCD"),
        ("LapTime1", "1A0"),
    ):
        record = parsed_record()
        record[field_name] = invalid
        invalid_records.append(record)

    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=standard)
        for invalid in invalid_records:
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([invalid]))
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}


def test_hc_dual_verifies_both_targets_before_mutation(tmp_path) -> None:
    safe_schema = SCHEMAS["NL_HC"]
    unsafe_schema = _defective_schema("NL_HC", "extra-required-column")
    for unsafe_target in ("primary", "secondary"):
        primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
        secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
        with primary, secondary:
            primary.execute(unsafe_schema if unsafe_target == "primary" else safe_schema)
            secondary.execute(unsafe_schema if unsafe_target == "secondary" else safe_schema)
            primary.commit()
            secondary.commit()
            with pytest.raises(SchemaMigrationError):
                DataImporter(DualDatabase(primary, secondary)).import_records(
                    iter([parsed_record()])
                )
            assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_HC") == {"count": 0}
            assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_HC") == {"count": 0}


def _defective_schema(table_name: str, defect: str) -> str:
    schema = SCHEMAS[table_name] if table_name == "NL_HC" else JRAVAN_SCHEMAS[table_name]
    key = "PRIMARY KEY (TresenKubun, ChokyoDate, ChokyoTime, KettoNum)"
    if defect == "wrong-key":
        return schema.replace(key, "PRIMARY KEY (TresenKubun, ChokyoDate, KettoNum)")
    if defect == "extra-unique":
        body, close = schema.rsplit(")", 1)
        return f"{body}, UNIQUE (ChokyoDate)\n        ){close}"
    if defect == "extra-check":
        body, close = schema.rsplit(")", 1)
        return f"{body}, CHECK (HaronTime4 <= 10)\n        ){close}"
    if defect == "extra-foreign-key":
        body, close = schema.rsplit(")", 1)
        return (
            f"{body}, FOREIGN KEY (TresenKubun, ChokyoDate, ChokyoTime, KettoNum) "
            f"REFERENCES {table_name} "
            "(TresenKubun, ChokyoDate, ChokyoTime, KettoNum) ON DELETE CASCADE\n"
            f"        ){close}"
        )
    if defect == "extra-required-column":
        return schema.replace(key, f"ExternalRequired TEXT NOT NULL, {key}")
    if defect == "extra-generated-required-column":
        return schema.replace(
            key,
            "ExternalRequired TEXT GENERATED ALWAYS AS (NULL) "
            f"VIRTUAL NOT NULL, {key}",
        )
    if defect == "wrong-type":
        if table_name == "NL_HC":
            return schema.replace("ChokyoDate TEXT", "ChokyoDate INTEGER")
        return schema.replace(
            "ChokyoDate                     VARCHAR(8) NOT NULL",
            "ChokyoDate                     INTEGER NOT NULL   ",
        )
    if defect == "nullable-key":
        return schema.replace("KettoNum TEXT NOT NULL", "KettoNum TEXT").replace(
            "KettoNum                       VARCHAR(10) NOT NULL",
            "KettoNum                       VARCHAR(10)         ",
        )
    raise AssertionError(defect)


@pytest.mark.parametrize("table_name,standard", [("NL_HC", False), ("HANRO", True)])
@pytest.mark.parametrize(
    "defect",
    [
        "wrong-key",
        "extra-unique",
        "extra-check",
        "extra-foreign-key",
        "extra-required-column",
        "extra-generated-required-column",
        "wrong-type",
        "nullable-key",
    ],
)
def test_hc_schema_defects_fail_before_any_row_mutation(
    tmp_path, table_name: str, standard: bool, defect: str
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{defect}.db")})
    with database:
        database.execute(_defective_schema(table_name, defect))
        database.commit()
        before_schema = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=standard).import_records(
                iter([parsed_record()])
            )
        assert (
            database.fetch_one(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
            )
            == before_schema
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}


@pytest.mark.parametrize("table_name,standard", [("NL_HC", False), ("HANRO", True)])
@pytest.mark.parametrize("auto_commit", [True, False])
def test_hc_single_record_uses_the_same_validator_and_exact_delete(
    tmp_path, table_name: str, standard: bool, auto_commit: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=standard)
        assert importer.import_single_record(parsed_record(), auto_commit=auto_commit)
        invalid = parsed_record()
        invalid["ChokyoTime"] = "1160"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid, auto_commit=auto_commit)
        delete = parsed_record(data_kubun="0")
        delete["HaronTime4"] = "not interpreted"
        assert importer.import_single_record(delete, auto_commit=auto_commit)
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 0}


def test_hc_accumulated_only_raw_does_not_write_realtime_cache_or_table(tmp_path) -> None:
    class CacheProbe:
        def __init__(self) -> None:
            self.calls = 0

        def write_rt_record(self, *_args) -> None:
            self.calls += 1

    cache = CacheProbe()
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-hc.db")})
    with database:
        updater = RealtimeUpdater(database, cache_manager=cache)
        assert updater.process_record(build_record()) is None
        assert cache.calls == 0
        assert not database.table_exists("RT_HC")


def test_hc_postgresql_provider_order_and_wrong_key_gate(postgresql_db) -> None:
    for table_name, standard in (("NL_HC", False), ("HANRO", True)):
        schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
        postgresql_db.execute(schema)
        postgresql_db.commit()
        for importer_class in (DataImporter, OptimizedDataImporter):
            for auto_commit in (True, False):
                stats = importer_class(postgresql_db, use_jravan_schema=standard).import_records(
                    iter(provider_order_records()),
                    auto_commit=auto_commit,
                )
                assert stats["records_imported"] == 7
                assert (
                    postgresql_db.fetch_all(
                        'SELECT TresenKubun AS "TresenKubun", '
                        'ChokyoDate AS "ChokyoDate", ChokyoTime AS "ChokyoTime", '
                        'KettoNum AS "KettoNum", HaronTime4 AS "HaronTime4", '
                        'LapTime1 AS "LapTime1" '
                        f"FROM {table_name} "
                        "ORDER BY TresenKubun, ChokyoDate, ChokyoTime, KettoNum"
                    )
                    == EXPECTED_SURVIVORS
                )
                postgresql_db.execute(f"DELETE FROM {table_name}")
                postgresql_db.commit()
        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.commit()

        # PostgreSQL marks primary-key attributes NOT NULL in its catalog even
        # when the DDL omits the redundant spelling; SQLite requires the
        # explicit nullable-key negative exercised above.
        for defect in (
            "wrong-key",
            "extra-unique",
            "extra-check",
            "extra-foreign-key",
            "extra-required-column",
            "wrong-type",
        ):
            postgresql_db.execute(_defective_schema(table_name, defect))
            postgresql_db.commit()
            before_schema = postgresql_db.fetch_all(
                "SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type, "
                "a.attnotnull AS not_null FROM pg_attribute a "
                "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 "
                "AND NOT a.attisdropped ORDER BY a.attnum",
                (table_name.lower(),),
            )
            with pytest.raises(SchemaMigrationError):
                DataImporter(postgresql_db, use_jravan_schema=standard).import_records(
                    iter([parsed_record()])
                )
            assert (
                postgresql_db.fetch_all(
                    "SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type, "
                    "a.attnotnull AS not_null FROM pg_attribute a "
                    "WHERE a.attrelid = to_regclass(?) AND a.attnum > 0 "
                    "AND NOT a.attisdropped ORDER BY a.attnum",
                    (table_name.lower(),),
                )
                == before_schema
            )
            assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 0
            }
            postgresql_db.rollback()
            postgresql_db.execute(f"DROP TABLE {table_name}")
            postgresql_db.commit()


def test_hc_postgresql_dual_rejects_extra_required_column_on_either_target(
    postgresql_db, tmp_path
) -> None:
    for table_name, standard in (("NL_HC", False), ("HANRO", True)):
        safe_schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
        unsafe_schema = _defective_schema(table_name, "extra-required-column")
        for unsafe_target in ("primary", "secondary"):
            sqlite = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-{unsafe_target}.db")})
            with sqlite:
                sqlite.execute(unsafe_schema if unsafe_target == "primary" else safe_schema)
                postgresql_db.execute(
                    unsafe_schema if unsafe_target == "secondary" else safe_schema
                )
                sqlite.commit()
                postgresql_db.commit()

                with pytest.raises(SchemaMigrationError):
                    DataImporter(
                        DualDatabase(sqlite, postgresql_db),
                        use_jravan_schema=standard,
                    ).import_records(iter([parsed_record()]))

                assert sqlite.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                    "count": 0
                }
                assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                    "count": 0
                }
                postgresql_db.rollback()
                postgresql_db.execute(f"DROP TABLE {table_name}")
                postgresql_db.commit()

        sqlite = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-generated.db")})
        with sqlite:
            sqlite.execute(_defective_schema(table_name, "extra-generated-required-column"))
            postgresql_db.execute(safe_schema)
            sqlite.commit()
            postgresql_db.commit()
            dual = DualDatabase(postgresql_db, sqlite)
            importer = DataImporter(dual, use_jravan_schema=standard)

            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([parsed_record()]))

            assert importer.get_statistics()["records_imported"] == 0
            assert dual.secondary_in_sync is True
            assert sqlite.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 0
            }
            assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 0
            }
            postgresql_db.rollback()
            postgresql_db.execute(f"DROP TABLE {table_name}")
            postgresql_db.commit()
