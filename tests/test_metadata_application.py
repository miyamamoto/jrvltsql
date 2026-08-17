#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for database metadata application functionality.

Tests that metadata from schema_metadata.py is correctly applied to
database tables and can be retrieved for MCP integration.

Test Coverage:
1. SQLite metadata table creation and population
2. PostgreSQL COMMENT ON execution
3. Metadata retrieval for all database types
4. Bulk metadata application
5. Error handling (non-existent tables, missing metadata)

Note: DuckDB is outside this project's supported database matrix.
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

import pytest

from scripts.setup_pg_test_db import postgresql_test_config
from src.database.dual_handler import DualDatabase
from src.database.indexes import INDEXES
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SCHEMAS, SchemaManager
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.schema_metadata import (
    TABLE_METADATA,
    _get_executable_index_columns,
    export_schema_for_mcp,
)
from src.database.schema_types import (
    get_table_column_nullability,
    get_table_column_types,
    get_table_primary_key_columns,
)
from src.database.sqlite_handler import SQLiteDatabase

RUN_POSTGRESQL_INTEGRATION = (
    os.environ.get("JLTSQL_RUN_POSTGRESQL_INTEGRATION") == "1"
)


def _catalog_type_family(declared_type):
    """Independent test oracle for backend catalog type families."""

    normalized = re.sub(r"\s+", " ", str(declared_type or "").strip().upper())
    token = normalized.split("(", 1)[0].split(" ", 1)[0]
    if token in {"CHAR", "CHARACTER", "CLOB", "NCHAR", "NVARCHAR", "TEXT", "VARCHAR"}:
        return "TEXT"
    if token in {"DATE", "DATETIME", "TIME", "TIMESTAMP"}:
        return "TEXT"
    if token in {"BIGINT", "INT8"}:
        return "BIGINT"
    if token in {"INT", "INT2", "INT4", "INTEGER", "SMALLINT"}:
        return "INTEGER"
    if token in {"DECIMAL", "DOUBLE", "FLOAT", "NUMERIC", "REAL"}:
        return "REAL"
    return None


def test_metadata_primary_key_columns_are_described():
    """Every metadata primary-key column should have a column definition."""

    for table_name, metadata in TABLE_METADATA.items():
        defined_columns = {column["name"] for column in metadata["columns"]}
        missing = set(metadata.get("primary_key", [])) - defined_columns
        assert not missing, f"{table_name} primary_key references missing columns: {sorted(missing)}"


def test_all_metadata_matches_the_executable_schema_exactly():
    """MCP metadata must target every real SQL column and primary-key field."""

    executable_tables = set(SCHEMAS) | set(JRAVAN_SCHEMAS)
    assert set(TABLE_METADATA) == executable_tables

    mismatches = {}
    for table_name, metadata in TABLE_METADATA.items():
        metadata_types = {
            column["name"]: column["type"] for column in metadata["columns"]
        }
        expected_types = get_table_column_types(table_name)
        metadata_nullability = {
            column["name"]: column["nullable"] for column in metadata["columns"]
        }
        expected_nullability = get_table_column_nullability(table_name)
        metadata_key = metadata.get("primary_key", [])
        expected_key = get_table_primary_key_columns(table_name)
        expected_index_columns = []
        for statement in INDEXES.get(table_name, []):
            match = re.search(
                r'\bON\s+(?P<table>[^\s(]+)\s*\((?P<columns>[^)]*)\)',
                statement,
                re.I,
            )
            assert match is not None, statement
            assert match.group("table").strip('`"[]').lower() == table_name.lower()
            for raw_column in match.group("columns").split(','):
                column_name = raw_column.strip().strip('`"[]')
                if column_name not in expected_index_columns:
                    expected_index_columns.append(column_name)

        if (
            metadata_types != expected_types
            or metadata_nullability != expected_nullability
            or metadata_key != expected_key
            or metadata.get("indexes", []) != expected_index_columns
        ):
            mismatches[table_name] = {
                "metadata_columns": sorted(metadata_types),
                "expected_columns": sorted(expected_types),
                "metadata_nullability": metadata_nullability,
                "expected_nullability": expected_nullability,
                "metadata_key": metadata_key,
                "expected_key": expected_key,
                "metadata_indexes": metadata.get("indexes", []),
                "expected_indexes": expected_index_columns,
            }

    assert mismatches == {}


