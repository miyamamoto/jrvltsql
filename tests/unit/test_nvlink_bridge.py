"""Tests for NVLinkBridge TCP client."""

import json
import base64
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.nvlink.bridge import (
    NVLinkBridge,
    NVLinkBridgeError,
    COMBrokenError,
    find_bridge_executable,
)


class TestFindBridgeExecutable:
    """Tests for find_bridge_executable (stub in TCP version)."""

    def test_always_returns_none(self):
        """TCP version doesn't need local executable."""
        assert find_bridge_executable() is None


class TestNVLinkBridgeInit:
    """Tests for NVLinkBridge initialization."""

    def test_init_defaults(self):
        bridge = NVLinkBridge()
        assert bridge.host == "127.0.0.1"
        assert bridge.port == 8901
        assert not bridge._is_open

    def test_init_custom_host_port(self):
        bridge = NVLinkBridge(host="192.168.0.250", port=9000)
        assert bridge.host == "192.168.0.250"
        assert bridge.port == 9000

    def test_init_with_sid(self):
        bridge = NVLinkBridge(sid="TEST")
        assert bridge.sid == "TEST"

    def test_default_timeout(self):
        bridge = NVLinkBridge(command_timeout=60.0)
        assert bridge.command_timeout == 60.0


@pytest.fixture
def bridge():
    """Create bridge with mocked socket connection."""
    b = NVLinkBridge(host="127.0.0.1", port=8901)
    b._socket = MagicMock(spec=socket.socket)
    b._socket_file = MagicMock()
    b._connected = True
    return b


def _patch_responses(bridge, *responses):
    """Patch _send_command to return queued responses."""
    bridge._send_command = MagicMock(side_effect=list(responses))


class TestNVLinkBridgeAPI:
    """Tests for NV-Link API methods via TCP bridge."""

    def test_nv_init_success(self, bridge):
        _patch_responses(
            bridge,
            {"status": "ok", "initResult": 0, "hwnd": 65548},
        )
        result = bridge.nv_init()
        assert result == 0

    def test_nv_init_error(self, bridge):
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

    def test_nv_file_delete(self, bridge):
        """nv_file_delete sends command and returns 0."""
        _patch_responses(bridge, {"status": "ok", "code": 0})
        assert bridge.nv_file_delete("test.nvd") == 0


class TestNVLinkBridgeLifecycle:
    """Tests for bridge lifecycle management."""

    def test_cleanup_closes_socket(self, bridge):
        sock = bridge._socket
        bridge.cleanup()
        sock.close.assert_called()
        assert bridge._socket is None

    def test_context_manager(self, bridge):
        _patch_responses(
            bridge,
            {"status": "ok", "initResult": 0, "hwnd": 1},   # init
            {"status": "ok"},               # close
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
        """reinitialize_com reconnects to bridge."""
        bridge._reconnect = MagicMock()
        bridge._send_command = MagicMock(return_value={"status": "ok", "initResult": 0})
        bridge.reinitialize_com()
        bridge._reconnect.assert_called_once()


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
