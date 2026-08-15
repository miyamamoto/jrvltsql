"""Official format-101 (WH horse-weight) parser and storage contract tests."""

import os
import re
from uuid import uuid4

import pytest

from src.database.migration import SchemaMigrationError, verify_table_schema
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.database.table_mappings import JLTSQL_TO_JRAVAN, JRAVAN_TO_JLTSQL
from src.importer.importer import DataImporter
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.wh_parser import WHParser
from src.realtime.updater import RealtimeUpdater


def _field(value: str, length: int) -> bytes:
    encoded = value.encode("cp932")
    assert len(encoded) <= length
    return encoded.ljust(length, b" ")


def _horse(umaban: str, name: str, weight: str, sign: str, delta: str) -> bytes:
    entry = (
        _field(umaban, 2)
        + _field(name, 36)
        + _field(weight, 3)
        + _field(sign, 1)
        + _field(delta, 3)
    )
    assert len(entry) == 45
    return entry


def _wh_record(
    *,
    announcement: str = "06150930",
    weight: str = "480",
    delimiter: bytes = b"\r\n",
    data_kubun: str = "1",
    include_horses: bool = True,
    make_date: str = "20260815",
    year: str = "2026",
    month_day: str = "0815",
) -> bytes:
    header = (
        b"WH"
        + data_kubun.encode("ascii")
        + make_date.encode("ascii")
        + year.encode("ascii")
        + month_day.encode("ascii")
        + b"05"
        + b"03"
        + b"08"
        + b"11"
        + announcement.encode("ascii")
    )
    horses = (
        [
            _horse("01", "日本馬", weight, "+", "005"),
            *[b" " * 45 for _ in range(16)],
            _horse("18", "最終枠", "999", " ", "999"),
        ]
        if include_horses
        else [b" " * 45 for _ in range(18)]
    )
    record = header + b"".join(horses) + delimiter
    assert len(record) == 847
    return record


def _invalid_cp932_record() -> bytes:
    record = bytearray(_wh_record())
    record[37:39] = b"\x81\x20"
    return bytes(record)


def _mutated_record(start: int, value: bytes) -> bytes:
    record = bytearray(_wh_record())
    record[start : start + len(value)] = value
    return bytes(record)


def _primary_key(ddl: str) -> list[str]:
    match = re.search(r"PRIMARY KEY \(([^)]*)\)", ddl)
    assert match
    return [column.strip() for column in match.group(1).split(",")]


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
    schema_name = f"jlt_wh_{uuid4().hex[:12]}"
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


def test_wh_parses_official_847_byte_record_by_byte_offset() -> None:
    rows = WHParser().parse(_wh_record())

    assert rows is not None
    assert len(rows) == 2
    assert {key: value for key, value in rows[0].items() if not key.startswith("_")} == {
        "RecordSpec": "WH",
        "DataKubun": "1",
        "MakeDate": "20260815",
        "Year": "2026",
        "MonthDay": "0815",
        "JyoCD": "05",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HappyoTime": "06150930",
        "Umaban": "01",
        "Bamei": "日本馬",
        "BaTaijyu": "480",
        "ZogenFugo": "+",
        "ZogenSa": "005",
    }
    assert rows[1]["Umaban"] == "18"
    assert rows[1]["Bamei"] == "最終枠"
    assert rows[1]["BaTaijyu"] == "999"
    assert rows[1]["ZogenFugo"] == ""
    assert rows[1]["ZogenSa"] == "999"
    assert rows[0]["_wide_record"]["Umaban1"] == "01"
    assert rows[0]["_wide_record"]["Umaban18"] == "18"


@pytest.mark.parametrize(
    "record",
    [
        # The repository's former 40-byte WE-like shape was never a WH format.
        b"WH1" + b"0" * 37,
        _wh_record(delimiter=b"  "),
        _wh_record()[:-1],
        _wh_record(include_horses=False),
        _invalid_cp932_record(),
        _mutated_record(2, b"2"),
        _mutated_record(3, b"2026A815"),
        _mutated_record(35, b"19"),
        _mutated_record(800, b"01"),
        _mutated_record(73, b"ABC"),
        _mutated_record(73, b"001"),
        _mutated_record(76, b"*"),
        _mutated_record(77, b"ABC"),
        _mutated_record(82, b"A"),
    ],
    ids=[
        "former-weather-shape",
        "missing-crlf",
        "short-record",
        "no-horses",
        "invalid-cp932",
        "invalid-data-kubun",
        "invalid-numeric-header",
        "out-of-range-umaban",
        "duplicate-umaban",
        "invalid-weight",
        "reserved-weight-001",
        "invalid-change-sign",
        "invalid-change-amount",
        "empty-slot-with-payload",
    ],
)
def test_wh_rejects_non_official_record_boundaries(record: bytes) -> None:
    assert WHParser().parse(record) is None


