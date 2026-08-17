"""Official SE layout, identity, and storage regressions."""

from __future__ import annotations

import ast
import json
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.setup_pg_test_db import postgresql_test_config
from src.database.dual_handler import DualDatabase
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import (
    DataImporter,
    convert_record_types,
    validate_import_record_header,
    validate_se_record,
)
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.canonical import canonicalize_se_fields
from src.parser.se_parser import SEParser
from src.realtime.updater import RealtimeUpdater
from tests.fixtures.record_factory import make_se_record

SE_KEY_COLUMNS = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "Umaban",
    "KettoNum",
)
OFFICIAL_MANIFEST = json.loads(
    (Path(__file__).parent / "fixtures/official_layout/jvdata_sdk500_manifest.json").read_text(
        encoding="utf-8"
    )
)


def _se_parser_slices() -> list[tuple[str, int, int]]:
    """Read every named fixed slice from the production SE parse method."""

    tree = ast.parse(Path("src/parser/se_parser.py").read_text(encoding="utf-8-sig"))
    parser_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SEParser"
    )
    parse_method = next(
        node
        for node in parser_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "parse"
    )
    slices = []
    for node in ast.walk(parse_method):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "result"
            and isinstance(target.slice, ast.Constant)
            and isinstance(target.slice.value, str)
        ):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not value.args:
            continue
        data_slice = value.args[0]
        if not (
            isinstance(data_slice, ast.Subscript)
            and isinstance(data_slice.value, ast.Name)
            and data_slice.value.id == "data"
            and isinstance(data_slice.slice, ast.Slice)
            and isinstance(data_slice.slice.lower, ast.Constant)
            and isinstance(data_slice.slice.upper, ast.Constant)
        ):
            continue
        start = int(data_slice.slice.lower.value)
        stop = int(data_slice.slice.upper.value)
        slices.append((target.slice.value, start + 1, stop - start))
    return sorted(slices, key=lambda item: item[1])


def _official_se_slices() -> list[tuple[str, int, int]]:
    """Expand the SDK root at the same logical granularity as SEParser."""

    structures = OFFICIAL_MANIFEST["structures"]
    root = structures["JV_SE_RACE_UMA"]
    aliases = {
        "reserved1": "Reserved_229",
        "reserved2": "Reserved_296",
        "reserved3": "Reserved_382",
        "reserved4": "Reserved_385",
        "crlf": "RecordSeparator",
    }
    result: list[tuple[str, int, int]] = []
    for field in root["fields"]:
        start = int(field["start"])
        if field["name"] == "head":
            result.extend(
                [
                    ("RecordSpec", start, 2),
                    ("DataKubun", start + 2, 1),
                    ("MakeDate", start + 3, 8),
                ]
            )
        elif field["kind"] == "nested":
            for child in structures[field["struct"]]["fields"]:
                result.append((child["name"], start + int(child["start"]) - 1, int(child["width"])))
        elif field["kind"] == "repeat":
            children = structures[field["struct"]]["fields"]
            for index in range(int(field["count"])):
                item_start = start + index * int(field["stride"])
                for child in children:
                    result.append(
                        (
                            f"{child['name']}{index + 1}",
                            item_start + int(child["start"]) - 1,
                            int(child["width"]),
                        )
                    )
        else:
            result.append((aliases.get(field["name"], field["name"]), start, int(field["width"])))
    return sorted(result, key=lambda item: item[1])


def _official_pk_schema(schema: str) -> str:
    """Return a native SE DDL with the official eighth key for red probes."""

    seven = "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)"
    eight = "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, " "Umaban, KettoNum)"
    return schema.replace(seven, eight)


