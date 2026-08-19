"""WC parser and storage contract for the official current 105-byte layout."""

import json
import os
from itertools import pairwise
from pathlib import Path
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import _STANDARD_FIELD_ALIASES, DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.wc_parser import WCParser


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


FIELDS = (
    ("RecordSpec", 1, 2, b"WC"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260817"),
    ("TresenKubun", 12, 1, b"0"),
    ("ChokyoDate", 13, 8, b"20260816"),
    ("ChokyoTime", 21, 4, b"0630"),
    ("KettoNum", 25, 10, b"2020100001"),
    ("Course", 35, 1, b"0"),
    ("BabaMawari", 36, 1, b"0"),
    ("reserved", 37, 1, b"0"),
    ("HaronTime10Total", 38, 4, b"1200"),
    ("LapTime_2000M_1800M", 42, 3, b"120"),
    ("HaronTime9Total", 45, 4, b"1080"),
    ("LapTime_1800M_1600M", 49, 3, b"120"),
    ("HaronTime8Total", 52, 4, b"0960"),
    ("LapTime_1600M_1400M", 56, 3, b"120"),
    ("HaronTime7Total", 59, 4, b"0840"),
    ("LapTime_1400M_1200M", 63, 3, b"120"),
    ("HaronTime6Total", 66, 4, b"0720"),
    ("LapTime_1200M_1000M", 70, 3, b"120"),
    ("HaronTime5Total", 73, 4, b"0600"),
    ("LapTime_1000M_800M", 77, 3, b"120"),
    ("HaronTime4Total", 80, 4, b"0480"),
    ("LapTime_800M_600M", 84, 3, b"120"),
    ("HaronTime3Total", 87, 4, b"0360"),
    ("LapTime_600M_400M", 91, 3, b"120"),
    ("HaronTime2Total", 94, 4, b"0240"),
    ("LapTime_400M_200M", 98, 3, b"120"),
    ("LapTime_200M_0M", 101, 3, b"120"),
    ("RecordDelimiter", 104, 2, b"\r\n"),
)

TIME_FIELDS = tuple(
    (name, width) for name, _, width, _ in FIELDS if name.startswith(("HaronTime", "LapTime"))
)
STANDARD_ALIASES = {
    "BabaMawari": "BabaAround",
    "HaronTime10Total": "HaronTime10",
    "LapTime_2000M_1800M": "LapTime10",
    "HaronTime9Total": "HaronTime9",
    "LapTime_1800M_1600M": "LapTime9",
    "HaronTime8Total": "HaronTime8",
    "LapTime_1600M_1400M": "LapTime8",
    "HaronTime7Total": "HaronTime7",
    "LapTime_1400M_1200M": "LapTime7",
    "HaronTime6Total": "HaronTime6",
    "LapTime_1200M_1000M": "LapTime6",
    "HaronTime5Total": "HaronTime5",
    "LapTime_1000M_800M": "LapTime5",
    "HaronTime4Total": "HaronTime4",
    "LapTime_800M_600M": "LapTime4",
    "HaronTime3Total": "HaronTime3",
    "LapTime_600M_400M": "LapTime3",
    "HaronTime2Total": "HaronTime2",
    "LapTime_400M_200M": "LapTime2",
    "LapTime_200M_0M": "LapTime1",
}
EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
NATIVE_FIELDS = set(EXPECTED)
STANDARD_FIELDS = NATIVE_FIELDS - {"RecordDelimiter", *STANDARD_ALIASES} | set(
    STANDARD_ALIASES.values()
)
OFFICIAL_KEY = ["TresenKubun", "ChokyoDate", "ChokyoTime", "KettoNum"]


def build_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260817",
    tresen_kubun: str = "0",
    chokyo_date: str = "20260816",
    chokyo_time: str = "0630",
    ketto_num: str = "2020100001",
    course: str = "0",
    baba_mawari: str = "0",
    all_nines: bool = False,
    field_overrides: dict[str, str] | None = None,
) -> bytes:
    values = {
        "DataKubun": data_kubun,
        "MakeDate": make_date,
        "TresenKubun": tresen_kubun,
        "ChokyoDate": chokyo_date,
        "ChokyoTime": chokyo_time,
        "KettoNum": ketto_num,
        "Course": course,
        "BabaMawari": baba_mawari,
    }
    if all_nines:
        values.update({name: "9" * width for name, width in TIME_FIELDS})
    if field_overrides:
        values.update(field_overrides)

    record = bytearray()
    for name, position, width, default in FIELDS:
        value = _pad(values[name], width) if name in values else default
        assert len(record) == position - 1
        assert len(value) == width
        record += value
    assert len(record) == WCParser.RECORD_LENGTH == 105
    return bytes(record)


