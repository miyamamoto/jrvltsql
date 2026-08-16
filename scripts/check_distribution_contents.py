#!/usr/bin/env python3
"""Fail closed when release archives contain non-distributable repository files."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


SUPERSEDED_AUDIT_PAGES = frozenset(
    {
        "crawler_audit_01_mining_spec.md",
        "crawler_audit_02_ra_extended_layout.md",
        "crawler_audit_03_we_realtime_spec.md",
        "crawler_audit_04_se_layout.md",
    }
)


def _artifact_kind(path: Path) -> str | None:
    if path.suffix == ".whl":
        return "wheel"
    if path.name.endswith(".tar.gz"):
        return "sdist"
    return None


def _archive_members(path: Path, kind: str) -> Iterable[str]:
    if kind == "wheel":
        with zipfile.ZipFile(path) as archive:
            yield from archive.namelist()
        return
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            yield member.name


def _member_error(path: Path, member: str) -> str | None:
    normalized = member.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    parts = tuple(part for part in pure_path.parts if part not in {"", "."})
    if pure_path.is_absolute() or ".." in parts:
        return f"{path.name}: unsafe archive member: {member}"
    lowered = tuple(part.lower() for part in parts)
    if "specs" in lowered:
        return f"{path.name}: repository specifications are not distributable: {member}"
    if lowered and lowered[-1] in SUPERSEDED_AUDIT_PAGES:
        return f"{path.name}: superseded audit page is not distributable: {member}"
    return None


def validate_distributions(paths: Sequence[Path]) -> list[str]:
    """Return every content-gate error for the supplied wheel/sdist artifacts."""
    errors: list[str] = []
    artifacts: list[tuple[Path, str]] = []
    observed_kinds: set[str] = set()

    for raw_path in paths:
        path = Path(raw_path)
        kind = _artifact_kind(path)
        if kind is None:
            errors.append(f"unsupported distribution artifact: {path.name}")
            continue
        observed_kinds.add(kind)
        artifacts.append((path, kind))
        if not path.is_file():
            errors.append(f"distribution artifact does not exist: {path}")

    for required_kind in ("wheel", "sdist"):
        if required_kind not in observed_kinds:
            errors.append(f"required {required_kind} artifact is missing")

    for path, kind in artifacts:
        if not path.is_file():
            continue
        try:
            for member in _archive_members(path, kind):
                error = _member_error(path, member)
                if error is not None:
                    errors.append(error)
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
            errors.append(f"could not inspect {path.name}: {error}")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args(argv)

    errors = validate_distributions(args.artifacts)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Distribution content check passed for {len(args.artifacts)} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
