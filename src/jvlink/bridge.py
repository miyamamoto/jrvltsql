"""JV-Link Bridge Client (JRA/中央競馬).

Communicates with the C# JVLinkBridge subprocess via stdin/stdout JSON protocol.
This replaces the Python win32com-based JVLinkWrapper, eliminating:
- 32-bit Python requirement
- COM threading/marshaling issues
- win32com dependency
"""

import base64
import binascii
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
    is_retired_data_spec,
    retired_data_spec_message,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _require_response_code(response: dict, command: str) -> int:
    if "code" not in response:
        raise JVLinkBridgeError(f"{command} response has no result code")
    code = response["code"]
    if type(code) is not int:
        raise JVLinkBridgeError(
            f"{command} response result code is not an integer: {code!r}"
        )
    return code


def _require_nonnegative_count(response: dict, field: str, command: str) -> int:
    if field not in response:
        raise JVLinkBridgeError(f"{command} response has no {field}")
    value = response[field]
    if type(value) is not int or value < 0:
        raise JVLinkBridgeError(
            f"{command} response {field} is not a non-negative integer: {value!r}"
        )
    return value


def _require_string(response: dict, field: str, command: str) -> str:
    if field not in response:
        raise JVLinkBridgeError(f"{command} response has no {field}")
    value = response[field]
    if not isinstance(value, str):
        raise JVLinkBridgeError(
            f"{command} response {field} is not a string: {value!r}"
        )
    return value


# Default bridge executable locations (searched in order)
_BRIDGE_SEARCH_PATHS = [
    # Relative to jrvltsql repo root (build output)
    Path("tools/jvlink-bridge/bin/x86/Release/net8.0-windows/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/Release/net8.0-windows/JVLinkBridge.exe"),
    # Relative to jrvltsql repo root (flat copy)
    Path("tools/jvlink-bridge/JVLinkBridge.exe"),
    # Generic Windows locations
    Path(r"C:\Program Files\JVLinkBridge\JVLinkBridge.exe"),
    Path(r"C:\Program Files (x86)\JVLinkBridge\JVLinkBridge.exe"),
]


