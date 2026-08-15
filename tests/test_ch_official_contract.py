#!/usr/bin/env python
"""CH physical and normalized-storage contract for the official 3862-byte layout."""

import os
from itertools import pairwise
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError, migrate_table_if_needed
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import get_table_column_types, get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.ch_parser import CHParser


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
    schema_name = f"jlt_ch_{uuid4().hex[:12]}"
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


# Native flattened header field, official one-based position, byte length, value.
HEADER_FIELDS = [
    ("RecordSpec", 1, 2, b"CH"),
    ("DataKubun", 3, 1, b"1"),
    ("MakeDate", 4, 8, b"20260815"),
    ("ChokyosiCode", 12, 5, b"C1234"),
    ("DelKubun", 17, 1, b"0"),
    ("IssueDate", 18, 8, b"20010101"),
    ("DelDate", 26, 8, b"00000000"),
    ("BirthDate", 34, 8, b"19700102"),
    ("ChokyosiName", 42, 34, _pad("Trainer Name Sentinel", 34)),
    ("ChokyosiNameKana", 76, 30, _pad("ﾄﾚｰﾅｰｾﾝﾁﾈﾙ", 30)),
    ("ChokyosiRyakusyo", 106, 8, _pad("TRN-S", 8)),
    ("ChokyosiNameEng", 114, 80, _pad("Distinct Trainer English Sentinel", 80)),
    ("SexCD", 194, 1, b"1"),
    ("TozaiCD", 195, 1, b"2"),
    ("Syotai", 196, 20, _pad("Invitation Sentinel", 20)),
]

RECENT_SUBFIELDS = [
    ("id", 0, 16),
    ("Hondai", 16, 60),
    ("Ryakusyo10", 76, 20),
    ("Ryakusyo6", 96, 12),
    ("Ryakusyo3", 108, 6),
    ("GradeCD", 114, 1),
    ("SyussoTosu", 115, 2),
    ("KettoNum", 117, 10),
    ("Bamei", 127, 36),
]


def _recent_value(block: int, suffix: str, size: int) -> bytes:
    values = {
        "id": f"20260{block}010501010{block}",
        "Hondai": f"Recent Grade Win Main Title {block}",
        "Ryakusyo10": f"Recent10-{block}",
        "Ryakusyo6": f"Recent6-{block}",
        "Ryakusyo3": f"R3-{block}",
        "GradeCD": str(block),
        "SyussoTosu": f"1{block}",
        "KettoNum": f"2026{block:06d}",
        "Bamei": f"Recent Winner Horse {block}",
    }
    return _pad(values[suffix], size)


