"""JV-Link Bridge Client (JRA/中央競馬).

Communicates with the C# JVLinkBridge subprocess via stdin/stdout JSON protocol.
This provides an out-of-process alternative to the Python win32com-based
JVLinkWrapper. Supported runtime architectures are established by release E2E
evidence, not by the process boundary alone.

Platform support:
- Windows: runs JVLinkBridge.exe directly
- Non-Windows: runs JVLinkBridge.exe through an explicitly configured external
  runner. The runner implementation belongs to the deployment environment and
  is not selected or documented by this package.
"""

import base64
import binascii
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, TextIO, Tuple

from src.jvlink.constants import (
    BUFFER_SIZE_JVREAD,
    JV_READ_NO_MORE_DATA,
    JV_READ_SUCCESS,
    validate_jvopen_combination,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JVLinkBridgeError(Exception):
    """JV-Link Bridge related error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code})"
        super().__init__(message)


def _bridge_error_suffix(response: dict) -> str:
    """Keep the runner's own diagnostic text on a protocol violation.

    A bridge that cannot create the JV-Link COM object answers with an error
    string and no result code; dropping it leaves the operator with nothing to
    act on when JV-Link is simply not installed in the prefix.
    """

    error = response.get("error")
    return f": {error}" if isinstance(error, str) and error else ""


def _require_response_code(response: dict, command: str) -> int:
    if "code" not in response:
        raise JVLinkBridgeError(
            f"{command} response has no result code{_bridge_error_suffix(response)}"
        )
    code = response["code"]
    if type(code) is not int:
        raise JVLinkBridgeError(
            f"{command} response result code is not an integer: {code!r}"
            f"{_bridge_error_suffix(response)}"
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
    # Native Win32 bridge (no .NET runtime dependency)
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

_BRIDGE_SEARCH_PATHS_NON_WINDOWS = [
    Path("/opt/jvlink-bridge/JVLinkBridge.exe"),
    Path.home() / "jvlink-bridge" / "JVLinkBridge.exe",
    Path("tools/jvlink-bridge/bin/native/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/x86/Release/net48/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/bin/x86/Release/net8.0-windows/JVLinkBridge.exe"),
    Path("tools/jvlink-bridge/JVLinkBridge.exe"),
]

# These are exact X11 title regular expressions for JV-Link dialogs proven to
# block a headless JVOpen/JVRTOpen call.  Escape selects the non-affirmative
# path; Return is deliberately not used because the DataLab update prompt
# focuses its "yes" button by default.
_DISMISSIBLE_DIALOG_TITLE_PATTERNS = (
    r"^JRA-VAN DataLab\.$",
    r"^JRA-VANからのお知らせ$",
)
_ENABLED_VALUES = {"1", "true", "yes", "on"}
_DISABLED_VALUES = {"0", "false", "no", "off"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _external_runner() -> Optional[str]:
    value = os.environ.get("JVLINK_BRIDGE_RUNNER", "").strip()
    return value or None


def _is_runner_available(runner: Optional[str]) -> bool:
    return runner is not None and shutil.which(runner) is not None


def find_bridge_executable() -> Optional[Path]:
    """Find the JVLinkBridge executable.

    Returns:
        Path to JVLinkBridge.exe, or None if not found.
    """
    env_path = os.environ.get("JVLINK_BRIDGE_EXE")
    if env_path:
        candidate = Path(env_path).expanduser()
        if not candidate.is_file():
            raise JVLinkBridgeError(
                "JVLINK_BRIDGE_EXE must point to a JVLinkBridge.exe file: "
                f"{candidate}"
            )
        return candidate

    search_paths = (
        _BRIDGE_SEARCH_PATHS_NON_WINDOWS
        if sys.platform != "win32"
        else _BRIDGE_SEARCH_PATHS
    )
    for p in search_paths:
        p = p.expanduser()
        if p.is_absolute() and p.is_file():
            return p
        if not p.is_absolute():
            for base in (Path.cwd(), _repo_root()):
                candidate = base / p
                if candidate.is_file():
                    return candidate
    return None


class JVLinkBridge:
    """JV-Link Bridge Client for JRA (中央競馬).

    Spawns the C# bridge subprocess with type="jra" to use JVDTLab.JVLink COM.
    Provides the same interface as JVLinkWrapper for drop-in replacement.

    The client itself does not import win32com/pythoncom. End-to-end support
    still depends on a validated bridge, JV-Link installation, and matching
    runtime architecture.

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
        self._use_external_runner = sys.platform != "win32"
        self._runner = _external_runner()
        self._stderr_file: Optional[TextIO] = None
        self._dialog_watcher_stop: Optional[threading.Event] = None
        self._dialog_watcher_thread: Optional[threading.Thread] = None

        if bridge_path is not None:
            self._bridge_path = Path(bridge_path)
        else:
            self._bridge_path = find_bridge_executable()

        if self._bridge_path is None or not self._bridge_path.is_file():
            raise JVLinkBridgeError(
                "JVLinkBridge.exe が見つかりません。"
                "tools/jvlink-bridge/ にビルド済みバイナリを配置してください。"
            )

        logger.info(
            "JVLinkBridge initialized",
            bridge_path=str(self._bridge_path),
            sid=sid,
            use_external_runner=self._use_external_runner,
            runner_configured=self._runner is not None,
        )

    @property
    def uses_external_runner(self) -> bool:
        return self._use_external_runner

    def _build_command(self) -> list[str]:
        if not self._use_external_runner:
            return [str(self._bridge_path)]
        if not _is_runner_available(self._runner):
            raise JVLinkBridgeError(
                "Non-Windows bridge execution requires JVLINK_BRIDGE_RUNNER "
                "to name an available external runner executable"
            )
        return [self._runner, str(self._bridge_path)]

    def _build_env(self) -> dict[str, str]:
        """Map the JV-Link settings onto the variables the runner understands.

        A Wine runner reads WINEPREFIX/WINEARCH, so the prefix holding
        the registered JV-Link is selected through JVLINK_WINEPREFIX and
        JVLINK_WINEARCH without the caller having to export Wine's own
        variables to the whole process.
        """

        env = os.environ.copy()
        if self._use_external_runner:
            env.setdefault("WINEDEBUG", "-all")
        wineprefix = env.get("JVLINK_WINEPREFIX")
        if wineprefix:
            env["WINEPREFIX"] = wineprefix
        winearch = env.get("JVLINK_WINEARCH")
        if winearch:
            env["WINEARCH"] = winearch
        return env

    def _dialog_watcher_enabled(self) -> bool:
        if not self._use_external_runner:
            return False
        value = os.environ.get("JVLINK_AUTO_CLOSE_DIALOGS", "1").lower()
        if value in _DISABLED_VALUES:
            return False
        if value not in _ENABLED_VALUES and value != "":
            logger.warning(
                "Ignoring invalid JVLINK_AUTO_CLOSE_DIALOGS value",
                value=value,
            )
            return False
        return bool(os.environ.get("DISPLAY")) and shutil.which("xdotool") is not None

    def _dismiss_known_dialogs_once(self) -> int:
        """Reject only known blocking JV-Link dialogs visible on this X display."""
        if not self._use_external_runner or not os.environ.get("DISPLAY"):
            return 0
        if shutil.which("xdotool") is None:
            return 0
        process = self._process
        if process is None or process.poll() is not None:
            return 0

        dismissed = 0
        env = self._build_env()
        for pattern in _DISMISSIBLE_DIALOG_TITLE_PATTERNS:
            try:
                result = subprocess.run(
                    [
                        "xdotool",
                        "search",
                        "--onlyvisible",
                        "--pid",
                        str(process.pid),
                        "--name",
                        pattern,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                    check=False,
                    env=env,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if result.returncode != 0:
                continue
            for window_id in result.stdout.split():
                try:
                    action = subprocess.run(
                        [
                            "xdotool",
                            "windowactivate",
                            window_id,
                            "key",
                            "Escape",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.0,
                        check=False,
                        env=env,
                    )
                except (OSError, subprocess.SubprocessError):
                    continue
                if action.returncode == 0:
                    dismissed += 1
                    logger.info(
                        "Rejected blocking JV-Link dialog",
                        title_pattern=pattern,
                    )
        return dismissed

    def _dialog_watch_interval(self) -> float:
        raw_value = os.environ.get(
            "JVLINK_DIALOG_WATCH_INTERVAL_SECONDS", "0.5"
        )
        try:
            interval = float(raw_value)
        except ValueError:
            interval = math.nan
        if not math.isfinite(interval):
            logger.warning(
                "Invalid JVLINK_DIALOG_WATCH_INTERVAL_SECONDS; using 0.5"
            )
            return 0.5
        return max(interval, 0.1)

    def _ensure_dialog_watcher(self) -> None:
        if not self._dialog_watcher_enabled():
            return
        if (
            self._dialog_watcher_thread is not None
            and self._dialog_watcher_thread.is_alive()
        ):
            return

        interval = self._dialog_watch_interval()
        stop = threading.Event()

        def _watch() -> None:
            while not stop.wait(interval):
                self._dismiss_known_dialogs_once()

        self._dialog_watcher_stop = stop
        self._dialog_watcher_thread = threading.Thread(
            target=_watch,
            name="jvlink-dialog-watcher",
            daemon=True,
        )
        self._dialog_watcher_thread.start()

    def _stop_dialog_watcher(self) -> None:
        if self._dialog_watcher_stop is not None:
            self._dialog_watcher_stop.set()
        if (
            self._dialog_watcher_thread is not None
            and self._dialog_watcher_thread.is_alive()
        ):
            self._dialog_watcher_thread.join(timeout=2.0)
        self._dialog_watcher_stop = None
        self._dialog_watcher_thread = None

    def _open_stderr_file(self) -> TextIO:
        if self._stderr_file is not None:
            try:
                self._stderr_file.close()
            except OSError:
                pass
        self._stderr_file = tempfile.TemporaryFile(
            mode="w+t", encoding="utf-8", errors="replace"
        )
        return self._stderr_file

    def _stderr_tail(self, limit: int = 4000) -> str:
        if self._stderr_file is None:
            return ""
        try:
            self._stderr_file.flush()
            self._stderr_file.seek(0)
            return self._stderr_file.read()[-limit:]
        except (OSError, ValueError):
            return ""

    def _close_stderr_file(self) -> None:
        if self._stderr_file is not None:
            try:
                self._stderr_file.close()
            except OSError:
                pass
            self._stderr_file = None

    def _abort_process(self) -> None:
        """Terminate a bridge whose protocol state can no longer be trusted."""
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5.0)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=5.0)
                except Exception:
                    pass
        self._is_open = False
        self._needs_close = False
        self._download_count = None
        self._stop_dialog_watcher()
        self._close_stderr_file()

    def _response_timeout(self, timeout: float) -> JVLinkBridgeError:
        stderr_tail = self._stderr_tail()
        self._abort_process()
        suffix = f". stderr: {stderr_tail}" if stderr_tail else ""
        return JVLinkBridgeError(f"Bridge response timeout ({timeout}s){suffix}")

    def _start_process(self):
        if self._process is not None and self._process.poll() is None:
            return

        logger.info(
            "Starting JVLinkBridge subprocess",
            path=str(self._bridge_path),
            external_runner=self._use_external_runner,
        )

        command = self._build_command()
        stderr_file = self._open_stderr_file()
        try:
            self._process = subprocess.Popen(
                command,
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
                    "Bridge failed to start: "
                    f"{response.get('error', 'unknown')}. stderr: {self._stderr_tail()}"
                )
            logger.info(
                "JVLinkBridge subprocess ready", version=response.get("version")
            )
        except Exception:
            self._abort_process()
            raise

    def _send_command(self, cmd: dict, timeout: Optional[float] = None) -> dict:
        if self._process is None or self._process.poll() is not None:
            raise JVLinkBridgeError("Bridge process is not running")

        if self._process.stdin is None:
            raise JVLinkBridgeError("Bridge stdin is not available")

        timeout = self._timeout if timeout is None else timeout
        cmd_json = json.dumps(cmd, ensure_ascii=False)
        self._ensure_dialog_watcher()

        try:
            self._process.stdin.write(cmd_json + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            self._abort_process()
            raise JVLinkBridgeError(f"Failed to send command: {exc}") from exc

        return self._read_response(timeout=timeout)

    def _read_response(self, timeout: float = 30.0) -> dict:
        if self._process is None:
            raise JVLinkBridgeError("Bridge process is not running")

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise self._response_timeout(timeout)

            process = self._process
            if process is None or process.stdout is None:
                raise JVLinkBridgeError("Bridge stdout is not available")

            result = [None]
            error = [None]

            def _read(
                process=process,
                result=result,
                error=error,
            ):
                try:
                    result[0] = process.stdout.readline()
                except Exception as exc:
                    error[0] = exc

            thread = threading.Thread(target=_read, daemon=True)
            thread.start()
            thread.join(timeout=remaining)

            if thread.is_alive():
                raise self._response_timeout(timeout)
            if error[0]:
                self._abort_process()
                raise JVLinkBridgeError(f"Bridge read error: {error[0]}")
            line = result[0]

            if not line:
                stderr_output = self._stderr_tail()
                self._abort_process()
                raise JVLinkBridgeError(
                    f"Bridge terminated unexpectedly. stderr: {stderr_output}"
                )

            raw = line.strip().lstrip("\ufeff")
            if not raw:
                continue

            try:
                response = json.loads(raw)
            except json.JSONDecodeError as exc:
                if not raw.startswith("{"):
                    logger.warning("Ignoring non-JSON bridge output", line=raw[:200])
                    continue
                stderr_output = self._stderr_tail()
                self._abort_process()
                raise JVLinkBridgeError(
                    f"Invalid JSON from bridge: {raw!r}: {exc}. "
                    f"stderr: {stderr_output}"
                ) from exc
            if not isinstance(response, dict):
                self._abort_process()
                raise JVLinkBridgeError(
                    "Invalid JSON from bridge: response is not an object"
                )
            return response

    # =========================================================================
    # JV-Link API Methods
    # =========================================================================

    def jv_init(self) -> int:
        self._start_process()
        response = self._send_command({"cmd": "init", "type": "jra", "key": self.sid})

        code = _require_response_code(response, "JVInit")
        if code != 0:
            raise JVLinkBridgeError(
                response.get("error", "JVInit failed"), error_code=code
            )

        logger.info("JV-Link initialized via bridge", code=code)
        return code

    def jv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        # JVRTOpen realtime IDs are a separate namespace; this guard applies
        # the official four-character JVOpen contract before transmission.
        validate_jvopen_combination(data_spec, option)

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
            # Older bridge protocol revisions acknowledge close with only
            # {"status":"ok"}. Preserve compatibility until every deployed
            # bridge propagates JVClose's official Long result code.
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
        # Current bridge protocol revisions serialize the COM JVFiledelete
        # return value as ``code``. A missing value is a protocol violation,
        # not an implicit success.
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
        self._close_stderr_file()
        self._stop_dialog_watcher()

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
