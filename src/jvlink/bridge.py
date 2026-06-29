"""JV-Link Bridge Client (JRA/中央競馬).

Communicates with the C# JVLinkBridge subprocess via stdin/stdout JSON protocol.
This replaces the Python win32com-based JVLinkWrapper, eliminating:
- 32-bit Python requirement
- COM threading/marshaling issues
- win32com dependency

Platform support:
- Windows (native): Runs JVLinkBridge.exe directly
- Linux (Wine): Runs via 'wine JVLinkBridge.exe' with COM DLLs registered in Wine
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, TextIO, Tuple

from src.jvlink.constants import (
    BUFFER_SIZE_JVREAD,
    JV_READ_NO_MORE_DATA,
    JV_READ_SUCCESS,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default bridge executable locations (searched in order)
_BRIDGE_SEARCH_PATHS = [
    # Native Win32 bridge (preferred for Wine; no .NET runtime dependency)
    Path("tools/jvlink-bridge/bin/native/JVLinkBridge.exe"),
    # Relative to jrvltsql repo root (build output)
    Path("tools/jvlink-bridge/bin/x86/Release/net8.0-windows/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/Release/net8.0-windows/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/x86/Release/net48/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/Release/net48/JVLinkBridge.exe"),
    # Relative to jrvltsql repo root (flat copy)
    Path("tools/jvlink-bridge/JVLinkBridge.exe"),
    # Generic Windows locations
    Path(r"C:\Program Files\JVLinkBridge\JVLinkBridge.exe"),
    Path(r"C:\Program Files (x86)\JVLinkBridge\JVLinkBridge.exe"),
]

# Linux-specific paths (Wine environment)
_BRIDGE_SEARCH_PATHS_LINUX = [
    Path("/opt/jvlink-bridge/JVLinkBridge.exe"),
    Path.home() / "jvlink-bridge" / "JVLinkBridge.exe",
    Path("tools/jvlink-bridge/bin/native/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/x86/Release/net48/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/x86/Release/net8.0-windows/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/JVLinkBridge.exe"),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _wine_executable() -> str:
    return os.environ.get("JVLINK_WINE", "wine")


def _is_wine_available(wine: Optional[str] = None) -> bool:
    """Check if Wine is installed and available."""
    return shutil.which(wine or _wine_executable()) is not None


def _looks_like_windows_path(path: str) -> bool:
    return (
        len(path) >= 3
        and path[1] == ":"
        and path[2] in ("\\", "/")
    ) or path.startswith("\\\\")


def find_bridge_executable() -> Optional[Path]:
    """Find the JVLinkBridge executable.

    On Linux, also checks Linux-specific paths for Wine-based execution.

    Returns:
        Path to JVLinkBridge.exe, or None if not found.
    """
    # Environment variable override
    env_path = os.environ.get("JVLINK_BRIDGE_EXE")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return p

    search_paths = _BRIDGE_SEARCH_PATHS_LINUX if sys.platform != "win32" else _BRIDGE_SEARCH_PATHS

    for p in search_paths:
        p = p.expanduser()
        if p.is_absolute() and p.exists():
            return p
        if not p.is_absolute():
            for base in (Path.cwd(), _repo_root()):
                abs_p = base / p
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
        self._use_wine = sys.platform != "win32"
        self._wine = _wine_executable()
        self._stderr_file: Optional[TextIO] = None

        if bridge_path:
            self._bridge_path = Path(bridge_path)
        else:
            self._bridge_path = find_bridge_executable()

        if self._bridge_path is None or not self._bridge_path.exists():
            raise JVLinkBridgeError(
                "JVLinkBridge.exe が見つかりません。"
                "tools/jvlink-bridge/ にビルド済みバイナリを配置してください。"
            )

        logger.info(
            "JVLinkBridge initialized",
            bridge_path=str(self._bridge_path),
            sid=sid,
            use_wine=self._use_wine,
            wine=self._wine if self._use_wine else None,
        )

    def _build_command(self) -> list[str]:
        if not self._use_wine:
            return [str(self._bridge_path)]

        if not _is_wine_available(self._wine):
            raise JVLinkBridgeError(
                "Linux環境ではWineが必要です。"
                "wine32/wine をインストールし、必要なら JVLINK_WINE に実行ファイルを指定してください。"
            )
        return [self._wine, str(self._bridge_path)]

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self._use_wine:
            env.setdefault("WINEDEBUG", "-all")
        wineprefix = env.get("JVLINK_WINEPREFIX")
        if wineprefix:
            env["WINEPREFIX"] = wineprefix
        winearch = env.get("JVLINK_WINEARCH")
        if winearch:
            env["WINEARCH"] = winearch
        return env

    def _open_stderr_file(self) -> TextIO:
        if self._stderr_file is not None:
            try:
                self._stderr_file.close()
            except Exception:
                pass
        self._stderr_file = tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace")
        return self._stderr_file

    def _stderr_tail(self, limit: int = 4000) -> str:
        if self._stderr_file is None:
            return ""
        try:
            self._stderr_file.flush()
            self._stderr_file.seek(0)
            data = self._stderr_file.read()
            return data[-limit:]
        except Exception:
            return ""

    def _to_wine_path(self, path: str) -> str:
        if not self._use_wine or _looks_like_windows_path(path):
            return path

        winepath = shutil.which("winepath")
        if winepath:
            try:
                result = subprocess.run(
                    [winepath, "-w", path],
                    env=self._build_env(),
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                converted = result.stdout.strip()
                if result.returncode == 0 and converted:
                    return converted
            except Exception:
                pass

        return "Z:" + str(Path(path)).replace("/", "\\")

    def _start_process(self):
        if self._process is not None and self._process.poll() is None:
            return

        logger.info("Starting JVLinkBridge subprocess", path=str(self._bridge_path), wine=self._use_wine)

        cmd = self._build_command()
        stderr_file = self._open_stderr_file()

        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self._build_env(),
            )

            response = self._read_response(timeout=10.0)
            if response.get("status") != "ready":
                raise JVLinkBridgeError(
                    f"Bridge failed to start: {response.get('error', 'unknown')}. "
                    f"stderr: {self._stderr_tail()}"
                )
            logger.info("JVLinkBridge subprocess ready", version=response.get("version"))
        except Exception:
            self.cleanup()
            raise

    def _send_command(self, cmd: dict, timeout: Optional[float] = None) -> dict:
        if self._process is None or self._process.poll() is not None:
            raise JVLinkBridgeError("Bridge process is not running")
        if self._process.stdin is None:
            raise JVLinkBridgeError("Bridge stdin is not available")

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

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise JVLinkBridgeError(
                    f"Bridge response timeout ({timeout}s). stderr: {self._stderr_tail()}"
                )

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
                thread.join(timeout=remaining)

                if thread.is_alive():
                    raise JVLinkBridgeError(
                        f"Bridge response timeout ({timeout}s). stderr: {self._stderr_tail()}"
                    )
                if error[0]:
                    raise JVLinkBridgeError(f"Bridge read error: {error[0]}")
                line = result[0]
            else:
                import select
                ready, _, _ = select.select([self._process.stdout], [], [], remaining)
                if not ready:
                    raise JVLinkBridgeError(
                        f"Bridge response timeout ({timeout}s). stderr: {self._stderr_tail()}"
                    )
                line = self._process.stdout.readline()

            if not line:
                raise JVLinkBridgeError(
                    f"Bridge terminated unexpectedly. stderr: {self._stderr_tail()}"
                )

            raw = line.strip().lstrip("\ufeff")
            if not raw:
                continue

            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                if not raw.startswith("{"):
                    logger.warning("Ignoring non-JSON bridge output", line=raw[:200])
                    continue
                raise JVLinkBridgeError(
                    f"Invalid JSON from bridge: {raw!r}: {e}. stderr: {self._stderr_tail()}"
                )

    # =========================================================================
    # JV-Link API Methods
    # =========================================================================

    def jv_init(self) -> int:
        self._start_process()
        response = self._send_command({"cmd": "init", "type": "jra", "key": self.sid})

        code = response.get("code", -1)
        if code != 0:
            raise JVLinkBridgeError(
                response.get("error", "JVInit failed"), error_code=code
            )

        logger.info("JV-Link initialized via bridge", code=code)
        return code

    def jv_set_service_key(self, service_key: str) -> int:
        """Set service key via COM bridge.

        Args:
            service_key: JRA-VAN DataLab service key (without dashes).
        """
        self._start_process()
        response = self._send_command({"cmd": "setservicekey", "servicekey": service_key})
        code = response.get("code", -1)
        if response.get("status") == "error" and "code" not in response:
            raise JVLinkBridgeError(response.get("error", "JVSetServiceKey failed"))
        if code != 0:
            logger.warning("JVSetServiceKey returned non-zero", code=code)
        return code

    def jv_set_save_path(self, path: str) -> int:
        """Set the data save path.

        Args:
            path: Directory path for JV-Data files (Windows path format).
        """
        self._start_process()
        response = self._send_command({"cmd": "setsavepath", "path": self._to_wine_path(path)})
        if response.get("status") == "error" and "code" not in response:
            raise JVLinkBridgeError(response.get("error", "JVSetSavePath failed"))
        return response.get("code", -1)

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

        # JVRTOpen returns positive N (= readcount) on success.
        # Normalize to match JVLinkWrapper contract: (JV_RT_SUCCESS, N).
        if code >= 0:
            read_count = code if read_count == 0 else read_count
            self._is_open = True
            return JV_READ_SUCCESS, read_count
        elif code == -1:
            return code, 0
        else:
            raise JVLinkBridgeError("JVRTOpen failed", error_code=code)

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
        if self._stderr_file is not None:
            try:
                self._stderr_file.close()
            except Exception:
                pass
            self._stderr_file = None

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
