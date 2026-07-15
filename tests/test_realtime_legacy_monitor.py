from unittest.mock import MagicMock

import pytest

from src.realtime.monitor import RealtimeMonitor


def _monitor_without_jvlink_initialization():
    monitor = RealtimeMonitor.__new__(RealtimeMonitor)
    monitor.database = MagicMock()
    monitor.jvlink = MagicMock()
    monitor.updater = MagicMock()
    monitor._stats = {
        "started_at": None,
        "last_update": None,
        "records_processed": 0,
        "records_inserted": 0,
        "records_updated": 0,
        "records_deleted": 0,
        "errors": 0,
    }
    return monitor


def test_poll_rolls_back_when_jv_read_raises_after_a_write():
    monitor = _monitor_without_jvlink_initialization()
    monitor.updater.process_record.return_value = {
        "operation": "insert",
        "success": True,
    }
    monitor.jvlink.jv_read.side_effect = [
        (10, b"record", "file"),
        RuntimeError("transport failed"),
    ]

    with pytest.raises(RuntimeError, match="transport failed"):
        monitor._poll_once()

    monitor.database.begin_transaction.assert_called_once_with()
    monitor.database.rollback.assert_called_once_with()
    monitor.database.commit.assert_not_called()
    assert monitor._stats["records_processed"] == 0
    assert monitor._stats["errors"] == 1


def test_poll_after_read_failure_starts_and_commits_a_fresh_transaction():
    monitor = _monitor_without_jvlink_initialization()
    monitor.updater.process_record.return_value = {
        "operation": "insert",
        "success": True,
    }
    monitor.jvlink.jv_read.side_effect = [
        (10, b"record", "file"),
        RuntimeError("transport failed"),
    ]

    with pytest.raises(RuntimeError):
        monitor._poll_once()

    monitor.jvlink.jv_read.side_effect = [(0, None, None)]
    monitor._poll_once()

    assert monitor.database.begin_transaction.call_count == 2
    monitor.database.rollback.assert_called_once_with()
    monitor.database.commit.assert_called_once_with()
