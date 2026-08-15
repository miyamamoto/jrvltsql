"""Unit tests for database handlers."""

import tempfile
from pathlib import Path

import pytest

from src.database.base import DatabaseError
from src.database.schema import SCHEMAS, SchemaManager
from src.database.sqlite_handler import SQLiteDatabase


class TestSQLiteDatabase:
    """Test cases for SQLite database handler."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create SQLite database instance."""
        config = {"path": str(temp_db_path)}
        return SQLiteDatabase(config)

    def test_connect_disconnect(self, db):
        """Test connection and disconnection."""
        assert not db.is_connected()

        db.connect()
        assert db.is_connected()

        db.disconnect()
        assert not db.is_connected()

    def test_context_manager(self, db):
        """Test context manager."""
        assert not db.is_connected()

        with db:
            assert db.is_connected()

        assert not db.is_connected()

    def test_context_manager_rejects_arbitrary_disconnect_with_uncommitted_write(self, db):
        """A clean context must not report success after an unrelated disconnect."""
        with pytest.raises(DatabaseError, match="No active connection"):
            with db:
                db.create_table("test", "CREATE TABLE test (id INTEGER PRIMARY KEY)")
                db.commit()
                db.insert("test", {"id": 1})
                db.disconnect()

        with db:
            assert db.fetch_one("SELECT COUNT(*) AS count FROM test")["count"] == 0

    def test_create_table(self, db):
        """Test table creation."""
        with db:
            schema = """
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """
            db.create_table("test_table", schema)

            assert db.table_exists("test_table")
            assert not db.table_exists("nonexistent_table")

    def test_insert(self, db):
        """Test single row insert."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)

            rows = db.insert("test", {"id": 1, "name": "Alice"})
            assert rows == 1

    def test_insert_many(self, db):
        """Test multiple row insert."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)

            data = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ]
            rows = db.insert_many("test", data)
            assert rows == 3

    def test_fetch_one(self, db):
        """Test fetching single row."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)
            db.insert("test", {"id": 1, "name": "Alice"})

            row = db.fetch_one("SELECT * FROM test WHERE id = ?", (1,))
            assert row is not None
            assert row["id"] == 1
            assert row["name"] == "Alice"

    def test_fetch_all(self, db):
        """Test fetching all rows."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)

            data = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
            db.insert_many("test", data)

            rows = db.fetch_all("SELECT * FROM test ORDER BY id")
            assert len(rows) == 2
            assert rows[0]["name"] == "Alice"
            assert rows[1]["name"] == "Bob"

    def test_execute(self, db):
        """Test execute method."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)

            db.execute("INSERT INTO test (id, name) VALUES (?, ?)", (1, "Alice"))
            row = db.fetch_one("SELECT * FROM test WHERE id = ?", (1,))

            assert row["name"] == "Alice"

    def test_commit_rollback(self, db):
        """Test commit and rollback."""
        db.connect()

        try:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)"
            db.create_table("test", schema)
            db.insert("test", {"id": 1, "name": "Alice"})
            db.commit()

            # Verify data was committed
            row = db.fetch_one("SELECT * FROM test WHERE id = ?", (1,))
            assert row is not None

            # Test rollback
            db.insert("test", {"id": 2, "name": "Bob"})
            db.rollback()

            # Bob should not be in database
            row = db.fetch_one("SELECT * FROM test WHERE id = ?", (2,))
            assert row is None

        finally:
            db.disconnect()

    def test_get_table_info(self, db):
        """Test getting table info."""
        with db:
            schema = "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            db.create_table("test", schema)

            info = db.get_table_info("test")
            assert len(info) == 2
            assert info[0]["name"] == "id"
            assert info[1]["name"] == "name"


class TestSchemaManager:
    """Test cases for SchemaManager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create SQLite database instance."""
        config = {"path": str(temp_db_path)}
        return SQLiteDatabase(config)

    @pytest.fixture
    def manager(self, db):
        """Create schema manager."""
        return SchemaManager(db)

    def test_get_table_names(self, manager):
        """Test getting table names."""
        names = manager.get_table_names()
        assert "NL_RA" in names
        assert "NL_SE" in names
        assert "NL_HR" in names

    def test_create_table(self, db, manager):
        """Test creating single table."""
        with db:
            result = manager.create_table("NL_RA")
            assert result is True

            assert manager.table_exists("NL_RA")

    def test_create_all_tables(self, db, manager):
        """Test creating all tables."""
        with db:
            results = manager.create_all_tables()

            assert len(results) == len(SCHEMAS)
            assert all(results.values())

            # Verify all tables exist
            existing = manager.get_existing_tables()
            assert len(existing) == len(SCHEMAS)

    def test_get_missing_tables(self, db, manager):
        """Test getting missing tables."""
        with db:
            # Initially all tables should be missing
            missing = manager.get_missing_tables()
            assert len(missing) == len(SCHEMAS)

            # Create one table
            manager.create_table("NL_RA")

            # Now one less table should be missing
            missing = manager.get_missing_tables()
            assert len(missing) == len(SCHEMAS) - 1
            assert "NL_RA" not in missing


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "integration.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create SQLite database instance."""
        config = {"path": str(temp_db_path)}
        return SQLiteDatabase(config)

    def test_full_workflow(self, db):
        """Test complete workflow: create tables, insert, query."""
        manager = SchemaManager(db)

        with db:
            # Create tables
            results = manager.create_all_tables()
            assert all(results.values())

            # Insert race data
            race_data = {
                "RecordSpec": "RA",
                "DataKubun": "1",
                "MakeDate": "20240601",
                "Year": 2024,
                "MonthDay": 601,
                "JyoCD": "06",
                "Kaiji": 3,
                "Nichiji": 8,
                "RaceNum": 11,
                "Hondai": "テストレース",
                "Kyori": 2000,
                "TrackCD": "1",
            }
            db.insert("NL_RA", race_data)

            # Query data
            row = db.fetch_one(
                """
                SELECT * FROM NL_RA
                WHERE Year = ? AND RaceNum = ?
                """,
                (2024, 11),
            )

            assert row is not None
            assert row["Hondai"] == "テストレース"
            assert row["Kyori"] == 2000
