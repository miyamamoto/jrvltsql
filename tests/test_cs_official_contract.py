"""Official CS course-information parser and storage contracts."""

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
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, validate_import_record_header
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.cs_parser import CSParser

OFFICIAL_FIXTURES = Path(__file__).parent / "fixtures" / "official_layout"
OFFICIAL_MANIFEST = json.loads(
    (OFFICIAL_FIXTURES / "jvdata_sdk500_manifest.json").read_text(encoding="utf-8")
)
CS_OFFICIAL_CONTRACT = json.loads(
    (OFFICIAL_FIXTURES / "cs_contract_4901.json").read_text(encoding="utf-8")
)
JYO_OFFICIAL_CONTRACT = json.loads(
    (OFFICIAL_FIXTURES / CS_OFFICIAL_CONTRACT["venue_code_contract"]).read_text(encoding="utf-8")
)
CS_KEY = ("JyoCD", "Kyori", "TrackCD", "KaishuDate")
CS_LAYOUT = (
    ("RecordSpec", 1, 2),
    ("DataKubun", 3, 1),
    ("MakeDate", 4, 8),
    ("JyoCD", 12, 2),
    ("Kyori", 14, 4),
    ("TrackCD", 18, 2),
    ("KaishuDate", 20, 8),
    ("CourseEx", 28, 6800),
    ("RecordDelimiter", 6828, 2),
)
LONG_COURSE_EX = "始" + ("中" * 3398) + "終"


def build_cs_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260817",
    jyo_cd: str = "08",
    kyori: str = "2400",
    track_cd: str = "18",
    kaishu_date: str = "20100101",
    course_ex: str = LONG_COURSE_EX,
) -> bytes:
    """Build one exact-width CS record from independently pinned spans."""

    record = bytearray(b" " * CSParser.RECORD_LENGTH)
    record[0:2] = b"CS"
    record[2:3] = data_kubun.encode("ascii")
    record[3:11] = make_date.encode("ascii")
    record[11:13] = jyo_cd.encode("ascii")
    record[13:17] = kyori.encode("ascii")
    record[17:19] = track_cd.encode("ascii")
    record[19:27] = kaishu_date.encode("ascii")
    encoded_course = course_ex.encode("cp932")
    if len(encoded_course) > 6800:
        raise ValueError("course_ex exceeds the official 6800-byte field")
    record[27 : 27 + len(encoded_course)] = encoded_course
    record[-2:] = b"\r\n"
    return bytes(record)


def parsed_record(**overrides) -> dict:
    record = CSParser().parse(build_cs_record(**overrides))
    assert record is not None
    return record


def _import_records(database, entrypoint, records, *, standard, auto_commit):
    if entrypoint == "data-batch":
        result = DataImporter(
            database,
            batch_size=1,
            use_jravan_schema=standard,
        ).import_records(iter(records), auto_commit=auto_commit)
        assert result["records_imported"] == len(records)
        assert result["records_failed"] == 0
    elif entrypoint == "optimized-batch":
        result = OptimizedDataImporter(
            database,
            batch_size=1,
            use_jravan_schema=standard,
        ).import_records(iter(records), auto_commit=auto_commit)
        assert result["records_imported"] == len(records)
        assert result["records_failed"] == 0
    else:
        importer = DataImporter(database, use_jravan_schema=standard)
        assert all(
            importer.import_single_record(record, auto_commit=auto_commit) for record in records
        )
        assert importer.get_statistics()["records_imported"] == len(records)
    if not auto_commit:
        database.commit()


