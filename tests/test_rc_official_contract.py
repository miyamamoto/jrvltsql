"""Official 501-byte RC parser and lossless storage contract tests."""

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
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.rc_parser import RCParser

RC_OFFICIAL_LENGTH = 501
RC_KEY = [
    "RecInfoKubun",
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "TokuNum",
    "SyubetuCD",
    "Kyori",
    "TrackCD",
]


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
    schema_name = f"jlt_rc_{uuid4().hex[:12]}"
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
        ("RecInfoKubun", 1),
        ("Year", 4),
        ("MonthDay", 4),
        ("JyoCD", 2),
        ("Kaiji", 2),
        ("Nichiji", 2),
        ("RaceNum", 2),
        ("TokuNum", 4),
        ("Hondai", 60),
        ("GradeCD", 1),
        ("SyubetuCD", 2),
        ("Kyori", 4),
        ("TrackCD", 2),
        ("RecKubun", 1),
        ("RecTime", 4),
        ("TenkoCD", 1),
        ("SibaBabaCD", 1),
        ("DirtBabaCD", 1),
    ):
        add(name, size)

    for number in range(1, 4):
        for name, size in (
            (f"RecUmaKettoNum{number}", 10),
            (f"RecUmaBamei{number}", 36),
            (f"RecUmaUmaKigoCD{number}", 2),
            (f"RecUmaSexCD{number}", 1),
            (f"RecUmaChokyosiCode{number}", 5),
            (f"RecUmaChokyosiName{number}", 34),
            (f"RecUmaFutan{number}", 3),
            (f"RecUmaKisyuCode{number}", 5),
            (f"RecUmaKisyuName{number}", 34),
        ):
            add(name, size)
    add("Crlf", 2)

    assert cursor == RC_OFFICIAL_LENGTH
    return tuple(fields)


OFFICIAL_RC_LAYOUT = _official_layout()


def _put(record: bytearray, start: int, size: int, value: str) -> None:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    record[start : start + size] = encoded.ljust(size, b" ")


def build_rc_record(
    *,
    data_kubun: str = "1",
    key_overrides: dict[str, str] | None = None,
    horse_prefix: str = "HORSE",
) -> tuple[bytes, dict[str, str]]:
    values = {
        "RecordSpec": "RC",
        "DataKubun": data_kubun,
        "MakeDate": "20260816",
        "RecInfoKubun": "1",
        "Year": "2026",
        "MonthDay": "0816",
        "JyoCD": "05",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "TokuNum": "0000",
        "Hondai": "東京記念",
        "GradeCD": "G",
        "SyubetuCD": "13",
        "Kyori": "2000",
        "TrackCD": "17",
        "RecKubun": "2",
        "RecTime": "1599",
        "TenkoCD": "1",
        "SibaBabaCD": "2",
        "DirtBabaCD": "3",
    }
    values.update(key_overrides or {})
    for number in range(1, 4):
        values.update(
            {
                f"RecUmaKettoNum{number}": f"20201{number:05d}",
                f"RecUmaBamei{number}": f"{horse_prefix}{number}",
                f"RecUmaUmaKigoCD{number}": f"A{number}",
                f"RecUmaSexCD{number}": str(number),
                f"RecUmaChokyosiCode{number}": f"00{100 + number}",
                f"RecUmaChokyosiName{number}": f"TRAINER{number}",
                f"RecUmaFutan{number}": str(560 + number),
                f"RecUmaKisyuCode{number}": f"00{200 + number}",
                f"RecUmaKisyuName{number}": f"JOCKEY{number}",
            }
        )

    record = bytearray(b" " * RC_OFFICIAL_LENGTH)
    expected: dict[str, str] = {}
    for name, start, size in OFFICIAL_RC_LAYOUT:
        if name == "Crlf":
            record[start : start + size] = b"\r\n"
            expected[name] = ""
            continue
        _put(record, start, size, values[name])
        expected[name] = values[name]
    return bytes(record), expected


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_rc_record()[0])
    record[32:34] = b"\x81\x20"
    return bytes(record)


