"""Tests for -502 timeout fix in HistoricalFetcher.

Tests:
- _wait_for_download times out after max_wait_seconds (default 300s)
- _wait_for_download retries -502 only max_retries (2) times then raises
- fetch() does NOT retry COM reinit on -502, raises immediately
"""

import time

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.utils.data_source import DataSource


@pytest.fixture
def fetcher():
    """Create a HistoricalFetcher with mocked internals."""
    with patch.object(HistoricalFetcher, '__init__', lambda self: None):
        f = HistoricalFetcher.__new__(HistoricalFetcher)
        f.data_source = DataSource.NAR
        f.show_progress = False
        f.progress_display = None
        f._skip_cleanup = False
        f.jvlink = MagicMock()
        f._service_key = None
        return f


class TestWaitForDownloadTimeout:
    """Test _wait_for_download timeout behavior."""

    def test_timeout_raises_fetcher_error(self, fetcher):
        """_wait_for_download should raise FetcherError when timeout is exceeded."""
        # jv_status always returns positive (download in progress) → triggers timeout
        fetcher.jvlink.jv_status.return_value = 50

        with pytest.raises(FetcherError, match="Download timeout"):
            fetcher._wait_for_download(timeout=1, interval=0.1)

    def test_default_timeout_is_600(self, fetcher):
        """Default timeout should be 600 seconds (10 minutes) for NAR server reliability."""
        import inspect
        sig = inspect.signature(fetcher._wait_for_download)
        assert sig.parameters['timeout'].default == 600

    def test_502_max_retries_is_2(self, fetcher):
        """_wait_for_download should retry -502 only 2 times (reduced from 5)."""
        # Return -502 every time
        fetcher.jvlink.jv_status.return_value = -502

        with pytest.raises(FetcherError, match="status code: -502"):
            fetcher._wait_for_download(timeout=60, interval=0.01)

        # Should be called 3 times total (1 initial + 2 retries)
        assert fetcher.jvlink.jv_status.call_count == 3


class TestFetchNo502ComRetry:
    """Test that fetch() does not retry COM reinit on -502."""

    def test_502_raises_immediately_no_com_reinit(self, fetcher):
        """fetch() should not attempt COM reinit on -502, just raise."""
        fetcher.jvlink.jv_init.return_value = None
        fetcher.jvlink.jv_open.return_value = (0, 10, 5, "20240101000000")
        fetcher.jvlink.is_open.return_value = True
        fetcher.jvlink.jv_close.return_value = None

        # _wait_for_download raises -502 error
        with patch.object(fetcher, '_wait_for_download', side_effect=FetcherError("Download failed with status code: -502")):
            with pytest.raises(FetcherError, match="-502"):
                list(fetcher.fetch("RACE", "20240101", "20240101", option=1))

        # jv_open should be called only once (no COM reinit retry)
        assert fetcher.jvlink.jv_open.call_count == 1
        # reinitialize_com should NOT be called
        fetcher.jvlink.reinitialize_com.assert_not_called()
