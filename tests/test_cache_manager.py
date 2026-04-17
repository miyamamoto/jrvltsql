"""Unit tests for src/cache/manager.py."""

import threading
from pathlib import Path

import pytest

from src.cache.manager import CacheManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache(tmp_path: Path) -> CacheManager:
    return CacheManager(tmp_path / "cache")


def _raw(s: str) -> bytes:
    return s.encode("ascii")


# ---------------------------------------------------------------------------
# NL_ write / read round-trip
# ---------------------------------------------------------------------------

class TestNlWriteRead:
    def test_write_and_read_single_record(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("hello"))
        records = list(cm.read_nl("RACE", "20260401", "20260401"))
        assert records == [_raw("hello")]

    def test_write_multiple_records_same_date(self, tmp_path):
        cm = _make_cache(tmp_path)
        for i in range(5):
            cm.write_nl_record("RACE", "20260401", _raw(f"rec{i}"))
        records = list(cm.read_nl("RACE", "20260401", "20260401"))
        assert len(records) == 5
        assert records[0] == _raw("rec0")
        assert records[4] == _raw("rec4")

    def test_read_multi_day_range(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("day1"))
        cm.write_nl_record("RACE", "20260402", _raw("day2"))
        cm.write_nl_record("RACE", "20260403", _raw("day3"))
        records = list(cm.read_nl("RACE", "20260401", "20260403"))
        assert records == [_raw("day1"), _raw("day2"), _raw("day3")]

    def test_read_skips_missing_dates(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("day1"))
        # 20260402 intentionally missing
        cm.write_nl_record("RACE", "20260403", _raw("day3"))
        records = list(cm.read_nl("RACE", "20260401", "20260403"))
        assert records == [_raw("day1"), _raw("day3")]

    def test_read_empty_when_no_data(self, tmp_path):
        cm = _make_cache(tmp_path)
        records = list(cm.read_nl("RACE", "20260401", "20260401"))
        assert records == []

    def test_binary_records_preserved_exactly(self, tmp_path):
        cm = _make_cache(tmp_path)
        data = bytes(range(256))
        cm.write_nl_record("SE", "20260401", data)
        [result] = list(cm.read_nl("SE", "20260401", "20260401"))
        assert result == data

    def test_spec_names_are_case_insensitive(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("race", "20260401", _raw("lower"))
        records = list(cm.read_nl("RACE", "20260401", "20260401"))
        assert records == [_raw("lower")]


# ---------------------------------------------------------------------------
# NL_ index: has_nl / has_nl_range / mark_nl_complete
# ---------------------------------------------------------------------------

class TestNlIndex:
    def test_has_nl_false_before_mark(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("x"))
        assert cm.has_nl("RACE", "20260401") is False

    def test_has_nl_true_after_mark(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("x"))
        cm.mark_nl_complete("RACE", "20260401")
        assert cm.has_nl("RACE", "20260401") is True

    def test_mark_nl_complete_records_count(self, tmp_path):
        cm = _make_cache(tmp_path)
        for i in range(3):
            cm.write_nl_record("RACE", "20260401", _raw(f"r{i}"))
        cm.mark_nl_complete("RACE", "20260401")
        idx = cm._load_index(cm._index_path("RACE"))
        assert idx["20260401"]["count"] == 3
        assert idx["20260401"]["complete"] is True

    def test_mark_nl_complete_empty_date(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.mark_nl_complete("RACE", "20260402")
        assert cm.has_nl("RACE", "20260402") is True

    def test_has_nl_range_all_complete(self, tmp_path):
        cm = _make_cache(tmp_path)
        for d in ("20260401", "20260402", "20260403"):
            cm.write_nl_record("RACE", d, _raw("x"))
            cm.mark_nl_complete("RACE", d)
        assert cm.has_nl_range("RACE", "20260401", "20260403") is True

    def test_has_nl_range_partial(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("x"))
        cm.mark_nl_complete("RACE", "20260401")
        # 20260402 not marked
        assert cm.has_nl_range("RACE", "20260401", "20260402") is False

    def test_has_nl_range_single_date(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.mark_nl_complete("RACE", "20260401")
        assert cm.has_nl_range("RACE", "20260401", "20260401") is True

    def test_index_persists_across_instances(self, tmp_path):
        cache_dir = tmp_path / "cache"
        cm1 = CacheManager(cache_dir)
        cm1.write_nl_record("RACE", "20260401", _raw("x"))
        cm1.mark_nl_complete("RACE", "20260401")

        cm2 = CacheManager(cache_dir)
        assert cm2.has_nl("RACE", "20260401") is True


# ---------------------------------------------------------------------------
# RT_ write / read
# ---------------------------------------------------------------------------

class TestRtWriteRead:
    def test_write_and_read_rt(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_rt_record("0B12", "20260401", _raw("rt_data"))
        records = list(cm.read_rt("0B12", "20260401"))
        assert records == [_raw("rt_data")]

    def test_read_rt_empty_when_no_data(self, tmp_path):
        cm = _make_cache(tmp_path)
        records = list(cm.read_rt("0B12", "20260401"))
        assert records == []

    def test_rt_multiple_records(self, tmp_path):
        cm = _make_cache(tmp_path)
        for i in range(10):
            cm.write_rt_record("0B15", "20260401", _raw(f"rt{i}"))
        records = list(cm.read_rt("0B15", "20260401"))
        assert len(records) == 10

    def test_rt_and_nl_are_separate(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("nl"))
        cm.write_rt_record("RACE", "20260401", _raw("rt"))
        nl = list(cm.read_nl("RACE", "20260401", "20260401"))
        rt = list(cm.read_rt("RACE", "20260401"))
        assert nl == [_raw("nl")]
        assert rt == [_raw("rt")]


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_all_nl(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("x"))
        cm.mark_nl_complete("RACE", "20260401")
        deleted = cm.clear()
        assert deleted >= 1
        assert list(cm.read_nl("RACE", "20260401", "20260401")) == []

    def test_clear_specific_spec(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("x"))
        cm.write_nl_record("SE", "20260401", _raw("y"))
        cm.clear(spec="RACE")
        assert list(cm.read_nl("RACE", "20260401", "20260401")) == []
        assert list(cm.read_nl("SE", "20260401", "20260401")) == [_raw("y")]

    def test_clear_specific_date(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("day1"))
        cm.write_nl_record("RACE", "20260402", _raw("day2"))
        cm.clear(spec="RACE", date_str="20260401")
        assert list(cm.read_nl("RACE", "20260401", "20260401")) == []
        assert list(cm.read_nl("RACE", "20260402", "20260402")) == [_raw("day2")]

    def test_clear_rt(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_rt_record("0B12", "20260401", _raw("rt"))
        cm.clear(rt=True)
        assert list(cm.read_rt("0B12", "20260401")) == []

    def test_clear_nonexistent_returns_zero(self, tmp_path):
        cm = _make_cache(tmp_path)
        assert cm.clear() == 0


# ---------------------------------------------------------------------------
# info()
# ---------------------------------------------------------------------------

class TestInfo:
    def test_info_empty_cache(self, tmp_path):
        cm = _make_cache(tmp_path)
        info = cm.info()
        assert info["nl"] == {}
        assert info["rt"] == {}
        assert info["total_size_bytes"] == 0

    def test_info_after_nl_write(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_nl_record("RACE", "20260401", _raw("hello"))
        cm.mark_nl_complete("RACE", "20260401")
        info = cm.info()
        assert "RACE" in info["nl"]
        assert info["nl"]["RACE"]["cached_dates"] == 1
        assert info["nl"]["RACE"]["complete_dates"] == 1
        assert info["total_size_bytes"] > 0

    def test_info_after_rt_write(self, tmp_path):
        cm = _make_cache(tmp_path)
        cm.write_rt_record("0B12", "20260401", _raw("rt"))
        info = cm.info()
        assert "0B12" in info["rt"]
        assert info["rt"]["0B12"]["cached_dates"] == 1


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_nl_writes(self, tmp_path):
        cm = _make_cache(tmp_path)
        n = 100
        errors = []

        def writer(i):
            try:
                cm.write_nl_record("RACE", "20260401", _raw(f"rec{i:04d}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        records = list(cm.read_nl("RACE", "20260401", "20260401"))
        assert len(records) == n

    def test_concurrent_rt_writes(self, tmp_path):
        cm = _make_cache(tmp_path)
        n = 50
        errors = []

        def writer(i):
            try:
                cm.write_rt_record("0B12", "20260401", _raw(f"rt{i:04d}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        records = list(cm.read_rt("0B12", "20260401"))
        assert len(records) == n