def _parsed_se(
    *,
    data_kubun: str = "1",
    ketto_num: str = "2020000001",
    reserved: bool = False,
    ba_taijyu: str = "508",
    zogen_sa: str = "003",
    honsyokin: str = "00000000",
    fukasyokin: str = "00000000",
) -> dict:
    raw = bytearray(
        make_se_record(
            data_kubun=data_kubun,
            kettonum=ketto_num,
            umaban="01",
        )
    )
    raw[324:327] = ba_taijyu.encode("ascii")
    raw[327:328] = b"+"
    raw[328:331] = zogen_sa.encode("ascii")
    raw[365:373] = honsyokin.encode("ascii")
    raw[373:381] = fukasyokin.encode("ascii")
    if reserved:
        raw[228:288] = b"A" * 60
        raw[295:296] = b"B"
        raw[381:384] = b"CCC"
        raw[384:387] = b"DDD"
    parsed = SEParser().parse(bytes(raw))
    assert parsed is not None
    return parsed


def _importer_classes() -> Iterator[type[DataImporter]]:
    yield DataImporter
    yield OptimizedDataImporter


def _import_records(
    database,
    entrypoint: str,
    records: list[dict],
    *,
    standard: bool,
    auto_commit: bool,
) -> None:
    if entrypoint == "data-batch":
        DataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    elif entrypoint == "optimized-batch":
        OptimizedDataImporter(database, use_jravan_schema=standard).import_records(
            iter(records), auto_commit=auto_commit
        )
    else:
        importer = DataImporter(database, use_jravan_schema=standard)
        for record in records:
            assert importer.import_single_record(record, auto_commit=auto_commit) is True
    if not auto_commit:
        database.commit()


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_se_{uuid4().hex[:12]}"
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


def test_se_current_fixture_is_provider_shaped_and_old_length_is_rejected() -> None:
    current = make_se_record(kettonum="2020000001")
    # The repository fixture is used by PostgreSQL storage tests, so it must
    # use the provider's space padding rather than SQLite-tolerated NUL bytes.
    assert len(current) == 555
    assert b"\x00" not in current
    assert SEParser().parse(current) is not None

    # Change-history row 331 proves only the old length and the two added
    # error fields. The complete old grammar is not pinned, so it stays an
    # explicit unsupported input instead of being inferred.
    old_length = current[:542] + current[550:553] + b"\r\n"
    assert len(old_length) == 547
    assert SEParser().parse(old_length) is None


def test_every_se_parser_slice_is_bound_to_the_pinned_sdk_manifest() -> None:
    expected = _official_se_slices()
    actual = _se_parser_slices()

    assert actual == expected
    covered = [False] * SEParser.RECORD_LENGTH
    for _, start, width in actual:
        for offset in range(start - 1, start - 1 + width):
            assert covered[offset] is False
            covered[offset] = True
    assert all(covered)
    header_and_key = {"RecordSpec", "DataKubun", "MakeDate", *SE_KEY_COLUMNS}
    expected_body_widths = {
        name: width
        for name, _, width in actual
        if name not in header_and_key and name != "RecordSeparator"
    }
    assert dict(SEParser.BODY_FIELD_BYTE_WIDTHS) == expected_body_widths


def test_se_all_storage_schemas_use_the_official_ordered_key() -> None:
    for table_name in ("NL_SE", "RT_SE", "UMA_RACE"):
        assert tuple(get_table_primary_key_columns(table_name)) == SE_KEY_COLUMNS


