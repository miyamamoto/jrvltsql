"""BT semantic and storage contract for the official current 6,889-byte layout."""

import os
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError, verify_table_schema
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter, ImporterError
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.bt_parser import BTParser

BUSINESS_FIELDS = {
    "RecordSpec",
    "DataKubun",
    "MakeDate",
    "HansyokuNum",
    "KeitoId",
    "KeitoName",
    "KeitoEx",
}

CANONICAL_KEITO_SCHEMA = """
    CREATE TABLE IF NOT EXISTS KEITO (
        RecordSpec CHAR(2),
        DataKubun CHAR(1),
        MakeDate DATE,
        HansyokuNum VARCHAR(10),
        KeitoId VARCHAR(30),
        KeitoName VARCHAR(36),
        KeitoEx VARCHAR(6800),
        PRIMARY KEY (HansyokuNum)
    )
"""


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


def build_record(
    *,
    data_kubun: str = "1",
    hansyoku_num: str = "0123456789",
    keito_id: str = "CURRENT-KEITO-ID",
    keito_name: str = "現行系統名",
    keito_ex: str = "現行公式仕様の系統説明",
) -> bytes:
    record = b"".join(
        (
            b"BT",
            _pad(data_kubun, 1),
            b"20260817",
            _pad(hansyoku_num, 10),
            _pad(keito_id, 30),
            _pad(keito_name, 36),
            _pad(keito_ex, 6800),
            b"\r\n",
        )
    )
    assert len(record) == BTParser.RECORD_LENGTH == 6889
    return record


def parsed_record(**kwargs) -> dict:
    return BTParser().parse(build_record(**kwargs))


def _race_schema_without_youbi(*, narrow_record_spec: bool = False) -> str:
    schema = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    if narrow_record_spec:
        schema = schema.replace(
            "            RecordSpec                     CHAR(2)             ,",
            "            RecordSpec                     CHAR(1)             ,",
        )
    return schema


def _record_schema_without_hondai(*, narrow_record_spec: bool = False) -> str:
    schema = JRAVAN_SCHEMAS["RECORD"].replace(
        "            Hondai                         VARCHAR(60)         ,  -- 文字列(60)\n",
        "",
    )
    if narrow_record_spec:
        schema = schema.replace(
            "            RecordSpec                     CHAR(2)             ,",
            "            RecordSpec                     CHAR(1)             ,",
        )
    return schema


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
    schema_name = f"jlt_bt_{uuid4().hex[:12]}"
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


@pytest.mark.parametrize("data_kubun", ("0", "1", "2"))
def test_bt_accepts_every_official_data_kubun(data_kubun: str) -> None:
    assert parsed_record(data_kubun=data_kubun)["DataKubun"] == data_kubun


@pytest.mark.parametrize("data_kubun", ("", "7", "9"))
def test_bt_rejects_undefined_data_kubun(data_kubun: str) -> None:
    with pytest.raises(ValueError, match="DataKubun"):
        parsed_record(data_kubun=data_kubun)