def test_rc_parses_all_49_official_fields_at_gap_free_offsets() -> None:
    record, expected = build_rc_record()

    assert len(OFFICIAL_RC_LAYOUT) == 49
    assert OFFICIAL_RC_LAYOUT[0] == ("RecordSpec", 0, 2)
    assert OFFICIAL_RC_LAYOUT[-1] == ("Crlf", 499, 2)
    assert all(
        start + size == next_start
        for (_, start, size), (_, next_start, _) in pairwise(OFFICIAL_RC_LAYOUT)
    )

    row = RCParser().parse(record)

    assert row is not None
    assert RCParser.RECORD_LENGTH == RC_OFFICIAL_LENGTH
    assert set(row) == set(expected)
    assert row == expected
    assert [row[f"RecUmaBamei{i}"] for i in range(1, 4)] == [
        "HORSE1",
        "HORSE2",
        "HORSE3",
    ]


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_rc_record()[0][:241], id="non-official-241"),
        pytest.param(build_rc_record()[0][:-1], id="short-500"),
        pytest.param(build_rc_record()[0] + b" ", id="long-502"),
        pytest.param(b"XX" + build_rc_record()[0][2:], id="wrong-record-type"),
        pytest.param(build_rc_record()[0][:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_rc_rejects_non_official_record_boundaries(record: bytes) -> None:
    assert RCParser().parse(record) is None


def test_rc_native_and_standard_schemas_store_the_complete_contract() -> None:
    parser_fields = {name for name, _, _ in OFFICIAL_RC_LAYOUT}

    assert set(get_table_column_types("NL_RC")) == parser_fields
    assert set(get_table_column_types("RECORD")) == parser_fields - {"Crlf"}
    assert get_table_primary_key_columns("NL_RC") == RC_KEY
    assert get_table_primary_key_columns("RECORD") == RC_KEY


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_RC", False), ("RECORD", True)),
)
def test_rc_round_trips_all_three_holders_and_separate_course_fields(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        parsed = RCParser().parse(build_rc_record()[0])
        assert parsed is not None
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([parsed]))
        row = database.fetch_one(
            f"SELECT SyubetuCD, Kyori, TrackCD, RecTime, "
            f"RecUmaBamei1, RecUmaFutan1, RecUmaBamei2, RecUmaFutan2, "
            f"RecUmaBamei3, RecUmaFutan3 FROM {table_name}"
        )

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert row is not None
    assert str(row["SyubetuCD"]) == "13"
    assert str(row["Kyori"]) == "2000"
    assert str(row["TrackCD"]) == "17"
    assert str(row["RecTime"]) == "1599"
    assert [row[f"RecUmaBamei{i}"] for i in range(1, 4)] == [
        "HORSE1",
        "HORSE2",
        "HORSE3",
    ]
    assert [str(row[f"RecUmaFutan{i}"]) for i in range(1, 4)] == ["561", "562", "563"]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_RC", False), ("RECORD", True)),
)
def test_rc_delete_is_ordered_and_scoped_to_the_complete_official_key(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    first = RCParser().parse(build_rc_record()[0])
    replacement = RCParser().parse(build_rc_record(horse_prefix="REPLACED")[0])
    second = RCParser().parse(
        build_rc_record(
            key_overrides={"SyubetuCD": "14"},
            horse_prefix="OTHER",
        )[0]
    )
    delete_first = RCParser().parse(build_rc_record(data_kubun="0")[0])
    assert all(row is not None for row in (first, replacement, second, delete_first))

    with database:
        database.create_table(table_name, schema)
        importer = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        )
        replacement_stats = importer.import_records(iter([first, replacement]))
        replaced = database.fetch_all(
            f"SELECT DataKubun, SyubetuCD, RecUmaBamei1 FROM {table_name}"
        )
        stats = importer.import_records(iter([second, delete_first]))
        rows = database.fetch_all(f"SELECT DataKubun, SyubetuCD, RecUmaBamei1 FROM {table_name}")

    assert replacement_stats["records_imported"] == 2
    assert replacement_stats["records_failed"] == 0
    assert replaced == [
        {"DataKubun": "1", "SyubetuCD": "13", "RecUmaBamei1": "REPLACED1"}
    ]
    assert stats["records_imported"] == 2
    assert stats["records_failed"] == 0
    assert rows == [{"DataKubun": "1", "SyubetuCD": "14", "RecUmaBamei1": "OTHER1"}]


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_incomplete_rc_key_aborts_the_whole_batch_before_mutation(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "incomplete-key.db")})
    valid = RCParser().parse(build_rc_record()[0])
    incomplete = RCParser().parse(
        build_rc_record(
            data_kubun="0",
            key_overrides={"TokuNum": ""},
        )[0]
    )
    assert valid is not None and incomplete is not None

    with database:
        database.create_table("NL_RC", SCHEMAS["NL_RC"])
        with pytest.raises(SchemaMigrationError, match="incomplete official key"):
            importer_class(database).import_records(iter([valid, incomplete]))

        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_RC")["count"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_unsupported_rc_data_kubun_aborts_before_mutation(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "unsupported-data-kubun.db")})
    unsupported = RCParser().parse(build_rc_record()[0])
    assert unsupported is not None
    unsupported["DataKubun"] = "9"

    with database:
        database.create_table("NL_RC", SCHEMAS["NL_RC"])
        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            importer_class(database).import_records(iter([unsupported]))

        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_RC")["count"] == 0


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_rc_batches_only_consecutive_upserts_around_ordered_deletes(
    tmp_path,
    monkeypatch,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "ordered-batches.db")})
    first = RCParser().parse(build_rc_record()[0])
    second = RCParser().parse(
        build_rc_record(key_overrides={"SyubetuCD": "14"}, horse_prefix="OTHER")[0]
    )
    delete_first = RCParser().parse(build_rc_record(data_kubun="0")[0])
    replacement = RCParser().parse(build_rc_record(horse_prefix="LAST")[0])
    assert all(row is not None for row in (first, second, delete_first, replacement))

    with database:
        database.create_table("NL_RC", SCHEMAS["NL_RC"])
        original_insert_many = database.insert_many
        batch_sizes = []

        def record_batch(table_name, rows, use_replace=True):
            batch_sizes.append(len(rows))
            return original_insert_many(table_name, rows, use_replace=use_replace)

        monkeypatch.setattr(database, "insert_many", record_batch)
        stats = importer_class(database).import_records(
            iter([first, second, delete_first, replacement])
        )
        rows = database.fetch_all(
            "SELECT SyubetuCD, RecUmaBamei1 FROM NL_RC ORDER BY SyubetuCD"
        )

    assert stats["records_imported"] == 4
    assert stats["records_failed"] == 0
    assert batch_sizes == [2, 1]
    assert rows == [
        {"SyubetuCD": "13", "RecUmaBamei1": "LAST1"},
        {"SyubetuCD": "14", "RecUmaBamei1": "OTHER1"},
    ]


