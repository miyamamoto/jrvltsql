"""Official 382-byte YS schedule parser and storage contract tests."""

import os
from itertools import pairwise
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.ys_parser import YSParser

YS_OFFICIAL_LENGTH = 382
YS_KEY = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji"]
GUIDANCE_FIELDS = (
    ("TokuNum", 4),
    ("Hondai", 60),
    ("Ryakusyo10", 20),
    ("Ryakusyo6", 12),
    ("Ryakusyo3", 6),
    ("Nkai", 3),
    ("GradeCD", 1),
    ("SyubetuCD", 2),
    ("KigoCD", 3),
    ("JyuryoCD", 1),
    ("Kyori", 4),
    ("TrackCD", 2),
)


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
    schema_name = f"jlt_ys_{uuid4().hex[:12]}"
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


def _official_layout() -> tuple[tuple[str, int, int], ...]:
    fields: list[tuple[str, int, int]] = []
    cursor = 0

    def add(name: str, size: int) -> None:
        nonlocal cursor
        fields.append((name, cursor, size))
        cursor += size

    for name, size in (
        ("RecordSpec", 2),
        ("DataKubun", 1),
        ("MakeDate", 8),
        ("Year", 4),
        ("MonthDay", 4),
        ("JyoCD", 2),
        ("Kaiji", 2),
        ("Nichiji", 2),
        ("YoubiCD", 1),
    ):
        add(name, size)
    for number in range(1, 4):
        for suffix, size in GUIDANCE_FIELDS:
            add(f"Jyusyo{number}{suffix}", size)
    add("RecordDelimiter", 2)

    assert cursor == YS_OFFICIAL_LENGTH
    return tuple(fields)


OFFICIAL_YS_LAYOUT = _official_layout()


def _put(record: bytearray, start: int, size: int, value: str) -> None:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    record[start : start + size] = encoded.ljust(size, b" ")


def build_ys_record(
    *,
    data_kubun: str = "1",
    key_overrides: dict[str, str] | None = None,
    guidance_prefix: str = "GUIDANCE",
) -> tuple[bytes, dict[str, str]]:
    values = {
        "RecordSpec": "YS",
        "DataKubun": data_kubun,
        "MakeDate": "20260816",
        "Year": "2026",
        "MonthDay": "0816",
        "JyoCD": "05",
        "Kaiji": "03",
        "Nichiji": "08",
        "YoubiCD": "7",
    }
    values.update(key_overrides or {})
    for number in range(1, 4):
        values.update(
            {
                f"Jyusyo{number}TokuNum": f"{1000 + number}",
                f"Jyusyo{number}Hondai": f"{guidance_prefix}{number}",
                f"Jyusyo{number}Ryakusyo10": f"SHORT10-{number}",
                f"Jyusyo{number}Ryakusyo6": f"SHORT6-{number}",
                f"Jyusyo{number}Ryakusyo3": f"S3-{number}",
                f"Jyusyo{number}Nkai": f"{10 + number:03d}",
                f"Jyusyo{number}GradeCD": chr(ord("A") + number - 1),
                f"Jyusyo{number}SyubetuCD": f"{10 + number}",
                f"Jyusyo{number}KigoCD": f"K{number:02d}",
                f"Jyusyo{number}JyuryoCD": str(number),
                f"Jyusyo{number}Kyori": f"{1600 + 200 * number:04d}",
                f"Jyusyo{number}TrackCD": f"{16 + number}",
            }
        )

    record = bytearray(b" " * YS_OFFICIAL_LENGTH)
    expected: dict[str, str] = {}
    for name, start, size in OFFICIAL_YS_LAYOUT:
        if name == "RecordDelimiter":
            record[start : start + size] = b"\r\n"
            expected[name] = ""
            continue
        _put(record, start, size, values[name])
        expected[name] = values[name]
    return bytes(record), expected


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_ys_record()[0])
    record[30:32] = b"\x81\x20"
    return bytes(record)