def parsed_record(**kwargs) -> dict:
    record = WCParser().parse(build_record(**kwargs))
    assert record is not None
    return record


def _split_cp932_at_field_boundary() -> bytes:
    record = bytearray(build_record())
    record[10] = 0x82
    record[11] = 0xA0
    bytes(record).decode("cp932", errors="strict")
    return bytes(record)


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
    schema_name = f"jlt_wc_{uuid4().hex[:12]}"
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


def test_wc_layout_is_gap_free_and_reads_every_official_field() -> None:
    assert all(
        position + width == next_position
        for (_, position, width, _), (_, next_position, _, _) in pairwise(FIELDS)
    )
    assert WCParser().parse(build_record()) == EXPECTED
    all_nines = WCParser().parse(build_record(all_nines=True))
    assert all_nines is not None
    assert all(all_nines[name] == "9" * width for name, width in TIME_FIELDS)


def test_wc_layout_is_bound_to_the_pinned_sdk_manifest() -> None:
    manifest = json.loads(
        Path("tests/fixtures/official_layout/jvdata_sdk500_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    structures = manifest["structures"]
    sdk_compact_contract = []
    for field in structures["JV_WC_WOOD"]["fields"]:
        if field["name"] == "head":
            for header_field in structures[field["struct"]]["fields"]:
                sdk_compact_contract.append(
                    (
                        header_field["name"],
                        field["start"] + header_field["start"] - 1,
                        header_field["width"],
                    )
                )
        else:
            sdk_compact_contract.append((field["name"], field["start"], field["width"]))

    parser_fields = WCParser()._fields
    fixture_contract = [(name, position, width) for name, position, width, _ in FIELDS]
    assert [
        (field.name, field.start + 1, field.length) for field in parser_fields
    ] == fixture_contract
    assert _STANDARD_FIELD_ALIASES["WOOD"] == STANDARD_ALIASES
    parser_canonical_contract = [
        (
            (
                "crlf"
                if field.name == "RecordDelimiter"
                else _STANDARD_FIELD_ALIASES["WOOD"].get(field.name, field.name)
            ),
            field.start + 1,
            field.length,
        )
        for field in parser_fields
    ]
    assert parser_canonical_contract == sdk_compact_contract


def test_wc_manifest_oracle_rejects_production_parser_offset_drift(monkeypatch) -> None:
    original_define_fields = WCParser._define_fields

    def swapped_equal_width_fields(self):
        fields = original_define_fields(self)
        by_name = {field.name: field for field in fields}
        first = by_name["LapTime_2000M_1800M"]
        second = by_name["LapTime_1800M_1600M"]
        first.start, second.start = second.start, first.start
        return fields

    monkeypatch.setattr(WCParser, "_define_fields", swapped_equal_width_fields)
    with pytest.raises(AssertionError):
        test_wc_layout_is_bound_to_the_pinned_sdk_manifest()


def test_wc_accepts_real_calendar_dates_and_midnight() -> None:
    parsed = WCParser().parse(
        build_record(
            make_date="20260228",
            chokyo_date="20240229",
            chokyo_time="0000",
        )
    )
    assert parsed is not None
    assert parsed["MakeDate"] == "20260228"
    assert parsed["ChokyoDate"] == "20240229"
    assert parsed["ChokyoTime"] == "0000"


@pytest.mark.parametrize(
    "record",
    (
        build_record()[:-1],
        build_record() + b" ",
        b"XX" + build_record()[2:],
        build_record()[:-2] + b"  ",
        _split_cp932_at_field_boundary(),
        build_record(data_kubun=""),
        build_record(data_kubun="8"),
        build_record(make_date="20A60817"),
        build_record(make_date="20260230"),
        build_record(tresen_kubun="8"),
        build_record(chokyo_date="202A0816"),
        build_record(chokyo_date="20260230"),
        build_record(chokyo_time="06A0"),
        build_record(chokyo_time="1160"),
        build_record(chokyo_time="2400"),
        build_record(chokyo_time="9999"),
        build_record(ketto_num="20201A0001"),
        build_record(course="8"),
        build_record(baba_mawari="8"),
        build_record(field_overrides={"HaronTime10Total": "12A0"}),
    ),
)
def test_wc_rejects_noncurrent_or_corrupt_records(record: bytes) -> None:
    assert WCParser().parse(record) is None


def test_wc_delete_record_keeps_the_exact_official_key_without_blank_body_rule() -> None:
    deleted = WCParser().parse(
        build_record(
            data_kubun="0",
            course="8",
            baba_mawari="8",
            field_overrides={
                "reserved": "A",
                "HaronTime10Total": "ABCD",
                "LapTime_1000M_800M": "A1B",
            },
        )
    )
    assert deleted is not None
    assert deleted["DataKubun"] == "0"
    assert [deleted[name] for name in OFFICIAL_KEY] == [
        "0",
        "20260816",
        "0630",
        "2020100001",
    ]


def test_wc_native_and_canonical_schemas_match_the_official_key_and_fields() -> None:
    assert set(get_table_column_types("NL_WC")) == NATIVE_FIELDS
    assert get_table_primary_key_columns("NL_WC") == OFFICIAL_KEY
    assert set(get_table_column_types("WOOD")) == STANDARD_FIELDS
    assert get_table_primary_key_columns("WOOD") == OFFICIAL_KEY
    assert JRAVAN_TO_JLTSQL["WOOD"] == "NL_WC"
    assert JLTSQL_TO_JRAVAN["NL_WC"] == "WOOD"
    metadata = TABLE_METADATA["NL_WC"]
    assert [(column["name"], column["type"]) for column in metadata["columns"]] == list(
        get_table_column_types("NL_WC").items()
    )
    assert metadata["primary_key"] == OFFICIAL_KEY


def test_wc_4701_history_is_documentation_only_not_a_physical_layout() -> None:
    history = json.loads(
        Path("tests/fixtures/official_layout/jvdata_layout_history.json").read_text(
            encoding="utf-8"
        )
    )
    assert not any(item["record_type"] == "WC" for item in history["physical_length_changes"])
    wc_change = next(
        item for item in history["same_length_semantic_changes"] if item["record_type"] == "WC"
    )
    assert wc_change == {
        "record_type": "WC",
        "announced_date": "2022-02-22",
        "official_spec_version": "4.7.0.1",
        "length_unchanged": True,
        "layout_unchanged": True,
        "change_kind": "availability_documentation_clarification",
        "provenance_required": False,
        "reason": (
            "The specification added availability and measured-distance notes for "
            "Miho/Ritto woodchip training without changing the 105-byte layout."
        ),
        "source": "JV-Data4901.xlsx:変更履歴:56;特記事項:237-240",
    }


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard", "auto_commit"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            auto_commit,
            id=f"{importer_class.__name__}-{table_name}-commit-{auto_commit}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_WC", False), ("WOOD", True))
        for auto_commit in (True, False)
    ],
)
def test_wc_official_key_coexistence_course_update_and_provider_ordered_delete(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"ordered-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    haron_column = "HaronTime10" if standard else "HaronTime10Total"
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        created = importer.import_records(
            iter([parsed_record(tresen_kubun="0"), parsed_record(tresen_kubun="1")]),
            auto_commit=auto_commit,
        )
        rows_after_create = database.fetch_all(
            f"SELECT TresenKubun, Course FROM {table_name} ORDER BY TresenKubun"
        )
        updated = importer.import_records(
            iter([parsed_record(tresen_kubun="0", course="1", all_nines=True)]),
            auto_commit=auto_commit,
        )
        rows_after_update = database.fetch_all(
            f"SELECT TresenKubun, Course, {haron_column} AS haron "
            f"FROM {table_name} ORDER BY TresenKubun"
        )
        ordered = importer.import_records(
            iter(
                [
                    parsed_record(
                        data_kubun="0",
                        tresen_kubun="0",
                        course="8",
                        baba_mawari="8",
                        field_overrides={"HaronTime10Total": "ABCD"},
                    ),
                    parsed_record(tresen_kubun="0", course="2"),
                ]
            ),
            auto_commit=auto_commit,
        )
        rows_after_ordered_delete = database.fetch_all(
            f"SELECT DataKubun, TresenKubun, Course FROM {table_name} ORDER BY TresenKubun"
        )

    assert created["records_imported"] == 2
    assert created["records_failed"] == 0
    assert updated["records_imported"] == 1
    assert updated["records_failed"] == 0
    assert ordered["records_imported"] == 2
    assert ordered["records_failed"] == 0
    assert rows_after_create == [
        {"TresenKubun": "0", "Course": "0"},
        {"TresenKubun": "1", "Course": "0"},
    ]
    assert rows_after_update == [
        {"TresenKubun": "0", "Course": "1", "haron": 999.9},
        {"TresenKubun": "1", "Course": "0", "haron": 120.0},
    ]
    assert rows_after_ordered_delete == [
        {"DataKubun": "1", "TresenKubun": "0", "Course": "2"},
        {"DataKubun": "1", "TresenKubun": "1", "Course": "0"},
    ]


def _canonical_only(record: dict) -> dict:
    canonical = dict(record)
    for native, standard in STANDARD_ALIASES.items():
        canonical[standard] = canonical.pop(native)
    return canonical


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            id=f"{importer_class.__name__}-{table_name}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_WC", False), ("WOOD", True))
    ],
)
def test_wc_caller_built_rows_are_revalidated_before_mutation(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"caller-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        importer.import_records(iter([parsed_record()]))

        legacy_headers = parsed_record(chokyo_time="0631")
        legacy_headers["headRecordSpec"] = legacy_headers.pop("RecordSpec")
        legacy_headers["headDataKubun"] = legacy_headers.pop("DataKubun")
        assert importer.import_records(iter([legacy_headers]))["records_imported"] == 1

        blank_reserved = parsed_record(chokyo_time="0633", field_overrides={"reserved": ""})
        assert importer.import_records(iter([blank_reserved]))["records_imported"] == 1

        zero_measurements = parsed_record(
            chokyo_time="0634",
            field_overrides={name: "0" * width for name, width in TIME_FIELDS},
        )
        assert importer.import_records(iter([zero_measurements]))["records_imported"] == 1
        if standard:
            zero_columns = ("HaronTime10", "LapTime5", "LapTime1")
        else:
            zero_columns = (
                "HaronTime10Total",
                "LapTime_1000M_800M",
                "LapTime_200M_0M",
            )
        zero_row = database.fetch_one(
            f"SELECT {zero_columns[0]} AS first_value, "
            f"{zero_columns[1]} AS middle_value, {zero_columns[2]} AS last_value "
            f"FROM {table_name} WHERE ChokyoTime = ?",
            ("0634",),
        )
        assert zero_row == {"first_value": 0.0, "middle_value": 0.0, "last_value": 0.0}

        opaque_delete = parsed_record(
            data_kubun="0",
            course="8",
            baba_mawari="8",
            field_overrides={"HaronTime10Total": "ABCD"},
        )
        opaque_delete["reserved"] = "OVERSIZED"
        assert importer.import_records(iter([opaque_delete]))["records_imported"] == 1
        assert importer.import_records(iter([parsed_record()]))["records_imported"] == 1

        if standard:
            canonical = _canonical_only(parsed_record(chokyo_time="0632", all_nines=True))
            assert importer.import_records(iter([canonical]))["records_imported"] == 1
            assert database.fetch_one(
                "SELECT BabaAround, HaronTime10, LapTime1 FROM WOOD WHERE ChokyoTime = ?",
                ("0632",),
            ) == {"BabaAround": "0", "HaronTime10": 999.9, "LapTime1": 99.9}

        before = database.fetch_all(f"SELECT * FROM {table_name}")
        invalid_records = []

        missing_status = parsed_record()
        missing_status.pop("DataKubun")
        invalid_records.append(missing_status)
        blank_status = parsed_record()
        blank_status["DataKubun"] = ""
        invalid_records.append(blank_status)
        conflicting_status = parsed_record()
        conflicting_status["headDataKubun"] = "0"
        invalid_records.append(conflicting_status)
        invalid_status = parsed_record()
        invalid_status["DataKubun"] = "8"
        invalid_records.append(invalid_status)

        for field_name, invalid_value in (
            ("TresenKubun", "8"),
            ("MakeDate", "20260230"),
            ("ChokyoDate", "202A0816"),
            ("ChokyoDate", "20260230"),
            ("ChokyoTime", "06A0"),
            ("ChokyoTime", "1160"),
            ("ChokyoTime", "2400"),
            ("KettoNum", "20201A0001"),
            ("Course", "8"),
            ("BabaMawari", "8"),
            ("reserved", "OVERSIZED"),
            ("reserved", "馬"),
            ("HaronTime10Total", "12A0"),
        ):
            invalid = parsed_record()
            invalid[field_name] = invalid_value
            invalid_records.append(invalid)

        incomplete = parsed_record(data_kubun="0")
        incomplete["KettoNum"] = ""
        invalid_records.append(incomplete)

        if standard:
            conflict = parsed_record()
            conflict["BabaAround"] = "1"
            invalid_records.append(conflict)

        for invalid in invalid_records:
            with pytest.raises(SchemaMigrationError):
                importer.import_records(iter([invalid]))
        after = database.fetch_all(f"SELECT * FROM {table_name}")

    assert after == before


def _obsolete_schema(table_name: str, *, standard: bool) -> str:
    if standard:
        schema = JRAVAN_SCHEMAS.get("WOOD")
        if schema is None:
            schema = SCHEMAS["NL_WC"].replace("NL_WC", "WOOD")
    else:
        schema = SCHEMAS["NL_WC"]
    return schema.replace(
        "PRIMARY KEY (TresenKubun, ChokyoDate, ChokyoTime, KettoNum)",
        "PRIMARY KEY (ChokyoDate, ChokyoTime, KettoNum, Course)",
    )


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard", "auto_commit"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            auto_commit,
            id=f"{importer_class.__name__}-{table_name}-commit-{auto_commit}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_WC", False), ("WOOD", True))
        for auto_commit in (True, False)
    ],
)
def test_wc_obsolete_wrong_key_is_rejected_before_schema_or_row_mutation(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"obsolete-{table_name}.db")})
    with database:
        database.execute(_obsolete_schema(table_name, standard=standard))
        database.execute(
            f"INSERT INTO {table_name} "
            "(RecordSpec, DataKubun, TresenKubun, ChokyoDate, ChokyoTime, KettoNum, Course) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("WC", "1", "0", "20260815", "0600", "2020100999", "0"),
        )
        database.commit()
        before_schema = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        before_rows = database.fetch_all(f"SELECT * FROM {table_name}")

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=standard).import_records(
                iter([parsed_record()]), auto_commit=auto_commit
            )

        after_schema = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        after_rows = database.fetch_all(f"SELECT * FROM {table_name}")

    assert after_schema == before_schema
    assert after_rows == before_rows


