"""Runtime checks for Windows batch interpreter selection.

These tests exercise cmd.exe parsing only.  They do not initialize JV-Link and
must not be used as SDK architecture or provider-acquisition evidence.
"""

import os
import subprocess
import sys
import venv
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
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    batch = checkout / "quickstart.bat"
    batch.write_bytes((ROOT / "quickstart.bat").read_bytes())
    (checkout / "scripts" / "quickstart.py").write_text(
        "import sys\n"
        'print(f"REAL_PYTHON_SELECTED={sys.executable}")\n',
        encoding="utf-8",
    )

    python_dir = tmp_path / "Program Files (x86)" / "Python312-32"
    venv.EnvBuilder(with_pip=False).create(python_dir)
    interpreter = python_dir / "Scripts" / "python.exe"

    env = os.environ.copy()
    env["PYTHON"] = str(interpreter)
    env["JLTSQL_SKIP_SCHEDULER_PROMPT"] = "1"
    result = _run_batch(batch, "--yes", "--help", env=env, cwd=checkout)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"REAL_PYTHON_SELECTED={interpreter}".lower() in result.stdout.lower()


def test_quickstart_rejects_compound_python_override():
    """A command fragment must fail loudly instead of selecting another Python."""
    env = os.environ.copy()
    env["PYTHON"] = "py -3.12-32"
    result = _run_batch(ROOT / "quickstart.bat", "--yes", "--help", env=env, cwd=ROOT)

    assert result.returncode != 0
    assert "PYTHON must be a full path to python.exe" in result.stdout


def test_quickstart_rejects_invalid_active_virtual_environment(tmp_path):
    """An invalid active environment must fail loudly, not fall back."""
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    batch = checkout / "quickstart.bat"
    batch.write_bytes((ROOT / "quickstart.bat").read_bytes())
    (checkout / "scripts" / "quickstart.py").write_text(
        'print("UNEXPECTED_FALLBACK")\n',
        encoding="utf-8",
    )

    active_env = tmp_path / "invalid active env"
    scripts_dir = active_env / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "python.exe").write_bytes(b"not-a-windows-executable")

    env = os.environ.copy()
    env.pop("PYTHON", None)
    env["VIRTUAL_ENV"] = str(active_env)
    env["JLTSQL_SKIP_SCHEDULER_PROMPT"] = "1"
    result = _run_batch(batch, "--yes", "--help", env=env, cwd=checkout)

    assert result.returncode != 0
    assert "VIRTUAL_ENV must point to 32-bit Python 3.12 or later" in result.stdout
    assert "UNEXPECTED_FALLBACK" not in result.stdout


def test_timeseries_fetch_requires_an_explicit_cli_override(tmp_path):
    """PATH-only commands are ignored; an explicit validated command is used."""
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
    path_only = _run_batch(batch, "20260801", "20260801", env=env, cwd=checkout)

    assert path_only.returncode != 0
    assert "PATH_JLTSQL_SELECTED" not in path_only.stdout

    env["JLTSQL"] = f'"{bin_dir / "jltsql.cmd"}"'
    explicit = _run_batch(batch, "20260801", "20260801", env=env, cwd=checkout)

    assert explicit.returncode == 0, explicit.stdout + explicit.stderr
    assert "PATH_JLTSQL_SELECTED" in explicit.stdout


def test_daily_sync_preserves_password_without_command_line_exposure(tmp_path):
    """PostgreSQL passwords must survive cmd metacharacters via the environment."""
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    batch = checkout / "daily_sync.bat"
    batch.write_bytes((ROOT / "daily_sync.bat").read_bytes())
    (checkout / "scripts" / "quickstart.py").write_text(
        "import os\n"
        "import sys\n"
        "preserved = (\n"
        "    os.environ.get('PGPASSWORD')\n"
        "    == os.environ.get('EXPECTED_PASSWORD')\n"
        ")\n"
        'print(f"PASSWORD_PRESERVED={preserved}")\n'
        'print(f"PASSWORD_ON_COMMAND_LINE={\'--pg-password\' in sys.argv}")\n',
        encoding="utf-8",
    )

    synthetic_password = "p@ss!word&caret^percent%done"
    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    env["POSTGRES_PASSWORD"] = synthetic_password
    env["EXPECTED_PASSWORD"] = synthetic_password
    result = _run_batch(batch, "--days-back", "0", env=env, cwd=checkout)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASSWORD_PRESERVED=True" in result.stdout
    assert "PASSWORD_ON_COMMAND_LINE=False" in result.stdout
