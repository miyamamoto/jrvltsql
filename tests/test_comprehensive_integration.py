#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive integration tests covering all major workflows.

This deterministic suite validates synthetic fetch, parse, SQLite import, and
realtime-monitor integration. Authenticated acquisition and live PostgreSQL
coverage are separate opt-in suites.

Test Categories:
1. Full pipeline tests (fetch → parse → import → query)
2. Realtime integration tests
3. Batch processing tests
4. Transaction handling tests
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.database.migration import SchemaMigrationError
from src.database.schema import SchemaManager
from src.database.sqlite_handler import SQLiteDatabase
from src.fetcher.realtime import RealtimeFetcher
from src.importer.batch import BatchProcessor
from src.importer.importer import DataImporter
from src.jvlink.constants import JV_RT_SUCCESS
from src.parser.factory import ParserFactory
from src.services.realtime_monitor import RealtimeMonitor
from tests.fixtures.record_factory import make_hr_record, make_ra_record, make_se_record


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

        record = self.factory.parse(make_ra_record(hondai="統合テスト競走"))
        self.assertIsNotNone(record)
        self.assertEqual(record["RecordSpec"], "RA")

        importer = DataImporter(self.database, batch_size=10)
        self.assertTrue(importer.import_single_record(record))

        rows = self.database.fetch_all("SELECT Hondai FROM NL_RA")
        self.assertEqual(rows, [{"Hondai": "統合テスト競走"}])

    def test_batch_processor_workflow(self):
        """Test batch processor with mocked JV-Link."""
        # Create necessary tables
        results = self.schema_mgr.create_all_tables()
        self.assertTrue(all(results.values()))

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

            result = processor.process_date_range(
                data_spec="RACE",
                from_date="20240101",
                to_date="20240101"
            )

            self.assertEqual(result['records_fetched'], 0)
            self.assertEqual(result['records_parsed'], 0)
            self.assertEqual(result['records_imported'], 0)
            mock_jvlink.jv_close.assert_called_once_with()

    def test_multiple_record_types(self):
        """Test importing multiple different record types."""
        # Create tables for multiple types
        test_tables = ['NL_RA', 'NL_SE', 'NL_HR']
        for table_name in test_tables:
            self.assertTrue(self.schema_mgr.create_table(table_name))

        samples = {
            'RA': make_ra_record(),
            'SE': make_se_record(),
            'HR': make_hr_record(),
        }

        importer = DataImporter(self.database, batch_size=10)

        for record_type, sample in samples.items():
            parsed = self.factory.parse(sample)
            self.assertIsNotNone(parsed)
            self.assertEqual(parsed["RecordSpec"], record_type)
            self.assertTrue(importer.import_single_record(parsed))
            rows = self.database.fetch_all(f"SELECT RecordSpec FROM NL_{record_type}")
            self.assertEqual(rows, [{"RecordSpec": record_type}])


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
        payload = b"RA20240101..."
        mock_jvlink.jv_read.side_effect = [
            (len(payload), payload, "test.txt"),
            (0, b"", ""),  # End of data
        ]

        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {'RecordSpec': 'RA', 'data': 'test'}
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory.return_value = mock_factory_instance

        # Test fetcher
        fetcher = RealtimeFetcher(sid="TEST")
        records = list(fetcher.fetch(data_spec="0B12", continuous=False))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["RecordSpec"], "RA")
        mock_jvlink.jv_close.assert_called_once_with()

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

        sample = ParserFactory().parse(make_ra_record(hondai="コミット確認"))
        self.assertIsNotNone(sample)
        self.assertTrue(importer.import_single_record(sample))

        rows = self.database.fetch_all("SELECT Hondai FROM NL_RA")
        self.assertEqual(rows, [{"Hondai": "コミット確認"}])

    def test_batch_import_partial_failure(self):
        """Test batch import with some invalid records."""
        importer = DataImporter(self.database, batch_size=5)
        factory = ParserFactory()

        records = [
            factory.parse(make_ra_record(race_num="01")),
            {"RecordSpec": "RA", "DataKubun": "Z"},
            factory.parse(make_ra_record(race_num="02")),
        ]
        self.assertTrue(all(record is not None for record in (records[0], records[2])))

        with self.assertRaises(SchemaMigrationError):
            importer.import_records(records)

        self.assertEqual(
            self.database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"],
            0,
        )


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

        factory = ParserFactory()
        records = [
            factory.parse(make_ra_record(race_num=f"{race_num:02d}"))
            for race_num in range(1, 11)
        ]
        self.assertTrue(all(record is not None for record in records))

        result = importer.import_records(records)
        self.assertEqual(result['records_imported'], 10)
        self.assertEqual(result['records_failed'], 0)
        self.assertEqual(
            self.database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"],
            10,
        )

    def test_unicode_handling(self):
        """Test handling of Japanese characters."""
        schema_mgr = SchemaManager(self.database)
        schema_mgr.create_table('NL_RA')

        sample = ParserFactory().parse(make_ra_record(hondai="東京新聞杯"))
        self.assertIsNotNone(sample)

        importer = DataImporter(self.database, batch_size=10)
        self.assertTrue(importer.import_single_record(sample))
        rows = self.database.fetch_all("SELECT Hondai FROM NL_RA")
        self.assertEqual(rows, [{"Hondai": "東京新聞杯"}])


if __name__ == '__main__':
    unittest.main()
