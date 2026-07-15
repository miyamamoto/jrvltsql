#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for realtime data fetching and monitoring."""

import unittest
from unittest.mock import Mock, MagicMock, patch, call, ANY
import threading
import time

from src.fetcher.realtime import RealtimeFetcher
from src.services.realtime_monitor import RealtimeMonitor, MonitorStatus
from src.realtime.updater import RealtimeUpdater, summarize_update_result
from src.jvlink.constants import (
    JV_RT_SUCCESS,
    JV_READ_SUCCESS,
    DATA_KUBUN_NEW,
    DATA_KUBUN_UPDATE,
    DATA_KUBUN_DELETE,
    DATA_KUBUN_ERASE,
)


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
        mock_jvlink.jv_rt_open.assert_called_once_with("0B12", ANY)
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


def test_summarize_update_result_counts_explicit_failures():
    successful, failed = summarize_update_result(
        [
            {"operation": "insert", "success": True},
            {"operation": "insert", "success": False},
        ]
    )

    assert len(successful) == 1
    assert failed == 1
    assert summarize_update_result(None) == ([], 1)


def test_process_parsed_record_preserves_failed_expanded_rows():
    updater = RealtimeUpdater(MagicMock())
    successful = {"operation": "insert", "success": True}
    updater._process_single_record = MagicMock(side_effect=[successful, None])

    result = updater.process_parsed_record(
        [{"RecordSpec": "RA"}, {"RecordSpec": "SE"}]
    )

    assert result == [successful, None]
    accepted, failed = summarize_update_result(result)
    assert accepted == [successful]
    assert failed == 1


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
        mock_mgr_instance.create_all_tables.return_value = {}
        mock_schema_mgr.return_value = mock_mgr_instance

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        result = monitor.start()

        self.assertTrue(result)
        self.assertTrue(monitor.status.is_running)
        self.assertIsNotNone(monitor.status.started_at)

        # Verify thread was created and started
        mock_mgr_instance.create_all_tables.assert_called_once()
        mock_thread.assert_called()
        mock_thread_instance.start.assert_called()

    def test_start_already_running(self):
        """Test starting monitor when already running."""
        monitor = RealtimeMonitor(database=self.mock_db)
        monitor.status.is_running = True

        result = monitor.start()

        self.assertFalse(result)

    def test_stop(self):
        """Test stopping monitor."""
        monitor = RealtimeMonitor(database=self.mock_db)

        # Simulate running state with a single monitoring thread
        monitor.status.is_running = True
        mock_thread_instance = MagicMock()
        mock_thread_instance.is_alive.return_value = True
        monitor._thread = mock_thread_instance

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

    def test_add_data_spec(self):
        """Test adding data spec to running monitor.

        The sequential monitor shares one thread, so add_data_spec only
        updates the spec list — no new thread is created.
        """
        monitor = RealtimeMonitor(
            database=self.mock_db,
            data_specs=["0B12"]
        )
        monitor.status.is_running = True

        result = monitor.add_data_spec("0B15")

        self.assertTrue(result)
        self.assertIn("0B15", monitor.status.monitored_specs)
        self.assertIn("0B15", monitor.data_specs)

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
        mock_mgr_instance.create_all_tables.return_value = {
            "NL_RA": True,
            "NL_SE": True,
        }
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

    def test_drain_key_reports_rejected_operations_to_cycle(self):
        monitor = RealtimeMonitor(database=self.mock_db)
        jvlink = MagicMock()
        jvlink.jv_rt_open.return_value = (0, 1)
        jvlink.jv_read.side_effect = [
            (100, b"record", "RT"),
            (0, None, None),
        ]
        updater = MagicMock()
        updater.process_record.return_value = [
            {"operation": "insert", "success": True},
            None,
        ]

        imported, failed = monitor._drain_key(
            jvlink, updater, "0B12", "20260715"
        )

        self.assertEqual((imported, failed), (1, 1))
        self.assertEqual(monitor.status.records_imported, 0)
        self.assertEqual(monitor.status.records_failed, 0)

    def test_today_race_keys_uses_parameterized_query(self):
        monitor = RealtimeMonitor(database=self.mock_db)
        self.mock_db.fetch_all.return_value = [{"JyoCD": "05", "RaceNum": 3}]

        keys = monitor._get_today_race_keys("20260715")

        self.assertEqual(keys, ["202607150503"])
        self.mock_db.fetch_all.assert_called_once_with(
            "SELECT JyoCD, RaceNum FROM NL_RA "
            "WHERE Year=? AND MonthDay=? "
            "ORDER BY JyoCD, RaceNum",
            ("2026", "0715"),
        )

    def test_today_race_keys_propagates_database_failure(self):
        monitor = RealtimeMonitor(database=self.mock_db)
        self.mock_db.fetch_all.side_effect = RuntimeError("query failed")

        with self.assertRaisesRegex(RuntimeError, "query failed"):
            monitor._get_today_race_keys("20260715")

    @patch("src.services.realtime_monitor.RealtimeFetcher")
    def test_begin_failure_is_accounted_and_monitor_becomes_unhealthy(self, fetcher_cls):
        monitor = RealtimeMonitor(database=self.mock_db, data_specs=["0B12"])
        monitor.status.is_running = True
        self.mock_db.begin_transaction.side_effect = RuntimeError("begin failed")
        monitor._stop_event = MagicMock()
        monitor._stop_event.is_set.side_effect = [False, True]
        fetcher_cls.return_value.jvlink = MagicMock()

        monitor._monitor_sequential()

        self.mock_db.rollback.assert_called_once_with()
        self.assertEqual(monitor.status.records_failed, 1)
        self.assertFalse(monitor.status.is_running)
        self.assertIsNotNone(monitor.status.stopped_at)

    def test_error_limit(self):
        """Test error list size limit."""
        monitor = RealtimeMonitor(database=self.mock_db)

        # Add 150 errors
        for i in range(150):
            monitor._add_error("test", f"Error {i}")

        # Should keep only last 100
        self.assertEqual(len(monitor.status.errors), 100)
        self.assertEqual(monitor.status.errors[-1]["error"], "Error 149")