RESULT_FIELD_WIDTHS = [
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

NATIVE_HEADER_FIELDS = {
    *(name for name, _, _, _ in HEADER_FIELDS),
    *(
        f"SaikinJyusyo{block}_{suffix}"
        for block in range(1, 4)
        for suffix, _, _ in RECENT_SUBFIELDS
    ),
}
STANDARD_HEADER_ALIASES = {
    **{name: name for name, _, _, _ in HEADER_FIELDS},
    **{
        f"SaikinJyusyo{block}_{suffix}": (
            f"SaikinJyusyo{block}SaikinJyusyoid"
            if suffix == "id"
            else f"SaikinJyusyo{block}{suffix}"
        )
        for block in range(1, 4)
        for suffix, _, _ in RECENT_SUBFIELDS
    },
}
SEISEKI_FIELDS = {"MakeDate", "ChokyosiCode", "Num", *(name for name, _ in RESULT_FIELD_WIDTHS)}
NUMERIC_HEADER_FIELDS = {f"SaikinJyusyo{block}_SyussoTosu" for block in range(1, 4)}
NUMERIC_SEISEKI_FIELDS = {"Num", *(name for name, _ in RESULT_FIELD_WIDTHS)}


def build_record() -> tuple[bytes, dict[str, str], list[dict[str, str]], list[tuple]]:
    record = bytearray(b" " * 3862)
    expected_header: dict[str, str] = {}
    expected_results: list[dict[str, str]] = []
    physical_fields: list[tuple] = []

    def put(name: str, position: int, size: int, value: bytes) -> None:
        assert len(value) == size, (name, len(value), size)
        start = position - 1
        assert record[start : start + size] == b" " * size
        record[start : start + size] = value
        physical_fields.append((name, position, size, value))

    for name, position, size, value in HEADER_FIELDS:
        put(name, position, size, value)
        expected_header[name] = value.decode("cp932").strip()

    for block in range(1, 4):
        block_position = 216 + 163 * (block - 1)
        for suffix, relative, size in RECENT_SUBFIELDS:
            name = f"SaikinJyusyo{block}_{suffix}"
            value = _recent_value(block, suffix, size)
            put(name, block_position + relative, size, value)
            expected_header[name] = value.decode("cp932").strip()

    count_value = 0
    years = ("2026", "2025", "1999")
    for block in range(1, 4):
        block_position = 705 + 1052 * (block - 1)
        offset = 0
        expected = {
            "MakeDate": expected_header["MakeDate"],
            "ChokyosiCode": expected_header["ChokyosiCode"],
            "Num": str(block),
        }
        for name, size in RESULT_FIELD_WIDTHS:
            if name == "SetYear":
                value = years[block - 1].encode("ascii")
            elif size == 10:
                count_value += 1
                value = f"{block}{count_value:09d}".encode("ascii")
            else:
                count_value += 1
                value = f"{count_value:06d}".encode("ascii")
            put(f"Result{block}_{name}", block_position + offset, size, value)
            expected[name] = value.decode("ascii")
            offset += size
        assert offset == 1052
        expected_results.append(expected)

    put("RecordDelimiter", 3861, 2, b"\r\n")
    expected_header["RecordDelimiter"] = ""
    return bytes(record), expected_header, expected_results, physical_fields


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_record()[0])
    record[41:43] = b"\x81\x20"
    return bytes(record)


def _expected_db_row(values: dict[str, str], numeric_fields: set[str]) -> dict:
    return {key: (int(value) if key in numeric_fields else value) for key, value in values.items()}


def test_ch_physical_layout_is_gap_free_and_complete() -> None:
    _, _, _, fields = build_record()
    ordered = sorted(fields, key=lambda item: item[1])

    assert ordered[0][1:3] == (1, 2)
    assert ordered[-1][1:3] == (3861, 2)
    assert all(
        position + size == next_position
        for (_, position, size, _), (_, next_position, _, _) in pairwise(ordered)
    )
    assert len(RESULT_FIELD_WIDTHS) == 173
    assert len(ordered) == 15 + 3 * 9 + 3 * 173 + 1


