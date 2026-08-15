"""Official format-28 DM parser and storage contract tests."""

import os
import re
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_types import get_table_column_types, get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.dm_parser import DMParser
from src.realtime.updater import RealtimeUpdater

RACE_KEY = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"]
NATIVE_KEY = [*RACE_KEY, "Umaban"]


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
    schema_name = f"jlt_dm_{uuid4().hex[:12]}"
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


def _entry(
    umaban: str = "",
    dm_time: str = "",
    error_plus: str = "",
    error_minus: str = "",
) -> bytes:
    values = ((umaban, 2), (dm_time, 5), (error_plus, 4), (error_minus, 4))
    encoded = []
    for value, size in values:
        field = value.encode("ascii")
        assert len(field) <= size
        encoded.append(field.ljust(size, b" "))
    result = b"".join(encoded)
    assert len(result) == 15
    return result


def _official_entries(*, time_offset: int = 0) -> list[bytes]:
    return [
        _entry(
            f"{index:02d}",
            f"{10000 + time_offset + index:05d}",
            f"{100 + index:04d}",
            f"{200 + index:04d}",
        )
        for index in range(1, 19)
    ]


def _dm_record(
    *,
    data_kubun: str = "3",
    make_date: str = "20260815",
    make_hm: str = "0930",
    entries: list[bytes] | None = None,
    delimiter: bytes = b"\r\n",
) -> bytes:
    header = (
        b"DM"
        + data_kubun.encode("ascii")
        + make_date.encode("ascii")
        + b"2026"
        + b"0815"
        + b"05"
        + b"03"
        + b"08"
        + b"11"
        + make_hm.encode("ascii")
    )
    blocks = entries if entries is not None else _official_entries()
    assert len(blocks) == 18
    record = header + b"".join(blocks) + delimiter
    assert len(record) == 303
    return record


def _mutate(record: bytes, start: int, value: bytes) -> bytes:
    changed = bytearray(record)
    changed[start : start + len(value)] = value
    return bytes(changed)


def test_dm_parses_all_18_official_entries_by_exact_byte_offset() -> None:
    rows = DMParser().parse(_dm_record())

    assert DMParser.RECORD_LENGTH == 303
    assert isinstance(rows, list)
    assert len(rows) == 18
    assert [row["Umaban"] for row in rows] == [f"{index:02d}" for index in range(1, 19)]
    assert rows[0]["DMTime"] == "10001"
    assert rows[0]["DMGosaP"] == "0101"
    assert rows[17]["DMTime"] == "10018"
    assert rows[17]["DMGosaM"] == "0218"
    assert rows[0]["_wide_record"]["Umaban1"] == "01"
    assert rows[0]["_wide_record"]["DMTime18"] == "10018"
    assert rows[0]["_wide_record"] == rows[17]["_wide_record"]
    assert rows[0]["_dm_snapshot_rows"] is rows[17]["_dm_snapshot_rows"]
    assert len(rows[0]["_dm_snapshot_rows"]) == 18
    assert [row["_dm_snapshot_index"] for row in rows] == list(range(18))


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_dm_record()[:46] + b"\r\n", id="repository-48-byte-truncation"),
        pytest.param(_dm_record()[:-1], id="short-302"),
        pytest.param(_dm_record() + b" ", id="long-304"),
        pytest.param(b"XX" + _dm_record()[2:], id="wrong-record-type"),
        pytest.param(_dm_record(delimiter=b"  "), id="missing-crlf"),
        pytest.param(_mutate(_dm_record(), 2, b"9"), id="invalid-data-kubun"),
        pytest.param(_mutate(_dm_record(), 3, b"2026A815"), id="invalid-make-date"),
        pytest.param(_mutate(_dm_record(), 31, b"19"), id="out-of-range-umaban"),
        pytest.param(_mutate(_dm_record(), 46, b"01"), id="duplicate-umaban"),
        pytest.param(_mutate(_dm_record(), 33, b"12A45"), id="invalid-time"),
        pytest.param(_mutate(_dm_record(), 38, b"1A34"), id="invalid-plus-error"),
        pytest.param(_dm_record(data_kubun="0"), id="delete-with-horse-payload"),
        pytest.param(
            _dm_record(entries=[_entry("", "12345", "0123", "0456"), *(_official_entries()[1:])]),
            id="blank-slot-with-payload",
        ),
    ],
)
def test_dm_rejects_truncated_or_corrupt_physical_records(record: bytes) -> None:
    assert DMParser().parse(record) is None