def _obsolete_native_schema() -> str:
    return """
        CREATE TABLE NL_YS (
            RecordSpec TEXT,
            DataKubun TEXT,
            MakeDate TEXT,
            Year INTEGER,
            MonthDay INTEGER,
            JyoCD TEXT,
            Kaiji INTEGER,
            Nichiji INTEGER,
            YoubiCD TEXT,
            Jyusyo1TokuNum INTEGER,
            Jyusyo1Hondai TEXT,
            Jyusyo1Ryakusyo10 TEXT,
            Jyusyo1Ryakusyo6 TEXT,
            Jyusyo1Ryakusyo3 TEXT,
            Jyusyo1Nkai INTEGER,
            Jyusyo1GradeCD TEXT,
            Jyusyo1SyubetuCD TEXT,
            Jyusyo1KigoCD TEXT,
            Jyusyo1JyuryoCD TEXT,
            Jyusyo1Kyori INTEGER,
            Jyusyo1TrackCD TEXT,
            RecordDelimiter TEXT,
            PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji)
        )
    """


def _keyless_standard_schema() -> str:
    return (
        JRAVAN_SCHEMAS["SCHEDULE"]
        .replace(
            "            Jyusyo3TrackCD                 VARCHAR(2)          ,",
            "            Jyusyo3TrackCD                 VARCHAR(2)           ",
        )
        .replace(
            "            PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji)\n",
            "",
        )
    )


