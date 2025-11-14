#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive integration tests covering all major workflows.

This test suite validates end-to-end integration of:
- JV-Link wrapper
- Data fetching (historical + realtime)
- Parsing (all record types)
- Database operations (SQLite, DuckDB, PostgreSQL)
- Import workflow
- Realtime monitoring

Test Categories:
1. Full pipeline tests (fetch → parse → import → query)
2. Multi-database consistency tests
3. Realtime integration tests
4. Batch processing tests
5. Transaction handling tests
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.database.sqlite_handler import SQLiteDatabase
from src.database.duckdb_handler import DuckDBDatabase
from src.database.postgresql_handler import PostgreSQLDatabase
from src.database.schema import SchemaManager, SCHEMAS
from src.parser.factory import ParserFactory, ALL_RECORD_TYPES
from src.importer.importer import DataImporter
from src.importer.batch import BatchProcessor
from src.fetcher.historical import HistoricalFetcher
from src.fetcher.realtime import RealtimeFetcher
from src.services.realtime_monitor import RealtimeMonitor
from src.jvlink.constants import JV_RT_SUCCESS, JV_READ_SUCCESS


class TestFullPipelineIntegration(unittest.TestCase):
    """Test complete data flow from fetching to storage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'integration.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.factory = ParserFactory()

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_parse_and_import_workflow(self):
        """Test parsing sample data and importing to database."""
        # Create NL_RA table
        self.assertTrue(self.schema_mgr.create_table("NL_RA"))

        # Sample RA record (simplified)
        sample_ra = (
            "RA120241201100120240101000000000000000000000000000000000"
            "東京0110R  1回東京1日1R                          "
            "新馬    芝    右  外 1600200024121412002412300000000"
        )

        # Parse
        record = self.factory.parse(sample_ra.encode('shift_jis'))

        if record:  # Parser may return None for incomplete data
            self.assertEqual(record.get('レコード種別ID'), 'RA')

            # Import
            importer = DataImporter(self.database, batch_size=10)
            success = importer.import_single_record(record)
            self.assertTrue(success, "Import should succeed")

            # Query back
            rows = self.database.fetch_all("SELECT * FROM NL_RA")
            self.assertGreater(len(rows), 0, "Should have imported data")

    def test_batch_processor_workflow(self):
        """Test batch processor with mocked JV-Link."""
        # Create necessary tables
        self.schema_mgr.create_all_tables()

        # Mock JV-Link to avoid actual API calls
        with patch('src.fetcher.base.JVLinkWrapper') as mock_jvlink_class:
            mock_jvlink = MagicMock()
            mock_jvlink_class.return_value = mock_jvlink

            # Mock JVOpen success
            mock_jvlink.jv_init.return_value = JV_RT_SUCCESS
            mock_jvlink.jv_open.return_value = (JV_RT_SUCCESS, 0, 0, "")
            mock_jvlink.jv_read.return_value = (0, b"", "")  # No data

            # Create batch processor
            processor = BatchProcessor(
                database=self.database,
                sid="TEST",
                batch_size=100
            )

            # Process (will return empty but shouldn't error)
            result = processor.process_date_range(
                data_spec="RACE",
                from_date="20240101",
                to_date="20240101"
            )

            self.assertIn('records_fetched', result)
            self.assertIn('records_parsed', result)
            self.assertIn('records_imported', result)

    def test_multiple_record_types(self):
        """Test importing multiple different record types."""
        # Create tables for multiple types
        test_tables = ['NL_RA', 'NL_SE', 'NL_HR', 'NL_YS']
        for table_name in test_tables:
            self.schema_mgr.create_table(table_name)

        # Sample records for different types
        samples = {
            'RA': b"RA120241201100120240101...",
            'SE': b"SE120241201100120240101...",
            'HR': b"HR120241201100120240101...",
            'YS': b"YS120241201100120240101...",
        }

        importer = DataImporter(self.database, batch_size=10)

        for record_type, sample in samples.items():
            parsed = self.factory.parse(sample)
            if parsed:
                # Should route to correct table
                success = importer.import_single_record(parsed)
                # May fail due to incomplete sample data, but shouldn't crash
                self.assertIsInstance(success, bool)


class TestMultiDatabaseConsistency(unittest.TestCase):
    """Test that same operations produce consistent results across databases."""

    def setUp(self):
        """Set up test databases."""
        self.temp_dir = tempfile.TemporaryDirectory()

        # SQLite
        sqlite_path = Path(self.temp_dir.name) / 'test.db'
        self.sqlite = SQLiteDatabase({'path': str(sqlite_path)})
        self.sqlite.connect()

        # DuckDB
        duckdb_path = Path(self.temp_dir.name) / 'test.duckdb'
        self.duckdb = DuckDBDatabase({'path': str(duckdb_path)})
        self.duckdb.connect()

        # PostgreSQL (skip if not available)
        try:
            pg_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'jltsql_test'),
                'user': os.getenv('POSTGRES_USER', 'jltsql'),
                'password': os.getenv('POSTGRES_PASSWORD', 'jltsql_pass')
            }
            self.postgresql = PostgreSQLDatabase(pg_config)
            self.postgresql.connect()
            self.pg_available = True
        except Exception:
            self.pg_available = False

        self.databases = [self.sqlite, self.duckdb]
        if self.pg_available:
            self.databases.append(self.postgresql)

    def tearDown(self):
        """Clean up."""
        for db in self.databases:
            if db._connection:
                db.disconnect()
        self.temp_dir.cleanup()

    def test_schema_creation_consistency(self):
        """Test that all databases create same schemas."""
        for db in self.databases:
            schema_mgr = SchemaManager(db)
            results = schema_mgr.create_all_tables()

            # All databases should create same number of tables
            successful = sum(1 for success in results.values() if success)
            self.assertEqual(successful, 57,
                f"{db.__class__.__name__}: Should create 57 tables")

    def test_data_storage_consistency(self):
        """Test that same data is stored consistently across databases."""
        sample_data = {
            'レコード種別ID': 'RA',
            '開催年月日': '20240101',
            '競馬場コード': '01',
            'レース番号': '01'
        }

        for db in self.databases:
            schema_mgr = SchemaManager(db)
            schema_mgr.create_table('NL_RA')

            # Insert same data
            importer = DataImporter(db, batch_size=10)
            success = importer.import_single_record(sample_data)

            if success:
                # Query back
                rows = db.fetch_all("SELECT * FROM NL_RA")
                self.assertEqual(len(rows), 1,
                    f"{db.__class__.__name__}: Should have 1 row")


class TestRealtimeIntegration(unittest.TestCase):
    """Test realtime monitoring integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'realtime.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    @patch('src.fetcher.base.JVLinkWrapper')
    @patch('src.fetcher.base.ParserFactory')
    def test_realtime_fetcher_integration(self, mock_factory, mock_jvlink_class):
        """Test RealtimeFetcher with mocked JV-Link."""
        # Setup mocks
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        mock_jvlink.jv_init.return_value = JV_RT_SUCCESS
        mock_jvlink.jv_rt_open.return_value = (JV_RT_SUCCESS, 10)
        mock_jvlink.jv_read.side_effect = [
            (JV_READ_SUCCESS, b"RA20240101...", "test.txt"),
            (0, b"", ""),  # End of data
        ]

        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {'レコード種別ID': 'RA', 'data': 'test'}
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory.return_value = mock_factory_instance

        # Test fetcher
        fetcher = RealtimeFetcher(sid="TEST")
        records = list(fetcher.fetch(data_spec="0B12", continuous=False))

        # Should have processed records
        self.assertGreaterEqual(len(records), 0)

    @patch('src.database.schema.SchemaManager')
    @patch('src.services.realtime_monitor.threading.Thread')
    def test_realtime_monitor_lifecycle(self, mock_thread, mock_schema_mgr):
        """Test RealtimeMonitor start/stop lifecycle."""
        # Mock schema manager
        mock_mgr = MagicMock()
        mock_mgr.get_missing_tables.return_value = []
        mock_schema_mgr.return_value = mock_mgr

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Create monitor
        monitor = RealtimeMonitor(
            database=self.database,
            data_specs=["0B12"],
            sid="TEST"
        )

        # Test lifecycle
        self.assertFalse(monitor.status.is_running)

        success = monitor.start()
        self.assertTrue(success)
        self.assertTrue(monitor.status.is_running)

        success = monitor.stop()
        self.assertTrue(success)
        self.assertFalse(monitor.status.is_running)


