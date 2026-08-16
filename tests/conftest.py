"""Shared test fixtures."""

import os

# Production auto-logging opens configured files during import. Tests exercise
# logging explicitly where needed and must not create repository-local log
# handles merely by collecting modules.
os.environ.setdefault("JLTSQL_SKIP_AUTO_LOGGING", "1")

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _no_sleep():
    """Automatically mock time.sleep in all tests to avoid real delays."""
    with patch("time.sleep"):
        yield
