# -*- coding: utf-8 -*-
"""Incomplete HR storage must be rebuilt instead of additively blessed.

Even with the current non-null key, missing repeated payout values cannot be
reconstructed from stored rows. Strict preflight must therefore stop before
adding columns and require backup/rebuild/reimport.
"""

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, create_all_tables
from src.database.sqlite_handler import SQLiteDatabase


def _old_hr_schema(table_name: str) -> str:
    """numbered 列追加前の旧HR定義（1件目のみ）を再現。"""
    sql = SCHEMAS[table_name]
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(f"{m} ") for m in (
            [f"{p}{i}" for p in ("TanUmaban", "TanPay", "TanNinki") for i in (2, 3)]
            + [f"{p}{i}" for p in ("FukuUmaban", "FukuPay", "FukuNinki") for i in range(2, 6)]
            + [f"{p}{i}" for p in ("WakuKumi", "WakuPay", "WakuNinki") for i in (2, 3)]
            + [f"{p}{i}" for p in ("UmarenKumi", "UmarenPay", "UmarenNinki") for i in (2, 3)]
            + [f"{p}{i}" for p in ("WideKumi", "WidePay", "WideNinki") for i in range(2, 8)]
            + [f"{p}{i}" for p in ("UmatanKumi", "UmatanPay", "UmatanNinki") for i in range(2, 7)]
            + [f"{p}{i}" for p in ("SanrenfukuKumi", "SanrenfukuPay", "SanrenfukuNinki") for i in (2, 3)]
            + [f"{p}{i}" for p in ("SanrentanKumi", "SanrentanPay", "SanrentanNinki") for i in range(2, 7)]
        )):
            continue
        if any(f"Yobi{i} " in line for i in range(4, 10)):
            continue
        if "LegacyReserved604_717Hex" in line or "OpaqueStatus9Body28_717Hex" in line:
            continue
        lines.append(line)
    return "\n".join(lines)


@pytest.mark.parametrize("table_name", ("NL_HR", "RT_HR"))
def test_legacy_nonempty_hr_requires_rebuild_before_any_additive_migration(
    tmp_path, table_name: str
):
    database = SQLiteDatabase({"path": str(tmp_path / f"old-{table_name}.db")})
    with database:
        database.execute(_old_hr_schema(table_name))
        database.execute(
            f"INSERT INTO {table_name} "
            "(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, FukuUmaban, FukuPay)"
            " VALUES ('2026', 611, '05', 3, 8, 11, '07', 150)"
        )
        database.commit()
        before = database.fetch_all(f'PRAGMA table_info("{table_name}")')
        key_nullability = {
            row["name"]: row["notnull"]
            for row in before
            if row["name"] in {"Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"}
        }
        assert key_nullability == {
            "Year": 1,
            "MonthDay": 1,
            "JyoCD": 1,
            "Kaiji": 1,
            "Nichiji": 1,
            "RaceNum": 1,
        }

        with pytest.raises(SchemaMigrationError):
            create_all_tables(database)

        assert database.fetch_all(f'PRAGMA table_info("{table_name}")') == before
        assert database.fetch_one(
            f"SELECT FukuUmaban, FukuPay FROM {table_name}"
        ) == {"FukuUmaban": "07", "FukuPay": 150}
