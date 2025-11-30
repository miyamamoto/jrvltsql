"""Logging configuration module."""

import logging
import logging.config
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

import structlog
import yaml


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    console_level: str = "ERROR",
) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default path
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        console_level: Console log level (default: ERROR - only critical errors)
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        if log_file is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = str(log_dir / "jltsql.log")
        else:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    handlers = []

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.upper()))
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)

    if log_to_file and log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )

    # Configure structlog to use stdlib integration (respects handler levels)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Update handlers with structlog formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
        ],
    )
    for handler in handlers:
        handler.setFormatter(formatter)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting data import", records=1000)
        >>> logger.error("Import failed", error=str(e))
    """
    return structlog.get_logger(name)


def setup_logging_from_config(config: dict) -> None:
    """Setup logging from configuration dictionary.

    Args:
        config: Configuration dictionary with logging settings

    Examples:
        >>> from src.utils.config import load_config
        >>> config = load_config()
        >>> setup_logging_from_config(config.to_dict())
    """
    logging_config = config.get("logging", {})

    level = logging_config.get("level", "INFO")
    file_config = logging_config.get("file", {})
    console_config = logging_config.get("console", {})

    log_to_file = file_config.get("enabled", True)
    log_to_console = console_config.get("enabled", True)
    log_file = file_config.get("path", None) if log_to_file else None

    setup_logging(
        level=level,
        log_file=log_file,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
    )


def setup_logging_from_yaml(config_path: Optional[str] = None) -> None:
    """Setup logging from YAML configuration file.

    This function loads logging configuration from a YAML file and applies it.
    The YAML file should follow Python's logging.config.dictConfig format.

    Supports:
    - RotatingFileHandler: Size-based log rotation
    - TimedRotatingFileHandler: Time-based log rotation (hourly, daily, weekly)
    - Multiple handlers with different rotation strategies
    - Custom formatters and log levels per logger

    Args:
        config_path: Path to logging.yaml file. If None, uses default config/logging.yaml

    Examples:
        >>> setup_logging_from_yaml()  # Uses default config
        >>> setup_logging_from_yaml("custom_logging.yaml")

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "config" / "logging.yaml")

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Logging config file not found: {config_path}")

    # Load YAML configuration
    with open(config_file, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Create log directory if it doesn't exist
    if 'handlers' in config_dict:
        for handler_name, handler_config in config_dict['handlers'].items():
            if 'filename' in handler_config:
                log_file = Path(handler_config['filename'])
                log_file.parent.mkdir(parents=True, exist_ok=True)

    # Apply logging configuration
    logging.config.dictConfig(config_dict)


def get_rotation_info() -> dict:
    """Get information about current log rotation settings.

    Returns:
        Dictionary with rotation information for each handler

    Examples:
        >>> info = get_rotation_info()
        >>> print(info['file']['type'])  # 'RotatingFileHandler'
        >>> print(info['file']['maxBytes'])  # 104857600
    """
    rotation_info = {}

    for handler in logging.getLogger().handlers:
        handler_name = handler.__class__.__name__
        info = {'type': handler_name}

        if isinstance(handler, logging.handlers.RotatingFileHandler):
            info.update({
                'filename': handler.baseFilename,
                'maxBytes': handler.maxBytes,
                'backupCount': handler.backupCount,
            })
        elif isinstance(handler, logging.handlers.TimedRotatingFileHandler):
            info.update({
                'filename': handler.baseFilename,
                'when': handler.when,
                'interval': handler.interval,
                'backupCount': handler.backupCount,
            })

        rotation_info[handler_name] = info

    return rotation_info


# Configure default logging on module import
# Try to load from YAML first, fall back to basic setup
try:
    setup_logging_from_yaml()
except (FileNotFoundError, yaml.YAMLError):
    setup_logging()
