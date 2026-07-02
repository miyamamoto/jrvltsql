#!/usr/bin/env python3
"""Small HTTP runner for the JRA collector container.

The KPS scheduler talks to this service over the Docker network instead of
mounting a collector worktree or reaching out to a Windows host.  The service
accepts a narrow JSON contract and builds the allowed jrvltsql commands itself.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
APP_ROOT = Path(os.getenv("JRA_COLLECTOR_ROOT", "/app"))
DEFAULT_DB = "postgresql"
DEFAULT_LOCK_PATH = "/tmp/jra_collector_service.lock"
DATE_RE = re.compile(r"^\d{8}$")
LOGIN_FAILURE_RE = re.compile(r"(login\s*failed|service\s*key|authentication)", re.IGNORECASE)
DEFAULT_BASE_SETUP_SPECS = "RACE,DIFN"
DEFAULT_BASE_SETUP_OPTION = "4"
SERVICE_KEY_RE = re.compile(r"\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}-[A-Z0-9]\b")
SECRET_ENV_NAMES = (
    "JVLINK_SERVICE_KEY",
    "JRA_VAN_SERVICE_KEY",
)


def _json_response(handler: BaseHTTPRequestHandler, status_code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _today_jst() -> str:
    return datetime.now(JST).strftime("%Y%m%d")


def _validate_date(value: str | None, name: str) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)
    if not DATE_RE.match(text):
        raise ValueError(f"{name} must be YYYYMMDD: {value!r}")
    return text


def _date_window(payload: dict[str, Any]) -> tuple[str, str]:
    date = _validate_date(payload.get("date"), "date")
    from_date = _validate_date(payload.get("from_date"), "from_date")
    to_date = _validate_date(payload.get("to_date"), "to_date")
    if date:
        return date, date
    today = _today_jst()
    start = from_date or today
    end = to_date or from_date or today
    return start, end


def _daily_update_days(from_date: str, to_date: str) -> tuple[int, int]:
    today = datetime.now(JST).date()
    start = datetime.strptime(from_date, "%Y%m%d").date()
    end = datetime.strptime(to_date, "%Y%m%d").date()
    return max(1, (today - start).days), max(0, (end - today).days)


def _python() -> str:
    return os.getenv("JRA_COLLECTOR_PYTHON", "/opt/venv/bin/python")


def _extra_args(env_name: str) -> list[str]:
    value = os.getenv(env_name, "").strip()
    return shlex.split(value) if value else []


def _mode(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("mode") or "").strip()
    if explicit:
        if explicit not in {"base_setup", "odds_and_results", "odds_only", "results_only"}:
            raise ValueError(f"unsupported mode: {explicit}")
        return explicit
    if bool(payload.get("results_only")) and bool(payload.get("no_collect_results")):
        raise ValueError("results_only and no_collect_results cannot both be true")
    if bool(payload.get("results_only")):
        return "results_only"
    if bool(payload.get("no_collect_results")):
        return "odds_only"
    return "odds_and_results"


def _commands(payload: dict[str, Any]) -> tuple[str, list[list[str]]]:
    from_date, to_date = _date_window(payload)
    mode = _mode(payload)
    db = str(payload.get("db") or os.getenv("JRA_COLLECTOR_DB", DEFAULT_DB))
    commands: list[list[str]] = []

    if mode == "base_setup":
        setup_specs = str(
            payload.get("setup_specs")
            or os.getenv("JRA_COLLECTOR_BASE_SETUP_SPECS", DEFAULT_BASE_SETUP_SPECS)
        )
        setup_option = str(
            payload.get("setup_option")
            or os.getenv("JRA_COLLECTOR_BASE_SETUP_OPTION", DEFAULT_BASE_SETUP_OPTION)
        )
        for raw_spec in setup_specs.split(","):
            spec = raw_spec.strip().upper()
            if not spec:
                continue
            command = [
                _python(),
                "-m",
                "src.cli.main",
                "fetch",
                "--from",
                from_date,
                "--to",
                to_date,
                "--spec",
                spec,
                "--option",
                setup_option,
                "--db",
                db,
                "--no-progress",
            ]
            command.extend(_extra_args("JRA_COLLECTOR_BASE_SETUP_EXTRA_ARGS"))
            commands.append(command)
        if not commands:
            raise ValueError("base_setup requires at least one setup spec")
        return mode, commands

    if mode in {"results_only", "odds_and_results"}:
        days_back, days_forward = _daily_update_days(from_date, to_date)
        commands.append(
            [
                _python(),
                "scripts/daily_update.py",
                "--db",
                db,
                "--days-back",
                str(days_back),
                "--days-forward",
                str(days_forward),
                "--specs",
                os.getenv("JRA_COLLECTOR_RESULTS_SPECS", "0B12"),
                *_extra_args("JRA_COLLECTOR_DAILY_UPDATE_EXTRA_ARGS"),
            ]
        )

    if mode in {"odds_only", "odds_and_results"}:
        command = [
            _python(),
            "-m",
            "src.cli.main",
            "realtime",
            "odds-sokuho-timeseries",
            "--from-date",
            from_date,
            "--to-date",
            to_date,
            "--db",
            db,
        ]
        db_path = os.getenv("JRA_COLLECTOR_DB_PATH", "").strip()
        if db_path:
            command.extend(["--db-path", db_path])
        command.extend(_extra_args("JRA_COLLECTOR_SOKUHO_EXTRA_ARGS"))
        commands.append(command)

    return mode, commands


def _tail(text: str, size: int = 1000) -> str:
    redacted = _redact_secrets(text)
    return redacted[-size:] if len(redacted) > size else redacted


def _redact_secrets(text: str) -> str:
    redacted = SERVICE_KEY_RE.sub("***", text or "")
    for name in SECRET_ENV_NAMES:
        value = os.getenv(name, "")
        if value and len(value) >= 8:
            redacted = redacted.replace(value, "***")
            redacted = redacted.replace(re.sub(r"[^A-Za-z0-9]", "", value), "***")
    return redacted


def _detect_login_failure(*texts: str) -> bool:
    return any(LOGIN_FAILURE_RE.search(text or "") for text in texts)


@contextmanager
def _service_lock(path: str, skip_if_running: bool):
    lock_path = Path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if skip_if_running else 0)
        try:
            fcntl.flock(handle.fileno(), flags)
            acquired = True
            handle.seek(0)
            handle.truncate()
            handle.write(f"{os.getpid()} {time.time()}\n")
            handle.flush()
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        if acquired:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    skip_if_running = bool(payload.get("skip_if_running", True))
    lock_path = str(payload.get("lock_path") or os.getenv("JRA_COLLECTOR_SERVICE_LOCK_PATH", DEFAULT_LOCK_PATH))
    with _service_lock(lock_path, skip_if_running) as acquired:
        if not acquired:
            return {"status": "already_running", "reason": "service_lock_held", "lock_path": lock_path}

        mode, commands = _commands(payload)
        timeout_seconds = int(payload.get("timeout_seconds") or os.getenv("JRA_COLLECTOR_TIMEOUT_SECONDS", "600"))
        env = os.environ.copy()
        env.setdefault("PYTHONPATH", str(APP_ROOT))
        started = time.monotonic()
        command_results: list[dict[str, Any]] = []
        final_returncode = 0
        combined_stdout = ""
        combined_stderr = ""

        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    cwd=APP_ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=max(30, timeout_seconds),
                    check=False,
                )
                returncode = int(completed.returncode)
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
            except subprocess.TimeoutExpired as exc:
                returncode = 1
                stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
                stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
                stderr = (stderr + "\n" if stderr else "") + "collector command timeout"

            combined_stdout += stdout
            combined_stderr += stderr
            command_results.append(
                {
                    "command": " ".join(shlex.quote(part) for part in command),
                    "returncode": returncode,
                    "stdout_tail": _tail(stdout),
                    "stderr_tail": _tail(stderr),
                }
            )
            final_returncode = returncode
            if returncode != 0 or _detect_login_failure(stdout, stderr):
                break

        status = "ok"
        if _detect_login_failure(combined_stdout, combined_stderr):
            status = "login_failure"
        elif final_returncode != 0:
            status = "failed"

        return {
            "status": status,
            "executor": "service",
            "kind": "jra",
            "mode": mode,
            "returncode": final_returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "commands": command_results,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "JRACollectorService/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[collector-service] {self.address_string()} - {fmt % args}", file=sys.stderr)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            _json_response(self, 200, {"status": "ok", "kind": "jra"})
            return
        _json_response(self, 404, {"status": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            _json_response(self, 404, {"status": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
            result = run_payload(payload)
            _json_response(self, 200, result)
        except Exception as exc:  # noqa: BLE001 - return JSON to the scheduler.
            _json_response(self, 400, {"status": "failed", "reason": str(exc), "kind": "jra"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", default="jra", choices=["jra"])
    parser.add_argument("--host", default=os.getenv("JRA_COLLECTOR_SERVICE_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("JRA_COLLECTOR_SERVICE_PORT", "8081")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[collector-service] kind=jra listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
