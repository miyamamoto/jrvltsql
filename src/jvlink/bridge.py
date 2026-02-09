"""JV-Link Bridge Client (JRA/中央競馬).

Communicates with the C# JV/NV-LinkBridge subprocess via stdin/stdout JSON protocol.
This replaces the Python win32com-based JVLinkWrapper, eliminating:
- 32-bit Python requirement
- COM threading/marshaling issues
- win32com dependency

Uses the same bridge executable as NVLinkBridge but with type="jra".
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from src.jvlink.constants import (
    JV_READ_NO_MORE_DATA,
    JV_READ_SUCCESS,
    BUFFER_SIZE_JVREAD,
)
from src.nvlink.bridge import find_bridge_executable, NVLinkBridgeError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JVLinkBridgeError(Exception):
    """JV-Link Bridge related error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code})"
        super().__init__(message)


class JVLinkBridge:
    """JV-Link Bridge Client for JRA (中央競馬).

    Spawns the C# bridge subprocess with type="jra" to use JVDTLab.JVLink COM.
    Provides the same interface as JVLinkWrapper for drop-in replacement.

    Benefits over JVLinkWrapper:
    - Works with 64-bit Python (no 32-bit restriction)
    - No win32com/pythoncom dependency
    - Native C# COM interop (more stable)

    Examples:
        >>> bridge = JVLinkBridge(sid="UNKNOWN")
        >>> bridge.jv_init()
        0
        >>> result, count, dl, ts = bridge.jv_open("RACE", "20240101000000", 1)
        >>> while True:
        ...     ret_code, buff, filename = bridge.jv_read()
        ...     if ret_code == 0:
        ...         break
        >>> bridge.jv_close()
    """

    def __init__(
        self,
        sid: str = "UNKNOWN",
        bridge_path: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        self.sid = sid
        self._timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._is_open = False

        if bridge_path:
            self._bridge_path = Path(bridge_path)
        else:
            self._bridge_path = find_bridge_executable()

        if self._bridge_path is None or not self._bridge_path.exists():
            raise JVLinkBridgeError(
                "JVLinkBridge.exe が見つかりません。"
                "tools/nvlink-bridge/ にビルド済みバイナリを配置してください。"
            )

        logger.info("JVLinkBridge initialized", bridge_path=str(self._bridge_path), sid=sid)

    def _start_process(self):
        if self._process is not None and self._process.poll() is None:
            return

        logger.info("Starting JVLinkBridge subprocess", path=str(self._bridge_path))

        self._process = subprocess.Popen(
            [str(self._bridge_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        response = self._read_response(timeout=10.0)
        if response.get("status") != "ready":
            raise JVLinkBridgeError(f"Bridge failed to start: {response.get('error', 'unknown')}")
        logger.info("JVLinkBridge subprocess ready", version=response.get("version"))

    def _send_command(self, cmd: dict, timeout: Optional[float] = None) -> dict:
        if self._process is None or self._process.poll() is not None:
            raise JVLinkBridgeError("Bridge process is not running")

        timeout = timeout or self._timeout
        cmd_json = json.dumps(cmd, ensure_ascii=False)

        try:
            self._process.stdin.write(cmd_json + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise JVLinkBridgeError(f"Failed to send command: {e}")

        return self._read_response(timeout=timeout)

    def _read_response(self, timeout: float = 30.0) -> dict:
        if self._process is None:
            raise JVLinkBridgeError("Bridge process is not running")

        if sys.platform == "win32":
            import threading
            result = [None]
            error = [None]

            def _read():
                try:
                    result[0] = self._process.stdout.readline()
                except Exception as e:
                    error[0] = e

            thread = threading.Thread(target=_read, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                raise JVLinkBridgeError(f"Bridge response timeout ({timeout}s)")
            if error[0]:
                raise JVLinkBridgeError(f"Bridge read error: {error[0]}")
            line = result[0]
        else:
            import select
            ready, _, _ = select.select([self._process.stdout], [], [], timeout)
            if not ready:
                raise JVLinkBridgeError(f"Bridge response timeout ({timeout}s)")
            line = self._process.stdout.readline()

        if not line:
            stderr_output = ""
            if self._process.stderr:
                try:
                    stderr_output = self._process.stderr.read()
                except Exception:
                    pass
            raise JVLinkBridgeError(f"Bridge terminated unexpectedly. stderr: {stderr_output}")

        try:
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            raise JVLinkBridgeError(f"Invalid JSON from bridge: {line.strip()!r}: {e}")

    # =========================================================================
    # JV-Link API Methods
    # =========================================================================

    def jv_init(self) -> int:
        self._start_process()
        response = self._send_command({"cmd": "init", "type": "jra", "key": self.sid})

        if response.get("status") == "error":
            code = response.get("code", -1)
            raise JVLinkBridgeError(response.get("error", "JVInit failed"), error_code=code)

        logger.info("JV-Link initialized via bridge", hwnd=response.get("hwnd"))
        return 0

    def jv_set_service_key(self, service_key: str) -> int:
        """Set service key. Note: Bridge doesn't directly support this yet.

        For JRA, the service key is typically set via registry by JRA-VAN DataLab installer.
        """
        logger.warning("jv_set_service_key not implemented in bridge; use JRA-VAN DataLab to configure")
        return 0

    def jv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        response = self._send_command(
            {"cmd": "open", "dataspec": data_spec, "fromtime": fromtime, "option": option},
            timeout=120.0,
        )

        code = response.get("code", -1)
        read_count = response.get("readcount", 0)
        download_count = response.get("downloadcount", 0)
        last_ts = response.get("lastfiletimestamp", "")

        if code < -2:
            raise JVLinkBridgeError("JVOpen failed", error_code=code)

        self._is_open = True
        logger.info("JVOpen via bridge", data_spec=data_spec, read_count=read_count, download_count=download_count)
        return code, read_count, download_count, last_ts

    def jv_rt_open(self, data_spec: str, key: str = "") -> Tuple[int, int]:
        response = self._send_command(
            {"cmd": "rtopen", "dataspec": data_spec, "key": key},
            timeout=30.0,
        )

        code = response.get("code", -1)
        read_count = response.get("readcount", 0)

        if code < -2:
            raise JVLinkBridgeError("JVRTOpen failed", error_code=code)

        self._is_open = True
        return code, read_count

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        if not self._is_open:
            raise JVLinkBridgeError("JV-Link stream not open.")

        response = self._send_command(
            {"cmd": "read", "size": BUFFER_SIZE_JVREAD},
            timeout=60.0,
        )

        code = response.get("code", 0)

        if code > 0:
            data_b64 = response.get("data", "")
            data_bytes = base64.b64decode(data_b64) if data_b64 else b""
            filename = response.get("filename", "")
            return code, data_bytes, filename
        elif code == JV_READ_SUCCESS:  # 0
            return code, None, None
        elif code == JV_READ_NO_MORE_DATA:  # -1
            return code, None, response.get("filename")
        elif code in (-3, -203, -402, -403, -502, -503):
            filename = response.get("filename", "")
            logger.warning("JVRead recoverable error via bridge", code=code, filename=filename)
            return code, None, filename
        else:
            logger.error("JVRead error via bridge", code=code)
            return code, None, response.get("filename")

    def jv_gets(self) -> Tuple[int, Optional[bytes]]:
        """JV-Link doesn't have JVGets; delegates to jv_read."""
        code, buff, filename = self.jv_read()
        return code, buff

    def jv_close(self) -> int:
        try:
            self._send_command({"cmd": "close"}, timeout=10.0)
        except JVLinkBridgeError:
            pass
        self._is_open = False
        logger.info("JV-Link stream closed via bridge")
        return 0

    def jv_status(self) -> int:
        response = self._send_command({"cmd": "status"}, timeout=10.0)
        return response.get("code", 0)

    def jv_file_delete(self, filename: str) -> int:
        response = self._send_command(
            {"cmd": "filedelete", "filename": filename},
            timeout=10.0,
        )
        return response.get("code", 0)

    def wait_for_download(self, timeout: float = 300.0, poll_interval: float = 0.5) -> bool:
        start = time.time()
        download_started = False

        while time.time() - start < timeout:
            status = self.jv_status()
            if status > 0:
                download_started = True
            elif status == 0 and download_started:
                logger.info("Download completed via bridge")
                return True
            elif status < 0:
                logger.error("Download error via bridge", status=status)
                return False
            time.sleep(poll_interval)

        logger.warning("Download timeout via bridge", timeout=timeout)
        return False

    def jv_wait_for_download(self, timeout: float = 300.0, poll_interval: float = 0.5) -> bool:
        return self.wait_for_download(timeout, poll_interval)

    def is_open(self) -> bool:
        return self._is_open

    def cleanup(self):
        if self._process is not None and self._process.poll() is None:
            try:
                self._send_command({"cmd": "quit"}, timeout=5.0)
            except Exception:
                pass
            try:
                self._process.terminate()
                self._process.wait(timeout=5.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        self._process = None
        self._is_open = False

    def __enter__(self):
        self.jv_init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_open:
            self.jv_close()
        self.cleanup()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass

    def __repr__(self) -> str:
        status = "open" if self._is_open else "closed"
        running = self._process is not None and self._process.poll() is None
        return f"<JVLinkBridge status={status} running={running}>"
