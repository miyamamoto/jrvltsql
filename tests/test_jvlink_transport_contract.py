"""Platform-neutral tests for the official JV-Link transport contract.

These tests deliberately bypass ``JVLinkWrapper.__init__`` so that the COM
call shape and state machine are checked on Linux as well as Windows.  The
fakes use fixed Python signatures: omitting an official in/out argument is a
test failure instead of being hidden by ``MagicMock``.
"""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.jvlink.bridge import JVLinkBridge, JVLinkBridgeError
from src.jvlink.wrapper import JVLinkError, JVLinkWrapper


def test_github_actions_executes_entire_deterministic_suite():
    workflow = Path(".github/workflows/test.yml").read_text(encoding="utf-8")
    assert "pytest tests \\" in workflow
    assert "--ignore=tests/integration" in workflow
    assert "--ignore=tests/e2e" in workflow
    assert "--ignore=tests/test_jvlink_transport_contract.py" not in workflow


def _wrapper(com, *, is_open=False):
    wrapper = JVLinkWrapper.__new__(JVLinkWrapper)
    wrapper.sid = "TEST"
    wrapper._jvlink = com
    wrapper._is_open = is_open
    wrapper._com_initialized = False
    return wrapper


def _historical_fetcher(jvlink):
    with (
        patch("src.jvlink.bridge.find_bridge_executable", return_value=None),
        patch("src.fetcher.base.JVLinkWrapper", return_value=jvlink),
    ):
        return HistoricalFetcher(sid="TEST", show_progress=False)


class SixArgumentOpenCom:
    def __init__(self, result=(0, 7, 3, "20260815000000")):
        self.result = result
        self.calls = []

    def JVOpen(
        self,
        data_spec,
        fromtime,
        option,
        read_count,
        download_count,
        last_file_timestamp,
    ):
        self.calls.append(
            (
                data_spec,
                fromtime,
                option,
                read_count,
                download_count,
                last_file_timestamp,
            )
        )
        return self.result


class ThreeArgumentGetsCom:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def JVGets(self, buff, size, filename):
        self.calls.append((buff, size, filename))
        return self.result


def test_native_jvopen_supplies_all_six_official_arguments():
    com = SixArgumentOpenCom()
    wrapper = _wrapper(com)

    assert wrapper.jv_open("RACE", "20260815000000", 1) == com.result
    assert com.calls == [
        ("RACE", "20260815000000", 1, 0, 0, ""),
    ]
    assert wrapper.is_open() is True


def test_open_rejects_an_undefined_positive_result_code():
    wrapper = _wrapper(SixArgumentOpenCom((1, 7, 0, "20260815000000")))
    with pytest.raises(JVLinkError, match="JVOpen"):
        wrapper.jv_open("RACE", "20260815000000", 1)

    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(
        return_value={
            "status": "ok",
            "code": 1,
            "readcount": 7,
            "downloadcount": 0,
            "lastfiletimestamp": "20260815000000",
        }
    )
    with pytest.raises(JVLinkBridgeError, match="JVOpen"):
        bridge.jv_open("RACE", "20260815000000", 1)


def test_open_rejects_impossible_counts_and_keeps_close_pending():
    wrapper = _wrapper(SixArgumentOpenCom((0, 1, 2, "20260815000000")))
    with pytest.raises(JVLinkError, match="download|count"):
        wrapper.jv_open("RACE", "20260815000000", 1)
    assert wrapper._needs_close is True

    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(
        return_value={
            "status": "ok",
            "code": 0,
            "readcount": 1,
            "downloadcount": 2,
            "lastfiletimestamp": "20260815000000",
        }
    )
    with pytest.raises(JVLinkBridgeError, match="download|count"):
        bridge.jv_open("RACE", "20260815000000", 1)
    assert bridge._needs_close is True


