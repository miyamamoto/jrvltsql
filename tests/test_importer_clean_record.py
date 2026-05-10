"""Tests for importer _clean_record method — metadata field filtering."""

import pytest
from unittest.mock import MagicMock


class TestCleanRecord:
    """Test that _clean_record removes metadata fields."""

    def setup_method(self):
        from src.importer.importer import DataImporter
        mock_db = MagicMock()
        self.importer = DataImporter(mock_db)

    def test_removes_record_delimiter(self):
        """RecordDelimiter should be removed from records."""
        record = {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "RecordDelimiter": "\r\n",
        }
        cleaned = self.importer._clean_record(record)
        assert "RecordDelimiter" not in cleaned
        assert "RecordSpec" in cleaned
        assert "DataKubun" in cleaned

    def test_removes_head_record_spec(self):
        """headRecordSpec should be removed."""
        record = {"headRecordSpec": "RA", "JyoCD": "01"}
        cleaned = self.importer._clean_record(record)
        assert "headRecordSpec" not in cleaned
        assert "JyoCD" in cleaned

    def test_removes_underscore_prefixed(self):
        """Fields starting with _ should be removed."""
        record = {"_raw_data": b"...", "_parse_errors": [], "JyoCD": "01"}
        cleaned = self.importer._clean_record(record)
        assert "_raw_data" not in cleaned
        assert "_parse_errors" not in cleaned
        assert "JyoCD" in cleaned

    def test_preserves_normal_fields(self):
        """Normal fields should be preserved."""
        record = {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "MakeDate": "20260209",
            "KaisaiDate": "20260209",
        }
        cleaned = self.importer._clean_record(record)
        assert len(cleaned) == 4


def test_convert_record_types_drops_schema_external_fields():
    """Shared converter should not pass parser metadata to database INSERT."""
    from src.importer.importer import convert_record_types

    converted = convert_record_types(
        {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "Year": "2026",
            "RecordDelimiter": "\r\n",
            "UnexpectedParserField": "x",
        },
        "RT_RA",
    )

    assert converted["RecordSpec"] == "RA"
    assert converted["Year"] == 2026
    assert "RecordDelimiter" not in converted
    assert "UnexpectedParserField" not in converted


def test_convert_record_types_maps_masked_numeric_to_null():
    """JV-Data masked numeric values should become NULL for typed columns."""
    from src.importer.importer import convert_record_types

    converted = convert_record_types(
        {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "Year": "****",
        },
        "RT_RA",
    )

    assert converted["Year"] is None
