"""write-through キャッシュは jv_read バッファ 1 個につき 1 回だけ書くこと.

フルストラクト系パーサは 1 バッファを多数の行へ展開し（H1: 28,955B → 1,485 行、
H6: 102,890B → 4,896 行）、その全行が同じ `_raw` を持つ。行ごとに書くと同じ
blob が行数ぶん重複する。
"""

from unittest.mock import MagicMock

import pytest

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher

H1_BYTES, H1_ROWS = 28_955, 1_485
H6_BYTES, H6_ROWS = 102_890, 4_896
JV_READ_COMPLETE = 0


def _fetcher(cache, jv_read_results) -> HistoricalFetcher:
    """JV-Link を持たない HistoricalFetcher を組み立てる."""
    f = HistoricalFetcher.__new__(HistoricalFetcher)
    f.parser_factory = MagicMock()
    f.cache_manager = cache
    f.show_progress = False
    f.progress_display = None
    f._service_key = None
    f._records_fetched = f._records_parsed = f._records_failed = 0
    f._files_processed = f._total_files = 0
    f._start_time = 0.0
    f._jvd_self_repair_attempts = f._jvd_replay_records_remaining = 0
    f._recoverable_read_errors = 0
    f._jv_open_context = f._jv_open_last_file_timestamp = f._fetch_task_id = None

    f.jvlink = MagicMock()
    f.jvlink.jv_init.return_value = None
    # (result, read_count, download_count, last_file_timestamp)
    f.jvlink.jv_open.return_value = (0, len(jv_read_results), 0, "20220110000000")
    f.jvlink.jv_read.side_effect = jv_read_results
    return f


def _row(n: int) -> dict:
    """同一バッファから展開された行（ヘッダ由来の日付は全行共通）."""
    return {"Year": "2022", "MonthDay": "0110", "SanrentanKumi": f"{n:06d}"}


def _run(fetcher) -> list:
    return list(fetcher.fetch("RACE", "20220101", "20221231", option=4))


def _written(cache) -> list:
    return [c.args[2] for c in cache.write_nl_record.call_args_list]


def _assert_cached_once(rows: int, size: int) -> None:
    buff = b"X" * size
    cache = MagicMock()
    f = _fetcher(cache, [(size, buff, "f1"), (JV_READ_COMPLETE, None, None)])
    f.parser_factory.parse.return_value = [_row(i) for i in range(rows)]

    assert len(_run(f)) == rows, "全行が呼び出し元へ渡ること"
    assert _written(cache) == [buff], (
        f"バッファ 1 個につき書き込みは 1 回（実際 {cache.write_nl_record.call_count} 回）"
    )
    assert cache.write_nl_record.call_args_list[0].args[:2] == ("RACE", "20220110")


def test_h1_full_struct_buffer_is_cached_once():
    _assert_cached_once(H1_ROWS, H1_BYTES)


def test_h6_full_struct_buffer_is_cached_once():
    _assert_cached_once(H6_ROWS, H6_BYTES)


def test_each_jv_read_buffer_is_cached_separately():
    """別バッファは別々に書かれること（重複排除しすぎていないこと）."""
    a, b = b"A" * 1000, b"B" * 1000
    cache = MagicMock()
    f = _fetcher(cache, [(1000, a, "f1"), (1000, b, "f2"), (JV_READ_COMPLETE, None, None)])
    f.parser_factory.parse.side_effect = [[_row(0), _row(1), _row(2)], [_row(3), _row(4)]]

    assert len(_run(f)) == 5
    assert _written(cache) == [a, b]


def test_single_record_parser_is_unaffected():
    """RA/SE のような 1 バッファ = 1 レコードのパーサは従来どおり."""
    buff = b"R" * 1300
    cache = MagicMock()
    f = _fetcher(cache, [(1300, buff, "f1"), (JV_READ_COMPLETE, None, None)])
    f.parser_factory.parse.return_value = _row(0)  # list ではなく単一 dict

    assert len(_run(f)) == 1
    assert _written(cache) == [buff]


def test_rows_filtered_out_by_to_date_do_not_lose_the_buffer():
    """先頭行が to_date で除外されても、そのバッファはキャッシュされること."""
    buff = b"F" * 2000
    cache = MagicMock()
    f = _fetcher(cache, [(2000, buff, "f1"), (JV_READ_COMPLETE, None, None)])
    f.parser_factory.parse.return_value = [
        {"Year": "2023", "MonthDay": "0105"},  # to_date(20221231) より後 -> 除外
        _row(1),
        _row(2),
    ]

    assert len(_run(f)) == 2, "範囲外の 1 行だけが除外されること"
    assert _written(cache) == [buff], "先頭行が除外されてもバッファは残ること"


def test_failed_stream_restores_cache_and_never_marks_complete():
    """STOP条件のピン: 失敗後にキャッシュ範囲が complete と誤記録されないこと.

    途中で JVRead が失敗したストリームは、追記済みキャッシュをチェック
    ポイントまで巻き戻し、いかなる日付にも complete マーカーを付けない。
    """
    buff = b"R" * 500
    cache = MagicMock()
    cache.checkpoint_nl.return_value = None
    f = _fetcher(cache, [(500, buff, "f1"), (-502, None, None)])
    f.parser_factory.parse.return_value = _row(0)

    with pytest.raises(FetcherError, match="-502"):
        _run(f)

    cache.mark_nl_range_complete.assert_not_called()
    cache.mark_nl_complete.assert_not_called()
    cache.restore_nl.assert_called_once_with("RACE", "20220110", None)