@pytest.mark.parametrize(
    ("table_name", "standard", "auto_commit"),
    [
        pytest.param(table_name, standard, auto_commit, id=f"{table_name}-{auto_commit}")
        for table_name, standard in (("NL_WC", False), ("WOOD", True))
        for auto_commit in (True, False)
    ],
)
def test_wc_single_record_uses_the_same_validation_and_exact_delete(
    tmp_path,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        importer = DataImporter(database, use_jravan_schema=standard)
        importer.import_records(iter([parsed_record()]))
        missing_status = parsed_record()
        missing_status.pop("DataKubun")
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(missing_status, auto_commit=auto_commit)
        invalid_time = parsed_record()
        invalid_time["ChokyoTime"] = "1160"
        with pytest.raises(SchemaMigrationError):
            importer.import_single_record(invalid_time, auto_commit=auto_commit)
        opaque_delete = parsed_record(
            data_kubun="0",
            course="8",
            baba_mawari="8",
            field_overrides={"HaronTime10Total": "ABCD"},
        )
        opaque_delete["reserved"] = "OVERSIZED"
        assert importer.import_single_record(opaque_delete, auto_commit=auto_commit)
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


def test_wc_postgresql_native_and_standard_key_update_delete(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_WC"])
    postgresql_db.execute(JRAVAN_SCHEMAS["WOOD"])
    postgresql_db.commit()
    assert SchemaManager(postgresql_db).apply_metadata_to_table("NL_WC") is True
    postgresql_db.commit()

    for importer_class in (DataImporter, OptimizedDataImporter):
        for table_name, standard in (("NL_WC", False), ("WOOD", True)):
            importer = importer_class(postgresql_db, use_jravan_schema=standard)
            stats = importer.import_records(
                iter([parsed_record(tresen_kubun="0"), parsed_record(tresen_kubun="1")])
            )
            assert stats["records_imported"] == 2
            assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 2
            }
            importer.import_records(iter([parsed_record(tresen_kubun="0", course="2")]))
            assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                "count": 2
            }
            importer.import_records(
                iter([parsed_record(data_kubun="0", tresen_kubun="0", course="4")])
            )
            assert postgresql_db.fetch_all(
                f"SELECT TresenKubun AS tresen FROM {table_name} ORDER BY TresenKubun"
            ) == [{"tresen": "1"}]
            postgresql_db.execute(f"DELETE FROM {table_name}")
            postgresql_db.commit()

    primary_key_query = (
        "SELECT pg_get_constraintdef(c.oid) AS definition "
        "FROM pg_constraint c WHERE c.conrelid = to_regclass(?) AND c.contype = 'p'"
    )
    for table_name, standard in (("NL_WC", False), ("WOOD", True)):
        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.execute(_obsolete_schema(table_name, standard=standard))
        postgresql_db.execute(
            f"INSERT INTO {table_name} "
            "(RecordSpec, DataKubun, TresenKubun, ChokyoDate, ChokyoTime, KettoNum, Course) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("WC", "1", "0", "20260815", "0600", "2020100999", "0"),
        )
        postgresql_db.commit()
        before_key = postgresql_db.fetch_one(primary_key_query, (table_name.lower(),))
        before_rows = postgresql_db.fetch_all(f"SELECT * FROM {table_name}")

        for importer_class, auto_commit in (
            (DataImporter, True),
            (OptimizedDataImporter, False),
        ):
            with pytest.raises(SchemaMigrationError, match="primary key"):
                importer_class(postgresql_db, use_jravan_schema=standard).import_records(
                    iter([parsed_record()]), auto_commit=auto_commit
                )
            assert postgresql_db.fetch_one(primary_key_query, (table_name.lower(),)) == before_key
            assert postgresql_db.fetch_all(f"SELECT * FROM {table_name}") == before_rows
            postgresql_db.rollback()

        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.commit()