def test_bt_standard_mapping_and_schema_are_complete() -> None:
    assert JRAVAN_TO_JLTSQL["BLOOD"] == "NL_BT"
    assert JRAVAN_TO_JLTSQL["KEITO"] == "NL_BT"
    assert JLTSQL_TO_JRAVAN["NL_BT"] == "KEITO"
    assert set(get_table_column_types("KEITO")) == BUSINESS_FIELDS
    assert get_table_primary_key_columns("KEITO") == ["HansyokuNum"]
    database = SQLiteDatabase({"path": ":memory:"})
    with database:
        database.execute(JRAVAN_SCHEMAS["KEITO"])
        verify_table_schema(database, "KEITO", CANONICAL_KEITO_SCHEMA)


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard"),
    [
        pytest.param(
            importer_class, table_name, standard, id=f"{importer_class.__name__}-{table_name}"
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_BT", False), ("KEITO", True))
    ],
)
def test_bt_round_trips_and_upserts_every_official_business_field(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"roundtrip-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        first = importer_class(database, use_jravan_schema=standard).import_records(
            iter([parsed_record(keito_name="登録系統", keito_ex="登録時説明")])
        )
        updated = importer_class(database, use_jravan_schema=standard).import_records(
            iter(
                [
                    parsed_record(
                        data_kubun="2",
                        keito_id="UPDATED-KEITO-ID",
                        keito_name="更新系統",
                        keito_ex="X" * 6800,
                    )
                ]
            )
        )
        row = database.fetch_one(
            f"SELECT RecordSpec, DataKubun, MakeDate, HansyokuNum, KeitoId, "
            f"KeitoName, KeitoEx FROM {table_name}"
        )
        count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

    assert first["records_imported"] == 1
    assert first["records_failed"] == 0
    assert updated["records_imported"] == 1
    assert updated["records_failed"] == 0
    assert count == 1
    assert row == {
        "RecordSpec": "BT",
        "DataKubun": "2",
        "MakeDate": 20260817 if standard else "20260817",
        "HansyokuNum": "0123456789",
        "KeitoId": "UPDATED-KEITO-ID",
        "KeitoName": "更新系統",
        "KeitoEx": "X" * 6800,
    }


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard"),
    [
        pytest.param(
            importer_class, table_name, standard, id=f"{importer_class.__name__}-{table_name}"
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_BT", False), ("KEITO", True))
    ],
)
def test_bt_delete_is_physical_and_preserves_provider_order(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        deleted = importer.import_records(
            iter(
                [
                    parsed_record(keito_name="登録系統"),
                    parsed_record(data_kubun="2", keito_name="更新系統"),
                    parsed_record(data_kubun="0", keito_id="", keito_name="", keito_ex=""),
                ]
            )
        )
        count_after_delete = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")[
            "count"
        ]
        recreated = importer.import_records(
            iter([parsed_record(keito_name="再登録系統", keito_ex="再登録説明")])
        )
        row = database.fetch_one(
            f"SELECT DataKubun, HansyokuNum, KeitoName, KeitoEx FROM {table_name}"
        )

    assert deleted["records_imported"] == 3
    assert deleted["records_failed"] == 0
    assert count_after_delete == 0
    assert recreated["records_imported"] == 1
    assert recreated["records_failed"] == 0
    assert row == {
        "DataKubun": "1",
        "HansyokuNum": "0123456789",
        "KeitoName": "再登録系統",
        "KeitoEx": "再登録説明",
    }


@pytest.mark.parametrize(
    ("importer_class", "table_name", "standard"),
    [
        pytest.param(
            importer_class, table_name, standard, id=f"{importer_class.__name__}-{table_name}"
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_BT", False), ("KEITO", True))
    ],
)
def test_bt_delete_with_incomplete_key_fails_without_row_loss(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"missing-key-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        importer.import_records(iter([parsed_record(keito_name="保持対象")]))

        with pytest.raises(ImporterError, match="incomplete key"):
            importer.import_records(
                iter(
                    [
                        parsed_record(
                            data_kubun="0",
                            hansyoku_num="",
                            keito_id="",
                            keito_name="",
                            keito_ex="",
                        )
                    ]
                )
            )
        rows = database.fetch_all(f"SELECT HansyokuNum, KeitoName FROM {table_name}")

    assert rows == [{"HansyokuNum": "0123456789", "KeitoName": "保持対象"}]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_bt_partial_keyless_keito_is_refused_without_schema_or_row_mutation(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "partial-keito.db")})
    with database:
        database.execute(_race_schema_without_youbi())
        database.execute(
            "CREATE TABLE KEITO (RecordSpec TEXT, DataKubun TEXT, MakeDate TEXT, "
            "KeitoId TEXT, KeitoName TEXT)"
        )
        database.execute(
            "INSERT INTO KEITO VALUES (?, ?, ?, ?, ?)",
            ("BT", "1", "20000101", "legacy-id", "preserve-me"),
        )
        database.commit()
        before_columns = database.fetch_all("PRAGMA table_info(KEITO)")
        before_race_columns = database.fetch_all("PRAGMA table_info(RACE)")

        with pytest.raises(SchemaMigrationError, match="Schema verification failed"):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))

        after_columns = database.fetch_all("PRAGMA table_info(KEITO)")
        after_race_columns = database.fetch_all("PRAGMA table_info(RACE)")
        rows = database.fetch_all("SELECT * FROM KEITO")

    assert after_columns == before_columns
    assert after_race_columns == before_race_columns
    assert rows == [
        {
            "RecordSpec": "BT",
            "DataKubun": "1",
            "MakeDate": "20000101",
            "KeitoId": "legacy-id",
            "KeitoName": "preserve-me",
        }
    ]


