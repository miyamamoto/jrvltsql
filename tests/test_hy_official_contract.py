"""HY parser and storage contract for the official current 123-byte layout."""

import os
from itertools import pairwise
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.hy_parser import HYParser


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


FIELDS = [
    ("RecordSpec", 1, 2, b"HY"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260817"),
    ("KettoNum", 12, 10, b"2026100001"),
    ("Bamei", 22, 36, _pad("公式馬名", 36)),
    ("Origin", 58, 64, _pad("公式仕様に基づく馬名の由来", 64)),
    ("RecordDelimiter", 122, 2, b"\r\n"),
]
EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
BUSINESS_FIELDS = set(EXPECTED) - {"RecordDelimiter"}


def build_record(
    *,
    data_kubun: str = "1",
    ketto_num: str = "2026100001",
    bamei: str = "公式馬名",
    origin: str = "公式仕様に基づく馬名の由来",
) -> bytes:
    values = {
        "DataKubun": _pad(data_kubun, 1),
        "KettoNum": _pad(ketto_num, 10),
        "Bamei": _pad(bamei, 36),
        "Origin": _pad(origin, 64),
    }
    record = bytearray()
    for name, position, width, default in FIELDS:
        value = values.get(name, default)
        assert len(record) == position - 1
        assert len(value) == width
        record += value
    assert len(record) == HYParser.RECORD_LENGTH == 123
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
    schema_name = f"jlt_hy_{uuid4().hex[:12]}"
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


def test_hy_layout_is_gap_free_and_reads_every_official_field() -> None:
    assert all(
        position + width == next_position
        for (_, position, width, _), (_, next_position, _, _) in pairwise(FIELDS)
    )

    parsed = HYParser().parse(build_record())

    assert parsed == EXPECTED


@pytest.mark.parametrize(
    "record",
    (
        build_record()[:-1],
        build_record() + b" ",
        b"XX" + build_record()[2:],
        build_record()[:-2] + b"  ",
        build_record(data_kubun="2"),
    ),
)
def test_hy_rejects_noncurrent_or_corrupt_records(record: bytes) -> None:
    assert HYParser().parse(record) is None


def test_hy_native_and_standard_schemas_match_current_business_fields() -> None:
    assert set(get_table_column_types("NL_HY")) == BUSINESS_FIELDS
    assert get_table_primary_key_columns("NL_HY") == ["KettoNum"]
    assert set(get_table_column_types("BAMEIORIGIN")) == BUSINESS_FIELDS
    assert get_table_primary_key_columns("BAMEIORIGIN") == ["KettoNum"]


def test_hy_standard_mapping_selects_bameiorigin_and_keeps_legacy_alias() -> None:
    assert JRAVAN_TO_JLTSQL["BAMEIORIGIN"] == "NL_HY"
    assert JRAVAN_TO_JLTSQL["MEANING"] == "NL_HY"
    assert JLTSQL_TO_JRAVAN["NL_HY"] == "BAMEIORIGIN"


@pytest.mark.parametrize(
    ("importer_class", "table_name", "use_jravan_schema"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            id=f"{importer_class.__name__}-{table_name}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_HY", False), ("BAMEIORIGIN", True))
    ],
)
def test_hy_round_trips_and_upserts_by_registration_number(
    tmp_path,
    importer_class,
    table_name: str,
    use_jravan_schema: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        first = HYParser().parse(build_record())
        updated = HYParser().parse(build_record(bamei="更新馬名", origin="更新後の馬名由来"))
        first_stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([first]))
        updated_stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([updated]))
        row = database.fetch_one(f"SELECT KettoNum, Bamei, Origin FROM {table_name}")
        row_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

    assert first_stats["records_imported"] == 1
    assert first_stats["records_failed"] == 0
    assert updated_stats["records_imported"] == 1
    assert updated_stats["records_failed"] == 0
    assert row_count == 1
    assert row == {
        "KettoNum": EXPECTED["KettoNum"],
        "Bamei": "更新馬名",
        "Origin": "更新後の馬名由来",
    }


