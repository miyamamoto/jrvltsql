#!/usr/bin/env python3
"""Fail closed when release archives contain non-distributable repository files."""

from __future__ import annotations

import argparse
import re
import tarfile
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

SUPERSEDED_AUDIT_PAGES = frozenset(
    {
        "crawler_audit_01_mining_spec.md",
        "crawler_audit_02_ra_extended_layout.md",
        "crawler_audit_03_we_realtime_spec.md",
        "crawler_audit_04_se_layout.md",
    }
)

SCANNED_TEXT_SUFFIXES = frozenset(
    {
        ".bat",
        ".cfg",
        ".csv",
        ".ini",
        ".json",
        ".md",
        ".ps1",
        ".py",
        ".rst",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SCANNED_TEXT_NAMES = frozenset({"license", "metadata", "record", "wheel"})
MAX_SCANNED_TEXT_BYTES = 4 * 1024 * 1024
SENSITIVE_TEXT_PATTERNS = (
    (
        "credential-shaped value",
        re.compile(
            rb"(?<![A-Z0-9])[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}-[A-Z0-9](?![A-Z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "private runtime provenance",
        re.compile(
            rb"(?is)\b[a-z0-9][a-z0-9_.-]{2,}-(?:runtime|adapter)\b"
            rb".{0,80}\b(?:through|commit)\s+[0-9a-f]{7,40}\b"
        ),
    ),
)


def _artifact_kind(path: Path) -> str | None:
    if path.suffix == ".whl":
        return "wheel"
    if path.name.endswith(".tar.gz"):
        return "sdist"
    return None


def _is_scanned_text_member(member: str) -> bool:
    pure_path = PurePosixPath(member.replace("\\", "/"))
    return (
        pure_path.suffix.lower() in SCANNED_TEXT_SUFFIXES
        or pure_path.name.lower() in SCANNED_TEXT_NAMES
    )


def _archive_entries(
    path: Path,
    kind: str,
) -> Iterable[tuple[str, bytes | None, str | None]]:
    if kind == "wheel":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                payload = None
                error = None
                if not member.is_dir() and _is_scanned_text_member(member.filename):
                    if member.file_size > MAX_SCANNED_TEXT_BYTES:
                        error = "text member exceeds the content-scan size limit"
                    else:
                        payload = archive.read(member)
                yield member.filename, payload, error
        return
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            payload = None
            error = None
            if member.isfile() and _is_scanned_text_member(member.name):
                if member.size > MAX_SCANNED_TEXT_BYTES:
                    error = "text member exceeds the content-scan size limit"
                else:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        error = "text member could not be read"
                    else:
                        payload = extracted.read(MAX_SCANNED_TEXT_BYTES + 1)
                        if len(payload) > MAX_SCANNED_TEXT_BYTES:
                            payload = None
                            error = "text member exceeds the content-scan size limit"
            yield member.name, payload, error


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


def _member_content_error(path: Path, member: str, payload: bytes) -> str | None:
    for category, pattern in SENSITIVE_TEXT_PATTERNS:
        if pattern.search(payload):
            return f"{path.name}: {category} in archive member: {member}"
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
            for member, payload, scan_error in _archive_entries(path, kind):
                error = _member_error(path, member)
                if error is not None:
                    errors.append(error)
                    continue
                if scan_error is not None:
                    errors.append(f"{path.name}: {scan_error}: {member}")
                    continue
                if payload is not None:
                    content_error = _member_content_error(path, member, payload)
                    if content_error is not None:
                        errors.append(content_error)
        except (
            EOFError,
            OSError,
            RuntimeError,
            ValueError,
            tarfile.TarError,
            zipfile.BadZipFile,
        ) as error:
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