@pytest.mark.parametrize(
    ("column_definitions", "narrow_columns"),
    (
        pytest.param(
            "RecordSpec CHAR(1), DataKubun CHAR(1), MakeDate DATE, "
            "HansyokuNum VARCHAR(8), KeitoId VARCHAR(29), KeitoName VARCHAR(35), "
            "KeitoEx VARCHAR(6799)",
            ("RecordSpec", "HansyokuNum", "KeitoId", "KeitoName", "KeitoEx"),
            id="standard-spellings",
        ),
        *(
            pytest.param(
                "RecordSpec CHAR(2), DataKubun CHAR(1), MakeDate DATE, "
                f"HansyokuNum {declared_type}, KeitoId VARCHAR(30), "
                "KeitoName VARCHAR(36), KeitoEx VARCHAR(6800)",
                ("HansyokuNum",),
                id=declared_type.lower().replace(" ", "-"),
            )
            for declared_type in (
                "NVARCHAR(8)",
                "NCHAR(8)",
                "CHAR VARYING(8)",
                "VARCHAR2(8)",
            )
        ),
    ),
)
def test_schema_verifier_rejects_narrow_bt_text_columns(
    column_definitions: str,
    narrow_columns: tuple[str, ...],
) -> None:
    database = SQLiteDatabase({"path": ":memory:"})
    with database:
        database.execute(f"CREATE TABLE KEITO ({column_definitions}, PRIMARY KEY (HansyokuNum))")
        with pytest.raises(SchemaMigrationError, match="column capacities") as error:
            verify_table_schema(database, "KEITO", CANONICAL_KEITO_SCHEMA)

    assert all(name.lower() in str(error.value).lower() for name in narrow_columns)


def test_schema_verifier_accepts_exact_or_unbounded_bt_text_columns() -> None:
    database = SQLiteDatabase({"path": ":memory:"})
    with database:
        database.execute(
            "CREATE TABLE KEITO (RecordSpec CHAR(2), DataKubun TEXT, MakeDate DATE, "
            "HansyokuNum VARCHAR(10), KeitoId TEXT, KeitoName VARCHAR(40), "
            "KeitoEx TEXT, PRIMARY KEY (HansyokuNum))"
        )
        verify_table_schema(database, "KEITO", CANONICAL_KEITO_SCHEMA)


