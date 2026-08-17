"""Official format-29 TM parser and storage contract tests."""

import os
import re
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import TABLE_METADATA
from src.database.schema_types import get_table_column_types, get_table_primary_key_columns
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.tm_parser import TMParser
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
    schema_name = f"jlt_tm_{uuid4().hex[:12]}"
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


def _entry(umaban: str = "", score: str = "") -> bytes:
    number = umaban.encode("ascii")
    encoded_score = score.encode("ascii")
    assert len(number) <= 2
    assert len(encoded_score) <= 4
    result = number.ljust(2, b" ") + encoded_score.ljust(4, b" ")
    assert len(result) == 6
    return result


def _official_entries(*, score_offset: int = 0) -> list[bytes]:
    return [_entry(f"{index:02d}", f"{100 + score_offset + index:04d}") for index in range(1, 19)]


def _tm_record(
    *,
    data_kubun: str = "3",
    make_date: str = "20260816",
    make_hm: str = "0930",
    entries: list[bytes] | None = None,
    delimiter: bytes = b"\r\n",
) -> bytes:
    header = (
        b"TM"
        + data_kubun.encode("ascii")
        + make_date.encode("ascii")
        + b"2026"
        + b"0816"
        + b"05"
        + b"03"
        + b"08"
        + b"11"
        + make_hm.encode("ascii")
    )
    blocks = entries if entries is not None else _official_entries()
    assert len(blocks) == 18
    record = header + b"".join(blocks) + delimiter
    assert len(record) == 141
    return record


def _mutate(record: bytes, start: int, value: bytes) -> bytes:
    changed = bytearray(record)
    changed[start : start + len(value)] = value
    return bytes(changed)


def test_tm_parses_all_18_official_entries_by_exact_byte_offset() -> None:
    rows = TMParser().parse(_tm_record())

    assert TMParser.RECORD_LENGTH == 141
    assert isinstance(rows, list)
    assert len(rows) == 18
    assert [row["Umaban"] for row in rows] == [f"{index:02d}" for index in range(1, 19)]
    assert rows[0]["TMScore"] == "0101"
    assert rows[17]["TMScore"] == "0118"
    assert rows[0]["_wide_record"]["Umaban1"] == "01"
    assert rows[0]["_wide_record"]["TMScore18"] == "0118"
    assert rows[0]["_wide_record"] == rows[17]["_wide_record"]
    assert rows[0]["_tm_snapshot_rows"] is rows[17]["_tm_snapshot_rows"]
    assert len(rows[0]["_tm_snapshot_rows"]) == 18
    assert [row["_tm_snapshot_index"] for row in rows] == list(range(18))


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(_tm_record()[:37] + b"\r\n", id="repository-39-byte-truncation"),
        pytest.param(_tm_record()[:-1], id="short-140"),
        pytest.param(_tm_record() + b" ", id="long-142"),
        pytest.param(b"XX" + _tm_record()[2:], id="wrong-record-type"),
        pytest.param(_tm_record(delimiter=b"  "), id="missing-crlf"),
        pytest.param(_mutate(_tm_record(), 2, b"9"), id="invalid-data-kubun"),
        pytest.param(_mutate(_tm_record(), 3, b"2026A816"), id="invalid-make-date"),
        pytest.param(_mutate(_tm_record(), 31, b"19"), id="out-of-range-umaban"),
        pytest.param(_mutate(_tm_record(), 37, b"01"), id="duplicate-umaban"),
        pytest.param(_mutate(_tm_record(), 33, b"01A1"), id="non-numeric-score"),
        pytest.param(_mutate(_tm_record(), 33, b"1001"), id="score-over-100-point-0"),
        pytest.param(_tm_record(data_kubun="0"), id="delete-with-horse-payload"),
        pytest.param(
            _tm_record(entries=[_entry("", "0101"), *(_official_entries()[1:])]),
            id="blank-slot-with-payload",
        ),
    ],
)
def test_tm_rejects_truncated_or_corrupt_physical_records(record: bytes) -> None:
    assert TMParser().parse(record) is None