def test_cs_layout_matches_the_pinned_sdk_and_both_current_workbooks():
    """The 4.8.0.2/4.9.0.1 rows and SDK 5.0 agree on one layout."""

    root = OFFICIAL_MANIFEST["root_records"]["CS"]
    structure = OFFICIAL_MANIFEST["structures"][root["struct"]]
    assert CS_OFFICIAL_CONTRACT["format_sources"] == [
        {
            "artifact": "JV-Data4802.xlsx",
            "sha256": "6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7",
            "sheet": "フォーマット",
            "rows": "1241-1251",
        },
        {
            "artifact": "JV-Data4901.xlsx",
            "sha256": "23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234",
            "sheet": "フォーマット",
            "rows": "1241-1251",
        },
    ]
    assert CS_OFFICIAL_CONTRACT["record_length"] == 6829
    assert [tuple(field) for field in CS_OFFICIAL_CONTRACT["fields"]] == list(CS_LAYOUT)
    assert CS_OFFICIAL_CONTRACT["primary_key"] == list(CS_KEY)
    assert root == {"struct": "JV_CS_COURSE", "length": 6829}
    assert structure["width"] == 6829
    assert [(field.name, field.start + 1, field.length) for field in CSParser()._fields] == list(
        CS_LAYOUT
    )
    assert [(field["name"], field["start"], field["width"]) for field in structure["fields"]] == [
        ("head", 1, 11),
        ("JyoCD", 12, 2),
        ("Kyori", 14, 4),
        ("TrackCD", 18, 2),
        ("KaishuDate", 20, 8),
        ("CourseEx", 28, 6800),
        ("crlf", 6828, 2),
    ]


def test_cs_parser_preserves_the_full_6800_byte_body_and_rejects_bad_length():
    parsed = parsed_record()
    assert parsed["CourseEx"] == LONG_COURSE_EX
    assert parsed["CourseEx"][0] == "始"
    assert parsed["CourseEx"][1700] == "中"
    assert parsed["CourseEx"][-1] == "終"

    with pytest.raises(ValueError, match="length mismatch"):
        CSParser().parse(build_cs_record() + b" ")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("make_date", "20260230"),
        ("jyo_cd", "@8"),
        ("jyo_cd", "ZZ"),
        ("jyo_cd", "11"),
        ("jyo_cd", "C4"),
        ("kyori", "24A0"),
        ("track_cd", "99"),
        ("track_cd", "30"),
        ("kaishu_date", "20260230"),
    ),
)
def test_cs_parser_rejects_malformed_official_key_fields(field, value):
    with pytest.raises(ValueError):
        CSParser().parse(build_cs_record(**{field: value}))


@pytest.mark.parametrize(
    ("jyo_cd", "track_cd"),
    (("A0", "00"), ("08", "59")),
)
def test_cs_parser_retains_official_initial_and_overseas_code_forms(jyo_cd, track_cd):
    parsed = parsed_record(jyo_cd=jyo_cd, track_cd=track_cd)
    assert parsed["JyoCD"] == jyo_cd
    assert parsed["TrackCD"] == track_cd


def test_cs_code_domains_match_the_complete_pinned_official_tables():
    assert CSParser.OFFICIAL_JYO_CODES == frozenset(
        JYO_OFFICIAL_CONTRACT["listed_non_initial_non_unused_codes"]
    )
    assert CSParser.OFFICIAL_JYO_CODES.isdisjoint(JYO_OFFICIAL_CONTRACT["excluded_codes"])
    assert CSParser.TRACK_CD_VALUES == frozenset(CS_OFFICIAL_CONTRACT["track_codes"])


@pytest.mark.parametrize(
    ("mutation", "value"),
    (
        ("missing", None),
        ("replace", None),
        ("replace", 6800),
        ("replace", "A" * 6801),
        ("replace", "😀"),
    ),
)
def test_cs_caller_body_validator_rejects_nonphysical_payloads(mutation, value):
    record = parsed_record(course_ex="x")
    if mutation == "missing":
        record.pop("CourseEx")
    else:
        record["CourseEx"] = value

    with pytest.raises(SchemaMigrationError, match="CourseEx"):
        validate_import_record_header(record)

    assert validate_import_record_header(parsed_record()) == ("CS", "1")
    blank_body = parsed_record(course_ex="x")
    blank_body["CourseEx"] = ""
    assert validate_import_record_header(blank_body) == ("CS", "1")


def test_cs_status_zero_keeps_the_future_delete_body_opaque():
    record = parsed_record(data_kubun="0", course_ex="ignored")
    record.pop("CourseEx")
    assert validate_import_record_header(record) == ("CS", "0")


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_cs_status_zero_discards_opaque_body_before_sqlite_storage(
    tmp_path, standard, entrypoint, auto_commit
):
    table_name = "COURSE" if standard else "NL_CS"
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"opaque-zero-{table_name}-{entrypoint}-{auto_commit}.db")}
    )
    record = parsed_record(data_kubun="0", course_ex="ignored")
    record["CourseEx"] = "A" * 6801
    with database:
        database.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
        database.commit()
        _import_records(
            database,
            entrypoint,
            [record],
            standard=standard,
            auto_commit=auto_commit,
        )
        row = database.fetch_one(f"SELECT DataKubun, CourseEx FROM {table_name}")
        assert row["DataKubun"] == "0"
        assert row["CourseEx"] is None


