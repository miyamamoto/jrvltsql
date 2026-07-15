"""Regression tests for additive migration of the corrected SE layout."""

import pytest

from src.database.migration import migrate_all_tables
from src.database.schema import SCHEMAS, SchemaManager
from src.database.sqlite_handler import SQLiteDatabase
from src.services.realtime_monitor import RealtimeMonitor


def _obsolete_se_schema(table_name: str) -> str:
    """Recreate the pre-fix schema while retaining the production primary key."""
    schema = SCHEMAS[table_name]
    for definition in (
        "            KettoNum2 TEXT,\n",
        "            Bamei2 TEXT,\n",
        "            KettoNum3 TEXT,\n",
        "            Bamei3 TEXT,\n",
    ):
        schema = schema.replace(definition, "")
    schema = schema.replace(
        "            KyakusituKubun TEXT,\n            PRIMARY KEY",
        "            KyakusituKubun TEXT,\n"
        "            Reserved_462 TEXT,\n"
        "            PRIMARY KEY",
    )
    return schema


@pytest.mark.parametrize("table_name", ["NL_SE", "RT_SE"])
def test_corrected_se_columns_are_added_without_dropping_existing_rows(
    tmp_path, table_name
):
    db = SQLiteDatabase({"path": str(tmp_path / f"{table_name.lower()}.db")})
    with db:
        db.execute(_obsolete_se_schema(table_name))
        db.execute(
            f"INSERT INTO {table_name} "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, "
            "KettoNum1, Bamei1, Reserved_462) "
            "VALUES (2026, 714, '05', 2, 3, 11, 7, "
            "'2020100001', 'WINNER-ONE', 'legacy')"
        )
        db.commit()

        assert migrate_all_tables(db, {table_name: SCHEMAS[table_name]}) == 1

        columns = {
            row["name"] for row in db.fetch_all(f"PRAGMA table_info({table_name})")
        }
        row = db.fetch_one(
            f"SELECT KettoNum1, Bamei1, KettoNum2, Bamei2, KettoNum3, Bamei3, "
            f"Reserved_462 FROM {table_name}"
        )

    assert {"KettoNum2", "Bamei2", "KettoNum3", "Bamei3"} <= columns
    assert "Reserved_462" in columns
    assert row == {
        "KettoNum1": "2020100001",
        "Bamei1": "WINNER-ONE",
        "KettoNum2": None,
        "Bamei2": None,
        "KettoNum3": None,
        "Bamei3": None,
        "Reserved_462": "legacy",
    }


def test_schema_manager_migrates_existing_rt_se_without_dropping_rows(tmp_path):
    db = SQLiteDatabase({"path": str(tmp_path / "manager.db")})
    with db:
        db.execute(_obsolete_se_schema("RT_SE"))
        db.execute(
            "INSERT INTO RT_SE "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, "
            "KettoNum1, Bamei1, Reserved_462) "
            "VALUES (2026, 714, '05', 2, 3, 11, 7, "
            "'2020100001', 'WINNER-ONE', 'legacy')"
        )
        db.commit()

        results = SchemaManager(db).create_all_tables()
        columns = {
            row["name"] for row in db.fetch_all("PRAGMA table_info(RT_SE)")
        }
        row_count = db.fetch_one("SELECT COUNT(*) AS count FROM RT_SE")["count"]

    assert all(results.values())
    assert {"KettoNum2", "Bamei2", "KettoNum3", "Bamei3"} <= columns
    assert row_count == 1


def test_schema_manager_create_table_migrates_existing_se(tmp_path):
    db = SQLiteDatabase({"path": str(tmp_path / "single-table.db")})
    with db:
        db.execute(_obsolete_se_schema("NL_SE"))
        assert SchemaManager(db).create_table("NL_SE") is True
        columns = {
            row["name"] for row in db.fetch_all("PRAGMA table_info(NL_SE)")
        }

    assert {"KettoNum2", "Bamei2", "KettoNum3", "Bamei3"} <= columns


def test_schema_manager_rejects_unsafe_primary_key_mismatch(tmp_path):
    db = SQLiteDatabase({"path": str(tmp_path / "unsafe-pk.db")})
    unsafe_schema = SCHEMAS["NL_SE"].replace(
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)",
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)",
    )
    with db:
        db.execute(unsafe_schema)
        assert SchemaManager(db).create_table("NL_SE") is False

        columns = {
            row["name"] for row in db.fetch_all("PRAGMA table_info(NL_SE)")
        }

    assert "KettoNum3" in columns


def test_realtime_startup_migrates_rt_se_when_no_tables_are_missing(tmp_path):
    db = SQLiteDatabase({"path": str(tmp_path / "realtime.db")})
    with db:
        for table_name, schema in SCHEMAS.items():
            db.execute(
                _obsolete_se_schema(table_name)
                if table_name == "RT_SE"
                else schema
            )
        db.commit()
        assert SchemaManager(db).get_missing_tables() == []

        RealtimeMonitor(database=db)._ensure_tables()
        columns = {
            row["name"] for row in db.fetch_all("PRAGMA table_info(RT_SE)")
        }

    assert {"KettoNum2", "Bamei2", "KettoNum3", "Bamei3"} <= columns