def test_tm_skips_empty_slots_but_preserves_all_wide_slots() -> None:
    entries = _official_entries()
    entries[1] = _entry()
    rows = TMParser().parse(_tm_record(entries=entries))

    assert rows is not None
    assert [row["Umaban"] for row in rows] == [
        "01",
        *[f"{index:02d}" for index in range(3, 19)],
    ]
    assert rows[0]["_wide_record"]["Umaban2"] == ""
    assert rows[0]["_wide_record"]["TMScore2"] == ""


def test_tm_preserves_blank_delete_record_for_race_level_delete() -> None:
    rows = TMParser().parse(_tm_record(data_kubun="0", entries=[_entry() for _ in range(18)]))

    assert rows == [
        {
            "RecordSpec": "TM",
            "DataKubun": "0",
            "MakeDate": "20260816",
            "Year": "2026",
            "MonthDay": "0816",
            "JyoCD": "05",
            "Kaiji": "03",
            "Nichiji": "08",
            "RaceNum": "11",
            "MakeHM": "0930",
        }
    ]
    assert RealtimeUpdater._expanded_record_delete_keys("RT_TM", rows[0]) == RACE_KEY


def test_tm_native_and_standard_schema_contracts_are_keyed_and_lossless() -> None:
    assert get_table_primary_key_columns("NL_TM") == NATIVE_KEY
    assert get_table_primary_key_columns("RT_TM") == NATIVE_KEY
    assert get_table_primary_key_columns("TAISENGATA_MINING") == RACE_KEY
    assert JRAVAN_TO_JLTSQL["TAISENGATA_MINING"] == "NL_TM"
    assert JLTSQL_TO_JRAVAN["NL_TM"] == "TAISENGATA_MINING"
    assert get_table_column_types("NL_TM")["TMScore"] == "TEXT"
    assert get_table_column_types("RT_TM")["TMScore"] == "TEXT"
    assert get_table_column_types("TAISENGATA_MINING")["TMScore1"] == "TEXT"
    assert len(re.findall(r"\bUmaban\d+\b", JRAVAN_SCHEMAS["TAISENGATA_MINING"])) == 18
    assert len(re.findall(r"\bTMScore\d+\b", JRAVAN_SCHEMAS["TAISENGATA_MINING"])) == 18


def test_tm_metadata_describes_the_complete_native_race_key() -> None:
    expected_key = [
        "開催年月日",
        "競馬場コード",
        "開催回",
        "開催日目",
        "レース番号",
        "馬番",
    ]

    for table_name in ("NL_TM", "RT_TM"):
        metadata = TABLE_METADATA[table_name]
        assert metadata["primary_key"] == expected_key
        column_names = {column["name"] for column in metadata["columns"]}
        assert set(expected_key) <= column_names


@pytest.mark.parametrize(
    "importer_class,table_name,use_standard,expected_count",
    [
        pytest.param(importer, table_name, standard, count, id=f"{importer.__name__}-{table_name}")
        for importer in (DataImporter, OptimizedDataImporter)
        for table_name, standard, count in (
            ("NL_TM", False, 18),
            ("TAISENGATA_MINING", True, 1),
        )
    ],
)
def test_tm_importers_preserve_every_entry_and_replace_one_race_revision(
    tmp_path, importer_class, table_name: str, use_standard: bool, expected_count: int
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, batch_size=3, use_jravan_schema=use_standard)
        first = TMParser().parse(_tm_record())
        corrected_entries = _official_entries(score_offset=100)
        corrected_entries[1] = _entry()
        corrected = TMParser().parse(_tm_record(make_hm="0945", entries=corrected_entries))
        assert first is not None and corrected is not None
        alias_key = "headRecordSpec" if importer_class is DataImporter else "レコード種別ID"
        for row in corrected:
            row[alias_key] = row.pop("RecordSpec")

        first_stats = importer.import_records(iter(first))
        corrected_stats = importer.import_records(iter(corrected))
        count = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

        if use_standard:
            stored = database.fetch_one(
                "SELECT MakeHM, Umaban1, TMScore1, Umaban2, TMScore2, "
                "Umaban18, TMScore18 FROM TAISENGATA_MINING"
            )
            assert stored == {
                "MakeHM": "0945",
                "Umaban1": 1,
                "TMScore1": "0201",
                "Umaban2": None,
                "TMScore2": None,
                "Umaban18": 18,
                "TMScore18": "0218",
            }
        else:
            stored = database.fetch_all("SELECT Umaban, MakeHM, TMScore FROM NL_TM ORDER BY Umaban")
            assert stored[0] == {"Umaban": 1, "MakeHM": "0945", "TMScore": "0201"}
            assert stored[-1] == {"Umaban": 18, "MakeHM": "0945", "TMScore": "0218"}
            assert all(row["Umaban"] != 2 for row in stored)

    assert first_stats["records_imported"] == expected_count
    assert first_stats["records_failed"] == 0
    assert corrected_stats["records_imported"] == (1 if use_standard else 17)
    assert corrected_stats["records_failed"] == 0
    assert count == (1 if use_standard else 17)