def test_dm_skips_empty_slots_but_preserves_all_wide_slots() -> None:
    entries = _official_entries()
    entries[1] = _entry()
    rows = DMParser().parse(_dm_record(entries=entries))

    assert rows is not None
    assert [row["Umaban"] for row in rows] == [
        "01",
        *[f"{index:02d}" for index in range(3, 19)],
    ]
    assert rows[0]["_wide_record"]["Umaban2"] == ""
    assert rows[0]["_wide_record"]["DMTime2"] == ""


def test_dm_preserves_blank_delete_record_for_race_level_delete() -> None:
    rows = DMParser().parse(_dm_record(data_kubun="0", entries=[_entry() for _ in range(18)]))

    assert rows == [
        {
            "RecordSpec": "DM",
            "DataKubun": "0",
            "MakeDate": "20260815",
            "Year": "2026",
            "MonthDay": "0815",
            "JyoCD": "05",
            "Kaiji": "03",
            "Nichiji": "08",
            "RaceNum": "11",
            "MakeHM": "0930",
        }
    ]
    assert RealtimeUpdater._expanded_record_delete_keys("RT_DM", rows[0]) == RACE_KEY


def test_dm_native_and_standard_schema_contracts_are_keyed() -> None:
    assert get_table_primary_key_columns("NL_DM") == NATIVE_KEY
    assert get_table_primary_key_columns("RT_DM") == NATIVE_KEY
    assert get_table_primary_key_columns("MINING") == RACE_KEY
    assert JRAVAN_TO_JLTSQL["MINING"] == "NL_DM"
    assert JLTSQL_TO_JRAVAN["NL_DM"] == "MINING"
    assert get_table_column_types("MINING")["DMTime1"] == "TEXT"
    assert get_table_column_types("MINING")["DMTime18"] == "TEXT"
    assert len(re.findall(r"\bUmaban\d+\b", JRAVAN_SCHEMAS["MINING"])) == 18
    assert len(re.findall(r"\bDMTime\d+\b", JRAVAN_SCHEMAS["MINING"])) == 18


@pytest.mark.parametrize(
    "importer_class,table_name,use_standard,expected_count",
    [
        pytest.param(importer, table_name, standard, count, id=f"{importer.__name__}-{table_name}")
        for importer in (DataImporter, OptimizedDataImporter)
        for table_name, standard, count in (("NL_DM", False, 18), ("MINING", True, 1))
    ],
)
def test_dm_importers_preserve_every_entry_and_replace_one_race_revision(
    tmp_path, importer_class, table_name: str, use_standard: bool, expected_count: int
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, batch_size=3, use_jravan_schema=use_standard)
        first = DMParser().parse(_dm_record())
        corrected_entries = _official_entries(time_offset=500)
        corrected_entries[1] = _entry()
        corrected = DMParser().parse(_dm_record(make_hm="0945", entries=corrected_entries))
        assert first is not None and corrected is not None

        first_stats = importer.import_records(iter(first[:1]))
        follower_stats = importer.import_records(iter(first[1:]))
        corrected_stats = importer.import_records(iter(corrected))
        count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

        if use_standard:
            stored = database.fetch_one(
                "SELECT MakeHM, Umaban1, DMTime1, Umaban2, DMTime2, "
                "Umaban18, DMTime18 FROM MINING"
            )
            assert stored == {
                "MakeHM": "0945",
                "Umaban1": 1,
                "DMTime1": "10501",
                "Umaban2": None,
                "DMTime2": None,
                "Umaban18": 18,
                "DMTime18": "10518",
            }
        else:
            stored = database.fetch_all("SELECT Umaban, MakeHM, DMTime FROM NL_DM ORDER BY Umaban")
            assert stored[0] == {"Umaban": 1, "MakeHM": "0945", "DMTime": "10501"}
            assert stored[-1] == {"Umaban": 18, "MakeHM": "0945", "DMTime": "10518"}
            assert all(row["Umaban"] != 2 for row in stored)

    first_expected_stats = {
        "records_imported": expected_count,
        "records_failed": 0,
        "batches_processed": 1,
    }
    corrected_count = 1 if use_standard else 17
    corrected_expected_stats = {
        "records_imported": corrected_count,
        "records_failed": 0,
        "batches_processed": 1,
    }
    assert {key: first_stats[key] for key in first_expected_stats} == first_expected_stats
    assert {key: follower_stats[key] for key in first_expected_stats} == {
        "records_imported": 0,
        "records_failed": 0,
        "batches_processed": 0,
    }
    assert {
        key: corrected_stats[key] for key in corrected_expected_stats
    } == corrected_expected_stats
    assert count == corrected_count


