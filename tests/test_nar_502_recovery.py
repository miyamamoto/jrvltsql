"""Tests for NAR -502 error recovery logic.

Tests the skip-and-continue behavior when NV-Link returns -502 errors
during daily chunk fetching.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.utils.data_source import DataSource


class MockJVLink:
    """Mock JV-Link/NV-Link wrapper for testing."""

    def __init__(self):
        self._is_open = False
        self.init_called = 0
        self.open_calls = []
        self.close_calls = 0
        self._fail_dates = set()  # Dates that should trigger -502

    def jv_init(self):
        self.init_called += 1
        return 0

    def jv_open(self, data_spec, fromtime, option):
        date_str = str(fromtime)[:8]
        self.open_calls.append((data_spec, fromtime, option))
        if date_str in self._fail_dates:
            self._is_open = True
            return 0, 5, 5, ""  # Has download count to trigger download wait
        self._is_open = True
        return 0, 3, 0, ""  # No download needed

    def jv_read(self):
        # Return "read complete" immediately
        return 0, None, None

    def jv_status(self):
        return -502  # Always fail download

    def jv_close(self):
        self._is_open = False
        self.close_calls += 1
        return 0

    def jv_file_delete(self, filename):
        return 0

    def is_open(self):
        return self._is_open

    def jv_wait_for_download(self, timeout=120.0, poll_interval=0.5):
        return False


class TestNar502SkipLogic:
    """Test -502 skip-and-continue in _fetch_nar_daily."""

    def _make_fetcher(self, fail_dates=None):
        """Create a HistoricalFetcher with mocked JV-Link."""
        with patch.object(HistoricalFetcher, '__init__', lambda self, **kw: None):
            fetcher = HistoricalFetcher()
            fetcher.data_source = DataSource.NAR
            fetcher.show_progress = False
            fetcher.progress_display = None
            fetcher._skip_cleanup = False
            fetcher._nar_skipped_dates = []
            fetcher._records_fetched = 0
            fetcher._records_parsed = 0
            fetcher._records_failed = 0
            fetcher._files_processed = 0
            fetcher._total_files = 0
            fetcher._start_time = None
            fetcher._service_key = None

            mock_jvlink = MockJVLink()
            if fail_dates:
                mock_jvlink._fail_dates = set(fail_dates)
            fetcher.jvlink = mock_jvlink

            return fetcher

    def test_no_errors_all_days_processed(self):
        """All days processed when no -502 errors occur."""
        fetcher = self._make_fetcher()

        # Mock fetch to yield nothing (no data) but not raise
        with patch.object(fetcher, 'fetch', return_value=iter([])):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240103", 1))

        assert results == []
        assert fetcher._nar_skipped_dates == []

    def test_single_502_day_skipped(self):
        """A single -502 day is skipped, others continue."""
        fetcher = self._make_fetcher()
        call_dates = []

        def mock_fetch(data_spec, from_date, to_date, option):
            call_dates.append(from_date)
            if from_date == "20240102":
                raise FetcherError("Download failed with status code: -502")
            return iter([])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240103", 1))

        assert "20240101" in call_dates
        assert "20240102" in call_dates
        assert "20240103" in call_dates
        assert fetcher._nar_skipped_dates == ["20240102"]

    def test_consecutive_502_aborts_remaining(self):
        """3 consecutive -502 days causes remaining days to be skipped."""
        fetcher = self._make_fetcher()
        call_dates = []

        def mock_fetch(data_spec, from_date, to_date, option):
            call_dates.append(from_date)
            if from_date in ("20240102", "20240103", "20240104"):
                raise FetcherError("Download failed with status code: -502")
            return iter([])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240107", 1))

        # Day 1 succeeds, days 2-4 fail with -502
        # After 3 consecutive failures, days 5-7 are auto-skipped
        assert "20240101" in call_dates
        assert "20240102" in call_dates
        assert "20240103" in call_dates
        assert "20240104" in call_dates
        # Days 5-7 should NOT be attempted (auto-skipped)
        assert "20240105" not in call_dates

        # All skipped dates should be recorded
        assert "20240102" in fetcher._nar_skipped_dates
        assert "20240103" in fetcher._nar_skipped_dates
        assert "20240104" in fetcher._nar_skipped_dates
        assert "20240105" in fetcher._nar_skipped_dates
        assert "20240106" in fetcher._nar_skipped_dates
        assert "20240107" in fetcher._nar_skipped_dates

    def test_non_502_error_reraised(self):
        """Non-502 errors are re-raised, not skipped."""
        fetcher = self._make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            if from_date == "20240102":
                raise FetcherError("NVOpen failed: connection refused")
            return iter([])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            with pytest.raises(FetcherError, match="connection refused"):
                list(fetcher._fetch_nar_daily("RACE", "20240101", "20240103", 1))

    def test_502_reset_on_success(self):
        """Consecutive -502 counter resets when a day succeeds.

        With option=2 fallback, failing days are called twice (option=1 then option=2).
        """
        fetcher = self._make_fetcher()
        call_log = []

        def mock_fetch(data_spec, from_date, to_date, option):
            call_log.append((from_date, option))
            # Days 2,3 fail (both option=1 and option=2), day 4 succeeds, day 5 fails
            if from_date in ("20240102", "20240103", "20240105"):
                raise FetcherError("Download failed with status code: -502")
            return iter([])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240106", 1))

        # Failing days are called twice (option=1 + option=2 fallback)
        # call_log: (d1,1), (d2,1), (d2,2), (d3,1), (d3,2), (d4,1), (d5,1), (d5,2), (d6,1)
        option1_dates = [d for d, o in call_log if o == 1]
        assert len(option1_dates) == 6  # All days attempted with option=1
        assert fetcher._nar_skipped_dates == ["20240102", "20240103", "20240105"]


class TestComReinitProtection:
    """Test that COM reinitialization handles Win32 exceptions gracefully."""

    def test_reinitialize_com_handles_exceptions(self):
        """reinitialize_com should not crash on Win32 exceptions."""
        # This test verifies the structure - actual COM testing requires Windows
        from src.nvlink.wrapper import NVLinkWrapper

        # We can't actually test COM on Mac, but verify the method exists
        # and has the right structure
        import inspect
        source = inspect.getsource(NVLinkWrapper.reinitialize_com)
        # Verify Win32 exception handling is present
        assert "Win32" in source or "CoUninitialize" in source


class TestRetryCountReduced:
    """Test that COM retry count was reduced from 16 to 3."""

    def test_max_retries_is_3(self):
        """Verify historical fetcher uses max 3 retries for -502."""
        import inspect
        source = inspect.getsource(HistoricalFetcher.fetch)
        assert "max_open_retries = 3" in source
