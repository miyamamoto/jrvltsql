#!/usr/bin/env python3
"""Fail closed when release archives contain non-distributable repository files."""

from __future__ import annotations

import argparse
import hashlib
import re
import stat
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

MAX_SCANNED_TEXT_BYTES = 4 * 1024 * 1024
PROHIBITED_TOKEN_SHA256 = frozenset(
    {
        "06a423e23a1131d5c1cd54a44911fc5fd259a4cbbaa5c9a13344a2d73baf5bbd",
        "08c64f088046a0504f39c8b52ed474483d642ac4efdee5211a54ad41a10684e8",
        "1487241b177b0353807ec09be32c409de832fc657c93f7ed5eb23b444708d7e7",
        "32c4feed996880bc92a062dc476f9b8cdb2596a989f2cc5246e9cef605bd5c78",
        "454e0f9c502a52a6c351c9614bac911e22d42908a87dcaf47467645b6001fb17",
        "594f63ba499f2248fdf20c6472a7527a13be1a96e0642615c7f045bf886c3405",
        "684be438b04d22074ca4bb4b1d83bac553d09e3c02680e1ee3a4936d8af22a0a",
        "73c8f9e2b5ef6864b87be7deda7fbeb12fcb1d8b90ade6e36e410b183a23f0a3",
        "8f3d03ddd4e6e26a782e700bb5b5f9e405526fda47eb4e26d5ed5024754e6bed",
        "ae18045e96b66b0e460c7d45703e60e6c26967378f1c0075e64c6e4a08cd3adc",
        "b8e53cd98b9bf7af29cbc6e4fa20d26399e6bc9d0e3e8fba32ae6d447fafacf5",
        "d64983e3ffe1b4e6a14c21d6de24f74a430abc60974cfebaaa2d6ae6ed27e37b",
        "f20bdf9f71ec0c4226a026cc6a982947d203cba6cd877186df673f3e6120c122",
        "f428ec1505fba1faf17b898419f19035cc5f0a3348a83dfbc51d3e9216c93b00",
        "fce60e2787277f5ac2251efd16d6516604a30278e4c457c8c6f74e98631bbcdc",
    }
)
SENSITIVE_TEXT_PATTERNS = (
    (
        "credential-shaped value",
        re.compile(
            rb"(?<![A-Z0-9])[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}-[A-Z0-9](?![A-Z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "credential-shaped value",
        re.compile(
            rb"(?:service[_ -]?key|<key>)\s*[:=>\"']*\s*"
            rb"[A-Z0-9]{17}(?![A-Z0-9])",
            re.IGNORECASE,
        ),
    ),
    (
        "private project runtime identifier",
        re.compile(
            rb"\b(?:jrvltsql|jltsql)-"
            rb"(?:[a-z0-9_.-]+-)?(?:runtime|adapter)\b",
            re.IGNORECASE,
        ),
    ),
)
TOKEN_PATTERN = re.compile(rb"[A-Za-z][A-Za-z0-9_.+]{2,}")


def _artifact_kind(path: Path) -> str | None:
    if path.suffix == ".whl":
        return "wheel"
    if path.name.endswith(".tar.gz"):
        return "sdist"
    return None


def _sensitive_category(payload: bytes) -> str | None:
    variants = (payload, payload.replace(b"\x00", b""))
    for candidate in variants:
        for category, pattern in SENSITIVE_TEXT_PATTERNS:
            if pattern.search(candidate):
                return category
        for token in TOKEN_PATTERN.findall(candidate):
            digest = hashlib.sha256(token.lower()).hexdigest()
            if digest in PROHIBITED_TOKEN_SHA256:
                return "private runner identifier"
    return None


def _artifact_label(path: Path) -> str:
    if _sensitive_category(path.name.encode("utf-8", errors="replace")):
        return "<redacted-artifact>"
    return path.name


def _member_label(member: str) -> str:
    if _sensitive_category(member.encode("utf-8", errors="replace")):
        return "<redacted-member>"
    return member


def _archive_entries(
    path: Path,
    kind: str,
) -> Iterable[tuple[str, bytes | None, str | None]]:
    if kind == "wheel":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                payload = None
                error = None
                member_type = (member.external_attr >> 16) & 0o170000
                if stat.S_ISLNK(member_type):
                    error = "archive links are not permitted"
                elif not member.is_dir():
                    if member.file_size > MAX_SCANNED_TEXT_BYTES:
                        error = "member exceeds the content-scan size limit"
                    else:
                        payload = archive.read(member)
                yield member.filename, payload, error
        return
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            payload = None
            error = None
            if member.issym() or member.islnk() or member.isdev():
                error = "archive links and device members are not permitted"
            elif member.isfile():
                if member.size > MAX_SCANNED_TEXT_BYTES:
                    error = "member exceeds the content-scan size limit"
                else:
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        error = "member could not be read"
                    else:
                        payload = extracted.read(MAX_SCANNED_TEXT_BYTES + 1)
                        if len(payload) > MAX_SCANNED_TEXT_BYTES:
                            payload = None
                            error = "member exceeds the content-scan size limit"
            yield member.name, payload, error


def _member_error(path: Path, member: str) -> str | None:
    normalized = member.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    parts = tuple(part for part in pure_path.parts if part not in {"", "."})
    path_label = _artifact_label(path)
    member_label = _member_label(member)
    if (
        pure_path.is_absolute()
        or ".." in parts
        or re.match(r"^[A-Za-z]:/", normalized)
        or normalized.startswith("//")
    ):
        return f"{path_label}: unsafe archive member: {member_label}"
    lowered = tuple(part.lower() for part in parts)
    if "specs" in lowered:
        return (
            f"{path_label}: repository specifications are not distributable: "
            f"{member_label}"
        )
    if lowered and lowered[-1] in SUPERSEDED_AUDIT_PAGES:
        return (
            f"{path_label}: superseded audit page is not distributable: "
            f"{member_label}"
        )
    return None


def _member_content_error(path: Path, member: str, payload: bytes) -> str | None:
    category = _sensitive_category(payload)
    if category is not None:
        return (
            f"{_artifact_label(path)}: {category} in archive member: "
            f"{_member_label(member)}"
        )
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
            errors.append(f"unsupported distribution artifact: {_artifact_label(path)}")
            continue
        observed_kinds.add(kind)
        artifacts.append((path, kind))
        if not path.is_file():
            errors.append(
                f"distribution artifact does not exist: {_artifact_label(path)}"
            )

    for required_kind in ("wheel", "sdist"):
        if required_kind not in observed_kinds:
            errors.append(f"required {required_kind} artifact is missing")

    for path, kind in artifacts:
        if not path.is_file():
            continue
        try:
            for member, payload, scan_error in _archive_entries(path, kind):
                name_category = _sensitive_category(
                    member.encode("utf-8", errors="replace")
                )
                if name_category is not None:
                    errors.append(
                        f"{_artifact_label(path)}: {name_category} in archive "
                        "member name: <redacted-member>"
                    )
                    continue
                error = _member_error(path, member)
                if error is not None:
                    errors.append(error)
                    continue
                if scan_error is not None:
                    errors.append(
                        f"{_artifact_label(path)}: {scan_error}: "
                        f"{_member_label(member)}"
                    )
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
            errors.append(f"could not inspect {_artifact_label(path)}: {error}")

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