@pytest.mark.parametrize("importer_class", list(_importer_classes()))
def test_native_se_keeps_records_that_differ_only_by_ketto_num(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{importer_class.__name__}.db")})
    with database:
        database.execute(SCHEMAS["NL_SE"])
        database.commit()
        stats = importer_class(database).import_records(
            iter(
                [
                    _parsed_se(ketto_num="2020000001"),
                    _parsed_se(ketto_num="2020000002"),
                ]
            )
        )
        stored = database.fetch_all("SELECT KettoNum FROM NL_SE ORDER BY KettoNum")

    assert stats["records_imported"] == 2
    assert stats["records_failed"] == 0
    assert stored == [{"KettoNum": "2020000001"}, {"KettoNum": "2020000002"}]


def test_native_se_erase_targets_one_complete_official_key(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "erase.db")})
    with database:
        # Use the correct live-table key so this regression observes the
        # erase predicate independently from the currently wrong shipped DDL.
        database.execute(_official_pk_schema(SCHEMAS["NL_SE"]))
        database.commit()
        importer = DataImporter(database)
        importer.import_records(
            iter(
                [
                    _parsed_se(ketto_num="2020000001"),
                    _parsed_se(ketto_num="2020000002"),
                ]
            )
        )
        erased = importer.import_records(iter([_parsed_se(data_kubun="0", ketto_num="2020000001")]))
        stored = database.fetch_all("SELECT KettoNum, DataKubun FROM NL_SE ORDER BY KettoNum")

    assert erased["records_imported"] == 1
    assert erased["records_failed"] == 0
    assert stored == [{"KettoNum": "2020000002", "DataKubun": "1"}]


@pytest.mark.parametrize("importer_class", list(_importer_classes()))
def test_standard_se_is_idempotent_and_preserves_all_reserved_fields(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"std-{importer_class.__name__}.db")})
    with database:
        database.execute(JRAVAN_SCHEMAS["UMA_RACE"])
        database.commit()
        importer = importer_class(database, use_jravan_schema=True)
        first = _parsed_se(ketto_num="2020000001", reserved=True)
        second = _parsed_se(ketto_num="2020000002")
        importer.import_records(iter([first, second]))
        revision = dict(first)
        revision["DataKubun"] = "2"
        importer.import_records(iter([revision]))
        count_after_revision = database.fetch_one("SELECT COUNT(*) AS n FROM UMA_RACE")
        reserved = database.fetch_one(
            "SELECT reserved1, reserved2, reserved3, reserved4 "
            "FROM UMA_RACE WHERE KettoNum = '2020000001'"
        )
        importer.import_records(iter([_parsed_se(data_kubun="0", ketto_num="2020000001")]))
        remaining = database.fetch_all("SELECT KettoNum FROM UMA_RACE")

    assert count_after_revision == {"n": 2}
    assert reserved == {
        "reserved1": "A" * 60,
        "reserved2": "B",
        "reserved3": "CCC",
        "reserved4": "DDD",
    }
    assert remaining == [{"KettoNum": "2020000002"}]


@pytest.mark.parametrize(
    "changes",
    [
        {"KettoNum": ""},
        {"KettoNum": "123"},
        {"KettoNum": "ABCDEFGHIJ"},
        {"KettoNum": "12345678901"},
        {"Year": "20A6"},
        {"MonthDay": "0230"},
        {"JyoCD": "ZZ"},
    ],
)
def test_se_caller_key_is_rejected_before_numeric_coercion(changes: dict) -> None:
    record = _parsed_se()
    record.update(changes)
    with pytest.raises(SchemaMigrationError):
        validate_import_record_header(record)


def test_se_canonical_key_and_status9_remain_valid() -> None:
    assert validate_import_record_header(_parsed_se()) == ("SE", "1")
    assert validate_import_record_header(_parsed_se(data_kubun="9")) == ("SE", "9")
    # B2's initial KettoNum is the ten-byte numeric initial value, not blank.
    assert validate_import_record_header(_parsed_se(data_kubun="B", ketto_num="0000000000")) == (
        "SE",
        "B",
    )


