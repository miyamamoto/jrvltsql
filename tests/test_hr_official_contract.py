"""Official HR payout/refund contract and durable-storage regressions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.dual_handler import DualDatabase
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema_types import get_table_column_types
from src.importer.importer import (
    DataImporter,
    clean_record_metadata,
    convert_record_types,
    translate_standard_field_names,
    validate_import_record_header,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.hr_parser import HRParser
from src.parser.status_domain import CURRENT_ACCUMULATED_DATA_KUBUN
from src.realtime.updater import RealtimeUpdater
from tests.test_hr_parser_full_payouts import build_record

FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
CONTRACT = json.loads((FIXTURES / "hr_contract_4901.json").read_text(encoding="utf-8"))
SDK_MANIFEST = json.loads((FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8"))
HR_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")


def _put(record: bytearray, start: int, width: int, value: str) -> None:
    encoded = value.encode("cp932", errors="strict")
    assert len(encoded) <= width
    record[start : start + width] = encoded.ljust(width, b" ")


def build_hr_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260818",
    year: str = "2026",
    month_day: str = "0818",
    jyo_cd: str = "05",
    kaiji: str = "03",
    nichiji: str = "08",
    race_num: str = "11",
) -> bytes:
    record = bytearray(build_record())
    for start, width, value in (
        (2, 1, data_kubun),
        (3, 8, make_date),
        (11, 4, year),
        (15, 4, month_day),
        (19, 2, jyo_cd),
        (21, 2, kaiji),
        (23, 2, nichiji),
        (25, 2, race_num),
    ):
        _put(record, start, width, value)
    for index, marker in enumerate(("111", "222", "333")):
        start = 405 + index * 16
        _put(record, start, 4, marker.zfill(4))
        _put(record, start + 4, 9, marker.zfill(9))
        _put(record, start + 13, 3, marker.zfill(3))
    return bytes(record)


def parsed_hr(**changes: str) -> dict:
    parsed = HRParser().parse(build_hr_record(**changes))
    assert parsed is not None
    return parsed


def import_records(
    database, entrypoint: str, records: list[dict], *, standard: bool, auto_commit: bool
) -> dict:
    if entrypoint == "data-batch":
        result = DataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    elif entrypoint == "optimized-batch":
        result = OptimizedDataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    else:
        importer = DataImporter(database, use_jravan_schema=standard)
        assert all(
            importer.import_single_record(record, auto_commit=auto_commit) for record in records
        )
        result = importer.get_statistics()
    if not auto_commit:
        database.commit()
    return result


def test_hr_layout_status_key_and_all_reserved_repeats_match_official_sources() -> None:
    assert CONTRACT["record_length"] == HRParser.RECORD_LENGTH == 719
    assert tuple(CONTRACT["primary_key"]) == HR_KEY
    assert frozenset(CONTRACT["current_data_kubun"]) == CURRENT_ACCUMULATED_DATA_KUBUN["HR"]
    assert SDK_MANIFEST["root_records"]["HR"] == {
        "struct": "JV_HR_PAY",
        "length": 719,
    }
    assert SDK_MANIFEST["structures"]["JV_HR_PAY"]["expanded_leaf_count"] == 202

    parsed = parsed_hr()
    assert [
        (parsed[f"Yobi{i}"], parsed[f"Yobi{i + 1}"], parsed[f"Yobi{i + 2}"]) for i in (1, 4, 7)
    ] == [
        ("0111", "000000111", "111"),
        ("0222", "000000222", "222"),
        ("0333", "000000333", "333"),
    ]
    assert parsed["SanrentanKumi"] == "070311"
    assert parsed["RecordDelimiter"] == ""

    # Bind every parser output and every standard translation to executable
    # storage. Representative-value tests alone missed most HARAI fields in
    # the previous implementation.
    assert set(parsed) == set(get_table_column_types("NL_HR"))
    translated = translate_standard_field_names(clean_record_metadata(parsed), "HARAI")
    converted = convert_record_types(translated, "HARAI")
    assert set(converted) == set(get_table_column_types("HARAI"))


@pytest.mark.parametrize(
    "changes",
    (
        {"year": "20A6"},
        {"month_day": "0230"},
        {"jyo_cd": "ZZ"},
        {"race_num": "1X"},
    ),
)
def test_hr_parser_rejects_malformed_official_keys(changes: dict[str, str]) -> None:
    assert HRParser().parse(build_hr_record(**changes)) is None


@pytest.mark.parametrize(
    "field,value",
    (
        ("FuseirituFlag1", "9"),
        ("HenkanUma28", "X"),
        ("TanPay", "notnumber"),
        ("WideKumi7", "123"),
    ),
)
def test_hr_caller_body_rejects_non_official_values_but_allows_blank_popularity(
    field: str, value: str
) -> None:
    valid = parsed_hr()
    valid["TanNinki"] = ""
    assert validate_import_record_header(valid) == ("HR", "1")
    invalid = parsed_hr()
    invalid[field] = value
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(invalid)


def test_hr_status_zero_rejects_a_coercible_wrong_key_before_delete() -> None:
    record = parsed_hr(data_kubun="0")
    record["RaceNum"] = "1X"
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_hr_same_length_2004_boundary_keeps_old_bytes_opaque() -> None:
    old_raw = build_hr_record(year="2004", month_day="0813")
    old = HRParser().parse(old_raw)
    current = parsed_hr(year="2004", month_day="0814")
    assert old is not None
    assert old["LegacyReserved604_717Hex"] == old_raw[603:717].hex()
    assert all(old[f"SanrentanKumi{'' if index == 1 else index}"] == "" for index in range(1, 7))
    assert current["LegacyReserved604_717Hex"] == ""
    assert current["SanrentanKumi"] == "070311"

    mislabeled_old = dict(old)
    mislabeled_old["SanrentanPay"] = "000000100"
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(mislabeled_old)

    mislabeled_current = dict(current)
    mislabeled_current["LegacyReserved604_717Hex"] = "00" * 114
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(mislabeled_current)


def test_hr_status_nine_keeps_unspecified_body_opaque() -> None:
    raw = build_hr_record(data_kubun="9")
    parsed = HRParser().parse(raw)
    assert parsed is not None
    assert parsed["OpaqueStatus9Body28_717Hex"] == raw[27:717].hex()
    assert len(parsed["OpaqueStatus9Body28_717Hex"]) == 1380
    assert parsed["TorokuTosu"] == ""
    assert parsed["FukuPay2"] == ""
    assert parsed["SanrentanPay"] == ""


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_hr_caller_built_status_nine_stores_only_key_and_state(tmp_path, standard: bool) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"caller-9-{standard}.db")})
    key_and_state = {
        key: value
        for key, value in parsed_hr(data_kubun="9").items()
        if key in {"RecordSpec", "DataKubun", "MakeDate", *HR_KEY}
    }
    with database:
        database.execute(schema)
        database.commit()
        importer = DataImporter(database, use_jravan_schema=standard)
        assert importer.import_single_record(parsed_hr()) is True
        assert importer.import_single_record(key_and_state) is True
        if standard:
            row = database.fetch_one(
                "SELECT DataKubun, PayFukusyoPay2 AS FukuPay2, "
                "OpaqueStatus9Body28_717Hex AS OpaqueBody FROM HARAI"
            )
        else:
            row = database.fetch_one(
                "SELECT DataKubun, FukuPay2, " "OpaqueStatus9Body28_717Hex AS OpaqueBody FROM NL_HR"
            )
        assert row == {"DataKubun": "9", "FukuPay2": None, "OpaqueBody": None}


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
def test_hr_storage_preserves_both_sides_of_the_same_length_2004_boundary(
    tmp_path, standard: bool
) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"boundary-{standard}.db")})
    with database:
        database.execute(schema)
        database.commit()
        result = DataImporter(database, use_jravan_schema=standard).import_records(
            iter(
                [
                    parsed_hr(year="2004", month_day="0813"),
                    parsed_hr(year="2004", month_day="0814"),
                ]
            )
        )
        assert result["records_imported"] == 2
        if standard:
            rows = database.fetch_all(
                "SELECT MonthDay, LegacyReserved604_717Hex AS LegacyBody, "
                "PaySanrentanPay1 AS SanrentanPay FROM HARAI ORDER BY MonthDay"
            )
            current_pay = "000015800"
        else:
            rows = database.fetch_all(
                "SELECT MonthDay, LegacyReserved604_717Hex AS LegacyBody, "
                "SanrentanPay FROM NL_HR ORDER BY MonthDay"
            )
            current_pay = 15800
        assert rows[0]["MonthDay"] == 813
        assert len(rows[0]["LegacyBody"]) == 228
        assert rows[0]["SanrentanPay"] is None
        assert rows[1] == {
            "MonthDay": 814,
            "LegacyBody": None,
            "SanrentanPay": current_pay,
        }


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hr_storage_preserves_payouts_provider_order_and_exact_erase(
    tmp_path, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{entrypoint}-{auto_commit}.db")})
    with database:
        database.execute(schema)
        database.commit()
        records = [
            parsed_hr(data_kubun="1"),
            parsed_hr(data_kubun="2"),
            parsed_hr(data_kubun="1", race_num="12"),
        ]
        result = import_records(
            database,
            entrypoint,
            records,
            standard=standard,
            auto_commit=auto_commit,
        )
        assert result["records_imported"] == 3
        assert result["records_failed"] == 0
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 2}
        if standard:
            row = database.fetch_one(
                "SELECT DataKubun, PayFukusyoPay2 AS FukuPay2, "
                "PayWidePay2 AS WidePay2, PayReserved1Kumi3 AS Yobi7, "
                "PayReserved1Pay3 AS Yobi8, PayReserved1Ninki3 AS Yobi9, "
                "PaySanrentanPay1 AS SanrentanPay FROM HARAI WHERE RaceNum = 11"
            )
            expected = {
                "DataKubun": "2",
                "FukuPay2": "000000280",
                "WidePay2": "000001370",
                "Yobi7": "0333",
                "Yobi8": "000000333",
                "Yobi9": "333",
                "SanrentanPay": "000015800",
            }
        else:
            row = database.fetch_one(
                "SELECT DataKubun, FukuPay2, WidePay2, Yobi7, Yobi8, Yobi9, "
                "SanrentanPay FROM NL_HR WHERE RaceNum = 11"
            )
            expected = {
                "DataKubun": "2",
                "FukuPay2": 280,
                "WidePay2": 1370,
                "Yobi7": "0333",
                "Yobi8": 333,
                "Yobi9": 333,
                "SanrentanPay": 15800,
            }
        assert row == expected

        cancellation_record = parsed_hr(data_kubun="9")
        cancellation_record["FukuPay2"] = "not-interpreted"
        cancellation_record["PayFukusyoPay2"] = "conflicting-opaque-body"
        cancelled = import_records(
            database,
            entrypoint,
            [cancellation_record],
            standard=standard,
            auto_commit=auto_commit,
        )
        assert cancelled["records_imported"] == 1
        if standard:
            cancelled_row = database.fetch_one(
                "SELECT DataKubun, PayFukusyoPay2 AS FukuPay2, "
                "PaySanrentanPay1 AS SanrentanPay, "
                "OpaqueStatus9Body28_717Hex AS OpaqueBody "
                "FROM HARAI WHERE RaceNum = 11"
            )
        else:
            cancelled_row = database.fetch_one(
                "SELECT DataKubun, FukuPay2, SanrentanPay, "
                "OpaqueStatus9Body28_717Hex AS OpaqueBody "
                "FROM NL_HR WHERE RaceNum = 11"
            )
        assert cancelled_row["DataKubun"] == "9"
        assert cancelled_row["FukuPay2"] is None
        assert cancelled_row["SanrentanPay"] is None
        assert len(cancelled_row["OpaqueBody"]) == 1380

        erase_record = parsed_hr(data_kubun="0")
        erase_record["FukuPay2"] = "not-interpreted"
        erase_record["PayFukusyoPay2"] = "conflicting-opaque-body"
        erased = import_records(
            database,
            entrypoint,
            [erase_record],
            standard=standard,
            auto_commit=auto_commit,
        )
        assert erased["records_imported"] == 1
        assert database.fetch_all(f"SELECT RaceNum FROM {table_name} ORDER BY RaceNum") == [
            {"RaceNum": 12}
        ]


def test_hr_wrong_primary_key_is_rejected_before_mutation(tmp_path) -> None:
    unsafe = SCHEMAS["NL_HR"].replace(
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)",
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, TanUmaban)",
        1,
    )
    assert unsafe != SCHEMAS["NL_HR"]
    database = SQLiteDatabase({"path": str(tmp_path / "wrong-key.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([parsed_hr()]))
        assert database.fetch_one("SELECT COUNT(*) AS n FROM NL_HR") == {"n": 0}


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", ("nullable-key", "wrong-type", "short-text", "extra-unique"))
def test_hr_unsafe_schema_is_rejected_before_mutation(
    tmp_path, standard: bool, defect: str
) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    unsafe = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if defect == "nullable-key":
        unsafe = unsafe.replace(
            (
                "Year                           SMALLINT NOT NULL"
                if standard
                else "Year INTEGER NOT NULL"
            ),
            "Year                           SMALLINT         " if standard else "Year INTEGER",
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
            (
                "LegacyReserved604_717Hex       VARCHAR(228)"
                if standard
                else "LegacyReserved604_717Hex TEXT"
            ),
            (
                "LegacyReserved604_717Hex       VARCHAR(227)"
                if standard
                else "LegacyReserved604_717Hex VARCHAR(227)"
            ),
            1,
        )
    else:
        unique_column = "PayTansyoUmaban1" if standard else "TanUmaban"
        unsafe = unsafe.replace(
            "PRIMARY KEY (", f"UNIQUE ({unique_column}),\n            PRIMARY KEY (", 1
        )
    database = SQLiteDatabase({"path": str(tmp_path / f"{standard}-{defect}.db")})
    with database:
        database.execute(unsafe)
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_hr()]))
        assert database.fetch_one(f"SELECT COUNT(*) AS n FROM {table_name}") == {"n": 0}


def test_realtime_hr_rejects_malformed_rows_and_erases_only_the_exact_key(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_HR"])
        database.commit()
        updater = RealtimeUpdater(database)
        inserted = updater.process_parsed_records_batch([parsed_hr(), parsed_hr(race_num="12")])
        revised = updater.process_parsed_records_batch([parsed_hr(data_kubun="9")])
        malformed = parsed_hr(data_kubun="0")
        malformed["RaceNum"] = "1X"
        rejected = updater.process_parsed_records_batch([malformed])
        erased = updater.process_parsed_records_batch([parsed_hr(data_kubun="0")])
        rows = database.fetch_all("SELECT RaceNum, DataKubun FROM RT_HR ORDER BY RaceNum")

    assert inserted["success"] is True
    assert inserted["inserted"] == 2
    assert inserted["errors"] == 0
    assert inserted["tables"] == ["RT_HR"]
    assert revised["success"] is True
    assert rejected["success"] is False and rejected["inserted"] == 0
    assert erased["success"] is True
    assert rows == [{"RaceNum": 12, "DataKubun": "1"}]


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
def test_hr_dual_rejects_an_unsafe_peer_before_either_database_changes(
    tmp_path, unsafe_target: str
) -> None:
    safe = SCHEMAS["NL_HR"]
    unsafe = safe.replace("PRIMARY KEY (", "UNIQUE (TanUmaban),\n            PRIMARY KEY (", 1)
    primary = SQLiteDatabase({"path": str(tmp_path / "primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "secondary.db")})
    with primary, secondary:
        primary.execute(unsafe if unsafe_target == "primary" else safe)
        secondary.execute(unsafe if unsafe_target == "secondary" else safe)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_hr()]))
        assert primary.fetch_one("SELECT COUNT(*) AS n FROM NL_HR") == {"n": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS n FROM NL_HR") == {"n": 0}


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")
    from scripts.setup_pg_test_db import postgresql_test_config
    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_hr_{uuid4().hex[:12]}"
    database.connect()
    try:
        database.execute(f"CREATE SCHEMA {schema_name}")
        database.execute(f"SET search_path TO {schema_name}")
        database.commit()
        yield database
    finally:
        try:
            database.rollback()
        except Exception:
            pass
        try:
            database.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            database.commit()
        finally:
            database.disconnect()


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_hr_postgresql_provider_order_readback_and_statistics(
    postgresql_db, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    postgresql_db.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
    postgresql_db.commit()
    records = [
        parsed_hr(data_kubun="1"),
        parsed_hr(data_kubun="2"),
        parsed_hr(data_kubun="9"),
        parsed_hr(data_kubun="1", race_num="12"),
    ]
    result = import_records(
        postgresql_db,
        entrypoint,
        records,
        standard=standard,
        auto_commit=auto_commit,
    )
    assert result["records_imported"] == 4
    assert result["records_failed"] == 0
    assert postgresql_db.fetch_one(f'SELECT COUNT(*) AS "n" FROM {table_name}') == {"n": 2}
    if standard:
        cancelled = postgresql_db.fetch_one(
            'SELECT DataKubun AS "DataKubun", PayFukusyoPay2 AS "FukuPay2", '
            'PaySanrentanPay1 AS "SanrentanPay", '
            'OpaqueStatus9Body28_717Hex AS "OpaqueBody" '
            "FROM HARAI WHERE RaceNum = 11"
        )
    else:
        cancelled = postgresql_db.fetch_one(
            'SELECT DataKubun AS "DataKubun", FukuPay2 AS "FukuPay2", '
            'SanrentanPay AS "SanrentanPay", '
            'OpaqueStatus9Body28_717Hex AS "OpaqueBody" '
            "FROM NL_HR WHERE RaceNum = 11"
        )
    assert cancelled["DataKubun"] == "9"
    assert cancelled["FukuPay2"] is None
    assert cancelled["SanrentanPay"] is None
    assert len(cancelled["OpaqueBody"]) == 1380


def test_hr_postgresql_realtime_status_nine_clears_prior_payouts(
    postgresql_db,
) -> None:
    postgresql_db.execute(SCHEMAS["RT_HR"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    live = updater.process_parsed_records_batch([parsed_hr(data_kubun="1")])
    cancelled = updater.process_parsed_records_batch([parsed_hr(data_kubun="9")])
    row = postgresql_db.fetch_one(
        'SELECT DataKubun AS "DataKubun", FukuPay2 AS "FukuPay2", '
        'OpaqueStatus9Body28_717Hex AS "OpaqueBody" FROM RT_HR'
    )
    assert live["success"] is True
    assert cancelled["success"] is True
    assert row["DataKubun"] == "9"
    assert row["FukuPay2"] is None
    assert len(row["OpaqueBody"]) == 1380


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("defect", ("wrong-type", "short-text", "extra-unique", "deferrable-pk"))
def test_hr_postgresql_rejects_unsafe_storage_before_mutation(
    postgresql_db, standard: bool, defect: str
) -> None:
    table_name = "HARAI" if standard else "NL_HR"
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if defect == "wrong-type":
        expected = (
            "Year                           SMALLINT NOT NULL"
            if standard
            else "Year INTEGER NOT NULL"
        )
        replacement = (
            "Year                           VARCHAR(4) NOT NULL"
            if standard
            else "Year TEXT NOT NULL"
        )
        schema = schema.replace(expected, replacement, 1)
    elif defect == "short-text":
        expected = (
            "OpaqueStatus9Body28_717Hex     VARCHAR(1380)"
            if standard
            else "OpaqueStatus9Body28_717Hex TEXT"
        )
        replacement = (
            "OpaqueStatus9Body28_717Hex     VARCHAR(1379)"
            if standard
            else "OpaqueStatus9Body28_717Hex VARCHAR(1379)"
        )
        schema = schema.replace(expected, replacement, 1)
    elif defect == "extra-unique":
        unique_column = "PayTansyoUmaban1" if standard else "TanUmaban"
        schema = schema.replace(
            "PRIMARY KEY (", f"UNIQUE ({unique_column}),\n            PRIMARY KEY (", 1
        )
    else:
        schema = schema.replace("RaceNum)", "RaceNum) DEFERRABLE INITIALLY DEFERRED", 1)
    postgresql_db.execute(schema)
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        DataImporter(postgresql_db, use_jravan_schema=standard).import_records(iter([parsed_hr()]))
    assert postgresql_db.fetch_one(f'SELECT COUNT(*) AS "n" FROM {table_name}') == {"n": 0}


@pytest.mark.parametrize("postgresql_is_primary", (False, True))
def test_hr_postgresql_dual_rejects_an_unsafe_peer_before_either_changes(
    postgresql_db, tmp_path, postgresql_is_primary: bool
) -> None:
    safe = SCHEMAS["NL_HR"]
    unsafe = safe.replace("PRIMARY KEY (", "UNIQUE (TanUmaban),\n            PRIMARY KEY (", 1)
    sqlite = SQLiteDatabase({"path": str(tmp_path / "hr-peer.db")})
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
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_hr()]))
        assert sqlite.fetch_one("SELECT COUNT(*) AS n FROM NL_HR") == {"n": 0}
        assert postgresql_db.fetch_one('SELECT COUNT(*) AS "n" FROM NL_HR') == {"n": 0}
