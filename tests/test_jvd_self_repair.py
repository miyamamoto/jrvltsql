"""Historical JVRead self-repair tests.

Recovery uses the exact filename returned by JVRead and JVFiledelete. It does
not inspect or unlink Wine cache paths directly.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.cache.manager import CacheManager
from src.jvlink.wrapper import JVLinkError, JVLinkWrapper


def _fetcher():
    fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
    fetcher.jvlink = MagicMock()
    fetcher.jvlink.jv_file_delete.return_value = 0
    fetcher.jvlink.jv_close.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 3, 1, "ts")
    fetcher.parser_factory = MagicMock()
    fetcher.progress_display = None
    fetcher._records_fetched = 0
    fetcher._records_parsed = 0
    fetcher._records_failed = 0
    fetcher._recoverable_read_errors = 0
    fetcher._repaired_read_errors = 0
    fetcher._files_processed = 0
    fetcher._total_files = 3
    fetcher._jvd_self_repair_attempts = 0
    fetcher._jvd_replay_records_remaining = 0
    fetcher._jv_open_context = ("RACE", "20260101000000", 1)
    fetcher._jv_open_last_file_timestamp = "ts"
    fetcher._fetch_task_id = None
    fetcher._wait_for_download = MagicMock()
    return fetcher


def test_zero_byte_read_error_deletes_exact_file_then_closes_and_reopens():
    fetcher = _fetcher()
    fetcher.jvlink.jv_read.side_effect = [
        (-402, None, "corrupt/RACE.jvd"),
        (0, None, None),
    ]
    calls = []
    fetcher.jvlink.jv_file_delete.side_effect = lambda filename: (
        calls.append(("delete", filename)) or 0
    )
    fetcher.jvlink.jv_close.side_effect = lambda: calls.append(("close", None)) or 0
    fetcher.jvlink.jv_open.side_effect = lambda *args: (
        calls.append(("open", args)) or (0, 3, 1, "ts")
    )

    assert list(
        fetcher._fetch_and_parse(
            recover_file_error=fetcher._recover_historical_read_error,
        )
    ) == []

    assert calls == [
        ("delete", "corrupt/RACE.jvd"),
        ("close", None),
        ("open", ("RACE", "20260101000000", 1)),
    ]
    assert fetcher._jvd_self_repair_attempts == 1
    assert fetcher.get_statistics()["recoverable_read_errors"] == 0
    assert fetcher.get_statistics()["repaired_read_errors"] == 1


def test_invalid_content_error_deletes_for_next_run_then_fails_closed():
    fetcher = _fetcher()
    fetcher.jvlink.jv_read.side_effect = [
        (-403, None, "corrupt/RACE.jvd"),
    ]

    with pytest.raises(FetcherError, match="automatic replay is limited"):
        list(
            fetcher._fetch_and_parse(
                recover_file_error=fetcher._recover_historical_read_error,
            )
        )

    fetcher.jvlink.jv_file_delete.assert_called_once_with("corrupt/RACE.jvd")
    fetcher.jvlink.jv_close.assert_not_called()
    fetcher.jvlink.jv_open.assert_not_called()


def test_read_recovery_waits_for_redownload():
    fetcher = _fetcher()
    fetcher.jvlink.jv_open.return_value = (0, 3, 2, "ts")
    fetcher._wait_for_download = MagicMock()

    fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    fetcher._wait_for_download.assert_called_once_with(download_count=2)


def test_read_recovery_resets_reopened_progress_total():
    fetcher = _fetcher()
    fetcher.progress_display = MagicMock()
    fetcher._fetch_task_id = 17
    fetcher._total_files = 8
    fetcher.jvlink.jv_open.return_value = (0, 8, 1, "ts")

    fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    fetcher.progress_display.update.assert_called_once_with(
        17,
        completed=0,
        total=8,
        status="再取得 0/8",
    )


def test_read_recovery_rejects_empty_reopened_stream():
    fetcher = _fetcher()
    fetcher._records_fetched = 2
    fetcher.jvlink.jv_open.return_value = (-1, 0, 0, "")

    with pytest.raises(FetcherError, match="Failed to reopen JVOpen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "returned no data" in str(exc_info.value.__cause__)
    assert fetcher._jvd_replay_records_remaining == 2


def test_read_recovery_rejects_reopen_without_redownload():
    fetcher = _fetcher()
    fetcher.jvlink.jv_open.return_value = (0, 3, 0, "ts")

    with pytest.raises(FetcherError, match="Failed to reopen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "did not restore" in str(exc_info.value.__cause__)
    assert "download_count=0" in str(exc_info.value.__cause__)


def test_read_recovery_rejects_shorter_reopened_stream():
    fetcher = _fetcher()
    fetcher.jvlink.jv_open.return_value = (0, 2, 1, "ts")

    with pytest.raises(FetcherError, match="Failed to reopen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "did not restore" in str(exc_info.value.__cause__)
    assert "read_count=2, expected_exactly=3" in str(exc_info.value.__cause__)


def test_read_recovery_rejects_longer_reopened_stream():
    fetcher = _fetcher()
    fetcher.jvlink.jv_open.return_value = (0, 4, 1, "ts")

    with pytest.raises(FetcherError, match="Failed to reopen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "did not restore" in str(exc_info.value.__cause__)
    assert "read_count=4, expected_exactly=3" in str(exc_info.value.__cause__)


def test_read_recovery_checks_count_when_original_stream_reported_zero():
    fetcher = _fetcher()
    fetcher._total_files = 0
    fetcher.jvlink.jv_open.return_value = (0, 1, 1, "ts")

    with pytest.raises(FetcherError, match="Failed to reopen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "did not restore" in str(exc_info.value.__cause__)
    assert "read_count=1, expected_exactly=0" in str(exc_info.value.__cause__)


def test_read_recovery_rejects_changed_last_file_timestamp():
    fetcher = _fetcher()
    fetcher.jvlink.jv_open.return_value = (0, 3, 1, "changed-ts")

    with pytest.raises(FetcherError, match="Failed to reopen") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt/RACE.jvd")

    assert isinstance(exc_info.value.__cause__, FetcherError)
    assert "stream changed" in str(exc_info.value.__cause__)
    assert "expected='ts'" in str(exc_info.value.__cause__)


def test_reopen_does_not_emit_already_processed_records_twice():
    fetcher = _fetcher()
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (-402, None, "corrupt.jvd"),
        (1, b"A", "first.jvd"),
        (1, b"B", "second.jvd"),
        (0, None, None),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "value": raw,
    }

    records = list(
        fetcher._fetch_and_parse(
            recover_file_error=fetcher._recover_historical_read_error,
            consume_replayed_record=fetcher._consume_replayed_record,
        )
    )

    assert [record["value"] for record in records] == [b"A", b"B"]
    assert fetcher._records_fetched == 2
    assert fetcher.parser_factory.parse.call_count == 2


def test_second_zero_byte_error_during_replay_restarts_same_prefix():
    fetcher = _fetcher()
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (-402, None, "corrupt-1.jvd"),
        (1, b"A", "first.jvd"),
        (-402, None, "corrupt-2.jvd"),
        (1, b"A", "first.jvd"),
        (1, b"B", "second.jvd"),
        (0, None, None),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "value": raw,
    }

    records = list(
        fetcher._fetch_and_parse(
            recover_file_error=fetcher._recover_historical_read_error,
            consume_replayed_record=fetcher._consume_replayed_record,
        )
    )

    assert [record["value"] for record in records] == [b"A", b"B"]
    assert fetcher._records_fetched == 2
    assert fetcher.parser_factory.parse.call_count == 2
    assert fetcher._jvd_self_repair_attempts == 2


def test_recovery_write_through_cache_contains_no_replayed_duplicate(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = CacheManager(tmp_path / "cache")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.side_effect = [
        (0, 2, 0, "ts"),
        (0, 2, 1, "ts"),
    ]
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (-402, None, "corrupt.jvd"),
        (1, b"A", "first.jvd"),
        (1, b"B", "second.jvd"),
        (0, None, None),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "Year": "2026",
        "MonthDay": "0101" if raw == b"A" else "0103",
        "value": raw,
    }

    records = list(fetcher.fetch("RACE", "20260101", "20260103"))

    assert [record["value"] for record in records] == [b"A", b"B"]
    assert list(
        fetcher.cache_manager.read_nl("RACE", "20260101", "20260103")
    ) == [b"A", b"B"]
    assert fetcher.cache_manager.has_nl_range(
        "RACE",
        "20260101",
        "20260103",
    )
    assert fetcher.get_statistics()["repaired_read_errors"] == 1


def test_failed_fetch_rolls_back_raw_cache_append(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = CacheManager(tmp_path / "cache")
    fetcher.cache_manager.write_nl_record("RACE", "20260101", b"existing")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 2, 0, "ts")
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (-403, None, "corrupt.jvd"),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "Year": "2026",
        "MonthDay": "0101",
        "value": raw,
    }

    with pytest.raises(FetcherError, match="automatic replay is limited"):
        list(fetcher.fetch("RACE", "20260101", "20260101"))

    assert list(
        fetcher.cache_manager.read_nl("RACE", "20260101", "20260101")
    ) == [b"existing"]
    assert not fetcher.cache_manager.has_nl("RACE", "20260101")


def test_abandoned_fetch_rolls_back_raw_cache_append(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = CacheManager(tmp_path / "cache")
    fetcher.cache_manager.write_nl_record("RACE", "20260101", b"existing")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 2, 0, "ts")
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (1, b"B", "second.jvd"),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "Year": "2026",
        "MonthDay": "0101",
        "value": raw,
    }

    records = fetcher.fetch("RACE", "20260101", "20260101")
    assert next(records)["value"] == b"A"
    records.close()

    assert list(
        fetcher.cache_manager.read_nl("RACE", "20260101", "20260101")
    ) == [b"existing"]
    assert not fetcher.cache_manager.has_nl("RACE", "20260101")


def test_abandoned_fetch_with_cache_clears_attached_manager(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    cache_manager = CacheManager(tmp_path / "cache")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 2, 0, "ts")
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (1, b"B", "second.jvd"),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: {
        "RecordSpec": "RA",
        "Year": "2026",
        "MonthDay": "0101",
        "value": raw,
    }

    records = fetcher.fetch_with_cache(
        cache_manager,
        "RACE",
        "20260101",
        "20260101",
    )
    assert next(records)["value"] == b"A"
    records.close()

    assert fetcher.cache_manager is None
    assert list(cache_manager.read_nl("RACE", "20260101", "20260101")) == []
    assert not cache_manager.has_nl("RACE", "20260101")


def test_undated_record_rolls_back_partial_cache_and_leaves_range_incomplete(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = CacheManager(tmp_path / "cache")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 2, 0, "ts")
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"dated", "dated.jvd"),
        (1, b"master", "master.jvd"),
        (0, None, None),
    ]
    fetcher.parser_factory.parse.side_effect = lambda raw: (
        {"RecordSpec": "RA", "Year": "2026", "MonthDay": "0101"}
        if raw == b"dated"
        else {"RecordSpec": "UM"}
    )

    records = list(fetcher.fetch("DIFN", "20260101", "20260101"))

    assert [record["RecordSpec"] for record in records] == ["RA", "UM"]
    assert not fetcher.cache_manager.has_nl("DIFN", "20260101")
    assert list(fetcher.cache_manager.read_nl("DIFN", "20260101", "20260101")) == []


def test_chokyo_date_is_used_for_cache_coverage(tmp_path):
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = CacheManager(tmp_path / "cache")
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 1, 0, "ts")
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"training", "training.jvd"),
        (0, None, None),
    ]
    fetcher.parser_factory.parse.return_value = {
        "RecordSpec": "HC",
        "ChokyoDate": "20260101",
    }

    records = list(fetcher.fetch("SLOP", "20260101", "20260101"))

    assert records[0]["ChokyoDate"] == "20260101"
    assert fetcher.cache_manager.has_nl("SLOP", "20260101")
    assert list(
        fetcher.cache_manager.read_nl("SLOP", "20260101", "20260101")
    ) == [b"training"]


def test_replay_skip_still_runs_periodic_com_buffer_gc():
    fetcher = _fetcher()
    fetcher._jvd_replay_records_remaining = 1
    fetcher.jvlink.jv_read.side_effect = [
        (1, b"A", "first.jvd"),
        (0, None, None),
    ]

    with (
        patch("src.fetcher.base.time") as fetcher_time,
        patch("src.fetcher.base.gc.collect") as collect,
        patch("src.fetcher.base.logger.info") as info,
    ):
        fetcher_time.time.side_effect = [0.0, 11.0]
        assert list(
            fetcher._fetch_and_parse(
                consume_replayed_record=fetcher._consume_replayed_record,
            )
        ) == []

    collect.assert_called_once_with()
    info.assert_any_call(
        "Replaying records after historical recovery",
        records_previously_emitted=0,
        files_processed=0,
        total_files=3,
    )


def test_file_not_found_during_replay_fails_closed():
    fetcher = _fetcher()
    fetcher._jvd_replay_records_remaining = 1
    fetcher.jvlink.jv_read.side_effect = [
        (-503, None, "missing.jvd"),
    ]

    with pytest.raises(FetcherError, match="-503"):
        list(
            fetcher._fetch_and_parse(
                consume_replayed_record=fetcher._consume_replayed_record,
            )
        )

    fetcher.jvlink.jv_file_delete.assert_not_called()
    assert fetcher._jvd_replay_records_remaining == 1


def test_incomplete_replay_does_not_mark_raw_cache_complete():
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = MagicMock()
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 3, 0, "ts")

    def incomplete_stream(*args, **kwargs):
        fetcher._jvd_replay_records_remaining = 1
        if False:
            yield None

    fetcher._fetch_and_parse = incomplete_stream

    with pytest.raises(FetcherError, match="recovery replay caught up"):
        list(fetcher.fetch("RACE", "20260101", "20260103"))

    fetcher.cache_manager.mark_nl_range_complete.assert_not_called()


def test_unrepaired_read_error_does_not_mark_raw_cache_complete():
    fetcher = _fetcher()
    fetcher.show_progress = False
    fetcher._service_key = None
    fetcher.cache_manager = MagicMock()
    fetcher.jvlink.jv_init.return_value = 0
    fetcher.jvlink.jv_open.return_value = (0, 3, 0, "ts")

    def incomplete_stream(*args, **kwargs):
        fetcher._recoverable_read_errors = 1
        if False:
            yield None

    fetcher._fetch_and_parse = incomplete_stream

    with pytest.raises(FetcherError, match="unrepaired JVRead error"):
        list(fetcher.fetch("RACE", "20260101", "20260103"))

    fetcher.cache_manager.mark_nl_range_complete.assert_not_called()


def test_read_recovery_is_bounded():
    fetcher = _fetcher()

    fetcher._recover_historical_read_error(-402, "first.jvd")
    fetcher._recover_historical_read_error(-402, "second.jvd")
    with pytest.raises(FetcherError, match="after 2 self-repair retries"):
        fetcher._recover_historical_read_error(-402, "third.jvd")

    assert fetcher.jvlink.jv_file_delete.call_count == 3
    assert fetcher.jvlink.jv_close.call_count == 2
    assert fetcher.jvlink.jv_open.call_count == 2


def test_read_recovery_fails_closed_without_filename():
    fetcher = _fetcher()

    with pytest.raises(FetcherError, match="without a filename"):
        fetcher._recover_historical_read_error(-402, "")

    fetcher.jvlink.jv_file_delete.assert_not_called()
    fetcher.jvlink.jv_close.assert_not_called()


def test_read_recovery_fails_closed_without_open_context():
    fetcher = _fetcher()
    fetcher._jv_open_context = None

    with pytest.raises(FetcherError, match="no JVOpen context"):
        fetcher._recover_historical_read_error(-402, "corrupt.jvd")


def test_read_recovery_preserves_delete_failure_as_cause():
    fetcher = _fetcher()
    delete_error = JVLinkError("delete failed", error_code=-1)
    fetcher.jvlink.jv_file_delete.side_effect = delete_error

    with pytest.raises(FetcherError, match="JVFiledelete failed") as exc_info:
        fetcher._recover_historical_read_error(-402, "corrupt.jvd")

    assert exc_info.value.__cause__ is delete_error
    fetcher.jvlink.jv_close.assert_not_called()


def test_read_recovery_rejects_nonzero_delete_result():
    fetcher = _fetcher()
    fetcher.jvlink.jv_file_delete.return_value = -1

    with pytest.raises(FetcherError, match="JVFiledelete returned -1"):
        fetcher._recover_historical_read_error(-402, "corrupt.jvd")

    fetcher.jvlink.jv_close.assert_not_called()


@pytest.mark.parametrize("error_code", [-203, -502, -503])
def test_non_corruption_error_fails_without_delete_or_stream_restart(error_code):
    fetcher = _fetcher()
    fetcher.jvlink.jv_read.side_effect = [
        (error_code, None, "other.jvd"),
        (0, None, None),
    ]

    with pytest.raises(FetcherError, match=str(error_code)):
        list(
            fetcher._fetch_and_parse(
                recover_file_error=fetcher._recover_historical_read_error,
            )
        )

    fetcher.jvlink.jv_read.assert_called_once()
    fetcher.jvlink.jv_file_delete.assert_not_called()
    fetcher.jvlink.jv_close.assert_not_called()
    fetcher.jvlink.jv_open.assert_not_called()


@pytest.mark.parametrize("error_code", [-402, -403])
def test_win32_wrapper_returns_recoverable_filename(error_code):
    wrapper = JVLinkWrapper.__new__(JVLinkWrapper)
    wrapper._is_open = True
    wrapper._jvlink = MagicMock()
    wrapper._jvlink.JVRead.return_value = (
        error_code,
        "",
        0,
        "corrupt/RACE.jvd",
    )

    assert wrapper.jv_read() == (error_code, None, "corrupt/RACE.jvd")
