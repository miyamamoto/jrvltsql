"""Tests for NAR (NV-Link) data fetch stability improvements.

Issue #64: NAR data fetching fails with -502, COM E_UNEXPECTED, and -421 errors.
These tests verify the fixes based on kmy-keiba reference implementation analysis.
"""

import gc
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.fetcher.base import FetcherError
from src.utils.data_source import DataSource


class TestDownloadPollingInterval:
    """Verify download polling uses 80ms interval (matching kmy-keiba)."""

    def test_wait_for_download_default_interval(self):
        """Default polling interval should be 80ms (kmy-keiba: Task.Delay(80))."""
        from src.fetcher.historical import HistoricalFetcher
        import inspect

        sig = inspect.signature(HistoricalFetcher._wait_for_download)
        assert sig.parameters['interval'].default == 0.08


class TestDownloadStallDetection:
    """Verify download stall detection (kmy-keiba: 60s stall timeout)."""

    @patch('src.fetcher.historical.HistoricalFetcher.__init__', return_value=None)
    def test_stall_raises_fetcher_error(self, mock_init):
        """Download stall (no progress for 60s) should raise FetcherError."""
        from src.fetcher.historical import HistoricalFetcher

        fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
        fetcher.jvlink = MagicMock()
        fetcher.progress_display = None
        fetcher.data_source = DataSource.NAR

        # Simulate: status goes to 50% and stays there
        call_count = 0
        def mock_status():
            nonlocal call_count
            call_count += 1
            return 5000  # 50%

        fetcher.jvlink.jv_status = mock_status

        # Patch time to simulate 61 seconds passing after initial change
        real_time = time.time
        start = real_time()
        with patch('src.fetcher.historical.time') as mock_time:
            # First call: start_time
            # Subsequent calls: advance past stall_timeout
            call_times = iter([
                start,       # start_time
                start,       # first elapsed check
                start + 0.1, # first status check (status changes to 5000)
                start + 0.1, # last_progress_time update
                start + 61,  # next iteration - elapsed check
                start + 61,  # stall check - exceeds 60s
                start + 61,  # stall_elapsed calculation
            ])
            mock_time.time = lambda: next(call_times, start + 100)
            mock_time.sleep = MagicMock()

            with pytest.raises(FetcherError, match="stalled"):
                fetcher._wait_for_download()


class TestGCBeforeNVClose:
    """Verify GC.collect() is called before NVClose (kmy-keiba pattern)."""

    def test_nv_close_calls_gc_collect(self):
        """nv_close should call gc.collect() before closing."""
        with patch('gc.collect') as mock_gc_collect:
            # Create a mock NVLink wrapper without COM
            with patch('src.nvlink.wrapper.NVLinkWrapper.__init__', return_value=None):
                from src.nvlink.wrapper import NVLinkWrapper
                wrapper = NVLinkWrapper.__new__(NVLinkWrapper)
                wrapper._nvlink = MagicMock()
                wrapper._nvlink.NVClose.return_value = 0
                wrapper._is_open = True

                wrapper.nv_close()

                mock_gc_collect.assert_called()
                wrapper._nvlink.NVClose.assert_called_once()


class TestPeriodicGCInReadLoop:
    """Verify periodic GC during read loop to prevent COM buffer buildup."""

    def test_gc_collect_called_during_long_read(self):
        """GC should be triggered periodically during read loop."""
        from src.fetcher.base import BaseFetcher

        # Create a concrete subclass for testing
        class TestFetcher(BaseFetcher):
            def fetch(self, **kwargs):
                pass

        with patch.object(BaseFetcher, '__init__', return_value=None):
            fetcher = TestFetcher.__new__(TestFetcher)
            fetcher.jvlink = MagicMock()
            fetcher.parser_factory = MagicMock()
            fetcher.progress_display = None
            fetcher._records_fetched = 0
            fetcher._records_parsed = 0
            fetcher._records_failed = 0
            fetcher._files_processed = 0
            fetcher._total_files = 10
            fetcher.data_source = DataSource.NAR

            # Return 3 records then EOF
            fetcher.jvlink.jv_read.side_effect = [
                (100, b"RA" + b"\x00" * 98, "file1.dat"),
                (100, b"RA" + b"\x00" * 98, "file1.dat"),
                (100, b"RA" + b"\x00" * 98, "file1.dat"),
                (0, None, None),  # EOF
            ]

            fetcher.parser_factory.parse.return_value = {"test": "data"}

            # Consume the generator
            real_time = time.time
            start = real_time()
            with patch('src.fetcher.base.time') as mock_time, \
                 patch('src.fetcher.base.gc') as mock_gc:
                # Simulate 15 seconds passing (should trigger GC at 10s)
                times = iter([start, start, start + 11, start + 11, start + 11,
                             start + 11, start + 11, start + 11,
                             start + 15, start + 15, start + 15, start + 15,
                             start + 15, start + 15, start + 15, start + 15,
                             start + 20, start + 20, start + 20, start + 20])
                mock_time.time = lambda: next(times, start + 30)
                mock_time.sleep = MagicMock()

                list(fetcher._fetch_and_parse())

                # GC should have been called at least once
                assert mock_gc.collect.call_count >= 1


class TestPostDownloadWait:
    """Verify post-download wait is minimal (kmy-keiba: no wait)."""

    def test_post_download_wait_is_minimal(self):
        """Post-download file-write wait should be 0.5s (reduced from 2s)."""
        from src.fetcher.historical import HistoricalFetcher
        import inspect

        # Read the source to check the wait_time value
        source = inspect.getsource(HistoricalFetcher._wait_for_download)
        assert "wait_time = 0.5" in source


class TestInterDayDelay:
    """Verify inter-day delay is reasonable."""

    def test_inter_day_delay_is_1_second(self):
        """Inter-day delay should be 1.0s (reduced from 2.0s)."""
        from src.fetcher.historical import HistoricalFetcher
        import inspect

        source = inspect.getsource(HistoricalFetcher._fetch_nar_daily)
        assert "delay = 1.0" in source
