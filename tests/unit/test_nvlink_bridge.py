"""Tests for NVLinkBridge client."""

import json
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.nvlink.bridge import (
    NVLinkBridge,
    NVLinkBridgeError,
    COMBrokenError,
    find_bridge_executable,
)


class TestFindBridgeExecutable:
    """Tests for find_bridge_executable."""

    def test_returns_none_when_not_found(self, tmp_path):
        with patch("src.nvlink.bridge._BRIDGE_SEARCH_PATHS", [tmp_path / "nonexistent.exe"]):
            assert find_bridge_executable() is None

    def test_finds_absolute_path(self, tmp_path):
        exe = tmp_path / "NVLinkBridge.exe"
        exe.touch()
        with patch("src.nvlink.bridge._BRIDGE_SEARCH_PATHS", [exe]):
            assert find_bridge_executable() == exe

    def test_finds_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "tools"
        subdir.mkdir()
        exe = subdir / "NVLinkBridge.exe"
        exe.touch()
        with patch("src.nvlink.bridge._BRIDGE_SEARCH_PATHS", [Path("tools/NVLinkBridge.exe")]):
            result = find_bridge_executable()
            assert result is not None
            assert result.exists()


class TestNVLinkBridgeInit:
    """Tests for NVLinkBridge initialization."""

    def test_raises_if_exe_not_found(self):
        with pytest.raises(NVLinkBridgeError, match="見つかりません"):
            NVLinkBridge(bridge_path="/nonexistent/path.exe")

    def test_init_with_valid_path(self, tmp_path):
        exe = tmp_path / "NVLinkBridge.exe"
        exe.touch()
        bridge = NVLinkBridge(bridge_path=exe)
        assert bridge._bridge_path == exe
        assert not bridge._is_open

    def test_default_timeout(self, tmp_path):
        exe = tmp_path / "NVLinkBridge.exe"
        exe.touch()
        bridge = NVLinkBridge(bridge_path=exe, timeout=60.0)
        assert bridge._timeout == 60.0


@pytest.fixture
def bridge(tmp_path):
    """Create bridge with mocked _send_command and _read_response."""
    exe = tmp_path / "NVLinkBridge.exe"
    exe.touch()
    b = NVLinkBridge(bridge_path=exe)
    # Mock process as running
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()
    b._process = mock_proc
    return b


def _patch_responses(bridge, *responses):
    """Patch _read_response to return queued responses."""
    bridge._read_response = MagicMock(side_effect=list(responses))


