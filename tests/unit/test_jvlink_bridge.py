"""Tests for JVLinkBridge client (JRA/中央競馬)."""

import base64
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.jvlink.bridge import (
    JVLinkBridge,
    JVLinkBridgeError,
    find_bridge_executable,
)
from src.parser.se_parser import SEParser
from tests.fixtures.record_factory import make_se_record


@pytest.fixture
def bridge(tmp_path):
    """Create bridge with mocked process."""
    exe = tmp_path / "JVLinkBridge.exe"
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
        exe = tmp_path / "JVLinkBridge.exe"
        exe.touch()
        b = JVLinkBridge(bridge_path=exe)
        assert b._bridge_path == exe

    def test_find_bridge_executable_honors_environment_override(
        self, tmp_path, monkeypatch
    ):
        exe = tmp_path / "native" / "JVLinkBridge.exe"
        exe.parent.mkdir()
        exe.touch()
        monkeypatch.setenv("JVLINK_BRIDGE_EXE", str(exe))

        assert find_bridge_executable() == exe

    def test_linux_bridge_builds_a_wine_command(self, tmp_path):
        exe = tmp_path / "JVLinkBridge.exe"
        exe.touch()
        bridge = JVLinkBridge(bridge_path=exe)

        with patch("src.jvlink.bridge.shutil.which", return_value="/usr/bin/wine"):
            assert bridge._build_command() == ["wine", str(exe)]

    def test_linux_bridge_fails_closed_when_wine_is_missing(self, tmp_path):
        exe = tmp_path / "JVLinkBridge.exe"
        exe.touch()
        bridge = JVLinkBridge(bridge_path=exe)

        with (
            patch("src.jvlink.bridge.shutil.which", return_value=None),
            pytest.raises(JVLinkBridgeError, match="Wine"),
        ):
            bridge._build_command()

    def test_known_update_dialog_is_rejected_instead_of_accepted(
        self, tmp_path, monkeypatch
    ):
        exe = tmp_path / "JVLinkBridge.exe"
        exe.touch()
        bridge = JVLinkBridge(bridge_path=exe)
        bridge._process = MagicMock(pid=777)
        bridge._process.poll.return_value = None
        monkeypatch.setenv("DISPLAY", ":1")

        search = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="42\n", stderr=""
        )
        dismissed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with (
            patch("src.jvlink.bridge.shutil.which", return_value="/usr/bin/xdotool"),
            patch(
                "src.jvlink.bridge.subprocess.run",
                side_effect=[
                    search,
                    dismissed,
                    subprocess.CompletedProcess([], 1, "", ""),
                ],
            ) as run,
        ):
            assert bridge._dismiss_known_dialogs_once() == 1

        assert run.call_args_list[0].args[0] == [
            "xdotool",
            "search",
            "--onlyvisible",
            "--pid",
            "777",
            "--name",
            r"^JRA-VAN DataLab\.$",
        ]
        assert run.call_args_list[1].args[0] == [
            "xdotool",
            "windowactivate",
            "42",
            "key",
            "Escape",
        ]

    def test_dialog_watcher_can_be_disabled(self, tmp_path, monkeypatch):
        exe = tmp_path / "JVLinkBridge.exe"
        exe.touch()
        bridge = JVLinkBridge(bridge_path=exe)
        monkeypatch.setenv("DISPLAY", ":1")
        monkeypatch.setenv("JVLINK_AUTO_CLOSE_DIALOGS", "0")

        with patch(
            "src.jvlink.bridge.shutil.which", return_value="/usr/bin/xdotool"
        ):
            bridge._ensure_dialog_watcher()

        assert bridge._dialog_watcher_thread is None

    @pytest.mark.parametrize("value", ["nan", "inf", "-inf", "invalid"])
    def test_invalid_dialog_watch_interval_falls_back(self, bridge, value):
        with patch.dict(
            "os.environ", {"JVLINK_DIALOG_WATCH_INTERVAL_SECONDS": value}
        ):
            assert bridge._dialog_watch_interval() == 0.5

    def test_bridge_response_ignores_wine_preamble_and_utf8_bom(self, bridge):
        bridge._process.stdout.readline.side_effect = [
            "wine runtime preamble\n",
            '\ufeff{"status":"ready","version":"test"}\n',
        ]
        with patch(
            "select.select",
            side_effect=[
                ([bridge._process.stdout], [], []),
                ([bridge._process.stdout], [], []),
            ],
        ):
            assert bridge._read_response(timeout=1.0) == {
                "status": "ready",
                "version": "test",
            }

    def test_bridge_response_timeout_aborts_the_stuck_process(self, bridge):
        process = bridge._process
        bridge._stderr_file = tempfile.TemporaryFile(mode="w+t")
        stderr_file = bridge._stderr_file
        with (
            patch("select.select", return_value=([], [], [])),
            pytest.raises(JVLinkBridgeError, match="timeout"),
        ):
            bridge._read_response(timeout=0.01)

        process.terminate.assert_called_once()
        assert bridge._process is None
        assert stderr_file.closed

    def test_bridge_send_failure_aborts_the_stuck_process(self, bridge):
        process = bridge._process
        process.stdin.write.side_effect = BrokenPipeError("closed")

        with pytest.raises(JVLinkBridgeError, match="Failed to send"):
            bridge._send_command({"cmd": "status"})

        process.terminate.assert_called_once()
        assert bridge._process is None