@pytest.mark.parametrize(
    "importer_class,table_name,use_standard",
    [
        pytest.param(importer, table_name, standard, id=f"{importer.__name__}-{table_name}")
        for importer in (DataImporter, OptimizedDataImporter)
        for table_name, standard in (
            ("NL_TM", False),
            ("TAISENGATA_MINING", True),
        )
    ],
)
def test_tm_accumulated_delete_removes_the_whole_race(
    tmp_path, importer_class, table_name: str, use_standard: bool
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"delete-{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_standard else SCHEMAS[table_name]
    with database:
        database.execute(schema)
        database.commit()
        importer = importer_class(database, use_jravan_schema=use_standard)
        inserted = TMParser().parse(_tm_record())
        deleted = TMParser().parse(
            _tm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
        )
        assert inserted is not None and deleted is not None

        importer.import_records(iter(inserted))
        delete_stats = importer.import_records(iter(deleted))
        remaining = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table_name}")["count"]

    assert delete_stats["records_imported"] == 1
    assert delete_stats["records_failed"] == 0
    assert remaining == 0


def test_tm_realtime_expansion_revision_and_race_delete(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "tm-realtime.db")})
    with database:
        database.execute(SCHEMAS["RT_TM"])
        database.commit()
        updater = RealtimeUpdater(database)

        first = updater.process_record(_tm_record())
        corrected_entries = _official_entries(score_offset=100)
        corrected_entries[1] = _entry()
        corrected = updater.process_record(_tm_record(make_hm="0945", entries=corrected_entries))
        rows = database.fetch_all("SELECT Umaban, MakeHM, TMScore FROM RT_TM ORDER BY Umaban")
        deleted = updater.process_record(
            _tm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
        )
        remaining = database.fetch_one("SELECT COUNT(*) AS count FROM RT_TM")["count"]

    assert isinstance(first, list) and len(first) == 18
    assert isinstance(corrected, list) and len(corrected) == 17
    assert all(result and result["success"] for result in first + corrected)
    assert len(rows) == 17
    assert rows[0] == {"Umaban": 1, "MakeHM": "0945", "TMScore": "0201"}
    assert rows[-1] == {"Umaban": 18, "MakeHM": "0945", "TMScore": "0218"}
    assert all(row["Umaban"] != 2 for row in rows)
    assert isinstance(deleted, list) and len(deleted) == 1
    assert deleted[0]["success"] is True
    assert remaining == 0


@pytest.mark.parametrize("caller_pending", (False, True))
def test_tm_realtime_snapshot_failure_rolls_back_the_active_transaction(
    tmp_path, monkeypatch, caller_pending
) -> None:
    # Keep this storage failure test independent of optional development
    # traceback renderers in compatibility environments.
    monkeypatch.setattr("src.realtime.updater.logger.error", lambda *args, **kwargs: None)
    database = SQLiteDatabase({"path": str(tmp_path / "tm-realtime-rollback.db")})
    with database:
        database.execute(SCHEMAS["RT_TM"])
        database.execute("CREATE TABLE CALLER_MARKER (id INTEGER PRIMARY KEY)")
        database.commit()
        updater = RealtimeUpdater(database)
        first = updater.process_record(_tm_record())
        assert isinstance(first, list) and all(result["success"] for result in first)
        database.commit()
        if caller_pending:
            database.execute("INSERT INTO CALLER_MARKER (id) VALUES (1)")
            assert database.has_pending_transaction() is True

        def fail_after_race_delete(*_args, **_kwargs):
            raise RuntimeError("injected snapshot insert failure")

        monkeypatch.setattr(database, "insert_many", fail_after_race_delete)
        failed = updater.process_record(
            _tm_record(make_hm="0945", entries=_official_entries(score_offset=100))
        )
        stored = database.fetch_all("SELECT Umaban, MakeHM, TMScore FROM RT_TM ORDER BY Umaban")
        transaction_pending = database.has_pending_transaction()
        marker_count = database.fetch_one(
            "SELECT COUNT(*) AS count FROM CALLER_MARKER"
        )["count"]

    assert isinstance(failed, list) and len(failed) == 18
    assert all(result["success"] is False for result in failed)
    assert len(stored) == 18
    assert stored[0] == {"Umaban": 1, "MakeHM": "0930", "TMScore": "0101"}
    assert stored[-1] == {"Umaban": 18, "MakeHM": "0930", "TMScore": "0118"}
    assert transaction_pending is False
    if caller_pending:
        assert marker_count == 0
    assert all(result["transaction_rolled_back"] is True for result in failed)