@pytest.mark.parametrize(
    ("table_name", "standard"),
    (("NL_WC", False), ("WOOD", True)),
)
def test_wc_storage_rejects_an_extra_unique_before_it_can_erase_another_key(
    tmp_path,
    table_name: str,
    standard: bool,
) -> None:
    """An extra UNIQUE turns a replacement into a silent erase of a different key."""

    schema = (JRAVAN_SCHEMAS if standard else SCHEMAS)[table_name]
    assert "PRIMARY KEY (" in schema
    drifted = schema.replace("PRIMARY KEY (", "UNIQUE (RecordSpec), PRIMARY KEY (", 1)

    for importer_class in (DataImporter, OptimizedDataImporter):
        for auto_commit in (True, False):
            database = SQLiteDatabase(
                {
                    "path": str(
                        tmp_path
                        / f"unique-{table_name}-{importer_class.__name__}-{auto_commit}.db"
                    )
                }
            )
            with database:
                database.execute(drifted)
                database.commit()
                before_indexes = database.fetch_all(f'PRAGMA index_list("{table_name}")')
                importer = importer_class(database, use_jravan_schema=standard)
                with pytest.raises(SchemaMigrationError, match="UNIQUE"):
                    importer.import_records(
                        iter([parsed_record(ketto_num="2020100001")]),
                        auto_commit=auto_commit,
                    )
                assert database.fetch_all(f'PRAGMA index_list("{table_name}")') == before_indexes
                assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {
                    "count": 0
                }
                assert importer.get_statistics()["records_imported"] == 0

    database = SQLiteDatabase({"path": str(tmp_path / f"official-{table_name}.db")})
    with database:
        database.create_table(table_name, schema)
        importer = DataImporter(database, use_jravan_schema=standard)
        importer.import_records(iter([parsed_record(ketto_num="2020100001")]))
        importer.import_records(iter([parsed_record(ketto_num="2020100002")]))
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}") == {"count": 2}
