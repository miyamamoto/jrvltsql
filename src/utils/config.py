"""Configuration management module."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

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
            key: Dot-separated key (e.g., "jvlink.service_key")
            default: Default value if key not found

        Returns:
            Configuration value

        Examples:
            >>> config.get("jvlink.service_key")
            "YOUR_KEY"
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
        ${JVLINK_SERVICE_KEY} -> value of JVLINK_SERVICE_KEY
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
    # Check required sections
    if "jvlink" not in config:
        raise ConfigError("Missing required section: jvlink")

    if "databases" not in config:
        raise ConfigError("Missing required section: databases")

    # Check at least one database is enabled
    databases = config.get("databases", {})
    enabled_dbs = [
        name for name, db_config in databases.items() if db_config.get("enabled", False)
    ]

    if not enabled_dbs:
        raise ConfigError("At least one database must be enabled")

    # Validate JV-Link service key (if not using env var)
    service_key = config.get("jvlink", {}).get("service_key", "")
    if not service_key or service_key.startswith("${"):
        # Will be expanded from environment variable
        pass
    elif len(service_key) < 10:
        # Assume valid keys are at least 10 characters
        raise ConfigError("Invalid JV-Link service key")

    # NV-Link settings are optional; if present, lightly validate service key format length
    nv_service_key = config.get("nvlink", {}).get("service_key", "")
    if nv_service_key and not nv_service_key.startswith("${") and len(nv_service_key) < 10:
        raise ConfigError("Invalid NV-Link service key")


def load_config(config_path: Optional[str] = None) -> Config:
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
        >>> service_key = config.get("jvlink.service_key")
    """
    if config_path is None:
        # Default config path
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in configuration file: {e}")

    if config_dict is None:
        raise ConfigError("Configuration file is empty")

    # Expand environment variables
    config_dict = _expand_env_vars(config_dict)

    # Validate configuration
    _validate_config(config_dict)

    return Config(config_dict)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration values.

    Returns:
        Default configuration dictionary
    """
    return {
        "jvlink": {
            "service_key": "",
        },
        "nvlink": {
            "service_key": "",
            "initialization_key": "",
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
