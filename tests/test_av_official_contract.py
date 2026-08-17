"""Official AV scratched/excluded-horse contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, validate_import_record_header
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.av_parser import AVParser
from src.parser.status_domain import (
    CURRENT_ACCUMULATED_DATA_KUBUN,
    HISTORICAL_DATA_KUBUN,
)
from src.realtime.updater import RealtimeUpdater

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
OFFICIAL_MANIFEST = json.loads(
    (FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
)
AV_CONTRACT = json.loads((FIXTURES / "av_contract_4901.json").read_text(encoding="utf-8"))
AV_KEY = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "Umaban",
)

AV_SDK_FIELD_NAMES = {
    ("head", "RecordSpec"): "RecordSpec",
    ("head", "DataKubun"): "DataKubun",
    ("head", "MakeDate"): "MakeDate",
    ("id", "Year"): "Year",
    ("id", "MonthDay"): "MonthDay",
    ("id", "JyoCD"): "JyoCD",
    ("id", "Kaiji"): "Kaiji",
    ("id", "Nichiji"): "Nichiji",
    ("id", "RaceNum"): "RaceNum",
    ("HappyoTime", "Month"): "HappyoTimeMonth",
    ("HappyoTime", "Day"): "HappyoTimeDay",
    ("HappyoTime", "Hour"): "HappyoTimeHour",
    ("HappyoTime", "Minute"): "HappyoTimeMinute",
    ("Umaban",): "Umaban",
    ("Bamei",): "Bamei",
    ("JiyuKubun",): "JiyuKubun",
    ("crlf",): "RecordDelimiter",
}


def _put(record: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    record[start : start + width] = encoded.ljust(width, b" ")


def build_av_record(
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
    jiyu_kubun: str = "001",
) -> bytes:
    record = bytearray(b" " * AVParser.RECORD_LENGTH)
    for start, width, value in (
        (0, 2, "AV"),
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
        (73, 3, jiyu_kubun),
    ):
        _put(record, start, width, value)
    record[-2:] = b"\r\n"
    return bytes(record)


def parsed_av(**overrides) -> dict:
    parsed = AVParser().parse(build_av_record(**overrides))
    assert parsed is not None
    return parsed


def sdk_av_parser_contract() -> list[tuple[str, int, int]]:
    structures = OFFICIAL_MANIFEST["structures"]
    contract: list[tuple[str, int, int]] = []

    def visit(structure_name: str, start: int, path: tuple[str, ...]) -> None:
        for field in structures[structure_name]["fields"]:
            field_start = start + field["start"] - 1
            field_path = (*path, field["name"])
            parser_name = AV_SDK_FIELD_NAMES.get(field_path)
            if parser_name is not None:
                contract.append((parser_name, field_start, field["width"]))
            elif field["kind"] == "nested":
                visit(field["struct"], field_start, field_path)
            else:
                raise AssertionError(f"unmapped AV SDK scalar: {field_path}")

    visit("JV_AV_INFO", 1, ())
    return contract


def import_records(
    database, entrypoint, records, *, standard, auto_commit, batch_size=1000
) -> None:
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


def test_av_layout_status_and_storage_keys_match_official_sources() -> None:
    assert AV_CONTRACT["record_length"] == 78
    assert tuple(AV_CONTRACT["primary_key"]) == AV_KEY
    parser_contract = [(field.name, field.start + 1, field.length) for field in AVParser()._fields]
    assert parser_contract == [tuple(field) for field in AV_CONTRACT["fields"]]

    sdk_contract = sdk_av_parser_contract()
    assert sdk_contract[:9] == parser_contract[:9]
    assert sdk_contract[9:13] == [
        ("HappyoTimeMonth", 28, 2),
        ("HappyoTimeDay", 30, 2),
        ("HappyoTimeHour", 32, 2),
        ("HappyoTimeMinute", 34, 2),
    ]
    assert sdk_contract[13:] == parser_contract[10:]
    assert OFFICIAL_MANIFEST["root_records"]["AV"] == {
        "struct": "JV_AV_INFO",
        "length": 78,
    }
    assert frozenset(AV_CONTRACT["current_data_kubun"]) == CURRENT_ACCUMULATED_DATA_KUBUN["AV"]
    historical = HISTORICAL_DATA_KUBUN["AV"]
    assert AV_CONTRACT["historical_data_kubun"]["value"] == historical.value
    assert AV_CONTRACT["historical_data_kubun"]["valid_before_make_date"] == (
        historical.valid_before_make_date.isoformat()
    )

    for table_name in ("NL_AV", "RT_AV", "TORIKESI_JYOGAI"):
        assert tuple(get_table_primary_key_columns(table_name)) == AV_KEY
        nullability = get_table_column_nullability(table_name)
        assert all(nullability[column] is False for column in AV_KEY)


@pytest.mark.parametrize(
    "overrides",
    (
        {"make_date": "20260230"},
        {"month_day": "0230"},
        {"jyo_cd": "ZZ"},
        {"race_num": "1X"},
        {"happyo_time": "99999999"},
        {"umaban": "19"},
        {"jiyu_kubun": "999"},
    ),
)
def test_av_parser_and_caller_reject_invalid_fields_before_mutation(overrides: dict) -> None:
    with pytest.raises(ValueError):
        AVParser().parse(build_av_record(**overrides))

    valid = parsed_av()
    field_name = {
        "make_date": "MakeDate",
        "month_day": "MonthDay",
        "jyo_cd": "JyoCD",
        "race_num": "RaceNum",
        "happyo_time": "HappyoTime",
        "umaban": "Umaban",
        "jiyu_kubun": "JiyuKubun",
    }[next(iter(overrides))]
    valid[field_name] = next(iter(overrides.values()))
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(valid)


@pytest.mark.parametrize("data_kubun", ("1", "2"))
@pytest.mark.parametrize("reason", AV_CONTRACT["reason_codes"])
def test_av_accepts_both_reason_representations_and_current_statuses(
    data_kubun: str, reason: str
) -> None:
    record = parsed_av(
        data_kubun=data_kubun,
        happyo_time="00000000",
        jiyu_kubun=reason,
    )
    assert validate_import_record_header(record) == ("AV", data_kubun)


def test_av_historical_erase_has_an_opaque_body_and_an_exact_cutoff() -> None:
    assert parsed_av(
        data_kubun="0",
        make_date="20030710",
        happyo_time="99999999",
        jiyu_kubun="999",
    )
    with pytest.raises(ValueError):
        AVParser().parse(build_av_record(data_kubun="0", make_date="20030711"))


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_av_storage_revises_one_identity_and_exactly_erases_old_status_zero(
    tmp_path, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "TORIKESI_JYOGAI" if standard else "NL_AV"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{entrypoint}-{auto_commit}.db")})
    with database:
        database.execute(schema)
        database.commit()
        first = parsed_av(make_date="20030710", happyo_time="07090630")
        revision = parsed_av(
            data_kubun="2",
            make_date="20030710",
            happyo_time="07090710",
            jiyu_kubun="003",
        )
        delete = parsed_av(
            data_kubun="0",
            make_date="20030710",
            happyo_time="99999999",
            jiyu_kubun="999",
        )
        import_records(
            database,
            entrypoint,
            [first, revision, delete],
            standard=standard,
            auto_commit=auto_commit,
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize(
    "defect", ("wrong-key", "nullable-key", "wrong-type", "short-text", "extra-unique")
)
def test_av_unsafe_schema_is_rejected_before_mutation(
    tmp_path, standard: bool, defect: str
) -> None:
    table_name = "TORIKESI_JYOGAI" if standard else "NL_AV"
    unsafe = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if defect == "wrong-key":
        unsafe = unsafe.replace("RaceNum, Umaban)", "RaceNum, HappyoTime, Umaban)", 1)
    elif defect == "nullable-key":
        unsafe = unsafe.replace(
            (
                "Umaban                         SMALLINT NOT NULL"
                if standard
                else "Umaban INTEGER NOT NULL"
            ),
            "Umaban                         SMALLINT         " if standard else "Umaban INTEGER",
            1,
        )
    elif defect == "wrong-type":
        unsafe = unsafe.replace(
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
        unsafe = unsafe.replace(
            "HappyoTime                     VARCHAR(8)" if standard else "HappyoTime TEXT",
            "HappyoTime                     VARCHAR(7)" if standard else "HappyoTime VARCHAR(7)",
            1,
        )
    else:
        unsafe = unsafe.replace(
            "PRIMARY KEY (", "UNIQUE (HappyoTime),\n            PRIMARY KEY (", 1
        )

    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{defect}.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_av()]))
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_av_malformed_caller_is_rejected_before_mutation(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "caller.db")})
    with database:
        database.execute(SCHEMAS["NL_AV"])
        database.commit()
        malformed = parsed_av()
        malformed["RaceNum"] = "1X"
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([malformed]))
        assert database.fetch_one("SELECT COUNT(*) AS n FROM NL_AV") == {"n": 0}


@pytest.mark.parametrize("changes", ({"Bamei": "😀"}, {"Bamei": "あ" * 19}))
def test_av_caller_text_must_fit_the_official_cp932_span(changes: dict) -> None:
    record = parsed_av()
    record.update(changes)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_realtime_av_rejects_malformed_rows_and_replaces_complete_date_snapshot(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        for table_name in RealtimeUpdater.DATE_SNAPSHOT_TABLES:
            database.execute(SCHEMAS[table_name])
        database.commit()
        updater = RealtimeUpdater(database)
        first = updater.process_parsed_records_batch(
            [parsed_av(umaban="01"), parsed_av(umaban="02")]
        )
        malformed = parsed_av(umaban="03")
        malformed["RaceNum"] = "1X"
        rejected = updater.process_parsed_records_batch([malformed])
        updater.replace_date_snapshot("20260818")
        replaced = updater.process_parsed_records_batch([parsed_av(umaban="02")])
        database.commit()
        rows = database.fetch_all("SELECT Umaban FROM RT_AV ORDER BY Umaban")

    assert first["success"] is True
    assert rejected["success"] is False
    assert rejected["inserted"] == 0
    assert replaced["success"] is True
    assert replaced["inserted"] == 1
    assert rows == [{"Umaban": 2}]


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
def test_av_dual_rejects_one_unsafe_target_before_either_database_changes(
    tmp_path, unsafe_target: str
) -> None:
    safe = SCHEMAS["NL_AV"]
    unsafe = safe.replace("PRIMARY KEY (", "UNIQUE (HappyoTime),\n            PRIMARY KEY (", 1)
    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    with primary, secondary:
        primary.execute(unsafe if unsafe_target == "primary" else safe)
        secondary.execute(unsafe if unsafe_target == "secondary" else safe)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_av()]))
        assert primary.fetch_one("SELECT COUNT(*) AS n FROM NL_AV") == {"n": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS n FROM NL_AV") == {"n": 0}


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_av_{uuid4().hex[:12]}"
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
def test_av_postgresql_identity_revision_and_historical_exact_erase(
    postgresql_db, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "TORIKESI_JYOGAI" if standard else "NL_AV"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema)
    postgresql_db.commit()
    first = parsed_av(make_date="20030710", happyo_time="07090630")
    revision = parsed_av(
        data_kubun="2",
        make_date="20030710",
        happyo_time="07090710",
        jiyu_kubun="003",
    )
    delete = parsed_av(
        data_kubun="0",
        make_date="20030710",
        happyo_time="99999999",
        jiyu_kubun="999",
    )
    import_records(
        postgresql_db,
        entrypoint,
        [first, revision, delete],
        standard=standard,
        auto_commit=auto_commit,
        batch_size=1,
    )
    assert postgresql_db.fetch_one(f'SELECT COUNT(*) AS "n" FROM {table_name}') == {"n": 0}


@pytest.mark.parametrize("defect", ("wrong-type", "short-text", "extra-unique", "deferrable-pk"))
def test_av_postgresql_rejects_unsafe_identity_schema(postgresql_db, defect: str) -> None:
    schema = SCHEMAS["NL_AV"]
    if defect == "wrong-type":
        schema = schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL", 1)
    elif defect == "short-text":
        schema = schema.replace("HappyoTime TEXT", "HappyoTime VARCHAR(7)", 1)
    elif defect == "extra-unique":
        schema = schema.replace(
            "PRIMARY KEY (", "UNIQUE (HappyoTime),\n            PRIMARY KEY (", 1
        )
    else:
        schema = schema.replace(
            "RaceNum, Umaban)",
            "RaceNum, Umaban) DEFERRABLE INITIALLY DEFERRED",
            1,
        )
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        DataImporter(postgresql_db).import_records(iter([parsed_av()]))


@pytest.mark.parametrize("postgresql_is_primary", (False, True))
def test_av_postgresql_dual_rejects_an_unsafe_peer_before_either_changes(
    postgresql_db, tmp_path, postgresql_is_primary: bool
) -> None:
    safe = SCHEMAS["NL_AV"]
    unsafe = safe.replace("PRIMARY KEY (", "UNIQUE (HappyoTime),\n            PRIMARY KEY (", 1)
    sqlite = SQLiteDatabase({"path": str(tmp_path / "peer.db")})
    with sqlite:
        if postgresql_is_primary:
            postgresql_db.execute(safe)
            sqlite.execute(unsafe)
            primary, secondary = postgresql_db, sqlite
        else:
            sqlite.execute(safe)
            postgresql_db.execute(unsafe)
            primary, secondary = sqlite, postgresql_db
        postgresql_db.commit()
        sqlite.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_av()]))
        assert sqlite.fetch_one("SELECT COUNT(*) AS n FROM NL_AV") == {"n": 0}
        assert postgresql_db.fetch_one('SELECT COUNT(*) AS "n" FROM NL_AV') == {"n": 0}
