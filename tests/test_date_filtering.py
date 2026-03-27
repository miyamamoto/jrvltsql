"""Test date filtering in historical fetcher.

This test verifies that the to_date parameter correctly filters records.
"""

import pytest
from unittest.mock import MagicMock
from src.fetcher.base import BaseFetcher


class ConcreteFetcher(BaseFetcher):
    """Concrete implementation for testing."""

    def fetch(self, data_spec, from_time, option=1, to_date=None):
        """Mock implementation."""
        return []


class TestDateFiltering:
    """Test date filtering functionality."""

    def test_is_within_date_range_valid_records(self):
        """Test that records within the date range are accepted."""
        # Create fetcher with mocked dependencies
        mock_wrapper = MagicMock()
        fetcher = ConcreteFetcher(mock_wrapper)

        # Test record within range
        record1 = {"Year": "2024", "MonthDay": "0615"}
        assert fetcher._is_within_date_range(record1, "20240630") is True

        # Test record at exact end date
        record2 = {"Year": "2024", "MonthDay": "0630"}
        assert fetcher._is_within_date_range(record2, "20240630") is True

        # Test record before start of range
        record3 = {"Year": "2024", "MonthDay": "0101"}
        assert fetcher._is_within_date_range(record3, "20240630") is True

    def test_is_within_date_range_outside_records(self):
        """Test that records outside the date range are rejected."""
        mock_wrapper = MagicMock()
        fetcher = ConcreteFetcher(mock_wrapper)

        # Test record after end date
        record1 = {"Year": "2024", "MonthDay": "0701"}
        assert fetcher._is_within_date_range(record1, "20240630") is False

        # Test record way past end date
        record2 = {"Year": "2024", "MonthDay": "1231"}
        assert fetcher._is_within_date_range(record2, "20240630") is False

        # Test record in next year
        record3 = {"Year": "2025", "MonthDay": "0101"}
        assert fetcher._is_within_date_range(record3, "20241231") is False

    def test_is_within_date_range_missing_fields(self):
        """Test that records missing date fields are included."""
        mock_wrapper = MagicMock()
        fetcher = ConcreteFetcher(mock_wrapper)

        # Record with no date fields
        record1 = {"SomeField": "Value"}
        assert fetcher._is_within_date_range(record1, "20240630") is True

        # Record with only Year
        record2 = {"Year": "2024"}
        assert fetcher._is_within_date_range(record2, "20240630") is True

        # Record with only MonthDay
        record3 = {"MonthDay": "0615"}
        assert fetcher._is_within_date_range(record3, "20240630") is True

        # Record with empty Year
        record4 = {"Year": "", "MonthDay": "0615"}
        assert fetcher._is_within_date_range(record4, "20240630") is True

    def test_is_within_date_range_edge_cases(self):
        """Test edge cases for date filtering."""
        mock_wrapper = MagicMock()
        fetcher = ConcreteFetcher(mock_wrapper)

        # Test year boundary
        record1 = {"Year": "2023", "MonthDay": "1231"}
        assert fetcher._is_within_date_range(record1, "20240101") is True

        record2 = {"Year": "2024", "MonthDay": "0101"}
        assert fetcher._is_within_date_range(record2, "20231231") is False

        # Test month boundary
        record3 = {"Year": "2024", "MonthDay": "0631"}  # Note: Invalid date but still works
        assert fetcher._is_within_date_range(record3, "20240630") is False

        record4 = {"Year": "2024", "MonthDay": "0629"}
        assert fetcher._is_within_date_range(record4, "20240630") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
