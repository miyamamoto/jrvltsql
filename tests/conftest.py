"""Shared test fixtures."""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _no_sleep():
    """Automatically mock time.sleep in all tests to avoid real delays."""
    with patch("time.sleep"):
        yield