def test_tm_realtime_snapshot_recovery_failure_is_not_returned_as_safe(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("src.realtime.updater.logger.error", lambda *args, **kwargs: None)
    database = SQLiteDatabase({"path": str(tmp_path / "tm-realtime-recovery.db")})
    with database:
        database.execute(SCHEMAS["RT_TM"])
        database.commit()
        updater = RealtimeUpdater(database)

        original_insert_many = database.insert_many
        original_rollback = database.rollback
        original_invalidate = database.invalidate_connection
        monkeypatch.setattr(
            database,
            "insert_many",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("injected snapshot insert failure")
            ),
        )
        monkeypatch.setattr(
            database,
            "rollback",
            lambda: (_ for _ in ()).throw(RuntimeError("injected rollback failure")),
        )
        monkeypatch.setattr(
            database,
            "invalidate_connection",
            lambda: (_ for _ in ()).throw(RuntimeError("injected invalidation failure")),
        )
        try:
            with pytest.raises(RuntimeError, match="connection invalidation failed"):
                updater.process_record(_tm_record())
        finally:
            monkeypatch.setattr(database, "insert_many", original_insert_many)
            monkeypatch.setattr(database, "rollback", original_rollback)
            monkeypatch.setattr(database, "invalidate_connection", original_invalidate)
            database.rollback()


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_tm_standard_import_refuses_keyless_table_without_row_loss(
    tmp_path, importer_class
) -> None:
    keyed_tail = (
        "            TMScore18                      VARCHAR(4)          ,  -- 文字列(4)\n"
        "            PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    )
    keyless_tail = "            TMScore18                      VARCHAR(4)            -- 文字列(4)"
    keyless = JRAVAN_SCHEMAS["TAISENGATA_MINING"].replace(keyed_tail, keyless_tail)
    assert keyless != JRAVAN_SCHEMAS["TAISENGATA_MINING"]

    database = SQLiteDatabase({"path": str(tmp_path / "keyless-tm.db")})
    with database:
        database.execute(keyless)
        database.execute(
            "INSERT INTO TAISENGATA_MINING (RecordSpec, DataKubun, MakeDate, Year, "
            "MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, MakeHM) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000"),
        )
        database.commit()

        parsed = TMParser().parse(_tm_record())
        assert parsed is not None
        with pytest.raises(SchemaMigrationError, match="primary key"):
            importer_class(database, use_jravan_schema=True).import_records(iter(parsed))
        preserved = database.fetch_all("SELECT Year, RaceNum, MakeHM FROM TAISENGATA_MINING")

    assert preserved == [{"Year": 2000, "RaceNum": 1, "MakeHM": "0000"}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_tm_standard_import_refuses_legacy_time_master_without_row_loss(
    tmp_path, importer_class
) -> None:
    legacy = JRAVAN_SCHEMAS["TAISENGATA_MINING"].replace(
        "CREATE TABLE IF NOT EXISTS TAISENGATA_MINING",
        "CREATE TABLE IF NOT EXISTS TIME_MASTER",
        1,
    )
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-time-master.db")})
    with database:
        database.execute(legacy)
        database.execute(
            "INSERT INTO TIME_MASTER (RecordSpec, DataKubun, MakeDate, Year, MonthDay, "
            "JyoCD, Kaiji, Nichiji, RaceNum, MakeHM, TMScore1) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000", "0123"),
        )
        database.commit()

        parsed = TMParser().parse(_tm_record())
        assert parsed is not None
        with pytest.raises(SchemaMigrationError, match=r"TIME_MASTER.*TAISENGATA_MINING"):
            importer_class(database, use_jravan_schema=True).import_records(iter(parsed))
        preserved = database.fetch_one("SELECT TMScore1 FROM TIME_MASTER")

    assert preserved == {"TMScore1": "0123"}


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_tm_native_import_refuses_integer_score_schema_without_row_loss(
    tmp_path, importer_class
) -> None:
    legacy = SCHEMAS["NL_TM"].replace("TMScore TEXT", "TMScore INTEGER")
    assert legacy != SCHEMAS["NL_TM"]
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-native-tm.db")})
    with database:
        database.execute(legacy)
        database.execute(
            "INSERT INTO NL_TM (RecordSpec, DataKubun, MakeDate, Year, MonthDay, JyoCD, "
            "Kaiji, Nichiji, RaceNum, MakeHM, Umaban, TMScore) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000", 1, 123),
        )
        database.commit()

        parsed = TMParser().parse(_tm_record())
        assert parsed is not None
        alias_key = "headRecordSpec" if importer_class is DataImporter else "レコード種別ID"
        for row in parsed:
            row[alias_key] = row.pop("RecordSpec")
        with pytest.raises(SchemaMigrationError, match="incompatible column types"):
            importer_class(database).import_records(iter(parsed))
        preserved = database.fetch_all("SELECT Year, RaceNum, Umaban, TMScore FROM NL_TM")

    assert preserved == [{"Year": 2000, "RaceNum": 1, "Umaban": 1, "TMScore": 123}]


