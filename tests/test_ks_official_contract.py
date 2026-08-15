#!/usr/bin/env python
"""KS physical and normalized-storage contract for the official 4173-byte layout."""

import os
from itertools import pairwise
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.database.base import DatabaseError
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import get_table_column_types, get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.ks_parser import KSParser


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
    schema_name = f"jlt_ks_{uuid4().hex[:12]}"
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


def _pad(value: str, size: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    return encoded.ljust(size, b" ")


HEADER_FIELDS = [
    ("RecordSpec", 1, 2, b"KS"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260816"),
    ("KisyuCode", 12, 5, b"01234"),
    ("DelKubun", 17, 1, b"0"),
    ("IssueDate", 18, 8, b"20010101"),
    ("DelDate", 26, 8, b"00000000"),
    ("BirthDate", 34, 8, b"19800102"),
    ("KisyuName", 42, 34, _pad("騎手 太郎", 34)),
    ("reserved", 76, 34, _pad("予備", 34)),
    ("KisyuNameKana", 110, 30, _pad("ｷｼｭ ﾀﾛｳ", 30)),
    ("KisyuRyakusyo", 140, 8, _pad("騎手太", 8)),
    ("KisyuNameEng", 148, 80, _pad("TARO KISHU", 80)),
    ("SexCD", 228, 1, b"1"),
    ("SikakuCD", 229, 1, b"1"),
    ("MinaraiCD", 230, 1, b"0"),
    ("TozaiCD", 231, 1, b"1"),
    ("Syotai", 232, 20, _pad("招待地域", 20)),
    ("ChokyosiCode", 252, 5, b"01235"),
    ("ChokyosiRyakusyo", 257, 8, _pad("調教太", 8)),
]

FIRST_RIDE_FIELDS = [
    ("Hatukijyoid", 0, 16),
    ("SyussoTosu", 16, 2),
    ("KettoNum", 18, 10),
    ("Bamei", 28, 36),
    ("KakuteiJyuni", 64, 2),
    ("IJyoCD", 66, 1),
]
FIRST_WIN_FIELDS = [
    ("Hatusyoriid", 0, 16),
    ("SyussoTosu", 16, 2),
    ("KettoNum", 18, 10),
    ("Bamei", 28, 36),
]
RECENT_FIELDS = [
    ("SaikinJyusyoid", 0, 16),
    ("Hondai", 16, 60),
    ("Ryakusyo10", 76, 20),
    ("Ryakusyo6", 96, 12),
    ("Ryakusyo3", 108, 6),
    ("GradeCD", 114, 1),
    ("SyussoTosu", 115, 2),
    ("KettoNum", 117, 10),
    ("Bamei", 127, 36),
]
RESULT_FIELDS = [
    ("SetYear", 4),
    ("HonSyokinHeichi", 10),
    ("HonSyokinSyogai", 10),
    ("FukaSyokinHeichi", 10),
    ("FukaSyokinSyogai", 10),
    *[(f"HeichiChakukaisu{rank}", 6) for rank in range(1, 7)],
    *[(f"SyogaiChakukaisu{rank}", 6) for rank in range(1, 7)],
    *[(f"Jyo{course}Chakukaisu{rank}", 6) for course in range(1, 21) for rank in range(1, 7)],
    *[(f"Kyori{distance}Chakukaisu{rank}", 6) for distance in range(1, 7) for rank in range(1, 7)],
]


def _block_value(kind: str, block: int, suffix: str, size: int) -> bytes:
    values = {
        "Hatukijyoid": f"20260{block}010501010{block}",
        "Hatusyoriid": f"20260{block}020501020{block}",
        "SaikinJyusyoid": f"20260{block}030501030{block}",
        "SyussoTosu": f"1{block}",
        "KettoNum": f"2026{block:06d}",
        "Bamei": f"{kind} Horse {block}",
        "KakuteiJyuni": f"0{block}",
        "IJyoCD": "0",
        "Hondai": f"Recent Grade Win Main Title {block}",
        "Ryakusyo10": f"Recent10-{block}",
        "Ryakusyo6": f"Recent6-{block}",
        "Ryakusyo3": f"R3-{block}",
        "GradeCD": str(block),
    }
    return _pad(values[suffix], size)


def build_record(*, data_kubun: str = "1", name: str = "騎手 太郎"):
    record = bytearray(b" " * 4173)
    expected_header = {}
    expected_results = []
    physical_fields = []

    def put(field_name: str, position: int, size: int, value: bytes) -> None:
        assert len(value) == size, (field_name, len(value), size)
        start = position - 1
        assert record[start : start + size] == b" " * size
        record[start : start + size] = value
        physical_fields.append((field_name, position, size, value))

    for field_name, position, size, default in HEADER_FIELDS:
        value = default
        if field_name == "DataKubun":
            value = data_kubun.encode("ascii")
        elif field_name == "KisyuName":
            value = _pad(name, size)
        put(field_name, position, size, value)
        expected_header[field_name] = value.decode("cp932").strip()

    for block in range(1, 3):
        block_position = 265 + 67 * (block - 1)
        for suffix, relative, size in FIRST_RIDE_FIELDS:
            field_name = f"HatuKiJyo{block}{suffix}"
            value = _block_value("First Ride", block, suffix, size)
            put(field_name, block_position + relative, size, value)
            expected_header[field_name] = value.decode("cp932").strip()

    for block in range(1, 3):
        block_position = 399 + 64 * (block - 1)
        for suffix, relative, size in FIRST_WIN_FIELDS:
            field_name = f"HatuSyori{block}{suffix}"
            value = _block_value("First Win", block, suffix, size)
            put(field_name, block_position + relative, size, value)
            expected_header[field_name] = value.decode("cp932").strip()

    for block in range(1, 4):
        block_position = 527 + 163 * (block - 1)
        for suffix, relative, size in RECENT_FIELDS:
            field_name = f"SaikinJyusyo{block}{suffix}"
            value = _block_value("Recent Winner", block, suffix, size)
            put(field_name, block_position + relative, size, value)
            expected_header[field_name] = value.decode("cp932").strip()

    counter = 0
    years = ("2026", "2025", "1999")
    for block in range(1, 4):
        block_position = 1016 + 1052 * (block - 1)
        offset = 0
        expected = {
            "MakeDate": expected_header["MakeDate"],
            "KisyuCode": expected_header["KisyuCode"],
            "Num": str(block),
        }
        for field_name, size in RESULT_FIELDS:
            if field_name == "SetYear":
                value = years[block - 1].encode("ascii")
            else:
                counter += 1
                value = f"{counter:0{size}d}".encode("ascii")
            put(f"Result{block}_{field_name}", block_position + offset, size, value)
            expected[field_name] = value.decode("ascii")
            offset += size
        assert offset == 1052
        expected_results.append(expected)

    put("RecordDelimiter", 4172, 2, b"\r\n")
    expected_header["RecordDelimiter"] = ""
    return bytes(record), expected_header, expected_results, physical_fields


NATIVE_HEADER_FIELDS = {
    *(name for name, _, _, _ in HEADER_FIELDS),
    *(f"HatuKiJyo{block}{suffix}" for block in range(1, 3) for suffix, _, _ in FIRST_RIDE_FIELDS),
    *(f"HatuSyori{block}{suffix}" for block in range(1, 3) for suffix, _, _ in FIRST_WIN_FIELDS),
    *(f"SaikinJyusyo{block}{suffix}" for block in range(1, 4) for suffix, _, _ in RECENT_FIELDS),
}
SEISEKI_FIELDS = {"MakeDate", "KisyuCode", "Num", *(name for name, _ in RESULT_FIELDS)}
NUMERIC_HEADER_FIELDS = {
    *(
        f"HatuKiJyo{block}{suffix}"
        for block in range(1, 3)
        for suffix in ("SyussoTosu", "KakuteiJyuni")
    ),
    *(f"HatuSyori{block}SyussoTosu" for block in range(1, 3)),
    *(f"SaikinJyusyo{block}SyussoTosu" for block in range(1, 4)),
}
NUMERIC_SEISEKI_FIELDS = {"Num", *(name for name, _ in RESULT_FIELDS)}


def _expected_db_row(values: dict[str, str], numeric_fields: set[str]) -> dict:
    return {key: (int(value) if key in numeric_fields else value) for key, value in values.items()}


def test_ks_physical_layout_is_gap_free_and_complete() -> None:
    _, _, _, fields = build_record()
    ordered = sorted(fields, key=lambda item: item[1])

    assert ordered[0][1:3] == (1, 2)
    assert ordered[-1][1:3] == (4172, 2)
    assert all(
        position + size == next_position
        for (_, position, size, _), (_, next_position, _, _) in pairwise(ordered)
    )
    assert len(RESULT_FIELDS) == 173


def test_ks_reads_every_official_field_without_silent_omission() -> None:
    record, expected_header, expected_results, _ = build_record()
    parsed = KSParser().parse(record)

    assert parsed is not None
    assert KSParser.RECORD_LENGTH == 4173
    assert {
        key: value for key, value in parsed.items() if key != "_ks_seiseki_rows"
    } == expected_header
    assert parsed["_ks_seiseki_rows"] == expected_results


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_record()[0][:770] + b"\r\n", id="repository-772"),
        pytest.param(build_record()[0][:-1], id="short"),
        pytest.param(build_record()[0] + b" ", id="long"),
        pytest.param(b"XX" + build_record()[0][2:], id="record-type"),
        pytest.param(build_record()[0][:-2] + b"  ", id="delimiter"),
        pytest.param(build_record()[0][:41] + b"\x81\x20" + build_record()[0][43:], id="cp932"),
        pytest.param(build_record()[0][:2] + b"9" + build_record()[0][3:], id="data-kubun"),
        pytest.param(build_record()[0][:3] + b"202X0816" + build_record()[0][11:], id="make-date"),
        pytest.param(build_record()[0][:1015] + b"20X6" + build_record()[0][1019:], id="result"),
    ],
)
def test_ks_rejects_truncated_or_corrupt_records(record: bytes) -> None:
    assert KSParser().parse(record) is None


