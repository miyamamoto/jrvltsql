"""Official 1,272-byte RA parser and storage contract tests."""

import re

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
from src.parser.ra_parser import RAParser

RACE_KEY = ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"]


def _put(record: bytearray, position: int, size: int, value: str) -> None:
    encoded = value.encode("cp932")
    assert len(encoded) <= size
    record[position - 1 : position - 1 + size] = encoded.ljust(size, b" ")


def build_ra_record() -> bytes:
    """Build one full current RA record with sentinels in every repeated slot."""

    record = bytearray(b" " * RA_OFFICIAL_LENGTH)
    fixed = {
        (1, 2): "RA",
        (3, 1): "7",
        (4, 8): "20260815",
        (12, 4): "2026",
        (16, 4): "0815",
        (20, 2): "05",
        (22, 2): "03",
        (24, 2): "08",
        (26, 2): "11",
        (33, 60): "東京記念",
        (698, 4): "2000",
        (874, 4): "1540",
        (878, 4): "1535",
        (882, 2): "18",
        (884, 2): "16",
        (886, 2): "16",
        (888, 1): "1",
        (889, 1): "2",
        (890, 1): "3",
        (966, 4): "1572",
        (970, 3): "361",
        (973, 3): "482",
        (976, 3): "343",
        (979, 3): "464",
        (1270, 1): "2",
    }
    for (position, size), value in fixed.items():
        _put(record, position, size, value)

    for index in range(7):
        _put(record, 714 + 8 * index, 8, f"{1001 + index:08d}")
    for index in range(5):
        _put(record, 770 + 8 * index, 8, f"{2001 + index:08d}")
        _put(record, 810 + 8 * index, 8, f"{3001 + index:08d}")
    for index in range(3):
        _put(record, 850 + 8 * index, 8, f"{4001 + index:08d}")
    for index in range(25):
        _put(record, 891 + 3 * index, 3, f"{101 + index:03d}")
    for index in range(4):
        base = 982 + 72 * index
        _put(record, base, 1, str(index + 1))
        _put(record, base + 1, 1, "1")
        _put(record, base + 2, 70, f"0{index + 1},0{index + 2},0{index + 3}")

    record[1270:1272] = b"\r\n"
    return bytes(record)


RA_OFFICIAL_LENGTH = 1272


def _invalid_cp932_record() -> bytes:
    record = bytearray(build_ra_record())
    record[32:34] = b"\x81\x20"
    return bytes(record)


def test_ra_parses_every_official_repeated_field() -> None:
    row = RAParser().parse(build_ra_record())

    assert row is not None
    assert RAParser.RECORD_LENGTH == RA_OFFICIAL_LENGTH
    assert row["RecordSpec"] == "RA"
    assert row["Hondai"] == "東京記念"
    assert [row[f"Honsyokin{i}"] for i in range(1, 8)] == [f"{1000 + i:08d}" for i in range(1, 8)]
    assert [row[f"HonsyokinBefore{i}"] for i in range(1, 6)] == [
        f"{2000 + i:08d}" for i in range(1, 6)
    ]
    assert [row[f"Fukasyokin{i}"] for i in range(1, 6)] == [f"{3000 + i:08d}" for i in range(1, 6)]
    assert [row[f"FukasyokinBefore{i}"] for i in range(1, 4)] == [
        f"{4000 + i:08d}" for i in range(1, 4)
    ]
    assert [row[f"LapTime{i}"] for i in range(1, 26)] == [f"{100 + i:03d}" for i in range(1, 26)]
    assert row["HaronTimeS3"] == "361"
    assert row["HaronTimeL4"] == "464"
    assert [row[f"Corner{i}"] for i in range(1, 5)] == ["1", "2", "3", "4"]
    assert [row[f"Jyuni{i}"] for i in range(1, 5)] == [
        "01,02,03",
        "02,03,04",
        "03,04,05",
        "04,05,06",
    ]
    assert row["RecordUpKubun"] == "2"


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(build_ra_record()[:856], id="non-official-856"),
        pytest.param(build_ra_record()[:1271], id="short-1271"),
        pytest.param(build_ra_record() + b" ", id="long-1273"),
        pytest.param(b"XX" + build_ra_record()[2:], id="wrong-record-type"),
        pytest.param(build_ra_record()[:1270] + b"  ", id="missing-crlf"),
        pytest.param(_invalid_cp932_record(), id="invalid-cp932"),
    ],
)
def test_ra_rejects_non_official_record_boundaries(record: bytes) -> None:
    assert RAParser().parse(record) is None


