"""Logging configuration module."""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses default path
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
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
        console_handler.setLevel(logging.INFO)
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

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.dev.ConsoleRenderer() if log_to_console else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


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


# Configure default logging on module import
setup_logging()