class TestJVLinkBridgeAPI:
    def test_jv_init_success(self, bridge):
        _patch_responses(
            bridge,
            {"status": "ok", "code": 0, "hwnd": 12345, "linkType": "jra"},
        )
        assert bridge.jv_init() == 0

    def test_jv_init_error(self, bridge):
        _patch_responses(bridge, {"status": "error", "error": "JVInit failed", "code": -100})
        with pytest.raises(JVLinkBridgeError):
            bridge.jv_init()

    def test_jv_init_requires_an_official_result_code(self, bridge):
        _patch_responses(bridge, {"status": "ok"})

        with pytest.raises(JVLinkBridgeError, match="no result code"):
            bridge.jv_init()

    def test_jv_init_sends_type_jra(self, bridge):
        """Verify init command includes type=jra."""
        sent_cmds = []

        def capture_send(cmd, **kwargs):
            sent_cmds.append(cmd)
            return {"status": "ok", "code": 0, "hwnd": 1, "linkType": "jra"}

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
        raw = make_se_record()
        b64 = base64.b64encode(raw).decode()
        _patch_responses(bridge, {"status": "ok", "code": len(raw), "data": b64, "filename": "f.jvd", "size": len(raw)})
        code, buff, fname = bridge.jv_read()
        assert code == len(raw)
        assert buff == raw
        assert fname == "f.jvd"
        assert len(buff) == SEParser.RECORD_LENGTH
        assert buff[-2:] == b"\r\n"
        assert SEParser().parse(buff)["KettoNum"] == "0000000001"

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

    @pytest.mark.parametrize("error_code", [-402, -403])
    def test_jv_read_corrupt_file_preserves_filename(self, bridge, error_code):
        bridge._is_open = True
        _patch_responses(
            bridge,
            {
                "status": "ok",
                "code": error_code,
                "filename": "corrupt/RACE.jvd",
            },
        )

        assert bridge.jv_read() == (error_code, None, "corrupt/RACE.jvd")

    def test_jv_file_delete_raises_on_bridge_error(self, bridge):
        _patch_responses(
            bridge,
            {
                "status": "error",
                "code": -1,
                "error": "delete failed",
            },
        )

        with pytest.raises(JVLinkBridgeError, match="delete failed"):
            bridge.jv_file_delete("corrupt/RACE.jvd")

    def test_jv_file_delete_requires_result_code(self, bridge):
        _patch_responses(bridge, {"status": "ok"})

        with pytest.raises(JVLinkBridgeError, match="no result code"):
            bridge.jv_file_delete("corrupt/RACE.jvd")

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
        _patch_responses(bridge, {"status": "ok", "code": 0})
        assert bridge.jv_close() == 0
        assert not bridge._is_open

    def test_jv_status(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 75})
        assert bridge.jv_status() == 75

    def test_jv_file_delete(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 0})
        assert bridge.jv_file_delete("test.jvd") == 0

    def test_jv_rt_open(self, bridge):
        _patch_responses(bridge, {"status": "ok", "code": 0, "readcount": 0})
        code, rc = bridge.jv_rt_open("0B12")
        assert code == 0
        assert rc == 0

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
            {"status": "ok", "code": 0, "hwnd": 1, "linkType": "jra"},  # init
            {"status": "ok", "code": 0},  # close
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
        statuses = [0, 50, 100]
        def fake_response(timeout=30.0):
            idx = min(call_count[0], len(statuses) - 1)
            call_count[0] += 1
            return {"status": "ok", "code": statuses[idx]}
        bridge._read_response = fake_response
        assert bridge.wait_for_download(
            download_count=100,
            timeout=5.0,
            poll_interval=0.01,
        ) is True