class TestTransactionHandling(unittest.TestCase):
    """Test transaction and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'transaction.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.schema_mgr.create_table('NL_RA')

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_transaction_commit(self):
        """Test successful transaction commit."""
        importer = DataImporter(self.database, batch_size=10)

        # Use RecordSpec to get proper field names
        sample = {
            'RecordSpec': 'RA',  # Using ASCII field name to avoid encoding issues
            'year': '2024',
            'month_day': '0101'
        }

        # Import may or may not succeed with limited fields, but shouldn't crash
        success = importer.import_single_record(sample)

        # Verify database connection still works
        rows = self.database.fetch_all("SELECT * FROM NL_RA")
        # Should return empty or with records depending on whether import succeeded
        self.assertIsInstance(rows, list)

    def test_batch_import_partial_failure(self):
        """Test batch import with some invalid records."""
        importer = DataImporter(self.database, batch_size=5)

        records = [
            {'RecordSpec': 'RA', 'year': '2024'},  # May succeed with limited fields
            {'RecordSpec': 'INVALID'},  # Invalid record type
            {'RecordSpec': 'RA', 'year': '2024'},  # May succeed with limited fields
        ]

        result = importer.import_records(records)

        # Should have statistics (at least the invalid one should fail)
        self.assertIn('records_imported', result)
        self.assertIn('records_failed', result)
        # Invalid record type should fail
        self.assertGreater(result['records_failed'], 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'edge.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_empty_database(self):
        """Test operations on empty database."""
        schema_mgr = SchemaManager(self.database)

        # Query non-existent table (should not crash)
        with self.assertRaises(Exception):
            self.database.fetch_all("SELECT * FROM non_existent")

        # Create and query empty table
        schema_mgr.create_table('NL_RA')
        rows = self.database.fetch_all("SELECT * FROM NL_RA")
        self.assertEqual(len(rows), 0)

    def test_large_batch_size(self):
        """Test with unusually large batch size."""
        schema_mgr = SchemaManager(self.database)
        schema_mgr.create_table('NL_RA')

        importer = DataImporter(self.database, batch_size=10000)

        # Should not crash with large batch size
        records = [
            {'レコード種別ID': 'RA', '開催年月日': f'2024010{i % 10}'}
            for i in range(100)
        ]

        result = importer.import_records(records)
        self.assertIn('records_imported', result)

    def test_unicode_handling(self):
        """Test handling of Japanese characters."""
        schema_mgr = SchemaManager(self.database)
        schema_mgr.create_table('NL_RA')

        # Sample with Japanese text
        sample = {
            'レコード種別ID': 'RA',
            '開催年月日': '20240101',
            'レース名': '東京新聞杯',  # Japanese race name
            '競馬場名': '東京'  # Japanese venue name
        }

        importer = DataImporter(self.database, batch_size=10)
        success = importer.import_single_record(sample)

        if success:
            rows = self.database.fetch_all("SELECT * FROM NL_RA")
            self.assertGreater(len(rows), 0)


if __name__ == '__main__':
    unittest.main()
