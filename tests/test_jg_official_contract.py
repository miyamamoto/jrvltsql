"""JG parser and storage contract for the official 80-byte layout."""

import os
from itertools import pairwise
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import (
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.jg_parser import JGParser


def _pad(value: str, width: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= width
    return encoded.ljust(width, b" ")


FIELDS = (
    ("RecordSpec", 1, 2, b"JG"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260817"),
    ("Year", 12, 4, b"2026"),
    ("MonthDay", 16, 4, b"0817"),
    ("JyoCD", 20, 2, b"05"),
    ("Kaiji", 22, 2, b"03"),
    ("Nichiji", 24, 2, b"04"),
    ("RaceNum", 26, 2, b"00"),
    ("KettoNum", 28, 10, b"2026100001"),
    ("Bamei", 38, 36, _pad("公式除外馬", 36)),
    ("Num", 74, 3, b"001"),
    ("SyussoKubun", 77, 1, b"1"),
    ("JyogaiStateKubun", 78, 1, b"0"),
    ("RecordDelimiter", 79, 2, b"\r\n"),
)
EXPECTED = {name: value.decode("cp932").strip() for name, _, _, value in FIELDS}
NATIVE_FIELDS = set(EXPECTED)
STANDARD_FIELDS = NATIVE_FIELDS - {"RecordDelimiter", "Num", "SyussoKubun", "JyogaiStateKubun"} | {
    "ShutsubaTohyoJun",
    "ShussoKubun",
    "JogaiJotaiKubun",
}
NATIVE_KEY = [
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "KettoNum",
    "Num",
]
STANDARD_KEY = [*NATIVE_KEY[:-1], "ShutsubaTohyoJun"]


def build_record(
    *,
    data_kubun: str = "1",
    make_date: str = "20260817",
    year: str = "2026",
    month_day: str = "0817",
    jyo_cd: str = "05",
    kaiji: str = "03",
    nichiji: str = "04",
    race_num: str = "00",
    ketto_num: str = "2026100001",
    bamei: str = "公式除外馬",
    num: str = "001",
    syusso_kubun: str = "1",
    jyogai_state_kubun: str = "0",
) -> bytes:
    values = {
        "DataKubun": _pad(data_kubun, 1),
        "MakeDate": _pad(make_date, 8),
        "Year": _pad(year, 4),
        "MonthDay": _pad(month_day, 4),
        "JyoCD": _pad(jyo_cd, 2),
        "Kaiji": _pad(kaiji, 2),
        "Nichiji": _pad(nichiji, 2),
        "RaceNum": _pad(race_num, 2),
        "KettoNum": _pad(ketto_num, 10),
        "Bamei": _pad(bamei, 36),
        "Num": _pad(num, 3),
        "SyussoKubun": _pad(syusso_kubun, 1),
        "JyogaiStateKubun": _pad(jyogai_state_kubun, 1),
    }
    record = bytearray()
    for name, position, width, default in FIELDS:
        value = values.get(name, default)
        assert len(record) == position - 1
        assert len(value) == width
        record += value
    assert len(record) == JGParser.RECORD_LENGTH == 80
    return bytes(record)


def parsed_record(**kwargs) -> dict:
    record = JGParser().parse(build_record(**kwargs))
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
    schema_name = f"jlt_jg_{uuid4().hex[:12]}"
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


def test_jg_layout_is_gap_free_and_reads_every_official_field() -> None:
    assert all(
        position + width == next_position
        for (_, position, width, _), (_, next_position, _, _) in pairwise(FIELDS)
    )
    assert JGParser().parse(build_record()) == EXPECTED


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
        build_record(year="20A6"),
        pytest.param(build_record(jyo_cd="@5"), id="invalid-jyo-code"),
        build_record(num="A01"),
        build_record(syusso_kubun="8"),
        build_record(jyogai_state_kubun="8"),
    ),
)
def test_jg_rejects_noncurrent_or_corrupt_records(record: bytes) -> None:
    assert JGParser().parse(record) is None


def test_jg_delete_record_preserves_only_the_official_key() -> None:
    deleted = JGParser().parse(
        build_record(
            data_kubun="0",
            bamei="",
            syusso_kubun="",
            jyogai_state_kubun="",
        )
    )
    assert deleted is not None
    assert deleted["DataKubun"] == "0"
    assert [deleted[name] for name in NATIVE_KEY] == [
        "2026",
        "0817",
        "05",
        "03",
        "04",
        "00",
        "2026100001",
        "001",
    ]


def test_jg_native_and_standard_schemas_match_the_official_key() -> None:
    assert set(get_table_column_types("NL_JG")) == NATIVE_FIELDS
    assert get_table_primary_key_columns("NL_JG") == NATIVE_KEY
    assert set(get_table_column_types("JOGAIBA")) == STANDARD_FIELDS
    assert get_table_primary_key_columns("JOGAIBA") == STANDARD_KEY


def test_jg_standard_mapping_selects_jogaiba_and_keeps_legacy_lookup() -> None:
    assert JRAVAN_TO_JLTSQL["WEIGHT_CHANGE"] == "NL_JG"
    assert JRAVAN_TO_JLTSQL["JOGAIBA"] == "NL_JG"
    assert JLTSQL_TO_JRAVAN["NL_JG"] == "JOGAIBA"


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
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True))
    ],
)
def test_jg_same_horse_revotes_coexist_and_one_key_upserts(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"revote-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    num_column = "ShutsubaTohyoJun" if standard else "Num"
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        first = importer.import_records(
            iter(
                [
                    parsed_record(num="001", bamei="初回投票馬"),
                    parsed_record(num="002", bamei="再投票馬", syusso_kubun="4"),
                ]
            )
        )
        rows_before_update = database.fetch_all(
            f"SELECT {num_column} AS num, Bamei FROM {table_name} ORDER BY {num_column}"
        )
        updated = importer.import_records(iter([parsed_record(num="001", bamei="初回投票更新")]))
        rows_after_update = database.fetch_all(
            f"SELECT {num_column} AS num, Bamei FROM {table_name} ORDER BY {num_column}"
        )

    expected_before = [
        {"num": 1 if standard else "001", "Bamei": "初回投票馬"},
        {"num": 2 if standard else "002", "Bamei": "再投票馬"},
    ]
    expected_after = [
        {"num": 1 if standard else "001", "Bamei": "初回投票更新"},
        {"num": 2 if standard else "002", "Bamei": "再投票馬"},
    ]
    assert first["records_imported"] == 2
    assert first["records_failed"] == 0
    assert first["batches_processed"] == 1
    assert updated["records_imported"] == 1
    assert updated["records_failed"] == 0
    assert rows_before_update == expected_before
    assert rows_after_update == expected_after


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
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True))
        for auto_commit in (True, False)
    ],
)
def test_jg_delete_is_exact_and_preserves_provider_order(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    num_column = "ShutsubaTohyoJun" if standard else "Num"
    with database:
        database.create_table(table_name, schema)
        stats = importer_class(database, use_jravan_schema=standard).import_records(
            iter(
                [
                    parsed_record(num="001", bamei="保持対象"),
                    parsed_record(num="002", bamei="削除対象", syusso_kubun="4"),
                    parsed_record(
                        data_kubun="0",
                        num="002",
                        bamei="",
                        syusso_kubun="",
                        jyogai_state_kubun="",
                    ),
                ]
            ),
            auto_commit=auto_commit,
        )
        rows = database.fetch_all(f"SELECT DataKubun, {num_column} AS num, Bamei FROM {table_name}")

    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0
    assert rows == [{"DataKubun": "1", "num": 1 if standard else "001", "Bamei": "保持対象"}]


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
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True))
    ],
)
def test_jg_direct_invalid_status_or_incomplete_delete_cannot_mutate_rows(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"invalid-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        importer = importer_class(database, use_jravan_schema=standard)
        importer.import_records(iter([parsed_record(bamei="保持対象")]))

        conflicting_record_type = parsed_record()
        conflicting_record_type["レコード種別ID"] = "JG"
        conflicting_record_type["RecordSpec"] = "RA"
        with pytest.raises(SchemaMigrationError, match="record-type.*alias"):
            importer.import_records(iter([conflicting_record_type]))

        legacy_headers = parsed_record(num="003", bamei="legacy header")
        legacy_headers["headRecordSpec"] = legacy_headers.pop("RecordSpec")
        legacy_headers["headDataKubun"] = legacy_headers.pop("DataKubun")
        assert importer.import_records(iter([legacy_headers]))["records_imported"] == 1

        same_aliases = parsed_record(num="004", bamei="same aliases")
        same_aliases["headRecordSpec"] = "JG"
        same_aliases["レコード種別ID"] = "JG"
        same_aliases["headDataKubun"] = "1"
        assert importer.import_records(iter([same_aliases]))["records_imported"] == 1

        if standard:
            canonical_only = parsed_record(num="005", bamei="canonical aliases")
            canonical_only["ShutsubaTohyoJun"] = canonical_only.pop("Num")
            canonical_only["ShussoKubun"] = canonical_only.pop("SyussoKubun")
            canonical_only["JogaiJotaiKubun"] = canonical_only.pop("JyogaiStateKubun")
            assert importer.import_records(iter([canonical_only]))["records_imported"] == 1
            assert database.fetch_one(
                "SELECT ShutsubaTohyoJun, ShussoKubun, JogaiJotaiKubun "
                "FROM JOGAIBA WHERE ShutsubaTohyoJun = ?",
                (5,),
            ) == {
                "ShutsubaTohyoJun": 5,
                "ShussoKubun": "1",
                "JogaiJotaiKubun": "0",
            }

        num_column = "ShutsubaTohyoJun" if standard else "Num"
        assert database.fetch_one(
            f"SELECT RecordSpec, DataKubun FROM {table_name} WHERE {num_column} = ?",
            (3 if standard else "003",),
        ) == {"RecordSpec": "JG", "DataKubun": "1"}
        before = database.fetch_all(f"SELECT * FROM {table_name}")

        missing_status = parsed_record()
        missing_status.pop("DataKubun")
        with pytest.raises(SchemaMigrationError, match="DataKubun.*required"):
            importer.import_records(iter([missing_status]))

        blank_status = parsed_record()
        blank_status["DataKubun"] = ""
        with pytest.raises(SchemaMigrationError, match="DataKubun.*required"):
            importer.import_records(iter([blank_status]))

        conflicting_status = parsed_record()
        conflicting_status["headDataKubun"] = "0"
        with pytest.raises(SchemaMigrationError, match="conflicting DataKubun"):
            importer.import_records(iter([conflicting_status]))

        invalid = parsed_record()
        invalid["DataKubun"] = "8"
        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            importer.import_records(iter([invalid]))

        for field_name, invalid_value in (
            ("JyoCD", "@5"),
            ("Num", "A01"),
            ("SyussoKubun", "8"),
            ("JyogaiStateKubun", "8"),
        ):
            invalid_code = parsed_record()
            invalid_code[field_name] = invalid_value
            with pytest.raises(SchemaMigrationError, match=field_name):
                importer.import_records(iter([invalid_code]))

        incomplete = parsed_record(data_kubun="0", bamei="")
        incomplete["KettoNum"] = ""
        with pytest.raises(SchemaMigrationError, match="incomplete.*key|key.*incomplete"):
            importer.import_records(iter([incomplete]))

        if standard:
            conflicting_alias = parsed_record()
            conflicting_alias["ShutsubaTohyoJun"] = "999"
            with pytest.raises(SchemaMigrationError, match="conflicting.*JG.*alias"):
                importer.import_records(iter([conflicting_alias]))
        after = database.fetch_all(f"SELECT * FROM {table_name}")

    assert after == before


def _obsolete_schema(table_name: str, *, standard: bool) -> str:
    schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
    key = STANDARD_KEY if standard else NATIVE_KEY
    obsolete_key = ", ".join(key[:-1])
    return schema.replace(
        f"PRIMARY KEY ({', '.join(key)})",
        f"PRIMARY KEY ({obsolete_key})",
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
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True))
        for auto_commit in (True, False)
    ],
)
def test_jg_obsolete_seven_column_key_is_refused_before_mutation(
    tmp_path,
    importer_class,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"obsolete-{table_name}.db")})
    with database:
        database.execute(_obsolete_schema(table_name, standard=standard))
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


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_jg_legacy_weight_change_only_storage_is_refused_without_row_loss(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-weight-change.db")})
    with database:
        database.execute("CREATE TABLE WEIGHT_CHANGE (KettoNum TEXT PRIMARY KEY, Note TEXT)")
        database.execute("INSERT INTO WEIGHT_CHANGE VALUES (?, ?)", ("legacy", "preserve"))
        database.commit()

        with pytest.raises(
            SchemaMigrationError,
            match=r"WEIGHT_CHANGE.*JOGAIBA|JOGAIBA.*WEIGHT_CHANGE",
        ):
            importer_class(database, use_jravan_schema=True).import_records(iter([parsed_record()]))
        rows = database.fetch_all("SELECT * FROM WEIGHT_CHANGE")

    assert rows == [{"KettoNum": "legacy", "Note": "preserve"}]


@pytest.mark.parametrize(
    ("table_name", "standard", "auto_commit"),
    [
        pytest.param(table_name, standard, auto_commit, id=f"{table_name}-{auto_commit}")
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True))
        for auto_commit in (True, False)
    ],
)
def test_jg_data_importer_single_record_uses_the_same_exact_delete_contract(
    tmp_path,
    table_name: str,
    standard: bool,
    auto_commit: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{table_name}.db")})
    with database:
        schema = JRAVAN_SCHEMAS[table_name] if standard else SCHEMAS[table_name]
        database.create_table(table_name, schema)
        DataImporter(database, use_jravan_schema=standard).import_records(iter([parsed_record()]))
        importer = DataImporter(database, use_jravan_schema=standard)
        missing_status = parsed_record()
        missing_status.pop("DataKubun")
        with pytest.raises(SchemaMigrationError, match="DataKubun.*required"):
            importer.import_single_record(missing_status, auto_commit=auto_commit)
        assert (
            importer.import_single_record(
                parsed_record(
                    data_kubun="0",
                    bamei="",
                    syusso_kubun="",
                    jyogai_state_kubun="",
                ),
                auto_commit=auto_commit,
            )
            is True
        )
        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 0


def test_jg_postgresql_native_and_standard_revote_update_delete(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_JG"])
    postgresql_db.execute(JRAVAN_SCHEMAS["JOGAIBA"])
    postgresql_db.commit()

    for importer_class in (DataImporter, OptimizedDataImporter):
        for table_name, standard in (("NL_JG", False), ("JOGAIBA", True)):
            importer = importer_class(postgresql_db, use_jravan_schema=standard)
            created = importer.import_records(
                iter(
                    [
                        parsed_record(num="001", bamei="PostgreSQL保持"),
                        parsed_record(num="002", bamei="PostgreSQL削除"),
                    ]
                )
            )
            assert created["records_imported"] == 2
            assert created["records_failed"] == 0
            assert (
                postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 2
            )

            deleted = importer.import_records(
                iter(
                    [
                        parsed_record(
                            data_kubun="0",
                            num="002",
                            bamei="",
                            syusso_kubun="",
                            jyogai_state_kubun="",
                        )
                    ]
                )
            )
            assert deleted["records_imported"] == 1
            assert deleted["records_failed"] == 0
            assert (
                postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 1
            )

            postgresql_db.execute(f"DELETE FROM {table_name}")
            postgresql_db.commit()

    primary_key_query = (
        "SELECT pg_get_constraintdef(c.oid) AS definition "
        "FROM pg_constraint c WHERE c.conrelid = to_regclass(?) AND c.contype = 'p'"
    )
    for table_name, standard in (("NL_JG", False), ("JOGAIBA", True)):
        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.execute(_obsolete_schema(table_name, standard=standard))
        num_column = "ShutsubaTohyoJun" if standard else "Num"
        syusso_column = "ShussoKubun" if standard else "SyussoKubun"
        jyogai_column = "JogaiJotaiKubun" if standard else "JyogaiStateKubun"
        postgresql_db.execute(
            f"INSERT INTO {table_name} "
            f"(RecordSpec, DataKubun, MakeDate, Year, MonthDay, JyoCD, Kaiji, "
            f"Nichiji, RaceNum, KettoNum, Bamei, {num_column}, {syusso_column}, "
            f"{jyogai_column}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "JG",
                "1",
                "20260817",
                2026,
                817,
                "05",
                3,
                4,
                0,
                "2026100001",
                "preserve",
                1 if standard else "001",
                "1",
                "0",
            ),
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
                    iter([parsed_record()]),
                    auto_commit=auto_commit,
                )
            assert postgresql_db.fetch_one(primary_key_query, (table_name.lower(),)) == before_key
            assert postgresql_db.fetch_all(f"SELECT * FROM {table_name}") == before_rows
            postgresql_db.rollback()

        postgresql_db.execute(f"DROP TABLE {table_name}")
        postgresql_db.commit()