def _obsolete_rc_schema(table_name: str) -> str:
    columns = [
        f"{name} TEXT"
        for name, _, _ in OFFICIAL_RC_LAYOUT
        if name != "Crlf" or table_name == "NL_RC"
    ]
    columns.append("PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, RecInfoKubun)")
    return f"CREATE TABLE {table_name} ({', '.join(columns)})"


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_RC", False), ("RECORD", True)),
)
def test_existing_obsolete_rc_key_fails_closed_without_data_loss(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"obsolete-{table_name}.db")})
    with database:
        database.execute(_obsolete_rc_schema(table_name))
        database.execute(
            f"INSERT INTO {table_name} "
            "(RecInfoKubun, Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) "
            "VALUES ('1', '2025', '0101', '05', '01', '01', '01')"
        )
        database.commit()

        parsed = RCParser().parse(build_rc_record()[0])
        assert parsed is not None
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(
                database,
                use_jravan_schema=use_jravan_schema,
            ).import_records(iter([parsed]))

        assert database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"] == 1


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_obsolete_standard_rc_table_does_not_block_unrelated_standard_import(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "unrelated-standard.db")})
    unrelated = {
        "RecordSpec": "HN",
        "DataKubun": "1",
        "MakeDate": "20260816",
        "HansyokuNum": "1234567890",
        "Bamei": "UNRELATED",
    }

    with database:
        database.execute(_obsolete_rc_schema("RECORD"))
        database.execute(JRAVAN_SCHEMAS["HANSYOKU"])
        database.commit()

        stats = importer_class(database, use_jravan_schema=True).import_records(
            iter([unrelated])
        )

        assert stats["records_imported"] == 1
        assert stats["records_failed"] == 0
        assert database.fetch_one(
            "SELECT HansyokuNum, Bamei FROM HANSYOKU"
        ) == {"HansyokuNum": "1234567890", "Bamei": "UNRELATED"}


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_rc_postgresql_native_and_standard_preserve_keyed_deletion(
    postgresql_db,
    importer_class,
) -> None:
    postgresql_db.execute(SCHEMAS["NL_RC"])
    postgresql_db.execute(JRAVAN_SCHEMAS["RECORD"])
    postgresql_db.commit()

    records = [
        RCParser().parse(build_rc_record()[0]),
        RCParser().parse(
            build_rc_record(
                data_kubun="2",
                key_overrides={"SyubetuCD": "14"},
                horse_prefix="OTHER",
            )[0]
        ),
        RCParser().parse(build_rc_record(data_kubun="0")[0]),
    ]
    assert all(record is not None for record in records)

    native = importer_class(postgresql_db).import_records(iter(records))
    standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(iter(records))

    assert native["records_imported"] == standard["records_imported"] == 3
    assert native["records_failed"] == standard["records_failed"] == 0
    assert {
        table_name: postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]
        for table_name in ("NL_RC", "RECORD")
    } == {"NL_RC": 1, "RECORD": 1}
    for table_name in ("NL_RC", "RECORD"):
        assert postgresql_db.fetch_one(
            'SELECT SyubetuCD AS "SyubetuCD", '
            'RecUmaBamei3 AS "RecUmaBamei3" '
            f"FROM {table_name}"
        ) == {"SyubetuCD": "14", "RecUmaBamei3": "OTHER3"}
