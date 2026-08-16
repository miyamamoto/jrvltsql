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
