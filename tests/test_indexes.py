#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for database index management."""

import tempfile
import unittest
from pathlib import Path

from src.database.indexes import INDEXES, IndexManager
from src.database.schema import SchemaManager
from src.database.sqlite_handler import SQLiteDatabase


class TestIndexDefinitions(unittest.TestCase):
    """Test index definitions structure."""

    def test_indexes_structure(self):
        """Test that INDEXES dict is properly structured."""
        self.assertIsInstance(INDEXES, dict)
        self.assertGreater(len(INDEXES), 0, "Should have index definitions")

        for table_name, index_list in INDEXES.items():
            self.assertIsInstance(index_list, list)
            self.assertGreater(len(index_list), 0, f"{table_name} should have indexes")

            for index_sql in index_list:
                self.assertIsInstance(index_sql, str)
                self.assertIn("CREATE INDEX", index_sql)
                self.assertIn(table_name, index_sql)

    def test_index_count(self):
        """Test that we have indexes for all working tables."""
        # 37 working tables (25 NL + 12 RT) — NL_SE and RT_SE added
        expected_tables = {
            'NL_AV', 'NL_BN', 'NL_BR', 'NL_BT', 'NL_CC', 'NL_CH', 'NL_CS', 'NL_DM',
            'NL_HS', 'NL_HY', 'NL_JG', 'NL_KS', 'NL_O1', 'NL_O2', 'NL_O3', 'NL_O4',
            'NL_RA', 'NL_RC', 'NL_SE', 'NL_TC', 'NL_TK', 'NL_TM', 'NL_WH', 'NL_YS',
            'RT_AV', 'RT_CC', 'RT_DM', 'RT_O1', 'RT_O2', 'RT_O3', 'RT_O4',
            'RT_RA', 'RT_RC', 'RT_SE', 'RT_TC', 'RT_TM', 'RT_WH'
        }

        defined_tables = set(INDEXES.keys())
        self.assertEqual(len(defined_tables), 37, "Should have indexes for 37 tables")
        self.assertEqual(defined_tables, expected_tables, "Should match working tables")

    def test_total_index_count(self):
        """Test total number of indexes defined."""
        total = sum(len(indexes) for indexes in INDEXES.values())
        # We defined 120+ indexes total
        self.assertGreaterEqual(total, 100, "Should have at least 100 indexes defined")

    def test_key_indexes_present(self):
        """Test that key tables have important indexes."""
        # NL_RA should have the most indexes (most queried table)
        self.assertIn('NL_RA', INDEXES)
        nl_ra_indexes = INDEXES['NL_RA']
        self.assertGreaterEqual(len(nl_ra_indexes), 6, "NL_RA should have many indexes")

        # Check for date indexes (critical for range queries)
        # Schema uses English column names: Year, JyoCD, RaceNum
        nl_ra_sql = ' '.join(nl_ra_indexes)
        self.assertIn('Year', nl_ra_sql, "Should have date index")
        self.assertIn('JyoCD', nl_ra_sql, "Should have venue index")
        self.assertIn('RaceNum', nl_ra_sql, "Should have race index")


