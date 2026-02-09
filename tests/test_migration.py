"""Tests for schema migration logic."""

import sqlite3
import tempfile
import os

import pytest

from src.database.sqlite_handler import SQLiteDatabase
from src.database.migration import (
    _extract_columns_from_sql,
    migrate_table_if_needed,
    migrate_all_tables,
)


@pytest.fixture
def db():
    """Create a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        database = SQLiteDatabase({"path": db_path})
        database.connect()
        yield database
        database.disconnect()


# --- _extract_columns_from_sql tests ---

def test_extract_columns_simple():
    sql = """CREATE TABLE IF NOT EXISTS T (
        A INTEGER, B TEXT, C REAL,
        PRIMARY KEY (A)
    )"""
    cols = _extract_columns_from_sql(sql)
    assert cols == {"A", "B", "C"}


def test_extract_columns_no_pk():
    sql = "CREATE TABLE T (X TEXT, Y INTEGER)"
    cols = _extract_columns_from_sql(sql)
    assert cols == {"X", "Y"}


# --- migrate_table_if_needed tests ---

OLD_SCHEMA = """CREATE TABLE IF NOT EXISTS NL_H1 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    HenkanUma1 TEXT, HenkanUma2 TEXT, HenkanUma3 TEXT,
    TanUma TEXT, TanHyo BIGINT,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
)"""

NEW_SCHEMA = """CREATE TABLE IF NOT EXISTS NL_H1 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    HenkanUma TEXT, BetType TEXT, Kumi TEXT, Hyo BIGINT, Ninki INTEGER,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, BetType, Kumi)
)"""


def test_migrate_drops_and_recreates_on_mismatch(db):
    """Old schema table should be dropped and recreated with new schema."""
    # Create table with old schema
    db.execute(OLD_SCHEMA)
    db.commit()

    # Verify old columns exist
    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    old_cols = {r['name'] for r in info}
    assert "TanUma" in old_cols
    assert "BetType" not in old_cols

    # Insert a row into old table
    db.execute("INSERT INTO NL_H1 (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, TanUma) VALUES (2025, 101, '01', 1, 1, 1, 'test')")
    db.commit()

    # Run migration
    result = migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA)
    assert result is True

    # Verify new columns
    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    new_cols = {r['name'] for r in info}
    assert "BetType" in new_cols
    assert "Kumi" in new_cols
    assert "TanUma" not in new_cols

    # Old data should be gone
    rows = db.fetch_all("SELECT * FROM NL_H1")
    assert len(rows) == 0


def test_migrate_no_op_when_schema_matches(db):
    """If schema already matches, no migration should occur."""
    db.execute(NEW_SCHEMA)
    db.commit()
    db.execute("INSERT INTO NL_H1 (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, BetType, Kumi) VALUES (2025, 101, '01', 1, 1, 1, 'T', '01')")
    db.commit()

    result = migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA)
    assert result is False

    # Data should still be there
    rows = db.fetch_all("SELECT * FROM NL_H1")
    assert len(rows) == 1


def test_migrate_no_op_when_table_missing(db):
    """If table doesn't exist, no migration needed."""
    result = migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA)
    assert result is False


# --- migrate_all_tables tests ---

OLD_H6 = """CREATE TABLE IF NOT EXISTS NL_H6 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    OldColumn TEXT,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
)"""

NEW_H6 = """CREATE TABLE IF NOT EXISTS NL_H6 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    SanrentanKumi TEXT, SanrentanHyo BIGINT,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, SanrentanKumi)
)"""


def test_migrate_all_tables_multiple(db):
    """Test that migrate_all_tables handles multiple tables."""
    db.execute(OLD_SCHEMA)
    db.execute(OLD_H6)
    db.commit()

    schemas = {"NL_H1": NEW_SCHEMA, "NL_H6": NEW_H6}
    count = migrate_all_tables(db, schemas)
    assert count == 2

    # Verify both tables have new schemas
    h1_cols = {r['name'] for r in db.fetch_all("PRAGMA table_info(NL_H1)")}
    assert "BetType" in h1_cols
    h6_cols = {r['name'] for r in db.fetch_all("PRAGMA table_info(NL_H6)")}
    assert "SanrentanKumi" in h6_cols