def find_bridge_executable() -> Optional[Path]:
    """Find the JVLinkBridge executable.

    Returns:
        Path to JVLinkBridge.exe, or None if not found.
    """
    for p in _BRIDGE_SEARCH_PATHS:
        if p.is_absolute() and p.exists():
            return p
        # Try relative to current working directory
        if not p.is_absolute():
            abs_p = Path.cwd() / p
            if abs_p.exists():
                return abs_p
    return None


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
        self._needs_close = False
        self._download_count: Optional[int] = None

        if bridge_path:
            self._bridge_path = Path(bridge_path)
        else:
            self._bridge_path = find_bridge_executable()

        if self._bridge_path is None or not self._bridge_path.exists():
            raise JVLinkBridgeError(
                "JVLinkBridge.exe が見つかりません。"
                "tools/jvlink-bridge/ にビルド済みバイナリを配置してください。"
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
        # 非対応の旧仕様 dataspec はブリッジへ送信する前に弾く（wrapper 側と同じ
        # fail-closed 境界。JVRTOpen の realtime spec は別名前空間なので対象外）。
        if is_retired_data_spec(data_spec):
            raise ValueError(retired_data_spec_message(data_spec))

        response = self._send_command(
            {"cmd": "open", "dataspec": data_spec, "fromtime": fromtime, "option": option},
            timeout=120.0,
        )

        # A protocol-level success means the remote COM call has already
        # opened state even if a malformed response omits its result code.
        # Preserve the close obligation before validating response fields.
        if response.get("status") == "ok":
            self._needs_close = True
        code = _require_response_code(response, "JVOpen")

        # The remote COM call has already changed state before its JSON out
        # fields are validated. A malformed success/no-data/cancel response
        # must still be closed instead of leaking into a later -202.
        if code in (0, -1, -2, -202):
            self._needs_close = True
            if code != -202:
                self._is_open = code == 0

        read_count = _require_nonnegative_count(response, "readcount", "JVOpen")
        download_count = _require_nonnegative_count(
            response, "downloadcount", "JVOpen"
        )
        last_ts = _require_string(response, "lastfiletimestamp", "JVOpen")

        if code not in (0, -1, -2):
            raise JVLinkBridgeError("JVOpen failed", error_code=code)
        if download_count > read_count:
            raise JVLinkBridgeError(
                "JVOpen response downloadcount exceeds readcount: "
                f"{download_count} > {read_count}"
            )

        self._download_count = download_count
        logger.info("JVOpen via bridge", data_spec=data_spec, read_count=read_count, download_count=download_count)
        return code, read_count, download_count, last_ts

    def jv_rt_open(self, data_spec: str, key: str = "") -> Tuple[int, int]:
        response = self._send_command(
            {"cmd": "rtopen", "dataspec": data_spec, "key": key},
            timeout=30.0,
        )

        if response.get("status") == "ok":
            self._needs_close = True
        code = _require_response_code(response, "JVRTOpen")
        # JVRTOpen officially has no read-count output. Older bridge builds
        # include a compatibility field on success but omit it for -1.
        read_count = 0
        if "readcount" in response:
            read_count = _require_nonnegative_count(
                response, "readcount", "JVRTOpen"
            )

        if code in (0, -1, -2, -202):
            self._needs_close = True
            if code != -202:
                self._is_open = code == 0

        if code not in (0, -1):
            raise JVLinkBridgeError("JVRTOpen failed", error_code=code)
        if read_count != 0:
            raise JVLinkBridgeError(
                "JVRTOpen compatibility readcount must be 0, "
                f"got {read_count}"
            )

        self._download_count = 0
        return code, read_count

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        if not self._is_open:
            raise JVLinkBridgeError("JV-Link stream not open.")

        response = self._send_command(
            {"cmd": "read", "size": BUFFER_SIZE_JVREAD},
            timeout=60.0,
        )

        code = _require_response_code(response, "JVRead")

        if code > 0:
            data_b64 = response.get("data", "")
            try:
                data_bytes = base64.b64decode(data_b64, validate=True)
            except (binascii.Error, TypeError, ValueError) as exc:
                raise JVLinkBridgeError(
                    "JVRead bridge payload is not valid base64"
                ) from exc
            if len(data_bytes) < code:
                raise JVLinkBridgeError(
                    "JVRead bridge payload is shorter than its return byte "
                    f"count: {len(data_bytes)} < {code}"
                )
            declared_size = response.get("size")
            if declared_size is not None and declared_size != code:
                raise JVLinkBridgeError(
                    "JVRead bridge size does not match its return byte count: "
                    f"{declared_size} != {code}"
                )
            filename = response.get("filename", "")
            return code, data_bytes[:code], filename
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
        """Expose the bridge's byte payload through the JVGets-shaped API.

        JV-Link has a native JVGets method, but the JSON bridge has only one
        read command and already returns CP932 bytes, so it delegates here.
        """
        code, buff, filename = self.jv_read()
        return code, buff

    def jv_close(self) -> int:
        response = self._send_command({"cmd": "close"}, timeout=10.0)
        if response.get("status") != "ok":
            raise JVLinkBridgeError(
                response.get("error", "JVClose returned an invalid response")
            )
        if "code" in response:
            code = _require_response_code(response, "JVClose")
            if code != 0:
                raise JVLinkBridgeError("JVClose failed", error_code=code)
        else:
            # jrvltsql-wine-runtime through be759ee acknowledges close with
            # only {"status":"ok"}. Preserve compatibility until that
            # adapter propagates JVClose's official Long result code.
            logger.warning(
                "JVClose bridge response omitted the native result code; "
                "accepting the legacy runtime acknowledgment"
            )
            code = 0
        self._is_open = False
        self._needs_close = False
        self._download_count = None
        logger.info("JV-Link stream closed via bridge")
        return code

    def jv_status(self) -> int:
        response = self._send_command({"cmd": "status"}, timeout=10.0)
        return _require_response_code(response, "JVStatus")

    def jv_file_delete(self, filename: str) -> int:
        response = self._send_command(
            {"cmd": "filedelete", "filename": filename},
            timeout=10.0,
        )
        if response.get("status") == "error":
            code = response.get("code", -1)
            raise JVLinkBridgeError(
                response.get("error", f"JVFiledelete failed for {filename}"),
                error_code=code,
            )
        # The production jrvltsql-wine-runtime bridge serializes the COM
        # JVFiledelete return value as ``code``. A missing value is a protocol
        # violation, not an implicit success.
        return _require_response_code(response, f"JVFiledelete for {filename}")

    def wait_for_download(
        self,
        timeout: float = 300.0,
        poll_interval: float = 0.5,
        download_count: Optional[int] = None,
    ) -> bool:
        """Wait until JVStatus exactly matches JVOpen's download count.

        ``timeout`` and ``poll_interval`` retain their historical positional
        order. Callers may supply ``download_count`` explicitly as a keyword;
        otherwise the validated value from the latest JVOpen is used.
        """
        if download_count is None:
            download_count = getattr(self, "_download_count", None)
        if download_count is None:
            raise ValueError(
                "download_count is unavailable; call JVOpen first or pass it explicitly"
            )
        if download_count < 0:
            raise ValueError("download_count must not be negative")
        if download_count == 0:
            return True

        start = time.time()

        while time.time() - start < timeout:
            status = self.jv_status()
            if status == download_count:
                logger.info(
                    "Download completed via bridge",
                    downloaded_files=status,
                    download_count=download_count,
                )
                return True
            if status > download_count:
                logger.error(
                    "JVStatus count exceeded JVOpen download count",
                    status=status,
                    download_count=download_count,
                )
                return False
            if status < 0:
                logger.error("Download error via bridge", status=status)
                return False
            time.sleep(poll_interval)

        logger.warning("Download timeout via bridge", timeout=timeout)
        return False

    def jv_wait_for_download(
        self,
        timeout: float = 300.0,
        poll_interval: float = 0.5,
        download_count: Optional[int] = None,
    ) -> bool:
        return self.wait_for_download(
            timeout=timeout,
            poll_interval=poll_interval,
            download_count=download_count,
        )

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
        self._needs_close = False
        self._download_count = None

    def __enter__(self):
        self.jv_init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_open or getattr(self, "_needs_close", False):
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