def test_cs_native_standard_and_metadata_schemas_preserve_the_official_contract():
    assert get_table_primary_key_columns("NL_CS") == list(CS_KEY)
    assert get_table_primary_key_columns("COURSE") == list(CS_KEY)
    assert get_table_column_types("NL_CS")["CourseEx"] == "TEXT"
    assert get_table_column_types("COURSE")["CourseEx"] == "TEXT"

    metadata = TABLE_METADATA["NL_CS"]
    assert [column["name"] for column in metadata["columns"]] == list(
        get_table_column_types("NL_CS")
    )
    assert metadata["primary_key"] == list(CS_KEY)


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_cs_import_preserves_two_renovations_and_updates_one_exact_key(
    tmp_path,
    standard,
    entrypoint,
    auto_commit,
):
    table_name = "COURSE" if standard else "NL_CS"
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"{table_name}-{entrypoint}-{auto_commit}.db")}
    )
    records = [
        parsed_record(kaishu_date="20100101", course_ex=LONG_COURSE_EX),
        parsed_record(kaishu_date="20230422", course_ex="改修後"),
        parsed_record(kaishu_date="20230422", course_ex="更新済み"),
    ]
    with database:
        database.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
        database.commit()
        _import_records(
            database,
            entrypoint,
            records,
            standard=standard,
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(
            f"SELECT JyoCD, Kyori, TrackCD, KaishuDate, CourseEx FROM {table_name} "
            "ORDER BY KaishuDate"
        )

    assert len(rows) == 2
    assert tuple(rows[0][column] for column in ("JyoCD", "Kyori", "TrackCD", "KaishuDate")) == (
        "08",
        2400,
        "18",
        "20100101",
    )
    assert rows[0]["CourseEx"] == LONG_COURSE_EX
    assert rows[1]["KaishuDate"] == "20230422"
    assert rows[1]["CourseEx"] == "更新済み"


OLD_NATIVE_CS_SCHEMA = """
CREATE TABLE NL_CS (
    RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, JyoCD TEXT,
    Kyori INTEGER, TrackCD TEXT, KaishuDate TEXT, CourseEx VARCHAR(6800),
    RecordDelimiter TEXT, PRIMARY KEY (JyoCD, Kyori, TrackCD)
)
"""
OLD_STANDARD_COURSE_SCHEMA = """
CREATE TABLE COURSE (
    RecordSpec CHAR(2), DataKubun CHAR(1), MakeDate DATE, JyoCD CHAR(2),
    Kyori SMALLINT, TrackCD VARCHAR(2), KaishuDate VARCHAR(8)
)
"""


@pytest.mark.parametrize(
    ("standard", "table_name", "schema_sql"),
    (
        (False, "NL_CS", OLD_NATIVE_CS_SCHEMA),
        (True, "COURSE", OLD_STANDARD_COURSE_SCHEMA),
    ),
    ids=("native-three-part-key", "standard-keyless-no-body"),
)
@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
def test_cs_legacy_storage_is_rejected_before_schema_or_row_mutation(
    tmp_path,
    standard,
    table_name,
    schema_sql,
    entrypoint,
):
    database = SQLiteDatabase({"path": str(tmp_path / f"legacy-{table_name}-{entrypoint}.db")})
    with database:
        database.execute(schema_sql)
        database.commit()
        before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )["sql"]
        with pytest.raises(SchemaMigrationError):
            _import_records(
                database,
                entrypoint,
                [parsed_record()],
                standard=standard,
                auto_commit=True,
            )
        after = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )["sql"]
        assert after == before
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("unsafe_target", ("primary", "secondary"))
@pytest.mark.parametrize("drift", ("extra-unique", "wrong-key-type"))
def test_cs_dual_rejects_unsafe_identity_storage_on_either_backend(tmp_path, unsafe_target, drift):
    safe_schema = """
    CREATE TABLE NL_CS (
        RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, JyoCD TEXT,
        Kyori INTEGER, TrackCD TEXT, KaishuDate TEXT, CourseEx VARCHAR(6800),
        RecordDelimiter TEXT, PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate)
    )
    """
    if drift == "extra-unique":
        unsafe_schema = safe_schema.replace(
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate)",
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate), UNIQUE (MakeDate)",
        )
    else:
        unsafe_schema = safe_schema.replace("Kyori INTEGER", "Kyori BLOB")
    primary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-primary.db")})
    secondary = SQLiteDatabase({"path": str(tmp_path / f"{unsafe_target}-secondary.db")})
    with primary, secondary:
        primary.execute(unsafe_schema if unsafe_target == "primary" else safe_schema)
        secondary.execute(unsafe_schema if unsafe_target == "secondary" else safe_schema)
        primary.commit()
        secondary.commit()
        with pytest.raises(SchemaMigrationError):
            DataImporter(DualDatabase(primary, secondary)).import_records(iter([parsed_record()]))
        assert primary.fetch_one("SELECT COUNT(*) AS count FROM NL_CS")["count"] == 0
        assert secondary.fetch_one("SELECT COUNT(*) AS count FROM NL_CS")["count"] == 0


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
def test_cs_caller_built_invalid_key_is_rejected_before_mutation(tmp_path, standard, entrypoint):
    table_name = "COURSE" if standard else "NL_CS"
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"caller-invalid-{table_name}-{entrypoint}.db")}
    )
    record = parsed_record()
    record["KaishuDate"] = "20260230"
    with database:
        database.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
        database.commit()
        with pytest.raises(SchemaMigrationError, match="CS"):
            _import_records(
                database,
                entrypoint,
                [record],
                standard=standard,
                auto_commit=True,
            )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_cs_caller_built_oversized_body_is_rejected_by_every_entrypoint(
    tmp_path, standard, entrypoint, auto_commit
):
    table_name = "COURSE" if standard else "NL_CS"
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"caller-body-{table_name}-{entrypoint}-{auto_commit}.db")}
    )
    record = parsed_record(course_ex="x")
    record["CourseEx"] = "A" * 6801
    with database:
        database.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
        database.commit()
        with pytest.raises(SchemaMigrationError, match="CourseEx"):
            _import_records(
                database,
                entrypoint,
                [record],
                standard=standard,
                auto_commit=auto_commit,
            )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
