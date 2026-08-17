#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for log rotation functionality."""

import logging
import logging.handlers
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.utils.logger import (
    setup_logging,
    setup_logging_from_yaml,
    get_rotation_info,
)


class TestLogRotation(unittest.TestCase):
    """Test log rotation configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name) / 'logs'
        self.log_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove all handlers to avoid interference between tests
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        self.temp_dir.cleanup()

    def test_default_log_file_uses_the_writable_current_directory(self):
        expected = Path(self.temp_dir.name) / "logs" / "jltsql.log"
        with patch(
            "src.utils.logger.Path.cwd",
            return_value=Path(self.temp_dir.name),
        ):
            setup_logging(log_to_console=False)

        self.assertTrue(expected.is_file())

    def test_rotating_file_handler_created(self):
        """Test that RotatingFileHandler is created with correct settings."""
        log_file = str(self.log_dir / 'test.log')

        setup_logging(
            level="INFO",
            log_file=log_file,
            log_to_console=False,
            log_to_file=True,
        )

        # Check that a RotatingFileHandler was created
        handlers = logging.getLogger().handlers
        rotating_handlers = [
            h for h in handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        self.assertEqual(len(rotating_handlers), 1)

        handler = rotating_handlers[0]
        self.assertEqual(handler.maxBytes, 100 * 1024 * 1024)  # 100MB
        self.assertEqual(handler.backupCount, 5)

    def test_log_rotation_on_size_limit(self):
        """Test that log file rotates when size limit is reached."""
        log_file = str(self.log_dir / 'test_size.log')

        # Create handler with small max size for testing
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=1024,  # 1KB for testing
            backupCount=3,
        )
        handler.setLevel(logging.INFO)

        logger = logging.getLogger('test_rotation')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Write enough data to trigger rotation
        for i in range(100):
            logger.info(f"Test log message {i} - " + "x" * 100)

        handler.close()

        # Check that backup files were created
        log_path = Path(log_file)
        backup_files = list(log_path.parent.glob(f"{log_path.name}.*"))

        self.assertGreater(len(backup_files), 0, "Backup files should be created")

    def test_setup_logging_from_yaml_default(self):
        """Test loading logging configuration from default YAML file."""
        # This should load config/logging.yaml
        try:
            setup_logging_from_yaml()

            # Check that handlers were created
            logger = logging.getLogger()
            self.assertGreater(len(logger.handlers), 0)

        except FileNotFoundError:
            self.skipTest("config/logging.yaml not found")

    def test_setup_logging_from_yaml_custom(self):
        """Test loading logging configuration from custom YAML file."""
        # Create custom YAML config
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'filename': str(self.log_dir / 'custom.log'),
                    'maxBytes': 50 * 1024 * 1024,  # 50MB
                    'backupCount': 7,
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['file']
            }
        }

        config_file = Path(self.temp_dir.name) / 'logging.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        # Load custom config
        setup_logging_from_yaml(str(config_file))

        # Verify handler was created with correct settings
        handlers = logging.getLogger().handlers
        rotating_handlers = [
            h for h in handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        self.assertEqual(len(rotating_handlers), 1)
        handler = rotating_handlers[0]
        self.assertEqual(handler.maxBytes, 50 * 1024 * 1024)
        self.assertEqual(handler.backupCount, 7)

    def test_timed_rotating_file_handler(self):
        """Test TimedRotatingFileHandler configuration."""
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'timed_file': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'filename': str(self.log_dir / 'timed.log'),
                    'when': 'midnight',
                    'interval': 1,
                    'backupCount': 30,
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['timed_file']
            }
        }

        config_file = Path(self.temp_dir.name) / 'timed_logging.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        setup_logging_from_yaml(str(config_file))

        # Verify TimedRotatingFileHandler was created
        handlers = logging.getLogger().handlers
        timed_handlers = [
            h for h in handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        self.assertEqual(len(timed_handlers), 1)
        handler = timed_handlers[0]
        self.assertEqual(handler.when, 'MIDNIGHT')
        # Note: interval is stored in seconds for midnight (86400 = 1 day)
        self.assertEqual(handler.interval, 86400)
        self.assertEqual(handler.backupCount, 30)

    def test_get_rotation_info(self):
        """Test getting rotation information from configured handlers."""
        log_file = str(self.log_dir / 'info_test.log')

        setup_logging(
            level="INFO",
            log_file=log_file,
            log_to_console=False,
            log_to_file=True,
        )

        rotation_info = get_rotation_info()

        # Should have rotation info for at least one handler
        self.assertGreater(len(rotation_info), 0)

        # Check that RotatingFileHandler info is present
        rotating_info = [
            info for name, info in rotation_info.items()
            if info['type'] == 'RotatingFileHandler'
        ]

        self.assertGreater(len(rotating_info), 0)

        # Verify info contains expected fields
        info = rotating_info[0]
        self.assertIn('filename', info)
        self.assertIn('maxBytes', info)
        self.assertIn('backupCount', info)

    def test_multiple_handlers_with_different_rotation(self):
        """Test multiple handlers with different rotation strategies."""
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'size_based': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'filename': str(self.log_dir / 'size_based.log'),
                    'maxBytes': 10 * 1024 * 1024,
                    'backupCount': 5,
                },
                'time_based': {
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'level': 'DEBUG',
                    'formatter': 'simple',
                    'filename': str(self.log_dir / 'time_based.log'),
                    'when': 'midnight',
                    'interval': 1,
                    'backupCount': 7,
                }
            },
            'root': {
                'level': 'DEBUG',
                'handlers': ['size_based', 'time_based']
            }
        }

        config_file = Path(self.temp_dir.name) / 'multi_logging.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        setup_logging_from_yaml(str(config_file))

        # Verify both handler types were created
        handlers = logging.getLogger().handlers

        rotating_handlers = [
            h for h in handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
            and not isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        timed_handlers = [
            h for h in handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]

        self.assertEqual(len(rotating_handlers), 1)
        self.assertEqual(len(timed_handlers), 1)

    def test_yaml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing config file."""
        with self.assertRaises(FileNotFoundError):
            setup_logging_from_yaml("/nonexistent/path/logging.yaml")

    def test_log_directory_auto_creation(self):
        """Test that log directory is created automatically."""
        nested_log_dir = self.log_dir / 'nested' / 'deep'
        log_file = str(nested_log_dir / 'test.log')

        # Directory doesn't exist yet
        self.assertFalse(nested_log_dir.exists())

        setup_logging(
            level="INFO",
            log_file=log_file,
            log_to_console=False,
            log_to_file=True,
        )

        # Directory should be created
        self.assertTrue(nested_log_dir.exists())


class TestRotationWithLogging(unittest.TestCase):
    """Test actual logging with rotation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name) / 'logs'
        self.log_dir.mkdir(exist_ok=True)

        # Remove all handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def tearDown(self):
        """Clean up."""
        # Remove all handlers
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        self.temp_dir.cleanup()

    def test_actual_logging_to_rotated_file(self):
        """Test that actual log messages are written to rotated files."""
        log_file = str(self.log_dir / 'app.log')

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=500,  # Very small for testing
            backupCount=3,
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        logger = logging.getLogger('test_app')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Write logs
        for i in range(50):
            logger.info(f"Application log message {i}")

        handler.close()

        # Check that log file exists
        self.assertTrue(Path(log_file).exists())

        # Read and verify log content
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('Application log message', content)


if __name__ == '__main__':
    unittest.main()
