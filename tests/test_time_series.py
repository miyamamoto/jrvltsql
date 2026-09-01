#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""時系列データ取得テスト

時系列データ（0B20, 0B30-0B36, 0B41-0B42）のキー生成とfetch_time_series()をテストします。
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_key_generation():
    """キー生成関数のテスト"""
    print("=" * 60)
    print("1. キー生成関数テスト")
    print("=" * 60)

    from src.jvlink.constants import (
        generate_time_series_key,
        generate_time_series_full_key,
        get_all_race_keys_for_date,
        JYO_CODES,
        JVRTOPEN_TIME_SERIES_SPECS,
        is_time_series_spec,
    )

    # 基本的なキー生成
    key = generate_time_series_key("20251201", "05", 11)
    print(f"generate_time_series_key('20251201', '05', 11) = '{key}'")
    assert key == "202512010511", f"Expected '202512010511', got '{key}'"
    print("  -> OK: キー形式 YYYYMMDDJJRR が正しい")

    # エッジケース
    key2 = generate_time_series_key("20251201", "01", 1)
    print(f"generate_time_series_key('20251201', '01', 1) = '{key2}'")
    assert key2 == "202512010101", f"Expected '202512010101', got '{key2}'"
    print("  -> OK: 1レース目もゼロ埋めされる")

    # 16桁キー生成は互換用ヘルパーとして残す
    full_key = generate_time_series_full_key("20251201", "05", 5, 8, 11)
    print(f"generate_time_series_full_key('20251201', '05', 5, 8, 11) = '{full_key}'")
    assert full_key == "2025120105050811", f"Expected '2025120105050811', got '{full_key}'"
    print("  -> OK: 互換用16桁キー YYYYMMDDJJKKNNRR が正しい")

    # 全レースキー生成（120キー）
    all_keys = get_all_race_keys_for_date("20251201")
    print(f"\nget_all_race_keys_for_date('20251201'): {len(all_keys)} keys")
    assert len(all_keys) == 120, f"Expected 120, got {len(all_keys)}"
    print("  -> OK: 10場 x 12レース = 120キー")

    # 時系列spec判定
    print(f"\nJVRTOPEN_TIME_SERIES_SPECS: {list(JVRTOPEN_TIME_SERIES_SPECS.keys())}")
    assert is_time_series_spec("0B30") == True
    assert is_time_series_spec("0B36") == True
    assert is_time_series_spec("0B41") == True
    assert is_time_series_spec("0B42") == True
    assert is_time_series_spec("0B12") == False
    print("  -> OK: is_time_series_spec() が正しく判定")

    # 競馬場コード
    print(f"\nJYO_CODES: {JYO_CODES}")

    print("\n[PASSED] キー生成関数テスト")


def test_fetch_time_series_batch_from_db_uses_simple_key():
    """DB登録済みレースからの時系列取得が12桁キーを使うことを確認する。"""
    from contextlib import closing
    import sqlite3
    import tempfile
    import types
    from pathlib import Path

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("""
                CREATE TABLE NL_RA (
                    Year INTEGER,
                    MonthDay INTEGER,
                    JyoCD TEXT,
                    Kaiji INTEGER,
                    Nichiji INTEGER,
                    RaceNum INTEGER
                )
                """)
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")
            conn.commit()

        class FakeJVLink:
            def __init__(self):
                self.opened = []
                self.closed = 0

            def jv_init(self):
                return 0

            def jv_rt_open(self, data_spec, key):
                self.opened.append((data_spec, key))
                return 0, 1

            def jv_close(self):
                self.closed += 1

        fetcher = object.__new__(RealtimeFetcher)
        fetcher.jvlink = FakeJVLink()

        def fake_fetch_and_parse(self):
            yield {"RecordSpec": "O1", "_raw": b"O1"}

        fetcher._fetch_and_parse = types.MethodType(fake_fetch_and_parse, fetcher)

        records = list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B30",
                db_path=str(db_path),
                from_date="20251201",
                to_date="20251201",
            )
        )

        assert fetcher.jvlink.opened == [("0B30", "202512010511")]
        assert fetcher.jvlink.closed >= 1
        assert records == [{"RecordSpec": "O1", "_raw": b"O1"}]


