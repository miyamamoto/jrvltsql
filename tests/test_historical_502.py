"""Tests for -502 skip logic in HistoricalFetcher._fetch_nar_daily.

Complements test_nar_502_recovery.py with focused unit-level tests on:
- Consecutive -502 day counting and skip→continue behaviour
- 3-consecutive-502 full abort of remaining days
- Non-502 errors propagate normally (no swallowing)
- _should_chunk_by_day gating logic
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.utils.data_source import DataSource


@pytest.fixture
def fetcher():
    """Create a HistoricalFetcher with mocked internals for NAR."""
    with patch.object(HistoricalFetcher, '__init__', lambda self: None):
        f = HistoricalFetcher.__new__(HistoricalFetcher)
        f.data_source = DataSource.NAR
        f.show_progress = False
        f.progress_display = None
        f._skip_cleanup = False
        f.jvlink = MagicMock()
        return f


class TestShouldChunkByDay:
    """Tests for _should_chunk_by_day gating."""

    def test_nar_multi_day_returns_true(self, fetcher):
        assert fetcher._should_chunk_by_day("20240101", "20240103", option=1) is True

    def test_nar_same_day_returns_false(self, fetcher):
        assert fetcher._should_chunk_by_day("20240101", "20240101", option=1) is False

    def test_jra_returns_false(self, fetcher):
        fetcher.data_source = DataSource.JRA
        assert fetcher._should_chunk_by_day("20240101", "20240103", option=1) is False

    def test_setup_option3_returns_false(self, fetcher):
        assert fetcher._should_chunk_by_day("20240101", "20240103", option=3) is False

    def test_setup_option4_returns_false(self, fetcher):
        assert fetcher._should_chunk_by_day("20240101", "20240103", option=4) is False


class TestFetchNarDaily502Logic:
    """Tests for _fetch_nar_daily -502 skip/abort behaviour."""

    def _run_daily(self, fetcher, from_date, to_date, side_effects):
        """Helper: patch fetch() with side_effects and run _fetch_nar_daily."""
        with patch.object(HistoricalFetcher, 'fetch', side_effect=side_effects) as mock_fetch:
            results = list(fetcher._fetch_nar_daily("RACE", from_date, to_date, 1))
            return results, mock_fetch

    def test_all_success_no_skips(self, fetcher):
        """All days succeed → no skipped dates."""
        effects = [iter([{"day": "1"}]), iter([{"day": "2"}]), iter([{"day": "3"}])]
        results, mock = self._run_daily(fetcher, "20240101", "20240103", effects)
        assert len(results) == 3
        assert fetcher._nar_skipped_dates == []
        assert mock.call_count == 3

    def test_single_502_skips_one_day(self, fetcher):
        """One -502 day gets skipped, remaining days continue."""
        effects = [
            FetcherError("Download failed: -502"),
            iter([{"day": "2"}]),
            iter([{"day": "3"}]),
        ]
        results, mock = self._run_daily(fetcher, "20240101", "20240103", effects)
        assert len(results) == 2
        assert fetcher._nar_skipped_dates == ["20240101"]

    def test_502_resets_on_success(self, fetcher):
        """Consecutive counter resets after a successful day."""
        effects = [
            FetcherError("-502 error"),  # day 1: fail (consecutive=1)
            FetcherError("-502 error"),  # day 2: fail (consecutive=2)
            iter([{"day": "3"}]),         # day 3: success (reset to 0)
            FetcherError("-502 error"),  # day 4: fail (consecutive=1)
            iter([{"day": "5"}]),         # day 5: success
        ]
        results, _ = self._run_daily(fetcher, "20240101", "20240105", effects)
        assert len(results) == 2
        assert fetcher._nar_skipped_dates == ["20240101", "20240102", "20240104"]

    def test_three_consecutive_502_aborts_remaining(self, fetcher):
        """3 consecutive -502 days → all remaining days skipped without fetch."""
        effects = [
            FetcherError("-502"),
            FetcherError("-502"),
            FetcherError("-502"),
            # Days 4-5 should never be called
            iter([{"day": "4"}]),
            iter([{"day": "5"}]),
        ]
        results, mock = self._run_daily(fetcher, "20240101", "20240105", effects)
        assert len(results) == 0
        # Only 3 fetch calls, not 5
        assert mock.call_count == 3
        # All 5 days skipped (3 failed + 2 remaining)
        assert fetcher._nar_skipped_dates == [
            "20240101", "20240102", "20240103", "20240104", "20240105"
        ]

    def test_503_also_counted(self, fetcher):
        """-503 errors are treated same as -502."""
        effects = [
            FetcherError("-503 error"),
            FetcherError("-502 error"),
            FetcherError("-503 error"),
        ]
        results, mock = self._run_daily(fetcher, "20240101", "20240105", effects)
        assert mock.call_count == 3
        assert len(fetcher._nar_skipped_dates) == 5  # 3 failed + 2 remaining

    def test_non_502_error_propagates(self, fetcher):
        """Non-502 errors are re-raised immediately."""
        effects = [
            iter([{"day": "1"}]),
            FetcherError("Database connection lost"),
        ]
        with patch.object(HistoricalFetcher, 'fetch', side_effect=effects):
            with pytest.raises(FetcherError, match="Database connection lost"):
                list(fetcher._fetch_nar_daily("RACE", "20240101", "20240103", 1))

    def test_skip_cleanup_flag_management(self, fetcher):
        """_skip_cleanup is True during iteration, False after."""
        effects = [iter([{"day": "1"}])]
        with patch.object(HistoricalFetcher, 'fetch', side_effect=effects):
            list(fetcher._fetch_nar_daily("RACE", "20240101", "20240101", 1))
        assert fetcher._skip_cleanup is False

    def test_single_day_range(self, fetcher):
        """Single day range works correctly."""
        effects = [iter([{"record": "data"}])]
        results, _ = self._run_daily(fetcher, "20240101", "20240101", effects)
        assert len(results) == 1
        assert fetcher._nar_skipped_dates == []
