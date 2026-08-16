"""Release-distribution content gate tests."""

import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_distribution_contents import validate_distributions


def _write_wheel(path: Path, members: tuple[str, ...]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, b"fixture")


def _write_sdist(path: Path, members: tuple[str, ...]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for member in members:
            payload = path.parent / "payload"
            payload.write_bytes(b"fixture")
            archive.add(payload, arcname=member)


def _clean_pair(tmp_path: Path) -> tuple[Path, Path]:
    wheel = tmp_path / "jltsql-0-py3-none-any.whl"
    sdist = tmp_path / "jltsql-0.tar.gz"
    _write_wheel(wheel, ("src/__init__.py", "jltsql-0.dist-info/METADATA"))
    _write_sdist(sdist, ("jltsql-0/src/__init__.py", "jltsql-0/pyproject.toml"))
    return wheel, sdist


def test_distribution_gate_accepts_clean_wheel_and_sdist(tmp_path: Path) -> None:
    wheel, sdist = _clean_pair(tmp_path)

    assert validate_distributions((wheel, sdist)) == []


@pytest.mark.parametrize(
    ("artifact", "member"),
    (
        ("wheel", "specs/operations/internal.md"),
        ("sdist", "jltsql-0/specs/operations/internal.md"),
        ("wheel", "docs/crawler_audit_02_ra_extended_layout.md"),
        ("sdist", "jltsql-0/docs/crawler_audit_04_se_layout.md"),
    ),
)
def test_distribution_gate_rejects_nondistributable_content(
    tmp_path: Path,
    artifact: str,
    member: str,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    if artifact == "wheel":
        _write_wheel(wheel, ("src/__init__.py", member))
    else:
        _write_sdist(sdist, ("jltsql-0/src/__init__.py", member))

    errors = validate_distributions((wheel, sdist))

    assert errors
    assert any(member in error for error in errors)


@pytest.mark.parametrize("missing", ("wheel", "sdist"))
def test_distribution_gate_fails_closed_when_an_artifact_kind_is_missing(
    tmp_path: Path,
    missing: str,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    paths = (sdist,) if missing == "wheel" else (wheel,)

    errors = validate_distributions(paths)

    assert errors
    assert any(missing in error for error in errors)