def test_wh_accepts_official_zero_initialized_unused_slots() -> None:
    record = bytearray(_wh_record())
    for index in range(1, 17):
        start = 35 + index * 45
        record[start : start + 2] = b"00"

    rows = WHParser().parse(bytes(record))

    assert rows is not None
    assert [row["Umaban"] for row in rows] == ["01", "18"]


def test_wh_preserves_pre_2003_delete_record_for_race_level_delete() -> None:
    """DataKubun=0 was removed in 2003, but old records remain actionable."""

    rows = WHParser().parse(
        _wh_record(
            data_kubun="0",
            include_horses=False,
            make_date="20030710",
            year="2003",
            month_day="0710",
        )
    )

    assert rows == [
        {
            "RecordSpec": "WH",
            "DataKubun": "0",
            "MakeDate": "20030710",
            "Year": "2003",
            "MonthDay": "0710",
            "JyoCD": "05",
            "Kaiji": "03",
            "Nichiji": "08",
            "RaceNum": "11",
            "HappyoTime": "06150930",
        }
    ]
    assert RealtimeUpdater._expanded_record_delete_keys("RT_WH", rows[0]) == [
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
    ]


def test_wh_realtime_insert_and_pre_2003_race_delete(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wh-realtime.db")})
    database.connect()
    try:
        database.execute(SCHEMAS["RT_WH"])
        database.commit()
        updater = RealtimeUpdater(database)
        historical = _wh_record(
            make_date="20030710",
            year="2003",
            month_day="0710",
        )

        inserted = updater.process_record(historical)

        assert isinstance(inserted, list)
        assert len(inserted) == 2
        assert all(result and result["success"] for result in inserted)
        assert database.fetch_one("SELECT COUNT(*) AS count FROM RT_WH")["count"] == 2

        deleted = updater.process_record(
            _wh_record(
                data_kubun="0",
                include_horses=False,
                make_date="20030710",
                year="2003",
                month_day="0710",
            )
        )

        assert isinstance(deleted, list)
        assert len(deleted) == 1
        assert deleted[0]["success"] is True
        assert database.fetch_one("SELECT COUNT(*) AS count FROM RT_WH")["count"] == 0
    finally:
        database.disconnect()


def test_wh_native_schema_matches_expanded_official_rows() -> None:
    expected_columns = {
        "RaceNum",
        "HappyoTime",
        "Umaban",
        "Bamei",
        "BaTaijyu",
        "ZogenFugo",
        "ZogenSa",
    }
    forbidden_weather_columns = {
        "HenkoID",
        "AtoTenkoCD",
        "AtoSibaBabaCD",
        "AtoDirtBabaCD",
        "MaeTenkoCD",
        "MaeSibaBabaCD",
        "MaeDirtBabaCD",
    }
    expected_key = [
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
        "Umaban",
    ]

    for table_name in ("NL_WH", "RT_WH"):
        ddl = SCHEMAS[table_name]
        assert expected_columns <= set(re.findall(r"^\s+(\w+)\s+\w+", ddl, re.MULTILINE))
        assert forbidden_weather_columns.isdisjoint(ddl)
        assert _primary_key(ddl) == expected_key


def test_wh_maps_to_official_bataijyu_table_name() -> None:
    assert "BABA" not in JRAVAN_TO_JLTSQL
    assert JRAVAN_TO_JLTSQL["BATAIJYU"] == "NL_WH"
    assert JLTSQL_TO_JRAVAN["NL_WH"] == "BATAIJYU"


def test_wh_latest_announcement_replaces_same_race_horse(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wh.db")})
    database.connect()
    try:
        database.execute(SCHEMAS["NL_WH"])
        database.commit()
        importer = DataImporter(database)

        first = WHParser().parse(_wh_record())
        corrected = WHParser().parse(_wh_record(announcement="06150935", weight="486"))
        assert first is not None and corrected is not None
        assert importer.import_records(iter(first))["records_imported"] == 2
        assert importer.import_records(iter(corrected))["records_imported"] == 2

        rows = database.fetch_all(
            "SELECT Umaban, HappyoTime, BaTaijyu, ZogenSa " "FROM NL_WH ORDER BY Umaban"
        )
        assert [dict(row) for row in rows] == [
            {
                "Umaban": 1,
                "HappyoTime": "06150935",
                "BaTaijyu": 486,
                "ZogenSa": 5,
            },
            {
                "Umaban": 18,
                "HappyoTime": "06150935",
                "BaTaijyu": 999,
                "ZogenSa": 999,
            },
        ]
    finally:
        database.disconnect()


@pytest.mark.parametrize(
    "importer_class",
    [DataImporter, OptimizedDataImporter],
    ids=["regular", "optimized"],
)
def test_wh_standard_schema_import_preserves_all_horse_slots(tmp_path, importer_class) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "wh-standard.db")})
    database.connect()
    try:
        database.execute(JRAVAN_SCHEMAS["BATAIJYU"])
        database.commit()
        rows = WHParser().parse(_wh_record())
        assert rows is not None

        importer = importer_class(database, use_jravan_schema=True)
        importer.import_records(iter(rows))
        corrected = WHParser().parse(_wh_record(announcement="06150935", weight="486"))
        assert corrected is not None
        importer.import_records(iter(corrected))

        stored = database.fetch_all(
            "SELECT HappyoTime, Umaban1, Bamei1, BaTaijyu1, ZogenSa1, "
            "Umaban18, Bamei18, BaTaijyu18, ZogenSa18 FROM BATAIJYU"
        )
        assert [dict(row) for row in stored] == [
            {
                "HappyoTime": "06150935",
                "Umaban1": 1,
                "Bamei1": "日本馬",
                "BaTaijyu1": 486,
                "ZogenSa1": 5,
                "Umaban18": 18,
                "Bamei18": "最終枠",
                "BaTaijyu18": 999,
                "ZogenSa18": 999,
            }
        ]
    finally:
        database.disconnect()