@pytest.mark.parametrize(
    "importer_class,table_name,use_standard",
    [
        pytest.param(importer, table_name, standard, id=f"{importer.__name__}-{table_name}")
        for importer in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (("NL_DM", False), ("MINING", True))
    ],
)
def test_dm_accumulated_delete_removes_the_whole_race(
    tmp_path, importer_class, table_name: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, use_jravan_schema=use_standard)
        inserted = DMParser().parse(_dm_record())
        deleted = DMParser().parse(
            _dm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
        )
        assert inserted is not None and deleted is not None

        importer.import_records(iter(inserted))
        delete_stats = importer.import_records(iter(deleted))
        remaining = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

    expected_stats = {
        "records_imported": 1,
        "records_failed": 0,
        "batches_processed": 1,
    }
    assert {key: delete_stats[key] for key in expected_stats} == expected_stats
    assert remaining == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_dm_delete_respects_caller_owned_transaction(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "delete-transaction.db")})
    with database:
        database.execute(SCHEMAS["NL_DM"])
        database.commit()
        importer = importer_class(database)
        inserted = DMParser().parse(_dm_record())
        deleted = DMParser().parse(
            _dm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
        )
        assert inserted is not None and deleted is not None
        importer.import_records(iter(inserted))

        corrected_entries = _official_entries(time_offset=500)
        corrected_entries[1] = _entry()
        corrected = DMParser().parse(_dm_record(make_hm="0945", entries=corrected_entries))
        assert corrected is not None
        importer.import_records(iter(corrected), auto_commit=False)
        corrected_rows = database.fetch_all("SELECT Umaban, MakeHM FROM NL_DM ORDER BY Umaban")
        assert len(corrected_rows) == 17
        assert all(row["Umaban"] != 2 and row["MakeHM"] == "0945" for row in corrected_rows)
        database.rollback()
        restored_rows = database.fetch_all("SELECT Umaban, MakeHM FROM NL_DM ORDER BY Umaban")
        assert len(restored_rows) == 18
        assert all(row["MakeHM"] == "0930" for row in restored_rows)

        importer.import_records(iter(deleted), auto_commit=False)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_DM")["count"] == 0
        database.rollback()
        restored = database.fetch_one("SELECT COUNT(*) AS count FROM NL_DM")["count"]

    assert restored == 18


def test_dm_single_record_import_replaces_the_complete_native_snapshot(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "single-record.db")})
    with database:
        database.execute(SCHEMAS["NL_DM"])
        database.commit()
        importer = DataImporter(database)
        first = DMParser().parse(_dm_record())
        corrected_entries = _official_entries(time_offset=500)
        corrected_entries[1] = _entry()
        corrected = DMParser().parse(_dm_record(make_hm="0945", entries=corrected_entries))
        assert first is not None and corrected is not None

        assert importer.import_single_record(first[-1]) is True
        assert importer.import_single_record(corrected[0]) is True
        rows = database.fetch_all("SELECT Umaban, MakeHM FROM NL_DM ORDER BY Umaban")

    assert len(rows) == 17
    assert all(row["Umaban"] != 2 and row["MakeHM"] == "0945" for row in rows)


