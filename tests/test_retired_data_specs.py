#!/usr/bin/env python
"""jrvltsql が非対応とする旧仕様 dataspec を受け付けないことのテスト。

旧名（DIFF / BLOD / SNAP / HOSE / TCOV / RCOV）と新名（DIFN / BLDN / SNPN /
HOSN / TCVN / RCVN）は別名ではない。2023-08 の JV-Data 仕様変更で桁数が変わって
おり（繁殖登録番号 8→10 / 生産者コード 6→8 / 生産者名 70→72）、旧名を要求すると
現行パーサが解釈できない別仕様のバイト列が降ってくる。旧仕様のデータは変換せず
新 dataspec で取り直す運用に決めたため、旧名は入口で拒否する。

RACE は 2023-08 の仕様変更の対象外なので、拒否対象に含めない。
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.cli.main import cli
from src.fetcher.historical import HistoricalFetcher
from src.jvlink.bridge import JVLinkBridge
from src.jvlink.constants import (
    DATA_SPEC_BLOD,
    DATA_SPEC_DIFF,
    DATA_SPEC_HOSE,
    DATA_SPEC_SNAP,
    JV_RT_ERROR,
    JVOPEN_VALID_COMBINATIONS,
    RETIRED_DATA_SPECS,
    is_retired_data_spec,
    is_valid_jvopen_combination,
    retired_data_spec_message,
    validate_jvopen_combination,
)
from src.jvlink.wrapper import JVLinkWrapper
from tests.cli_test_support import CliRunner

RETIRED = ("DIFF", "BLOD", "SNAP", "HOSE", "TCOV", "RCOV")
REPLACEMENTS = ("DIFN", "BLDN", "SNPN", "HOSN", "TCVN", "RCVN")
REPLACEMENT_OPTIONS = (
    ("DIFN", 1),
    ("BLDN", 1),
    ("SNPN", 2),
    ("HOSN", 1),
    ("TCVN", 2),
    ("RCVN", 2),
)
LEGACY_COMPATIBILITY_CONSTANTS = (
    DATA_SPEC_DIFF,
    DATA_SPEC_BLOD,
    DATA_SPEC_SNAP,
    DATA_SPEC_HOSE,
)
CURRENT_JVOPEN_BY_OPTION = {
    1: {
        "TOKU", "RACE", "SLOP", "WOOD", "YSCH", "HOYU", "COMM", "MING",
        "DIFN", "BLDN", "SNPN", "HOSN",
    },
    2: {"TOKU", "RACE", "TCVN", "RCVN", "SNPN"},
    3: {
        "TOKU", "RACE", "SLOP", "WOOD", "YSCH", "HOYU", "COMM", "MING",
        "DIFN", "BLDN", "SNPN", "HOSN",
    },
    4: {
        "TOKU", "RACE", "SLOP", "WOOD", "YSCH", "HOYU", "COMM", "MING",
        "DIFN", "BLDN", "SNPN", "HOSN",
    },
}
INVALID_JVOPEN_REQUESTS = ("O1", "RACEDIFF")
VALID_JVOPEN_REQUESTS = REPLACEMENT_OPTIONS + (("RACEDIFN", 1), ("RACESNPN", 2))


class TestRetiredDataSpecTable:
    @pytest.mark.parametrize("data_spec", LEGACY_COMPATIBILITY_CONSTANTS)
    def test_deprecated_public_constants_remain_importable_but_invalid(self, data_spec):
        assert data_spec in RETIRED_DATA_SPECS
        for option in (1, 2, 3, 4):
            assert is_valid_jvopen_combination(data_spec, option) is False

    def test_retired_specs_map_to_their_replacements(self):
        assert RETIRED_DATA_SPECS == {
            "DIFF": "DIFN",
            "BLOD": "BLDN",
            "SNAP": "SNPN",
            "HOSE": "HOSN",
            "TCOV": "TCVN",
            "RCOV": "RCVN",
        }

    @pytest.mark.parametrize("data_spec", RETIRED + ("DIFFRACE", "RACEDIFF"))
    def test_retired_specs_are_recognized(self, data_spec):
        assert is_retired_data_spec(data_spec) is True

    @pytest.mark.parametrize("data_spec", REPLACEMENTS + ("RACE", "TOKU", "YSCH"))
    def test_current_specs_are_not_retired(self, data_spec):
        assert is_retired_data_spec(data_spec) is False

    def test_race_is_not_retired(self):
        # RACE は 2023-08 の桁数変更の対象外。拒否は 6 つに限る。
        assert "RACE" not in RETIRED_DATA_SPECS
        assert len(RETIRED_DATA_SPECS) == 6

    @pytest.mark.parametrize("data_spec", ("diff", "Diff", "bLoD", "snap", "hose"))
    def test_lowercase_spellings_are_also_retired(self, data_spec):
        # CacheManager は spec.upper() でディレクトリを引くので、小文字で渡しても
        # 同じ nl/DIFF/ を読める。大小を区別すると拒否をすり抜けてしまう。
        assert is_retired_data_spec(data_spec) is True
        assert RETIRED_DATA_SPECS[data_spec.upper()] in retired_data_spec_message(data_spec)


class TestJVOpenCombinations:
    def test_allowlist_is_the_current_official_dataspec_matrix(self):
        assert {
            option: set(data_specs)
            for option, data_specs in JVOPEN_VALID_COMBINATIONS.items()
        } == CURRENT_JVOPEN_BY_OPTION

    @pytest.mark.parametrize("option", sorted(JVOPEN_VALID_COMBINATIONS))
    def test_no_option_accepts_a_retired_spec(self, option):
        accepted = set(JVOPEN_VALID_COMBINATIONS[option])
        assert accepted.isdisjoint(RETIRED_DATA_SPECS)

    @pytest.mark.parametrize("data_spec", RETIRED)
    @pytest.mark.parametrize("option", (1, 2, 3, 4))
    def test_is_valid_jvopen_combination_rejects_retired(self, data_spec, option):
        assert is_valid_jvopen_combination(data_spec, option) is False

    @pytest.mark.parametrize("data_spec", ("DIFN", "BLDN", "SNPN", "HOSN"))
    @pytest.mark.parametrize("option", (1, 3, 4))
    def test_replacements_remain_valid_for_accumulated_options(self, data_spec, option):
        assert is_valid_jvopen_combination(data_spec, option) is True

    @pytest.mark.parametrize("data_spec", ("SNPN", "TCVN", "RCVN"))
    def test_change_specs_remain_valid_for_option_2(self, data_spec):
        assert is_valid_jvopen_combination(data_spec, 2) is True

    @pytest.mark.parametrize("option", (1, 2, 3, 4))
    def test_race_still_passes_on_every_option(self, option):
        assert is_valid_jvopen_combination("RACE", option) is True

    @pytest.mark.parametrize(
        "data_spec,option",
        (("RACEDIFN", 1), ("RACESNPN", 2), ("RACEDIFN", 3), ("RACEDIFN", 4)),
    )
    def test_concatenated_current_dataspecs_are_valid(self, data_spec, option):
        assert is_valid_jvopen_combination(data_spec, option) is True

    def test_validator_rejects_unhashable_option_without_crashing(self):
        with pytest.raises(ValueError, match="option"):
            validate_jvopen_combination("RACE", [])


class TestRejectionMessage:
    @pytest.mark.parametrize("data_spec,replacement", list(zip(RETIRED, REPLACEMENTS, strict=True)))
    def test_message_names_the_replacement_and_when_it_changed(self, data_spec, replacement):
        message = retired_data_spec_message(data_spec)
        assert data_spec in message
        assert replacement in message
        assert "2023-08" in message

    def test_message_rejects_non_retired_spec(self):
        with pytest.raises(ValueError):
            retired_data_spec_message("RACE")

    def test_constants_no_longer_claim_the_names_are_aliases(self):
        # 受け入れ条件: constants.py から「別名 / equivalent」という宣言が消えている
        # こと。旧名は新名の別表記ではないので、そう読める記述を残さない。
        source = (Path(__file__).resolve().parents[1] / "src/jvlink/constants.py").read_text(
            encoding="utf-8"
        )
        for claim in (
            "are aliases",
            "are equivalent",
            "(DIFF の別名)",
            "(BLOD の別名)",
            "(HOSE の別名)",
        ):
            assert claim not in source, f"constants.py still claims {claim!r}"


class TestFetcherRejectsBeforeReachingJVLink:
    """取得器は生成器なので、例外は最初の反復で出る。

    JVOpen に到達しないことが要点で、送出のタイミングは問わない。
    """

    def _fetcher(self):
        # JVLinkWrapper は Windows COM を掴むので、__init__ を通さずに組み立てる
        # (tests/test_jvd_self_repair.py と同じ方式)。
        fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
        fetcher.jvlink = MagicMock()
        fetcher.jvlink.jv_init.return_value = 0
        fetcher.jvlink.jv_open.return_value = (JV_RT_ERROR, 0, 0, "")  # -1 = 該当データ無し
        fetcher.parser_factory = MagicMock()
        fetcher.show_progress = False
        fetcher.progress_display = None
        fetcher.cache_manager = None
        fetcher._fetch_task_id = None
        fetcher._jvd_self_repair_attempts = 0
        fetcher._jvd_replay_records_remaining = 0
        fetcher._jv_open_context = None
        fetcher._jv_open_last_file_timestamp = None
        return fetcher

    @pytest.mark.parametrize("data_spec", RETIRED)
    def test_fetch_never_reaches_jvopen(self, data_spec):
        fetcher = self._fetcher()

        with pytest.raises(ValueError) as excinfo:
            list(fetcher.fetch(data_spec, "20240101", "20241231", option=1))

        assert data_spec in str(excinfo.value)
        assert RETIRED_DATA_SPECS[data_spec] in str(excinfo.value)
        fetcher.jvlink.jv_init.assert_not_called()
        fetcher.jvlink.jv_open.assert_not_called()

    @pytest.mark.parametrize("data_spec", INVALID_JVOPEN_REQUESTS)
    def test_fetch_rejects_invalid_or_mixed_requests_before_jvlink(self, data_spec):
        fetcher = self._fetcher()

        with pytest.raises(ValueError):
            list(fetcher.fetch(data_spec, "20240101", "20241231", option=1))

        fetcher.jvlink.jv_init.assert_not_called()
        fetcher.jvlink.jv_open.assert_not_called()

    def test_fetch_still_opens_the_stream_for_the_replacement(self):
        fetcher = self._fetcher()

        assert list(fetcher.fetch("DIFN", "20240101", "20241231")) == []

        fetcher.jvlink.jv_open.assert_called_once()
        assert fetcher.jvlink.jv_open.call_args.args[0] == "DIFN"

    @pytest.mark.parametrize("data_spec", RETIRED)
    def test_fetch_with_cache_rejects_before_reading_the_cache(self, data_spec):
        # キャッシュヒット時は fetch() を通らないので、こちらにも入口が要る。
        fetcher = self._fetcher()
        cache_manager = MagicMock()

        with pytest.raises(ValueError) as excinfo:
            list(fetcher.fetch_with_cache(cache_manager, data_spec, "20240101", "20241231"))

        assert RETIRED_DATA_SPECS[data_spec] in str(excinfo.value)
        cache_manager.has_nl_range.assert_not_called()
        cache_manager.read_nl.assert_not_called()

    def test_fetch_with_cache_rejects_a_lowercase_retired_spec(self):
        # CacheManager が spec.upper() で引く以上、小文字でも同じ旧仕様の
        # キャッシュに到達できてしまう。
        fetcher = self._fetcher()
        cache_manager = MagicMock()

        with pytest.raises(ValueError):
            list(fetcher.fetch_with_cache(cache_manager, "diff", "20240101", "20241231"))

        cache_manager.has_nl_range.assert_not_called()

    def test_fetch_with_cache_still_serves_the_replacement(self):
        fetcher = self._fetcher()
        cache_manager = MagicMock()
        cache_manager.has_nl_range.return_value = False

        assert list(fetcher.fetch_with_cache(cache_manager, "DIFN", "20240101", "20241231")) == []

        fetcher.jvlink.jv_open.assert_called_once()

    @pytest.mark.parametrize("data_spec", RETIRED)
    def test_fetch_with_date_range_never_reaches_jvopen(self, data_spec):
        fetcher = self._fetcher()
        start, end = datetime(2024, 1, 1), datetime(2024, 12, 31)

        with pytest.raises(ValueError):
            list(fetcher.fetch_with_date_range(data_spec, start, end))

        fetcher.jvlink.jv_open.assert_not_called()

    def test_fetch_with_date_range_still_opens_the_stream_for_the_replacement(self):
        fetcher = self._fetcher()
        start, end = datetime(2024, 1, 1), datetime(2024, 12, 31)

        assert list(fetcher.fetch_with_date_range("DIFN", start, end, option=3)) == []

        fetcher.jvlink.jv_open.assert_called_once()
        assert fetcher.jvlink.jv_open.call_args.args[0] == "DIFN"


class TestWrapperRejectsBeforeCOM:
    """公開 JVLinkWrapper.jv_open の直接呼び出しでも COM の JVOpen 前に弾く。

    fetcher を経由しない直接利用者が旧 dataspec で JVOpen へ到達できると、
    fail-closed の境界が破れる。
    """

    def _wrapper(self):
        # JVLinkWrapper は __init__ で Windows COM を掴むので、__new__ で迂回して
        # COM オブジェクトだけを差し替える (TestFetcherRejectsBeforeReachingJVLink
        # と同じ方式)。JVOpen には正常応答を仕込み、拒否が実装より手前で起きた
        # ことを「呼ばれていない」で判定できるようにする。
        wrapper = JVLinkWrapper.__new__(JVLinkWrapper)
        wrapper.sid = "TEST"
        wrapper._jvlink = MagicMock()
        wrapper._jvlink.JVOpen.return_value = (0, 100, 0, "20241231235959")
        wrapper._is_open = False
        wrapper._com_initialized = False
        return wrapper

    @pytest.mark.parametrize("data_spec", RETIRED + ("diff",))
    def test_jv_open_never_calls_com_jvopen(self, data_spec):
        wrapper = self._wrapper()

        with pytest.raises(ValueError) as excinfo:
            wrapper.jv_open(data_spec, "20240101000000", option=1)

        assert RETIRED_DATA_SPECS[data_spec.upper()] in str(excinfo.value)
        assert "2023-08" in str(excinfo.value)
        wrapper._jvlink.JVOpen.assert_not_called()
        assert wrapper.is_open() is False

    @pytest.mark.parametrize("data_spec", INVALID_JVOPEN_REQUESTS)
    def test_jv_open_rejects_invalid_or_mixed_requests_before_com(self, data_spec):
        wrapper = self._wrapper()

        with pytest.raises(ValueError):
            wrapper.jv_open(data_spec, "20240101000000", option=1)

        wrapper._jvlink.JVOpen.assert_not_called()
        assert wrapper.is_open() is False

    @pytest.mark.parametrize("data_spec,option", VALID_JVOPEN_REQUESTS)
    def test_jv_open_still_reaches_com_for_the_replacement(self, data_spec, option):
        wrapper = self._wrapper()

        result, read_count, _, _ = wrapper.jv_open(
            data_spec, "20240101000000", option=option
        )

        assert (result, read_count) == (0, 100)
        wrapper._jvlink.JVOpen.assert_called_once_with(
            data_spec, "20240101000000", option, 0, 0, ""
        )


class TestBridgeRejectsBeforeTransmission:
    """公開 JVLinkBridge.jv_open の直接呼び出しでもブリッジ送信前に弾く。"""

    def _bridge(self):
        # ブリッジ実行ファイルもサブプロセスも不要。__new__ で迂回して送信層だけ
        # を差し替え、正常応答を仕込む (wrapper 側と同じ判定方式)。
        bridge = JVLinkBridge.__new__(JVLinkBridge)
        bridge.sid = "TEST"
        bridge._send_command = MagicMock(
            return_value={
                "status": "ok",
                "code": 0,
                "readcount": 100,
                "downloadcount": 5,
                "lastfiletimestamp": "20241231235959",
            }
        )
        bridge._is_open = False
        return bridge

    @pytest.mark.parametrize("data_spec", RETIRED + ("diff",))
    def test_jv_open_never_transmits_a_bridge_command(self, data_spec):
        bridge = self._bridge()

        with pytest.raises(ValueError) as excinfo:
            bridge.jv_open(data_spec, "20240101000000", option=1)

        assert RETIRED_DATA_SPECS[data_spec.upper()] in str(excinfo.value)
        assert "2023-08" in str(excinfo.value)
        bridge._send_command.assert_not_called()
        assert bridge.is_open() is False

    @pytest.mark.parametrize("data_spec", INVALID_JVOPEN_REQUESTS)
    def test_jv_open_rejects_invalid_or_mixed_requests_before_transmission(self, data_spec):
        bridge = self._bridge()

        with pytest.raises(ValueError):
            bridge.jv_open(data_spec, "20240101000000", option=1)

        bridge._send_command.assert_not_called()
        assert bridge.is_open() is False

    @pytest.mark.parametrize("data_spec,option", VALID_JVOPEN_REQUESTS)
    def test_jv_open_still_transmits_for_the_replacement(self, data_spec, option):
        bridge = self._bridge()

        code, read_count, download_count, _ = bridge.jv_open(
            data_spec, "20240101000000", option=option
        )

        assert (code, read_count, download_count) == (0, 100, 5)
        bridge._send_command.assert_called_once()
        assert bridge._send_command.call_args.args[0]["dataspec"] == data_spec


# ルートコールバックは設定ファイルを前提条件とする（無ければ init 以外は終了）。
# サブコマンドのガードまで到達させるため、検証 (_validate_config) を満たす最小の
# 設定を書いて --config で渡す。auto_update_check は無効にして外部照会を避ける。
MINIMAL_CLI_CONFIG = """\
jvlink: {}
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: test.db
auto_update_check: false
"""


def _invoke_cli_with_config(args):
    """Invoke the real root command with a minimal temporary config."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        config_path = Path("config.yaml")
        config_path.write_text(MINIMAL_CLI_CONFIG, encoding="utf-8")
        return runner.invoke(cli, ["--config", str(config_path), *args])


