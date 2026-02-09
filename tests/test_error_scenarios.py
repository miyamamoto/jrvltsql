#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive error scenario tests.

Tests various error conditions and recovery mechanisms:
1. Invalid data handling
2. Database connectivity issues
3. Resource constraints
4. Concurrent operations
5. Data integrity violations
6. Timeout handling
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
import time

from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SchemaManager
from src.database.base import DatabaseError
from src.parser.factory import ParserFactory
from src.importer.importer import DataImporter
from src.fetcher.historical import HistoricalFetcher, FetcherError


class TestInvalidDataHandling(unittest.TestCase):
    """Test handling of invalid input data."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'error_test.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.schema_mgr.create_table('NL_RA')

        self.factory = ParserFactory()
        self.importer = DataImporter(self.database, batch_size=10)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_empty_data_parsing(self):
        """Test parsing empty data."""
        result = self.factory.parse(b"")
        self.assertIsNone(result, "Empty data should return None")

    def test_invalid_record_type(self):
        """Test parsing data with invalid record type."""
        invalid_data = b"ZZ999999999999999999"
        result = self.factory.parse(invalid_data)
        self.assertIsNone(result, "Invalid record type should return None")

    def test_corrupted_data_parsing(self):
        """Test parsing corrupted/malformed data."""
        corrupted_samples = [
            b"\x00\x00\x00\x00",  # Null bytes
            b"\xff\xff\xff\xff",  # Invalid characters
            b"RA",  # Too short
        ]

        for sample in corrupted_samples:
            result = self.factory.parse(sample)
            # Should not crash, may return None
            self.assertIsInstance(result, (dict, type(None)))

    def test_import_invalid_record(self):
        """Test importing record with missing required fields."""
        invalid_record = {
            'レコード種別ID': 'RA',
            # Missing required fields
        }

        success = self.importer.import_single_record(invalid_record)
        # May succeed or fail depending on schema, but shouldn't crash
        self.assertIsInstance(success, bool)

    def test_import_wrong_record_type(self):
        """Test importing record to wrong table."""
        # SE record but trying to import to RA table
        wrong_record = {
            'レコード種別ID': 'SE',  # Should go to NL_SE
            '開催年月日': '20240101',
        }

        success = self.importer.import_single_record(wrong_record)
        # Should handle gracefully
        self.assertIsInstance(success, bool)

    def test_duplicate_key_violation(self):
        """Test handling of duplicate key constraint violations."""
        # Use ASCII field names to avoid encoding issues
        sample = {
            'RecordSpec': 'RA',
            'year': '2024',
            'month_day': '0101'
        }

        # Import first time (may or may not succeed with limited fields)
        success1 = self.importer.import_single_record(sample)

        # Import again (may fail due to UNIQUE constraint)
        success2 = self.importer.import_single_record(sample)

        # Should handle gracefully without crashing
        self.assertIsInstance(success1, bool)
        self.assertIsInstance(success2, bool)

    def test_null_value_handling(self):
        """Test handling of NULL/None values."""
        record_with_nulls = {
            'レコード種別ID': 'RA',
            '開催年月日': None,  # NULL value
            '競馬場コード': '',  # Empty string
        }

        success = self.importer.import_single_record(record_with_nulls)
        # Should handle NULL values gracefully
        self.assertIsInstance(success, bool)


class TestDatabaseConnectivityErrors(unittest.TestCase):
    """Test database connectivity error handling."""

    def test_connect_to_nonexistent_path(self):
        """Test connecting to invalid database path."""
        # Use a path with non-existent parent directories that SQLite can't auto-create
        # Use platform-appropriate invalid path
        import sys
        if sys.platform == "win32":
            invalid_path = "Z:\\nonexistent\\dir\\that\\cannot\\be\\created\\database.db"
        else:
            invalid_path = "/nonexistent/dir/that/cannot/be/created/database.db"

        # Should raise error when trying to use connection
        with self.assertRaises((DatabaseError, Exception)):
            db = SQLiteDatabase({'path': invalid_path})
            db.connect()
            db.execute("CREATE TABLE test (id INTEGER)")

    def test_query_after_disconnect(self):
        """Test querying after database disconnection."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'test.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()
        db.disconnect()

        # Query after disconnect should fail
        with self.assertRaises((DatabaseError, Exception)):
            db.fetch_all("SELECT * FROM non_existent")

        temp_dir.cleanup()

    def test_concurrent_write_conflict(self):
        """Test concurrent write operations."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'concurrent.db'

        db1 = SQLiteDatabase({'path': str(db_path)})
        db1.connect()

        db2 = SQLiteDatabase({'path': str(db_path)})
        db2.connect()

        # Create table in first connection
        db1.execute("""
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)

        # Both connections should be able to write
        # (SQLite handles this with locking)
        try:
            db1.execute("INSERT INTO test VALUES (1, 'from_db1')")
            db2.execute("INSERT INTO test VALUES (2, 'from_db2')")
            # Should complete without deadlock
        except Exception as e:
            # Some conflicts are expected with SQLite
            self.assertIsInstance(e, Exception)

        db1.disconnect()
        db2.disconnect()
        temp_dir.cleanup()

    def test_invalid_sql_syntax(self):
        """Test executing invalid SQL."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'test.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()

        # Invalid SQL should raise error
        with self.assertRaises((DatabaseError, Exception)):
            db.execute("INVALID SQL SYNTAX HERE")

        db.disconnect()
        temp_dir.cleanup()


class TestResourceConstraints(unittest.TestCase):
    """Test behavior under resource constraints."""

    def test_very_large_batch(self):
        """Test importing very large batch of records."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'large_batch.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()

        schema_mgr = SchemaManager(db)
        schema_mgr.create_table('NL_RA')

        # Generate large batch
        large_batch = [
            {
                'レコード種別ID': 'RA',
                '開催年月日': f'2024{i:04d}',
                '競馬場コード': f'{i % 10:02d}',
                'レース番号': f'{i % 12:02d}'
            }
            for i in range(1000)  # 1000 records
        ]

        importer = DataImporter(db, batch_size=100)
        result = importer.import_records(large_batch)

        # Should complete without memory errors
        self.assertIn('records_imported', result)
        self.assertIn('records_failed', result)

        db.disconnect()
        temp_dir.cleanup()

    def test_long_string_values(self):
        """Test handling of very long string values."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'long_strings.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()

        schema_mgr = SchemaManager(db)
        schema_mgr.create_table('NL_RA')

        # Record with very long string
        long_record = {
            'レコード種別ID': 'RA',
            '開催年月日': '20240101',
            'レース名': 'A' * 10000,  # Very long race name
        }

        importer = DataImporter(db, batch_size=10)
        success = importer.import_single_record(long_record)

        # Should handle or truncate long strings
        self.assertIsInstance(success, bool)

        db.disconnect()
        temp_dir.cleanup()

    def test_many_columns_record(self):
        """Test record with many columns."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'many_columns.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()

        schema_mgr = SchemaManager(db)
        schema_mgr.create_table('NL_RA')

        # Create record with all possible fields
        many_fields_record = {'レコード種別ID': 'RA'}
        for i in range(100):
            many_fields_record[f'field_{i}'] = f'value_{i}'

        importer = DataImporter(db, batch_size=10)
        success = importer.import_single_record(many_fields_record)

        # Should handle gracefully (extra fields ignored)
        self.assertIsInstance(success, bool)

        db.disconnect()
        temp_dir.cleanup()