@pytest.mark.parametrize("drift", ("extra-unique", "short-body", "wrong-key-type"))
def test_cs_storage_drift_is_rejected_before_mutation(tmp_path, standard, entrypoint, drift):
    table_name = "COURSE" if standard else "NL_CS"
    schema_sql = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if drift == "extra-unique":
        schema_sql = schema_sql.replace(
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate)",
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate), UNIQUE (MakeDate)",
        )
    elif drift == "short-body":
        schema_sql = schema_sql.replace("VARCHAR(6800)", "VARCHAR(1)")
    elif standard:
        schema_sql = schema_sql.replace("Kyori                          SMALLINT", "Kyori TEXT")
    else:
        schema_sql = schema_sql.replace("Kyori INTEGER", "Kyori BLOB")
    database = SQLiteDatabase(
        {"path": str(tmp_path / f"drift-{drift}-{table_name}-{entrypoint}.db")}
    )
    with database:
        database.execute(schema_sql)
        expected_rows = 0
        if drift == "wrong-key-type":
            database.execute(
                f"INSERT INTO {table_name} "
                "(RecordSpec, DataKubun, MakeDate, JyoCD, Kyori, TrackCD, "
                "KaishuDate, CourseEx) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("CS", "1", "20200101", "08", "0900", "18", "20100101", "existing"),
            )
            expected_rows = 1
        database.commit()
        with pytest.raises(SchemaMigrationError):
            _import_records(
                database,
                entrypoint,
                [parsed_record(course_ex="長い説明")],
                standard=standard,
                auto_commit=True,
            )
        assert (
            database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]
            == expected_rows
        )