def test_native_malformed_success_response_keeps_close_pending():
    wrapper = _wrapper(SixArgumentOpenCom((0, 1, 0)))

    with pytest.raises(JVLinkError, match="tuple length|return"):
        wrapper.jv_open("RACE", "20260815000000", 1)

    assert wrapper._needs_close is True


@pytest.mark.parametrize("result_code", [-1, -2])
def test_native_jvopen_non_success_does_not_expose_a_readable_stream(result_code):
    com = SixArgumentOpenCom((result_code, 0, 0, ""))
    wrapper = _wrapper(com)

    assert wrapper.jv_open("RACE", "20260815000000", 3)[0] == result_code
    assert wrapper.is_open() is False
    assert wrapper._needs_close is True


def test_historical_fetcher_reports_setup_cancel_instead_of_no_data():
    jvlink = MagicMock()
    jvlink.jv_init.return_value = 0
    jvlink.jv_open.return_value = (-2, 0, 0, "")
    fetcher = _historical_fetcher(jvlink)

    with pytest.raises(FetcherError, match="cancel"):
        list(fetcher.fetch("RACE", "20260815", "20260815", option=3))

    jvlink.jv_close.assert_called_once()


# --- Official JVOpen semantics (JV-Link仕様書 4.9.0.1 p.17-20) --------------
# fromtime は「開始時刻のみ」または「開始-終了」(YYYYMMDDhhmmss-YYYYMMDDhhmmss、
# 半角ハイフン結合) の2形式で、対象条件は「開始時刻より大きく、終了時刻まで」。
# 終了時刻は setup (option 3/4) でもセットアップ用アーカイブを期間で絞る
# (2026-08-23 実機計測: --from 1986 固定で終了時刻だけを振ると readcount が
# 3,973 / 4,337 と変わる)。1 read の費用は JVOpen が並べた対象ファイル数で
# 決まるので、範囲形式を使える dataspec は暦年で刻む。
# 刻めるのは RANGE_FROMTIME_DATA_SPECS だけ。p.18 の終了時刻禁止リスト
# (TOKU / DIFF・DIFN / HOSE・HOSN / HOYU / COMM) は開始のみで1回開く。
# 要求された from_date を包含させるため、setup の排他的開始点は前日23:59:59。
# option 1 の差分カーソルと option 2 の今週データ契約は変更しない。


@pytest.mark.parametrize(
    ("data_spec", "option", "expected_fromtimes"),
    [
        # 範囲形式を使える dataspec は暦年で刻む。2025-08-20〜2026-08-19 は 2 年に
        # またがるので JVOpen は 2 回。境界は共有し、穴も重複も作らない。
        (
            "RACE",
            4,
            ["20250819235959-20251231235959", "20251231235959-20260819235959"],
        ),
        (
            "RACE",
            3,
            ["20250819235959-20251231235959", "20251231235959-20260819235959"],
        ),
        # p.18 の終了時刻禁止リストに載る DIFN は開始のみで 1 回
        ("DIFN", 4, ["20250819235959"]),
        # 連結された dataspec も許可リストに一致しないので開始のみ
        ("RACEDIFN", 4, ["20250819235959"]),
        # option=1 の差分カーソルは真夜中のまま。刻んでも先頭はずらさない。
        (
            "RACE",
            1,
            ["20250820000000-20251231235959", "20251231235959-20260819235959"],
        ),
    ],
)
def test_jvopen_fromtime_is_chunked_by_calendar_year_where_the_spec_allows_it(
    data_spec, option, expected_fromtimes
):
    jvlink = MagicMock()
    jvlink.jv_open.return_value = (-1, 0, 0, "")
    fetcher = _historical_fetcher(jvlink)

    assert list(fetcher.fetch(data_spec, "20250820", "20260819", option=option)) == []

    assert [c.args[1] for c in jvlink.jv_open.call_args_list] == expected_fromtimes
    assert all(c.args[0] == data_spec and c.args[2] == option
               for c in jvlink.jv_open.call_args_list)


