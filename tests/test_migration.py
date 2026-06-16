"""Tests for schema migration logic."""

import sqlite3
import tempfile
import os
from typing import Any, Dict, List, Optional

import pytest

from src.database.base import BaseDatabase
from src.database.sqlite_handler import SQLiteDatabase
from src.database.migration import (
    _extract_columns_from_sql,
    _extract_primary_key_columns,
    migrate_table_if_needed,
    migrate_all_tables,
)


class MockPostgreSQLDatabase(BaseDatabase):
    """Minimal in-memory mock that behaves like PostgreSQLDatabase for migration tests."""

    def __init__(self):
        super().__init__({})
        self._tables: Dict[str, List[str]] = {}  # table_name -> [col_name, ...]
        self._primary_keys: Dict[str, List[str]] = {}
        self._executed: List[str] = []

    def get_db_type(self) -> str:
        return "postgresql"

    def connect(self): pass
    def disconnect(self): pass
    def commit(self): pass
    def rollback(self): pass

    def table_exists(self, table_name: str) -> bool:
        # Real PostgreSQL stores unquoted identifiers in lowercase.
        return table_name.lower() in self._tables

    def execute(self, sql: str, parameters=None):
        self._executed.append(sql.strip())
        upper = sql.strip().upper()
        if upper.startswith("DROP TABLE"):
            # Extract table name: DROP TABLE "NL_H1" or DROP TABLE NL_H1
            # IF EXISTS is supported and silently no-ops on missing tables.
            import re
            m = re.search(r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?"?(\w+)"?', sql, re.IGNORECASE)
            if m:
                # Real PG: unquoted name is lowercased; quoted name preserves case.
                # The migration code now uses unquoted lowercase for PG, so just
                # normalize to lowercase to match real behavior.
                table = m.group(1).lower()
                self._tables.pop(table, None)
                self._primary_keys.pop(table, None)
        elif upper.startswith("ALTER TABLE"):
            import re
            m = re.search(
                r'ALTER\s+TABLE\s+"?(\w+)"?\s+ADD\s+COLUMN\s+"?(\w+)"?',
                sql,
                re.IGNORECASE,
            )
            if m:
                table = m.group(1).lower()
                column = m.group(2)
                self._tables.setdefault(table, []).append(column)
        elif upper.startswith("CREATE TABLE"):
            from src.database.migration import _extract_columns_from_sql
            import re
            m = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"?(\w+)"?', sql, re.IGNORECASE)
            if m:
                cols = _extract_columns_from_sql(sql)
                pk = _extract_primary_key_columns(sql)
                # Real PG lowercases unquoted identifiers when storing.
                table = m.group(1).lower()
                self._tables[table] = list(cols or [])
                self._primary_keys[table] = list(pk or [])

    def executemany(self, sql: str, parameters): pass

    def fetch_one(self, sql: str, parameters=None) -> Optional[Dict[str, Any]]:
        rows = self.fetch_all(sql, parameters)
        return rows[0] if rows else None

    def fetch_all(self, sql: str, parameters=None) -> List[Dict[str, Any]]:
        # Respond to information_schema.columns query used in migration.
        # Real PG stores names lowercased and migration.py passes .lower(),
        # so compare on lowercase here.
        if "information_schema.columns" in sql.lower():
            table_name = parameters[0] if parameters else None
            cols = self._tables.get((table_name or "").lower(), [])
            return [{"name": c} for c in cols]
        if "pg_index" in sql.lower():
            table_name = parameters[0] if parameters else None
            pk = self._primary_keys.get((table_name or "").lower(), [])
            return [{"name": c} for c in pk]
        return []

    def create_table(self, table_name: str, schema: str): pass

    def _execute_raw(self, sql: str, parameters=None): pass


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


def test_extract_primary_key_columns():
    sql = """CREATE TABLE IF NOT EXISTS T (
        A INTEGER, B TEXT, C REAL,
        PRIMARY KEY (A, B)
    )"""
    assert _extract_primary_key_columns(sql) == ["A", "B"]


def test_extract_primary_key_columns_inline_definition():
    sql = """CREATE TABLE IF NOT EXISTS T (
        Id INTEGER PRIMARY KEY,
        Name TEXT
    )"""
    assert _extract_primary_key_columns(sql) == ["Id"]


def test_extract_primary_key_columns_named_constraint():
    sql = """CREATE TABLE IF NOT EXISTS T (
        A INTEGER,
        B TEXT,
        CONSTRAINT pk_t PRIMARY KEY (A, B)
    )"""
    assert _extract_primary_key_columns(sql) == ["A", "B"]


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

ADDITIVE_OLD_SCHEMA = """CREATE TABLE IF NOT EXISTS NL_H1 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    HenkanUma TEXT, BetType TEXT, Kumi TEXT,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, BetType, Kumi)
)"""

INLINE_OLD_SCHEMA = """CREATE TABLE IF NOT EXISTS INLINE_PK (
    Id INTEGER PRIMARY KEY,
    Name TEXT
)"""

INLINE_NEW_SCHEMA = """CREATE TABLE IF NOT EXISTS INLINE_PK (
    Id INTEGER PRIMARY KEY,
    Name TEXT,
    Score REAL
)"""


def test_migrate_adds_missing_columns_without_dropping(db):
    """Missing columns should be added without dropping existing rows."""
    # Create table with old schema
    db.execute(ADDITIVE_OLD_SCHEMA)
    db.commit()

    # Verify old columns exist
    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    old_cols = {r['name'] for r in info}
    assert "BetType" in old_cols
    assert "Hyo" not in old_cols

    # Insert a row into old table
    db.execute("INSERT INTO NL_H1 (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, BetType, Kumi) VALUES (2025, 101, '01', 1, 1, 1, 'T', '01')")
    db.commit()

    # Run migration
    result = migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA)
    assert result is True

    # Verify new columns were added and old columns were preserved.
    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    new_cols = {r['name'] for r in info}
    assert "BetType" in new_cols
    assert "Kumi" in new_cols
    assert "Hyo" in new_cols

    # Old data should be preserved.
    rows = db.fetch_all("SELECT * FROM NL_H1")
    assert len(rows) == 1


