#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for RA Parser with JRA-VAN standard format."""

import unittest

from src.parser.ra_parser import RAParser as RAParserJRAVAN


class TestRAParserJRAVAN(unittest.TestCase):
    """Test RA parser with type conversions."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = RAParserJRAVAN()

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        self.assertEqual(self.parser.RECORD_TYPE, "RA")
        self.assertEqual(self.parser.RECORD_LENGTH, 856)

    def test_field_names(self):
        """Test field names match JRA-VAN standard."""
        # Parse a minimal record to get field names
        sample_data = b"RA1" + b" " * 853  # Minimal 856-byte record
        result = self.parser.parse(sample_data)
        field_names = result.keys()

        # Check key fields exist with standard names
        self.assertIn("RecordSpec", field_names)
        self.assertIn("MakeDate", field_names)
        self.assertIn("Year", field_names)
        self.assertIn("MonthDay", field_names)
        self.assertIn("JyoCD", field_names)
        self.assertIn("Kaiji", field_names)
        self.assertIn("RaceNum", field_names)
        self.assertIn("Kyori", field_names)
        self.assertIn("HassoTime", field_names)
        self.assertIn("TorokuTosu", field_names)
        self.assertIn("Honsyokin1", field_names)
        # Lap times are in single LapTime field in this parser
        self.assertIn("LapTime", field_names)

    def test_parse_sample_record(self):
        """Test parsing a sample RA record.

        Note: RAParser returns all values as strings (no type conversion).
        Type conversion is done by the importer/database layer.
        """
        # Create a minimal valid RA record
        sample_data = (
            b"RA"                          # RecordSpec (2)
            b"1"                           # DataKubun (1)
            b"20231115"                    # MakeDate (8)
            b"2023"                        # Year (4)
            b"1115"                        # MonthDay (4)
            b"06"                          # JyoCD (2) - Tokyo
            b"03"                          # Kaiji (2)
            b"08"                          # Nichiji (2)
            b"11"                          # RaceNum (2)
        )
        # Pad to 856 bytes
        sample_data += b" " * (856 - len(sample_data))

        result = self.parser.parse(sample_data)

        # RAParser returns strings for all fields
        self.assertEqual(result["RecordSpec"], "RA")
        self.assertEqual(result["DataKubun"], "1")
        self.assertEqual(result["MakeDate"], "20231115")
        self.assertEqual(result["Year"], "2023")
        self.assertEqual(result["MonthDay"], "1115")
        self.assertEqual(result["JyoCD"], "06")
        self.assertEqual(result["Kaiji"], "03")
        self.assertEqual(result["Nichiji"], "08")
        self.assertEqual(result["RaceNum"], "11")

    def test_extended_layout_reads_post_time_from_late_offsets(self):
        """Recent RA payloads can carry post time after extended prize arrays."""

        sample_data = bytearray(b" " * 1270)
        sample_data[0:2] = b"RA"
        sample_data[2:3] = b"7"
        sample_data[3:11] = b"20260508"
        sample_data[11:15] = b"2026"
        sample_data[15:19] = b"0508"
        sample_data[19:21] = b"05"
        sample_data[21:23] = b"02"
        sample_data[23:25] = b"03"
        sample_data[25:27] = b"12"
        # Old 856-byte offset contains prize/previous-prize digits in the
        # extended layout and must not be used as the post time.
        sample_data[745:749] = b"0000"
        sample_data[873:877] = b"1540"
        sample_data[877:881] = b"1535"
        sample_data[881:883] = b"18"
        sample_data[883:885] = b"16"
        sample_data[885:887] = b"16"
        sample_data[887:888] = b"2"
        sample_data[888:889] = b"1"
        sample_data[889:890] = b"1"

        result = self.parser.parse(bytes(sample_data))

        self.assertEqual(result["RecordSpec"], "RA")
        self.assertEqual(result["HassoTime"], "1540")
        self.assertEqual(result["HassoTimeBefore"], "1535")
        self.assertEqual(result["TorokuTosu"], "18")
        self.assertEqual(result["SyussoTosu"], "16")
        self.assertEqual(result["NyusenTosu"], "16")
        self.assertEqual(result["Syukaisu"], "2")
        self.assertEqual(result["RecordUpKubun"], "1")
        self.assertEqual(result["TenkoCD"], "1")

    def test_empty_values_convert_to_empty_string(self):
        """Test that empty/whitespace values convert to empty string.

        Note: RAParser strips whitespace and returns empty strings.
        Conversion to None is done by the importer/database layer.
        """
        # Create record with empty values
        sample_data = (
            b"RA1"
            + b"        "  # MakeDate (8) - empty
            + b"    "      # Year (4) - empty
            + b"    "      # MonthDay (4) - empty
            + b"  "        # JyoCD (2)
            + b"  "        # Kaiji (2) - empty
            + b"  "        # Nichiji (2)
            + b"  "        # RaceNum (2)
        )
        # Pad to 856 bytes
        sample_data += b" " * (856 - len(sample_data))

        result = self.parser.parse(sample_data)

        # Empty values should be empty strings (stripped whitespace)
        self.assertEqual(result["MakeDate"], "")
        self.assertEqual(result["Year"], "")
        self.assertEqual(result["MonthDay"], "")
        self.assertEqual(result["Kaiji"], "")


if __name__ == '__main__':
    unittest.main()