def test_wh_legacy_standard_table_requires_operator_migration(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-standard-wh.db")})
    database.connect()
    try:
        legacy_ddl = JRAVAN_SCHEMAS["BATAIJYU"].replace(
            ",  -- 増減(kg)\n            PRIMARY KEY "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)",
            "   -- 増減(kg)",
        )
        assert "PRIMARY KEY" not in legacy_ddl
        database.execute(legacy_ddl)
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            verify_table_schema(database, "BATAIJYU", JRAVAN_SCHEMAS["BATAIJYU"])
    finally:
        database.disconnect()


def test_wh_legacy_weather_table_requires_operator_migration(tmp_path) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "legacy-wh.db")})
    database.connect()
    try:
        legacy_ddl = """
            CREATE TABLE LEGACY_WH (
                RecordSpec TEXT,
                DataKubun TEXT,
                MakeDate TEXT,
                Year INTEGER,
                MonthDay INTEGER,
                JyoCD TEXT,
                Kaiji INTEGER,
                Nichiji INTEGER,
                HappyoTime TEXT,
                HenkoID TEXT,
                AtoTenkoCD TEXT,
                AtoSibaBabaCD TEXT,
                AtoDirtBabaCD TEXT,
                MaeTenkoCD TEXT,
                MaeSibaBabaCD TEXT,
                MaeDirtBabaCD TEXT,
                PRIMARY KEY (
                    Year, MonthDay, JyoCD, Kaiji, Nichiji, HappyoTime, HenkoID
                )
            )
        """
        database.execute(legacy_ddl)
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            verify_table_schema(database, "LEGACY_WH", SCHEMAS["NL_WH"])
    finally:
        database.disconnect()


def test_wh_postgresql_native_and_standard_storage(postgresql_db) -> None:
    postgresql_db.execute(SCHEMAS["NL_WH"])
    postgresql_db.execute(JRAVAN_SCHEMAS["BATAIJYU"])
    postgresql_db.commit()
    rows = WHParser().parse(_wh_record())
    assert rows is not None

    DataImporter(postgresql_db).import_records(iter(rows))
    DataImporter(postgresql_db, use_jravan_schema=True).import_records(iter(rows))

    native = postgresql_db.fetch_all(
        "SELECT Umaban AS umaban, BaTaijyu AS weight " "FROM NL_WH ORDER BY Umaban"
    )
    standard = postgresql_db.fetch_all(
        "SELECT Umaban1 AS umaban1, BaTaijyu1 AS weight1, "
        "Umaban18 AS umaban18, BaTaijyu18 AS weight18 FROM BATAIJYU"
    )
    assert [(row["umaban"], row["weight"]) for row in native] == [
        (1, 480),
        (18, 999),
    ]
    assert [dict(row) for row in standard] == [
        {"umaban1": 1, "weight1": 480, "umaban18": 18, "weight18": 999}
    ]
