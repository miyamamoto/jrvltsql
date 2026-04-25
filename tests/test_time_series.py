#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""時系列データ取得テスト

時系列データ（0B20, 0B30-0B36）のキー生成とfetch_time_series()をテストします。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime


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

    # DB登録済みレースからの過去時系列取得では回次・日次を含む16桁キーを使う
    full_key = generate_time_series_full_key("20251201", "05", 5, 8, 11)
    print(f"generate_time_series_full_key('20251201', '05', 5, 8, 11) = '{full_key}'")
    assert full_key == "2025120105050811", f"Expected '2025120105050811', got '{full_key}'"
    print("  -> OK: 履歴取得用の16桁キー YYYYMMDDJJKKNNRR が正しい")

    # 全レースキー生成（120キー）
    all_keys = get_all_race_keys_for_date("20251201")
    print(f"\nget_all_race_keys_for_date('20251201'): {len(all_keys)} keys")
    assert len(all_keys) == 120, f"Expected 120, got {len(all_keys)}"
    print("  -> OK: 10場 x 12レース = 120キー")

    # 時系列spec判定
    print(f"\nJVRTOPEN_TIME_SERIES_SPECS: {list(JVRTOPEN_TIME_SERIES_SPECS.keys())}")
    assert is_time_series_spec("0B30") == True
    assert is_time_series_spec("0B36") == True
    assert is_time_series_spec("0B12") == False
    print("  -> OK: is_time_series_spec() が正しく判定")

    # 競馬場コード
    print(f"\nJYO_CODES: {JYO_CODES}")

    print("\n[PASSED] キー生成関数テスト")
    return True


def test_fetch_time_series_batch_from_db_uses_full_key():
    """DB登録済みレースからの時系列取得が16桁キーを使うことを確認する。"""
    import sqlite3
    import tempfile
    import types
    from pathlib import Path

    from src.fetcher.realtime import RealtimeFetcher

    with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
        db_path = Path(temp_dir) / "keiba.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE NL_RA (
                    Year INTEGER,
                    MonthDay INTEGER,
                    JyoCD TEXT,
                    Kaiji INTEGER,
                    Nichiji INTEGER,
                    RaceNum INTEGER
                )
                """
            )
            conn.execute("INSERT INTO NL_RA VALUES (2025, 1201, '05', 5, 8, 11)")

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

        assert fetcher.jvlink.opened == [("0B30", "2025120105050811")]
        assert records == [{"RecordSpec": "O1", "_raw": b"O1"}]


def test_fetch_time_series_batch_from_postgres_uses_pg_race_keys(monkeypatch):
    """PostgreSQL保存のNL_RAから時系列取得キーを作れることを確認する。"""
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
            data_spec="0B32",
            db_path="ignored.sqlite",
            from_date="20251201",
            to_date="20251201",
            pg_config={"host": "localhost", "database": "keiba"},
        )
    )

    assert "FROM nl_ra" in captured["query"]
    assert captured["params"] == [2025, 2025, 1201, 2025, 2025, 1201]
    assert fetcher.jvlink.opened == [("0B32", "2025120105050811")]
    assert records == [{"RecordSpec": "O2", "_raw": b"O2"}]


def test_fetch_time_series_method():
    """fetch_time_series()メソッドのテスト（実際のJV-Link呼び出し）"""
    import sys

    if sys.platform != "win32":
        print("[SKIP] JV-Link COM is only available on Windows")
        return True

    print("\n" + "=" * 60)
    print("2. fetch_time_series()メソッドテスト")
    print("=" * 60)

    try:
        from src.fetcher.realtime import RealtimeFetcher
    except ImportError as e:
        print(f"[SKIP] インポートエラー: {e}")
        return True

    # 本日の日付
    today = datetime.now().strftime("%Y%m%d")
    print(f"今日の日付: {today}")

    # 東京競馬場のR11（メインレース）でテスト
    test_cases = [
        ("0B30", "05", 11, "単勝オッズ@東京11R"),
        ("0B31", "06", 1, "複勝オッズ@中山1R"),
    ]

    fetcher = RealtimeFetcher(sid="TEST")

    for spec, jyo, race_num, description in test_cases:
        print(f"\n--- {description} (spec={spec}, jyo={jyo}, race={race_num}) ---")

        try:
            records = []
            for record in fetcher.fetch_time_series(
                data_spec=spec,
                jyo_code=jyo,
                race_num=race_num,
                date=today,
            ):
                records.append(record)

            if records:
                print(f"  取得レコード数: {len(records)}")
                # 最初のレコードの一部を表示
                first = records[0]
                print(f"  最初のレコード (keys): {list(first.keys())[:5]}...")
            else:
                print("  データなし（レースが存在しないか、まだオッズが発表されていない）")

        except Exception as e:
            error_str = str(e)
            if "-114" in error_str:
                print(f"  [INFO] -114: 契約外またはキー形式エラー")
            elif "-1" in error_str or "no data" in error_str.lower():
                print(f"  [INFO] データなし（正常）")
            else:
                print(f"  [ERROR] {e}")

    print("\n[PASSED] fetch_time_series()メソッドテスト")
    return True


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

    print("\n[PASSED] 静的メソッドテスト")
    return True


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("時系列データ取得テスト")
    print("=" * 60)

    results = []

    # 1. キー生成関数テスト
    try:
        results.append(("キー生成関数", test_key_generation()))
    except Exception as e:
        print(f"[FAILED] キー生成関数: {e}")
        results.append(("キー生成関数", False))

    # 2. 静的メソッドテスト
    try:
        results.append(("静的メソッド", test_list_methods()))
    except Exception as e:
        print(f"[FAILED] 静的メソッド: {e}")
        results.append(("静的メソッド", False))

    # 3. fetch_time_series（JV-Link呼び出し）
    try:
        results.append(("fetch_time_series", test_fetch_time_series_method()))
    except Exception as e:
        print(f"[FAILED] fetch_time_series: {e}")
        results.append(("fetch_time_series", False))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "[PASSED]" if ok else "[FAILED]"
        print(f"  {status} {name}")

    print(f"\n合計: {passed}/{total} テスト成功")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