@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
def test_cs_standard_adds_only_a_missing_body_to_an_already_correct_key(tmp_path, entrypoint):
    schema_without_body = JRAVAN_SCHEMAS["COURSE"].replace(
        "            CourseEx                       VARCHAR(6800)        ,  -- コース説明\n",
        "",
    )
    assert "CourseEx" not in schema_without_body
    database = SQLiteDatabase({"path": str(tmp_path / f"add-body-{entrypoint}.db")})
    with database:
        database.execute(schema_without_body)
        database.commit()
        _import_records(
            database,
            entrypoint,
            [parsed_record(course_ex="追加済み")],
            standard=True,
            auto_commit=True,
        )
        row = database.fetch_one("SELECT CourseEx FROM COURSE")
        assert row["CourseEx"] == "追加済み"


@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("drift", ("nonempty-missing-body", "missing-nonbody"))
def test_cs_standard_additive_migration_rejects_unsafe_missing_columns(tmp_path, entrypoint, drift):
    if drift == "nonempty-missing-body":
        schema_sql = JRAVAN_SCHEMAS["COURSE"].replace(
            "            CourseEx                       VARCHAR(6800)        ,  -- コース説明\n",
            "",
        )
    else:
        schema_sql = JRAVAN_SCHEMAS["COURSE"].replace(
            "            DataKubun                      CHAR(1)             ,  -- データ区分\n",
            "",
        )
    expected_missing = "CourseEx" if drift == "nonempty-missing-body" else "DataKubun"
    assert expected_missing not in schema_sql
    database = SQLiteDatabase({"path": str(tmp_path / f"unsafe-additive-{drift}-{entrypoint}.db")})
    with database:
        database.execute(schema_sql)
        if drift == "nonempty-missing-body":
            database.execute(
                "INSERT INTO COURSE "
                "(RecordSpec, DataKubun, MakeDate, JyoCD, Kyori, TrackCD, KaishuDate) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("CS", "1", "20200101", "08", 2400, "18", "20100101"),
            )
        database.commit()
        before = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='COURSE'"
        )["sql"]
        with pytest.raises(SchemaMigrationError):
            _import_records(
                database,
                entrypoint,
                [parsed_record(kaishu_date="20230422")],
                standard=True,
                auto_commit=True,
            )
        after = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='COURSE'"
        )["sql"]
        assert after == before
        expected_rows = 1 if drift == "nonempty-missing-body" else 0
        assert database.fetch_one("SELECT COUNT(*) AS count FROM COURSE")["count"] == expected_rows


@pytest.fixture
def postgresql_db():
    if os.getenv("JLTSQL_RUN_POSTGRESQL_INTEGRATION") != "1":
        pytest.skip("Set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run PostgreSQL tests")

    from src.database.postgresql_handler import PostgreSQLDatabase

    database = PostgreSQLDatabase(postgresql_test_config())
    schema_name = f"jlt_cs_{uuid4().hex[:12]}"
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
@pytest.mark.parametrize(
    "entrypoint",
    ("data-batch", "optimized-batch", "single"),
)
def test_cs_postgresql_preserves_the_full_key_and_body(postgresql_db, standard, entrypoint):
    table_name = "COURSE" if standard else "NL_CS"
    postgresql_db.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
    postgresql_db.commit()
    _import_records(
        postgresql_db,
        entrypoint,
        [
            parsed_record(kaishu_date="20100101", course_ex=LONG_COURSE_EX),
            parsed_record(kaishu_date="20230422", course_ex="更新前"),
            parsed_record(kaishu_date="20230422", course_ex="更新済み"),
        ],
        standard=standard,
        auto_commit=True,
    )
    rows = postgresql_db.fetch_all(
        f'SELECT jyocd AS "JyoCD", kyori AS "Kyori", trackcd AS "TrackCD", '
        f'kaishudate AS "KaishuDate", courseex AS "CourseEx" FROM {table_name} '
        "ORDER BY kaishudate"
    )
    assert len(rows) == 2
    assert rows[0]["CourseEx"] == LONG_COURSE_EX
    assert rows[1]["CourseEx"] == "更新済み"


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
def test_cs_postgresql_rejects_a_caller_body_over_the_physical_byte_width(
    postgresql_db, standard, entrypoint
):
    table_name = "COURSE" if standard else "NL_CS"
    postgresql_db.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
    postgresql_db.commit()
    record = parsed_record(course_ex="x")
    record["CourseEx"] = "界" * 6800
    with pytest.raises(SchemaMigrationError, match="CourseEx"):
        _import_records(
            postgresql_db,
            entrypoint,
            [record],
            standard=standard,
            auto_commit=True,
        )
    assert postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("entrypoint", ("data-batch", "optimized-batch", "single"))
