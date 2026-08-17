"""Public setup examples must match the executable provider contract."""

import sys
import tomllib
import re
from pathlib import Path
from unittest.mock import patch

import yaml

from src.jvlink.constants import validate_jvopen_combination
from src.utils.config import Config, get_default_config

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


def test_installer_manual_commands_bind_the_installed_configuration() -> None:
    powershell = (REPOSITORY_ROOT / "install.ps1").read_text(encoding="utf-8").lower()
    batch = (REPOSITORY_ROOT / "install.bat").read_text(encoding="utf-8").lower()

    assert "run: jltsql init" not in powershell
    assert "run: jltsql init" not in batch
    assert 'set-location `"$install_dir`"' in powershell
    assert 'jltsql --config `".\\config\\config.yaml`"' in powershell
    assert 'cd /d "%install_dir%"' in batch
    assert 'jltsql --config "config\\config.yaml"' in batch


def test_automatic_windows_paths_do_not_select_unverified_64_bit_python() -> None:
    batch = (REPOSITORY_ROOT / "install.bat").read_text(encoding="utf-8")
    powershell = (REPOSITORY_ROOT / "install.ps1").read_text(encoding="utf-8")
    quickstart = (REPOSITORY_ROOT / "quickstart.bat").read_text(encoding="utf-8")

    assert "py -3.12 --version" not in batch
    assert "py -3 --version" not in batch
    assert re.search(r'Command = "py"; Arguments = @\("-3\.12"\)', powershell) is None
    assert "py -3.12 --version" not in quickstart
    assert "py -3 -c" not in quickstart


def test_sqlite_bootstrap_does_not_import_an_optional_postgresql_driver() -> None:
    from src.database import create_database_from_config
    from src.database.sqlite_handler import SQLiteDatabase

    with patch.dict(
        sys.modules,
        {
            "src.database.postgresql_handler": None,
            "psycopg": None,
            "pg8000": None,
        },
    ):
        database = create_database_from_config(Config(get_default_config()))

    assert isinstance(database, SQLiteDatabase)


def test_removed_public_setup_contract_is_recorded_for_2_0() -> None:
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    constants = (REPOSITORY_ROOT / "src/jvlink/constants.py").read_text(
        encoding="utf-8"
    )
    project = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert "2.0.0" in changelog
    assert "JVLINK_BRIDGE_RUNNER" in changelog
    assert project["project"]["version"].startswith("2.0.0")
    assert "wrapper.py の JVSetServiceKey 呼び出し箇所" not in constants
    for record_type in range(1, 7):
        assert f"DATA_SPEC_O{record_type} =" not in constants
        assert f"RECORD_TYPE_O{record_type} =" in constants


def test_version_and_lock_metadata_are_consistent() -> None:
    from src import __version__
    from src.cli import main as cli_main

    project = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    lock = tomllib.loads(
        (REPOSITORY_ROOT / "uv.lock").read_text(encoding="utf-8")
    )
    locked_project = next(
        package for package in lock["package"] if package["name"] == "jltsql"
    )

    assert __version__ == project["project"]["version"]
    assert cli_main.__version__ == __version__
    assert locked_project["version"] == __version__


def test_architecture_documents_the_generic_non_windows_runner_contract() -> None:
    architecture = (REPOSITORY_ROOT / "docs/architecture.md").read_text(
        encoding="utf-8"
    )

    assert "JVLINK_BRIDGE_RUNNER" in architecture


def test_2_0_notes_define_the_data_and_rollback_migration_boundary() -> None:
    notes = (REPOSITORY_ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8").lower()
    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower()

    for term in (
        "parser",
        "schema",
        "transaction",
        "backup",
        "rebuild",
        "reimport",
        "docs/data_support.md",
    ):
        assert term in notes
    assert "reimport" in changelog
    assert "rollback" in changelog
