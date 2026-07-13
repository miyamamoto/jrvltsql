"""Regression tests for additive migration of the corrected SE layout."""

import pytest

from src.database.migration import migrate_all_tables
from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase


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
