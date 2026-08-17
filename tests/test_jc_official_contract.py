"""Official JC jockey-change announcement contracts."""

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
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    validate_import_record_header,
    verify_jc_storage_schema,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.jc_parser import JCParser
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
OFFICIAL_MANIFEST = json.loads(
    (FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
)
JC_CONTRACT = json.loads((FIXTURES / "jc_contract_4901.json").read_text(encoding="utf-8"))
JC_KEY = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "HappyoTime",
    "Umaban",
)

JC_SDK_FIELD_NAMES = {
    ("head", "RecordSpec"): "RecordSpec",
    ("head", "DataKubun"): "DataKubun",
    ("head", "MakeDate"): "MakeDate",
    ("id", "Year"): "Year",
    ("id", "MonthDay"): "MonthDay",
    ("id", "JyoCD"): "JyoCD",
    ("id", "Kaiji"): "Kaiji",
    ("id", "Nichiji"): "Nichiji",
    ("id", "RaceNum"): "RaceNum",
    ("HappyoTime",): "HappyoTime",
    ("Umaban",): "Umaban",
    ("Bamei",): "Bamei",
    ("JCInfoAfter", "Futan"): "AtoFutan",
    ("JCInfoAfter", "KisyuCode"): "AtoKisyuCode",
    ("JCInfoAfter", "KisyuName"): "AtoKisyuName",
    ("JCInfoAfter", "MinaraiCD"): "AtoMinaraiCD",
    ("JCInfoBefore", "Futan"): "MaeFutan",
    ("JCInfoBefore", "KisyuCode"): "MaeKisyuCode",
    ("JCInfoBefore", "KisyuName"): "MaeKisyuName",
    ("JCInfoBefore", "MinaraiCD"): "MaeMinaraiCD",
    ("crlf",): "RecordDelimiter",
}


def _put(record: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    record[start : start + width] = encoded.ljust(width, b" ")


def build_jc_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260818",
    year: str = "2026",
    month_day: str = "0818",
    jyo_cd: str = "05",
    kaiji: str = "03",
    nichiji: str = "08",
    race_num: str = "11",
    happyo_time: str = "08180930",
    umaban: str = "01",
    bamei: str = "テストホース",
    ato_futan: str = "550",
    ato_kisyu_code: str = "01234",
    ato_kisyu_name: str = "新騎手",
    ato_minarai: str = "0",
    mae_futan: str = "560",
    mae_kisyu_code: str = "05678",
    mae_kisyu_name: str = "旧騎手",
    mae_minarai: str = "9",
) -> bytes:
    record = bytearray(b" " * JCParser.RECORD_LENGTH)
    values = (
        (0, 2, "JC"),
        (2, 1, data_kubun),
        (3, 8, make_date),
        (11, 4, year),
        (15, 4, month_day),
        (19, 2, jyo_cd),
        (21, 2, kaiji),
        (23, 2, nichiji),
        (25, 2, race_num),
        (27, 8, happyo_time),
        (35, 2, umaban),
        (37, 36, bamei),
        (73, 3, ato_futan),
        (76, 5, ato_kisyu_code),
        (81, 34, ato_kisyu_name),
        (115, 1, ato_minarai),
        (116, 3, mae_futan),
        (119, 5, mae_kisyu_code),
        (124, 34, mae_kisyu_name),
        (158, 1, mae_minarai),
    )
    for start, width, value in values:
        _put(record, start, width, value)
    record[-2:] = b"\r\n"
    return bytes(record)


def parsed_jc(**overrides) -> dict:
    parsed = JCParser().parse(build_jc_record(**overrides))
    assert parsed is not None
    return parsed


def sdk_jc_parser_contract() -> list[tuple[str, int, int]]:
    structures = OFFICIAL_MANIFEST["structures"]
    contract: list[tuple[str, int, int]] = []

    def visit(structure_name: str, start: int, path: tuple[str, ...]) -> None:
        for field in structures[structure_name]["fields"]:
            field_start = start + field["start"] - 1
            field_path = (*path, field["name"])
            parser_name = JC_SDK_FIELD_NAMES.get(field_path)
            if parser_name is not None:
                contract.append((parser_name, field_start, field["width"]))
            elif field["kind"] == "nested":
                visit(field["struct"], field_start, field_path)
            else:
                raise AssertionError(f"unmapped JC SDK scalar: {field_path}")

    visit("JV_JC_INFO", 1, ())
    return contract


