# -*- coding: utf-8 -*-
"""NL_HR/RT_HR の numbered 払戻列が additive migration で追加されることの回帰テスト。

PR #121 は schema.py に FukuUmaban2..5 / WideKumi2..7 等を追加した。
既存 DB (旧スキーマで作成済み) は CREATE TABLE IF NOT EXISTS では列が増えないため、
migrate_all_tables の additive ALTER で追従することを保証する。
"""

import sqlite3
import tempfile
from pathlib import Path

from src.database.schema import SCHEMAS
from src.database.migration import migrate_all_tables


class _SqliteDB:
    """migration.py が要求する最小インターフェースの SQLite ラッパー。"""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.db_type = "sqlite"

    def get_db_type(self):
        return self.db_type

    def table_exists(self, name):
        cur = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return cur.fetchone() is not None

    def execute(self, sql, params=None):
        return self.conn.execute(sql, params or [])

    def fetch_all(self, sql, params=None):
        return self.conn.execute(sql, params or []).fetchall()

    def commit(self):
        self.conn.commit()


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
        lines.append(line)
    return "\n".join(lines)


def test_numbered_payout_columns_added_by_migration(tmp_path):
    db = _SqliteDB(tmp_path / "old.db")
    db.execute(_old_nl_hr_schema())
    db.execute(
        "INSERT INTO NL_HR (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, FukuUmaban, FukuPay)"
        " VALUES ('2026', 611, '05', 3, 8, 11, '07', 150)"
    )
    db.commit()

    cols_before = {r[1] for r in db.fetch_all("PRAGMA table_info(NL_HR)")}
    assert "FukuUmaban2" not in cols_before

    migrate_all_tables(db, {"NL_HR": SCHEMAS["NL_HR"]})

    cols_after = {r[1] for r in db.fetch_all("PRAGMA table_info(NL_HR)")}
    for col in ("FukuUmaban2", "FukuPay5", "WideKumi7", "SanrentanNinki6"):
        assert col in cols_after, col

    # 既存行が保持されること
    row = db.fetch_all("SELECT FukuUmaban, FukuPay, FukuUmaban2 FROM NL_HR")[0]
    assert row[0] == "07" and row[1] == 150 and row[2] is None