@pytest.mark.parametrize(
    ("importer_class", "auto_commit", "single_record"),
    [
        pytest.param(
            importer_class,
            auto_commit,
            False,
            id=f"{importer_class.__name__}-{auto_commit}-batch",
        )
        for importer_class in (DataImporter, OptimizedDataImporter)
        for auto_commit in (True, False)
    ]
    + [
        pytest.param(
            DataImporter,
            auto_commit,
            True,
            id=f"DataImporter-{auto_commit}-single",
        )
        for auto_commit in (True, False)
    ],
)
@pytest.mark.parametrize(
    ("table_name", "schema_sql"),
    (
        pytest.param(
            "RACE",
            _race_schema_without_youbi(narrow_record_spec=True),
            id="ordinary-table",
        ),
        pytest.param(
            "RECORD",
            _record_schema_without_hondai(narrow_record_spec=True),
            id="ordered-master",
        ),
    ),
)
def test_standard_preflight_rejects_before_any_additive_schema_mutation(
    tmp_path,
    importer_class,
    auto_commit: bool,
    single_record: bool,
    table_name: str,
    schema_sql: str,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "mixed-schema.db")})
    with database:
        database.execute(schema_sql)
        database.execute(CANONICAL_KEITO_SCHEMA)
        database.commit()
        before_columns = database.fetch_all(f'PRAGMA table_info("{table_name}")')
        before_sql = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        before_keito_rows = database.fetch_all("SELECT * FROM KEITO")

        with pytest.raises(SchemaMigrationError, match="column capacities"):
            importer = importer_class(database, use_jravan_schema=True)
            if single_record:
                importer.import_single_record(parsed_record(), auto_commit=auto_commit)
            else:
                importer.import_records(iter(()), auto_commit=auto_commit)

        after_columns = database.fetch_all(f'PRAGMA table_info("{table_name}")')
        after_sql = database.fetch_one(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        after_keito_rows = database.fetch_all("SELECT * FROM KEITO")

    assert after_columns == before_columns
    assert after_sql == before_sql
    assert after_keito_rows == before_keito_rows


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_bt_legacy_blood_only_storage_is_refused_without_row_loss(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-blood.db")})
    with database:
        database.execute(_race_schema_without_youbi())
        database.execute(CANONICAL_KEITO_SCHEMA.replace("KEITO", "BLOOD"))
        database.execute(
            "INSERT INTO BLOOD VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("BT", "1", "20000101", "12345678", "legacy-id", "legacy", "preserve"),
        )
        database.commit()
        before_race_columns = database.fetch_all("PRAGMA table_info(RACE)")

        with pytest.raises(
            SchemaMigrationError,
            match=r"BLOOD.*KEITO|KEITO.*BLOOD",
        ):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        rows = database.fetch_all("SELECT HansyokuNum, KeitoEx FROM BLOOD")
        after_race_columns = database.fetch_all("PRAGMA table_info(RACE)")

    assert rows == [{"HansyokuNum": "12345678", "KeitoEx": "preserve"}]
    assert after_race_columns == before_race_columns


def test_bt_postgresql_roundtrip_delete_and_narrow_schema_rejection(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_BT"])
    postgresql_db.execute(JRAVAN_SCHEMAS["KEITO"])
    postgresql_db.commit()

    for importer_class in (DataImporter, OptimizedDataImporter):
        for table_name, standard in (("NL_BT", False), ("KEITO", True)):
            importer = importer_class(postgresql_db, use_jravan_schema=standard)
            stored = importer.import_records(
                iter([parsed_record(keito_name="PostgreSQL系統", keito_ex="P" * 6800)])
            )
            row = postgresql_db.fetch_one(
                f"SELECT HansyokuNum AS hansyoku_num, KeitoName AS keito_name, "
                f"length(KeitoEx) AS explanation_length FROM {table_name}"
            )
            assert stored["records_imported"] == 1
            assert dict(row) == {
                "hansyoku_num": "0123456789",
                "keito_name": "PostgreSQL系統",
                "explanation_length": 6800,
            }

            deleted = importer.import_records(
                iter(
                    [
                        parsed_record(
                            data_kubun="0",
                            keito_id="",
                            keito_name="",
                            keito_ex="",
                        )
                    ]
                )
            )
            assert deleted["records_imported"] == 1
            assert (
                postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0
            )

    postgresql_db.execute("DROP TABLE KEITO")
    postgresql_db.execute(
        "CREATE TABLE KEITO (RecordSpec CHAR(2), DataKubun CHAR(1), MakeDate DATE, "
        "HansyokuNum VARCHAR(8), KeitoId VARCHAR(30), KeitoName VARCHAR(36), "
        "KeitoEx VARCHAR(6800), PRIMARY KEY (HansyokuNum))"
    )
    postgresql_db.execute(
        "INSERT INTO KEITO VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("BT", "1", "20000101", "12345678", "legacy-id", "legacy", "preserve"),
    )
    postgresql_db.commit()

    with pytest.raises(SchemaMigrationError, match="column capacities"):
        DataImporter(postgresql_db, use_jravan_schema=True).import_records(iter([parsed_record()]))
    assert dict(
        postgresql_db.fetch_one(
            "SELECT HansyokuNum AS hansyoku_num, KeitoEx AS keito_ex FROM KEITO"
        )
    ) == {"hansyoku_num": "12345678", "keito_ex": "preserve"}

    postgresql_db.execute("DROP TABLE KEITO")
    column_query = (
        "SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type "
        "FROM pg_attribute a WHERE a.attrelid = to_regclass(?) "
        "AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"
    )
    for table_name, schema_sql in (
        ("RACE", _race_schema_without_youbi(narrow_record_spec=True)),
        ("RECORD", _record_schema_without_hondai(narrow_record_spec=True)),
    ):
        postgresql_db.execute(schema_sql)
        postgresql_db.commit()
        before_columns = postgresql_db.fetch_all(column_query, (table_name.lower(),))

        for importer_class, auto_commit in (
            (DataImporter, True),
            (OptimizedDataImporter, False),
        ):
            with pytest.raises(SchemaMigrationError, match="column capacities"):
                importer_class(postgresql_db, use_jravan_schema=True).import_records(
                    iter(()),
                    auto_commit=auto_commit,
                )
            after_columns = postgresql_db.fetch_all(column_query, (table_name.lower(),))
            assert after_columns == before_columns
            postgresql_db.rollback()

        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.commit()
