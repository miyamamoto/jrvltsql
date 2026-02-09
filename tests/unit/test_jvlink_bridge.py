"""Tests for JVLinkBridge client (JRA/中央競馬)."""

import json
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.jvlink.bridge import (
    JVLinkBridge,
    JVLinkBridgeError,
)


@pytest.fixture
def bridge(tmp_path):
    """Create bridge with mocked process."""
    exe = tmp_path / "NVLinkBridge.exe"
    exe.touch()
    with patch("src.jvlink.bridge.find_bridge_executable", return_value=exe):
        b = JVLinkBridge(sid="TEST", bridge_path=exe)
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()
    b._process = mock_proc
    return b


def _patch_responses(bridge, *responses):
    bridge._read_response = MagicMock(side_effect=list(responses))


class TestJVLinkBridgeInit:
    def test_raises_if_exe_not_found(self):
        with patch("src.jvlink.bridge.find_bridge_executable", return_value=None):
            with pytest.raises(JVLinkBridgeError, match="見つかりません"):
                JVLinkBridge(bridge_path="/nonexistent.exe")

    def test_init_with_valid_path(self, tmp_path):
        exe = tmp_path / "NVLinkBridge.exe"
        exe.touch()
        b = JVLinkBridge(bridge_path=exe)
        assert b._bridge_path == exe


class TestJVLinkBridgeAPI:
    def test_jv_init_success(self, bridge):
        _patch_responses(bridge, {"status": "ok", "hwnd": 12345, "linkType": "jra"})
        assert bridge.jv_init() == 0

    def test_jv_init_error(self, bridge):
        _patch_responses(bridge, {"status": "error", "error": "JVInit failed", "code": -100})
        with pytest.raises(JVLinkBridgeError):
            bridge.jv_init()

    def test_jv_init_sends_type_jra(self, bridge):
        """Verify init command includes type=jra."""
        sent_cmds = []
        original_send = bridge._send_command

        def capture_send(cmd, **kwargs):
            sent_cmds.append(cmd)
            return {"status": "ok", "hwnd": 1, "linkType": "jra"}

        bridge._send_command = capture_send
        bridge.jv_init()
        assert sent_cmds[0]["type"] == "jra"

    def test_jv_open_success(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 0, "readcount": 100, "downloadcount": 5, "lastfiletimestamp": "20260101"})
        code, rc, dc, ts = bridge.jv_open("RACE", "20260101000000", 1)
        assert code == 0
        assert rc == 100
        assert dc == 5

    def test_jv_open_no_data(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": -1, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""})
        code, rc, dc, ts = bridge.jv_open("RACE", "20260101000000")
        assert code == -1

    def test_jv_open_error(self, bridge):
        _patch_responses(bridge, {"status": "error", "code": -301, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""})
        with pytest.raises(JVLinkBridgeError):
            bridge.jv_open("RACE", "20260101000000")

    def test_jv_read_data(self, bridge):
        bridge._is_open = True
        raw = b"RA2026test record data"
        b64 = base64.b64encode(raw).decode()
        _patch_responses(bridge, {"status": "ok", "code": len(raw), "data": b64, "filename": "f.jvd", "size": len(raw)})
        code, buff, fname = bridge.jv_read()
        assert code == len(raw)
        assert buff == raw
        assert fname == "f.jvd"

    def test_jv_read_complete(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok", "code": 0})
        code, buff, fname = bridge.jv_read()
        assert code == 0
        assert buff is None

    def test_jv_read_file_switch(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok", "code": -1, "filename": "next.jvd"})
        code, buff, fname = bridge.jv_read()
        assert code == -1

    def test_jv_read_not_open(self, bridge):
        with pytest.raises(JVLinkBridgeError, match="not open"):
            bridge.jv_read()

    def test_jv_read_recoverable_502(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "error", "code": -502, "filename": "bad.jvd"})
        code, buff, fname = bridge.jv_read()
        assert code == -502

    def test_jv_gets_delegates_to_read(self, bridge):
        """jv_gets should delegate to jv_read."""
        bridge._is_open = True
        raw = b"test"
        b64 = base64.b64encode(raw).decode()
        _patch_responses(bridge, {"status": "ok", "code": 4, "data": b64, "filename": "f", "size": 4})
        code, buff = bridge.jv_gets()
        assert buff == raw

    def test_jv_close(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok"})
        assert bridge.jv_close() == 0
        assert not bridge._is_open

    def test_jv_status(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 75})
        assert bridge.jv_status() == 75

    def test_jv_file_delete(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 0})
        assert bridge.jv_file_delete("test.jvd") == 0

    def test_jv_rt_open(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 0, "readcount": 5})
        code, rc = bridge.jv_rt_open("0B12")
        assert code == 0

    def test_jv_set_service_key_stub(self, bridge):
        """Service key setting is a stub in bridge mode."""
        assert bridge.jv_set_service_key("test-key") == 0


class TestJVLinkBridgeLifecycle:
    def test_cleanup(self, bridge):
        proc = bridge._process
        _patch_responses(bridge, {"status": "ok", "message": "bye"})
        bridge.cleanup()
        proc.terminate.assert_called_once()
        assert bridge._process is None

    def test_context_manager(self, bridge):
        _patch_responses(
            bridge,
            {"status": "ok", "hwnd": 1, "linkType": "jra"},  # init
            {"status": "ok"},  # close
            {"status": "ok", "message": "bye"},  # quit
        )
        with bridge:
            bridge._is_open = True
        assert not bridge._is_open

    def test_repr(self, bridge):
        assert "JVLinkBridge" in repr(bridge)
        assert "closed" in repr(bridge)

    def test_is_open(self, bridge):
        assert not bridge.is_open()
        bridge._is_open = True
        assert bridge.is_open()

    def test_wait_for_download(self, bridge):
        call_count = [0]
        statuses = [0, 50, 100, 0]
        def fake_response(timeout=30.0):
            idx = min(call_count[0], len(statuses) - 1)
            call_count[0] += 1
            return {"status": "ok", "code": statuses[idx]}
        bridge._read_response = fake_response
        assert bridge.wait_for_download(timeout=5.0, poll_interval=0.01) is True