def test_setup_end_point_follows_the_requested_to_date():
    """to_date を変えると JVOpen へ渡る終了点も変わること。

    終了時刻は setup アーカイブを期間で絞るので、要求の終端がそのまま
    最後の chunk の終了点になる。
    """
    jvlink = MagicMock()
    jvlink.jv_open.return_value = (-1, 0, 0, "")
    fetcher = _historical_fetcher(jvlink)

    list(fetcher.fetch("RACE", "20240820", "20241231", option=4))
    list(fetcher.fetch("RACE", "20240820", "20250615", option=4))

    assert [c.args[1] for c in jvlink.jv_open.call_args_list] == [
        "20240819235959-20241231235959",
        "20240819235959-20241231235959",
        "20241231235959-20250615235959",
    ]


@pytest.mark.parametrize(
    ("bad_from", "bad_to"),
    [
        ("2025-08-20", "20260819"),  # 区切り文字入り
        ("20250820", "2026-08-19"),  # 区切り文字入り
        ("20250820", "20260832"),    # 実在しない暦日
        ("", "20260819"),            # 欠落
        (None, "20260819"),          # 欠落
        ("20260819", "20250820"),    # 逆転した範囲
    ],
)
def test_invalid_or_inverted_dates_fail_before_any_jvlink_call(bad_from, bad_to):
    jvlink = MagicMock()
    jvlink.jv_open.return_value = (-1, 0, 0, "")
    fetcher = _historical_fetcher(jvlink)

    with pytest.raises(ValueError):
        list(fetcher.fetch("RACE", bad_from, bad_to, option=4))

    jvlink.jv_init.assert_not_called()
    jvlink.jv_open.assert_not_called()


def test_inverted_cache_range_fails_before_cache_lookup_or_jvlink_call():
    cache = MagicMock()
    jvlink = MagicMock()
    fetcher = _historical_fetcher(jvlink)

    with pytest.raises(ValueError):
        list(fetcher.fetch_with_cache(cache, "RACE", "20260819", "20250820", 4))

    cache.has_nl_range.assert_not_called()
    cache.read_nl.assert_not_called()
    jvlink.jv_init.assert_not_called()
    jvlink.jv_open.assert_not_called()


def test_native_jvgets_uses_byte_array_size_and_filename_arguments():
    com = ThreeArgumentGetsCom((4, memoryview(b"ABCD"), "RACE.jvd"))
    wrapper = _wrapper(com, is_open=True)

    assert wrapper.jv_gets() == (4, b"ABCD")
    assert len(com.calls) == 1
    buff, size, filename = com.calls[0]
    assert isinstance(buff, bytearray)
    assert size > 4
    assert isinstance(filename, bytearray)


def test_native_jvread_uses_stable_pywin32_dummy_buffers():
    com = MagicMock()
    com.JVRead.return_value = (0, "", 0, "")
    wrapper = _wrapper(com, is_open=True)

    assert wrapper.jv_read() == (0, None, None)
    buff, size, filename = com.JVRead.call_args.args
    assert isinstance(buff, bytearray)
    assert size > 0
    assert isinstance(filename, bytearray)


def test_native_jvread_and_jvgets_propagate_downloading_status():
    read_com = MagicMock()
    read_com.JVRead.return_value = (-3, "", 0, "RACE.jvd")
    assert _wrapper(read_com, is_open=True).jv_read() == (-3, None, "RACE.jvd")

    gets_com = ThreeArgumentGetsCom((-3, memoryview(b""), "RACE.jvd"))
    assert _wrapper(gets_com, is_open=True).jv_gets() == (-3, None)


def test_fetcher_waits_and_resumes_after_downloading_status():
    jvlink = MagicMock()
    jvlink.jv_read.side_effect = [(-3, None, "RACE.jvd"), (0, None, None)]
    fetcher = _historical_fetcher(jvlink)

    with patch("src.fetcher.base.time.sleep") as sleep:
        assert list(fetcher._fetch_and_parse()) == []

    sleep.assert_called_once()
    assert jvlink.jv_read.call_count == 2