class TestIndexManager(unittest.TestCase):
    """Test IndexManager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.db'

        self.db = SQLiteDatabase({'path': str(self.db_path)})
        self.db.connect()

        # Create schema manager and a test table
        self.schema_manager = SchemaManager(self.db)
        self.schema_manager.create_table('NL_RA')  # Create one test table

        self.index_manager = IndexManager(self.db)

    def tearDown(self):
        """Clean up."""
        self.db.disconnect()
        self.temp_dir.cleanup()

    def test_index_manager_initialization(self):
        """Test IndexManager initialization."""
        self.assertIsNotNone(self.index_manager)
        self.assertEqual(self.index_manager.database, self.db)

    def test_create_indexes_single_table(self):
        """Test creating indexes for a single table."""
        result = self.index_manager.create_indexes('NL_RA')
        self.assertTrue(result, "Should successfully create indexes")

        # Verify indexes were created by checking SQLite master table
        sql = "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_nl_ra%'"
        indexes = self.db.fetch_all(sql)
        self.assertGreater(len(indexes), 0, "Should have created indexes")

    def test_create_indexes_nonexistent_table(self):
        """Test creating indexes for table without definitions."""
        result = self.index_manager.create_indexes('NONEXISTENT_TABLE')
        self.assertFalse(result, "Should return False for nonexistent table")

    def test_get_index_count(self):
        """Test getting index count for a table."""
        count = self.index_manager.get_index_count('NL_RA')
        self.assertGreater(count, 0, "NL_RA should have indexes")

        count_none = self.index_manager.get_index_count('NONEXISTENT')
        self.assertEqual(count_none, 0, "Nonexistent table should have 0 indexes")

    def test_get_all_index_count(self):
        """Test getting total index count."""
        total = self.index_manager.get_all_index_count()
        self.assertGreaterEqual(total, 100, "Should have at least 100 total indexes")

    def test_list_tables_with_indexes(self):
        """Test listing tables with index definitions."""
        tables = self.index_manager.list_tables_with_indexes()
        self.assertEqual(len(tables), 37, "Should have 37 tables with indexes")
        self.assertIn('NL_RA', tables)
        self.assertIn('NL_SE', tables)
        self.assertIn('RT_RA', tables)
        self.assertIn('RT_RC', tables)
        self.assertIn('RT_SE', tables)

    def test_drop_indexes(self):
        """Test dropping indexes from a table."""
        # First create indexes
        self.index_manager.create_indexes('NL_RA')

        # Verify they exist
        sql = "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_nl_ra%'"
        indexes_before = self.db.fetch_all(sql)
        self.assertGreater(len(indexes_before), 0)

        # Drop indexes
        result = self.index_manager.drop_indexes('NL_RA')
        self.assertTrue(result, "Should successfully drop indexes")

        # Verify they're gone
        indexes_after = self.db.fetch_all(sql)
        self.assertEqual(len(indexes_after), 0, "Indexes should be dropped")


class TestIndexCreationIntegration(unittest.TestCase):
    """Integration tests for creating indexes on multiple tables."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.db'

        self.db = SQLiteDatabase({'path': str(self.db_path)})
        self.db.connect()

        self.schema_manager = SchemaManager(self.db)
        self.index_manager = IndexManager(self.db)

    def tearDown(self):
        """Clean up."""
        self.db.disconnect()
        self.temp_dir.cleanup()

    def test_create_all_indexes(self):
        """Test creating all indexes across multiple tables."""
        # Create a few test tables first
        test_tables = ['NL_RA', 'NL_AV', 'NL_BN', 'RT_RA', 'RT_O1']

        for table in test_tables:
            self.schema_manager.create_table(table)

        # Create all indexes
        results = self.index_manager.create_all_indexes()

        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0, "Should have results")

        # Check that indexes were created for our test tables
        for table in test_tables:
            if table in results:
                self.assertGreater(
                    results[table], 0,
                    f"Should have created indexes for {table}"
                )

    def test_indexes_work_with_queries(self):
        """Test that indexes improve query performance (functionality check)."""
        # Create table and indexes
        self.schema_manager.create_table('NL_RA')
        self.index_manager.create_indexes('NL_RA')

        # Test query with indexed column
        # This should not raise an error
        # Schema uses English column names: Year, JyoCD, RaceNum
        try:
            result = self.db.fetch_all(
                "SELECT * FROM NL_RA WHERE Year = 2024"
            )
            self.assertIsNotNone(result, "Query should work with indexed column")
        except Exception as e:
            self.fail(f"Query with indexed column failed: {e}")

    def test_composite_index_creation(self):
        """Test that composite indexes are created properly."""
        # NL_RA has composite index: idx_nl_ra_venue_date
        self.schema_manager.create_table('NL_RA')
        self.index_manager.create_indexes('NL_RA')

        # Check if composite index exists
        sql = """
            SELECT name FROM sqlite_master
            WHERE type='index'
            AND name = 'idx_nl_ra_venue_date'
        """
        result = self.db.fetch_one(sql)
        self.assertIsNotNone(result, "Composite index should exist")


class TestIndexPerformance(unittest.TestCase):
    """Test index performance characteristics."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.db'

        self.db = SQLiteDatabase({'path': str(self.db_path)})
        self.db.connect()

        self.schema_manager = SchemaManager(self.db)
        self.index_manager = IndexManager(self.db)

    def tearDown(self):
        """Clean up."""
        self.db.disconnect()
        self.temp_dir.cleanup()

    def test_index_creation_is_idempotent(self):
        """Test that creating indexes multiple times doesn't cause errors."""
        self.schema_manager.create_table('NL_RA')

        # Create indexes first time
        result1 = self.index_manager.create_indexes('NL_RA')
        self.assertTrue(result1)

        # Create indexes second time (should use IF NOT EXISTS)
        result2 = self.index_manager.create_indexes('NL_RA')
        self.assertTrue(result2, "Should be idempotent")

    def test_realtime_table_indexes(self):
        """Test that real-time tables have appropriate indexes."""
        # Real-time tables should have date/venue/race indexes
        rt_tables = ['RT_RA', 'RT_O1', 'RT_AV', 'RT_WH', 'RT_RC']

        for table in rt_tables:
            self.assertIn(table, INDEXES, f"{table} should have index definitions")

            index_sqls = INDEXES[table]
            self.assertGreater(
                len(index_sqls), 0,
                f"{table} should have at least one index"
            )


if __name__ == '__main__':
    unittest.main()
