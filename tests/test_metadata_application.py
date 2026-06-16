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

Note: DuckDB is not supported (32-bit Python required for JV-Link).
"""

import os
import tempfile
import unittest
from pathlib import Path

from src.database.sqlite_handler import SQLiteDatabase
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SchemaManager
from src.database.schema_metadata import TABLE_METADATA


def test_metadata_primary_key_columns_are_described():
    """Every metadata primary-key column should have a column definition."""

    for table_name, metadata in TABLE_METADATA.items():
        defined_columns = {column["name"] for column in metadata["columns"]}
        missing = set(metadata.get("primary_key", [])) - defined_columns
        assert not missing, f"{table_name} primary_key references missing columns: {sorted(missing)}"


def test_av_metadata_matches_scratch_exclusion_schema():
    """AV metadata should describe the official race/horse scratch schema."""

    for table_name in ("NL_AV", "RT_AV"):
        metadata = TABLE_METADATA[table_name]
        column_names = {column["name"] for column in metadata["columns"]}
        assert "出走取消・競走除外" in metadata["description"]
        assert metadata["primary_key"] == [
            "開催年", "開催月日", "競馬場コード", "開催回",
            "開催日目", "レース番号", "馬番",
        ]
        assert {"開催年", "開催月日", "競馬場コード", "レース番号", "馬番", "事由区分"} <= column_names
        assert "セール主催者名" not in column_names
        assert "取引価格" not in column_names


def test_hs_metadata_matches_market_price_schema():
    """HS metadata should describe the official market-price schema."""

    metadata = TABLE_METADATA["NL_HS"]
    column_names = {column["name"] for column in metadata["columns"]}
    assert "競走馬市場取引価格" in metadata["description"]
    assert metadata["primary_key"] == ["血統登録番号", "主催者・市場コード", "市場開始日"]
    assert {"血統登録番号", "主催者・市場コード", "市場開始日", "取引価格"} <= column_names


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
        self.assertIn('レコード種別ID', col_names)

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

        # Apply metadata twice
        success1 = self.schema_mgr.apply_metadata_to_table('NL_RA')
        success2 = self.schema_mgr.apply_metadata_to_table('NL_RA')

        self.assertTrue(success1)
        self.assertTrue(success2)

        # Should still have only one table description (column_name is empty string)
        rows = self.database.fetch_all(
            """SELECT COUNT(*) as cnt FROM _metadata
               WHERE table_name = 'NL_RA' AND column_name = ''"""
        )
        self.assertEqual(rows[0]['cnt'], 1)


class TestPostgreSQLMetadata(unittest.TestCase):
    """Test metadata application and retrieval for PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        """Check if PostgreSQL is available."""
        try:
            pg_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'jltsql_test'),
                'user': os.getenv('POSTGRES_USER', 'jltsql'),
                'password': os.getenv('POSTGRES_PASSWORD', 'jltsql_pass')
            }
            test_db = PostgreSQLDatabase(pg_config)
            test_db.connect()
            test_db.disconnect()
            cls.pg_available = True
        except Exception:
            cls.pg_available = False

    def setUp(self):
        """Set up test fixtures."""
        if not self.pg_available:
            self.skipTest("PostgreSQL not available")

        pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'jltsql_test'),
            'user': os.getenv('POSTGRES_USER', 'jltsql'),
            'password': os.getenv('POSTGRES_PASSWORD', 'jltsql_pass')
        }

        self.database = PostgreSQLDatabase(pg_config)
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)

    def tearDown(self):
        """Clean up."""
        if self.pg_available:
            # Drop test tables
            try:
                self.database.execute("DROP TABLE IF EXISTS NL_RA CASCADE")
                self.database.execute("DROP TABLE IF EXISTS NL_SE CASCADE")
                self.database.execute("DROP TABLE IF EXISTS NL_HR CASCADE")
            except Exception:
                pass
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
            WHERE table_name = 'NL_RA'
        """)

        self.assertEqual(len(rows), 1)


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
        # Sample a few different record types
        sample_tables = [
            'NL_RA',  # Race
            'NL_SE',  # Horse per race
            'NL_HR',  # Payoff
            'NL_UM',  # Horse master
            'NL_KS',  # Jockey master
            'NL_O1',  # Odds
            'RT_RA',  # Realtime race
        ]

        for table_name in sample_tables:
            if table_name in TABLE_METADATA:
                self.schema_mgr.create_table(table_name)
                success = self.schema_mgr.apply_metadata_to_table(table_name)
                self.assertTrue(success,
                    f"Should apply metadata to {table_name}")


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

        # Should return None or empty metadata
        if metadata is not None:
            self.assertEqual(len(metadata.get('columns', {})), 0)

    def test_get_metadata_for_nonexistent_table(self):
        """Test retrieving metadata for table that doesn't exist."""
        metadata = self.schema_mgr.get_table_metadata('NONEXISTENT_TABLE')

        # Should return dict with None table and empty columns, or empty dict
        if metadata:
            self.assertIsNone(metadata.get('table'))
            self.assertEqual(metadata.get('columns', {}), {})

    def test_column_descriptions_completeness(self):
        """Test that all columns get descriptions."""
        self.schema_mgr.create_table('NL_SE')
        self.schema_mgr.apply_metadata_to_table('NL_SE')

        metadata = self.schema_mgr.get_table_metadata('NL_SE')

        # Should have descriptions for multiple columns
        self.assertGreater(len(metadata['columns']), 0)

        # Check specific columns exist
        col_names = list(metadata['columns'].keys())
        self.assertIn('レコード種別ID', col_names)


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
        # Verify it contains Japanese characters
        if metadata['table']:
            self.assertTrue(any(ord(char) > 127 for char in metadata['table']))


if __name__ == '__main__':
    unittest.main()
