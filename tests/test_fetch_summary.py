"""HistoricalFetcher が JVOpen ごとの戻り値を残すこと、と summary の集約規則.

JVOpen の戻り値（JV-Link インターフェース仕様書 4.9.0.1）:
  p.19  readcount / downloadcount / lastfiletimestamp
  p.54  0=正常, -1=該当データ無し（又は最新バージョンの DL 選択）,
        -2=セットアップダイアログでキャンセル, それ以外の負値はエラー
"""

from __future__ import annotations

import json

import pytest

from src.fetcher.base import FetcherError
from src.fetcher.summary import (
    STATUS_ERROR,
    STATUS_NO_DATA,
    STATUS_OK,
    STATUS_SKIPPED,
    aggregate_open_code,
    jvopen_entry,
    requirement_failures,
    summarize_jvopen_spec,
    summarize_jvrtopen_spec,
    write_summary_json,
)
from src.jvlink.wrapper import JVLinkError
from tests.test_jvopen_yearly_chunks import DONE, _fetcher_with, _Wrapper


class _RaisingWrapper(_Wrapper):
    def __init__(self, error):
        super().__init__(opens=[], reads_per_open=[])
        self.error = error

    def jv_open(self, data_spec, fromtime, option):
        self.open_fromtimes.append(fromtime)
        raise self.error


class TestFetcherRecordsEveryJVOpen:
    def test_each_calendar_year_chunk_is_recorded(self):
        wrapper = _Wrapper(
            opens=[(-1, 0, 0, ""), (0, 3, 2, "20250105103000")],
            reads_per_open=[[], [(4, b"bbbb", "f2"), DONE]],
        )
        f = _fetcher_with(wrapper)
        f._wait_for_download = lambda *args, **kwargs: None

        list(f.fetch("RACE", "20240101", "20251231", option=4))

        assert f.get_jvopen_results() == [
            jvopen_entry(
                fromtime=wrapper.open_fromtimes[0],
                jvopen_code=-1,
                read_count=0,
                download_count=0,
                lastfiletimestamp="",
            ),
            jvopen_entry(
                fromtime=wrapper.open_fromtimes[1],
                jvopen_code=0,
                read_count=3,
                download_count=2,
                lastfiletimestamp="20250105103000",
            ),
        ]

    def test_results_are_reset_by_the_next_fetch(self):
        wrapper = _Wrapper(
            opens=[(0, 1, 0, "20240110000000"), (-1, 0, 0, "")],
            reads_per_open=[[(4, b"aaaa", "f1"), DONE], []],
        )
        f = _fetcher_with(wrapper)

        list(f.fetch("DIFN", "20240101", "20240131", option=1))
        list(f.fetch("DIFN", "20240101", "20240131", option=1))

        assert [r["jvopen_code"] for r in f.get_jvopen_results()] == [-1]

    def test_setup_cancel_minus_2_is_recorded_and_raised(self):
        wrapper = _Wrapper(opens=[(-2, 0, 0, "")], reads_per_open=[[]])
        f = _fetcher_with(wrapper)

        with pytest.raises(FetcherError, match=r"cancelled \(code: -2\)"):
            list(f.fetch("RACE", "20240101", "20240131", option=4))

        assert [r["jvopen_code"] for r in f.get_jvopen_results()] == [-2]

    def test_a_raised_open_error_keeps_its_code(self):
        f = _fetcher_with(_RaisingWrapper(JVLinkError("JVOpen failed", error_code=-504)))

        with pytest.raises(FetcherError):
            list(f.fetch("RACE", "20240101", "20240131", option=1))

        [entry] = f.get_jvopen_results()
        assert entry["jvopen_code"] == -504
        assert entry["read_count"] is None

    def test_records_dropped_by_the_to_date_filter_are_counted(self):
        wrapper = _Wrapper(
            opens=[(0, 1, 0, "20240110000000")],
            reads_per_open=[[(4, b"aaaa", "f1"), DONE]],
        )
        f = _fetcher_with(wrapper)
        # _fetcher_with parses every buffer as a 2022-01-10 record.

        rows = list(f.fetch("DIFN", "20211201", "20211231", option=1))

        assert rows == []
        assert f.get_records_out_of_range() == 1