def test_tm_realtime_refuses_integer_score_schema_without_row_loss(tmp_path, monkeypatch) -> None:
    # Isolate the storage contract from optional rich/structlog renderer version
    # combinations in the compatibility test environment.
    monkeypatch.setattr("src.realtime.updater.logger.error", lambda *args, **kwargs: None)
    legacy = SCHEMAS["RT_TM"].replace("TMScore TEXT", "TMScore INTEGER")
    assert legacy != SCHEMAS["RT_TM"]
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-realtime-tm.db")})
    with database:
        database.execute(legacy)
        database.execute(
            "INSERT INTO RT_TM (RecordSpec, DataKubun, MakeDate, Year, MonthDay, JyoCD, "
            "Kaiji, Nichiji, RaceNum, MakeHM, Umaban, TMScore) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TM", "7", "20000101", 2000, 101, "05", 1, 1, 1, "0000", 1, 123),
        )
        database.commit()

        results = RealtimeUpdater(database).process_record(_tm_record())
        preserved = database.fetch_all("SELECT Year, RaceNum, Umaban, TMScore FROM RT_TM")

    assert isinstance(results, list) and len(results) == 18
    assert all(result["success"] is False for result in results)
    assert all("incompatible column types" in result["error"] for result in results)
    assert preserved == [{"Year": 2000, "RaceNum": 1, "Umaban": 1, "TMScore": 123}]


