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
        # JV-Data 4.9.0.1 拡張レイアウト(1-indexed): 天候888/芝馬場889/ダート馬場890。
        sample_data[887:888] = b"2"
        sample_data[888:889] = b"1"
        sample_data[889:890] = b"3"

        result = self.parser.parse(bytes(sample_data))

        self.assertEqual(result["RecordSpec"], "RA")
        self.assertEqual(result["HassoTime"], "1540")
        self.assertEqual(result["HassoTimeBefore"], "1535")
        self.assertEqual(result["TorokuTosu"], "18")
        self.assertEqual(result["SyussoTosu"], "16")
        self.assertEqual(result["NyusenTosu"], "16")
        self.assertEqual(result["TenkoCD"], "2")
        self.assertEqual(result["SibaBabaCD"], "1")
        self.assertEqual(result["DirtBabaCD"], "3")
        # 周回数(Syukaisu)は<コーナー通過順位>節のフィールドで、コーナー不在なら空。
        self.assertEqual(result["Syukaisu"], "")

    def test_extended_layout_reads_weather_baba_and_haron(self):
        """拡張レイアウトで 天候/芝ダート馬場/ラップ/前後ハロン を仕様位置から読む。

        JV-Data 4.9.0.1 (1-indexed): 天候=888 芝馬場=889 ダート馬場=890
        ラップ=891 障害マイル=966 前3=970 前4=973 後3=976 後4=979。
        従来は入線頭数の直後で +2 ずれ、ダート馬場を TenkoCD として読み、
        芝/ダート馬場とラップ/ハロンは 856byte 互換位置の賞金断片に化けていた。
        """
        data = bytearray(b" " * 1272)
        data[0:2] = b"RA"
        data[2:3] = b"7"
        data[3:11] = b"20260508"
        data[11:15] = b"2026"
        data[15:19] = b"0508"
        data[19:21] = b"05"
        data[21:23] = b"02"
        data[23:25] = b"03"
        data[25:27] = b"12"
        data[873:877] = b"1540"  # 発走時刻 -> 拡張レイアウト判定
        data[887:888] = b"1"     # 天候=晴
        data[888:889] = b"2"     # 芝馬場=稍重
        data[889:890] = b"0"     # ダート馬場=なし(芝レース)
        data[890:893] = b"122"   # ラップ先頭ハロン
        data[965:969] = b"0000"  # 障害マイルタイム
        data[969:972] = b"341"   # 前3ハロン
        data[972:975] = b"455"   # 前4ハロン
        data[975:978] = b"363"   # 後3ハロン
        data[978:981] = b"476"   # 後4ハロン
        data[1269:1270] = b"1"   # レコード更新区分

        result = self.parser.parse(bytes(data))

        self.assertEqual(result["TenkoCD"], "1")
        self.assertEqual(result["SibaBabaCD"], "2")
        self.assertEqual(result["DirtBabaCD"], "0")
        self.assertEqual(result["LapTime"], "122")
        self.assertEqual(result["SyogaiMileTime"], "0000")
        self.assertEqual(result["Haron3F"], "341")
        self.assertEqual(result["Haron4F"], "455")
        self.assertEqual(result["Haron3L"], "363")
        self.assertEqual(result["Haron4L"], "476")
        self.assertEqual(result["RecordUpKubun"], "1")

    @staticmethod
    def _build_extended_record(corner_sets=(), legacy_corner_bytes=None):
        """Build a full-layout (1272 byte) RA record for corner tests.

        Args:
            corner_sets: Iterable of (corner, syukaisu, jyuni) byte tuples
                         written to the JV-Data full-layout positions (981+).
            legacy_corner_bytes: Optional bytes written at the 856-byte
                         compat corner position (781-853) to simulate the
                         prize-array digits that occupy it in full layout.
        """
        data = bytearray(b" " * 1272)
        data[0:2] = b"RA"
        data[2:3] = b"1"
        data[3:11] = b"20260607"
        data[11:15] = b"2026"
        data[15:19] = b"0607"
        data[19:21] = b"05"
        data[21:23] = b"03"
        data[23:25] = b"01"
        data[25:27] = b"11"
        # Extended-layout post time triggers the full-layout branch.
        data[873:877] = b"1545"
        if legacy_corner_bytes:
            data[781:781 + len(legacy_corner_bytes)] = legacy_corner_bytes
        for idx, (corner, syukaisu, jyuni) in enumerate(corner_sets):
            base = 981 + idx * 72
            data[base:base + 1] = corner
            data[base + 1:base + 2] = syukaisu
            data[base + 2:base + 2 + len(jyuni)] = jyuni
        return bytes(data)

    def test_legacy_record_keeps_single_corner_set_and_blank_expansion(self):
        """856-byte compat records expose one corner set; sets 2-4 stay empty."""
        sample_data = bytearray(b" " * 856)
        sample_data[0:2] = b"RA"
        sample_data[2:3] = b"1"
        sample_data[781:782] = b"4"
        sample_data[782:783] = b"1"
        sample_data[783:791] = b"03,05,07"

        result = self.parser.parse(bytes(sample_data))

        self.assertEqual(result["Corner"], "4")
        self.assertEqual(result["Syukaisu"], "1")
        self.assertEqual(result["TsukaJyuni"], "03,05,07")
        for idx in (2, 3, 4):
            self.assertEqual(result[f"Corner{idx}"], "")
            self.assertEqual(result[f"Syukaisu{idx}"], "")
            self.assertEqual(result[f"TsukaJyuni{idx}"], "")

    def test_extended_layout_expands_four_corner_sets(self):
        """Full-layout records expand all four corner sets by position."""
        sample_data = self._build_extended_record(
            corner_sets=[
                (b"1", b"1", b"02,04,06"),
                (b"2", b"1", b"04,02,06"),
                (b"3", b"1", b"06,02,04"),
                (b"4", b"2", b"01,02,03"),
            ],
        )

        result = self.parser.parse(sample_data)

        # First set keeps the backward-compatible column names.
        self.assertEqual(result["Corner"], "1")
        self.assertEqual(result["Syukaisu"], "1")
        self.assertEqual(result["TsukaJyuni"], "02,04,06")
        self.assertEqual(result["Corner2"], "2")
        self.assertEqual(result["Syukaisu2"], "1")
        self.assertEqual(result["TsukaJyuni2"], "04,02,06")
        self.assertEqual(result["Corner3"], "3")
        self.assertEqual(result["Syukaisu3"], "1")
        self.assertEqual(result["TsukaJyuni3"], "06,02,04")
        self.assertEqual(result["Corner4"], "4")
        self.assertEqual(result["Syukaisu4"], "2")
        self.assertEqual(result["TsukaJyuni4"], "01,02,03")

    def test_extended_layout_blank_corners_clear_legacy_garbage(self):
        """Blank full-layout corners must not leak compat-position digits."""
        sample_data = bytearray(
            self._build_extended_record(
                corner_sets=[],
                # In full layout 781-853 holds prize-array digits, which the
                # compat read would misinterpret as corner data.
                legacy_corner_bytes=b"0001234500067890",
            )
        )
        result = self.parser.parse(bytes(sample_data))

        self.assertEqual(result["Corner"], "")
        self.assertEqual(result["TsukaJyuni"], "")
        # 周回数(Syukaisu)は<コーナー通過順位>節のフィールド。空コーナーでは空。
        self.assertEqual(result["Syukaisu"], "")
        for idx in (2, 3, 4):
            self.assertEqual(result[f"Corner{idx}"], "")
            self.assertEqual(result[f"Syukaisu{idx}"], "")
            self.assertEqual(result[f"TsukaJyuni{idx}"], "")

    def test_extended_layout_short_record_does_not_leak_legacy_corner(self):
        """拡張レイアウトだがコーナー節に届かない短いレコードでも、856byte互換
        位置(781-853)の賞金配列断片が Corner/TsukaJyuni に漏れないこと。

        HassoTime(873) が有効なので拡張判定は真になるが、レコード長が
        コーナー1セット目(981+72=1053)未満のため展開ループは即 break する。
        """
        # 拡張判定は成立、しかしコーナー節(1053)には届かない長さ。
        sample_data = bytearray(b" " * 1000)
        sample_data[0:2] = b"RA"
        sample_data[2:3] = b"1"
        sample_data[3:11] = b"20260607"
        sample_data[873:877] = b"1545"  # 発走時刻 -> 拡張レイアウト判定
        # 856byte互換位置には賞金配列断片が入る。
        sample_data[781:797] = b"0001234500067890"

        result = self.parser.parse(bytes(sample_data))

        self.assertEqual(result["Corner"], "")
        self.assertEqual(result["TsukaJyuni"], "")
        self.assertEqual(result["Syukaisu"], "")

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