def test_fetch_time_series_batch_from_db_closes_no_data_stream():
    """JVRTOpenがno-dataを返しても次キー前にJVCloseする。"""
    from contextlib import closing
    import sqlite3
    import tempfile
    from pathlib import Path

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("""
                CREATE TABLE NL_RA (
                    Year INTEGER,
                    MonthDay INTEGER,
                    JyoCD TEXT,
                    Kaiji INTEGER,
                    Nichiji INTEGER,
                    RaceNum INTEGER
                )
                """)
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")

            conn.commit()

        class FakeJVLink:
            def __init__(self):
                self.opened = []
                self.closed = 0

            def jv_init(self):
                return 0

            def jv_rt_open(self, data_spec, key):
                self.opened.append((data_spec, key))
                return -1, 0

            def jv_close(self):
                self.closed += 1

        progress = []
        fetcher = object.__new__(RealtimeFetcher)
        fetcher.jvlink = FakeJVLink()

        records = list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B30",
                db_path=str(db_path),
                from_date="20251201",
                to_date="20251201",
                progress_callback=progress.append,
            )
        )

        assert records == []
        assert fetcher.jvlink.opened == [("0B30", "202512010511")]
        assert fetcher.jvlink.closed >= 1
        assert progress[-1]["status"] == "no_data"
        assert progress[-1]["processed_keys"] == 1
        assert progress[-1]["no_data_keys"] == 1


def test_fetch_time_series_batch_from_db_discards_partial_key():
    """後続JVRead失敗時に同一レースの途中レコードを外へ流さない。"""
    from contextlib import closing
    from pathlib import Path
    import sqlite3
    import tempfile
    import types

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("""
                CREATE TABLE NL_RA (
                    Year INTEGER,
                    MonthDay INTEGER,
                    JyoCD TEXT,
                    Kaiji INTEGER,
                    Nichiji INTEGER,
                    RaceNum INTEGER
                )
                """)
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")
            conn.commit()

        class FakeJVLink:
            def jv_init(self):
                return 0

            def jv_rt_open(self, data_spec, key):
                return 0, 2

            def jv_close(self):
                pass

        fetcher = object.__new__(RealtimeFetcher)
        fetcher.jvlink = FakeJVLink()

        def partial_then_error(self):
            yield {"RecordSpec": "O1", "_raw": b"partial"}
            raise RuntimeError("later JVRead failed")

        fetcher._fetch_and_parse = types.MethodType(partial_then_error, fetcher)
        progress = []

        records = list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B30",
                db_path=str(db_path),
                from_date="20251201",
                to_date="20251201",
                progress_callback=progress.append,
            )
        )

        assert records == []
        assert progress[-1]["status"] == "exception"
        assert progress[-1]["success_keys"] == 0
        assert progress[-1]["error_keys"] == 1
        assert progress[-1]["records_for_key"] == 0
        assert progress[-1]["total_records"] == 0


def test_fetch_time_series_batch_discards_partial_key():
    """全場走査経路でも途中レコードを外へ流さない。"""
    import types

    from src.fetcher.realtime import RealtimeFetcher

    class FakeJVLink:
        def jv_init(self):
            return 0

        def jv_rt_open(self, data_spec, key):
            return 0, 2

        def jv_close(self):
            pass

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = FakeJVLink()

    def partial_then_error(self):
        yield {"RecordSpec": "O1", "_raw": b"partial"}
        raise RuntimeError("later JVRead failed")

    fetcher._fetch_and_parse = types.MethodType(partial_then_error, fetcher)

    records = list(
        fetcher.fetch_time_series_batch(
            data_spec="0B30",
            from_date="20251201",
            to_date="20251201",
            jyo_codes=["05"],
            race_nums=[11],
        )
    )

    assert records == []