def test_ys_parses_all_46_official_fields_at_gap_free_offsets() -> None:
    record, expected = build_ys_record()

    assert len(OFFICIAL_YS_LAYOUT) == 46
    assert OFFICIAL_YS_LAYOUT[0] == ("RecordSpec", 0, 2)
    assert OFFICIAL_YS_LAYOUT[-1] == ("RecordDelimiter", 380, 2)
    assert all(
        start + size == next_start
        for (_, start, size), (_, next_start, _) in pairwise(OFFICIAL_YS_LAYOUT)
    )

    row = YSParser().parse(record)

    assert row is not None
    assert YSParser.RECORD_LENGTH == YS_OFFICIAL_LENGTH
    assert row == expected
    assert [row[f"Jyusyo{i}Hondai"] for i in range(1, 4)] == [
        "GUIDANCE1",
        "GUIDANCE2",
        "GUIDANCE3",
    ]


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_ys_record()[0][:146], id="non-official-146"),
        pytest.param(build_ys_record()[0] + b" " * 42, id="non-official-424"),
        pytest.param(build_ys_record()[0][:-1], id="short-381"),
        pytest.param(build_ys_record()[0] + b" ", id="long-383"),
        pytest.param(b"XX" + build_ys_record()[0][2:], id="wrong-record-type"),
        pytest.param(build_ys_record()[0][:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_ys_rejects_non_official_record_boundaries(record: bytes) -> None:
    assert YSParser().parse(record) is None


def test_ys_schemas_and_metadata_match_the_complete_contract() -> None:
    parser_fields = {name for name, _, _ in OFFICIAL_YS_LAYOUT}

    assert set(get_table_column_types("NL_YS")) == parser_fields
    assert set(get_table_column_types("SCHEDULE")) == parser_fields - {"RecordDelimiter"}
    assert get_table_primary_key_columns("NL_YS") == YS_KEY
    assert get_table_primary_key_columns("SCHEDULE") == YS_KEY
    assert [column["name"] for column in TABLE_METADATA["NL_YS"]["columns"]] == list(
        get_table_column_types("NL_YS")
    )
    assert TABLE_METADATA["NL_YS"]["primary_key"] == YS_KEY
    assert "開催スケジュール" in TABLE_METADATA["NL_YS"]["description"]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_YS", False), ("SCHEDULE", True)),
)
def test_ys_round_trips_all_three_guidance_blocks(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        parsed = YSParser().parse(build_ys_record()[0])
        assert parsed is not None
        stats = importer_class(database, use_jravan_schema=use_jravan_schema).import_records(
            iter([parsed])
        )
        row = database.fetch_one(
            f"SELECT YoubiCD, Jyusyo1Hondai, Jyusyo2Hondai, Jyusyo3Hondai, "
            f"Jyusyo3TokuNum, Jyusyo3Kyori, Jyusyo3TrackCD FROM {table_name}"
        )

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert row is not None
    assert [row[f"Jyusyo{i}Hondai"] for i in range(1, 4)] == [
        "GUIDANCE1",
        "GUIDANCE2",
        "GUIDANCE3",
    ]
    assert str(row["Jyusyo3TokuNum"]) == "1003"
    assert str(row["Jyusyo3Kyori"]) == "2200"
    assert str(row["Jyusyo3TrackCD"]) == "19"


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_YS", False), ("SCHEDULE", True)),
)
def test_ys_status_upserts_cancellation_and_exact_deletion(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"status-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    plan = YSParser().parse(build_ys_record(guidance_prefix="PLAN")[0])
    immediate = YSParser().parse(build_ys_record(data_kubun="2", guidance_prefix="IMMEDIATE")[0])
    cancelled = YSParser().parse(build_ys_record(data_kubun="9", guidance_prefix="CANCELLED")[0])
    other = YSParser().parse(
        build_ys_record(
            data_kubun="3",
            key_overrides={"MonthDay": "0817"},
            guidance_prefix="OTHER",
        )[0]
    )
    delete = YSParser().parse(build_ys_record(data_kubun="0")[0])
    assert all(row is not None for row in (plan, immediate, cancelled, other, delete))

    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=use_jravan_schema)
        update_stats = importer.import_records(iter([plan, immediate, cancelled]))
        updated = database.fetch_all(
            f"SELECT DataKubun, Jyusyo1Hondai, Jyusyo3Hondai FROM {table_name}"
        )
        final_stats = importer.import_records(iter([other, delete]))
        rows = database.fetch_all(f"SELECT DataKubun, MonthDay, Jyusyo1Hondai FROM {table_name}")

    assert update_stats["records_imported"] == 3
    assert update_stats["records_failed"] == 0
    assert updated == [
        {
            "DataKubun": "9",
            "Jyusyo1Hondai": "CANCELLED1",
            "Jyusyo3Hondai": "CANCELLED3",
        }
    ]
    assert final_stats["records_imported"] == 2
    assert final_stats["records_failed"] == 0
    assert rows == [{"DataKubun": "3", "MonthDay": 817, "Jyusyo1Hondai": "OTHER1"}]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("invalid_record", "message"),
    (
        (
            build_ys_record(data_kubun="0", key_overrides={"MonthDay": ""})[0],
            "incomplete official key",
        ),
        (build_ys_record(data_kubun="4")[0], "unsupported DataKubun"),
    ),
    ids=("incomplete-delete-key", "unsupported-status"),
)
def test_invalid_ys_row_aborts_the_whole_batch_before_mutation(
    tmp_path,
    importer_class,
    invalid_record,
    message,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "invalid-row.db")})
    valid = YSParser().parse(build_ys_record()[0])
    invalid = YSParser().parse(invalid_record)
    assert valid is not None and invalid is not None

    with database:
        database.create_table("NL_YS", SCHEMAS["NL_YS"])
        with pytest.raises(SchemaMigrationError, match=message):
            importer_class(database).import_records(iter([valid, invalid]))

        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_YS")["count"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_ys_batches_only_consecutive_upserts_around_ordered_deletes(
    tmp_path,
    monkeypatch,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "ordered-batches.db")})
    first = YSParser().parse(build_ys_record(guidance_prefix="FIRST")[0])
    second = YSParser().parse(
        build_ys_record(
            key_overrides={"MonthDay": "0817"},
            guidance_prefix="SECOND",
        )[0]
    )
    delete_first = YSParser().parse(build_ys_record(data_kubun="0")[0])
    replacement = YSParser().parse(build_ys_record(data_kubun="2", guidance_prefix="LAST")[0])
    assert all(row is not None for row in (first, second, delete_first, replacement))

    with database:
        database.create_table("NL_YS", SCHEMAS["NL_YS"])
        original_insert_many = database.insert_many
        batch_sizes = []

        def record_batch(table_name, rows, use_replace=True):
            batch_sizes.append(len(rows))
            return original_insert_many(table_name, rows, use_replace=use_replace)

        monkeypatch.setattr(database, "insert_many", record_batch)
        stats = importer_class(database).import_records(
            iter([first, second, delete_first, replacement])
        )
        rows = database.fetch_all("SELECT MonthDay, Jyusyo1Hondai FROM NL_YS ORDER BY MonthDay")

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert batch_sizes == [2, 1]
    assert rows == [
        {"MonthDay": 816, "Jyusyo1Hondai": "LAST1"},
        {"MonthDay": 817, "Jyusyo1Hondai": "SECOND1"},
    ]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema", "obsolete_schema"),
    (
        pytest.param("NL_YS", False, _obsolete_native_schema(), id="native-partial"),
        pytest.param("SCHEDULE", True, _keyless_standard_schema(), id="standard-keyless"),
    ),
)
def test_obsolete_ys_storage_fails_closed_without_data_loss(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
    obsolete_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"obsolete-{table_name}.db")})
    with database:
        database.execute(obsolete_schema)
        database.execute(
            f"INSERT INTO {table_name} (Year, MonthDay, JyoCD, Kaiji, Nichiji) "
            "VALUES (2025, 101, '05', 1, 1)"
        )
        database.commit()

        parsed = YSParser().parse(build_ys_record()[0])
        assert parsed is not None
        with pytest.raises(SchemaMigrationError):
            importer_class(database, use_jravan_schema=use_jravan_schema).import_records(
                iter([parsed])
            )

        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 1


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_obsolete_standard_schedule_does_not_block_unrelated_standard_import(
    tmp_path,
    monkeypatch,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "unrelated-standard.db")})
    future_schedule_schema = """
        CREATE TABLE IF NOT EXISTS SCHEDULE (
            Year SMALLINT,
            MonthDay SMALLINT,
            JyoCD CHAR(2),
            Kaiji SMALLINT,
            Nichiji SMALLINT,
            PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji)
        )
    """
    unrelated = {
        "RecordSpec": "HN",
        "DataKubun": "1",
        "MakeDate": "20260816",
        "HansyokuNum": "1234567890",
        "Bamei": "UNRELATED",
    }

    with database:
        database.execute(JRAVAN_SCHEMAS["SCHEDULE"])
        database.execute(JRAVAN_SCHEMAS["HANSYOKU"])
        database.commit()
        monkeypatch.setitem(JRAVAN_SCHEMAS, "SCHEDULE", future_schedule_schema)

        stats = importer_class(database, use_jravan_schema=True).import_records(iter([unrelated]))

        assert stats["records_imported"] == 1
        assert stats["records_failed"] == 0
        assert database.fetch_one("SELECT HansyokuNum, Bamei FROM HANSYOKU") == {
            "HansyokuNum": "1234567890",
            "Bamei": "UNRELATED",
        }


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_ys_postgresql_native_and_standard_preserve_status_and_deletion(
    postgresql_db,
    importer_class,
) -> None:
    postgresql_db.execute(SCHEMAS["NL_YS"])
    postgresql_db.execute(JRAVAN_SCHEMAS["SCHEDULE"])
    postgresql_db.commit()

    rows = [
        YSParser().parse(build_ys_record()[0]),
        YSParser().parse(build_ys_record(data_kubun="9", guidance_prefix="CANCELLED")[0]),
        YSParser().parse(
            build_ys_record(
                data_kubun="3",
                key_overrides={"MonthDay": "0817"},
                guidance_prefix="OTHER",
            )[0]
        ),
        YSParser().parse(build_ys_record(data_kubun="0")[0]),
    ]
    assert all(row is not None for row in rows)

    native = importer_class(postgresql_db).import_records(iter(rows))
    standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(iter(rows))

    assert native["records_imported"] == standard["records_imported"] == 4
    assert native["records_failed"] == standard["records_failed"] == 0
    for table_name in ("NL_YS", "SCHEDULE"):
        assert (
            postgresql_db.fetch_one(f'SELECT COUNT(*) AS "count" FROM {table_name}')["count"] == 1
        )
        assert postgresql_db.fetch_one(
            'SELECT DataKubun AS "DataKubun", MonthDay AS "MonthDay", '
            'Jyusyo3Hondai AS "Jyusyo3Hondai" '
            f"FROM {table_name}"
        ) == {"DataKubun": "3", "MonthDay": 817, "Jyusyo3Hondai": "OTHER3"}
