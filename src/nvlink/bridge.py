"""NV-Link Bridge Client.

Communicates with the C# NVLinkBridge subprocess via stdin/stdout JSON protocol.
This replaces the Python win32com-based NVLinkWrapper for NAR operations,
solving COM VARIANT BYREF marshaling issues that cause E_UNEXPECTED errors.

The C# bridge uses native COM interop (like kmy-keiba) and properly handles
NV-Link's Delphi COM memory management via Array.Resize(ref buff, 0).
"""

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Union

from src.nvlink.constants import (
    BUFFER_SIZE_NVREAD,
    NV_READ_NO_MORE_DATA,
    NV_READ_SUCCESS,
    get_error_message,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default bridge executable locations (searched in order)
_BRIDGE_SEARCH_PATHS = [
    # Relative to jrvltsql repo root (build output)
    Path("tools/nvlink-bridge/bin/x86/Release/net8.0-windows/NVLinkBridge.exe"),
    # Relative to jrvltsql repo root (flat copy)
    Path("tools/nvlink-bridge/NVLinkBridge.exe"),
    # A6 build locations
    Path(r"C:\Users\mitsu\work\jrvltsql\tools\nvlink-bridge\bin\x86\Release\net8.0-windows\NVLinkBridge.exe"),
    Path(r"C:\Users\mitsu\work\nvlink-bridge\bin\x86\Release\net8.0-windows\NVLinkBridge.exe"),
    # Generic Windows location
    Path(r"C:\Program Files\NVLinkBridge\NVLinkBridge.exe"),
    Path(r"C:\Program Files (x86)\NVLinkBridge\NVLinkBridge.exe"),
]


def find_bridge_executable() -> Optional[Path]:
    """Find the NVLinkBridge executable.

    Returns:
        Path to NVLinkBridge.exe, or None if not found.
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


class NVLinkBridgeError(Exception):
    """NV-Link Bridge related error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code}, {get_error_message(error_code)})"
        super().__init__(message)


class COMBrokenError(NVLinkBridgeError):
    """Raised when COM object is broken."""

    def __init__(self, message: str = "COM error via bridge"):
        super().__init__(message, error_code=-2147418113)