def test_fetcher_downloading_retry_has_a_hard_timeout():
    jvlink = MagicMock()
    jvlink.jv_read.return_value = (-3, None, "RACE.jvd")
    fetcher = _historical_fetcher(jvlink)

    with (
        patch("src.fetcher.base.JV_READ_DOWNLOAD_TIMEOUT_SECONDS", 1.0, create=True),
        patch("src.fetcher.base.time.monotonic", side_effect=[0.0, 0.5, 1.1]),
        patch("src.fetcher.base.time.sleep") as sleep,
        pytest.raises(FetcherError, match="downloading.*timeout"),
    ):
        list(fetcher._fetch_and_parse())

    assert jvlink.jv_read.call_count == 3
    assert sleep.call_count == 2


@pytest.mark.parametrize("error_code", [-201, -202, -203, -502, -503])
def test_fetcher_does_not_retry_deterministic_or_download_failures(error_code):
    jvlink = MagicMock()
    jvlink.jv_read.side_effect = [
        (error_code, None, "RACE.jvd"),
        (0, None, None),
    ]
    fetcher = _historical_fetcher(jvlink)

    with pytest.raises(FetcherError, match=str(error_code)):
        list(fetcher._fetch_and_parse())

    jvlink.jv_read.assert_called_once()
    jvlink.jv_file_delete.assert_not_called()


@pytest.mark.parametrize("error_code", [-402, -403])
def test_fetcher_corrupt_file_without_recovery_callback_fails_once(error_code):
    jvlink = MagicMock()
    jvlink.jv_read.side_effect = [
        (error_code, None, "RACE.jvd"),
        (0, None, None),
    ]
    fetcher = _historical_fetcher(jvlink)

    with pytest.raises(FetcherError, match=f"{error_code}|recovery"):
        list(fetcher._fetch_and_parse())

    jvlink.jv_read.assert_called_once()
    jvlink.jv_file_delete.assert_not_called()


def test_native_jvread_rejects_irrecoverable_replacement_character():
    com = MagicMock()
    com.JVRead.return_value = (1, "\ufffd", 1, "RACE.jvd")
    wrapper = _wrapper(com, is_open=True)

    with pytest.raises(JVLinkError, match="recover|buffer|replacement"):
        wrapper.jv_read()


def test_native_jvread_preserves_cp1252_mapped_raw_byte():
    com = MagicMock()
    com.JVRead.return_value = (1, "\u201c", 1, "RACE.jvd")
    wrapper = _wrapper(com, is_open=True)

    assert wrapper.jv_read() == (1, b"\x93", "RACE.jvd")


def test_native_jvread_rejects_a_buffer_shorter_than_returned_byte_count():
    com = MagicMock()
    com.JVRead.return_value = (4, b"ABC", 3, "RACE.jvd")
    wrapper = _wrapper(com, is_open=True)

    with pytest.raises(JVLinkError, match="short|length|buffer"):
        wrapper.jv_read()


def test_bridge_setup_cancel_does_not_expose_a_readable_stream():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._send_command = MagicMock(
        return_value={
            "status": "ok",
            "code": -2,
            "readcount": 0,
            "downloadcount": 0,
            "lastfiletimestamp": "",
        }
    )

    assert bridge.jv_open("RACE", "20260815000000", 3)[0] == -2
    assert bridge.is_open() is False
    assert bridge._needs_close is True


def test_bridge_realtime_no_data_does_not_expose_a_readable_stream():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(return_value={"status": "ok", "code": -1, "readcount": 0})

    assert bridge.jv_rt_open("0B12", "2026081501010101") == (-1, 0)
    assert bridge.is_open() is False
    assert bridge._needs_close is True