def test_dm_realtime_expansion_revision_and_race_delete(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "dm-realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_DM"])
        database.commit()
        updater = RealtimeUpdater(database)

        first = updater.process_record(_dm_record())
        corrected_entries = _official_entries(time_offset=500)
        corrected_entries[1] = _entry()
        corrected = updater.process_record(_dm_record(make_hm="0945", entries=corrected_entries))
        rows = database.fetch_all("SELECT Umaban, MakeHM, DMTime FROM RT_DM ORDER BY Umaban")

        deleted = updater.process_record(
            _dm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
        )
        remaining = database.fetch_one("SELECT COUNT(*) AS count FROM RT_DM")["count"]

    assert isinstance(first, list) and len(first) == 18
    assert isinstance(corrected, list) and len(corrected) == 17
    assert all(result and result["success"] for result in first + corrected)
    assert len(rows) == 17
    assert rows[0] == {"Umaban": 1, "MakeHM": "0945", "DMTime": "10501"}
    assert rows[-1] == {"Umaban": 18, "MakeHM": "0945", "DMTime": "10518"}
    assert all(row["Umaban"] != 2 for row in rows)
    assert isinstance(deleted, list) and len(deleted) == 1
    assert deleted[0]["success"] is True
    assert remaining == 0


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_dm_standard_import_refuses_keyless_mining_without_row_loss(
    tmp_path, importer_class
) -> None:
    keyed_tail = (
        "            DMGosaM18                      VARCHAR(4)          ,  -- 文字列(4)\n"
        "            PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    )
    keyless_tail = "            DMGosaM18                      VARCHAR(4)            -- 文字列(4)"
    keyless = JRAVAN_SCHEMAS["MINING"].replace(keyed_tail, keyless_tail)
    assert keyless != JRAVAN_SCHEMAS["MINING"], "MINING primary-key literal is stale"

    database = SQLiteDatabase({"path": str(tmp_path / "keyless-mining.db")})
    with database:
        database.execute(keyless)
        database.execute(
            "INSERT INTO MINING (RecordSpec, DataKubun, MakeDate, Year, MonthDay, "
            "JyoCD, Kaiji, Nichiji, RaceNum, MakeHM) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("DM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter(DMParser().parse(_dm_record()))
            )
        preserved = database.fetch_all("SELECT Year, RaceNum, MakeHM FROM MINING")

    assert preserved == [{"Year": 2000, "RaceNum": 1, "MakeHM": "0000"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_dm_standard_import_refuses_numeric_time_columns_without_row_loss(
    tmp_path, importer_class
) -> None:
    legacy = JRAVAN_SCHEMAS["MINING"]
    for index in range(1, 19):
        legacy = legacy.replace(
            f"DMTime{index:<2}                       VARCHAR(5)          ,",
            f"DMTime{index:<2}                       DECIMAL(6,1)        ,",
        )
    assert "DMTime1                        DECIMAL(6,1)" in legacy

    database = SQLiteDatabase({"path": str(tmp_path / "numeric-mining.db")})
    with database:
        database.execute(legacy)
        database.execute(
            "INSERT INTO MINING (RecordSpec, DataKubun, MakeDate, Year, MonthDay, "
            "JyoCD, Kaiji, Nichiji, RaceNum, MakeHM, DMTime1) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("DM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000", 1234.5),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="incompatible column types"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter(DMParser().parse(_dm_record()))
            )
        preserved = database.fetch_one("SELECT DMTime1 FROM MINING")

    assert preserved == {"DMTime1": 1234.5}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_dm_standard_import_refuses_legacy_data_master_without_row_loss(
    tmp_path, importer_class
) -> None:
    legacy = JRAVAN_SCHEMAS["MINING"].replace(
        "CREATE TABLE IF NOT EXISTS MINING",
        "CREATE TABLE IF NOT EXISTS DATA_MASTER",
        1,
    )
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-data-master.db")})
    with database:
        database.execute(legacy)
        database.execute(
            "INSERT INTO DATA_MASTER (RecordSpec, DataKubun, MakeDate, Year, MonthDay, "
            "JyoCD, Kaiji, Nichiji, RaceNum, MakeHM, DMTime1) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("DM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000", "12345"),
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="DATA_MASTER.*MINING"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter(DMParser().parse(_dm_record()))
            )
        preserved = database.fetch_one("SELECT DMTime1 FROM DATA_MASTER")

    assert preserved == {"DMTime1": "12345"}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_dm_postgresql_native_and_standard_revision_delete(postgresql_db, importer_class) -> None:
    postgresql_db.execute(SCHEMAS["NL_DM"])
    postgresql_db.execute(JRAVAN_SCHEMAS["MINING"])
    postgresql_db.commit()
    first = DMParser().parse(_dm_record())
    corrected_entries = _official_entries(time_offset=500)
    corrected_entries[1] = _entry()
    corrected = DMParser().parse(_dm_record(make_hm="0945", entries=corrected_entries))
    deleted = DMParser().parse(_dm_record(data_kubun="0", entries=[_entry() for _ in range(18)]))
    assert first is not None and corrected is not None and deleted is not None

    native = importer_class(postgresql_db)
    standard = importer_class(postgresql_db, use_jravan_schema=True)
    native.import_records(iter(first))
    standard.import_records(iter(DMParser().parse(_dm_record())))
    native.import_records(iter(corrected))
    standard.import_records(
        iter(DMParser().parse(_dm_record(make_hm="0945", entries=corrected_entries)))
    )

    native_rows = postgresql_db.fetch_all(
        'SELECT Umaban AS "Umaban", MakeHM AS "MakeHM", DMTime AS "DMTime" '
        "FROM NL_DM ORDER BY Umaban"
    )
    standard_row = postgresql_db.fetch_one(
        'SELECT MakeHM AS "MakeHM", Umaban1 AS "Umaban1", '
        'DMTime1 AS "DMTime1", Umaban2 AS "Umaban2", DMTime2 AS "DMTime2", '
        'Umaban18 AS "Umaban18", '
        'DMTime18 AS "DMTime18" FROM MINING'
    )
    assert len(native_rows) == 17
    assert dict(native_rows[0]) == {"Umaban": 1, "MakeHM": "0945", "DMTime": "10501"}
    assert all(row["Umaban"] != 2 for row in native_rows)
    assert dict(native_rows[-1]) == {
        "Umaban": 18,
        "MakeHM": "0945",
        "DMTime": "10518",
    }
    assert dict(standard_row) == {
        "MakeHM": "0945",
        "Umaban1": 1,
        "DMTime1": "10501",
        "Umaban2": None,
        "DMTime2": None,
        "Umaban18": 18,
        "DMTime18": "10518",
    }

    native.import_records(iter(deleted))
    standard.import_records(
        iter(DMParser().parse(_dm_record(data_kubun="0", entries=[_entry() for _ in range(18)])))
    )
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_DM")["count"] == 0
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM MINING")["count"] == 0


def test_dm_postgresql_realtime_snapshot_revision_delete(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["RT_DM"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    corrected_entries = _official_entries(time_offset=500)
    corrected_entries[1] = _entry()

    postgresql_db.begin_transaction()
    first = updater.process_record(_dm_record())
    postgresql_db.commit()
    postgresql_db.begin_transaction()
    corrected = updater.process_record(_dm_record(make_hm="0945", entries=corrected_entries))
    realtime_rows = postgresql_db.fetch_all(
        'SELECT Umaban AS "Umaban", MakeHM AS "MakeHM", DMTime AS "DMTime" '
        "FROM RT_DM ORDER BY Umaban"
    )
    postgresql_db.commit()

    assert isinstance(first, list) and len(first) == 18
    assert isinstance(corrected, list) and len(corrected) == 17
    assert all(result["success"] for result in first + corrected)
    assert len(realtime_rows) == 17
    assert all(row["Umaban"] != 2 for row in realtime_rows)
    assert dict(realtime_rows[0]) == {
        "Umaban": 1,
        "MakeHM": "0945",
        "DMTime": "10501",
    }

    postgresql_db.begin_transaction()
    deleted = updater.process_record(
        _dm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
    )
    remaining = postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM RT_DM")["count"]
    postgresql_db.commit()

    assert isinstance(deleted, list) and len(deleted) == 1
    assert deleted[0]["success"] is True
    assert remaining == 0
