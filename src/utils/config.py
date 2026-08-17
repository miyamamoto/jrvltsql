"""Configuration management module."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


class ConfigError(Exception):
    """Configuration error exception."""

    pass


class Config:
    """Configuration holder class."""

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize configuration.

        Args:
            config_dict: Configuration dictionary
        """
        self._config = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key
            default: Default value if key not found

        Returns:
            Configuration value

        Examples:
            >>> config.get("databases.sqlite.enabled")
            True
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary syntax.

        Args:
            key: Configuration key

        Returns:
            Configuration value

        Raises:
            KeyError: If key not found
        """
        value = self.get(key)
        if value is None:
            raise KeyError(f"Configuration key not found: {key}")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()


def _expand_env_vars(config: Any) -> Any:
    """Recursively expand environment variables in configuration.

    Supports ${VAR} and ${VAR:default} syntax.

    Args:
        config: Configuration value (dict, list, str, etc.)

    Returns:
        Configuration with expanded environment variables

    Examples:
        ${POSTGRES_HOST:localhost} -> value of POSTGRES_HOST or "localhost"
    """
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Pattern: ${VAR} or ${VAR:default}
        pattern = r"\$\{([^}:]+)(?::([^}]+))?\}"

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) or ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, config)
    else:
        return config


def _validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ConfigError("Configuration root must be a mapping")

    # Check required sections
    if "jvlink" not in config:
        raise ConfigError("Missing required section: jvlink")
    if not isinstance(config["jvlink"], dict):
        raise ConfigError("Section jvlink must be a mapping")

    if "databases" not in config:
        raise ConfigError("Missing required section: databases")
    if not isinstance(config["databases"], dict):
        raise ConfigError("Section databases must be a mapping")

    database_selector = config.get("database", {})
    if not isinstance(database_selector, dict):
        raise ConfigError("Section database must be a mapping")
    selected_database = database_selector.get("type")
    if selected_database is not None:
        if not isinstance(selected_database, str):
            raise ConfigError("database.type must be a string")
        if selected_database not in {"sqlite", "postgresql", "dual"}:
            raise ConfigError(f"Unsupported database.type: {selected_database}")

    # Check at least one database is enabled
    databases = config.get("databases", {})
    if any(not isinstance(db_config, dict) for db_config in databases.values()):
        raise ConfigError("Every databases entry must be a mapping")
    for name, db_config in databases.items():
        enabled = db_config.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ConfigError(f"databases.{name}.enabled must be a boolean")
        path = db_config.get("path")
        if path is not None and not isinstance(path, str):
            raise ConfigError(f"databases.{name}.path must be a string")
    enabled_dbs = [
        name for name, db_config in databases.items() if db_config.get("enabled", False)
    ]

    if not enabled_dbs:
        raise ConfigError("At least one database must be enabled")

    required_backends: tuple[str, ...] = ()
    if selected_database in {"sqlite", "postgresql"}:
        required_backends = (selected_database,)
    elif selected_database == "dual":
        required_backends = ("sqlite", "postgresql")
    for backend in required_backends:
        backend_config = databases.get(backend)
        if not isinstance(backend_config, dict) or not backend_config.get(
            "enabled", False
        ):
            raise ConfigError(
                f"database.type {selected_database} requires enabled "
                f"databases.{backend}"
            )

    logging_config = config.get("logging", {})
    if not isinstance(logging_config, dict):
        raise ConfigError("Section logging must be a mapping")
    logging_level = logging_config.get("level", "INFO")
    if not isinstance(logging_level, str):
        raise ConfigError("logging.level must be a string")
    for subsection in ("file", "console"):
        value = logging_config.get(subsection, {})
        if not isinstance(value, dict):
            raise ConfigError(f"Section logging.{subsection} must be a mapping")
        enabled = value.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ConfigError(f"logging.{subsection}.enabled must be a boolean")
    log_path = logging_config.get("file", {}).get("path")
    if log_path is not None and not isinstance(log_path, str):
        raise ConfigError("logging.file.path must be a string")


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file.
                    If None, looks for config/config.yaml

    Returns:
        Config object

    Raises:
        ConfigError: If configuration file not found or invalid

    Examples:
        >>> config = load_config()
    """
    resolved_path: Path
    if config_path is None:
        # Keep the default writable and identical to the CLI bootstrap path.
        resolved_path = Path.cwd() / "config" / "config.yaml"
    else:
        resolved_path = Path(config_path)

    if not resolved_path.exists():
        raise ConfigError(f"Configuration file not found: {resolved_path}")

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in configuration file: {e}") from e
    except (OSError, UnicodeError) as e:
        raise ConfigError(
            f"Could not read configuration file ({type(e).__name__})"
        ) from e

    if config_dict is None:
        raise ConfigError("Configuration file is empty")

    # Expand environment variables
    config_dict = _expand_env_vars(config_dict)

    # Validate configuration
    _validate_config(config_dict)

    return Config(config_dict)


def get_default_config() -> Dict[str, Any]:
    """Get the safe, self-contained SQLite bootstrap configuration.

    Returns:
        A valid configuration that works without PostgreSQL extras. Optional
        PostgreSQL, monitoring, and advanced settings remain opt-in.
    """
    return {
        "jvlink": {},
        "database": {
            "type": "sqlite",
        },
        "databases": {
            "sqlite": {
                "enabled": True,
                "path": "./data/keiba.db",
                "pragma": {
                    "journal_mode": "WAL",
                    "synchronous": "NORMAL",
                },
            },
        },
        "data_fetch": {
            "initial": {
                "enabled": False,
                "date_from": "2020-01-01",
                "date_to": "2024-12-31",
                "data_specs": ["RACE"],
            },
            "realtime": {
                "enabled": False,
                "interval_seconds": 60,
                "data_specs": ["0B12", "0B15", "0B20", "0B31"],
            },
        },
        "performance": {
            "batch_size": 1000,
            "commit_interval": 10000,
            "max_workers": 4,
        },
        "auto_update_check": False,
        "logging": {
            "level": "INFO",
            "file": {
                "enabled": True,
                "path": "./logs/jltsql.log",
            },
            "console": {
                "enabled": True,
            },
        },
    }