def test_bridge_realtime_no_data_accepts_current_runtime_response_without_count():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(
        return_value={"status": "error", "code": -1, "error": "JVRTOpen failed"}
    )

    assert bridge.jv_rt_open("0B12", "2026081501010101") == (-1, 0)
    assert bridge.is_open() is False
    assert bridge._needs_close is True


def test_realtime_open_rejects_undefined_positive_result_code():
    native_com = MagicMock()
    native_com.JVRTOpen.return_value = (1, 0)
    with pytest.raises(JVLinkError, match="JVRTOpen"):
        _wrapper(native_com).jv_rt_open("0B12", "2026081501010101")

    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(return_value={"status": "ok", "code": 1, "readcount": 0})
    with pytest.raises(JVLinkBridgeError, match="JVRTOpen"):
        bridge.jv_rt_open("0B12", "2026081501010101")


def test_realtime_open_rejects_nonzero_compatibility_read_count():
    native_com = MagicMock()
    native_com.JVRTOpen.return_value = (0, 1)
    with pytest.raises(JVLinkError, match="read count|read_count"):
        _wrapper(native_com).jv_rt_open("0B12", "2026081501010101")

    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(return_value={"status": "ok", "code": 0, "readcount": 1})
    with pytest.raises(JVLinkBridgeError, match="readcount|read count"):
        bridge.jv_rt_open("0B12", "2026081501010101")


def test_native_realtime_malformed_success_keeps_close_pending():
    native_com = MagicMock()
    native_com.JVRTOpen.return_value = (0,)
    wrapper = _wrapper(native_com)

    with pytest.raises(JVLinkError, match="tuple length|JVRTOpen"):
        wrapper.jv_rt_open("0B12", "2026081501010101")

    assert wrapper._needs_close is True


def test_bridge_close_failure_keeps_pending_close_state_and_is_reported():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._needs_close = True
    bridge._send_command = MagicMock(side_effect=JVLinkBridgeError("close transport failed"))

    with pytest.raises(JVLinkBridgeError, match="close transport failed"):
        bridge.jv_close()

    assert bridge.is_open() is True
    assert bridge._needs_close is True


def test_bridge_close_error_response_keeps_pending_close_state_and_is_reported():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._needs_close = True
    bridge._send_command = MagicMock(return_value={"status": "error", "error": "JVClose failed"})

    with pytest.raises(JVLinkBridgeError, match="JVClose failed"):
        bridge.jv_close()

    assert bridge.is_open() is True
    assert bridge._needs_close is True


def test_bridge_close_accepts_current_runtime_ack_without_code():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._needs_close = True
    bridge._send_command = MagicMock(return_value={"status": "ok"})

    assert bridge.jv_close() == 0
    assert bridge.is_open() is False
    assert bridge._needs_close is False


def test_close_rejects_nonzero_result_and_preserves_pending_state():
    native_com = MagicMock()
    native_com.JVClose.return_value = -1
    wrapper = _wrapper(native_com, is_open=True)
    wrapper._needs_close = True
    with pytest.raises(JVLinkError, match="JVClose"):
        wrapper.jv_close()
    assert wrapper.is_open() is True
    assert wrapper._needs_close is True

    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._needs_close = True
    bridge._send_command = MagicMock(return_value={"status": "ok", "code": -1})
    with pytest.raises(JVLinkBridgeError, match="JVClose"):
        bridge.jv_close()
    assert bridge.is_open() is True
    assert bridge._needs_close is True


@pytest.mark.parametrize("method_name", ["jv_open", "jv_rt_open", "jv_read", "jv_status"])
def test_bridge_missing_result_code_is_a_protocol_error(method_name):
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._needs_close = True
    bridge._send_command = MagicMock(return_value={"status": "ok"})

    method = getattr(bridge, method_name)
    args = {
        "jv_open": ("RACE", "20260815000000", 1),
        "jv_rt_open": ("0B12", "2026081501010101"),
        "jv_read": (),
        "jv_status": (),
    }[method_name]

    with pytest.raises(JVLinkBridgeError, match="code|result"):
        method(*args)