def test_metadata_index_binding_rejects_a_definition_for_another_table(monkeypatch):
    """An index with a shared column name must still target its owning table."""

    monkeypatch.setitem(
        INDEXES,
        "NL_RA",
        ["CREATE INDEX idx_wrong_target ON NL_SE(Year)"],
    )

    with pytest.raises(ValueError, match="NL_RA.*NL_SE"):
        _get_executable_index_columns("NL_RA")


def test_mcp_export_declares_the_breaking_physical_metadata_contract():
    exported = export_schema_for_mcp()

    assert exported["version"] == "2.0.0"
    assert exported["semantics"] == {
        "nullable": "logical portable schema contract",
        "indexes": "distinct physical columns used by configured secondary indexes",
    }


def test_ch_metadata_matches_normalized_native_schema():
    """CH MCP metadata must expose both normalized tables exactly as stored."""

    for table_name in ("NL_CH", "NL_CH_SEISEKI"):
        metadata = TABLE_METADATA[table_name]
        metadata_types = {
            column["name"]: column["type"] for column in metadata["columns"]
        }
        assert metadata_types == get_table_column_types(table_name)
        assert metadata["primary_key"] == get_table_primary_key_columns(table_name)


def test_ch_postgresql_metadata_targets_the_actual_lowercase_identifiers():
    """Unquoted DDL identifiers are stored lowercase by PostgreSQL."""

    database = PostgreSQLDatabase({})
    statements = []
    database.table_exists = lambda _table_name: True
    database.execute = lambda sql, parameters=None: statements.append(sql) or 0

    manager = SchemaManager(database)
    manager._metadata_schema_matches = lambda *_args: True

    assert manager.apply_metadata_to_table("NL_CH") is True
    assert "COMMENT ON TABLE nl_ch " in statements[0]
    assert any(
        statement.startswith("COMMENT ON COLUMN nl_ch.chokyosicode ")
        for statement in statements
    )
    assert not any('"ChokyosiCode"' in statement for statement in statements)


def test_av_metadata_matches_scratch_exclusion_schema():
    """AV metadata should describe the official race/horse scratch schema."""

    for table_name in ("NL_AV", "RT_AV"):
        metadata = TABLE_METADATA[table_name]
        column_names = {column["name"] for column in metadata["columns"]}
        assert "出走取消・競走除外" in metadata["description"]
        assert metadata["primary_key"] == get_table_primary_key_columns(table_name)
        assert {"Year", "MonthDay", "JyoCD", "RaceNum", "Umaban", "JiyuKubun"} <= column_names
        assert "SaleHostName" not in column_names
        assert "Price" not in column_names


def test_hs_metadata_matches_market_price_schema():
    """HS metadata should describe the official market-price schema."""

    metadata = TABLE_METADATA["NL_HS"]
    column_names = {column["name"] for column in metadata["columns"]}
    assert "競走馬市場取引価格" in metadata["description"]
    assert metadata["primary_key"] == get_table_primary_key_columns("NL_HS")
    assert {"KettoNum", "SaleCode", "FromDate", "Price"} <= column_names


def test_sk_metadata_describes_all_three_generation_lineage_slots():
    """SK metadata must target every executable physical schema column."""

    expected_lineage_columns = {
        "FNum",
        "MNum",
        "FFNum",
        "FMNum",
        "MFNum",
        "MMNum",
        "FFFNum",
        "FFMNum",
        "FMFNum",
        "FMMNum",
        "MFFNum",
        "MFMNum",
        "MMFNum",
        "MMMNum",
    }
    metadata = TABLE_METADATA["NL_SK"]
    metadata_types = {
        column["name"]: column["type"] for column in metadata["columns"]
    }

    assert expected_lineage_columns <= set(metadata_types)
    assert metadata_types == get_table_column_types("NL_SK")
    assert metadata["primary_key"] == get_table_primary_key_columns("NL_SK")