def test_ch_reads_every_official_field_without_silent_omission() -> None:
    record, expected_header, expected_results, _ = build_record()
    parsed = CHParser().parse(record)

    assert parsed is not None
    assert CHParser.RECORD_LENGTH == 3862
    assert {
        key: value for key, value in parsed.items() if key != "_ch_seiseki_rows"
    } == expected_header
    assert parsed["_ch_seiseki_rows"] == expected_results


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_record()[0][:590] + b"\r\n", id="repository-592"),
        pytest.param(build_record()[0][:-1], id="short-3861"),
        pytest.param(build_record()[0] + b" ", id="long-3863"),
        pytest.param(b"XX" + build_record()[0][2:], id="wrong-record-type"),
        pytest.param(build_record()[0][:-2] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_ch_rejects_truncated_or_corrupt_physical_records(record: bytes) -> None:
    assert CHParser().parse(record) is None


def test_ch_normalized_schemas_match_official_cardinality_and_keys() -> None:
    assert set(get_table_column_types("NL_CH")) == NATIVE_HEADER_FIELDS
    assert set(get_table_column_types("CHOKYO")) == set(STANDARD_HEADER_ALIASES.values())
    assert set(get_table_column_types("NL_CH_SEISEKI")) == SEISEKI_FIELDS
    assert set(get_table_column_types("CHOKYO_SEISEKI")) == SEISEKI_FIELDS
    assert get_table_primary_key_columns("NL_CH") == ["ChokyosiCode"]
    assert get_table_primary_key_columns("CHOKYO") == ["ChokyosiCode"]
    assert get_table_primary_key_columns("NL_CH_SEISEKI") == ["ChokyosiCode", "Num"]
    assert get_table_primary_key_columns("CHOKYO_SEISEKI") == ["ChokyosiCode", "Num"]


@pytest.mark.parametrize(
    "importer_class,main_table,result_table,use_standard",
    [
        pytest.param(importer_class, main, result, standard, id=f"{importer_class.__name__}-{main}")
        for importer_class in (DataImporter, OptimizedDataImporter)
        for main, result, standard in (
            ("NL_CH", "NL_CH_SEISEKI", False),
            ("CHOKYO", "CHOKYO_SEISEKI", True),
        )
    ],
)
def test_ch_importers_store_header_and_three_complete_result_rows_idempotently(
    tmp_path, importer_class, main_table: str, result_table: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{main_table}.db")})
    record, expected_header, expected_results, _ = build_record()
    main_schema = JRAVAN_SCHEMAS[main_table] if use_standard else SCHEMAS[main_table]
    result_schema = JRAVAN_SCHEMAS[result_table] if use_standard else SCHEMAS[result_table]
    with database:
        database.create_table(main_table, main_schema)
        database.create_table(result_table, result_schema)
        importer = importer_class(database, use_jravan_schema=use_standard)
        first = importer.import_records(iter([CHParser().parse(record)]))
        second = importer.import_records(iter([CHParser().parse(record)]))
        main_row = database.fetch_one(f"SELECT * FROM {main_table}")
        result_rows = database.fetch_all(f"SELECT * FROM {result_table} ORDER BY Num")

    expected_native_header = {
        key: value for key, value in expected_header.items() if key != "RecordDelimiter"
    }
    if use_standard:
        expected_main = {
            STANDARD_HEADER_ALIASES[key]: value for key, value in expected_native_header.items()
        }
        numeric_main = {STANDARD_HEADER_ALIASES[key] for key in NUMERIC_HEADER_FIELDS}
    else:
        expected_main = expected_native_header
        numeric_main = NUMERIC_HEADER_FIELDS

    assert first["records_imported"] == 1
    assert first["records_failed"] == 0
    assert second["records_imported"] == 1
    assert second["records_failed"] == 0
    assert main_row == _expected_db_row(expected_main, numeric_main)
    assert result_rows == [
        _expected_db_row(row, NUMERIC_SEISEKI_FIELDS) for row in expected_results
    ]


@pytest.mark.parametrize(
    "main_table,result_table,use_standard",
    [
        pytest.param("NL_CH", "NL_CH_SEISEKI", False, id="native"),
        pytest.param("CHOKYO", "CHOKYO_SEISEKI", True, id="standard"),
    ],
)
def test_ch_single_record_api_stores_one_header_and_three_results(
    tmp_path, main_table: str, result_table: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"single-{main_table}.db")})
    main_schema = JRAVAN_SCHEMAS[main_table] if use_standard else SCHEMAS[main_table]
    result_schema = JRAVAN_SCHEMAS[result_table] if use_standard else SCHEMAS[result_table]
    parsed = CHParser().parse(build_record()[0])
    assert parsed is not None

    with database:
        database.create_table(main_table, main_schema)
        database.create_table(result_table, result_schema)
        inserted = DataImporter(database, use_jravan_schema=use_standard).import_single_record(
            parsed
        )
        main_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {main_table}")["count"]
        result_count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {result_table}")["count"]

    assert inserted is True
    assert main_count == 1
    assert result_count == 3


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_import_refuses_missing_result_table_before_main_mutation(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "missing-child.db")})
    with database:
        database.create_table("NL_CH", SCHEMAS["NL_CH"])
        with pytest.raises(SchemaMigrationError, match="NL_CH_SEISEKI"):
            importer_class(database).import_records(iter([CHParser().parse(build_record()[0])]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_import_refuses_incomplete_result_metadata_before_mutation(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "incomplete-metadata.db")})
    parsed = CHParser().parse(build_record()[0])
    assert parsed is not None
    parsed["_ch_seiseki_rows"] = parsed["_ch_seiseki_rows"][:2]
    with database:
        database.create_table("NL_CH", SCHEMAS["NL_CH"])
        database.create_table("NL_CH_SEISEKI", SCHEMAS["NL_CH_SEISEKI"])
        with pytest.raises(SchemaMigrationError, match="three"):
            importer_class(database).import_records(iter([parsed]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH")["count"] == 0
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH_SEISEKI")["count"] == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_coupled_child_failure_rolls_back_main_row(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "atomic.db")})
    child_schema = SCHEMAS["NL_CH_SEISEKI"].replace(
        "PRIMARY KEY (ChokyosiCode, Num)",
        "MustSupply TEXT NOT NULL, PRIMARY KEY (ChokyosiCode, Num)",
    )
    with database:
        database.create_table("NL_CH", SCHEMAS["NL_CH"])
        database.create_table("NL_CH_SEISEKI", child_schema)
        stats = importer_class(database).import_records(iter([CHParser().parse(build_record()[0])]))
        main_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH")["count"]
        child_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH_SEISEKI")["count"]

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert main_count == 0
    assert child_count == 0


OBSOLETE_NATIVE_CH = """
    CREATE TABLE IF NOT EXISTS NL_CH (
        RecordSpec TEXT,
        DataKubun TEXT,
        MakeDate TEXT,
        ChokyosiCode TEXT,
        ChokyosiName TEXT,
        SaikinJyusyo1_id TEXT,
        SetYear INTEGER,
        Reserved_591 TEXT,
        PRIMARY KEY (ChokyosiCode)
    )
"""


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_native_additive_migration_preserves_old_row_then_full_reimport(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "native-migration.db")})
    with database:
        database.execute(OBSOLETE_NATIVE_CH)
        database.execute(
            "INSERT INTO NL_CH "
            "(RecordSpec, DataKubun, MakeDate, ChokyosiCode, ChokyosiName, "
            "SaikinJyusyo1_id, SetYear, Reserved_591) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("CH", "1", "20000101", "C1234", "preserve-trainer", "legacy-win", 2000, "tail"),
        )
        database.commit()

        assert migrate_table_if_needed(database, "NL_CH", SCHEMAS["NL_CH"])
        database.create_table("NL_CH_SEISEKI", SCHEMAS["NL_CH_SEISEKI"])
        migrated = database.fetch_one(
            "SELECT ChokyosiCode, ChokyosiName, SetYear, Reserved_591, "
            "SaikinJyusyo2_id, SaikinJyusyo3_Bamei FROM NL_CH"
        )

        stats = importer_class(database).import_records(iter([CHParser().parse(build_record()[0])]))
        completed = database.fetch_one(
            "SELECT ChokyosiName, SaikinJyusyo2_id, SaikinJyusyo3_Bamei FROM NL_CH"
        )
        result_rows = database.fetch_one("SELECT COUNT(*) AS count FROM NL_CH_SEISEKI")

    assert migrated == {
        "ChokyosiCode": "C1234",
        "ChokyosiName": "preserve-trainer",
        "SetYear": 2000,
        "Reserved_591": "tail",
        "SaikinJyusyo2_id": None,
        "SaikinJyusyo3_Bamei": None,
    }
    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert completed == {
        "ChokyosiName": "Trainer Name Sentinel",
        "SaikinJyusyo2_id": "2026020105010102",
        "SaikinJyusyo3_Bamei": "Recent Winner Horse 3",
    }
    assert result_rows["count"] == 3


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_standard_keyless_header_fails_closed_without_row_loss(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "keyless-header.db")})
    keyless_header = JRAVAN_SCHEMAS["CHOKYO"].replace(
        ",\n            PRIMARY KEY (ChokyosiCode)", ""
    )
    with database:
        database.create_table("CHOKYO", keyless_header)
        database.create_table("CHOKYO_SEISEKI", JRAVAN_SCHEMAS["CHOKYO_SEISEKI"])
        database.execute(
            "INSERT INTO CHOKYO (RecordSpec, DataKubun, MakeDate, ChokyosiCode, ChokyosiName) "
            "VALUES (?, ?, ?, ?, ?)",
            ("ZZ", "9", "20000101", "OLD01", "preserve-header"),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([CHParser().parse(build_record()[0])])
            )
        rows = database.fetch_all("SELECT ChokyosiCode, ChokyosiName FROM CHOKYO")

    assert rows == [{"ChokyosiCode": "OLD01", "ChokyosiName": "preserve-header"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_standard_keyless_result_table_fails_closed_without_row_loss(
    tmp_path, importer_class
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "keyless-child.db")})
    keyless_child = JRAVAN_SCHEMAS["CHOKYO_SEISEKI"].replace(
        ",\n            PRIMARY KEY (ChokyosiCode, Num)", ""
    )
    with database:
        database.create_table("CHOKYO", JRAVAN_SCHEMAS["CHOKYO"])
        database.create_table("CHOKYO_SEISEKI", keyless_child)
        database.execute(
            "INSERT INTO CHOKYO_SEISEKI (MakeDate, ChokyosiCode, Num, SetYear) "
            "VALUES (?, ?, ?, ?)",
            ("20000101", "OLD01", 1, 2000),
        )
        database.commit()
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([CHParser().parse(build_record()[0])])
            )
        rows = database.fetch_all("SELECT ChokyosiCode, Num, SetYear FROM CHOKYO_SEISEKI")
        main_count = database.fetch_one("SELECT COUNT(*) AS count FROM CHOKYO")["count"]

    assert rows == [{"ChokyosiCode": "OLD01", "Num": 1, "SetYear": 2000}]
    assert main_count == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_postgresql_native_and_standard_store_all_coupled_rows(
    postgresql_db, importer_class
) -> None:
    for schema in (
        SCHEMAS["NL_CH"],
        SCHEMAS["NL_CH_SEISEKI"],
        JRAVAN_SCHEMAS["CHOKYO"],
        JRAVAN_SCHEMAS["CHOKYO_SEISEKI"],
    ):
        postgresql_db.execute(schema)
    postgresql_db.commit()

    parsed = CHParser().parse(build_record()[0])
    native = importer_class(postgresql_db).import_records(iter([parsed]))
    standard = importer_class(postgresql_db, use_jravan_schema=True).import_records(
        iter([CHParser().parse(build_record()[0])])
    )

    counts = {
        table: postgresql_db.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")["count"]
        for table in ("NL_CH", "NL_CH_SEISEKI", "CHOKYO", "CHOKYO_SEISEKI")
    }
    standard_header = postgresql_db.fetch_one(
        'SELECT DelDate AS "DelDate", SaikinJyusyo3Bamei AS "Bamei3" FROM CHOKYO'
    )
    standard_tail = postgresql_db.fetch_one(
        'SELECT Num AS "Num", Kyori6Chakukaisu6 AS "Tail" '
        "FROM CHOKYO_SEISEKI ORDER BY Num DESC LIMIT 1"
    )

    assert native["records_imported"] == 1
    assert native["records_failed"] == 0
    assert standard["records_imported"] == 1
    assert standard["records_failed"] == 0
    assert counts == {
        "NL_CH": 1,
        "NL_CH_SEISEKI": 3,
        "CHOKYO": 1,
        "CHOKYO_SEISEKI": 3,
    }
    assert standard_header == {"DelDate": "00000000", "Bamei3": "Recent Winner Horse 3"}
    assert standard_tail == {"Num": 3, "Tail": 516}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_ch_postgresql_child_failure_rolls_back_header(postgresql_db, importer_class) -> None:
    child_schema = SCHEMAS["NL_CH_SEISEKI"].replace(
        "PRIMARY KEY (ChokyosiCode, Num)",
        "MustSupply TEXT NOT NULL, PRIMARY KEY (ChokyosiCode, Num)",
    )
    postgresql_db.execute(SCHEMAS["NL_CH"])
    postgresql_db.execute(child_schema)
    postgresql_db.commit()

    stats = importer_class(postgresql_db).import_records(
        iter([CHParser().parse(build_record()[0])])
    )

    assert stats["records_imported"] == 0
    assert stats["records_failed"] == 1
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_CH")["count"] == 0
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_CH_SEISEKI")["count"] == 0
