"""Failure accounting for historical cache replay."""

from unittest.mock import MagicMock

from src.fetcher.historical import HistoricalFetcher


def _fetcher_without_jvlink() -> HistoricalFetcher:
    fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
    fetcher.parser_factory = MagicMock()
    fetcher._records_fetched = 0
    fetcher._records_parsed = 0
    fetcher._records_failed = 0
    fetcher._files_processed = 0
    fetcher._total_files = 0
    return fetcher


def test_cache_replay_counts_parser_rejection_as_failure():
    cache = MagicMock()
    cache.has_nl_range.return_value = True
    cache.read_nl.return_value = iter([b"invalid"])
    fetcher = _fetcher_without_jvlink()
    fetcher.parser_factory.parse.return_value = None

    assert list(fetcher.fetch_with_cache(cache, "RACE", "20260714", "20260714")) == []
    assert fetcher.get_statistics()["records_failed"] == 1


def test_cache_replay_counts_parser_exception_as_failure():
    cache = MagicMock()
    cache.has_nl_range.return_value = True
    cache.read_nl.return_value = iter([b"invalid"])
    fetcher = _fetcher_without_jvlink()
    fetcher.parser_factory.parse.side_effect = ValueError("broken cache record")

    assert list(fetcher.fetch_with_cache(cache, "RACE", "20260714", "20260714")) == []
    stats = fetcher.get_statistics()
    assert stats["records_fetched"] == 1
    assert stats["records_parsed"] == 0
    assert stats["records_failed"] == 1


def test_cache_replay_counts_each_parsed_list_item():
    cache = MagicMock()
    cache.has_nl_range.return_value = True
    cache.read_nl.return_value = iter([b"valid"])
    fetcher = _fetcher_without_jvlink()
    fetcher.parser_factory.parse.return_value = [{"RecordSpec": "H1"}, {"RecordSpec": "H1"}]

    records = list(fetcher.fetch_with_cache(cache, "RACE", "20260714", "20260714"))

    assert len(records) == 2
    assert all(record["_raw"] == b"valid" for record in records)
    stats = fetcher.get_statistics()
    assert stats["records_fetched"] == 1
    assert stats["records_parsed"] == 2
    assert stats["records_failed"] == 0