class TestAggregateOpenCode:
    @pytest.mark.parametrize(
        ("codes", "expected"),
        [
            ([], None),
            ([None], None),
            ([-1, -1], -1),
            ([-1, 0], 0),
            ([0, -504], -504),
            ([-2, 0], -2),
        ],
    )
    def test_first_error_wins_then_success_then_no_data(self, codes, expected):
        assert aggregate_open_code(codes) == expected


def _spec(**overrides):
    values = {
        "dataspec": "RACE",
        "option": 1,
        "from_date": "20261010",
        "to_date": "20261011",
        "opens": [],
        "fetch_stats": {},
        "records_imported": 0,
        "records_out_of_range": 0,
        "elapsed_seconds": 0.0,
    }
    values.update(overrides)
    return summarize_jvopen_spec(**values)


class TestSpecStatus:
    def test_listed_files_are_ok(self):
        opens = [jvopen_entry(fromtime="x", jvopen_code=0, read_count=2, download_count=0,
                              lastfiletimestamp="20261010120000")]
        assert _spec(opens=opens)["status"] == STATUS_OK

    @pytest.mark.parametrize("code", [0, -1])
    def test_zero_files_is_no_data(self, code):
        opens = [jvopen_entry(fromtime="x", jvopen_code=code, read_count=0,
                              download_count=0, lastfiletimestamp="")]
        summary = _spec(opens=opens)
        assert summary["status"] == STATUS_NO_DATA
        assert summary["lastfiletimestamp"] is None

    def test_error_wins_over_listed_files(self):
        opens = [jvopen_entry(fromtime="x", jvopen_code=0, read_count=2)]
        summary = _spec(opens=opens, error=RuntimeError("boom"))
        assert summary["status"] == STATUS_ERROR
        assert summary["error"] == "RuntimeError: boom"

    def test_skipped_reports_the_skipped_code(self):
        summary = _spec(skipped=True, skipped_code=-303, error=None)
        assert summary["status"] == STATUS_SKIPPED
        assert summary["jvopen_code"] == -303

    def test_counts_are_summed_and_latest_timestamp_kept(self):
        opens = [
            jvopen_entry(fromtime="a", jvopen_code=0, read_count=2, download_count=1,
                         lastfiletimestamp="20251231235959"),
            jvopen_entry(fromtime="b", jvopen_code=0, read_count=3, download_count=0,
                         lastfiletimestamp="20260105010101"),
        ]
        summary = _spec(opens=opens)
        assert summary["read_count"] == 5
        assert summary["download_count"] == 1
        assert summary["lastfiletimestamp"] == "20260105010101"
        assert summary["fromtimes"] == ["a", "b"]


class TestRequirementFailures:
    def test_spec_with_files_passes_and_missing_spec_fails(self):
        ok = _spec(opens=[jvopen_entry(fromtime="x", jvopen_code=0, read_count=1)])
        assert requirement_failures(["RACE"], [ok]) == []
        assert requirement_failures(["MING"], [ok]) == [
            {"dataspec": "MING", "status": "not_run", "read_count": None}
        ]

    def test_realtime_spec_is_judged_on_records_read(self):
        summary = summarize_jvrtopen_spec(
            dataspec="0B12",
            from_date="20261010",
            to_date="20261011",
            opens=[{"key": "20261010", "jvrtopen_code": 0}],
            stats={"records_fetched": 4, "records_imported": 4},
            elapsed_seconds=0.0,
        )
        assert summary["status"] == STATUS_OK
        assert requirement_failures(["0B12"], [summary]) == []


def test_write_summary_json_replaces_atomically(tmp_path):
    target = tmp_path / "nested" / "summary.json"

    write_summary_json(target, {"schema_version": 1, "specs": []})
    write_summary_json(target, {"schema_version": 1, "specs": [{"dataspec": "RACE"}]})

    assert json.loads(target.read_text(encoding="utf-8"))["specs"] == [{"dataspec": "RACE"}]
    assert [p.name for p in target.parent.iterdir()] == ["summary.json"]