class TestRealtimeUpdater(unittest.TestCase):
    """Test RealtimeUpdater class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.updater = RealtimeUpdater(self.mock_db)

    def test_initialization(self):
        """Test RealtimeUpdater initialization."""
        self.assertEqual(self.updater.database, self.mock_db)
        self.assertIsNotNone(self.updater.parser_factory)

    def test_record_type_table_mapping(self):
        """Test RECORD_TYPE_TABLE mapping includes all expected types."""
        expected_mappings = {
            # Speed Report (0B1x)
            "WE": "RT_WE",  # Kaisai info
            "RA": "RT_RA",  # Race detail
            "SE": "RT_SE",  # Horse race info
            "DM": "RT_DM",  # Data mining (time type)
            "AV": "RT_AV",  # Scratched/excluded horse
            "HR": "RT_HR",  # Payout
            "WH": "RT_WH",  # Horse weight
            "TM": "RT_TM",  # Data mining (match type)
            "WF": "RT_WF",  # WIN5
            # Time Series (0B2x-0B3x)
            "H1": "RT_H1",  # Vote count
            "H6": "RT_H6",  # Vote count (3rentan)
            "O1": "RT_O1",  # Odds (win/place/bracket quinella)
            "O2": "RT_O2",  # Odds (quinella)
            "O3": "RT_O3",  # Odds (wide)
            "O4": "RT_O4",  # Odds (exacta)
            "O5": "RT_O5",  # Odds (trio)
            "O6": "RT_O6",  # Odds (trifecta)
            # Results
            "JC": "RT_JC",  # Jockey results
            "TC": "RT_TC",  # Trainer results
            "CC": "RT_CC",  # Horse results
            # Change info (0B4x)
            "RC": "RT_RC",  # Jockey change info
        }

        for record_type, expected_table in expected_mappings.items():
            self.assertEqual(
                self.updater.RECORD_TYPE_TABLE.get(record_type),
                expected_table,
                f"Mapping mismatch for {record_type}",
            )

    def test_timeseries_table_routing_separates_official_and_sokuho(self):
        """Official 0B41/0B42 and速報 0B30-0B36 use different tables."""
        self.assertEqual(
            self.updater._resolve_timeseries_table({"RecordSpec": "O1", "SourceSpec": "0B41"}),
            "TS_O1",
        )
        self.assertEqual(
            self.updater._resolve_timeseries_table({"RecordSpec": "O2", "SourceSpec": "0B42"}),
            "TS_O2",
        )
        self.assertEqual(
            self.updater._resolve_timeseries_table({"RecordSpec": "O1", "SourceSpec": "0B30"}),
            "TS_SOKUHO_O1",
        )
        self.assertEqual(
            self.updater._resolve_timeseries_table({"RecordSpec": "O6", "SourceSpec": "0B36"}),
            "TS_SOKUHO_O6",
        )

    def test_process_parsed_records_batch_keeps_source_spec_for_sokuho_only(self):
        """SourceSpec is persisted for速報 tables and stripped from official TS tables."""
        records = [
            {
                "RecordSpec": "O1",
                "SourceSpec": "0B41",
                "Year": 2026,
                "MonthDay": 503,
                "JyoCD": "05",
                "Kaiji": 1,
                "Nichiji": 2,
                "RaceNum": 11,
                "HassoTime": "1540",
                "Umaban": 1,
                "Kumi": "00",
            },
            {
                "RecordSpec": "O1",
                "SourceSpec": "0B30",
                "Year": 2026,
                "MonthDay": 503,
                "JyoCD": "05",
                "Kaiji": 1,
                "Nichiji": 2,
                "RaceNum": 11,
                "HassoTime": "1540",
                "Umaban": 1,
                "Kumi": "00",
            },
        ]

        result = self.updater.process_parsed_records_batch(records, timeseries=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["inserted"], 2)
        self.assertEqual(result["tables"], ["TS_O1", "TS_SOKUHO_O1"])

        inserted_by_table = {
            call.args[0]: call.args[1]
            for call in self.mock_db.insert_many.call_args_list
        }
        self.assertNotIn("SourceSpec", inserted_by_table["TS_O1"][0])
        self.assertIn("CollectedAt", inserted_by_table["TS_O1"][0])
        self.assertEqual(inserted_by_table["TS_SOKUHO_O1"][0]["SourceSpec"], "0B30")
        self.assertIn("CollectedAt", inserted_by_table["TS_SOKUHO_O1"][0])

    def test_ts_o1_primary_key_fields_are_not_blank(self):
        """O1 horse rows keep a non-null Kumi sentinel for PostgreSQL keys."""
        data = self.updater._prepare_data_for_db(
            "TS_O1",
            {
                "RecordSpec": "O1",
                "Year": "2026",
                "MonthDay": "0503",
                "JyoCD": "05",
                "Kaiji": "1",
                "Nichiji": "2",
                "RaceNum": "1",
                "HassoTime": "1540",
                "Umaban": "01",
                "Kumi": "",
            },
        )

        self.assertEqual(data["Umaban"], 1)
        self.assertEqual(data["Kumi"], "00")

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_new(self, mock_factory_class):
        """Test processing new record (headDataKubun=1)."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RA",
            "headDataKubun": DATA_KUBUN_NEW,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "01",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "01",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RA20240101...")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "insert")
        self.assertEqual(result["table"], "RT_RA")
        self.assertTrue(result["success"])

        # Verify database insert was called
        self.mock_db.insert.assert_called_once()

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_update(self, mock_factory_class):
        """Test processing update record (headDataKubun=2)."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "SE",
            "headDataKubun": DATA_KUBUN_UPDATE,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "01",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "01",
            "Umaban": "1",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("SE20240101...")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "update")
        self.assertEqual(result["table"], "RT_SE")
        self.assertTrue(result["success"])

        # Verify database insert was called (update uses insert for now)
        self.mock_db.insert.assert_called_once()

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_delete(self, mock_factory_class):
        """Test processing delete record (headDataKubun=9)."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RA",
            "headDataKubun": DATA_KUBUN_DELETE,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "01",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "01",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RA20240101...")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["table"], "RT_RA")
        self.assertTrue(result["success"])

        # Verify database execute was called for DELETE
        self.mock_db.execute.assert_called_once()
        call_args = self.mock_db.execute.call_args
        self.assertIn("DELETE FROM RT_RA", call_args[0][0])

    def test_record_data_kubun_zero_physically_deletes(self):
        updater = RealtimeUpdater(self.mock_db)

        result = updater.process_parsed_record(
            {
                "RecordSpec": "RA",
                "DataKubun": DATA_KUBUN_ERASE,
                "Year": "2026",
                "MonthDay": "0715",
                "JyoCD": "05",
                "Kaiji": "2",
                "Nichiji": "3",
                "RaceNum": "1",
            }
        )

        self.assertEqual(result["operation"], "delete")
        self.assertTrue(result["success"])
        self.mock_db.execute.assert_called_once()
        sql, parameters = self.mock_db.execute.call_args.args
        self.assertIn("DELETE FROM RT_RA", sql)
        self.assertEqual(parameters, (2026, 715, "05", 2, 3, 1))

    def test_drain_0b14_replaces_date_snapshot_before_import(self):
        monitor = RealtimeMonitor(database=self.mock_db)
        jvlink = MagicMock()
        jvlink.jv_rt_open.return_value = (0, 0)
        jvlink.jv_read.return_value = (0, None, None)
        updater = MagicMock()

        imported, failed = monitor._drain_key(
            jvlink, updater, "0B14", "20260715"
        )

        self.assertEqual((imported, failed), (0, 0))
        updater.replace_date_snapshot.assert_called_once_with("20260715")

    def test_drain_0b14_interruption_rejects_partial_snapshot(self):
        monitor = RealtimeMonitor(database=self.mock_db)
        jvlink = MagicMock()
        jvlink.jv_rt_open.return_value = (0, 1)

        def stop_during_read():
            monitor._stop_event.set()
            return (100, b"record", "RT")

        jvlink.jv_read.side_effect = stop_during_read
        updater = MagicMock()
        updater.process_record.return_value = {
            "operation": "insert",
            "success": True,
        }

        imported, failed = monitor._drain_key(
            jvlink, updater, "0B14", "20260715"
        )

        self.assertEqual(imported, 1)
        self.assertEqual(failed, 1)
        updater.replace_date_snapshot.assert_called_once_with("20260715")

    def test_drain_0b14_busy_after_clear_rejects_snapshot(self):
        from src.jvlink.wrapper import JVLinkError

        monitor = RealtimeMonitor(database=self.mock_db)
        jvlink = MagicMock()
        jvlink.jv_rt_open.return_value = (0, 1)
        jvlink.jv_read.side_effect = JVLinkError("busy", error_code=-202)
        updater = MagicMock()

        imported, failed = monitor._drain_key(
            jvlink, updater, "0B14", "20260715"
        )

        self.assertEqual((imported, failed), (0, 1))
        updater.replace_date_snapshot.assert_called_once_with("20260715")

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_rc_mapping(self, mock_factory_class):
        """Test RC record type maps to RT_RC table."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RC",
            "headDataKubun": DATA_KUBUN_NEW,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "01",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "01",
            "Umaban": "1",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RC20240101...")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["table"], "RT_RC")
        self.assertTrue(result["success"])

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_unknown_type(self, mock_factory_class):
        """Test processing record with unknown type returns None."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "XX",  # Unknown type
            "headDataKubun": DATA_KUBUN_NEW,
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("XX20240101...")

        # Verify result is None
        self.assertIsNone(result)

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_parse_failure(self, mock_factory_class):
        """Test processing record when parsing fails."""
        # Setup mock parser to return None
        mock_parser = MagicMock()
        mock_parser.parse.return_value = None
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("INVALID...")

        # Verify result is None
        self.assertIsNone(result)

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_missing_record_spec(self, mock_factory_class):
        """Test processing record without RecordSpec."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "headDataKubun": DATA_KUBUN_NEW,
            # Missing RecordSpec
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RA20240101...")

        # Verify result is None
        self.assertIsNone(result)

    @patch('src.realtime.updater.ParserFactory')
    def test_process_record_delete_missing_primary_key_values(self, mock_factory_class):
        """Test deleting record fails when primary key values are incomplete."""
        # Setup mock parser for DM with an incomplete primary key.
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "DM",
            "headDataKubun": DATA_KUBUN_DELETE,
            "Year": "2024",
            "MonthDay": "0101",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("DM20240101...")

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "delete")
        self.assertEqual(result["table"], "RT_DM")
        self.assertFalse(result["success"])
        self.assertIn("Missing primary key values", result["error"])
        self.mock_db.execute.assert_not_called()

    def test_get_primary_keys(self):
        """Test _get_primary_keys returns correct primary keys."""
        # Test tables with primary keys
        self.assertEqual(
            self.updater._get_primary_keys("RT_RA"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_SE"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_RC"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_O1"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban", "Kumi"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_H1"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "BetType", "Kumi"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_H6"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "SanrentanKumi"],
        )

        # Test tables with primary keys (weather/track)
        self.assertEqual(
            self.updater._get_primary_keys("RT_WH"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "HappyoTime", "HenkoID"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_WE"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "HenkoID"],
        )
        self.assertEqual(
            self.updater._get_primary_keys("TS_SOKUHO_O2"),
            [
                "Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji",
                "RaceNum", "Kumi", "HassoTime", "SourceSpec", "CollectedAt",
            ],
        )
        self.assertEqual(
            self.updater._get_primary_keys("RT_DM"),
            ["Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum", "Umaban"],
        )

        # Test unknown table
        self.assertEqual(self.updater._get_primary_keys("UNKNOWN_TABLE"), [])

    def test_realtime_primary_keys_match_schema(self):
        """Realtime updater primary-key map should stay aligned with schema.py."""
        import re

        from src.database.schema import SCHEMAS

        for table_name, ddl in SCHEMAS.items():
            if not table_name.startswith(("RT_", "TS_")):
                continue
            match = re.search(r"PRIMARY KEY \(([^)]*)\)", ddl)
            schema_pk = [column.strip() for column in match.group(1).split(",")] if match else []
            self.assertEqual(
                self.updater._get_primary_keys(table_name),
                schema_pk,
                f"Primary key mismatch for {table_name}",
            )

    @patch('src.realtime.updater.ParserFactory')
    def test_handle_new_record_removes_metadata(self, mock_factory_class):
        """Test that metadata fields (starting with _) are removed."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RA",
            "headDataKubun": DATA_KUBUN_NEW,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "05",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "1",
            "_metadata": "should be removed",
            "_internal": "also removed",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        updater.process_record("RA20240101...")

        # Verify metadata fields were removed
        call_args = self.mock_db.insert.call_args
        inserted_data = call_args[0][1]
        self.assertNotIn("_metadata", inserted_data)
        self.assertNotIn("_internal", inserted_data)
        self.assertIn("Year", inserted_data)

    @patch('src.realtime.updater.ParserFactory')
    def test_record_data_kubun_is_persisted_not_used_as_delete(self, mock_factory_class):
        """RA DataKubun=9 is a cancelled-race state, not a DELETE command."""
        # Setup mock parser - only DataKubun is present
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RA",
            "DataKubun": DATA_KUBUN_DELETE,
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "05",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "1",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RA20240101...")

        # Record-level status is stored through the normal upsert path.
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "insert")
        self.mock_db.insert.assert_called_once()
        self.mock_db.execute.assert_not_called()

    def test_cancellation_status_is_upserted_for_realtime_state_records(self):
        updater = RealtimeUpdater(self.mock_db)

        for record_type in ("RA", "SE", "WF"):
            with self.subTest(record_type=record_type):
                self.mock_db.reset_mock()
                result = updater.process_parsed_record(
                    {
                        "RecordSpec": record_type,
                        "DataKubun": DATA_KUBUN_DELETE,
                        "Year": "2026",
                        "MonthDay": "0715",
                        "JyoCD": "05",
                        "Kaiji": "1",
                        "Nichiji": "1",
                        "RaceNum": "1",
                        "Umaban": "1",
                    }
                )

                self.assertEqual(result["operation"], "insert")
                self.assertTrue(result["success"])
                self.mock_db.insert.assert_called_once()
                self.mock_db.execute.assert_not_called()

    @patch('src.realtime.updater.ParserFactory')
    def test_head_data_kubun_default_fallback(self, mock_factory_class):
        """Test fallback to default value when both headDataKubun and DataKubun are missing."""
        # Setup mock parser - neither headDataKubun nor DataKubun present
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {
            "RecordSpec": "RA",
            # No headDataKubun or DataKubun - defaults to "1" (NEW)
            "Year": "2024",
            "MonthDay": "0101",
            "JyoCD": "05",
            "Kaiji": "1",
            "Nichiji": "1",
            "RaceNum": "1",
        }
        mock_factory_instance = MagicMock()
        mock_factory_instance.parse = mock_parser.parse
        mock_factory_class.return_value = mock_factory_instance

        # Create updater with mocked factory
        updater = RealtimeUpdater(self.mock_db)
        updater.parser_factory = mock_factory_instance

        # Process record
        result = updater.process_record("RA20240101...")

        # Verify it defaults to NEW (insert)
        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "insert")
        self.mock_db.insert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
