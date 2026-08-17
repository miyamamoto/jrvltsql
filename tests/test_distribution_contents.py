"""Release-distribution content gate tests."""

import hashlib
import tarfile
import zipfile
import zlib
from pathlib import Path

import pytest

from scripts import check_distribution_contents as content_gate
from scripts.check_distribution_contents import validate_distributions
from scripts.smoke_distribution_init import _wheel_cli_command, validate_wheel_init


def _write_wheel(
    path: Path,
    members: tuple[str, ...],
    payload: bytes = b"fixture",
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, payload)


def _corrupt_zip_payload(path: Path, payload: bytes) -> None:
    archive_bytes = bytearray(path.read_bytes())
    payload_offset = archive_bytes.index(payload)
    archive_bytes[payload_offset] ^= 0x01
    path.write_bytes(archive_bytes)


def _write_sdist(
    path: Path,
    members: tuple[str, ...],
    payload: bytes = b"fixture",
) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for member in members:
            payload_path = path.parent / "payload"
            payload_path.write_bytes(payload)
            archive.add(payload_path, arcname=member)


def _write_sdist_link(path: Path, member: str, target: str) -> None:
    with tarfile.open(path, "w:gz") as archive:
        link = tarfile.TarInfo(member)
        link.type = tarfile.SYMTYPE
        link.linkname = target
        archive.addfile(link)


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
        ("wheel", "tests/test_release_surface.py"),
        ("sdist", "jltsql-0/tests/test_release_surface.py"),
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


@pytest.mark.parametrize(
    ("artifact", "payload_parts"),
    (
        (
            "wheel",
            (b'example_key = "ABCD-', b"EFGH-IJKL-MNOP-Q\""),
        ),
        (
            "sdist",
            (
                b"jltsql-private-",
                b"runtime through ",
                b"deadbee acknowledges close",
            ),
        ),
    ),
)
def test_distribution_gate_rejects_sensitive_text_without_echoing_it(
    tmp_path: Path,
    artifact: str,
    payload_parts: tuple[bytes, ...],
) -> None:
    payload = b"".join(payload_parts)
    wheel, sdist = _clean_pair(tmp_path)
    member = "src/release_surface.py"
    if artifact == "wheel":
        _write_wheel(wheel, (member,), payload)
    else:
        member = f"jltsql-0/{member}"
        _write_sdist(sdist, (member,), payload)

    errors = validate_distributions((wheel, sdist))
    rendered = "\n".join(errors)

    assert errors
    assert member in rendered
    assert payload.decode("ascii") not in rendered


@pytest.mark.parametrize(
    ("artifact", "member", "payload"),
    (
        (
            "wheel",
            ".env",
            b"SERVICE_KEY=" + b"".join((b"ABCD-", b"EFGH-IJKL-MNOP-Q")),
        ),
        (
            "sdist",
            "PKG-INFO",
            b"Service-Key: " + b"".join((b"ABCD", b"EFGHIJKLMNOPQ")),
        ),
        (
            "wheel",
            "config/provider.xml",
            b"<key>" + b"".join((b"ABCD", b"EFGHIJKLMNOPQ")) + b"</key>",
        ),
        (
            "wheel",
            "scripts/setup.ps1",
            (
                "service_key = "
                + "".join(("ABCD-", "EFGH-IJKL-MNOP-Q"))
            ).encode("utf-16-le"),
        ),
        (
            "wheel",
            "src/provider.py",
            b"JVSetServiceKey(" + b"".join((b"ABCD", b"EFGHIJKLMNOPQ")) + b")",
        ),
        (
            "wheel",
            "src/provider.py",
            b'key = "ABCD-" "EFGH-" "IJKL-" "MNOP-Q"',
        ),
        (
            "sdist",
            "src/bridge.py",
            b"".join((b"jltsql-private-", b"runtime revision deadbeef")),
        ),
    ),
)
def test_distribution_gate_rejects_sensitive_archive_variants(
    tmp_path: Path,
    artifact: str,
    member: str,
    payload: bytes,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    if artifact == "wheel":
        _write_wheel(wheel, (member,), payload)
    else:
        member = f"jltsql-0/{member}"
        _write_sdist(sdist, (member,), payload)

    assert validate_distributions((wheel, sdist))


def test_distribution_gate_redacts_a_sensitive_member_name(tmp_path: Path) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    secret = "".join(("ABCD-", "EFGH-IJKL-MNOP-Q"))
    member = f"specs/{secret}.txt"
    _write_wheel(wheel, (member,))

    rendered = "\n".join(validate_distributions((wheel, sdist)))

    assert rendered
    assert secret not in rendered


def test_distribution_gate_allows_public_runtime_provenance(tmp_path: Path) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    _write_wheel(
        wheel,
        ("src/release_surface.py",),
        b"public-example-runtime through deadbee",
    )

    assert validate_distributions((wheel, sdist)) == []


def test_distribution_gate_applies_the_hashed_private_token_denylist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    token = b"syntheticrunner"
    monkeypatch.setattr(
        content_gate,
        "PROHIBITED_TOKEN_SHA256",
        frozenset({hashlib.sha256(token).hexdigest()}),
    )
    wheel, sdist = _clean_pair(tmp_path)
    _write_wheel(wheel, ("src/bridge.py",), token)

    assert validate_distributions((wheel, sdist))


def test_distribution_gate_pins_the_private_runner_hash_without_plaintext() -> None:
    assert (
        "3958765b23d8a51d3445d91f98c1e76f62b896d615011d132b4ae85e4331d2fe"
        in content_gate.PROHIBITED_TOKEN_SHA256
    )


@pytest.mark.parametrize(
    "member",
    ("C:/escape.py", "C:\\escape.py", "C:escape.py", "specs./internal.md"),
)
def test_distribution_gate_rejects_windows_absolute_members(
    tmp_path: Path,
    member: str,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    _write_wheel(wheel, (member,))

    assert validate_distributions((wheel, sdist))


def test_distribution_gate_rejects_archive_links(tmp_path: Path) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    _write_sdist_link(
        sdist,
        "jltsql-0/src/linked.py",
        "../../escape.py",
    )

    assert validate_distributions((wheel, sdist))


def test_wheel_smoke_binds_execution_to_the_extracted_wheel(tmp_path: Path) -> None:
    command = _wheel_cli_command(tmp_path, ("init",))

    assert "-I" in command
    assert any("is_relative_to" in argument for argument in command)


def test_wheel_smoke_rejects_a_partial_wheel_despite_an_editable_install(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "jltsql-0-py3-none-any.whl"
    _write_wheel(wheel, ("src/__init__.py",), b'__version__ = "0"')

    assert validate_wheel_init(wheel)


def test_distribution_gate_redacts_sensitive_names_on_crc_failure(
    tmp_path: Path,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)
    secret = "".join(("ABCD-", "EFGH-IJKL-MNOP-Q"))
    payload = b"CRC_UNIQUE_PAYLOAD"
    _write_wheel(wheel, (f"src/{secret}.py",), payload)
    _corrupt_zip_payload(wheel, payload)

    rendered = "\n".join(validate_distributions((wheel, sdist)))

    assert rendered
    assert secret not in rendered


def test_distribution_gate_returns_an_error_for_corrupt_deflate_stream(
    tmp_path: Path,
    monkeypatch,
) -> None:
    wheel, sdist = _clean_pair(tmp_path)

    def corrupt_read(*_args, **_kwargs):
        raise zlib.error("synthetic corrupt stream")

    monkeypatch.setattr(zipfile.ZipFile, "read", corrupt_read)

    assert validate_distributions((wheel, sdist))
