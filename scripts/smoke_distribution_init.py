#!/usr/bin/env python3
"""Run ``jltsql init`` from an extracted wheel in a fresh writable directory."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path


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
        env["PYTHONPATH"] = str(extract_dir)
        env["PYTHONSAFEPATH"] = "1"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli.main", "init"],
                cwd=run_dir,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=30.0,
            )
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