def test_migrate_drops_and_recreates_on_mismatch_when_explicitly_allowed(db, monkeypatch):
    """DROP+recreate is opt-in because production DBs must not be wiped."""
    monkeypatch.setenv("JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS", "1")
    db.execute(OLD_SCHEMA)
    db.commit()
    db.execute("INSERT INTO NL_H1 (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, TanUma) VALUES (2025, 101, '01', 1, 1, 1, 'test')")
    db.commit()

    assert migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA) is True

    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    new_cols = {r['name'] for r in info}
    assert "BetType" in new_cols
    assert "Kumi" in new_cols
    assert "TanUma" not in new_cols
    assert db.fetch_all("SELECT * FROM NL_H1") == []


def test_primary_key_mismatch_requires_destructive_opt_in(db):
    """Primary-key changes are not safe additive migrations."""
    db.execute(OLD_SCHEMA)
    db.commit()

    result = migrate_table_if_needed(db, "NL_H1", NEW_SCHEMA)
    assert result is False

    info = db.fetch_all("PRAGMA table_info(NL_H1)")
    cols = {r['name'] for r in info}
    assert "BetType" not in cols


def test_inline_primary_key_does_not_create_false_mismatch(db):
    """Inline PRIMARY KEY definitions should allow additive migrations."""
    db.execute(INLINE_OLD_SCHEMA)
    db.execute("INSERT INTO INLINE_PK (Id, Name) VALUES (1, 'keiba')")
    db.commit()

    result = migrate_table_if_needed(db, "INLINE_PK", INLINE_NEW_SCHEMA)
    assert result is True

    cols = {r['name'] for r in db.fetch_all("PRAGMA table_info(INLINE_PK)")}
    assert "Score" in cols
    rows = db.fetch_all("SELECT Id, Name FROM INLINE_PK")
    assert rows == [{"Id": 1, "Name": "keiba"}]


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