@pytest.mark.parametrize(
    "defect",
    [
        "wrong-key-type",
        "wrong-body-type",
        "extra-unique",
        "null-key-row",
        "nonnull-body",
    ],
)
def test_se_unsafe_schema_is_rejected_before_mutation(tmp_path, defect: str) -> None:
    schema = _official_pk_schema(SCHEMAS["NL_SE"])
    if defect == "wrong-key-type":
        schema = schema.replace("Year INTEGER", "Year TEXT", 1)
    elif defect == "wrong-body-type":
        schema = schema.replace("BaTaijyu REAL", "BaTaijyu TEXT", 1)
    elif defect == "extra-unique":
        primary_key = (
            "PRIMARY KEY (\n"
            "                Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, "
            "Umaban, KettoNum\n"
            "            )"
        )
        schema = schema.replace(
            primary_key,
            f"UNIQUE (Bamei),\n            {primary_key}",
        )
        assert "UNIQUE (Bamei)" in schema
    elif defect == "null-key-row":
        schema = schema.replace("KettoNum TEXT NOT NULL", "KettoNum TEXT", 1)
    else:
        schema = schema.replace("Bamei TEXT,", "Bamei TEXT NOT NULL,", 1)

    database = SQLiteDatabase({"path": str(tmp_path / f"{defect}.db")})
    with database:
        database.execute(schema)
        if defect == "null-key-row":
            database.execute(
                "INSERT INTO NL_SE "
                "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, KettoNum) "
                "VALUES (2026, 101, '05', 1, 1, 1, 1, NULL)"
            )
        database.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(database).import_records(iter([_parsed_se()]))
        expected_rows = 1 if defect == "null-key-row" else 0
        assert database.fetch_one("SELECT COUNT(*) AS n FROM NL_SE") == {"n": expected_rows}