@pytest.mark.parametrize("auto_commit", (True, False), ids=("owned", "caller"))
def test_cs_postgresql_status_zero_discards_opaque_body_before_storage(
    postgresql_db, standard, entrypoint, auto_commit
):
    table_name = "COURSE" if standard else "NL_CS"
    postgresql_db.execute(JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name])
    postgresql_db.commit()
    record = parsed_record(data_kubun="0", course_ex="ignored")
    record["CourseEx"] = "A" * 6801
    _import_records(
        postgresql_db,
        entrypoint,
        [record],
        standard=standard,
        auto_commit=auto_commit,
    )
    row = postgresql_db.fetch_one(
        f'SELECT datakubun AS "DataKubun", courseex AS "CourseEx" FROM {table_name}'
    )
    assert row["DataKubun"] == "0"
    assert row["CourseEx"] is None


def test_cs_postgresql_rejects_a_nonempty_course_missing_the_body_before_alter(
    postgresql_db,
):
    schema_without_body = JRAVAN_SCHEMAS["COURSE"].replace(
        "            CourseEx                       VARCHAR(6800)        ,  -- コース説明\n",
        "",
    )
    assert "CourseEx" not in schema_without_body
    postgresql_db.execute(schema_without_body)
    postgresql_db.execute(
        "INSERT INTO COURSE "
        "(RecordSpec, DataKubun, MakeDate, JyoCD, Kyori, TrackCD, KaishuDate) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("CS", "1", "20200101", "08", 2400, "18", "20100101"),
    )
    postgresql_db.commit()

    with pytest.raises(SchemaMigrationError, match="existing rows"):
        DataImporter(postgresql_db, use_jravan_schema=True).import_records(
            iter([parsed_record(kaishu_date="20230422")])
        )

    columns = postgresql_db.fetch_all(
        "SELECT column_name AS name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'course'"
    )
    assert "courseex" not in {str(row["name"]).lower() for row in columns}
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM COURSE")["count"] == 1


@pytest.mark.parametrize("standard", (False, True), ids=("native", "standard"))
@pytest.mark.parametrize("drift", ("extra-unique", "deferrable-primary-key", "wrong-key-type"))
def test_cs_postgresql_constraint_drift_is_rejected_before_mutation(postgresql_db, standard, drift):
    table_name = "COURSE" if standard else "NL_CS"
    schema_sql = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    if drift == "extra-unique":
        replacement = "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate), UNIQUE (MakeDate)"
        schema_sql = schema_sql.replace(
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate)", replacement
        )
    elif drift == "deferrable-primary-key":
        replacement = (
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate) " "DEFERRABLE INITIALLY DEFERRED"
        )
        schema_sql = schema_sql.replace(
            "PRIMARY KEY (JyoCD, Kyori, TrackCD, KaishuDate)", replacement
        )
    elif standard:
        schema_sql = schema_sql.replace("Kyori                          SMALLINT", "Kyori TEXT")
    else:
        schema_sql = schema_sql.replace("Kyori INTEGER", "Kyori TEXT")
    postgresql_db.execute(schema_sql)
    expected_rows = 0
    if drift == "wrong-key-type":
        postgresql_db.execute(
            f"INSERT INTO {table_name} "
            "(RecordSpec, DataKubun, MakeDate, JyoCD, Kyori, TrackCD, "
            "KaishuDate, CourseEx) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("CS", "1", "20200101", "08", "0900", "18", "20100101", "existing"),
        )
        expected_rows = 1
    postgresql_db.commit()
    with pytest.raises(SchemaMigrationError):
        DataImporter(postgresql_db, use_jravan_schema=standard).import_records(
            iter([parsed_record()])
        )
    assert (
        postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]
        == expected_rows
    )


def test_cs_postgresql_metadata_targets_physical_columns(postgresql_db):
    postgresql_db.execute(SCHEMAS["NL_CS"])
    postgresql_db.commit()
    assert SchemaManager(postgresql_db).apply_metadata_to_table("NL_CS") is True