class NVLinkBridge:
    """NV-Link Bridge Client.

    Spawns and communicates with the C# NVLinkBridge subprocess.
    Provides the same interface as NVLinkWrapper for drop-in replacement.

    The bridge process must run in a GUI context (console session) on Windows.
    When running headless (SSH), use schtasks to launch in interactive session.

    Examples:
        >>> bridge = NVLinkBridge()
        >>> bridge.nv_init()
        0
        >>> result, count, dl, ts = bridge.nv_open("RACE", "20240101000000", 1)
        >>> while True:
        ...     ret_code, buff, filename = bridge.nv_gets()
        ...     if ret_code == 0:
        ...         break
        >>> bridge.nv_close()
    """

    def __init__(
        self,
        sid: str = "UNKNOWN",
        initialization_key: Optional[str] = None,
        bridge_path: Optional[Union[str, Path]] = None,
        timeout: float = 600.0,
    ):
        """Initialize NVLinkBridge.

        Args:
            sid: Session ID (passed to NVInit as key).
            initialization_key: Optional init key (overrides sid for NVInit).
            bridge_path: Path to NVLinkBridge.exe. Auto-detected if None.
            timeout: Default timeout for bridge commands in seconds.
        """
        self.sid = sid
        self.initialization_key = initialization_key
        self._timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._is_open = False

        # Find bridge executable
        if bridge_path:
            self._bridge_path = Path(bridge_path)
        else:
            self._bridge_path = find_bridge_executable()

        if self._bridge_path is None or not self._bridge_path.exists():
            raise NVLinkBridgeError(
                "NVLinkBridge.exe が見つかりません。"
                "tools/nvlink-bridge/ にビルド済みバイナリを配置するか、"
                "bridge_path を指定してください。"
            )

        logger.info("NVLinkBridge initialized", bridge_path=str(self._bridge_path), sid=sid)

    def _start_process(self):
        """Start the bridge subprocess."""
        if self._process is not None and self._process.poll() is None:
            return  # Already running

        logger.info("Starting NVLinkBridge subprocess", path=str(self._bridge_path))

        self._process = subprocess.Popen(
            [str(self._bridge_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,  # Line-buffered
        )

        # Wait for "ready" signal
        response = self._read_response(timeout=10.0)
        if response.get("status") != "ready":
            raise NVLinkBridgeError(
                f"NVLinkBridge failed to start: {response.get('error', 'unknown')}"
            )
        logger.info("NVLinkBridge subprocess ready", version=response.get("version"))

    def _send_command(self, cmd: dict, timeout: Optional[float] = None) -> dict:
        """Send a JSON command to the bridge and read the response.

        Args:
            cmd: Command dictionary (must have "cmd" key).
            timeout: Override default timeout.

        Returns:
            Response dictionary from bridge.

        Raises:
            NVLinkBridgeError: If communication fails.
        """
        if self._process is None or self._process.poll() is not None:
            raise NVLinkBridgeError("Bridge process is not running")

        timeout = timeout or self._timeout
        cmd_json = json.dumps(cmd, ensure_ascii=False)

        try:
            self._process.stdin.write(cmd_json + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise NVLinkBridgeError(f"Failed to send command to bridge: {e}")

        return self._read_response(timeout=timeout)

    def _read_response(self, timeout: float = 30.0) -> dict:
        """Read a JSON response line from the bridge stdout.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Parsed JSON response.
        """
        if self._process is None:
            raise NVLinkBridgeError("Bridge process is not running")

        import select

        # On Windows, select doesn't work on pipes. Use a simple blocking read
        # with timeout via threading.
        if sys.platform == "win32":
            import threading

            result = [None]
            error = [None]

            def _read():
                try:
                    line = self._process.stdout.readline()
                    result[0] = line
                except Exception as e:
                    error[0] = e

            thread = threading.Thread(target=_read, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                raise NVLinkBridgeError(f"Bridge response timeout ({timeout}s)")
            if error[0]:
                raise NVLinkBridgeError(f"Bridge read error: {error[0]}")

            line = result[0]
        else:
            # Unix: use select for timeout
            ready, _, _ = select.select([self._process.stdout], [], [], timeout)
            if not ready:
                raise NVLinkBridgeError(f"Bridge response timeout ({timeout}s)")
            line = self._process.stdout.readline()

        if not line:
            # Process may have exited
            stderr_output = ""
            if self._process.stderr:
                try:
                    stderr_output = self._process.stderr.read()
                except Exception:
                    pass
            raise NVLinkBridgeError(
                f"Bridge process terminated unexpectedly. stderr: {stderr_output}"
            )

        try:
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            raise NVLinkBridgeError(f"Invalid JSON from bridge: {line.strip()!r}: {e}")

    # =========================================================================
    # NV-Link API Methods (same interface as NVLinkWrapper)
    # =========================================================================

    def nv_init(self) -> int:
        """Initialize NV-Link via bridge.

        Returns:
            Result code (0 = success).
        """
        self._start_process()

        init_key = self.initialization_key or self.sid
        response = self._send_command({"cmd": "init", "type": "nar", "key": init_key})

        if response.get("status") == "error":
            code = response.get("code", -1)
            raise NVLinkBridgeError(
                response.get("error", "NVInit failed"), error_code=code
            )

        logger.info("NV-Link initialized via bridge", hwnd=response.get("hwnd"))
        return 0

    def nv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        """Open NV-Link data stream.

        Args:
            data_spec: Data specification (e.g., "RACE", "DIFF").
            fromtime: Start time in YYYYMMDDhhmmss format.
            option: Open option (1=normal, 2=thisweek, 3=setup, 4=split-setup).

        Returns:
            Tuple of (result_code, read_count, download_count, last_file_timestamp).
        """
        response = self._send_command(
            {
                "cmd": "open",
                "dataspec": data_spec,
                "fromtime": fromtime,
                "option": option,
            },
            timeout=600.0,  # Open can take a while with downloads
        )

        code = response.get("code", -1)
        read_count = response.get("readcount", 0)
        download_count = response.get("downloadcount", 0)
        last_ts = response.get("lastfiletimestamp", "")

        # -202: Already open — close and retry
        if code == -202:
            logger.warning("NVOpen returned -202 (AlreadyOpen), closing and retrying")
            self._send_command({"cmd": "close"})
            self._is_open = False
            response = self._send_command(
                {
                    "cmd": "open",
                    "dataspec": data_spec,
                    "fromtime": fromtime,
                    "option": option,
                },
                timeout=600.0,
            )
            code = response.get("code", -1)
            read_count = response.get("readcount", 0)
            download_count = response.get("downloadcount", 0)
            last_ts = response.get("lastfiletimestamp", "")

        # Authentication errors
        if code in (-301, -302, -303):
            error_msgs = {
                -301: "認証エラー: サーバー認証に失敗しました。",
                -302: "認証エラー: 利用キーが不正または有効期限切れです。",
                -303: "認証エラー: 利用キーが設定されていません。",
            }
            raise NVLinkBridgeError(error_msgs.get(code, "認証エラー"), error_code=code)

        # Other fatal errors
        if code < -2 and code not in (-1, -2):
            if code in (-111, -114):
                raise NVLinkBridgeError(
                    "このデータ種別は地方競馬DATAの契約に含まれていません。",
                    error_code=code,
                )
            raise NVLinkBridgeError("NVOpen failed", error_code=code)

        self._is_open = True
        logger.info(
            "NVOpen via bridge",
            data_spec=data_spec,
            fromtime=fromtime,
            option=option,
            read_count=read_count,
            download_count=download_count,
        )

        return code, read_count, download_count, last_ts

    def nv_gets(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record using NVGets (byte array, recommended for NAR).

        Returns:
            Tuple of (return_code, buffer, filename).
            buffer is raw Shift-JIS bytes when return_code > 0.
        """
        if not self._is_open:
            raise NVLinkBridgeError("NV-Link stream not open.")

        response = self._send_command(
            {"cmd": "gets", "size": BUFFER_SIZE_NVREAD},
            timeout=60.0,
        )

        code = response.get("code", 0)

        if code > 0:
            # Decode base64 data to raw bytes
            data_b64 = response.get("data", "")
            if data_b64:
                data_bytes = base64.b64decode(data_b64)
            else:
                data_bytes = b""
            filename = response.get("filename", "")
            return code, data_bytes, filename

        elif code == NV_READ_SUCCESS:  # 0 = complete
            return code, None, None

        elif code == NV_READ_NO_MORE_DATA:  # -1 = file switch
            filename = response.get("filename", "")
            return code, None, filename

        elif code in (-203, -402, -403, -502, -503):
            # Recoverable errors
            filename = response.get("filename", "")
            logger.warning("NVGets recoverable error via bridge", code=code, filename=filename)
            return code, None, filename

        else:
            # Other errors
            filename = response.get("filename", "")
            logger.error("NVGets error via bridge", code=code, filename=filename)
            return code, None, filename

    def nv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record using NVRead (string-based).

        Returns:
            Tuple of (return_code, buffer, filename).
        """
        if not self._is_open:
            raise NVLinkBridgeError("NV-Link stream not open.")

        response = self._send_command(
            {"cmd": "read", "size": BUFFER_SIZE_NVREAD},
            timeout=60.0,
        )

        code = response.get("code", 0)

        if code > 0:
            data_b64 = response.get("data", "")
            data_bytes = base64.b64decode(data_b64) if data_b64 else b""
            filename = response.get("filename", "")
            return code, data_bytes, filename

        elif code == NV_READ_SUCCESS:
            return code, None, None

        elif code == NV_READ_NO_MORE_DATA:
            return code, None, response.get("filename")

        elif code in (-203, -402, -403, -502, -503):
            filename = response.get("filename", "")
            logger.warning("NVRead recoverable error via bridge", code=code, filename=filename)
            return code, None, filename

        else:
            filename = response.get("filename", "")
            logger.error("NVRead error via bridge", code=code, filename=filename)
            return code, None, filename

    def nv_status(self) -> int:
        """Get download status.

        Returns:
            Status code (>0 = progress %, 0 = idle/complete, <0 = error).
        """
        response = self._send_command({"cmd": "status"}, timeout=10.0)
        return response.get("code", 0)

    def nv_close(self) -> int:
        """Close NV-Link data stream.

        Returns:
            Result code (0 = success).
        """
        try:
            self._send_command({"cmd": "close"}, timeout=10.0)
        except NVLinkBridgeError:
            pass  # Best effort
        self._is_open = False
        logger.info("NV-Link stream closed via bridge")
        return 0

    def nv_file_delete(self, filename: str) -> int:
        """Delete a cached file. (Not yet implemented in C# bridge.)

        Args:
            filename: File to delete.

        Returns:
            0 (stub).
        """
        # TODO: Add NVFiledelete command to C# bridge
        logger.warning("nv_file_delete not implemented in bridge", filename=filename)
        return 0

    def wait_for_download(self, timeout: float = 600.0, poll_interval: float = 1.0) -> bool:
        """Wait for download to complete.

        Args:
            timeout: Maximum wait time in seconds.
            poll_interval: Polling interval in seconds.

        Returns:
            True if download completed, False on timeout/error.
        """
        start = time.time()
        download_started = False

        while time.time() - start < timeout:
            status = self.nv_status()
            if status > 0:
                download_started = True
                logger.debug("Download progress via bridge", progress=status)
            elif status == 0:
                if download_started:
                    logger.info("Download completed via bridge")
                    return True
            else:
                logger.error("Download error via bridge", status=status)
                return False
            time.sleep(poll_interval)

        logger.warning("Download timeout via bridge", timeout=timeout)
        return False

    def is_open(self) -> bool:
        """Check if stream is open."""
        return self._is_open

    def cleanup(self):
        """Stop the bridge subprocess."""
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
        """Context manager entry."""
        self.nv_init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._is_open:
            self.nv_close()
        self.cleanup()

    def __del__(self):
        """Destructor."""
        try:
            self.cleanup()
        except Exception:
            pass

    def __repr__(self) -> str:
        status = "open" if self._is_open else "closed"
        running = self._process is not None and self._process.poll() is None
        return f"<NVLinkBridge status={status} running={running}>"

    # =========================================================================
    # JVLinkWrapper互換エイリアス（BaseFetcherでポリモーフィックに使用）
    # =========================================================================

    def jv_init(self) -> int:
        return self.nv_init()

    def jv_open(self, data_spec: str, fromtime: str, option: int = 1) -> Tuple[int, int, int, str]:
        return self.nv_open(data_spec, fromtime, option)

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        return self.nv_gets()  # Use NVGets (byte array) by default — more reliable

    def jv_gets(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        return self.nv_gets()

    def jv_file_delete(self, filename: str) -> int:
        return self.nv_file_delete(filename)

    def jv_close(self) -> int:
        return self.nv_close()

    def jv_status(self) -> int:
        return self.nv_status()

    def jv_wait_for_download(self, timeout: float = 600.0, poll_interval: float = 1.0) -> bool:
        return self.wait_for_download(timeout, poll_interval)

    def reinitialize_com(self):
        """Reinitialize by restarting the bridge process."""
        logger.warning("Reinitializing bridge (restart subprocess)")
        self.cleanup()
        self._start_process()
        init_key = self.initialization_key or self.sid
        self._send_command({"cmd": "init", "type": "nar", "key": init_key})
