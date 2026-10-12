"""Test date filtering in historical fetcher.

This test verifies that the to_date parameter correctly filters records.
"""

import pytest
from src.fetcher.base import BaseFetcher


class ConcreteFetcher(BaseFetcher):
    """Concrete implementation for testing."""

    def fetch(self, data_spec, from_time, option=1, to_date=None):
        """Mock implementation."""
        return []


class TestDateFiltering:
    """Test date filtering functionality."""

    @pytest.fixture
    def fetcher(self):
        """Date filtering does not require a live JV-Link wrapper."""
        return ConcreteFetcher.__new__(ConcreteFetcher)

    def test_is_within_date_range_valid_records(self, fetcher):
        """Test that records within the date range are accepted."""
        # Create fetcher with mocked dependencies
        # Test record within range
        record1 = {"Year": "2024", "MonthDay": "0615"}
        assert fetcher._is_within_date_range(record1, "20240630") is True

        # Test record at exact end date
        record2 = {"Year": "2024", "MonthDay": "0630"}
        assert fetcher._is_within_date_range(record2, "20240630") is True

        # Test record before start of range
        record3 = {"Year": "2024", "MonthDay": "0101"}
        assert fetcher._is_within_date_range(record3, "20240630") is True

    def test_is_within_date_range_outside_records(self, fetcher):
        """Test that records outside the date range are rejected."""
        # Test record after end date
        record1 = {"Year": "2024", "MonthDay": "0701"}
        assert fetcher._is_within_date_range(record1, "20240630") is False

        # Test record way past end date
        record2 = {"Year": "2024", "MonthDay": "1231"}
        assert fetcher._is_within_date_range(record2, "20240630") is False

        # Test record in next year
        record3 = {"Year": "2025", "MonthDay": "0101"}
        assert fetcher._is_within_date_range(record3, "20241231") is False

        # HC/WC training records carry the event date in ChokyoDate.
        assert fetcher._is_within_date_range(
            {"RecordSpec": "HC", "ChokyoDate": "20240701"},
            "20240630",
        ) is False
        assert fetcher._is_within_date_range(
            {"RecordSpec": "WC", "ChokyoDate": "20240630"},
            "20240630",
        ) is True

    def test_is_within_date_range_missing_fields(self, fetcher):
        """Test that records missing date fields are included."""
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

    def test_is_within_date_range_edge_cases(self, fetcher):
        """Test edge cases for date filtering."""
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

    def test_integer_month_day_from_parsers(self, fetcher):
        """CK/TC/JC/CC/WE parsers return MonthDay as an int (MONTH_DAY: "0105" -> 105).

        Concatenating it unpadded made "2026105" sort after "20261011", so every
        January-September record of the to_date's year was dropped.
        """
        from src.parser.converters import convert_value

        def record(year: str, month_day: str) -> dict:
            return {
                "Year": convert_value(year, "SMALLINT"),
                "MonthDay": convert_value(month_day, "MONTH_DAY"),
            }

        assert record("2026", "0105") == {"Year": 2026, "MonthDay": 105}
        for month_day in ("0101", "0105", "0630", "0930", "1001", "1011"):
            assert fetcher._is_within_date_range(record("2026", month_day), "20261011") is True
        assert fetcher._is_within_date_range(record("2026", "1012"), "20261011") is False
        assert fetcher._is_within_date_range(record("2025", "1231"), "20261011") is True
        assert fetcher._is_within_date_range(record("2027", "0101"), "20261011") is False
        # a to_date early in the year must not drop or keep by string accident either
        assert fetcher._is_within_date_range(record("2026", "0310"), "20260315") is True
        assert fetcher._is_within_date_range(record("2026", "0316"), "20260315") is False


def test_cache_event_date_accepts_integer_month_day():
    """The NL cache buckets records by event date; int MonthDay must not lose it."""
    from src.fetcher.historical import _extract_record_date
    from src.parser.converters import convert_value

    record = {
        "Year": convert_value("2026", "SMALLINT"),
        "MonthDay": convert_value("0105", "MONTH_DAY"),
    }
    assert _extract_record_date(record) == "20260105"
    assert _extract_record_date({"Year": "2026", "MonthDay": "0105"}) == "20260105"
    assert _extract_record_date({"Year": 2026, "MonthDay": 1011}) == "20261011"
    assert _extract_record_date({"Year": "26", "MonthDay": "0105"}) is None
    assert _extract_record_date({"ChokyoDate": "20260105"}) == "20260105"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