def test_realtime_se_uses_the_complete_key_for_targeted_erase(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with database:
        database.execute(_official_pk_schema(SCHEMAS["RT_SE"]))
        database.commit()
        updater = RealtimeUpdater(database)
        inserted = updater.process_parsed_records_batch(
            [_parsed_se(ketto_num="2020000001"), _parsed_se(ketto_num="2020000002")]
        )
        erased = updater.process_parsed_records_batch(
            [_parsed_se(data_kubun="0", ketto_num="2020000001")]
        )
        stored = database.fetch_all("SELECT KettoNum FROM RT_SE")

    assert inserted["success"] is True
    assert inserted["inserted"] == 2
    assert erased["success"] is True
    assert erased["inserted"] == 1
    assert stored == [{"KettoNum": "2020000002"}]


def test_se_native_units_and_status_a_prize_zero_follow_the_official_cells() -> None:
    status_a = _parsed_se(data_kubun="A", honsyokin="00000000", fukasyokin="00000000")
    converted = convert_record_types(status_a, "NL_SE")
    canonical = canonicalize_se_fields(status_a)

    assert converted["BaTaijyu"] == 508
    assert converted["ZogenSa"] == 3
    assert canonical["HonsyokinYen"] == 0
    assert canonical["FukasyokinYen"] is None


def test_se_dual_preserves_both_official_identities_and_targeted_erase(tmp_path) -> None:
    primary = SQLiteDatabase({"path": str(tmp_path / "dual-primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / "dual-secondary.db")})
    with primary, secondary:
        primary.execute(SCHEMAS["NL_SE"])
        secondary.execute(SCHEMAS["NL_SE"])
        primary.commit()
        secondary.commit()
        importer = DataImporter(DualDatabase(primary, secondary))
        importer.import_records(
            iter(
                [
                    _parsed_se(ketto_num="2020000001"),
                    _parsed_se(ketto_num="2020000002"),
                ]
            )
        )
        importer.import_records(iter([_parsed_se(data_kubun="0", ketto_num="2020000001")]))
        for database in (primary, secondary):
            assert database.fetch_all("SELECT KettoNum FROM NL_SE") == [{"KettoNum": "2020000002"}]


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
@pytest.mark.parametrize("defect", ("wrong-key-type", "extra-unique"))
def test_se_dual_rejects_unsafe_identity_on_either_target(
    tmp_path, unsafe_target: str, defect: str
) -> None:
    safe_schema = SCHEMAS["NL_SE"]
    if defect == "wrong-key-type":
        unsafe_schema = safe_schema.replace("Year INTEGER NOT NULL", "Year TEXT NOT NULL", 1)
    else:
        primary_key = (
            "PRIMARY KEY (\n"
            "                Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, "
            "Umaban, KettoNum\n"
            "            )"
        )
        unsafe_schema = safe_schema.replace(
            primary_key,
            f"UNIQUE (Bamei),\n            {primary_key}",
        )
    primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
    with primary, secondary:
        primary.execute(unsafe_schema if unsafe_target == "primary" else safe_schema)
        secondary.execute(unsafe_schema if unsafe_target == "secondary" else safe_schema)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([_parsed_se()]))
        assert primary.fetch_one("SELECT COUNT(*) AS n FROM NL_SE") == {"n": 0}
        assert secondary.fetch_one("SELECT COUNT(*) AS n FROM NL_SE") == {"n": 0}


@pytest.mark.parametrize(
    "defect",
    ("legacy-key", "nullable-key", "wrong-body-type", "nonnull-body"),
)
def test_unsafe_standard_se_key_stops_before_unrelated_additive_migration(
    tmp_path, defect: str
) -> None:
    race_schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    assert race_schema != JRAVAN_SCHEMAS["RACE"]
    if defect == "legacy-key":
        unsafe_se = (
            "CREATE TABLE UMA_RACE (Year INTEGER, MonthDay INTEGER, JyoCD TEXT, "
            "Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER, Umaban INTEGER, "
            "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban))"
        )
    elif defect == "nullable-key":
        unsafe_se = JRAVAN_SCHEMAS["UMA_RACE"].replace(
            "KettoNum                       VARCHAR(10) NOT NULL",
            "KettoNum                       VARCHAR(10)         ",
            1,
        )
        assert unsafe_se != JRAVAN_SCHEMAS["UMA_RACE"]
    elif defect == "wrong-body-type":
        unsafe_se = JRAVAN_SCHEMAS["UMA_RACE"].replace(
            "BaTaijyu                       SMALLINT",
            "BaTaijyu                       VARCHAR(3)",
            1,
        )
    else:
        unsafe_se = JRAVAN_SCHEMAS["UMA_RACE"].replace(
            "Bamei                          VARCHAR(36)         ",
            "Bamei                          VARCHAR(36) NOT NULL",
            1,
        )
    database = SQLiteDatabase({"path": str(tmp_path / "preflight.db")})
    with database:
        database.execute(race_schema)
        database.execute(unsafe_se)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=True).import_records(iter([]))
        after = database.fetch_all('PRAGMA table_info("RACE")')

    assert after == before


@pytest.mark.parametrize(
    "changes",
    (
        {"Reserved_229": "A", "reserved1": "B"},
        {"Reserved_229": "A" * 61},
    ),
)
def test_first_se_body_rejection_stops_before_standard_migration(
    tmp_path, changes: dict
) -> None:
    race_schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    database = SQLiteDatabase({"path": str(tmp_path / "first-body.db")})
    with database:
        database.execute(race_schema)
        database.execute(JRAVAN_SCHEMAS["UMA_RACE"])
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        record = _parsed_se()
        record.update(changes)
        with pytest.raises(SchemaMigrationError):
            DataImporter(database, use_jravan_schema=True).import_records(iter([record]))
        after = database.fetch_all('PRAGMA table_info("RACE")')

    assert after == before


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("Bamei", "馬" * 19),
        ("Bamei", "\U0001f40e"),
        ("Reserved_229", "A" * 61),
        ("Reserved_296", "AB"),
        ("Reserved_382", "ABCD"),
        ("Reserved_385", "ABCD"),
    ],
)
def test_se_caller_body_must_fit_the_official_cp932_span(
    field_name: str, value: str
) -> None:
    record = _parsed_se()
    record[field_name] = value

    with pytest.raises(SchemaMigrationError):
        validate_se_record(record, "UMA_RACE")

    delete = _parsed_se(data_kubun="0")
    delete[field_name] = value
    assert validate_se_record(delete, "UMA_RACE") is True


