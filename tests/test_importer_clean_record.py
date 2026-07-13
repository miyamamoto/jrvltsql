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
            "RecordSeparator": "\r\n",
        }
        cleaned = self.importer._clean_record(record)
        assert "RecordDelimiter" not in cleaned
        assert "RecordSeparator" not in cleaned
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


def test_jravan_uma_race_import_keeps_all_opponent_slots(tmp_path):
    from src.database.schema_jravan import JRAVAN_SCHEMAS
    from src.database.sqlite_handler import SQLiteDatabase
    from src.importer.importer import DataImporter
    from src.parser.se_parser import SEParser

    raw = bytearray(b" " * 555)
    raw[0:2] = b"SE"
    raw[2:3] = b"7"
    raw[3:11] = b"20260714"
    raw[11:15] = b"2026"
    raw[15:19] = b"0714"
    raw[19:21] = b"05"
    raw[21:23] = b"02"
    raw[23:25] = b"03"
    raw[25:27] = b"11"
    raw[28:30] = b"07"
    raw[393:403] = b"2020100001"
    raw[403:439] = b"WINNER-ONE".ljust(36)
    raw[439:449] = b"2020100002"
    raw[449:485] = b"WINNER-TWO".ljust(36)
    raw[485:495] = b"2020100003"
    raw[495:531] = b"WINNER-THREE".ljust(36)
    raw[531:535] = b"+123"
    raw[552:553] = b"4"
    raw[553:555] = b"\r\n"

    record = SEParser().parse(bytes(raw))
    assert record is not None

    db = SQLiteDatabase({"path": str(tmp_path / "jravan.db")})
    with db:
        db.create_table("UMA_RACE", JRAVAN_SCHEMAS["UMA_RACE"])
        assert db.table_exists("UMA_RACE")
        stats = DataImporter(db, use_jravan_schema=True).import_records(iter([record]))
        row = db.fetch_one(
            "SELECT KettoNum1, Bamei1, KettoNum2, Bamei2, KettoNum3, Bamei3, "
            "TimeDiff, KyakusituKubun FROM UMA_RACE"
        )

    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert row is not None
    columns = (
        "KettoNum1",
        "Bamei1",
        "KettoNum2",
        "Bamei2",
        "KettoNum3",
        "Bamei3",
        "TimeDiff",
        "KyakusituKubun",
    )
    assert tuple(row[column] for column in columns) == (
        "2020100001",
        "WINNER-ONE",
        "2020100002",
        "WINNER-TWO",
        "2020100003",
        "WINNER-THREE",
        "+123",
        "4",
    )


def test_jravan_schema_types_cover_every_declared_sql_type():
    from src.database.schema_types import get_table_column_types

    race_types = get_table_column_types("RACE")
    assert race_types["HassoTime"] == "TEXT"
    assert race_types["Year"] == "INTEGER"
    assert race_types["Kyori"] == "INTEGER"

    se_types = get_table_column_types("UMA_RACE")
    assert se_types["Bamei3"] == "TEXT"
    assert se_types["DMTime"] == "REAL"