@pytest.mark.parametrize(
    ("importer_class", "table_name", "use_jravan_schema"),
    [
        pytest.param(
            importer_class,
            table_name,
            standard,
            id=f"{importer_class.__name__}-{table_name}",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_HY", False), ("BAMEIORIGIN", True))
    ],
)
def test_hy_deletion_removes_the_registration_number_in_provider_order(
    tmp_path,
    importer_class,
    table_name: str,
    use_jravan_schema: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        created = HYParser().parse(build_record())
        deleted = HYParser().parse(build_record(data_kubun="0", bamei="", origin=""))
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([created, deleted]))
        row_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

    assert stats["records_imported"] == 2
    assert stats["records_failed"] == 0
    assert row_count == 0


OBSOLETE_NATIVE_SCHEMA = """
    CREATE TABLE NL_HY (
        RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT,
        Bamei TEXT, Field5 TEXT, Field6 TEXT, Field7 TEXT,
        PRIMARY KEY (Bamei)
    )
"""


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hy_native_schema_change_fails_closed_without_row_loss(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-native.db")})
    with database:
        database.execute(OBSOLETE_NATIVE_SCHEMA)
        database.execute(
            "INSERT INTO NL_HY VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "HY",
                "1",
                "20000101",
                "2000100001",
                "legacy-name",
                "legacy-origin",
                "",
            ),
        )
        database.commit()

        assert SchemaManager(database).create_table("NL_HY") is False
        with pytest.raises(SchemaMigrationError, match="Schema verification failed"):
            importer_class(database).import_records(iter([HYParser().parse(build_record())]))
        row = database.fetch_one("SELECT * FROM NL_HY")

    assert row == {
        "RecordSpec": "HY",
        "DataKubun": "1",
        "MakeDate": "20000101",
        "Bamei": "2000100001",
        "Field5": "legacy-name",
        "Field6": "legacy-origin",
        "Field7": "",
    }


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hy_native_wrong_primary_key_is_refused_without_row_loss(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wrong-native-key.db")})
    with database:
        database.execute(
            "CREATE TABLE NL_HY ("
            "RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, KettoNum TEXT, "
            "Bamei TEXT, Origin TEXT, PRIMARY KEY (Bamei))"
        )
        database.execute(
            "INSERT INTO NL_HY VALUES (?, ?, ?, ?, ?, ?)",
            ("HY", "1", "20000101", "2000100001", "preserve-me", "legacy-origin"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database).import_records(iter([HYParser().parse(build_record())]))
        rows = database.fetch_all("SELECT * FROM NL_HY")

    assert rows == [
        {
            "RecordSpec": "HY",
            "DataKubun": "1",
            "MakeDate": "20000101",
            "KettoNum": "2000100001",
            "Bamei": "preserve-me",
            "Origin": "legacy-origin",
        }
    ]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hy_standard_keyless_schema_is_refused_without_row_loss(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "obsolete-standard.db")})
    with database:
        database.execute(
            "CREATE TABLE BAMEIORIGIN ("
            "RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, Bamei TEXT)"
        )
        database.execute(
            "INSERT INTO BAMEIORIGIN VALUES (?, ?, ?, ?)",
            ("HY", "1", "20000101", "preserve-me"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([HYParser().parse(build_record())])
            )
        rows = database.fetch_all("SELECT * FROM BAMEIORIGIN")

    assert rows == [
        {
            "RecordSpec": "HY",
            "DataKubun": "1",
            "MakeDate": "20000101",
            "Bamei": "preserve-me",
        }
    ]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_hy_legacy_meaning_alias_is_refused_without_row_loss(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-alias.db")})
    with database:
        database.execute("CREATE TABLE MEANING (Bamei TEXT PRIMARY KEY)")
        database.execute("INSERT INTO MEANING VALUES (?)", ("preserve-alias",))
        database.commit()

        with pytest.raises(
            SchemaMigrationError,
            match=r"MEANING.*BAMEIORIGIN|BAMEIORIGIN.*MEANING",
        ):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([HYParser().parse(build_record())])
            )
        rows = database.fetch_all("SELECT * FROM MEANING")

    assert rows == [{"Bamei": "preserve-alias"}]


def test_hy_postgresql_native_and_standard_upsert(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_HY"])
    postgresql_db.execute(JRAVAN_SCHEMAS["BAMEIORIGIN"])
    postgresql_db.commit()

    updates = (
        (DataImporter, "PostgreSQL馬名1", "PostgreSQL由来1"),
        (OptimizedDataImporter, "PostgreSQL馬名2", "PostgreSQL由来2"),
    )
    for importer_class, bamei, origin in updates:
        record = HYParser().parse(build_record(bamei=bamei, origin=origin))
        native = importer_class(postgresql_db).import_records(iter([record]))
        standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(
            iter([record])
        )
        assert native["records_imported"] == 1
        assert native["records_failed"] == 0
        assert standard["records_imported"] == 1
        assert standard["records_failed"] == 0

    native_row = postgresql_db.fetch_one(
        "SELECT KettoNum AS ketto_num, Bamei AS bamei, Origin AS origin FROM NL_HY"
    )
    standard_row = postgresql_db.fetch_one(
        "SELECT KettoNum AS ketto_num, Bamei AS bamei, Origin AS origin " "FROM BAMEIORIGIN"
    )
    assert dict(native_row) == {
        "ketto_num": EXPECTED["KettoNum"],
        "bamei": "PostgreSQL馬名2",
        "origin": "PostgreSQL由来2",
    }
    assert dict(standard_row) == dict(native_row)

    deleted = HYParser().parse(build_record(data_kubun="0", bamei="", origin=""))
    for importer_class in (DataImporter, OptimizedDataImporter):
        for table_name, standard in (("NL_HY", False), ("BAMEIORIGIN", True)):
            created = HYParser().parse(build_record())
            importer = importer_class(postgresql_db, use_jravan_schema=standard)
            created_stats = importer.import_records(iter([created]))
            deleted_stats = importer.import_records(iter([deleted]))
            row_count = postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")[
                "count"
            ]
            assert created_stats["records_imported"] == 1
            assert created_stats["records_failed"] == 0
            assert deleted_stats["records_imported"] == 1
            assert deleted_stats["records_failed"] == 0
            assert row_count == 0