def test_schema_manager_stops_unrelated_native_migration_on_unsafe_se(tmp_path) -> None:
    unsafe_se = SCHEMAS["NL_SE"].replace(
        "Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, KettoNum",
        "Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban",
        1,
    )
    incomplete_ra = SCHEMAS["NL_RA"].replace("            Crlf TEXT,\n", "", 1)
    assert incomplete_ra != SCHEMAS["NL_RA"]
    database = SQLiteDatabase({"path": str(tmp_path / "schema-manager.db")})
    with database:
        database.execute(unsafe_se)
        database.execute(incomplete_ra)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("NL_RA")')
        created = SchemaManager(database).create_table("NL_RA")
        after = database.fetch_all('PRAGMA table_info("NL_RA")')

    assert created is False
    assert after == before


@pytest.mark.parametrize("table_name", ("NL_SE", "RT_SE"))
@pytest.mark.parametrize("existing_target", ("primary", "secondary"))
def test_schema_manager_repairs_only_the_missing_dual_se_table(
    tmp_path, table_name: str, existing_target: str
) -> None:
    primary = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / f"{table_name}-secondary.db")})
    with primary, secondary:
        existing = primary if existing_target == "primary" else secondary
        existing.execute(SCHEMAS[table_name])
        existing.commit()
        created = SchemaManager(DualDatabase(primary, secondary)).create_table(table_name)

        assert created is True
        assert primary.table_exists_strict(table_name) is True
        assert secondary.table_exists_strict(table_name) is True


def test_data_importer_fallback_counts_only_durable_se_rows(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "fallback.db")})
    with database:
        database.execute(SCHEMAS["NL_SE"])
        database.execute(
            "CREATE TRIGGER reject_se_bamei BEFORE INSERT ON NL_SE "
            "WHEN NEW.Bamei = 'FAIL' BEGIN SELECT RAISE(ABORT, 'rejected'); END"
        )
        database.commit()
        good = _parsed_se(ketto_num="2020000001")
        bad = _parsed_se(ketto_num="2020000002")
        good["Bamei"] = "OK"
        bad["Bamei"] = "FAIL"
        stats = DataImporter(database).import_records(iter([good, bad]))
        durable = database.fetch_all("SELECT KettoNum FROM NL_SE")

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 1
    assert durable == [{"KettoNum": "2020000001"}]


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_se_postgresql_full_key_update_erase_and_readback(
    postgresql_db, standard: bool, entrypoint: str, auto_commit: bool
) -> None:
    table_name = "UMA_RACE" if standard else "NL_SE"
    schema_sql = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    postgresql_db.execute(schema_sql)
    postgresql_db.commit()

    first = _parsed_se(ketto_num="2020000001", reserved=True)
    second = _parsed_se(ketto_num="2020000002")
    _import_records(
        postgresql_db,
        entrypoint,
        [first, second],
        standard=standard,
        auto_commit=auto_commit,
    )
    revision = dict(first)
    revision["DataKubun"] = "2"
    _import_records(
        postgresql_db,
        entrypoint,
        [revision],
        standard=standard,
        auto_commit=auto_commit,
    )
    reserved_name = "reserved1" if standard else "Reserved_229"
    rows = postgresql_db.fetch_all(
        f'SELECT kettonum AS "KettoNum", bataijyu AS "BaTaijyu", '
        f'{reserved_name} AS "Reserved" FROM {table_name} ORDER BY kettonum'
    )
    assert rows == [
        {"KettoNum": "2020000001", "BaTaijyu": 508, "Reserved": "A" * 60},
        {"KettoNum": "2020000002", "BaTaijyu": 508, "Reserved": None},
    ]

    _import_records(
        postgresql_db,
        entrypoint,
        [_parsed_se(data_kubun="0", ketto_num="2020000001")],
        standard=standard,
        auto_commit=auto_commit,
    )
    assert postgresql_db.fetch_all(f'SELECT kettonum AS "KettoNum" FROM {table_name}') == [
        {"KettoNum": "2020000002"}
    ]