def test_fetch_time_series_batch_from_postgres_uses_pg_race_keys(monkeypatch):
    """PostgreSQL保存のNL_RA/RT_RAから時系列取得キーを作れることを確認する。"""
    import types

    from src.fetcher.realtime import RealtimeFetcher

    captured = {}

    def fake_pg_rows(query, params, pg_config):
        captured["query"] = query
        captured["params"] = params
        captured["pg_config"] = pg_config
        return [(2025, 1201, "05", 5, 8, 11)]

    monkeypatch.setattr(
        RealtimeFetcher,
        "_fetch_time_series_race_rows_from_postgres",
        staticmethod(fake_pg_rows),
    )
    monkeypatch.setattr(
        RealtimeFetcher,
        "_postgres_table_exists",
        staticmethod(lambda _config, table_name: table_name == "rt_ra"),
    )

    class FakeJVLink:
        def __init__(self):
            self.opened = []

        def jv_init(self):
            return 0

        def jv_rt_open(self, data_spec, key):
            self.opened.append((data_spec, key))
            return 0, 1

        def jv_close(self):
            pass

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = FakeJVLink()

    def fake_fetch_and_parse(self):
        yield {"RecordSpec": "O2", "_raw": b"O2"}

    fetcher._fetch_and_parse = types.MethodType(fake_fetch_and_parse, fetcher)

    records = list(
        fetcher.fetch_time_series_batch_from_db(
            data_spec="0B42",
            db_path="ignored.sqlite",
            from_date="20251201",
            to_date="20251201",
            pg_config={"host": "localhost", "database": "keiba"},
        )
    )

    assert "FROM nl_ra" in captured["query"]
    assert "FROM rt_ra" in captured["query"]
    assert captured["params"] == [2025, 2025, 1201, 2025, 2025, 1201]
    assert fetcher.jvlink.opened == [("0B42", "202512010511")]
    assert records == [{"RecordSpec": "O2", "_raw": b"O2"}]


def test_fetch_time_series_batch_from_postgres_supports_missing_rt_ra(monkeypatch):
    """旧PostgreSQL schemaにRT_RAが無くてもNL_RAだけで収集を継続する。"""
    import types

    from src.fetcher.realtime import RealtimeFetcher

    captured = {}

    def fake_pg_rows(query, params, pg_config):
        captured["query"] = query
        return [(2025, 1201, "05", 5, 8, 11)]

    monkeypatch.setattr(
        RealtimeFetcher,
        "_fetch_time_series_race_rows_from_postgres",
        staticmethod(fake_pg_rows),
    )
    monkeypatch.setattr(
        RealtimeFetcher,
        "_postgres_table_exists",
        staticmethod(lambda _config, _table_name: False),
    )

    class FakeJVLink:
        def jv_init(self):
            return 0

        def jv_rt_open(self, data_spec, key):
            return 0, 1

        def jv_close(self):
            pass

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = FakeJVLink()

    def fake_fetch_and_parse(self):
        yield {"RecordSpec": "O2", "_raw": b"O2"}

    fetcher._fetch_and_parse = types.MethodType(fake_fetch_and_parse, fetcher)

    records = list(
        fetcher.fetch_time_series_batch_from_db(
            data_spec="0B42",
            db_path="ignored.sqlite",
            from_date="20251201",
            to_date="20251201",
            pg_config={"host": "localhost", "database": "keiba"},
        )
    )

    assert "FROM nl_ra" in captured["query"]
    assert "FROM rt_ra" not in captured["query"]
    assert records == [{"RecordSpec": "O2", "_raw": b"O2"}]


def _fixed_window_now(monkeypatch):
    from datetime import datetime, timedelta, timezone

    import src.fetcher.realtime as realtime_module

    now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone(timedelta(hours=9)))
    monkeypatch.setattr(realtime_module, "_now_jst", lambda: now, raising=False)


def _window_jvlink():
    class FakeJVLink:
        def __init__(self):
            self.opened = []
            self.init_calls = 0

        def jv_init(self):
            self.init_calls += 1
            return 0

        def jv_rt_open(self, data_spec, key):
            self.opened.append((data_spec, key))
            return -1, 0

        def jv_close(self):
            return 0

    return FakeJVLink()