class TestNVLinkBridgeAPI:
    """Tests for NV-Link API methods via bridge."""

    def test_nv_init_success(self, bridge):
        # Process already running (fixture), so _start_process skips.
        _patch_responses(
            bridge,
            {"status": "ok", "hwnd": 65548},
        )
        result = bridge.nv_init()
        assert result == 0

    def test_nv_init_error(self, bridge):
        # Process already running (fixture), so _start_process returns immediately.
        # Only the init command response is read.
        _patch_responses(
            bridge,
            {"status": "error", "error": "NVInit failed", "code": -100},
        )
        with pytest.raises(NVLinkBridgeError):
            bridge.nv_init()

    def test_nv_open_success(self, bridge):
        _patch_responses(
            bridge,
            {"status": "ok", "code": 0, "readcount": 11, "downloadcount": 0, "lastfiletimestamp": ""},
        )
        code, rc, dc, ts = bridge.nv_open("RACE", "20260201000000", 1)
        assert code == 0
        assert rc == 11
        assert dc == 0

    def test_nv_open_auth_error(self, bridge):
        _patch_responses(
            bridge,
            {"status": "error", "code": -301, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""},
        )
        with pytest.raises(NVLinkBridgeError, match="認証エラー"):
            bridge.nv_open("RACE", "20260201000000")

    def test_nv_open_unsubscribed(self, bridge):
        _patch_responses(
            bridge,
            {"status": "error", "code": -111, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""},
        )
        with pytest.raises(NVLinkBridgeError, match="契約"):
            bridge.nv_open("MING", "20260201000000")

    def test_nv_open_already_open_retry(self, bridge):
        _patch_responses(
            bridge,
            {"status": "error", "code": -202, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""},
            {"status": "ok"},  # close
            {"status": "ok", "code": 0, "readcount": 5, "downloadcount": 0, "lastfiletimestamp": ""},
        )
        code, rc, dc, ts = bridge.nv_open("RACE", "20260201000000")
        assert code == 0
        assert rc == 5

    def test_nv_open_no_data(self, bridge):
        """nv_open returns -1 (no data) without raising."""
        _patch_responses(
            bridge,
            {"status": "ok", "code": -1, "readcount": 0, "downloadcount": 0, "lastfiletimestamp": ""},
        )
        code, rc, dc, ts = bridge.nv_open("RACE", "20260201000000")
        assert code == -1

    def test_nv_gets_data(self, bridge):
        bridge._is_open = True
        raw_data = b"H1test data in shift-jis"
        b64 = base64.b64encode(raw_data).decode()
        _patch_responses(
            bridge,
            {"status": "ok", "code": len(raw_data), "data": b64, "filename": "H1NV.nvd", "size": len(raw_data)},
        )
        code, buff, fname = bridge.nv_gets()
        assert code == len(raw_data)
        assert buff == raw_data
        assert fname == "H1NV.nvd"

    def test_nv_gets_complete(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok", "code": 0})
        code, buff, fname = bridge.nv_gets()
        assert code == 0
        assert buff is None

    def test_nv_gets_file_switch(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok", "code": -1, "filename": "next.nvd"})
        code, buff, fname = bridge.nv_gets()
        assert code == -1
        assert fname == "next.nvd"

    def test_nv_gets_recoverable_502(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "error", "code": -502, "filename": "bad.nvd"})
        code, buff, fname = bridge.nv_gets()
        assert code == -502
        assert fname == "bad.nvd"

    def test_nv_gets_recoverable_203(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "error", "code": -203, "filename": "x.nvd"})
        code, buff, fname = bridge.nv_gets()
        assert code == -203

    def test_nv_gets_not_open(self, bridge):
        with pytest.raises(NVLinkBridgeError, match="not open"):
            bridge.nv_gets()

    def test_nv_read_data(self, bridge):
        bridge._is_open = True
        raw_data = b"SE test record"
        b64 = base64.b64encode(raw_data).decode()
        _patch_responses(
            bridge,
            {"status": "ok", "code": len(raw_data), "data": b64, "filename": "f.nvd", "size": len(raw_data)},
        )
        code, buff, fname = bridge.nv_read()
        assert code == len(raw_data)
        assert buff == raw_data

    def test_nv_read_not_open(self, bridge):
        with pytest.raises(NVLinkBridgeError, match="not open"):
            bridge.nv_read()

    def test_nv_close(self, bridge):
        bridge._is_open = True
        _patch_responses(bridge, {"status": "ok"})
        result = bridge.nv_close()
        assert result == 0
        assert not bridge._is_open

    def test_nv_close_already_closed(self, bridge):
        """Close on already-closed bridge is idempotent."""
        _patch_responses(bridge, {"status": "ok"})
        result = bridge.nv_close()
        assert result == 0

    def test_nv_status(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 50})
        assert bridge.nv_status() == 50

    def test_nv_status_error(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": -502})
        assert bridge.nv_status() == -502

    def test_wait_for_download_immediate(self, bridge):
        """Download already complete (status stays 0)."""
        # Starts with 0 (not started), gets >0 (progress), then 0 (complete)
        call_count = [0]
        statuses = [0, 50, 100, 0]
        original = bridge._read_response
        def fake_response(timeout=30.0):
            idx = min(call_count[0], len(statuses) - 1)
            call_count[0] += 1
            return {"status": "ok", "code": statuses[idx]}
        bridge._read_response = fake_response
        result = bridge.wait_for_download(timeout=5.0, poll_interval=0.01)
        assert result is True

    def test_nv_file_delete_stub(self, bridge):
        """nv_file_delete is a stub returning 0."""
        assert bridge.nv_file_delete("test.nvd") == 0


class TestNVLinkBridgeLifecycle:
    """Tests for bridge lifecycle management."""

    def test_cleanup_terminates_process(self, bridge):
        proc = bridge._process
        _patch_responses(bridge, {"status": "ok", "message": "bye"})
        bridge.cleanup()
        proc.terminate.assert_called_once()
        assert bridge._process is None

    def test_cleanup_kills_on_timeout(self, bridge):
        proc = bridge._process
        _patch_responses(bridge, {"status": "ok", "message": "bye"})
        proc.wait.side_effect = TimeoutError
        bridge.cleanup()
        proc.kill.assert_called_once()

    def test_context_manager(self, bridge):
        # Process already running. __enter__ calls nv_init (sends init cmd).
        # __exit__ calls nv_close + cleanup.
        _patch_responses(
            bridge,
            {"status": "ok", "hwnd": 1},   # init
            {"status": "ok"},               # close
            {"status": "ok", "message": "bye"},  # quit
        )
        with bridge:
            bridge._is_open = True
        assert not bridge._is_open

    def test_repr_closed(self, bridge):
        assert "closed" in repr(bridge)

    def test_repr_open(self, bridge):
        bridge._is_open = True
        assert "open" in repr(bridge)

    def test_is_open(self, bridge):
        assert not bridge.is_open()
        bridge._is_open = True
        assert bridge.is_open()


class TestNVLinkBridgeAliases:
    """Tests for JVLinkWrapper compatibility aliases."""

    def test_jv_aliases_exist(self, bridge):
        assert hasattr(bridge, "jv_init")
        assert hasattr(bridge, "jv_open")
        assert hasattr(bridge, "jv_read")
        assert hasattr(bridge, "jv_gets")
        assert hasattr(bridge, "jv_close")
        assert hasattr(bridge, "jv_status")
        assert hasattr(bridge, "jv_file_delete")
        assert hasattr(bridge, "jv_wait_for_download")
        assert hasattr(bridge, "reinitialize_com")

    def test_jv_read_uses_gets(self, bridge):
        """jv_read delegates to nv_gets (not nv_read)."""
        bridge._is_open = True
        raw_data = b"test"
        b64 = base64.b64encode(raw_data).decode()
        _patch_responses(
            bridge,
            {"status": "ok", "code": 4, "data": b64, "filename": "f.nvd", "size": 4},
        )
        code, buff, fname = bridge.jv_read()
        assert buff == raw_data

    def test_reinitialize_com(self, bridge):
        """reinitialize_com calls cleanup then restarts."""
        # Just verify cleanup is called and the method doesn't crash
        bridge.cleanup = MagicMock()
        bridge._start_process = MagicMock()
        bridge._send_command = MagicMock(return_value={"status": "ok"})
        bridge.reinitialize_com()
        bridge.cleanup.assert_called_once()
        bridge._start_process.assert_called_once()


class TestCOMBrokenError:
    """Tests for COMBrokenError."""

    def test_is_nvlink_bridge_error(self):
        err = COMBrokenError("test")
        assert isinstance(err, NVLinkBridgeError)
        assert err.error_code == -2147418113

    def test_catchable(self):
        """Can be caught by NVLinkBridgeError handler."""
        with pytest.raises(NVLinkBridgeError):
            raise COMBrokenError("broken")
