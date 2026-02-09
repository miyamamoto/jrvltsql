"""Tests for NAR RACE -502 fallback to option=2.

NV-LinkサーバーはUmaConnでデータダウンロード未完了のスペックに対して
option=1で-502を返すことがある。この場合、option=2（差分モード）で
自動的に再試行する機能のテスト。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from src.fetcher.historical import HistoricalFetcher
from src.fetcher.base import FetcherError
from src.utils.data_source import DataSource


@pytest.fixture
def nar_fetcher():
    """NAR用HistoricalFetcherのモックを作成"""
    with patch.object(HistoricalFetcher, '__init__', lambda self, **kw: None):
        fetcher = HistoricalFetcher()
        fetcher.data_source = DataSource.NAR
        fetcher.show_progress = False
        fetcher.progress_display = None
        fetcher._skip_cleanup = False
        fetcher._nar_skipped_dates = []
        fetcher.jvlink = MagicMock()
        return fetcher


def _make_mock_fetch(behavior):
    """Create a mock fetch method based on behavior dict.

    behavior: dict mapping (date, option) -> "success" | "fail_502" | list of records
    Default: "fail_502"
    """
    def mock_fetch(data_spec, from_date, to_date, option=1):
        key = (from_date, option)
        action = behavior.get(key, "fail_502")
        if action == "fail_502":
            raise FetcherError("Download failed with status code: -502")
        elif action == "success":
            yield {"record": "data", "date": from_date}
        elif isinstance(action, list):
            yield from action
        else:
            yield action
    return mock_fetch


class TestNarOption2Fallback:
    """option=1で-502時にoption=2へフォールバックするテスト"""

    def test_fallback_to_option2_on_502(self, nar_fetcher):
        """option=1で-502 → option=2で成功するケース"""
        nar_fetcher.fetch = _make_mock_fetch({
            ("20250101", 1): "fail_502",
            ("20250101", 2): "success",
        })
        results = list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250101", 1))
        assert len(results) == 1
        assert results[0]["record"] == "data"
        assert nar_fetcher._nar_skipped_dates == []

    def test_fallback_option2_also_fails(self, nar_fetcher):
        """option=1もoption=2も-502で失敗するケース"""
        nar_fetcher.fetch = _make_mock_fetch({
            ("20250101", 1): "fail_502",
            ("20250101", 2): "fail_502",
        })
        results = list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250101", 1))
        assert len(results) == 0
        assert nar_fetcher._nar_skipped_dates == ["20250101"]

    def test_no_fallback_when_already_option2(self, nar_fetcher):
        """option=2で-502の場合、さらにフォールバックしない"""
        call_log = []

        def mock_fetch(data_spec, from_date, to_date, option=1):
            call_log.append((from_date, option))
            raise FetcherError("Download failed with status code: -502")
            yield  # noqa: make generator

        nar_fetcher.fetch = mock_fetch
        results = list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250101", 2))
        assert len(results) == 0
        assert nar_fetcher._nar_skipped_dates == ["20250101"]
        # Should only try option=2 once, no further fallback
        assert call_log == [("20250101", 2)]

    def test_consecutive_502_skip_remaining(self, nar_fetcher):
        """3日連続-502で残りをスキップ（option=2フォールバック後も失敗）"""
        nar_fetcher.fetch = _make_mock_fetch({})  # All fail with -502
        results = list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250105", 1))
        assert len(results) == 0
        # 3日連続失敗後、残り2日もスキップ
        assert len(nar_fetcher._nar_skipped_dates) == 5

    def test_successful_day_resets_consecutive_count(self, nar_fetcher):
        """成功した日で連続カウントがリセットされる"""
        nar_fetcher.fetch = _make_mock_fetch({
            ("20250101", 1): "fail_502",
            ("20250101", 2): "fail_502",
            ("20250102", 1): "success",
            ("20250103", 1): "fail_502",
            ("20250103", 2): "fail_502",
        })
        results = list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250103", 1))
        assert len(results) == 1
        assert "20250101" in nar_fetcher._nar_skipped_dates
        assert "20250102" not in nar_fetcher._nar_skipped_dates
        assert "20250103" in nar_fetcher._nar_skipped_dates

    def test_non_502_error_propagated(self, nar_fetcher):
        """-502以外のエラーはそのまま再送出される"""
        def mock_fetch(data_spec, from_date, to_date, option=1):
            raise FetcherError("Authentication failed: -100")
            yield

        nar_fetcher.fetch = mock_fetch
        with pytest.raises(FetcherError, match="-100"):
            list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250101", 1))

    def test_non_502_error_in_option2_fallback_propagated(self, nar_fetcher):
        """-502フォールバック中に-502以外のエラーが出たら再送出"""
        call_count = 0

        def mock_fetch(data_spec, from_date, to_date, option=1):
            nonlocal call_count
            call_count += 1
            if option == 1:
                raise FetcherError("Download failed with status code: -502")
            else:
                raise FetcherError("Authentication failed: -100")
            yield

        nar_fetcher.fetch = mock_fetch
        with pytest.raises(FetcherError, match="-100"):
            list(nar_fetcher._fetch_nar_daily("RACE", "20250101", "20250101", 1))


class TestNarSimpleSpecs:
    """NAR用SIMPLE_SPECSの順序テスト"""

    def test_nar_simple_specs_difn_first(self):
        """NAR_SIMPLE_SPECSでDIFNがRACEより前にある"""
        import pathlib
        quickstart_path = pathlib.Path(__file__).parent.parent / 'scripts' / 'quickstart.py'
        content = quickstart_path.read_text(encoding='utf-8')

        assert 'NAR_SIMPLE_SPECS' in content

        lines = content.split('\n')
        in_nar_specs = False
        difn_line = -1
        race_line = -1
        for i, line in enumerate(lines):
            if 'NAR_SIMPLE_SPECS' in line and '=' in line:
                in_nar_specs = True
                continue
            if in_nar_specs:
                if ']' in line and '(' not in line:
                    break
                if '"DIFN"' in line:
                    difn_line = i
                if '"RACE"' in line:
                    race_line = i

        assert difn_line > 0, "DIFN not found in NAR_SIMPLE_SPECS"
        assert race_line > 0, "RACE not found in NAR_SIMPLE_SPECS"
        assert difn_line < race_line, "DIFN should come before RACE in NAR_SIMPLE_SPECS"

    def test_nar_simple_specs_race_option2(self):
        """NAR_SIMPLE_SPECSでRACEがoption=2を使用する"""
        import pathlib
        quickstart_path = pathlib.Path(__file__).parent.parent / 'scripts' / 'quickstart.py'
        content = quickstart_path.read_text(encoding='utf-8')

        lines = content.split('\n')
        in_nar_specs = False
        for line in lines:
            if 'NAR_SIMPLE_SPECS' in line and '=' in line:
                in_nar_specs = True
                continue
            if in_nar_specs:
                if ']' in line and '(' not in line:
                    break
                if '"RACE"' in line:
                    assert ', 2)' in line or ', 2,' in line, \
                        f"RACE in NAR_SIMPLE_SPECS should use option=2, got: {line.strip()}"
                    break


class TestGetSpecsForMode:
    """_get_specs_for_modeのデータソース分岐テスト"""

    def test_get_specs_contains_nar_branch(self):
        """_get_specs_for_modeがNARデータソースを判別する"""
        import pathlib
        quickstart_path = pathlib.Path(__file__).parent.parent / 'scripts' / 'quickstart.py'
        content = quickstart_path.read_text(encoding='utf-8')

        # _get_specs_for_mode内でdata_sourceを確認してNAR_SIMPLE_SPECSを使用
        assert "data_source" in content
        assert "NAR_SIMPLE_SPECS" in content
        assert "'nar'" in content or '"nar"' in content