def test_sqlite_race_window_keeps_near_post_and_reports_drop_reasons(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing

    from src.fetcher.realtime import RealtimeFetcher

    _fixed_window_now(monkeypatch)
    db_path = tmp_path / "window.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE NL_RA (
                Year INTEGER, MonthDay INTEGER, JyoCD TEXT, Kaiji INTEGER,
                Nichiji INTEGER, RaceNum INTEGER, HassoTime TEXT
            )
            """)
        conn.executemany(
            "INSERT INTO NL_RA VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (2026, 901, "05", 3, 4, 1, "1230"),
                (2026, 901, "05", 3, 4, 2, "1231"),
                (2026, 901, "05", 3, 4, 3, "1157"),
            ],
        )
        conn.commit()

    progress = []
    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    assert (
        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B41",
                db_path=str(db_path),
                from_date="20260901",
                to_date="20260901",
                post_time_within_minutes=30,
                post_time_not_past_minutes=2,
                progress_callback=progress.append,
            )
        )
        == []
    )

    assert fetcher.jvlink.opened == [("0B41", "202609010501")]
    assert progress[0] == {
        "status": "window_filter",
        "key": None,
        "processed_keys": 0,
        "total_keys": 1,
        "considered_keys": 3,
        "window_candidate_keys": 3,
        "window_kept_keys": 1,
        "dropped_too_far_future": 1,
        "dropped_too_far_past": 1,
        "skipped_out_of_window_by_date": 0,
        "success_keys": 0,
        "no_data_keys": 0,
        "error_keys": 0,
        "total_records": 0,
    }


def test_race_window_skips_malformed_post_time_on_out_of_window_date(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing

    from src.fetcher.realtime import RealtimeFetcher

    _fixed_window_now(monkeypatch)
    db_path = tmp_path / "date-excluded.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE NL_RA (
                Year INTEGER, MonthDay INTEGER, JyoCD TEXT, Kaiji INTEGER,
                Nichiji INTEGER, RaceNum INTEGER, HassoTime TEXT
            )
            """)
        conn.executemany(
            "INSERT INTO NL_RA VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (2026, 901, "05", 3, 4, 1, "1230"),
                (2026, 902, "05", 3, 4, 1, "not-a-time"),
            ],
        )
        conn.commit()

    progress = []
    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    assert (
        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B41",
                db_path=str(db_path),
                from_date="20260901",
                to_date="20260902",
                post_time_within_minutes=30,
                progress_callback=progress.append,
            )
        )
        == []
    )

    assert fetcher.jvlink.opened == [("0B41", "202609010501")]
    assert progress[0]["considered_keys"] == 2
    assert progress[0]["window_candidate_keys"] == 1
    assert progress[0]["window_kept_keys"] == 1
    assert progress[0]["dropped_too_far_future"] == 1
    assert progress[0]["dropped_too_far_past"] == 0
    assert progress[0]["skipped_out_of_window_by_date"] == 1