ADDITIVE_OLD_H6 = """CREATE TABLE IF NOT EXISTS NL_H6 (
    Year INTEGER, MonthDay INTEGER, JyoCD TEXT,
    Kaiji INTEGER, Nichiji INTEGER, RaceNum INTEGER,
    SanrentanKumi TEXT,
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, SanrentanKumi)
)"""


def test_migrate_all_tables_multiple(db):
    """Test that migrate_all_tables handles multiple tables."""
    db.execute(ADDITIVE_OLD_SCHEMA)
    db.execute(ADDITIVE_OLD_H6)
    db.commit()

    schemas = {"NL_H1": NEW_SCHEMA, "NL_H6": NEW_H6}
    count = migrate_all_tables(db, schemas)
    assert count == 2

    # Verify both tables have new schemas
    h1_cols = {r['name'] for r in db.fetch_all("PRAGMA table_info(NL_H1)")}
    assert "BetType" in h1_cols
    h6_cols = {r['name'] for r in db.fetch_all("PRAGMA table_info(NL_H6)")}
    assert "SanrentanKumi" in h6_cols


# --- PostgreSQL path tests (mock DB, no server required) ---

@pytest.fixture
def pg_db():
    return MockPostgreSQLDatabase()


def test_pg_migrate_adds_missing_columns_without_dropping(pg_db):
    """PostgreSQL path: mismatch adds columns and preserves existing schema."""
    pg_db.execute(ADDITIVE_OLD_SCHEMA)

    result = migrate_table_if_needed(pg_db, "NL_H1", NEW_SCHEMA)
    assert result is True

    # Table should now have both old and new columns.
    assert "BetType" in pg_db._tables["nl_h1"]
    assert "Hyo" in pg_db._tables["nl_h1"]


def test_pg_migrate_drops_and_recreates_on_mismatch_when_explicitly_allowed(pg_db, monkeypatch):
    """PostgreSQL destructive migration requires explicit opt-in."""
    monkeypatch.setenv("JLTSQL_ALLOW_DESTRUCTIVE_MIGRATIONS", "1")
    pg_db.execute(OLD_SCHEMA)

    assert migrate_table_if_needed(pg_db, "NL_H1", NEW_SCHEMA) is True

    assert "BetType" in pg_db._tables["nl_h1"]
    assert "TanUma" not in pg_db._tables["nl_h1"]


def test_pg_primary_key_mismatch_requires_destructive_opt_in(pg_db):
    """PostgreSQL path: primary-key changes require destructive opt-in."""
    pg_db.execute(OLD_SCHEMA)

    result = migrate_table_if_needed(pg_db, "NL_H1", NEW_SCHEMA)
    assert result is False
    assert "BetType" not in pg_db._tables["nl_h1"]


def test_pg_migrate_no_op_when_schema_matches(pg_db):
    """PostgreSQL path: no migration when columns already match."""
    pg_db.execute(NEW_SCHEMA)

    result = migrate_table_if_needed(pg_db, "NL_H1", NEW_SCHEMA)
    assert result is False


def test_pg_migrate_no_op_when_table_missing(pg_db):
    """PostgreSQL path: no migration when table doesn't exist."""
    result = migrate_table_if_needed(pg_db, "NL_H1", NEW_SCHEMA)
    assert result is False


def test_pg_migrate_all_tables(pg_db):
    """PostgreSQL path: migrate_all_tables handles multiple tables."""
    pg_db.execute(ADDITIVE_OLD_SCHEMA)
    pg_db.execute(ADDITIVE_OLD_H6)

    count = migrate_all_tables(pg_db, {"NL_H1": NEW_SCHEMA, "NL_H6": NEW_H6})
    assert count == 2
    # Real PG stores unquoted identifiers lowercased.
    assert "BetType" in pg_db._tables["nl_h1"]
    assert "SanrentanKumi" in pg_db._tables["nl_h6"]