@pytest.mark.parametrize(
    ("method_name", "args", "response"),
    [
        (
            "jv_open",
            ("RACE", "20260815000000", 1),
            {
                "status": "ok",
                "readcount": 4,
                "downloadcount": 2,
                "lastfiletimestamp": "20260815000000",
            },
        ),
        (
            "jv_rt_open",
            ("0B12", "2026081501010101"),
            {"status": "ok"},
        ),
    ],
)
def test_bridge_malformed_success_without_code_keeps_close_pending(method_name, args, response):
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(return_value=response)

    with pytest.raises(JVLinkBridgeError, match="code|result"):
        getattr(bridge, method_name)(*args)

    assert bridge.is_open() is False
    assert bridge._needs_close is True


@pytest.mark.parametrize("missing_field", ["readcount", "downloadcount", "lastfiletimestamp"])
def test_bridge_open_missing_output_field_is_a_protocol_error(missing_field):
    response = {
        "status": "ok",
        "code": 0,
        "readcount": 4,
        "downloadcount": 2,
        "lastfiletimestamp": "20260815000000",
    }
    del response[missing_field]
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._send_command = MagicMock(return_value=response)

    with pytest.raises(JVLinkBridgeError, match=missing_field):
        bridge.jv_open("RACE", "20260815000000", 1)
    assert bridge._needs_close is True


@pytest.mark.parametrize(
    "encoded",
    [
        base64.b64encode(b"ABC").decode("ascii"),
        "not-valid-base64!",
    ],
)
def test_bridge_read_rejects_malformed_or_short_payload(encoded):
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = True
    bridge._send_command = MagicMock(
        return_value={
            "status": "ok",
            "code": 4,
            "data": encoded,
            "filename": "RACE.jvd",
            "size": 4,
        }
    )

    with pytest.raises(JVLinkBridgeError, match="base64|short|length|payload"):
        bridge.jv_read()


def test_bridge_wait_for_download_completes_at_exact_open_count():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge.jv_status = MagicMock(side_effect=[0, 1, 2])

    with patch("src.jvlink.bridge.time.sleep"):
        assert (
            bridge.wait_for_download(
                download_count=2,
                timeout=1.0,
                poll_interval=0.01,
            )
            is True
        )

    assert bridge.jv_status.call_count == 3


def test_bridge_wait_for_download_preserves_legacy_signature_with_open_count():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._is_open = False
    bridge._needs_close = False
    bridge._download_count = None
    bridge._send_command = MagicMock(
        return_value={
            "status": "ok",
            "code": 0,
            "readcount": 4,
            "downloadcount": 2,
            "lastfiletimestamp": "20260815000000",
        }
    )
    bridge.jv_open("RACE", "20260815000000", 1)
    bridge.jv_status = MagicMock(side_effect=[1, 2])

    with patch("src.jvlink.bridge.time.sleep"):
        assert bridge.wait_for_download(timeout=1.0, poll_interval=0.01) is True


def test_bridge_wait_for_download_without_expected_count_fails_closed():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge._download_count = None
    bridge.jv_status = MagicMock(return_value=0)

    with pytest.raises(ValueError, match="download|count|JVOpen"):
        bridge.wait_for_download(timeout=1.0, poll_interval=0.01)

    bridge.jv_status.assert_not_called()


def test_bridge_wait_for_download_rejects_count_overshoot():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge.jv_status = MagicMock(return_value=3)

    with patch("src.jvlink.bridge.time.sleep"):
        assert (
            bridge.wait_for_download(
                download_count=2,
                timeout=1.0,
                poll_interval=0.01,
            )
            is False
        )

    bridge.jv_status.assert_called_once()


def test_download_wait_rejects_negative_expected_count():
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge.jv_status = MagicMock()
    with pytest.raises(ValueError, match="download_count"):
        bridge.wait_for_download(download_count=-1)
    bridge.jv_status.assert_not_called()

    fetcher = _historical_fetcher(MagicMock())
    with pytest.raises(FetcherError, match="download_count"):
        fetcher._wait_for_download(download_count=-1)