def test_race_window_boundary_date_is_evaluated_by_post_time(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing
    from datetime import datetime

    import src.fetcher.realtime as realtime_module
    from src.fetcher.realtime import JST, RealtimeFetcher

    monkeypatch.setattr(
        realtime_module,
        "_now_jst",
        lambda: datetime(2026, 9, 1, 0, 0, tzinfo=JST),
        raising=False,
    )
    db_path = tmp_path / "boundary-date.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE NL_RA (
                Year INTEGER, MonthDay INTEGER, JyoCD TEXT, Kaiji INTEGER,
                Nichiji INTEGER, RaceNum INTEGER, HassoTime TEXT
            )
            """)
        conn.executemany(
            "INSERT INTO NL_RA VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (2026, 831, "05", 3, 4, 1, "1200"),
                (2026, 831, "05", 3, 4, 2, "2359"),
            ],
        )
        conn.commit()

    progress = []
    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    assert (
        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B41",
                db_path=str(db_path),
                from_date="20260831",
                to_date="20260831",
                post_time_within_minutes=30,
                post_time_not_past_minutes=2,
                progress_callback=progress.append,
            )
        )
        == []
    )

    assert fetcher.jvlink.opened == [("0B41", "202608310502")]
    assert progress[0]["considered_keys"] == 2
    assert progress[0]["window_candidate_keys"] == 2
    assert progress[0]["window_kept_keys"] == 1
    assert progress[0]["dropped_too_far_future"] == 0
    assert progress[0]["dropped_too_far_past"] == 1
    assert progress[0]["skipped_out_of_window_by_date"] == 0


@pytest.mark.parametrize(
    ("race_row", "within_minutes", "not_past_minutes", "race_key"),
    [
        ((2026, 831, "05", 3, 4, 1, "930"), 30, None, "202608310501"),
        ((2026, 902, "05", 3, 4, 1, "930"), None, 2, "202609020501"),
    ],
)
def test_race_window_disabled_bound_does_not_date_exclude_candidate(
    monkeypatch, race_row, within_minutes, not_past_minutes, race_key
):
    from src.fetcher.base import FetcherError
    from src.fetcher.realtime import _filter_race_rows_by_post_time

    _fixed_window_now(monkeypatch)

    with pytest.raises(FetcherError, match=rf"{race_key}.*unparsable"):
        _filter_race_rows_by_post_time(
            [race_row],
            post_time_within_minutes=within_minutes,
            post_time_not_past_minutes=not_past_minutes,
        )


def test_postgresql_race_window_filters_rows_from_pg_source(monkeypatch):
    from src.fetcher.realtime import RealtimeFetcher

    _fixed_window_now(monkeypatch)
    captured = {}

    def fake_pg_rows(query, params, pg_config):
        captured["query"] = query
        return [
            (2026, 901, "05", 3, 4, 1, "1230"),
            (2026, 901, "05", 3, 4, 2, "1231"),
            (2026, 901, "05", 3, 4, 3, "1157"),
        ]

    monkeypatch.setattr(
        RealtimeFetcher,
        "_fetch_time_series_race_rows_from_postgres",
        staticmethod(fake_pg_rows),
    )
    monkeypatch.setattr(
        RealtimeFetcher,
        "_postgres_table_exists",
        staticmethod(lambda _config, _table_name: False),
    )
    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    assert (
        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B42",
                db_path="ignored.sqlite",
                from_date="20260901",
                to_date="20260901",
                pg_config={"host": "localhost", "database": "keiba"},
                post_time_within_minutes=30,
                post_time_not_past_minutes=2,
            )
        )
        == []
    )

    assert "hassotime" in captured["query"].lower()
    assert fetcher.jvlink.opened == [("0B42", "202609010501")]


@pytest.mark.parametrize(
    ("post_times", "reason"),
    [
        ([None], "missing"),
        (["930"], "unparsable"),
        (["１２３０"], "unparsable"),
        (["1230", "1231"], "ambiguous"),
    ],
)
def test_race_window_candidate_fails_closed_and_names_bad_race_key(
    tmp_path, monkeypatch, post_times, reason
):
    import sqlite3
    from contextlib import closing

    import pytest

    from src.fetcher.base import FetcherError
    from src.fetcher.realtime import RealtimeFetcher

    _fixed_window_now(monkeypatch)
    db_path = tmp_path / f"bad-{reason}.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("""
            CREATE TABLE NL_RA (
                Year INTEGER, MonthDay INTEGER, JyoCD TEXT, Kaiji INTEGER,
                Nichiji INTEGER, RaceNum INTEGER, HassoTime TEXT
            )
            """)
        conn.executemany(
            "INSERT INTO NL_RA VALUES (2026, 901, '05', 3, 4, 1, ?)",
            [(post_time,) for post_time in post_times],
        )
        conn.commit()

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    with pytest.raises(FetcherError, match=rf"202609010501.*{reason}"):
        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B41",
                db_path=str(db_path),
                from_date="20260901",
                to_date="20260901",
                post_time_within_minutes=30,
            )
        )
    assert fetcher.jvlink.init_calls == 0


def test_race_window_off_leaves_legacy_postgresql_query_and_rows_untouched(monkeypatch):
    from unittest.mock import MagicMock

    from src.fetcher.realtime import RealtimeFetcher

    captured = {}

    def fake_pg_rows(query, params, pg_config):
        captured["query"] = query
        return [(2026, 901, "05", 3, 4, 1)]

    monkeypatch.setattr(
        RealtimeFetcher,
        "_fetch_time_series_race_rows_from_postgres",
        staticmethod(fake_pg_rows),
    )
    monkeypatch.setattr(
        RealtimeFetcher,
        "_postgres_table_exists",
        staticmethod(lambda _config, _table_name: False),
    )
    monkeypatch.setattr(
        "src.fetcher.realtime._now_jst",
        MagicMock(side_effect=AssertionError("off path must not read the clock")),
        raising=False,
    )
    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = _window_jvlink()

    list(
        fetcher.fetch_time_series_batch_from_db(
            data_spec="0B41",
            db_path="ignored.sqlite",
            from_date="20260901",
            to_date="20260901",
            pg_config={"host": "localhost", "database": "keiba"},
        )
    )

    expected_query = """
                WITH race_targets AS (
                    SELECT year, monthday, jyocd, kaiji, nichiji, racenum
                    FROM nl_ra
                    <RT_UNION>
                )
                SELECT DISTINCT
                    year, monthday, jyocd, kaiji, nichiji, racenum
                FROM race_targets
                WHERE 1=1
            """.replace("<RT_UNION>", "")
    expected_query += " AND (year > %s OR (year = %s AND monthday >= %s))"
    expected_query += " AND (year < %s OR (year = %s AND monthday <= %s))"
    expected_query += (
        " AND LPAD(CAST(jyocd AS TEXT), 2, '0') "
        "IN ('01','02','03','04','05','06','07','08','09','10')"
    )
    expected_query += " ORDER BY year, monthday, jyocd, racenum"
    assert captured["query"] == expected_query
    assert fetcher.jvlink.opened == [("0B41", "202609010501")]


def test_odds_parsers_expand_combination_arrays():
    """O1-O6 parsers should expand embedded odds arrays into row lists."""
    from src.parser.o1_parser import O1Parser
    from src.parser.o2_parser import O2Parser
    from src.parser.o3_parser import O3Parser
    from src.parser.o4_parser import O4Parser
    from src.parser.o5_parser import O5Parser
    from src.parser.o6_parser import O6Parser
    from src.database.schema import SCHEMAS

    assert O1Parser.RECORD_LENGTH == 962
    assert O2Parser.RECORD_LENGTH == 2042
    assert O3Parser.RECORD_LENGTH == 2654
    assert O4Parser.RECORD_LENGTH == 4031
    assert O5Parser.RECORD_LENGTH == 12293
    assert O6Parser.RECORD_LENGTH == 83285
    assert (
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, Kumi)"
        in SCHEMAS["NL_O1"]
    )
    assert (
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban, Kumi)"
        in SCHEMAS["RT_O1"]
    )
    header_o1 = (
        b"O1"
        + b"4"
        + b"20260419"
        + b"2026"
        + b"0419"
        + b"06"
        + b"03"
        + b"08"
        + b"11"
        + b"04191549"
        + b"18"
        + b"18"
        + b"777"
        + b"3"
    )
    tan = b"01012301" + b"02045602" + b"0" * (26 * 8)
    fuku = b"010010002001" + b"020030004002" + b"0" * (26 * 12)
    wakuren = b"120123401" + b"130567802" + b"0" * (34 * 9)
    raw_o1 = header_o1 + tan + fuku + wakuren + b"000000001230000000045600000000789\r\n"
    assert len(raw_o1) == O1Parser.RECORD_LENGTH
    rows_o1 = O1Parser().parse(raw_o1)
    assert len(rows_o1) == 4
    assert rows_o1[0]["Umaban"] == "01"
    assert rows_o1[0]["Kumi"] == "00"
    assert rows_o1[0]["TanOdds"] == "0123"
    assert rows_o1[0]["FukuOddsHigh"] == "0020"
    assert rows_o1[-1]["Kumi"] == "13"
    assert rows_o1[-1]["Umaban"] == "0"

    header_combo = (
        b"O2"
        + b"4"
        + b"20260419"
        + b"2026"
        + b"0419"
        + b"06"
        + b"03"
        + b"08"
        + b"11"
        + b"04191549"
        + b"18"
        + b"18"
        + b"7"
    )
    raw_o2 = (
        header_combo + b"0102000123010" + b"0103000456020" + b"0" * (151 * 13) + b"00000000999\r\n"
    )
    assert len(raw_o2) == O2Parser.RECORD_LENGTH
    rows_o2 = O2Parser().parse(raw_o2)
    assert [(r["Kumi"], r["Odds"], r["Ninki"], r["Vote"]) for r in rows_o2] == [
        ("0102", "000123", "010", "00000000999"),
        ("0103", "000456", "020", "00000000999"),
    ]

    header_o3 = b"O3" + header_combo[2:]
    raw_o3 = (
        header_o3
        + b"01020012300456010"
        + b"01030023400567020"
        + b"0" * (151 * 17)
        + b"00000000777\r\n"
    )
    assert len(raw_o3) == O3Parser.RECORD_LENGTH
    rows_o3 = O3Parser().parse(raw_o3)
    assert [(r["Kumi"], r["OddsLow"], r["OddsHigh"], r["Ninki"], r["Vote"]) for r in rows_o3] == [
        ("0102", "00123", "00456", "010", "00000000777"),
        ("0103", "00234", "00567", "020", "00000000777"),
    ]

    header_o4 = b"O4" + header_combo[2:]
    raw_o4 = (
        header_o4 + b"0102000123010" + b"0201000456020" + b"0" * (304 * 13) + b"00000000666\r\n"
    )
    assert len(raw_o4) == O4Parser.RECORD_LENGTH
    rows_o4 = O4Parser().parse(raw_o4)
    assert [(r["Kumi"], r["Odds"], r["Ninki"], r["Vote"]) for r in rows_o4] == [
        ("0102", "000123", "010", "00000000666"),
        ("0201", "000456", "020", "00000000666"),
    ]

    header_o5 = b"O5" + header_combo[2:]
    raw_o5 = (
        header_o5 + b"010203000123010" + b"010204000456020" + b"0" * (814 * 15) + b"00000000555\r\n"
    )
    assert len(raw_o5) == O5Parser.RECORD_LENGTH
    rows_o5 = O5Parser().parse(raw_o5)
    assert [(r["Kumi"], r["Odds"], r["Ninki"], r["Vote"]) for r in rows_o5] == [
        ("010203", "000123", "010", "00000000555"),
        ("010204", "000456", "020", "00000000555"),
    ]

    header_o6 = b"O6" + header_combo[2:]
    raw_o6 = (
        header_o6
        + b"01020300012340010"
        + b"01020400045670020"
        + b"0" * (4894 * 17)
        + b"00000000888\r\n"
    )
    assert len(raw_o6) == O6Parser.RECORD_LENGTH
    rows_o6 = O6Parser().parse(raw_o6)
    assert [(r["Kumi"], r["Odds"], r["Ninki"], r["Vote"]) for r in rows_o6] == [
        ("010203", "0001234", "0010", "00000000888"),
        ("010204", "0004567", "0020", "00000000888"),
    ]


def test_list_methods():
    """静的メソッドのテスト"""
    print("\n" + "=" * 60)
    print("3. 静的メソッドテスト")
    print("=" * 60)

    from src.fetcher.realtime import RealtimeFetcher

    # list_time_series_specs
    specs = RealtimeFetcher.list_time_series_specs()
    print(f"list_time_series_specs(): {len(specs)} specs")
    for code, desc in specs.items():
        print(f"  {code}: {desc}")

    # list_tracks
    tracks = RealtimeFetcher.list_tracks()
    print(f"\nlist_tracks(): {len(tracks)} tracks")
    for code, name in sorted(tracks.items()):
        print(f"  {code}: {name}")

    # list_data_specs
    all_specs = RealtimeFetcher.list_data_specs()
    print(f"\nlist_data_specs(): {len(all_specs)} specs (速報+時系列)")

    assert set(specs) == {
        "0B20",
        "0B30",
        "0B31",
        "0B32",
        "0B33",
        "0B34",
        "0B35",
        "0B36",
        "0B41",
        "0B42",
    }
    assert set(tracks) == {f"{code:02d}" for code in range(1, 11)}
    assert set(specs) <= set(all_specs)
    print("\n[PASSED] 静的メソッドテスト")


def test_fetch_time_series_batch_closes_no_data_stream_before_next_key():
    """The range-scan path must close a no-data JVRTOpen before the next key.

    JVRTOpen opens the stream even when it answers -1, so skipping JVClose
    leaves it open and the next JVRTOpen fails with -202 (not closed). Every
    later key in the scan is then lost.
    """
    from src.fetcher.realtime import RealtimeFetcher

    class FakeJVLink:
        def __init__(self):
            self.opened = []
            self.closed = 0
            self._open = False

        def jv_init(self):
            return 0

        def jv_rt_open(self, data_spec, key):
            if self._open:
                return -202, 0
            self._open = True
            self.opened.append((data_spec, key))
            return -1, 0

        def jv_close(self):
            self._open = False
            self.closed += 1
            return 0

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = FakeJVLink()

    records = list(
        fetcher.fetch_time_series_batch(
            data_spec="0B30",
            from_date="20251201",
            to_date="20251201",
            jyo_codes=["05"],
            race_nums=[1, 2],
        )
    )

    assert records == []
    assert fetcher.jvlink.opened == [
        ("0B30", "202512010501"),
        ("0B30", "202512010502"),
    ]


def test_fetch_time_series_batch_closes_error_stream_before_next_key():
    """A non-success JVRTOpen other than -1 carries the same close obligation."""
    from src.fetcher.realtime import RealtimeFetcher

    class FakeJVLink:
        def __init__(self):
            self.opened = []
            self.closed = 0
            self._open = False

        def jv_init(self):
            return 0

        def jv_rt_open(self, data_spec, key):
            if self._open:
                return -202, 0
            self._open = True
            self.opened.append((data_spec, key))
            return -114, 0

        def jv_close(self):
            self._open = False
            self.closed += 1
            return 0

    fetcher = object.__new__(RealtimeFetcher)
    fetcher.jvlink = FakeJVLink()

    records = list(
        fetcher.fetch_time_series_batch(
            data_spec="0B30",
            from_date="20251201",
            to_date="20251201",
            jyo_codes=["05"],
            race_nums=[1, 2],
        )
    )

    assert records == []
    assert fetcher.jvlink.opened == [
        ("0B30", "202512010501"),
        ("0B30", "202512010502"),
    ]


def test_fetch_time_series_batch_from_db_includes_rt_ra_targets():
    """Forward-only 0B15 cards land in RT_RA before NL_RA exists.

    Same-day odds collection must be able to run off the card feed alone, so
    the race-target query reads NL_RA and RT_RA and de-duplicates.
    """
    from contextlib import closing
    import sqlite3
    import tempfile
    from pathlib import Path

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with closing(sqlite3.connect(db_path)) as conn:
            for table in ("NL_RA", "RT_RA"):
                conn.execute(f"""
                    CREATE TABLE {table} (
                        Year INTEGER,
                        MonthDay INTEGER,
                        JyoCD TEXT,
                        Kaiji INTEGER,
                        Nichiji INTEGER,
                        RaceNum INTEGER
                    )
                    """)
            # Shared in both tables plus one that only the card feed knows.
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")
            conn.execute("INSERT INTO RT_RA VALUES (2025, 1201, '05', 5, 8, 11)")
            conn.execute("INSERT INTO RT_RA VALUES (2025, 1201, '05', 5, 8, 12)")
            conn.commit()

        class FakeJVLink:
            def __init__(self):
                self.opened = []

            def jv_init(self):
                return 0

            def jv_rt_open(self, data_spec, key):
                self.opened.append((data_spec, key))
                return -1, 0

            def jv_close(self):
                return 0

        fetcher = object.__new__(RealtimeFetcher)
        fetcher.jvlink = FakeJVLink()

        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B30",
                db_path=str(db_path),
                from_date="20251201",
                to_date="20251201",
            )
        )

        assert sorted(fetcher.jvlink.opened) == [
            ("0B30", "202512010511"),
            ("0B30", "202512010512"),
        ]


def test_fetch_time_series_batch_from_db_works_without_rt_ra():
    """A database that predates the card feed still resolves NL_RA targets."""
    from contextlib import closing
    import sqlite3
    import tempfile
    from pathlib import Path

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("""
                CREATE TABLE NL_RA (
                    Year INTEGER,
                    MonthDay INTEGER,
                    JyoCD TEXT,
                    Kaiji INTEGER,
                    Nichiji INTEGER,
                    RaceNum INTEGER
                )
                """)
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")
            conn.commit()

        class FakeJVLink:
            def __init__(self):
                self.opened = []

            def jv_init(self):
                return 0

            def jv_rt_open(self, data_spec, key):
                self.opened.append((data_spec, key))
                return -1, 0

            def jv_close(self):
                return 0

        fetcher = object.__new__(RealtimeFetcher)
        fetcher.jvlink = FakeJVLink()

        list(
            fetcher.fetch_time_series_batch_from_db(
                data_spec="0B30",
                db_path=str(db_path),
                from_date="20251201",
                to_date="20251201",
            )
        )

        assert fetcher.jvlink.opened == [("0B30", "202512010511")]


def test_postgres_table_probe_resolves_like_the_query(monkeypatch):
    """The probe must follow ``search_path``, as the unqualified query does."""

    import pytest  # noqa: F401 - module keeps imports function-local
    from src.fetcher.realtime import RealtimeFetcher

    captured: dict = {}

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def execute(self, query, params=None):
            captured["query"] = query
            captured["params"] = params

        def fetchone(self):
            return (True,)

    class _Connection:
        def cursor(self):
            return _Cursor()

        def close(self):
            pass

    monkeypatch.setattr("psycopg.connect", lambda **_kwargs: _Connection(), raising=False)
    assert RealtimeFetcher._postgres_table_exists({}, "rt_ra") is True
    assert "to_regclass" in captured["query"]
    assert "information_schema" not in captured["query"]
    assert captured["params"] == ["rt_ra"]


def test_postgres_table_probe_failure_is_a_fetcher_error(monkeypatch):
    """A probe that cannot answer must not silently drop the RT_RA targets."""

    import pytest
    from src.fetcher.base import FetcherError
    from src.fetcher.realtime import RealtimeFetcher

    def _explode(**_kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("psycopg.connect", _explode, raising=False)
    with pytest.raises(FetcherError):
        RealtimeFetcher._postgres_table_exists({}, "rt_ra")
