"""Runtime checks for Windows batch interpreter selection.

These tests exercise cmd.exe parsing only.  They do not initialize JV-Link and
must not be used as SDK architecture or provider-acquisition evidence.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows cmd.exe runtime contract",
)

ROOT = Path(__file__).resolve().parents[1]


def _run_batch(
    batch: Path, *args: str, env: dict[str, str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmd.exe", "/d", "/c", "call", str(batch), *args],
        cwd=cwd,
        env=env,
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )


def test_quickstart_accepts_explicit_python_path_with_parentheses(tmp_path):
    """A typical 32-bit installation path must not close an IF block early."""
    python_dir = tmp_path / "Program Files (x86)" / "Python312-32"
    python_dir.mkdir(parents=True)
    wrapper = python_dir / "python.cmd"
    wrapper.write_text(
        f'@echo off\r\n"{sys.executable}" %*\r\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHON"] = str(wrapper)
    env["JLTSQL_SKIP_SCHEDULER_PROMPT"] = "1"
    result = _run_batch(ROOT / "quickstart.bat", "--yes", "--help", env=env, cwd=ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert str(wrapper) in result.stdout


def test_quickstart_rejects_compound_python_override():
    """A command fragment must fail loudly instead of selecting another Python."""
    env = os.environ.copy()
    env["PYTHON"] = "py -3.12-32"
    result = _run_batch(ROOT / "quickstart.bat", "--yes", "--help", env=env, cwd=ROOT)

    assert result.returncode != 0
    assert "PYTHON must be a full path to python.exe" in result.stdout


def test_timeseries_fetch_uses_path_installed_cli_before_global_python(tmp_path):
    """A working PATH CLI must win over unrelated global launcher fallbacks."""
    checkout = tmp_path / "checkout"
    (checkout / "config").mkdir(parents=True)
    batch = checkout / "fetch_timeseries_postgres.bat"
    batch.write_bytes((ROOT / "fetch_timeseries_postgres.bat").read_bytes())
    (checkout / "config" / "config.yaml").write_text("database: {}\n", encoding="utf-8")

    bin_dir = tmp_path / "active bin"
    bin_dir.mkdir()
    (bin_dir / "jltsql.cmd").write_text(
        "@echo off\r\necho PATH_JLTSQL_SELECTED\r\nexit /b 0\r\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.pop("PYTHON", None)
    env.pop("VIRTUAL_ENV", None)
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    result = _run_batch(batch, "20260801", "20260801", env=env, cwd=checkout)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PATH_JLTSQL_SELECTED" in result.stdout
