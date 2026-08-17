#!/usr/bin/env python3
"""Run ``jltsql init`` from an extracted wheel in a fresh writable directory."""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path


_WHEEL_BOOTSTRAP = """
import builtins
import pathlib
import runpy
import sys

wheel_root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(wheel_root))
import src

module_origin = pathlib.Path(src.__file__).resolve()
if not module_origin.is_relative_to(wheel_root):
    raise RuntimeError("jltsql was not imported from the extracted wheel")

if sys.argv[2] == "1":
    real_import = builtins.__import__

    def import_without_optional_postgresql(name, *args, **kwargs):
        if name == "psycopg" or name.startswith("psycopg."):
            raise ImportError("optional PostgreSQL driver disabled by wheel smoke")
        if name == "pg8000" or name.startswith("pg8000."):
            raise ImportError("optional PostgreSQL driver disabled by wheel smoke")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = import_without_optional_postgresql

sys.argv = ["jltsql", *sys.argv[3:]]
runpy.run_module("src.cli.main", run_name="__main__")
"""


def _wheel_cli_command(
    extract_dir: Path,
    arguments: Sequence[str],
    *,
    block_postgresql: bool = True,
) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-c",
        _WHEEL_BOOTSTRAP,
        str(extract_dir),
        "1" if block_postgresql else "0",
        *arguments,
    ]


def _run_wheel_cli(
    extract_dir: Path,
    run_dir: Path,
    env: dict[str, str],
    arguments: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _wheel_cli_command(extract_dir, arguments),
        cwd=run_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30.0,
    )


def validate_wheel_init(wheel: Path) -> list[str]:
    errors: list[str] = []
    if not wheel.is_file() or wheel.suffix != ".whl":
        return [f"wheel artifact does not exist: {wheel}"]

    with (
        tempfile.TemporaryDirectory(prefix="jltsql-wheel-extract-") as extract_raw,
        tempfile.TemporaryDirectory(prefix="jltsql-wheel-init-") as run_raw,
    ):
        extract_dir = Path(extract_raw)
        run_dir = Path(run_raw)
        try:
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(extract_dir)
        except (OSError, zipfile.BadZipFile) as error:
            return [f"could not extract wheel {wheel.name}: {error}"]

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONSAFEPATH"] = "1"
        private_home = run_dir / ".home"
        private_state = run_dir / ".state"
        private_home.mkdir()
        private_state.mkdir()
        env["HOME"] = str(private_home)
        env["USERPROFILE"] = str(private_home)
        env["LOCALAPPDATA"] = str(private_state)
        env["XDG_STATE_HOME"] = str(private_state)
        try:
            result = _run_wheel_cli(extract_dir, run_dir, env, ("init",))
        except subprocess.TimeoutExpired:
            return ["wheel init timed out after 30 seconds"]
        if result.returncode != 0:
            errors.append(f"wheel init exited {result.returncode}")
            return errors

        for relative_path, expected_kind in (
            (Path("config/config.yaml"), "file"),
            (Path("data"), "directory"),
            (Path("logs"), "directory"),
        ):
            candidate = run_dir / relative_path
            if expected_kind == "file" and not candidate.is_file():
                errors.append(f"wheel init did not create file: {relative_path}")
            if expected_kind == "directory" and not candidate.is_dir():
                errors.append(f"wheel init did not create directory: {relative_path}")

        if "service key" in result.stdout.lower():
            errors.append("wheel init printed retired config service-key guidance")

        commands = (
            (("config", "--show"), "Type: sqlite"),
            (("version",), "version"),
            (("create-tables", "--db", "sqlite"), None),
        )
        for arguments, required_output in commands:
            try:
                command_result = _run_wheel_cli(
                    extract_dir,
                    run_dir,
                    env,
                    arguments,
                )
            except subprocess.TimeoutExpired:
                errors.append(f"wheel {' '.join(arguments)} timed out")
                continue
            if command_result.returncode != 0:
                errors.append(
                    f"wheel {' '.join(arguments)} exited "
                    f"{command_result.returncode}"
                )
                continue
            if required_output and required_output not in command_result.stdout:
                errors.append(
                    f"wheel {' '.join(arguments)} omitted expected output"
                )
            if "unknown" in command_result.stdout.lower():
                errors.append(
                    f"wheel {' '.join(arguments)} reported an unknown value"
                )

        sqlite_path = run_dir / "data" / "keiba.db"
        if not sqlite_path.is_file():
            errors.append("wheel SQLite bootstrap did not create data/keiba.db")
        else:
            with sqlite3.connect(sqlite_path) as connection:
                table_count = connection.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
                ).fetchone()[0]
            if table_count == 0:
                errors.append("wheel SQLite bootstrap created no tables")

        for forbidden in (
            extract_dir / "logs" / "jltsql.log",
            extract_dir / "data" / ".update_check.json",
        ):
            if forbidden.exists():
                errors.append("wheel command wrote runtime state into the package tree")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)

    errors = validate_wheel_init(args.wheel)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Wheel init smoke passed: {args.wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