class TestSQLiteMetadata(unittest.TestCase):
    """Test metadata application and retrieval for SQLite."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'metadata_test.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_sqlite_metadata_table_creation(self):
        """Test that _metadata table is created in SQLite."""
        # Create a test table
        self.schema_mgr.create_table('NL_RA')

        # Apply metadata
        success = self.schema_mgr.apply_metadata_to_table('NL_RA')
        self.assertTrue(success, "Metadata application should succeed")

        # Check that _metadata table exists
        rows = self.database.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_metadata'"
        )
        self.assertEqual(len(rows), 1, "_metadata table should exist")

    def test_sqlite_table_description_stored(self):
        """Test that table description is stored in _metadata."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        # Query table description (column_name is empty string for table descriptions)
        rows = self.database.fetch_all(
            """SELECT description FROM _metadata
               WHERE table_name = 'NL_RA' AND column_name = ''"""
        )

        self.assertEqual(len(rows), 1, "Should have one table description")
        self.assertIn('レース詳細', rows[0]['description'])

    def test_sqlite_column_descriptions_stored(self):
        """Test that column descriptions are stored in _metadata."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        # Query column descriptions
        rows = self.database.fetch_all(
            """SELECT column_name, description FROM _metadata
               WHERE table_name = 'NL_RA' AND column_name IS NOT NULL
               ORDER BY column_name"""
        )

        self.assertGreater(len(rows), 0, "Should have column descriptions")

        # Check for specific column
        col_names = [row['column_name'] for row in rows]
        self.assertIn('RecordSpec', col_names)

    def test_sqlite_metadata_retrieval(self):
        """Test retrieving metadata from SQLite."""
        self.schema_mgr.create_table('NL_SE')
        self.schema_mgr.apply_metadata_to_table('NL_SE')

        # Retrieve metadata
        metadata = self.schema_mgr.get_table_metadata('NL_SE')

        self.assertIsNotNone(metadata, "Should retrieve metadata")
        self.assertIn('table', metadata)
        self.assertIn('columns', metadata)
        self.assertGreater(len(metadata['columns']), 0)

    def test_sqlite_metadata_update(self):
        """Test that metadata can be updated (INSERT OR REPLACE)."""
        self.schema_mgr.create_table('NL_RA')

        # Apply metadata once, then simulate a display-only label retained from
        # a pre-contract release before applying the current metadata again.
        success1 = self.schema_mgr.apply_metadata_to_table('NL_RA')
        self.database.execute(
            """INSERT INTO _metadata
               (table_name, column_name, description, metadata_type)
               VALUES (?, ?, ?, 'column')""",
            ('NL_RA', '旧表示専用列', 'stale',),
        )
        success2 = self.schema_mgr.apply_metadata_to_table('NL_RA')

        self.assertTrue(success1)
        self.assertTrue(success2)

        # Should still have only one table description (column_name is empty string)
        rows = self.database.fetch_all(
            """SELECT COUNT(*) as cnt FROM _metadata
               WHERE table_name = 'NL_RA' AND column_name = ''"""
        )
        self.assertEqual(rows[0]['cnt'], 1)
        stale_rows = self.database.fetch_all(
            """SELECT column_name FROM _metadata
               WHERE table_name = 'NL_RA' AND column_name = '旧表示専用列'"""
        )
        self.assertEqual(stale_rows, [])

    def test_sqlite_metadata_rejects_schema_drift_before_mutation(self):
        self.database.execute("CREATE TABLE NL_RA (RecordSpec TEXT)")
        self.database.execute(
            """CREATE TABLE _metadata (
                   table_name TEXT NOT NULL,
                   column_name TEXT NOT NULL DEFAULT '',
                   description TEXT,
                   metadata_type TEXT NOT NULL DEFAULT 'column',
                   PRIMARY KEY (table_name, column_name)
               )"""
        )
        self.database.execute(
            """INSERT INTO _metadata
               (table_name, column_name, description, metadata_type)
               VALUES ('NL_RA', 'sentinel', 'keep', 'column')"""
        )

        self.assertFalse(self.schema_mgr.apply_metadata_to_table("NL_RA"))
        rows = self.database.fetch_all(
            "SELECT column_name, description FROM _metadata WHERE table_name = 'NL_RA'"
        )
        self.assertEqual(rows, [{"column_name": "sentinel", "description": "keep"}])


@unittest.skipUnless(
    RUN_POSTGRESQL_INTEGRATION,
    "set JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 to run live PostgreSQL tests",
)
class TestPostgreSQLMetadata(unittest.TestCase):
    """Test metadata application and retrieval for PostgreSQL."""

    def setUp(self):
        """Set up test fixtures."""
        self.database = PostgreSQLDatabase(postgresql_test_config())
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        self.database.execute("DROP TABLE IF EXISTS NL_RA CASCADE")
        self.database.execute("DROP TABLE IF EXISTS NL_SE CASCADE")
        self.database.execute("DROP TABLE IF EXISTS NL_HR CASCADE")
        self.database.commit()
        self.database.disconnect()

    def test_postgresql_comment_on_table(self):
        """Test that COMMENT ON TABLE works in PostgreSQL."""
        self.schema_mgr.create_table('NL_RA')

        success = self.schema_mgr.apply_metadata_to_table('NL_RA')
        self.assertTrue(success, "Metadata application should succeed")

        # Retrieve comment from pg_description
        rows = self.database.fetch_all("""
            SELECT obj_description('NL_RA'::regclass) as description
        """)

        self.assertIsNotNone(rows[0]['description'])
        self.assertIn('レース詳細', rows[0]['description'])

    def test_postgresql_comment_on_columns(self):
        """Test that COMMENT ON COLUMN works in PostgreSQL."""
        self.schema_mgr.create_table('NL_SE')

        success = self.schema_mgr.apply_metadata_to_table('NL_SE')
        self.assertTrue(success)

        # Retrieve column comment
        rows = self.database.fetch_all("""
            SELECT col_description('NL_SE'::regclass, 1) as description
        """)

        # Should have some description
        self.assertIsNotNone(rows[0]['description'])

    def test_postgresql_metadata_retrieval(self):
        """Test retrieving metadata from PostgreSQL information_schema."""
        self.schema_mgr.create_table('NL_HR')
        self.schema_mgr.apply_metadata_to_table('NL_HR')

        # Retrieve metadata
        metadata = self.schema_mgr.get_table_metadata('NL_HR')

        self.assertIsNotNone(metadata)
        self.assertIn('table', metadata)
        self.assertIn('columns', metadata)

    def test_postgresql_information_schema_integration(self):
        """Test that comments are visible in information_schema."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        # Query information_schema
        rows = self.database.fetch_all("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = 'nl_ra'
        """)

        self.assertEqual(len(rows), 1)

    def test_postgresql_all_metadata_targets_are_executable(self):
        """Every metadata entry must apply to a freshly created physical table."""

        try:
            create_results = self.schema_mgr.create_all_tables()
            self.assertTrue(all(create_results.values()))
            for schema_sql in JRAVAN_SCHEMAS.values():
                self.database.execute(schema_sql)

            for table_name in sorted(set(SCHEMAS) | set(JRAVAN_SCHEMAS)):
                self.assertTrue(
                    self.schema_mgr.apply_metadata_to_table(table_name),
                    f"Should apply executable metadata to {table_name}",
                )
                catalog = self.database.fetch_all(
                    """SELECT a.attname AS name,
                              format_type(a.atttypid, a.atttypmod) AS type,
                              a.attnotnull AS not_null
                       FROM pg_attribute a
                       WHERE a.attrelid = to_regclass(?)
                         AND a.attnum > 0
                         AND NOT a.attisdropped
                       ORDER BY a.attnum""",
                    (table_name.lower(),),
                )
                metadata_columns = {
                    column["name"].lower(): column
                    for column in TABLE_METADATA[table_name]["columns"]
                }
                self.assertEqual(
                    set(metadata_columns),
                    {row["name"].lower() for row in catalog},
                )
                for row in catalog:
                    column = metadata_columns[row["name"].lower()]
                    self.assertEqual(
                        _catalog_type_family(row["type"]),
                        column["type"],
                        f"{table_name}.{row['name']} type",
                    )
                    self.assertEqual(
                        not bool(row["not_null"]),
                        column["nullable"],
                        f"{table_name}.{row['name']} nullable",
                    )

                key_rows = self.database.fetch_all(
                    """SELECT a.attname AS name
                       FROM pg_index i
                       JOIN pg_attribute a
                         ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                       WHERE i.indrelid = to_regclass(?)
                         AND i.indisprimary
                       ORDER BY array_position(i.indkey, a.attnum)""",
                    (table_name.lower(),),
                )
                self.assertEqual(
                    [row["name"].lower() for row in key_rows],
                    [
                        column.lower()
                        for column in TABLE_METADATA[table_name]["primary_key"]
                    ],
                )
                comment_count = self.database.fetch_one(
                    """SELECT COUNT(*) AS n
                       FROM pg_description d
                       JOIN pg_class c ON c.oid = d.objoid
                       WHERE c.relname = ? AND d.objsubid > 0""",
                    (table_name.lower(),),
                )["n"]
                self.assertEqual(comment_count, len(catalog))
        finally:
            all_tables = [*SCHEMAS.keys(), *JRAVAN_SCHEMAS.keys()]
            for table_name in reversed(all_tables):
                self.database.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    def test_postgresql_metadata_rejects_wrong_type_and_key_before_comments(self):
        defects = {
            "unknown-type": SCHEMAS["NL_RA"].replace(
                "Year INTEGER,", "Year INTERVAL,", 1
            ),
            "wrong-nullability": SCHEMAS["NL_RA"].replace(
                "RecordSpec TEXT,", "RecordSpec TEXT NOT NULL,", 1
            ),
            "wrong-key": SCHEMAS["NL_RA"].replace(
                "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)",
                "PRIMARY KEY (Year)",
            ),
        }
        for defect, drifted_schema in defects.items():
            with self.subTest(defect=defect):
                self.database.execute("DROP TABLE IF EXISTS NL_RA CASCADE")
                self.database.execute(drifted_schema)
                self.database.execute("COMMENT ON TABLE NL_RA IS 'sentinel'")

                self.assertFalse(self.schema_mgr.apply_metadata_to_table("NL_RA"))
                comment = self.database.fetch_one(
                    "SELECT obj_description('NL_RA'::regclass) AS description"
                )["description"]
                self.assertEqual(comment, "sentinel")

    def test_dual_metadata_uses_each_backend_specific_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite = SQLiteDatabase({"path": str(Path(temp_dir) / "metadata-dual.db")})
            sqlite.connect()
            try:
                SchemaManager(sqlite).create_table("NL_RA")
                self.schema_mgr.create_table("NL_RA")
                dual = DualDatabase(sqlite, self.database)

                self.assertTrue(SchemaManager(dual).apply_metadata_to_table("NL_RA"))
                dual.commit()
                sqlite_count = sqlite.fetch_one(
                    """SELECT COUNT(*) AS n FROM _metadata
                       WHERE table_name = 'NL_RA' AND metadata_type = 'column'"""
                )["n"]
                pg_count = self.database.fetch_one(
                    """SELECT COUNT(*) AS n
                       FROM pg_description d
                       JOIN pg_class c ON c.oid = d.objoid
                       WHERE c.relname = 'nl_ra' AND d.objsubid > 0"""
                )["n"]
                self.assertEqual(
                    sqlite_count, len(TABLE_METADATA["NL_RA"]["columns"])
                )
                self.assertEqual(pg_count, sqlite_count)
                self.assertTrue(dual.secondary_in_sync)

                sqlite.execute(
                    """UPDATE _metadata SET description = 'sentinel'
                       WHERE table_name = 'NL_RA' AND column_name = ''"""
                )
                sqlite.commit()
                self.database.execute("DROP TABLE NL_RA")
                self.database.execute(
                    SCHEMAS["NL_RA"].replace(
                        "Year INTEGER,", "Year TEXT,", 1
                    )
                )
                self.database.commit()

                self.assertFalse(SchemaManager(dual).apply_metadata_to_table("NL_RA"))
                description = sqlite.fetch_one(
                    """SELECT description FROM _metadata
                       WHERE table_name = 'NL_RA' AND column_name = ''"""
                )["description"]
                self.assertEqual(description, "sentinel")
            finally:
                sqlite.disconnect()


class TestMetadataApplicationWorkflow(unittest.TestCase):
    """Test complete metadata application workflows."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'workflow_test.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_apply_metadata_to_nonexistent_table(self):
        """Test applying metadata to table that doesn't exist."""
        success = self.schema_mgr.apply_metadata_to_table('NL_NONEXISTENT')
        self.assertFalse(success, "Should fail for non-existent table")

    def test_apply_metadata_for_table_without_metadata(self):
        """Test applying metadata when metadata is not defined."""
        # Create a custom table not in TABLE_METADATA
        self.database.execute("""
            CREATE TABLE custom_table (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)

        success = self.schema_mgr.apply_metadata_to_table('custom_table')
        self.assertFalse(success, "Should fail when metadata not defined")

    def test_apply_all_metadata_for_existing_tables(self):
        """Test apply_all_metadata() for tables that exist."""
        # Create a few tables
        test_tables = ['NL_RA', 'NL_SE', 'NL_HR']
        for table_name in test_tables:
            self.schema_mgr.create_table(table_name)

        # Apply all metadata
        results = self.schema_mgr.apply_all_metadata()

        # Should have results for all tables in TABLE_METADATA
        self.assertEqual(len(results), len(TABLE_METADATA))

        # Tables we created should succeed
        for table_name in test_tables:
            self.assertTrue(results[table_name],
                f"Should successfully apply metadata to {table_name}")

    def test_metadata_consistency_after_reapplication(self):
        """Test that reapplying metadata doesn't cause issues."""
        self.schema_mgr.create_table('NL_YS')

        # Apply metadata multiple times
        success1 = self.schema_mgr.apply_metadata_to_table('NL_YS')
        success2 = self.schema_mgr.apply_metadata_to_table('NL_YS')
        success3 = self.schema_mgr.apply_metadata_to_table('NL_YS')

        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertTrue(success3)

        # Metadata should still be consistent
        metadata = self.schema_mgr.get_table_metadata('NL_YS')
        self.assertIsNotNone(metadata)

    def test_metadata_for_all_record_types(self):
        """Test that all record types in TABLE_METADATA can be applied."""
        create_results = self.schema_mgr.create_all_tables()
        self.assertTrue(all(create_results.values()))
        for schema_sql in JRAVAN_SCHEMAS.values():
            self.database.execute(schema_sql)

        for table_name in sorted(set(SCHEMAS) | set(JRAVAN_SCHEMAS)):
            expected = TABLE_METADATA[table_name]
            success = self.schema_mgr.apply_metadata_to_table(table_name)
            self.assertTrue(success, f"Should apply metadata to {table_name}")
            catalog = self.database.fetch_all(f'PRAGMA table_info("{table_name}")')
            stored = self.database.fetch_all(
                """SELECT column_name FROM _metadata
                   WHERE table_name = ? AND metadata_type = 'column'""",
                (table_name,),
            )
            self.assertEqual(
                {row["column_name"] for row in stored},
                {row["name"] for row in catalog},
            )
            metadata_columns = {
                column["name"]: column for column in expected["columns"]
            }
            self.assertEqual(set(metadata_columns), {row["name"] for row in catalog})
            for row in catalog:
                column = metadata_columns[row["name"]]
                self.assertEqual(
                    _catalog_type_family(row["type"]),
                    column["type"],
                    f"{table_name}.{row['name']} type",
                )
                actual_nullable = not bool(row["notnull"]) and not bool(row["pk"])
                self.assertEqual(
                    actual_nullable,
                    column["nullable"],
                    f"{table_name}.{row['name']} nullable",
                )
            self.assertEqual(
                [row["name"] for row in sorted(catalog, key=lambda row: row["pk"]) if row["pk"]],
                expected["primary_key"],
            )


class TestMetadataRetrieval(unittest.TestCase):
    """Test metadata retrieval functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'retrieval_test.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_get_metadata_for_table_with_metadata(self):
        """Test retrieving metadata for table that has metadata applied."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        metadata = self.schema_mgr.get_table_metadata('NL_RA')

        self.assertIsNotNone(metadata)
        self.assertIn('table', metadata)
        self.assertIn('columns', metadata)
        self.assertIsInstance(metadata['columns'], dict)

    def test_get_metadata_for_table_without_metadata(self):
        """Test retrieving metadata for table without metadata applied."""
        self.schema_mgr.create_table('NL_RA')
        # Don't apply metadata

        metadata = self.schema_mgr.get_table_metadata('NL_RA')

        self.assertEqual(metadata, {"table": None, "columns": {}})

    def test_get_metadata_for_nonexistent_table(self):
        """Test retrieving metadata for table that doesn't exist."""
        metadata = self.schema_mgr.get_table_metadata('NONEXISTENT_TABLE')

        self.assertEqual(metadata, {"table": None, "columns": {}})

    def test_column_descriptions_completeness(self):
        """Test that all columns get descriptions."""
        self.schema_mgr.create_table('NL_SE')
        self.schema_mgr.apply_metadata_to_table('NL_SE')

        metadata = self.schema_mgr.get_table_metadata('NL_SE')

        # Should have descriptions for multiple columns
        self.assertGreater(len(metadata['columns']), 0)

        # Check specific columns exist
        col_names = list(metadata['columns'].keys())
        self.assertIn('RecordSpec', col_names)


class TestMCPIntegration(unittest.TestCase):
    """Test metadata features for MCP integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'mcp_test.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_mcp_can_query_table_metadata(self):
        """Test that MCP can query metadata from _metadata table."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        # Simulate MCP querying metadata
        rows = self.database.fetch_all("""
            SELECT table_name, column_name, description
            FROM _metadata
            WHERE table_name = 'NL_RA'
            ORDER BY column_name
        """)

        self.assertGreater(len(rows), 0, "MCP should be able to query metadata")

    def test_mcp_can_discover_all_tables(self):
        """Test that MCP can discover all tables with metadata."""
        # Create multiple tables
        tables = ['NL_RA', 'NL_SE', 'NL_HR']
        for table_name in tables:
            self.schema_mgr.create_table(table_name)
            self.schema_mgr.apply_metadata_to_table(table_name)

        # MCP queries all tables with metadata (column_name is empty string for table descriptions)
        rows = self.database.fetch_all("""
            SELECT DISTINCT table_name
            FROM _metadata
            WHERE column_name = '' AND metadata_type = 'table'
            ORDER BY table_name
        """)

        discovered_tables = [row['table_name'] for row in rows]
        for table_name in tables:
            self.assertIn(table_name, discovered_tables)

    def test_metadata_includes_japanese_descriptions(self):
        """Test that metadata includes Japanese descriptions for MCP."""
        self.schema_mgr.create_table('NL_RA')
        self.schema_mgr.apply_metadata_to_table('NL_RA')

        metadata = self.schema_mgr.get_table_metadata('NL_RA')

        # Should have Japanese descriptions
        self.assertIsNotNone(metadata['table'])
        self.assertTrue(any(ord(char) > 127 for char in metadata['table']))


if __name__ == '__main__':
    unittest.main()