@pytest.mark.parametrize("importer_class", [DataImporter, OptimizedDataImporter])
def test_tm_postgresql_native_and_standard_revision_delete(postgresql_db, importer_class) -> None:
    postgresql_db.execute(SCHEMAS["NL_TM"])
    postgresql_db.execute(JRAVAN_SCHEMAS["TAISENGATA_MINING"])
    postgresql_db.commit()
    first = TMParser().parse(_tm_record())
    corrected_entries = _official_entries(score_offset=100)
    corrected_entries[1] = _entry()
    corrected = TMParser().parse(_tm_record(make_hm="0945", entries=corrected_entries))
    deleted = TMParser().parse(_tm_record(data_kubun="0", entries=[_entry() for _ in range(18)]))
    assert first is not None and corrected is not None and deleted is not None

    native = importer_class(postgresql_db)
    standard = importer_class(postgresql_db, use_jravan_schema=True)
    native.import_records(iter(first))
    standard.import_records(iter(TMParser().parse(_tm_record())))
    native.import_records(iter(corrected))
    standard.import_records(
        iter(TMParser().parse(_tm_record(make_hm="0945", entries=corrected_entries)))
    )

    native_rows = postgresql_db.fetch_all(
        'SELECT Umaban AS "Umaban", MakeHM AS "MakeHM", TMScore AS "TMScore" '
        "FROM NL_TM ORDER BY Umaban"
    )
    standard_row = postgresql_db.fetch_one(
        'SELECT MakeHM AS "MakeHM", Umaban1 AS "Umaban1", TMScore1 AS "TMScore1", '
        'Umaban2 AS "Umaban2", TMScore2 AS "TMScore2", Umaban18 AS "Umaban18", '
        'TMScore18 AS "TMScore18" FROM TAISENGATA_MINING'
    )
    assert len(native_rows) == 17
    assert dict(native_rows[0]) == {"Umaban": 1, "MakeHM": "0945", "TMScore": "0201"}
    assert all(row["Umaban"] != 2 for row in native_rows)
    assert dict(standard_row) == {
        "MakeHM": "0945",
        "Umaban1": 1,
        "TMScore1": "0201",
        "Umaban2": None,
        "TMScore2": None,
        "Umaban18": 18,
        "TMScore18": "0218",
    }

    native.import_records(iter(deleted))
    standard.import_records(
        iter(TMParser().parse(_tm_record(data_kubun="0", entries=[_entry() for _ in range(18)])))
    )
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM NL_TM")["count"] == 0
    assert postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM TAISENGATA_MINING")["count"] == 0


def test_tm_postgresql_realtime_snapshot_revision_delete(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["RT_TM"])
    postgresql_db.commit()
    updater = RealtimeUpdater(postgresql_db)
    corrected_entries = _official_entries(score_offset=100)
    corrected_entries[1] = _entry()

    postgresql_db.begin_transaction()
    first = updater.process_record(_tm_record())
    postgresql_db.commit()
    postgresql_db.begin_transaction()
    corrected = updater.process_record(_tm_record(make_hm="0945", entries=corrected_entries))
    realtime_rows = postgresql_db.fetch_all(
        'SELECT Umaban AS "Umaban", MakeHM AS "MakeHM", TMScore AS "TMScore" '
        "FROM RT_TM ORDER BY Umaban"
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
        "TMScore": "0201",
    }

    postgresql_db.execute("CREATE TABLE CALLER_MARKER (id INTEGER PRIMARY KEY)")
    postgresql_db.execute(
        "CREATE FUNCTION reject_tm_0950() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.makehm = '0950' THEN RAISE EXCEPTION 'simulated TM failure'; "
        "END IF; RETURN NEW; END $$"
    )
    postgresql_db.execute(
        "CREATE TRIGGER reject_tm_0950 BEFORE INSERT OR UPDATE ON RT_TM "
        "FOR EACH ROW EXECUTE FUNCTION reject_tm_0950()"
    )
    postgresql_db.commit()
    postgresql_db.execute("INSERT INTO CALLER_MARKER (id) VALUES (1)")
    assert postgresql_db.has_pending_transaction() is True
    failed = updater.process_record(_tm_record(make_hm="0950"))
    pending_after_failure = postgresql_db.has_pending_transaction()
    retained_after_failure = postgresql_db.fetch_one(
        "SELECT COUNT(*) AS count FROM RT_TM"
    )["count"]
    marker_after_failure = postgresql_db.fetch_one(
        "SELECT COUNT(*) AS count FROM CALLER_MARKER"
    )["count"]
    postgresql_db.commit()

    assert isinstance(failed, list) and len(failed) == 18
    assert all(result["success"] is False for result in failed)
    assert all(result["transaction_rolled_back"] is True for result in failed)
    assert pending_after_failure is False
    assert retained_after_failure == 17
    assert marker_after_failure == 0

    postgresql_db.begin_transaction()
    deleted = updater.process_record(
        _tm_record(data_kubun="0", entries=[_entry() for _ in range(18)])
    )
    remaining = postgresql_db.fetch_one("SELECT COUNT(*) AS count FROM RT_TM")["count"]
    postgresql_db.commit()

    assert isinstance(deleted, list) and len(deleted) == 1
    assert deleted[0]["success"] is True
    assert remaining == 0
