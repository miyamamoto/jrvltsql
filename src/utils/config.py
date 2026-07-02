"""Configuration management module."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import parse_qs, unquote, urlparse

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
        # Pattern: ${VAR} or ${VAR:default}.  The default may be empty.
        pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) or ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, config)
    else:
        return config


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _coerce_port(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid PostgreSQL port: {value!r}") from exc


def _postgres_config_from_url(value: str) -> Dict[str, Any]:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ConfigError(
            "PostgreSQL URL must use postgresql:// or postgres:// scheme"
        )

    try:
        port = parsed.port
    except ValueError as exc:
        raise ConfigError(f"Invalid PostgreSQL URL port: {value!r}") from exc

    config: Dict[str, Any] = {}
    if parsed.hostname:
        config["host"] = parsed.hostname
    if port is not None:
        config["port"] = port
    if parsed.path and parsed.path != "/":
        config["database"] = unquote(parsed.path.lstrip("/"))
    if parsed.username:
        config["user"] = unquote(parsed.username)
    if parsed.password:
        config["password"] = unquote(parsed.password)

    query = parse_qs(parsed.query)
    for key in ("sslmode", "connect_timeout"):
        values = query.get(key)
        if values and values[0] != "":
            config[key] = values[0]
    return config


def _apply_postgres_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply PostgreSQL connection overrides from environment variables.

    Operational collectors often run with a single explicit connection URL.
    When a URL is set it must win over generic ``POSTGRES_USER`` etc.; KPS, for
    example, exposes an ETL read-only user in ``POSTGRES_USER`` while
    ``JRVLTSQL_POSTGRES_URL`` carries the ingestion writer credentials.
    """

    databases = config.get("databases")
    if not isinstance(databases, dict):
        return config
    pg_config = databases.get("postgresql")
    if not isinstance(pg_config, dict):
        return config

    url = _first_env("JRVLTSQL_POSTGRES_URL", "POSTGRES_URL", "DATABASE_URL")
    if url:
        pg_config.update(_postgres_config_from_url(url))
        return config

    overrides: Dict[str, Any] = {}
    host = _first_env("POSTGRES_HOST", "PGHOST")
    port = _first_env("POSTGRES_PORT", "PGPORT")
    database = _first_env("POSTGRES_DB", "POSTGRES_DATABASE", "PGDATABASE", "KPS_POSTGRES_DB")
    user = _first_env("POSTGRES_USER", "PGUSER")
    password = _first_env("POSTGRES_PASSWORD", "PGPASSWORD")

    if host:
        overrides["host"] = host
    coerced_port = _coerce_port(port)
    if coerced_port is not None:
        overrides["port"] = coerced_port
    if database:
        overrides["database"] = database
    if user:
        overrides["user"] = user
    if password:
        overrides["password"] = password

    pg_config.update(overrides)
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
        >>> service_key = config.get("jvlink.service_key")
    """
    resolved_path: Path
    if config_path is None:
        # Default config path
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / "config" / "config.yaml"
    else:
        resolved_path = Path(config_path)

    if not resolved_path.exists():
        raise ConfigError(f"Configuration file not found: {resolved_path}")

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in configuration file: {e}")

    if config_dict is None:
        raise ConfigError("Configuration file is empty")

    # Expand environment variables
    config_dict = _expand_env_vars(config_dict)
    config_dict = _apply_postgres_env_overrides(config_dict)

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