def test_historical_wait_rejects_count_overshoot_and_status_error_immediately():
    jvlink = MagicMock()
    fetcher = _historical_fetcher(jvlink)

    for status in (3, -502):
        jvlink.reset_mock()
        jvlink.jv_status.return_value = status
        with pytest.raises(FetcherError):
            fetcher._wait_for_download(
                download_count=2,
                timeout=1,
                interval=0.01,
            )
        jvlink.jv_status.assert_called_once()


# --- JVRead の往復変換でレコードが 1 バイト縮む回帰 ---
#
# pywin32 は同じバッファを latin-1 相当でも CP1252 でも CP932 のテキストとしても
# 渡してくる。「1 文字 = 1 バイト」を前提にした戻し方を CP932 のバッファへ当てると
# 長さが縮む。CP932 では 2 バイトなのに 1 バイトへ落ちる文字が 2 群ある。
CP932_TWO_BYTE_BUT_LATIN1_CODEPOINT = [
    b"\x81\x4c",  # U+00B4 ´
    b"\x81\x4e",  # U+00A8 ¨
    b"\x81\x7d",  # U+00B1 ±
    b"\x81\x7e",  # U+00D7 ×
    b"\x81\x80",  # U+00F7 ÷
    b"\x81\x8b",  # U+00B0 °
    b"\x81\x98",  # U+00A7 §
    b"\x81\xf7",  # U+00B6 ¶
]
CP932_TWO_BYTE_BUT_IN_CP1252_TABLE = [
    b"\x81\x65",  # U+2018 ‘
    b"\x81\x66",  # U+2019 ’   実際に取り込みを止めた文字
    b"\x81\x67",  # U+201C “
    b"\x81\x68",  # U+201D ”
    b"\x81\xf5",  # U+2020 †
    b"\x81\xf6",  # U+2021 ‡
    b"\x81\x63",  # U+2026 …
    b"\x81\xf1",  # U+2030 ‰
]


@pytest.mark.parametrize(
    "two_byte",
    CP932_TWO_BYTE_BUT_LATIN1_CODEPOINT + CP932_TWO_BYTE_BUT_IN_CP1252_TABLE,
)
def test_recover_com_buffer_keeps_every_two_byte_cp932_character(two_byte):
    """CP932 で 2 バイトの文字は、符号位置が何であれ 2 バイトのまま戻す。"""
    from src.jvlink.wrapper import _recover_com_buffer

    raw = b"A" * 635 + two_byte + b"B" * 635
    assert len(raw) == 1272

    recovered = _recover_com_buffer(raw.decode("cp932"), len(raw), "JVRead")

    assert recovered == raw


