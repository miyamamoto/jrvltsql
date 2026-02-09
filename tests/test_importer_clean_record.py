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