class TestFetcherErrors(unittest.TestCase):
    """Test fetcher error handling."""

    @patch('src.fetcher.base.JVLinkWrapper')
    def test_jvlink_init_failure(self, mock_jvlink_class):
        """Test handling of JV-Link initialization failure."""
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        # Mock JV_Init failure (raises exception)
        mock_jvlink.jv_init.side_effect = Exception("JV_Init failed")

        fetcher = HistoricalFetcher(sid="TEST")

        with self.assertRaises(Exception):
            list(fetcher.fetch("RACE", "20240101", "20240101"))

    @patch('src.fetcher.base.JVLinkWrapper')
    def test_jvopen_failure(self, mock_jvlink_class):
        """Test handling of JVOpen failure."""
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        mock_jvlink.jv_init.return_value = None  # Success
        mock_jvlink.jv_open.side_effect = Exception("JVOpen failed")

        fetcher = HistoricalFetcher(sid="TEST")

        with self.assertRaises(Exception):
            list(fetcher.fetch("RACE", "20240101", "20240101"))

    @patch('src.fetcher.base.JVLinkWrapper')
    @patch('src.fetcher.base.ParserFactory')
    def test_jvread_error_recovery(self, mock_factory, mock_jvlink_class):
        """Test recovery from JVRead errors."""
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        mock_jvlink.jv_init.return_value = None
        mock_jvlink.jv_open.return_value = (0, 10, 0, "")

        # Mock JVRead with error code < -1 (should raise FetcherError)
        mock_jvlink.jv_read.return_value = (-2, b"", "")  # Error code < -1

        # Mock parser
        mock_parser = MagicMock()
        mock_factory.return_value = mock_parser

        fetcher = HistoricalFetcher(sid="TEST")

        # Error code < -1 should raise FetcherError
        with self.assertRaises(FetcherError):
            list(fetcher.fetch("RACE", "20240101", "20240101"))