def test_ra_native_and_standard_schemas_store_the_complete_contract() -> None:
    repeated_fields = {
        *[f"Honsyokin{i}" for i in range(1, 8)],
        *[f"HonsyokinBefore{i}" for i in range(1, 6)],
        *[f"Fukasyokin{i}" for i in range(1, 6)],
        *[f"FukasyokinBefore{i}" for i in range(1, 4)],
        *[f"LapTime{i}" for i in range(1, 26)],
    }
    native_corner_fields = {
        *[f"Corner{i}" for i in range(2, 5)],
        *[f"Syukaisu{i}" for i in range(2, 5)],
        *[f"TsukaJyuni{i}" for i in range(2, 5)],
        "Corner",
        "Syukaisu",
        "TsukaJyuni",
    }
    standard_corner_fields = {
        *[f"Corner{i}" for i in range(1, 5)],
        *[f"Syukaisu{i}" for i in range(1, 5)],
        *[f"Jyuni{i}" for i in range(1, 5)],
    }

    for table_name in ("NL_RA", "RT_RA"):
        columns = set(get_table_column_types(table_name))
        assert repeated_fields | native_corner_fields <= columns
        assert get_table_primary_key_columns(table_name) == RACE_KEY

    assert repeated_fields | standard_corner_fields <= set(get_table_column_types("RACE"))
    assert get_table_primary_key_columns("RACE") == RACE_KEY


def test_existing_keyless_standard_race_table_fails_closed_without_data_loss(tmp_path) -> None:
    schema = JRAVAN_SCHEMAS["RACE"]
    keyless_schema = re.sub(
        r"^(\s*RecordUpKubun\s+VARCHAR\(1\)\s*),(\s*--[^\n]*)\n" r"\s*PRIMARY KEY\s*\([^)]*\)\s*$",
        r"\1\2",
        schema,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    assert keyless_schema != schema

    database = SQLiteDatabase({"path": str(tmp_path / "keyless-race.db")})
    with database:
        database.execute(keyless_schema)
        database.execute(
            "INSERT INTO RACE (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum) "
            "VALUES (2026, 815, '05', 3, 8, 11)"
        )
        database.commit()

        with pytest.raises(SchemaMigrationError, match="primary key"):
            DataImporter(database, use_jravan_schema=True).import_records(
                iter([RAParser().parse(build_ra_record())])
            )

        assert database.fetch_one("SELECT COUNT(*) AS count FROM RACE")["count"] == 1


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
@pytest.mark.parametrize(
    ("table_name", "use_jravan_schema"),
    (("NL_RA", False), ("RACE", True)),
)
def test_ra_full_record_round_trips_without_array_loss(
    tmp_path,
    importer_class,
    table_name,
    use_jravan_schema,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"{table_name}.db")})
    schema = JRAVAN_SCHEMAS[table_name] if use_jravan_schema else SCHEMAS[table_name]
    with database:
        database.create_table(table_name, schema)
        parsed = RAParser().parse(build_ra_record())
        assert parsed is not None
        stats = importer_class(
            database,
            use_jravan_schema=use_jravan_schema,
        ).import_records(iter([parsed]))
        if use_jravan_schema:
            row = database.fetch_one(
                "SELECT Honsyokin7, HonsyokinBefore5, Fukasyokin5, "
                "FukasyokinBefore3, LapTime25, SyogaiMileTime, HaronTimeL4, "
                "Corner1, Jyuni1, Corner4, Jyuni4 FROM RACE"
            )
        else:
            row = database.fetch_one(
                "SELECT Honsyokin7, HonsyokinBefore5, Fukasyokin5, "
                "FukasyokinBefore3, LapTime25, SyogaiMileTime, Haron4L, "
                "Corner, TsukaJyuni, Corner4, TsukaJyuni4 FROM NL_RA"
            )

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert row["Honsyokin7"] == 1007
    assert row["HonsyokinBefore5"] == 2005
    assert row["Fukasyokin5"] == 3005
    assert row["FukasyokinBefore3"] == 4003
    assert row["LapTime25"] == 12.5
    if use_jravan_schema:
        assert row["SyogaiMileTime"] == 157.2
        assert row["HaronTimeL4"] == 46.4
        assert row["Corner1"] == "1"
        assert row["Jyuni1"] == "01,02,03"
        assert row["Jyuni4"] == "04,05,06"
    else:
        assert row["SyogaiMileTime"] == "1572"
        assert row["Haron4L"] == 46.4
        assert row["Corner"] == "1"
        assert row["TsukaJyuni"] == "01,02,03"
        assert row["TsukaJyuni4"] == "04,05,06"
