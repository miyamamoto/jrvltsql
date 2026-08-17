"""Public setup examples must match the executable provider contract."""

from pathlib import Path

import yaml

from src.jvlink.constants import validate_jvopen_combination

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_public_setup_uses_supported_registration_and_dataspecs() -> None:
    public_setup_files = (
        REPOSITORY_ROOT / "install.ps1",
        REPOSITORY_ROOT / "install.bat",
        REPOSITORY_ROOT / "src/cli/main.py",
        REPOSITORY_ROOT / "src/fetcher/base.py",
    )
    stale_guidance = (
        "set your jv-link service key",
        "set your service keys",
        "service key can be provided programmatically",
    )
    for path in public_setup_files:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(guidance in text for guidance in stale_guidance), path

    config = yaml.safe_load(
        (REPOSITORY_ROOT / "config/config.yaml.example").read_text(
            encoding="utf-8"
        )
    )
    data_specs = config["data_fetch"]["initial"]["data_specs"]
    assert data_specs
    for data_spec in data_specs:
        validate_jvopen_combination(data_spec, 1)