class TestCLIRejectsRetiredSpecs:
    @pytest.mark.parametrize("data_spec,replacement", list(zip(RETIRED, REPLACEMENTS, strict=True)))
    def test_fetch_command_reports_why(self, data_spec, replacement):
        result = _invoke_cli_with_config(
            ["fetch", "--from", "20240101", "--to", "20241231",
             "--spec", data_spec, "--db", "sqlite"],
        )

        assert result.exit_code != 0
        assert "2023-08" in result.output
        assert replacement in result.output

    def test_cache_build_command_reports_why(self):
        result = _invoke_cli_with_config(
            ["cache", "build", "--spec", "DIFF",
             "--from", "20240101", "--to", "20241231"],
        )

        assert result.exit_code != 0
        assert "2023-08" in result.output
        assert "DIFN" in result.output

    def test_cache_build_command_rejects_a_lowercase_retired_spec(self):
        result = _invoke_cli_with_config(
            ["cache", "build", "--spec", "diff",
             "--from", "20240101", "--to", "20241231"],
        )

        assert result.exit_code != 0
        assert "DIFN" in result.output

    def test_cache_rebuild_rejects_before_deleting_existing_cache(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(MINIMAL_CLI_CONFIG, encoding="utf-8")
            cache_file = Path("cache/nl/DIFF/20240101.v2.bin")
            cache_file.parent.mkdir(parents=True)
            cache_file.write_bytes(b"existing-cache")

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_path),
                    "cache", "rebuild", "--spec", "DIFF",
                    "--from", "20240101", "--to", "20240101",
                    "--cache-dir", "cache",
                ],
            )

            assert result.exit_code != 0
            assert "2023-08" in result.output
            assert "DIFN" in result.output
            assert cache_file.read_bytes() == b"existing-cache"

    @pytest.mark.parametrize("command", ("build", "rebuild"))
    def test_cache_commands_reject_record_type_before_cache_access(self, command):
        from src.cache import CacheManager

        runner = CliRunner()
        with runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(MINIMAL_CLI_CONFIG, encoding="utf-8")
            manager = CacheManager(Path("cache"))
            manager.write_nl_record("O1", "20240101", b"existing-cache")
            manager.mark_nl_complete("O1", "20240101")

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_path),
                    "cache", command, "--spec", "O1",
                    "--from", "20240101", "--to", "20240101",
                    "--cache-dir", "cache",
                ],
            )

            assert result.exit_code != 0
            assert manager.has_nl_range("O1", "20240101", "20240101") is True
            assert list(manager.read_nl("O1", "20240101", "20240101")) == [
                b"existing-cache"
            ]