def test_recover_com_buffer_restores_the_ra_record_that_stopped_the_import():
    """実際に取り込みを止めた RA レコードを戻せること。

    1987-12-05 阪神 5 回 1 日目 9R。Hondai（競走名本題・data[32:92]）が
    「’８７ゴールデンスパーＴ」で始まり、年を表す ’（U+2019・CP932 では 81 66）が
    CP1252 表で 0x92 の 1 バイトになっていた。1272 -> 1271。
    """
    from src.jvlink.wrapper import _recover_com_buffer

    header = b"RA720021220198712050905010910000"
    hondai = "’８７ゴールデンスパーＴ".encode("cp932")
    raw = header + hondai + b"\x81\x40" * ((1272 - len(header) - len(hondai)) // 2)
    assert len(raw) == 1272
    assert raw[32:34] == b"\x81\x66"  # Hondai の先頭が ’

    recovered = _recover_com_buffer(raw.decode("cp932"), len(raw), "JVRead")

    assert recovered == raw
    assert recovered[32:34] == b"\x81\x66"


def test_recover_com_buffer_still_handles_a_cp1252_marshaled_buffer():
    """CP1252 で渡ってきたバッファは従来どおり 1 文字 1 バイトで戻す。"""
    from src.jvlink.wrapper import _recover_com_buffer

    raw = b"A" * 10 + b"\x91\x92\x93\x94" + b"B" * 10  # CP1252 の ‘ ’ “ ”
    marshaled = raw.decode("cp1252")

    recovered = _recover_com_buffer(marshaled, len(raw), "JVRead")

    assert recovered == raw


@pytest.mark.parametrize("marshal_encoding", ["cp1252", "cp932"])
def test_recover_com_buffer_ignores_trailing_com_nul_before_choosing_encoding(
    marshal_encoding,
):
    """COM末尾NULを候補長へ混ぜても、別encodingを誤選択してはいけない。"""
    from src.jvlink.wrapper import _recover_com_buffer

    raw = b"A" * 10 + b"\x91\x92\x93\x94" + b"B" * 10
    trailing_nuls = 1
    if marshal_encoding == "cp932":
        raw = b"A" * 10 + "‘’“”".encode("cp932") + b"B" * 10
        # Four collapsed two-byte symbols plus four padding NULs produce the
        # same candidate length, so length equality alone picks wrong bytes.
        trailing_nuls = 4
    marshaled = raw.decode(marshal_encoding) + "\x00" * trailing_nuls

    recovered = _recover_com_buffer(marshaled, len(raw), "JVRead")

    assert recovered == raw


def test_recover_com_buffer_rejects_disagreeing_oversized_prefixes():
    """期待長を満たす複数候補のbytesが違うなら、推測で成功させない。"""
    from src.jvlink.wrapper import _recover_com_buffer

    with pytest.raises(JVLinkError, match="ambiguous"):
        _recover_com_buffer("¢A", 1, "JVRead")


def test_cp1252_table_matches_latin1_for_every_byte():
    """latin-1 が通る値では、CP1252 表の経路は同じバイト列にしかならない。

    符号位置 0xFF 以下は表の経路もそのまま 1 バイトで写すため。候補を飛ばして
    よい根拠がこれなので、256 バイトすべてで押さえておく。
    """
    from src.jvlink.wrapper import _decode_via_cp1252_table

    value = bytes(range(256)).decode("latin-1")

    assert _decode_via_cp1252_table(value, "JVRead") == value.encode("latin-1")


def test_recover_com_buffer_skips_the_per_character_table_when_latin1_fits(monkeypatch):
    """latin-1 で戻せる値では、1 文字ずつ回す CP1252 表の候補を作らない。"""
    import src.jvlink.wrapper as wrapper
    from src.jvlink.wrapper import _recover_com_buffer

    def fail(value, method_name):
        raise AssertionError("_decode_via_cp1252_table should not be reached")

    monkeypatch.setattr(wrapper, "_decode_via_cp1252_table", fail)
    raw = b"RA7200212201987120509050109100" + b"\xb4" + b"A" * 1241
    assert len(raw) == 1272

    assert _recover_com_buffer(raw.decode("latin-1"), len(raw), "JVRead") == raw


def test_recover_com_buffer_still_builds_the_table_candidate_when_latin1_fails(
    monkeypatch,
):
    """latin-1 が失敗する値では、従来どおり CP1252 表の候補を作る。"""
    import src.jvlink.wrapper as wrapper
    from src.jvlink.wrapper import _decode_via_cp1252_table, _recover_com_buffer

    reached = []

    def spy(value, method_name):
        reached.append(value)
        return _decode_via_cp1252_table(value, method_name)

    monkeypatch.setattr(wrapper, "_decode_via_cp1252_table", spy)
    raw = b"A" * 10 + b"\x91\x92\x93\x94" + b"B" * 10  # CP1252 の ‘ ’ “ ”

    recovered = _recover_com_buffer(raw.decode("cp1252"), len(raw), "JVRead")

    assert recovered == raw
    assert reached