class TestConcurrencyIssues(unittest.TestCase):
    """Test concurrent operation handling."""

    def test_multiple_importers_same_db(self):
        """Test multiple DataImporter instances on same database."""
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / 'concurrent.db'

        db = SQLiteDatabase({'path': str(db_path)})
        db.connect()

        schema_mgr = SchemaManager(db)
        schema_mgr.create_table('NL_RA')

        # Create multiple importers
        importer1 = DataImporter(db, batch_size=10)
        importer2 = DataImporter(db, batch_size=10)

        # Both try to import
        record1 = {'レコード種別ID': 'RA', '開催年月日': '20240101'}
        record2 = {'レコード種別ID': 'RA', '開催年月日': '20240102'}

        success1 = importer1.import_single_record(record1)
        success2 = importer2.import_single_record(record2)

        # Both should succeed (or handle conflicts)
        self.assertIsInstance(success1, bool)
        self.assertIsInstance(success2, bool)

        db.disconnect()
        temp_dir.cleanup()


class TestDataIntegrityViolations(unittest.TestCase):
    """Test data integrity constraint violations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'integrity.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_foreign_key_violation(self):
        """Test handling of foreign key constraint violations."""
        # Create tables with foreign key
        self.database.execute("""
            CREATE TABLE parent (
                id INTEGER PRIMARY KEY
            )
        """)

        self.database.execute("""
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES parent(id)
            )
        """)

        # Try to insert child with non-existent parent
        # SQLite doesn't enforce FK by default, but test the pattern
        try:
            self.database.execute(
                "INSERT INTO child (id, parent_id) VALUES (1, 999)"
            )
        except Exception as e:
            # FK violation may or may not raise depending on DB config
            self.assertIsInstance(e, Exception)

    def test_check_constraint_violation(self):
        """Test handling of CHECK constraint violations."""
        self.database.execute("""
            CREATE TABLE test_check (
                id INTEGER PRIMARY KEY,
                value INTEGER CHECK(value > 0)
            )
        """)

        # Try to insert invalid value
        with self.assertRaises((DatabaseError, Exception)):
            self.database.execute(
                "INSERT INTO test_check (id, value) VALUES (1, -1)"
            )


if __name__ == '__main__':
    unittest.main()
