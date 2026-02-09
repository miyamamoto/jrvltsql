"""Tests for COM E_UNEXPECTED (-2147418113) recovery.

Verifies that:
1. NVRead raises COMBrokenError on E_UNEXPECTED
2. _fetch_and_parse propagates COMBrokenError (not swallowed as FetcherError)
3. _fetch_nar_daily retries the day after COM recovery
4. Skips the day if retry also fails
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.nvlink.wrapper import COMBrokenError, NVLinkError, NVLinkWrapper


class TestCOMBrokenError:
    """Test COMBrokenError exception class."""

    def test_is_nvlink_error_subclass(self):
        err = COMBrokenError()
        assert isinstance(err, NVLinkError)

    def test_default_message(self):
        err = COMBrokenError()
        assert "E_UNEXPECTED" in str(err)

    def test_custom_message(self):
        err = COMBrokenError("custom msg")
        assert "custom msg" in str(err)

    def test_error_code(self):
        err = COMBrokenError()
        assert err.error_code == -2147418113


class TestNVReadCOMBroken:
    """Test that nv_read raises COMBrokenError on E_UNEXPECTED."""

    def _make_wrapper(self):
        """Create a NVLinkWrapper with mocked COM."""
        with patch("src.nvlink.wrapper.NVLinkWrapper.__init__", lambda self, **kw: None):
            w = NVLinkWrapper.__new__(NVLinkWrapper)
            w.sid = "TEST"
            w.initialization_key = None
            w._nvlink = MagicMock()
            w._is_open = True
            w._com_initialized = False
            return w

    def test_raises_com_broken_on_e_unexpected(self):
        w = self._make_wrapper()
        # Simulate COM raising E_UNEXPECTED
        w._nvlink.NVRead.side_effect = Exception(
            "(-2147418113, 'Unexpected failure', None, None)"
        )
        with pytest.raises(COMBrokenError):
            w.nv_read()
        assert w._is_open is False

    def test_raises_com_broken_on_e_unexpected_text(self):
        w = self._make_wrapper()
        w._nvlink.NVRead.side_effect = Exception("E_UNEXPECTED error occurred")
        with pytest.raises(COMBrokenError):
            w.nv_read()

    def test_normal_error_still_raises_nvlink_error(self):
        w = self._make_wrapper()
        w._nvlink.NVRead.side_effect = Exception("some other COM error")
        with pytest.raises(NVLinkError, match="NVRead failed"):
            w.nv_read()

    def test_normal_read_works(self):
        w = self._make_wrapper()
        # Simulate successful read: (data_length, buff_str, size, filename)
        w._nvlink.NVRead.return_value = (100, "A" * 100, 100, "test.dat")
        ret_code, data, fname = w.nv_read()
        assert ret_code == 100
        assert data is not None
        assert fname == "test.dat"


class TestFetchAndParsePropagatesCOMBroken:
    """Test that _fetch_and_parse lets COMBrokenError propagate."""

    def test_com_broken_not_wrapped_in_fetcher_error(self):
        """COMBrokenError should NOT be caught and wrapped as FetcherError."""
        from src.fetcher.base import BaseFetcher, FetcherError

        # Create a minimal concrete subclass
        class DummyFetcher(BaseFetcher):
            def fetch(self, *a, **kw):
                yield from self._fetch_and_parse()

        mock_jvlink = MagicMock()
        mock_jvlink.jv_read.side_effect = COMBrokenError("test")

        fetcher = DummyFetcher.__new__(DummyFetcher)
        fetcher.jvlink = mock_jvlink
        fetcher.parser_factory = MagicMock()
        fetcher.progress_display = None
        fetcher.show_progress = False
        fetcher._records_fetched = 0
        fetcher._records_parsed = 0
        fetcher._records_failed = 0
        fetcher._files_processed = 0
        fetcher._total_files = 0
        fetcher._start_time = 0

        with pytest.raises(COMBrokenError):
            list(fetcher._fetch_and_parse())


class TestFetchNARDailyRetry:
    """Test _fetch_nar_daily retries on COMBrokenError."""

    def _make_fetcher(self):
        from src.fetcher.historical import HistoricalFetcher
        from src.utils.data_source import DataSource

        fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
        fetcher.jvlink = MagicMock()
        fetcher.jvlink.jv_close = MagicMock()
        fetcher.jvlink.jv_init = MagicMock()
        fetcher.jvlink.reinitialize_com = MagicMock()
        fetcher.parser_factory = MagicMock()
        fetcher.progress_display = None
        fetcher.show_progress = False
        fetcher.data_source = DataSource.NAR
        fetcher._skip_cleanup = False
        fetcher._service_key = None
        return fetcher

    def test_retry_succeeds_after_com_broken(self):
        """Day should be retried after COM recovery and succeed."""
        fetcher = self._make_fetcher()

        call_count = 0
        def mock_fetch(ds, from_d, to_d, opt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise COMBrokenError("broken")
            # Second call succeeds
            return iter([{"id": 1}])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240101", 1))

        assert len(results) == 1
        assert results[0]["id"] == 1
        fetcher.jvlink.reinitialize_com.assert_called_once()

    def test_skip_day_if_retry_also_fails(self):
        """Day should be skipped if retry also raises COMBrokenError."""
        fetcher = self._make_fetcher()

        def mock_fetch(ds, from_d, to_d, opt):
            raise COMBrokenError("broken again")

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240101", 1))

        assert results == []
        assert fetcher._nar_skipped_dates == ["20240101"]

    def test_multi_day_continues_after_com_broken(self):
        """Other days should still be processed after one day's COM failure."""
        fetcher = self._make_fetcher()

        call_count = 0
        def mock_fetch(ds, from_d, to_d, opt):
            nonlocal call_count
            call_count += 1
            # Day 1 (20240101): always fails
            if to_d == "20240101":
                raise COMBrokenError("broken")
            # Day 2 (20240102): succeeds
            return iter([{"date": to_d}])

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240102", 1))

        # Day 2 should have data
        assert len(results) == 1
        assert results[0]["date"] == "20240102"
        # Day 1 should be skipped
        assert "20240101" in fetcher._nar_skipped_dates