def import_records(database, entrypoint, records, *, standard, auto_commit, batch_size=1000):
    if entrypoint == "data-batch":
        result = DataImporter(
            database, batch_size=batch_size, use_jravan_schema=standard
        ).import_records(iter(records), auto_commit=auto_commit)
        assert result["records_imported"] == len(records)
        assert result["records_failed"] == 0
    elif entrypoint == "optimized-batch":
        result = OptimizedDataImporter(
            database, batch_size=batch_size, use_jravan_schema=standard
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


def test_jc_layout_and_storage_keys_match_the_pinned_official_sources() -> None:
    assert JC_CONTRACT["record_length"] == 161
    assert tuple(JC_CONTRACT["primary_key"]) == JC_KEY
    parser_contract = [(field.name, field.start + 1, field.length) for field in JCParser()._fields]
    assert parser_contract == [tuple(field) for field in JC_CONTRACT["fields"]]
    assert parser_contract == sdk_jc_parser_contract()
    assert OFFICIAL_MANIFEST["root_records"]["JC"] == {
        "struct": "JV_JC_INFO",
        "length": 161,
    }
    for table_name in ("NL_JC", "RT_JC", "KISYU_CHANGE"):
        assert tuple(get_table_primary_key_columns(table_name)) == JC_KEY
        nullability = get_table_column_nullability(table_name)
        assert all(nullability[column] is False for column in JC_KEY)


@pytest.mark.parametrize(
    "overrides",
    (
        {"make_date": "20260230"},
        {"month_day": "0230"},
        {"jyo_cd": "ZZ"},
        {"happyo_time": "99999999"},
        {"umaban": "19"},
        {"ato_futan": "5A0"},
        {"ato_kisyu_code": "12X34"},
        {"ato_minarai": "8"},
    ),
)
def test_jc_parser_and_caller_reject_invalid_fields_before_mutation(overrides: dict) -> None:
    with pytest.raises(ValueError):
        JCParser().parse(build_jc_record(**overrides))

    valid = parsed_jc()
    valid.update(
        {
            {
                "make_date": "MakeDate",
                "month_day": "MonthDay",
                "jyo_cd": "JyoCD",
                "happyo_time": "HappyoTime",
                "umaban": "Umaban",
                "ato_futan": "AtoFutan",
                "ato_kisyu_code": "AtoKisyuCode",
                "ato_minarai": "AtoMinaraiCD",
            }[next(iter(overrides))]: next(iter(overrides.values()))
        }
    )
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(valid)

    assert validate_import_record_header(parsed_jc()) == ("JC", "1")


def test_jc_historical_status_boundary_and_opaque_body() -> None:
    assert parsed_jc(
        data_kubun="0",
        make_date="20030710",
        ato_futan="ABC",
        ato_kisyu_code="ABCDE",
        ato_minarai="8",
    )
    with pytest.raises(ValueError):
        JCParser().parse(build_jc_record(data_kubun="0", make_date="20030711"))


def test_jc_accepts_official_initial_time_and_undecided_rider_shape() -> None:
    record = parsed_jc(
        happyo_time="00000000",
        ato_kisyu_code="00000",
        ato_kisyu_name="未定",
        ato_minarai="0",
    )
    assert validate_import_record_header(record) == ("JC", "1")


@pytest.mark.parametrize(
    "changes",
    (
        {"Bamei": "😀"},
        {"AtoKisyuName": "あ" * 18},
        {"MaeKisyuName": 123},
    ),
)
def test_jc_caller_text_must_fit_the_official_cp932_span(changes: dict) -> None:
    record = parsed_jc()
    record.update(changes)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_jc_storage_preserves_times_revises_and_exactly_erases(
    tmp_path, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "KISYU_CHANGE" if standard else "NL_JC"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{entrypoint}-{auto_commit}.db")})
    with database:
        database.execute(schema)
        database.commit()
        first = parsed_jc(make_date="20030710", happyo_time="07090630")
        second = parsed_jc(
            make_date="20030710",
            happyo_time="07090710",
            ato_kisyu_code="09999",
        )
        revision = dict(first)
        revision["AtoKisyuCode"] = "08888"
        delete = parsed_jc(
            data_kubun="0",
            make_date="20030710",
            happyo_time="07090630",
            ato_futan="ABC",
            ato_kisyu_code="ABCDE",
            ato_minarai="8",
        )
        import_records(
            database,
            entrypoint,
            [first, second, revision, delete],
            standard=standard,
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(
            f"SELECT HappyoTime, DataKubun FROM {table_name} ORDER BY HappyoTime"
        )

    assert rows == [{"HappyoTime": "07090710", "DataKubun": "1"}]


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_jc_weight_unit_is_kg_only_in_real_storage(tmp_path, standard: bool) -> None:
    table_name = "KISYU_CHANGE" if standard else "NL_JC"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"weight-{standard}.db")})
    with database:
        database.execute(schema)
        database.commit()
        import_records(database, "data-batch", [parsed_jc()], standard=standard, auto_commit=True)
        row = database.fetch_one(f"SELECT AtoFutan, MaeFutan FROM {table_name}")
    assert row == (
        {"AtoFutan": "550", "MaeFutan": "560"} if standard else {"AtoFutan": 55.0, "MaeFutan": 56.0}
    )


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize(
    "defect", ("legacy-key", "nullable-key", "wrong-type", "short-text", "extra-unique")
)
def test_unsafe_jc_schema_is_rejected_before_mutation(
    tmp_path, standard: bool, defect: str
) -> None:
    table_name = "KISYU_CHANGE" if standard else "NL_JC"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if defect == "legacy-key":
        schema = schema.replace("RaceNum, HappyoTime, Umaban)", "RaceNum, Umaban)", 1)
    elif defect == "nullable-key":
        schema = schema.replace(
            (
                "HappyoTime                     VARCHAR(8) NOT NULL"
                if standard
                else "HappyoTime TEXT NOT NULL"
            ),
            "HappyoTime                     VARCHAR(8)         " if standard else "HappyoTime TEXT",
            1,
        )
    elif defect == "wrong-type":
        schema = schema.replace(
            (
                "Year                           SMALLINT NOT NULL"
                if standard
                else "Year INTEGER NOT NULL"
            ),
            (
                "Year                           VARCHAR(4) NOT NULL"
                if standard
                else "Year TEXT NOT NULL"
            ),
            1,
        )
    elif defect == "short-text":
        schema = schema.replace(
            (
                "HappyoTime                     VARCHAR(8) NOT NULL"
                if standard
                else "HappyoTime TEXT NOT NULL"
            ),
            (
                "HappyoTime                     VARCHAR(7) NOT NULL"
                if standard
                else "HappyoTime VARCHAR(7) NOT NULL"
            ),
            1,
        )
    else:
        schema = schema.replace(
            "PRIMARY KEY (", "UNIQUE (AtoKisyuCode),\n            PRIMARY KEY (", 1
        )

    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{defect}.db")})
    with database:
        database.execute(schema)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_jc()]))
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_unsafe_standard_jc_stops_before_unrelated_additive_migration(tmp_path) -> None:
    race_schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    unsafe_jc = JRAVAN_SCHEMAS["KISYU_CHANGE"].replace(
        "RaceNum, HappyoTime, Umaban)", "RaceNum, Umaban)", 1
    )
    database = SQLiteDatabase({"path": str(tmp_path / "standard-preflight.db")})
    with database:
        database.execute(race_schema)
        database.execute(unsafe_jc)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=True).import_records(iter([]))
        after = database.fetch_all('PRAGMA table_info("RACE")')
    assert after == before


