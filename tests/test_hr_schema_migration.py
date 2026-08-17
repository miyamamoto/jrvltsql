# -*- coding: utf-8 -*-
"""Legacy HR identities must be rebuilt instead of additively blessed.

Old HR tables have nullable keys and incomplete repeated payout storage.  The
missing values cannot be reconstructed from stored rows, so strict preflight
must stop before adding columns and require backup/rebuild/reimport.
"""

import pytest

from src.database.schema import SCHEMAS
from src.database.migration import SchemaMigrationError
from src.database.schema import create_all_tables
from src.database.sqlite_handler import SQLiteDatabase


def _old_nl_hr_schema() -> str:
    """numbered 列追加前の旧 NL_HR 定義 (1件目のみ) を再現。"""
    sql = SCHEMAS["NL_HR"]
    drop_markers = [
        "TanUmaban2", "TanPay2", "TanNinki2", "TanUmaban3", "TanPay3", "TanNinki3",
    ]
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
        if "LegacyReserved604_717Hex" in line:
            continue
        lines.append(line.replace(" INTEGER NOT NULL", " INTEGER").replace(" TEXT NOT NULL", " TEXT"))
    return "\n".join(lines)


def test_legacy_nonempty_hr_requires_rebuild_before_any_additive_migration(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "old.db")})
    with database:
        database.execute(_old_nl_hr_schema())
        database.execute(
            "INSERT INTO NL_HR (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, FukuUmaban, FukuPay)"
            " VALUES ('2026', 611, '05', 3, 8, 11, '07', 150)"
        )
        database.commit()
        before = database.fetch_all('PRAGMA table_info("NL_HR")')

        with pytest.raises(SchemaMigrationError):
            create_all_tables(database)

        assert database.fetch_all('PRAGMA table_info("NL_HR")') == before
        assert database.fetch_one(
            "SELECT FukuUmaban, FukuPay FROM NL_HR"
        ) == {"FukuUmaban": "07", "FukuPay": 150}
