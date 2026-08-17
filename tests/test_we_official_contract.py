"""Official WE weather/track announcement contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.setup_pg_test_db import postgresql_test_config
from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    validate_import_record_header,
    verify_we_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.we_parser import WEParser
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
OFFICIAL_MANIFEST = json.loads(
    (FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
)
WE_CONTRACT = json.loads((FIXTURES / "we_contract_4901.json").read_text(encoding="utf-8"))
WE_KEY = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "HappyoTime",
    "HenkoID",
)


def build_we_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260818",
    year: str = "2026",
    month_day: str = "0818",
    jyo_cd: str = "05",
    kaiji: str = "03",
    nichiji: str = "08",
    happyo_time: str = "08180930",
    body: str = "1111000",
) -> bytes:
    """Build one exact-width WE record from independently pinned spans."""

    record = bytearray(b" " * WEParser.RECORD_LENGTH)
    record[0:2] = b"WE"
    record[2:3] = data_kubun.encode("ascii")
    record[3:11] = make_date.encode("ascii")
    record[11:15] = year.encode("ascii")
    record[15:19] = month_day.encode("ascii")
    record[19:21] = jyo_cd.encode("ascii")
    record[21:23] = kaiji.encode("ascii")
    record[23:25] = nichiji.encode("ascii")
    record[25:33] = happyo_time.encode("ascii")
    record[33:40] = body.encode("ascii")
    record[-2:] = b"\r\n"
    return bytes(record)


def parsed_we(**overrides) -> dict:
    parsed = WEParser().parse(build_we_record(**overrides))
    assert parsed is not None
    return parsed


def import_records(database, entrypoint, records, *, standard, auto_commit):
    if entrypoint == "data-batch":
        result = DataImporter(database, batch_size=1, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
        assert result["records_imported"] == len(records)
        assert result["records_failed"] == 0
    elif entrypoint == "optimized-batch":
        result = OptimizedDataImporter(
            database, batch_size=1, use_jravan_schema=standard
        ).import_records(iter(records), auto_commit=auto_commit)
        assert result["records_imported"] == len(records)
        assert result["records_failed"] == 0
    else:
        importer = DataImporter(database, use_jravan_schema=standard)
        assert all(
            importer.import_single_record(record, auto_commit=auto_commit) for record in records
        )
    if not auto_commit:
        database.commit()


def test_we_layout_and_all_storage_keys_match_the_pinned_official_sources() -> None:
    assert WE_CONTRACT["format_sources"] == [
        {
            "artifact": "JV-Data4802.xlsx",
            "sha256": "6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7",
            "sheet": "フォーマット",
            "rows": "1435-1458",
        },
        {
            "artifact": "JV-Data4901.xlsx",
            "sha256": "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234",
            "sheet": "フォーマット",
            "rows": "1435-1458",
        },
    ]
    assert WE_CONTRACT["record_length"] == 42
    assert tuple(WE_CONTRACT["primary_key"]) == WE_KEY
    assert [(field.name, field.start + 1, field.length) for field in WEParser()._fields] == [
        tuple(field) for field in WE_CONTRACT["fields"]
    ]
    assert OFFICIAL_MANIFEST["root_records"]["WE"] == {
        "struct": "JV_WE_WEATHER",
        "length": 42,
    }
    for table_name in ("NL_WE", "RT_WE", "TENKO_BABA"):
        assert tuple(get_table_primary_key_columns(table_name)) == WE_KEY
        nullability = get_table_column_nullability(table_name)
        assert all(nullability[column] is False for column in WE_KEY)


@pytest.mark.parametrize(
    ("happyo_time", "body"),
    (
        ("00000000", "1111000"),
        ("02290930", "2300200"),
        ("08181000", "3011022"),
    ),
    ids=("initial-sentinel", "weather-change", "track-change"),
)
def test_we_parser_accepts_the_paired_official_positive_shapes(happyo_time: str, body: str) -> None:
    parsed = parsed_we(year="2024", month_day="0229", happyo_time=happyo_time, body=body)
    assert parsed["HappyoTime"] == happyo_time
    assert parsed["HenkoID"] == body[0]


@pytest.mark.parametrize(
    "overrides",
    (
        {"make_date": "20260230"},
        {"month_day": "0230"},
        {"jyo_cd": "ZZ"},
        {"kaiji": "A3"},
        {"happyo_time": "99999999"},
        {"body": "9111000"},
        {"body": "1911000"},
        {"body": "1151000"},
        {"body": "2311200"},
        {"body": "3111022"},
    ),
)
def test_we_parser_rejects_malformed_key_and_body_fields(overrides: dict) -> None:
    with pytest.raises(ValueError):
        WEParser().parse(build_we_record(**overrides))


@pytest.mark.parametrize(
    "changes",
    (
        {"HappyoTime": "99999999"},
        {"HenkoID": "9"},
        {"AtoTenkoCD": "2"},
    ),
)
def test_we_caller_validation_rejects_malformed_and_conflicting_values(
    changes: dict,
) -> None:
    record = parsed_we()
    record.update(changes)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)

    assert validate_import_record_header(parsed_we()) == ("WE", "1")
    canonical = parsed_we()
    for native_name, canonical_name in (
        ("TenkoState", "AtoTenkoCD"),
        ("SibaBabaState", "AtoSibaBabaCD"),
        ("DirtBabaState", "AtoDirtBabaCD"),
        ("TenkoState2", "MaeTenkoCD"),
        ("SibaBabaState2", "MaeSibaBabaCD"),
        ("DirtBabaState2", "MaeDirtBabaCD"),
    ):
        canonical[canonical_name] = canonical.pop(native_name)
    assert validate_import_record_header(canonical) == ("WE", "1")


def test_we_historical_status_boundary_is_explicit() -> None:
    assert parsed_we(data_kubun="0", make_date="20030710", body="1999999")
    with pytest.raises(ValueError):
        WEParser().parse(build_we_record(data_kubun="0", make_date="20030711", body="1999999"))


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_we_storage_keeps_distinct_times_and_exact_reimport_is_idempotent(
    tmp_path, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "TENKO_BABA" if standard else "NL_WE"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{entrypoint}-{auto_commit}.db")})
    with database:
        database.execute(schema)
        database.commit()
        first = parsed_we(happyo_time="08180930", body="1111000")
        second = parsed_we(happyo_time="08181000", body="2300200")
        revision = dict(first)
        revision["DataKubun"] = "1"
        revision["TenkoState"] = "2"
        import_records(
            database,
            entrypoint,
            [first, second, revision],
            standard=standard,
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(
            f'SELECT HappyoTime, {"AtoTenkoCD" if standard else "TenkoState"} AS Tenko '
            f"FROM {table_name} ORDER BY HappyoTime"
        )

    assert rows == [
        {"HappyoTime": "08180930", "Tenko": "2"},
        {"HappyoTime": "08181000", "Tenko": "3"},
    ]


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_we_historical_status_zero_exactly_erases_one_official_key(
    tmp_path, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "TENKO_BABA" if standard else "NL_WE"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"erase-{standard}-{entrypoint}-{auto_commit}.db")}
    )
    with database:
        database.execute(schema)
        database.commit()
        first = parsed_we(make_date="20030710", happyo_time="07090930", body="1111000")
        second = parsed_we(make_date="20030710", happyo_time="07091000", body="2300200")
        delete = parsed_we(
            data_kubun="0",
            make_date="20030710",
            happyo_time="07090930",
            body="1999999",
        )
        delete["AtoTenkoCD"] = "0"
        import_records(
            database,
            entrypoint,
            [first, second, delete],
            standard=standard,
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(
            f"SELECT HappyoTime, DataKubun FROM {table_name} ORDER BY HappyoTime"
        )

    assert rows == [{"HappyoTime": "07091000", "DataKubun": "1"}]


def test_realtime_we_uses_happyo_time_for_targeted_historical_erase(tmp_path) -> None:
    corrected_schema = SCHEMAS["RT_WE"].replace(
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, HenkoID)",
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, HappyoTime, HenkoID)",
    )
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(corrected_schema)
        database.commit()
        updater = RealtimeUpdater(database)
        inserted = updater.process_parsed_records_batch(
            [
                parsed_we(make_date="20030710", happyo_time="07090930"),
                parsed_we(make_date="20030710", happyo_time="07091000"),
            ]
        )
        erased = updater.process_parsed_records_batch(
            [
                parsed_we(
                    data_kubun="0",
                    make_date="20030710",
                    happyo_time="07090930",
                    body="1999999",
                )
            ]
        )
        rows = database.fetch_all("SELECT HappyoTime FROM RT_WE")

    assert inserted["success"] is True
    assert erased["success"] is True
    assert rows == [{"HappyoTime": "07091000"}]


@pytest.mark.parametrize("defect", ("legacy-key", "nullable-key", "wrong-key-type", "extra-unique"))
def test_we_unsafe_schema_is_rejected_before_mutation(tmp_path, defect: str) -> None:
    schema = SCHEMAS["NL_WE"]
    if defect == "legacy-key":
        schema = schema.replace(", HappyoTime, HenkoID)", ", HenkoID)", 1)
    elif defect == "nullable-key":
        schema = schema.replace("HappyoTime TEXT NOT NULL", "HappyoTime TEXT", 1)
    elif defect == "wrong-key-type":
        schema = schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL", 1)
    else:
        schema = schema.replace("PRIMARY KEY (", "UNIQUE (HenkoID),\n            PRIMARY KEY (", 1)
    database = SQLiteDatabase({"path": str(tmp_path / "unsafe.db")})
    with database:
        database.execute(schema)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([parsed_we()]))
        assert database.fetch_one("SELECT COUNT(*) AS n FROM NL_WE") == {"n": 0}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_first_we_rejection_stops_standard_migration(tmp_path, importer_class) -> None:
    race_schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    database = SQLiteDatabase({"path": str(tmp_path / "first-rejection.db")})
    with database:
        database.execute(race_schema)
        database.execute(JRAVAN_SCHEMAS["TENKO_BABA"])
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        invalid = parsed_we()
        invalid["HappyoTime"] = "99999999"
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=True).import_records(iter([invalid]))
        after = database.fetch_all('PRAGMA table_info("RACE")')
    assert after == before


def test_realtime_we_rejects_caller_malformed_row_before_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-invalid.db")})
    with database:
        database.execute(SCHEMAS["RT_WE"])
        database.commit()
        invalid = parsed_we()
        invalid["HenkoID"] = "9"
        result = RealtimeUpdater(database).process_parsed_records_batch([invalid])
        assert result["success"] is False
        assert result["inserted"] == 0
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WE") == {"n": 0}


def test_we_executable_metadata_exposes_the_complete_identity() -> None:
    for table_name in ("NL_WE", "RT_WE"):
        metadata = TABLE_METADATA[table_name]
        assert tuple(metadata["primary_key"]) == WE_KEY
        assert {column["name"] for column in metadata["columns"]} == {
            field.name for field in WEParser()._fields
        }


def test_unsafe_standard_we_stops_before_unrelated_additive_migration(tmp_path) -> None:
    race_schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    unsafe_we = JRAVAN_SCHEMAS["TENKO_BABA"].replace(
        "PRIMARY KEY (", "UNIQUE (HenkoID),\n            PRIMARY KEY (", 1
    )
    database = SQLiteDatabase({"path": str(tmp_path / "standard-preflight.db")})
    with database:
        database.execute(race_schema)
        database.execute(unsafe_we)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=True).import_records(iter([]))
        after = database.fetch_all('PRAGMA table_info("RACE")')
    assert after == before


def test_schema_manager_rejects_legacy_we_before_unrelated_native_migration(
    tmp_path,
) -> None:
    legacy_we = SCHEMAS["NL_WE"].replace(", HappyoTime, HenkoID)", ", HenkoID)", 1)
    incomplete_ra = SCHEMAS["NL_RA"].replace("            Crlf TEXT,\n", "", 1)
    database = SQLiteDatabase({"path": str(tmp_path / "native-preflight.db")})
    with database:
        database.execute(legacy_we)
        database.execute(incomplete_ra)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("NL_RA")')
        assert SchemaManager(database).create_table("NL_RA") is False
        after = database.fetch_all('PRAGMA table_info("NL_RA")')
    assert after == before


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
def test_we_dual_verifies_every_target_before_mutation(tmp_path, unsafe_target: str) -> None:
    safe_schema = SCHEMAS["NL_WE"]
    unsafe_schema = safe_schema.replace(
        "PRIMARY KEY (", "UNIQUE (HenkoID),\n            PRIMARY KEY (", 1
    )
    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    with primary, secondary:
        primary.execute(unsafe_schema if unsafe_target == "primary" else safe_schema)
        secondary.execute(unsafe_schema if unsafe_target == "secondary" else safe_schema)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_we()]))
        assert primary.fetch_one("SELECT COUNT(*) AS n FROM NL_WE") == {"n": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS n FROM NL_WE") == {"n": 0}


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_we_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.rollback()
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_we_postgresql_identity_update_and_historical_exact_erase(
    postgresql_db, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "TENKO_BABA" if standard else "NL_WE"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    first = parsed_we(make_date="20030710", happyo_time="07090930", body="1111000")
    second = parsed_we(make_date="20030710", happyo_time="07091000", body="2300200")
    revision = dict(first)
    revision["TenkoState"] = "2"
    import_records(
        postgresql_db,
        entrypoint,
        [first, second, revision],
        standard=standard,
        auto_commit=auto_commit,
    )
    assert postgresql_db.fetch_all(
        f'SELECT happyotime AS "HappyoTime" FROM {table_name} ORDER BY happyotime'
    ) == [{"HappyoTime": "07090930"}, {"HappyoTime": "07091000"}]

    delete = parsed_we(
        data_kubun="0",
        make_date="20030710",
        happyo_time="07090930",
        body="1999999",
    )
    import_records(
        postgresql_db,
        entrypoint,
        [delete],
        standard=standard,
        auto_commit=auto_commit,
    )
    assert postgresql_db.fetch_all(f'SELECT happyotime AS "HappyoTime" FROM {table_name}') == [
        {"HappyoTime": "07091000"}
    ]


@pytest.mark.parametrize("defect", ("wrong-key-type", "extra-unique", "deferrable-pk"))
def test_we_postgresql_rejects_unsafe_identity_schema(postgresql_db, defect: str) -> None:
    schema = SCHEMAS["NL_WE"]
    if defect == "wrong-key-type":
        schema = schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL", 1)
    elif defect == "extra-unique":
        schema = schema.replace("PRIMARY KEY (", "UNIQUE (HenkoID),\n            PRIMARY KEY (", 1)
    else:
        schema = schema.replace(
            "HappyoTime, HenkoID)",
            "HappyoTime, HenkoID) DEFERRABLE INITIALLY DEFERRED",
            1,
        )
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_we_storage_schema(postgresql_db, "NL_WE")


def test_we_postgresql_realtime_preserves_times_and_erases_one_key(
    postgresql_db,
) -> None:
    postgresql_db.execute(SCHEMAS["RT_WE"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    inserted = updater.process_parsed_records_batch(
        [
            parsed_we(make_date="20030710", happyo_time="07090930"),
            parsed_we(make_date="20030710", happyo_time="07091000"),
        ]
    )
    erased = updater.process_parsed_records_batch(
        [
            parsed_we(
                data_kubun="0",
                make_date="20030710",
                happyo_time="07090930",
                body="1999999",
            )
        ]
    )
    assert inserted["success"] is True
    assert inserted["inserted"] == 2
    assert erased["success"] is True
    assert postgresql_db.fetch_all('SELECT happyotime AS "HappyoTime" FROM RT_WE') == [
        {"HappyoTime": "07091000"}
    ]