def test_schema_manager_rejects_legacy_jc_before_unrelated_native_migration(
    tmp_path,
) -> None:
    legacy_jc = SCHEMAS["NL_JC"].replace("RaceNum, HappyoTime, Umaban)", "RaceNum, Umaban)", 1)
    incomplete_ra = SCHEMAS["NL_RA"].replace("            Crlf TEXT,\n", "", 1)
    database = SQLiteDatabase({"path": str(tmp_path / "native-preflight.db")})
    with database:
        database.execute(legacy_jc)
        database.execute(incomplete_ra)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("NL_RA")')
        assert SchemaManager(database).create_table("NL_RA") is False
        after = database.fetch_all('PRAGMA table_info("NL_RA")')
    assert after == before


def test_realtime_jc_uses_happyo_time_for_historical_exact_erase(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_JC"])
        database.commit()
        updater = RealtimeUpdater(database)
        inserted = updater.process_parsed_records_batch(
            [
                parsed_jc(make_date="20030710", happyo_time="07090630"),
                parsed_jc(make_date="20030710", happyo_time="07090710"),
            ]
        )
        erased = updater.process_parsed_records_batch(
            [
                parsed_jc(
                    data_kubun="0",
                    make_date="20030710",
                    happyo_time="07090630",
                    ato_futan="ABC",
                    ato_kisyu_code="ABCDE",
                    ato_minarai="8",
                )
            ]
        )
        rows = database.fetch_all("SELECT HappyoTime FROM RT_JC ORDER BY HappyoTime")

    assert inserted["success"] is True
    assert erased["success"] is True
    assert rows == [{"HappyoTime": "07090710"}]


def test_realtime_jc_rejects_malformed_caller_row_before_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime-invalid.db")})
    with database:
        database.execute(SCHEMAS["RT_JC"])
        database.commit()
        invalid = parsed_jc()
        invalid["HappyoTime"] = "99999999"
        result = RealtimeUpdater(database).process_parsed_records_batch([invalid])
        assert result["success"] is False
        assert result["inserted"] == 0
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_JC") == {"n": 0}


def test_jc_metadata_exposes_the_complete_identity_and_weight_unit() -> None:
    for table_name in ("NL_JC", "RT_JC"):
        metadata = TABLE_METADATA[table_name]
        assert tuple(metadata["primary_key"]) == JC_KEY
        columns = {column["name"]: column for column in metadata["columns"]}
        assert set(columns) == {
            field.name for field in JCParser()._fields if field.name != "RecordDelimiter"
        }
        assert "kg" in columns["AtoFutan"]["description"]


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
def test_jc_dual_verifies_every_target_before_mutation(tmp_path, unsafe_target: str) -> None:
    safe = SCHEMAS["NL_JC"]
    unsafe = safe.replace("PRIMARY KEY (", "UNIQUE (AtoKisyuCode),\n            PRIMARY KEY (", 1)
    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    with primary, secondary:
        primary.execute(unsafe if unsafe_target == "primary" else safe)
        secondary.execute(unsafe if unsafe_target == "secondary" else safe)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_jc()]))
        assert primary.fetch_one("SELECT COUNT(*) AS n FROM NL_JC") == {"n": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS n FROM NL_JC") == {"n": 0}


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_jc_{uuid4().hex[:12]}"
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
def test_jc_postgresql_identity_revision_and_historical_exact_erase(
    postgresql_db, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "KISYU_CHANGE" if standard else "NL_JC"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    first = parsed_jc(make_date="20030710", happyo_time="07090630")
    second = parsed_jc(make_date="20030710", happyo_time="07090710", ato_kisyu_code="09999")
    revision = dict(first)
    revision["AtoKisyuCode"] = "08888"
    delete = parsed_jc(
        data_kubun="0",
        make_date="20030710",
        happyo_time="07090630",
        ato_futan="ABC",
        ato_kisyu_code="ABCDE",
        ato_minarai="8",
    )
    import_records(
        postgresql_db,
        entrypoint,
        [first, second, revision, delete],
        standard=standard,
        auto_commit=auto_commit,
        batch_size=1,
    )
    assert postgresql_db.fetch_all(
        f'SELECT happyotime AS "HappyoTime" FROM {table_name} ORDER BY happyotime'
    ) == [{"HappyoTime": "07090710"}]
    assert postgresql_db.fetch_one(
        f'SELECT atofutan AS "AtoFutan", maefutan AS "MaeFutan" FROM {table_name}'
    ) == (
        {"AtoFutan": "550", "MaeFutan": "560"} if standard else {"AtoFutan": 55.0, "MaeFutan": 56.0}
    )


@pytest.mark.parametrize("defect", ("wrong-type", "short-text", "extra-unique", "deferrable-pk"))
def test_jc_postgresql_rejects_unsafe_identity_schema(postgresql_db, defect: str) -> None:
    schema = SCHEMAS["NL_JC"]
    if defect == "wrong-type":
        schema = schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL", 1)
    elif defect == "short-text":
        schema = schema.replace("HappyoTime TEXT NOT NULL", "HappyoTime VARCHAR(7) NOT NULL", 1)
    elif defect == "extra-unique":
        schema = schema.replace(
            "PRIMARY KEY (", "UNIQUE (AtoKisyuCode),\n            PRIMARY KEY (", 1
        )
    else:
        schema = schema.replace(
            "HappyoTime, Umaban)",
            "HappyoTime, Umaban) DEFERRABLE INITIALLY DEFERRED",
            1,
        )
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        verify_jc_storage_schema(postgresql_db, "NL_JC")


def test_jc_postgresql_realtime_preserves_times_and_erases_one_key(
    postgresql_db,
) -> None:
    postgresql_db.execute(SCHEMAS["RT_JC"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    inserted = updater.process_parsed_records_batch(
        [
            parsed_jc(make_date="20030710", happyo_time="07090630"),
            parsed_jc(make_date="20030710", happyo_time="07090710"),
        ]
    )
    erased = updater.process_parsed_records_batch(
        [
            parsed_jc(
                data_kubun="0",
                make_date="20030710",
                happyo_time="07090630",
                ato_futan="ABC",
                ato_kisyu_code="ABCDE",
                ato_minarai="8",
            )
        ]
    )
    assert inserted["success"] is True
    assert erased["success"] is True
    assert postgresql_db.fetch_all(
        'SELECT happyotime AS "HappyoTime" FROM RT_JC ORDER BY happyotime'
    ) == [{"HappyoTime": "07090710"}]