def test_ks_normalized_schemas_match_official_cardinality_and_keys() -> None:
    assert set(get_table_column_types("NL_KS")) == NATIVE_HEADER_FIELDS
    assert set(get_table_column_types("KISYU")) == NATIVE_HEADER_FIELDS
    assert set(get_table_column_types("NL_KS_SEISEKI")) == SEISEKI_FIELDS
    assert set(get_table_column_types("KISYU_SEISEKI")) == SEISEKI_FIELDS
    assert get_table_primary_key_columns("NL_KS") == ["KisyuCode"]
    assert get_table_primary_key_columns("KISYU") == ["KisyuCode"]
    assert get_table_primary_key_columns("NL_KS_SEISEKI") == ["KisyuCode", "Num"]
    assert get_table_primary_key_columns("KISYU_SEISEKI") == ["KisyuCode", "Num"]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
@pytest.mark.parametrize(
    "main_table,result_table,use_standard",
    [("NL_KS", "NL_KS_SEISEKI", False), ("KISYU", "KISYU_SEISEKI", True)],
)
def test_ks_importers_store_complete_record_idempotently(
    tmp_path, importer_class, main_table: str, result_table: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{main_table}.db")})
    record, expected_header, expected_results, _ = build_record()
    schemas = JRAVAN_SCHEMAS if use_standard else SCHEMAS
    with database:
        database.create_table(main_table, schemas[main_table])
        database.create_table(result_table, schemas[result_table])
        importer = importer_class(database, use_jravan_schema=use_standard)
        first = importer.import_records(iter([KSParser().parse(record)]))
        second = importer.import_records(iter([KSParser().parse(record)]))
        main_row = database.fetch_one(f"SELECT * FROM {main_table}")
        result_rows = database.fetch_all(f"SELECT * FROM {result_table} ORDER BY Num")

    expected_main = {
        key: value for key, value in expected_header.items() if key != "RecordDelimiter"
    }
    assert first["records_imported"] == second["records_imported"] == 1
    assert first["records_failed"] == second["records_failed"] == 0
    assert main_row == _expected_db_row(expected_main, NUMERIC_HEADER_FIELDS)
    assert result_rows == [
        _expected_db_row(row, NUMERIC_SEISEKI_FIELDS) for row in expected_results
    ]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
@pytest.mark.parametrize(
    "main_table,result_table,use_standard",
    [("NL_KS", "NL_KS_SEISEKI", False), ("KISYU", "KISYU_SEISEKI", True)],
)
def test_ks_delete_removes_parent_and_children_in_delivery_order(
    tmp_path, importer_class, main_table: str, result_table: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{main_table}.db")})
    schemas = JRAVAN_SCHEMAS if use_standard else SCHEMAS
    initial = KSParser().parse(build_record()[0])
    deletion = KSParser().parse(build_record(data_kubun="0")[0])
    replacement = KSParser().parse(build_record(data_kubun="2", name="騎手 次郎")[0])
    with database:
        database.create_table(main_table, schemas[main_table])
        database.create_table(result_table, schemas[result_table])
        importer = importer_class(database, use_jravan_schema=use_standard)
        deleted = importer.import_records(iter([initial, deletion]))
        deleted_main_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {main_table}")[
            "count"
        ]
        deleted_child_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {result_table}")[
            "count"
        ]
        stats = importer.import_records(iter([initial, deletion, replacement]))
        main_rows = database.fetch_all(f"SELECT KisyuName FROM {main_table}")
        child_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {result_table}")["count"]

    assert deleted["records_imported"] == 2
    assert deleted["records_failed"] == 0
    assert deleted_main_count == deleted_child_count == 0
    assert stats["records_imported"] == 3
    assert stats["records_failed"] == 0
    assert main_rows == [{"KisyuName": "騎手 次郎"}]
    assert child_count == 3


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_import_refuses_missing_result_table_before_parent_mutation(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "missing-child.db")})
    with database:
        database.create_table("NL_KS", SCHEMAS["NL_KS"])
        with pytest.raises(SchemaMigrationError, match="NL_KS_SEISEKI"):
            importer_class(database).import_records(iter([KSParser().parse(build_record()[0])]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_KS")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_standard_keyless_header_fails_closed_without_row_loss(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "keyless-standard.db")})
    keyless_header = JRAVAN_SCHEMAS["KISYU"].replace(",\n            PRIMARY KEY (KisyuCode)", "")
    with database:
        database.create_table("KISYU", keyless_header)
        database.create_table("KISYU_SEISEKI", JRAVAN_SCHEMAS["KISYU_SEISEKI"])
        database.execute(
            "INSERT INTO KISYU (RecordSpec, DataKubun, MakeDate, KisyuCode, KisyuName) "
            "VALUES (?, ?, ?, ?, ?)",
            ("KS", "1", "20000101", "99999", "preserve"),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([KSParser().parse(build_record()[0])])
            )
        rows = database.fetch_all("SELECT KisyuCode, KisyuName FROM KISYU")

    assert rows == [{"KisyuCode": "99999", "KisyuName": "preserve"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_legacy_standard_header_fails_closed_without_row_loss(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-standard.db")})
    legacy_header = """
        CREATE TABLE KISYU (
            RecordSpec TEXT,
            DataKubun TEXT,
            MakeDate TEXT,
            KisyuName TEXT
        )
    """
    with database:
        database.create_table("KISYU", legacy_header)
        database.create_table("KISYU_SEISEKI", JRAVAN_SCHEMAS["KISYU_SEISEKI"])
        database.execute(
            "INSERT INTO KISYU VALUES (?, ?, ?, ?)",
            ("KS", "1", "20000101", "preserve-legacy"),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([KSParser().parse(build_record()[0])])
            )
        rows = database.fetch_all("SELECT RecordSpec, KisyuName FROM KISYU")

    assert rows == [{"RecordSpec": "KS", "KisyuName": "preserve-legacy"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_standard_keyless_result_table_fails_closed_without_row_loss(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "keyless-child.db")})
    keyless_child = JRAVAN_SCHEMAS["KISYU_SEISEKI"].replace(
        ",\n            PRIMARY KEY (KisyuCode, Num)", ""
    )
    with database:
        database.create_table("KISYU", JRAVAN_SCHEMAS["KISYU"])
        database.create_table("KISYU_SEISEKI", keyless_child)
        database.execute(
            "INSERT INTO KISYU_SEISEKI (MakeDate, KisyuCode, Num, SetYear) " "VALUES (?, ?, ?, ?)",
            ("20000101", "99999", 1, 2000),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([KSParser().parse(build_record()[0])])
            )
        rows = database.fetch_all("SELECT KisyuCode, Num, SetYear FROM KISYU_SEISEKI")

    assert rows == [{"KisyuCode": "99999", "Num": 1, "SetYear": 2000}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_child_failure_rolls_back_parent(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "atomic.db")})
    child_schema = SCHEMAS["NL_KS_SEISEKI"].replace(
        "PRIMARY KEY (KisyuCode, Num)",
        "MustSupply TEXT NOT NULL, PRIMARY KEY (KisyuCode, Num)",
    )
    with database:
        database.create_table("NL_KS", SCHEMAS["NL_KS"])
        database.create_table("NL_KS_SEISEKI", child_schema)
        stats = importer_class(database).import_records(iter([KSParser().parse(build_record()[0])]))
        main_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_KS")["count"]
        child_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_KS_SEISEKI")["count"]

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert main_count == child_count == 0


def test_ks_coupled_failure_never_enters_parent_only_batch_fallback(monkeypatch) -> None:
    database = MagicMock()
    database.get_db_type.return_value = "sqlite"
    importer = DataImporter(database)
    parsed = KSParser().parse(build_record()[0])

    monkeypatch.setattr(
        "src.importer.importer.verify_ks_coupled_table",
        lambda _database, _table_name: "NL_KS_SEISEKI",
    )

    def fail_coupled_write(*_args, **_kwargs):
        raise DatabaseError("rollback could not be confirmed")

    monkeypatch.setattr(
        "src.importer.importer.insert_ks_coupled_batch",
        fail_coupled_write,
    )

    with pytest.raises(DatabaseError, match="rollback could not be confirmed"):
        importer._flush_batch("NL_KS", [parsed], auto_commit=True)

    database.insert.assert_not_called()


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_postgresql_native_and_standard_store_all_rows(postgresql_db, importer_class) -> None:
    for schema in (
        SCHEMAS["NL_KS"],
        SCHEMAS["NL_KS_SEISEKI"],
        JRAVAN_SCHEMAS["KISYU"],
        JRAVAN_SCHEMAS["KISYU_SEISEKI"],
    ):
        postgresql_db.execute(schema)
    postgresql_db.commit()

    native = importer_class(postgresql_db).import_records(
        iter(
            [
                KSParser().parse(build_record()[0]),
                KSParser().parse(build_record(data_kubun="0")[0]),
                KSParser().parse(build_record(data_kubun="2", name="騎手 次郎")[0]),
            ]
        )
    )
    standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(
        iter(
            [
                KSParser().parse(build_record()[0]),
                KSParser().parse(build_record(data_kubun="0")[0]),
                KSParser().parse(build_record(data_kubun="2", name="騎手 次郎")[0]),
            ]
        )
    )

    assert native["records_imported"] == standard["records_imported"] == 3
    assert native["records_failed"] == standard["records_failed"] == 0
    assert {
        table: postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")["count"]
        for table in ("NL_KS", "NL_KS_SEISEKI", "KISYU", "KISYU_SEISEKI")
    } == {"NL_KS": 1, "NL_KS_SEISEKI": 3, "KISYU": 1, "KISYU_SEISEKI": 3}
    assert postgresql_db.fetch_one('SELECT KisyuName AS "KisyuName" FROM NL_KS') == {
        "KisyuName": "騎手 次郎"
    }
    assert postgresql_db.fetch_one('SELECT KisyuName AS "KisyuName" FROM KISYU') == {
        "KisyuName": "騎手 次郎"
    }
    assert postgresql_db.fetch_one(
        'SELECT Num AS "Num", Kyori6Chakukaisu6 AS "Tail" '
        "FROM KISYU_SEISEKI ORDER BY Num DESC LIMIT 1"
    ) == {"Num": 3, "Tail": 516}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ks_postgresql_child_failure_rolls_back_parent(postgresql_db, importer_class) -> None:
    child_schema = SCHEMAS["NL_KS_SEISEKI"].replace(
        "PRIMARY KEY (KisyuCode, Num)",
        "MustSupply TEXT NOT NULL, PRIMARY KEY (KisyuCode, Num)",
    )
    postgresql_db.execute(SCHEMAS["NL_KS"])
    postgresql_db.execute(child_schema)
    postgresql_db.commit()

    stats = importer_class(postgresql_db).import_records(
        iter([KSParser().parse(build_record()[0])])
    )

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_KS")["count"] == 0
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_KS_SEISEKI")["count"] == 0
