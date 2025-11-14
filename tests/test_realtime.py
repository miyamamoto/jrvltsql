#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for realtime data fetching and monitoring."""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time

from src.fetcher.realtime import RealtimeFetcher
from src.services.realtime_monitor import RealtimeMonitor, MonitorStatus
from src.jvlink.constants import JV_RT_SUCCESS, JV_READ_SUCCESS


class TestRealtimeFetcher(unittest.TestCase):
    """Test RealtimeFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sid = "TEST_SID"

    @patch('src.fetcher.base.JVLinkWrapper')
    @patch('src.fetcher.base.ParserFactory')
    def test_initialization(self, mock_factory, mock_jvlink):
        """Test RealtimeFetcher initialization."""
        fetcher = RealtimeFetcher(sid=self.sid)

        # Check that fetcher initializes correctly
        self.assertIsNotNone(fetcher.jvlink)
        self.assertIsNotNone(fetcher.parser_factory)
        self.assertFalse(fetcher._stream_open)

    def test_list_data_specs(self):
        """Test listing available data specs."""
        specs = RealtimeFetcher.list_data_specs()

        # Should return dict of specs
        self.assertIsInstance(specs, dict)
        self.assertGreater(len(specs), 0)

        # Check some known specs
        self.assertIn("0B12", specs)  # Race results
        self.assertIn("0B15", specs)  # Payouts
        self.assertIn("0B31", specs)  # Odds

    @patch('src.fetcher.base.ParserFactory')
    @patch('src.fetcher.base.JVLinkWrapper')
    def test_fetch_single_batch(self, mock_jvlink_class, mock_factory):
        """Test fetching in single batch mode."""
        # Setup mocks
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        mock_jvlink.jv_init.return_value = JV_RT_SUCCESS
        mock_jvlink.jv_rt_open.return_value = (JV_RT_SUCCESS, 10)

        # Mock JVRead responses
        # ret_code > 0 means success with data (value is data length)
        # ret_code == 0 means no more data
        mock_jvlink.jv_read.side_effect = [
            (100, b"RA20240101...", "test.txt"),  # 100 bytes of data
            (100, b"RA20240102...", "test.txt"),  # 100 bytes of data
            (0, b"", ""),  # End of data (JV_READ_SUCCESS)
        ]

        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = [
            {"レコード種別ID": "RA", "data": "test1"},
            {"レコード種別ID": "RA", "data": "test2"},
        ]
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory.return_value = mock_factory_instance

        # Create fetcher and fetch
        fetcher = RealtimeFetcher(sid=self.sid)
        records = list(fetcher.fetch(data_spec="0B12", continuous=False))

        # Verify results
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["レコード種別ID"], "RA")
        self.assertEqual(records[1]["レコード種別ID"], "RA")

        # Verify JV-Link calls
        mock_jvlink.jv_init.assert_called_once()
        mock_jvlink.jv_rt_open.assert_called_once_with("0B12", "")
        mock_jvlink.jv_close.assert_called_once()

    @patch('src.fetcher.base.JVLinkWrapper')
    @patch('src.fetcher.base.ParserFactory')
    def test_fetch_invalid_spec_warning(self, mock_factory, mock_jvlink_class):
        """Test warning for unknown data spec."""
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        mock_jvlink.jv_init.return_value = JV_RT_SUCCESS
        mock_jvlink.jv_rt_open.return_value = (JV_RT_SUCCESS, 0)
        mock_jvlink.jv_read.return_value = (0, b"", "")

        fetcher = RealtimeFetcher(sid=self.sid)

        # Should proceed despite warning
        with patch('src.fetcher.realtime.logger') as mock_logger:
            list(fetcher.fetch(data_spec="INVALID", continuous=False))
            mock_logger.warning.assert_called()

    @patch('src.fetcher.base.JVLinkWrapper')
    @patch('src.fetcher.base.ParserFactory')
    def test_context_manager(self, mock_factory, mock_jvlink_class):
        """Test context manager protocol."""
        mock_jvlink = MagicMock()
        mock_jvlink_class.return_value = mock_jvlink

        with RealtimeFetcher(sid=self.sid) as fetcher:
            self.assertIsNotNone(fetcher)

        # Context manager exit should not raise


class TestMonitorStatus(unittest.TestCase):
    """Test MonitorStatus class."""

    def test_initialization(self):
        """Test MonitorStatus initialization."""
        status = MonitorStatus()

        self.assertIsNone(status.started_at)
        self.assertIsNone(status.stopped_at)
        self.assertFalse(status.is_running)
        self.assertEqual(status.records_imported, 0)
        self.assertEqual(status.records_failed, 0)
        self.assertEqual(len(status.errors), 0)
        self.assertEqual(len(status.monitored_specs), 0)

    def test_to_dict(self):
        """Test status conversion to dict."""
        from datetime import datetime

        status = MonitorStatus()
        status.is_running = True
        status.started_at = datetime.now()
        status.records_imported = 100
        status.monitored_specs = {"0B12", "0B15"}

        status_dict = status.to_dict()

        self.assertTrue(status_dict["is_running"])
        self.assertIsNotNone(status_dict["started_at"])
        self.assertEqual(status_dict["records_imported"], 100)
        self.assertIn("0B12", status_dict["monitored_specs"])
        self.assertIn("0B15", status_dict["monitored_specs"])


class TestRealtimeMonitor(unittest.TestCase):
    """Test RealtimeMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.mock_db._connection = MagicMock()

    def test_initialization(self):
        """Test RealtimeMonitor initialization."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12", "0B15"],
            sid="TEST_SID",
            batch_size=50
        )

        self.assertEqual(monitor.database, self.mock_db)
        self.assertEqual(monitor.data_specs, ["0B12", "0B15"])
        self.assertEqual(monitor.sid, "TEST_SID")
        self.assertEqual(monitor.batch_size, 50)
        self.assertFalse(monitor.status.is_running)
        self.assertEqual(monitor.status.monitored_specs, {"0B12", "0B15"})

    def test_default_initialization(self):
        """Test RealtimeMonitor with default values."""
        monitor = RealtimeMonitor(database=self.mock_db)

        self.assertEqual(monitor.data_specs, ["0B12"])
        self.assertEqual(monitor.sid, "JLTSQL")
        self.assertEqual(monitor.batch_size, 100)
        self.assertTrue(monitor.auto_create_tables)

    @patch('src.database.schema.SchemaManager')
    @patch('src.services.realtime_monitor.threading.Thread')
    def test_start(self, mock_thread, mock_schema_mgr):
        """Test starting monitor."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12"]
        )

        # Mock schema manager
        mock_mgr_instance = MagicMock()
        mock_mgr_instance.get_missing_tables.return_value = []
        mock_schema_mgr.return_value = mock_mgr_instance

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = monitor.start()

        self.assertTrue(result)
        self.assertTrue(monitor.status.is_running)
        self.assertIsNotNone(monitor.status.started_at)

        # Verify thread was created and started
        mock_thread.assert_called()
        mock_thread_instance.start.assert_called()

    def test_start_already_running(self):
        """Test starting monitor when already running."""
        monitor = RealtimeMonitor(database=self.mock_db)
        monitor.status.is_running = True

        result = monitor.start()

        self.assertFalse(result)

    @patch('src.services.realtime_monitor.threading.Thread')
    def test_stop(self, mock_thread):
        """Test stopping monitor."""
        monitor = RealtimeMonitor(database=self.mock_db)

        # Simulate running state
        monitor.status.is_running = True
        mock_thread_instance = MagicMock()
        monitor._threads = [mock_thread_instance]

        result = monitor.stop()

        self.assertTrue(result)
        self.assertFalse(monitor.status.is_running)
        self.assertIsNotNone(monitor.status.stopped_at)

        # Verify thread was joined
        mock_thread_instance.join.assert_called()

    def test_stop_not_running(self):
        """Test stopping monitor when not running."""
        monitor = RealtimeMonitor(database=self.mock_db)

        result = monitor.stop()

        self.assertFalse(result)

    def test_get_status(self):
        """Test getting monitor status."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12"]
        )

        status = monitor.get_status()

        self.assertIsInstance(status, dict)
        self.assertFalse(status["is_running"])
        self.assertEqual(status["records_imported"], 0)
        self.assertIn("0B12", status["monitored_specs"])

    @patch('src.services.realtime_monitor.threading.Thread')
    def test_add_data_spec(self, mock_thread):
        """Test adding data spec to running monitor."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12"]
        )
        monitor.status.is_running = True

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = monitor.add_data_spec("0B15")

        self.assertTrue(result)
        self.assertIn("0B15", monitor.status.monitored_specs)

        # Verify thread was created
        mock_thread.assert_called()
        mock_thread_instance.start.assert_called()

    def test_add_data_spec_not_running(self):
        """Test adding data spec when monitor not running."""
        monitor = RealtimeMonitor(database=self.mock_db)

        result = monitor.add_data_spec("0B15")

        self.assertFalse(result)

    def test_add_data_spec_already_monitored(self):
        """Test adding already monitored data spec."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12"]
        )
        monitor.status.is_running = True

        result = monitor.add_data_spec("0B12")

        self.assertFalse(result)

    def test_context_manager(self):
        """Test context manager protocol."""
        with patch.object(RealtimeMonitor, 'start') as mock_start, \
             patch.object(RealtimeMonitor, 'stop') as mock_stop:

            with RealtimeMonitor(database=self.mock_db) as monitor:
                self.assertIsNotNone(monitor)

            mock_start.assert_called_once()
            mock_stop.assert_called_once()

    @patch('src.database.schema.SchemaManager')
    def test_ensure_tables(self, mock_schema_mgr):
        """Test automatic table creation."""
        monitor = RealtimeMonitor(
            database=self.mock_db,
            auto_create_tables=True
        )

        # Mock schema manager
        mock_mgr_instance = MagicMock()
        mock_mgr_instance.get_missing_tables.return_value = ["NL_RA", "NL_SE"]
        mock_schema_mgr.return_value = mock_mgr_instance

        monitor._ensure_tables()

        # Verify tables were created
        mock_mgr_instance.get_missing_tables.assert_called_once()
        mock_mgr_instance.create_all_tables.assert_called_once()

    def test_add_error(self):
        """Test error tracking."""
        monitor = RealtimeMonitor(database=self.mock_db)

        monitor._add_error("0B12", "Test error")

        self.assertEqual(len(monitor.status.errors), 1)
        self.assertEqual(monitor.status.errors[0]["context"], "0B12")
        self.assertEqual(monitor.status.errors[0]["error"], "Test error")

    def test_error_limit(self):
        """Test error list size limit."""
        monitor = RealtimeMonitor(database=self.mock_db)

        # Add 150 errors
        for i in range(150):
            monitor._add_error("test", f"Error {i}")

        # Should keep only last 100
        self.assertEqual(len(monitor.status.errors), 100)
        self.assertEqual(monitor.status.errors[-1]["error"], "Error 149")


if __name__ == "__main__":
    unittest.main()
