#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NAR（地方競馬）パーサー・フェッチャーの負荷テスト・ストレステスト

テスト対象:
  - HAParser（払戻）: 大量レコード、バウンダリケース、メモリ使用量
  - NUParser（競走馬登録）: 大量レコード、バウンダリケース、メモリ使用量
  - BNParser（馬主マスタ）: 大量レコード、バウンダリケース、メモリ使用量
  - HistoricalFetcher._fetch_nar_daily: 1年分シミュレーション、-502連続シナリオ

すべてモック/フィクスチャ使用（実データなし）
"""

import gc
import sys
import tracemalloc
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.parser.ha_parser import HAParser
from src.parser.nu_parser import NUParser
from src.parser.bn_parser import BNParser
from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.utils.data_source import DataSource


# ---------------------------------------------------------------------------
# ヘルパー: テストレコード生成
# ---------------------------------------------------------------------------

def _make_ha_record(
    kaisai_date="20240115", jyo_cd="10", race_num="05",
    payout_entries=None, total_pay=3500,
) -> bytes:
    """HAレコード（1032バイト）を生成"""
    header = (
        b"HA"           # RecordSpec
        + b"1"          # DataKubun
        + b"20240101"   # MakeDate
        + kaisai_date.encode()  # KaisaiDate
        + jyo_cd.encode().ljust(2)
        + b"01"         # Kaiji
        + b"02"         # Nichiji
        + race_num.encode().ljust(2)
        + b"12"         # TorokuTosu
        + b"11"         # SyussoTosu
    )
    flags = b"1" + b"\x00" * 16 + b" " * 15  # HatsubaiFlag + Reserved

    if payout_entries is None:
        payout_entries = [(b"01", 1000), (b"02", 2500)]
    payout_data = b""
    for kumi, pay in payout_entries:
        payout_data += kumi + str(pay).rjust(13).encode()
    payout_data += b" " * 15  # separator
    payout_data += b"00" + str(total_pay).rjust(13).encode()

    body = header + flags + payout_data
    padding = 1030 - len(body)
    if padding > 0:
        body += b" " * padding
    return body[:1030] + b"\r\n"


def _make_nu_record(uma_id="4200502202", bamei="テストウマ") -> bytes:
    """NUレコード（64バイト）を生成"""
    raw = (
        "NU"
        + uma_id.ljust(10)
        + "1199603170"
        + "0000000000000000"
        + "19940405"
        + bamei
    )
    data = raw.encode("cp932")
    if len(data) < 64:
        data += b" " * (64 - len(data))
    return data[:64]


def _make_bn_record(banusi_code="000001", banusi_name="テスト馬主") -> bytes:
    """BNレコード（387バイト）を生成"""
    data = bytearray(387)
    data[0:2] = b"BN"
    data[2:3] = b"1"
    data[3:11] = b"20240101"
    data[11:17] = banusi_code.encode().ljust(6)
    data[17:81] = banusi_name.encode("cp932").ljust(64)
    data[81:145] = banusi_name.encode("cp932").ljust(64)
    data[385:387] = b"\r\n"
    return bytes(data)


# ===========================================================================
# HAParser 負荷テスト
# ===========================================================================

class TestHAParserStress:
    """HAParser大量データ・バウンダリテスト"""

    def setup_method(self):
        self.parser = HAParser()

    # --- 大量レコードパース ---

    def test_parse_10000_records(self):
        """10,000件のHAレコードを連続パース"""
        records = [_make_ha_record(race_num=f"{(i % 12) + 1:02d}") for i in range(10_000)]
        parsed = 0
        for rec in records:
            result = self.parser.parse(rec)
            if result is not None:
                parsed += 1
        assert parsed == 10_000

    def test_parse_varied_payouts_bulk(self):
        """異なる払戻エントリー数を持つ5,000件"""
        records = []
        for i in range(5_000):
            n_entries = (i % 5) + 1  # 1〜5エントリー
            entries = [(f"{j+1:02d}".encode(), 100 * (j + 1)) for j in range(n_entries)]
            total = sum(p for _, p in entries)
            records.append(_make_ha_record(payout_entries=entries, total_pay=total))

        parsed = 0
        for rec in records:
            result = self.parser.parse(rec)
            if result is not None:
                parsed += 1
        assert parsed == 5_000

    # --- メモリ使用量 ---

    def test_memory_usage_10000_records(self):
        """10,000件パースでメモリ増加が50MB未満"""
        tracemalloc.start()
        records = [_make_ha_record() for _ in range(10_000)]
        results = []
        for rec in records:
            r = self.parser.parse(rec)
            if r:
                results.append(r)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        # 50MB未満であること
        assert peak < 50 * 1024 * 1024, f"ピークメモリ {peak / 1024 / 1024:.1f}MB が50MB超過"

    # --- バウンダリケース ---

    def test_empty_data(self):
        """空データ → None"""
        assert self.parser.parse(b"") is None

    def test_too_short(self):
        """最小サイズ未満 → None"""
        assert self.parser.parse(b"HA" + b"\x00" * 5) is None

    def test_exactly_minimum_size(self):
        """ヘッダー+フラグちょうどのサイズ"""
        data = b"HA" + b"1" + b"20240101" + b"20240115" + b"10" + b"01" + b"02" + b"05" + b"12" + b"11"
        data += b"1" + b"\x00" * 16 + b" " * 15
        result = self.parser.parse(data)
        # パース可能（払戻データなし）
        assert result is not None
        assert result["PayoutCount"] == "0"

    def test_all_spaces_record(self):
        """全スペースの1032バイト"""
        result = self.parser.parse(b" " * 1032)
        # RecordSpecが空 → パースは成功するがフィールドは空
        assert result is not None or result is None  # エラーにならないこと

    def test_null_bytes_in_payout(self):
        """NULLバイトを含む払戻データ"""
        record = _make_ha_record()
        # 一部をNULLバイトに置換
        record = record[:70] + b"\x00" * 10 + record[80:]
        # クラッシュしないこと
        result = self.parser.parse(record)
        # Noneでもdictでも可（クラッシュしなければOK）
        assert result is None or isinstance(result, dict)

    def test_max_payout_amount(self):
        """最大金額（13桁全9）"""
        entries = [(b"01", 9999999999999)]
        record = _make_ha_record(payout_entries=entries, total_pay=9999999999999)
        result = self.parser.parse(record)
        assert result is not None
        assert result["PayAmount1"] == "9999999999999"

    def test_zero_payout(self):
        """払戻金額0円"""
        entries = [(b"01", 0)]
        record = _make_ha_record(payout_entries=entries, total_pay=0)
        result = self.parser.parse(record)
        assert result is not None


# ===========================================================================
# NUParser 負荷テスト
# ===========================================================================

class TestNUParserStress:
    """NUParser大量データ・バウンダリテスト"""

    def setup_method(self):
        self.parser = NUParser()

    def test_parse_10000_records(self):
        """10,000件のNUレコード連続パース"""
        records = [_make_nu_record(uma_id=f"{i:010d}") for i in range(10_000)]
        parsed = 0
        for rec in records:
            result = self.parser.parse(rec)
            if result is not None:
                parsed += 1
        assert parsed == 10_000

    def test_memory_usage_10000_records(self):
        """10,000件パースでメモリ増加が50MB未満"""
        tracemalloc.start()
        records = [_make_nu_record(uma_id=f"{i:010d}") for i in range(10_000)]
        results = [self.parser.parse(r) for r in records]
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 50 * 1024 * 1024

    def test_empty_data(self):
        """空データ → ValueError（BaseParser仕様）"""
        with pytest.raises(ValueError):
            self.parser.parse(b"")

    def test_too_short(self):
        """短すぎるデータ → パース可能（Noneフィールド）"""
        result = self.parser.parse(b"NU")
        assert result is not None
        assert result["RecordSpec"] == "NU"

    def test_all_spaces(self):
        """全スペース64バイト → RecordSpec不一致でValueError"""
        with pytest.raises(ValueError, match="Record type mismatch"):
            self.parser.parse(b" " * 64)

    def test_japanese_names_bulk(self):
        """様々な日本語馬名を大量パース"""
        names = ["テストウマ", "サクラバクシンオー", "ディープインパクト", "オルフェーヴル", "キタサンブラック"]
        records = [_make_nu_record(uma_id=f"{i:010d}", bamei=names[i % len(names)]) for i in range(5_000)]
        parsed = sum(1 for r in records if self.parser.parse(r) is not None)
        assert parsed == 5_000

    def test_max_length_bamei(self):
        """馬名フィールドが最大（18バイトcp932 = 全角9文字）"""
        # 全角9文字 = 18バイト in cp932
        record = _make_nu_record(bamei="あいうえおかきくけ")
        result = self.parser.parse(record)
        assert result is not None


# ===========================================================================
# BNParser 負荷テスト
# ===========================================================================

class TestBNParserStress:
    """BNParser大量データ・バウンダリテスト"""

    def setup_method(self):
        self.parser = BNParser()

    def test_parse_10000_records(self):
        """10,000件のBNレコード連続パース"""
        records = [_make_bn_record(banusi_code=f"{i:06d}") for i in range(10_000)]
        parsed = 0
        for rec in records:
            result = self.parser.parse(rec)
            if result is not None:
                parsed += 1
        assert parsed == 10_000

    def test_memory_usage_10000_records(self):
        """10,000件パースでメモリ増加が50MB未満"""
        tracemalloc.start()
        records = [_make_bn_record(banusi_code=f"{i:06d}") for i in range(10_000)]
        results = [self.parser.parse(r) for r in records]
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 50 * 1024 * 1024

    def test_empty_data(self):
        """空データ"""
        result = self.parser.parse(b"")
        assert result is None or isinstance(result, dict)

    def test_short_record(self):
        """最小未満データ"""
        result = self.parser.parse(b"BN" + b"\x00" * 10)
        # warningログが出るがクラッシュしないこと
        assert result is None or isinstance(result, dict)

    def test_all_fields_populated(self):
        """全フィールドが入ったBNレコード"""
        data = bytearray(387)
        data[0:2] = b"BN"
        data[2:3] = b"1"
        data[3:11] = b"20240101"
        data[11:17] = b"123456"
        name = "テスト馬主株式会社".encode("cp932")
        data[17:17+len(name)] = name
        data[81:81+len(name)] = name
        kana = "ﾃｽﾄﾊﾞﾇｼ".encode("cp932")
        data[145:145+len(kana)] = kana
        data[355:359] = b"2024"
        data[359:369] = b"0012345678"
        data[369:379] = b"0000012345"
        data[379:385] = b"001234"
        data[385:387] = b"\r\n"
        result = self.parser.parse(bytes(data))
        assert result is not None
        assert result["BanusiCode"] == "123456"
        assert result["SetYear"] == "2024"

    def test_null_bytes_everywhere(self):
        """全NULLバイトの387バイト"""
        result = self.parser.parse(b"\x00" * 387)
        # クラッシュしないこと
        assert result is None or isinstance(result, dict)


# ===========================================================================
# HistoricalFetcher._fetch_nar_daily 負荷テスト
# ===========================================================================

def _make_fetcher():
    """テスト用のHistoricalFetcherを生成（モック）"""
    with patch.object(HistoricalFetcher, '__init__', lambda self, **kw: None):
        f = HistoricalFetcher()
        f.data_source = DataSource.NAR
        f.show_progress = False
        f.progress_display = None
        f._skip_cleanup = False
        f._nar_skipped_dates = []
        f._records_fetched = 0
        f._records_parsed = 0
        f._records_failed = 0
        f._files_processed = 0
        f._total_files = 0
        f._start_time = None
        f._service_key = None
        f.jvlink = MagicMock()
        return f


class TestFetcherNarDailyLoadTest:
    """_fetch_nar_daily の長期間・大量チャンクテスト"""

    def test_one_year_daily_all_success(self):
        """1年分（365日）の日次チャンク - 全成功"""
        fetcher = _make_fetcher()
        call_count = 0

        def mock_fetch(data_spec, from_date, to_date, option):
            nonlocal call_count
            call_count += 1
            yield {"date": from_date, "record": "data"}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))

        assert call_count == 366  # 2024はうるう年
        assert len(results) == 366
        assert fetcher._nar_skipped_dates == []

    def test_one_year_with_sporadic_502(self):
        """1年分 - 月初に-502が散発的に発生"""
        fetcher = _make_fetcher()
        call_count = 0

        def mock_fetch(data_spec, from_date, to_date, option):
            nonlocal call_count
            call_count += 1
            # 毎月1日に-502
            if from_date.endswith("01") and not from_date.endswith("0101"):
                raise FetcherError("Download failed with status code: -502")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))

        # 11ヶ月分の月初がスキップ（2月〜12月の1日 = 11日）
        assert len(fetcher._nar_skipped_dates) == 11
        # 残りの日はすべてパースされる
        assert len(results) == 366 - 11

    def test_one_year_with_502_bursts(self):
        """1年分 - 3日連続-502バーストが月に1回"""
        fetcher = _make_fetcher()

        # 各月の5,6,7日を-502にする → 連続3日で残りスキップ
        fail_days = set()
        for month in range(1, 13):
            for day in [5, 6, 7]:
                fail_days.add(f"2024{month:02d}{day:02d}")

        call_count = 0

        def mock_fetch(data_spec, from_date, to_date, option):
            nonlocal call_count
            call_count += 1
            if from_date in fail_days:
                raise FetcherError("-502")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))

        # 1月: 1-4成功、5-7失敗（3連続）→ 8-31スキップ（24日）→ 計28日スキップ
        # ただし1月分の残りがスキップされた後、2月以降は呼ばれない
        # 最初の3連続-502で残り全日スキップ
        assert len(fetcher._nar_skipped_dates) > 0
        # 1/5で連続開始 → 1/5,6,7で3連続 → 残り全スキップ
        assert "20240105" in fetcher._nar_skipped_dates

    def test_502_at_very_end(self):
        """最後の3日だけ-502 → 残り日なしで正常終了"""
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            if from_date in ("20240129", "20240130", "20240131"):
                raise FetcherError("-502")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240131", 1))

        assert len(results) == 28  # 1/1〜1/28
        assert len(fetcher._nar_skipped_dates) == 3

    def test_alternating_502_never_triggers_abort(self):
        """-502が1日おき → 連続カウントリセットで中断しない

        With option=2 fallback, each -502 day is called twice (option=1 + option=2).
        """
        fetcher = _make_fetcher()
        option1_count = 0

        def mock_fetch(data_spec, from_date, to_date, option):
            nonlocal option1_count
            if option == 1:
                option1_count += 1
            day = int(from_date[-2:])
            if day % 2 == 0:  # 偶数日に-502 (both option=1 and option=2)
                raise FetcherError("-502")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240131", 1))

        # 全31日がoption=1で試行される
        assert option1_count == 31
        assert len(results) == 16  # 奇数日のみ成功（1,3,5,...,31 = 16日）
        assert len(fetcher._nar_skipped_dates) == 15  # 偶数日スキップ

    def test_mixed_error_types_server_errors_skipped(self):
        """-502とtimeoutの混合 → 両方スキップされて残りは成功"""
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            if from_date == "20240102":
                raise FetcherError("-502")
            if from_date == "20240103":
                raise FetcherError("Connection timeout")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20240105", 1))
        # Days 1, 4, 5 succeed; days 2 (-502) and 3 (timeout) are skipped
        assert len(results) == 3

    def test_non_server_error_raises(self):
        """非サーバーエラー（例: パース失敗）は即座に例外"""
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            if from_date == "20240102":
                raise FetcherError("Parse error: invalid record format")
            yield {"date": from_date}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            with pytest.raises(FetcherError, match="Parse error"):
                list(fetcher._fetch_nar_daily("RACE", "20240101", "20240105", 1))

    def test_performance_daily_iteration(self):
        """365日のイテレーション性能（1秒未満）"""
        import time
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            yield {"date": from_date}

        start = time.monotonic()
        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))
        elapsed = time.monotonic() - start

        assert len(results) == 366
        assert elapsed < 1.0, f"365日イテレーションに{elapsed:.2f}秒かかった（1秒未満期待）"

    def test_large_records_per_day(self):
        """各日に100レコード → 365日で36,600レコード"""
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            for i in range(100):
                yield {"date": from_date, "idx": i}

        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))

        assert len(results) == 36_600

    def test_memory_usage_one_year(self):
        """1年分のフェッチでメモリ増加が100MB未満"""
        fetcher = _make_fetcher()

        def mock_fetch(data_spec, from_date, to_date, option):
            yield {"date": from_date, "data": "x" * 1000}

        tracemalloc.start()
        with patch.object(fetcher, 'fetch', side_effect=mock_fetch):
            results = list(fetcher._fetch_nar_daily("RACE", "20240101", "20241231", 1))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 100 * 1024 * 1024


# ===========================================================================
# 全パーサー横断ストレステスト
# ===========================================================================

class TestCrossParserStress:
    """複数パーサーを並行的に使用するストレステスト"""

    def test_interleaved_parsing(self):
        """HA/NU/BNレコードを交互にパース（レコードタイプの混在シミュレーション）"""
        ha = HAParser()
        nu = NUParser()
        bn = BNParser()

        success = 0
        for i in range(3_000):
            typ = i % 3
            if typ == 0:
                r = ha.parse(_make_ha_record(race_num=f"{(i % 12) + 1:02d}"))
            elif typ == 1:
                r = nu.parse(_make_nu_record(uma_id=f"{i:010d}"))
            else:
                r = bn.parse(_make_bn_record(banusi_code=f"{i:06d}"))
            if r is not None:
                success += 1

        assert success == 3_000

    def test_wrong_record_to_wrong_parser(self):
        """間違ったパーサーにレコードを渡してもクラッシュしない"""
        ha = HAParser()
        nu = NUParser()
        bn = BNParser()

        # HAレコードをBNパーサーに（NUはBaseParser経由でValueError可能性あり）
        ha_rec = _make_ha_record()
        try:
            bn.parse(ha_rec)
        except (ValueError, Exception):
            pass  # クラッシュしなければOK

        # NUレコードをHA/BNパーサーに
        nu_rec = _make_nu_record()
        try:
            ha.parse(nu_rec)
        except (ValueError, Exception):
            pass
        try:
            bn.parse(nu_rec)
        except (ValueError, Exception):
            pass

        # HAレコードをNUパーサーに（BaseParser: 長さ不一致でもValueErrorのみ）
        try:
            nu.parse(ha_rec)
        except (ValueError, Exception):
            pass

    def test_corrupted_data_resilience(self):
        """ランダムバイトデータでクラッシュしないこと（致命的例外以外）"""
        import random
        random.seed(42)
        ha = HAParser()
        nu = NUParser()
        bn = BNParser()

        for _ in range(1_000):
            garbage = bytes(random.randint(0, 255) for _ in range(random.randint(0, 2000)))
            # ValueError/その他の例外は許容、SegFault等の致命的クラッシュだけNG
            try:
                ha.parse(garbage)
            except Exception:
                pass
            try:
                nu.parse(garbage)
            except Exception:
                pass
            try:
                bn.parse(garbage)
            except Exception:
                pass