def test_se_postgresql_realtime_preserves_full_key_and_targeted_erase(
    postgresql_db,
) -> None:
    postgresql_db.execute(SCHEMAS["RT_SE"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)

    inserted = updater.process_parsed_records_batch(
        [_parsed_se(ketto_num="2020000001"), _parsed_se(ketto_num="2020000002")]
    )
    erased = updater.process_parsed_records_batch(
        [_parsed_se(data_kubun="0", ketto_num="2020000001")]
    )

    assert inserted["success"] is True
    assert inserted["inserted"] == 2
    assert erased["success"] is True
    assert erased["inserted"] == 1
    assert postgresql_db.fetch_all('SELECT kettonum AS "KettoNum" FROM RT_SE') == [
        {"KettoNum": "2020000002"}
    ]


@pytest.mark.parametrize("defect", ("wrong-key-type", "extra-unique", "deferrable-pk"))
def test_se_postgresql_rejects_unsafe_identity_schema(postgresql_db, defect: str) -> None:
    schema = SCHEMAS["NL_SE"]
    primary_key = (
        "PRIMARY KEY (\n"
        "                Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, "
        "Umaban, KettoNum\n"
        "            )"
    )
    if defect == "wrong-key-type":
        schema = schema.replace("Year INTEGER NOT NULL", "Year VARCHAR(4) NOT NULL", 1)
    elif defect == "extra-unique":
        schema = schema.replace(
            primary_key,
            f"UNIQUE (Bamei),\n            {primary_key}",
        )
    else:
        schema = schema.replace(
            primary_key,
            f"{primary_key} DEFERRABLE INITIALLY DEFERRED",
        )
    postgresql_db.execute(schema)
    postgresql_db.commit()

    with pytest.raises(SchemaMigrationError):
        DataImporter(postgresql_db).import_records(iter([_parsed_se()]))
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS n FROM NL_SE") == {"n": 0}


@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
def test_se_postgresql_dual_rejects_overwidth_body_before_any_write(
    tmp_path, postgresql_db, entrypoint: str
) -> None:
    sqlite = SQLiteDatabase({"path": str(tmp_path / f"dual-{entrypoint}.db")})
    with sqlite:
        sqlite.execute(JRAVAN_SCHEMAS["UMA_RACE"])
        postgresql_db.execute(JRAVAN_SCHEMAS["UMA_RACE"])
        sqlite.commit()
        postgresql_db.commit()
        dual = DualDatabase(sqlite, postgresql_db)
        record = _parsed_se()
        record["Reserved_229"] = "A" * 61

        with pytest.raises(SchemaMigrationError):
            if entrypoint == "data-batch":
                DataImporter(dual, use_jravan_schema=True).import_records(iter([record]))
            elif entrypoint == "optimized-batch":
                OptimizedDataImporter(dual, use_jravan_schema=True).import_records(
                    iter([record])
                )
            else:
                DataImporter(dual, use_jravan_schema=True).import_single_record(record)

        assert sqlite.fetch_one("SELECT COUNT(*) AS n FROM UMA_RACE") == {"n": 0}
        assert postgresql_db.fetch_one("SELECT COUNT(*) AS n FROM UMA_RACE") == {"n": 0}


def test_se_postgresql_fallback_counts_only_durable_rows(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_SE"])
    postgresql_db.execute(
        "CREATE FUNCTION reject_se_bamei() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.bamei = 'FAIL' THEN RAISE EXCEPTION 'rejected'; END IF; "
        "RETURN NEW; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_se_bamei BEFORE INSERT ON NL_SE "
        "FOR EACH ROW EXECUTE FUNCTION reject_se_bamei()"
    )
    postgresql_db.commit()
    good = _parsed_se(ketto_num="2020000001")
    bad = _parsed_se(ketto_num="2020000002")
    good["Bamei"] = "OK"
    bad["Bamei"] = "FAIL"

    stats = DataImporter(postgresql_db).import_records(iter([good, bad]))

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 1
    assert postgresql_db.fetch_all('SELECT kettonum AS "KettoNum" FROM NL_SE') == [
        {"KettoNum": "2020000001"}
    ]
