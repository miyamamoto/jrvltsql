#!/usr/bin/env python
"""Tests for the current official JRA-VAN RA representation."""

import unittest

from src.parser.ra_parser import RAParser
from tests.fixtures.record_factory import make_ra_record


class TestRAParserJRAVAN(unittest.TestCase):
    """Exercise current-only RA parsing and backward-compatible aliases."""

    def setUp(self):
        self.parser = RAParser()

    def test_parser_initialization(self):
        self.assertEqual(self.parser.RECORD_TYPE, "RA")
        self.assertEqual(self.parser.RECORD_LENGTH, 1272)

    def test_field_names_include_complete_official_arrays(self):
        result = self.parser.parse(make_ra_record())

        self.assertIsNotNone(result)
        for field_name in (
            "Honsyokin7",
            "HonsyokinBefore5",
            "Fukasyokin5",
            "FukasyokinBefore3",
            "LapTime25",
            "Corner1",
            "Jyuni4",
            "RecordUpKubun",
            "Crlf",
        ):
            self.assertIn(field_name, result)

    def test_parse_sample_record(self):
        result = self.parser.parse(
            make_ra_record(
                make_date="20231115",
                year="2023",
                month_day="1115",
                jyo_cd="06",
                kaiji="03",
                nichiji="08",
                race_num="11",
                hasso_time="1540",
            )
        )

        self.assertEqual(result["RecordSpec"], "RA")
        self.assertEqual(result["DataKubun"], "1")
        self.assertEqual(result["MakeDate"], "20231115")
        self.assertEqual(result["Year"], "2023")
        self.assertEqual(result["MonthDay"], "1115")
        self.assertEqual(result["JyoCD"], "06")
        self.assertEqual(result["Kaiji"], "03")
        self.assertEqual(result["Nichiji"], "08")
        self.assertEqual(result["RaceNum"], "11")
        self.assertEqual(result["HassoTime"], "1540")

    def test_weather_lap_haron_and_corners_use_current_offsets(self):
        data = bytearray(make_ra_record())
        data[890:893] = b"122"
        data[965:969] = b"1572"
        data[969:972] = b"341"
        data[972:975] = b"455"
        data[975:978] = b"363"
        data[978:981] = b"476"
        for index, values in enumerate(((b"1", b"1", b"02,04,06"), (b"4", b"2", b"01,02,03"))):
            base = 981 + index * 216
            corner, lap, order = values
            data[base : base + 1] = corner
            data[base + 1 : base + 2] = lap
            data[base + 2 : base + 2 + len(order)] = order

        result = self.parser.parse(bytes(data))

        self.assertEqual(result["TenkoCD"], "1")
        self.assertEqual(result["SibaBabaCD"], "1")
        self.assertEqual(result["DirtBabaCD"], "0")
        self.assertEqual(result["LapTime1"], "122")
        self.assertEqual(result["LapTime"], "122")
        self.assertEqual(result["SyogaiMileTime"], "1572")
        self.assertEqual(result["HaronTimeS3"], "341")
        self.assertEqual(result["Haron3F"], "341")
        self.assertEqual(result["HaronTimeL4"], "476")
        self.assertEqual(result["Haron4L"], "476")
        self.assertEqual(result["Corner1"], "1")
        self.assertEqual(result["Corner"], "1")
        self.assertEqual(result["Jyuni1"], "02,04,06")
        self.assertEqual(result["TsukaJyuni"], "02,04,06")
        self.assertEqual(result["Corner4"], "4")
        self.assertEqual(result["Jyuni4"], "01,02,03")
        self.assertEqual(result["TsukaJyuni4"], "01,02,03")

    def test_cancelled_and_international_records_use_the_same_layout(self):
        for data_kubun, post_time in (("9", "0000"), ("A", ""), ("B", "")):
            with self.subTest(data_kubun=data_kubun):
                result = self.parser.parse(
                    make_ra_record(data_kubun=data_kubun, hasso_time=post_time)
                )
                self.assertIsNotNone(result)
                self.assertEqual(result["DataKubun"], data_kubun)
                self.assertEqual(result["HassoTime"], post_time)

    def test_empty_values_are_empty_strings(self):
        result = self.parser.parse(
            make_ra_record(
                make_date="",
                year="",
                month_day="",
                jyo_cd="",
                kaiji="",
                nichiji="",
                race_num="",
            )
        )

        self.assertEqual(result["MakeDate"], "")
        self.assertEqual(result["Year"], "")
        self.assertEqual(result["MonthDay"], "")
        self.assertEqual(result["Kaiji"], "")

    def test_non_official_shape_and_delimiter_are_rejected(self):
        record = make_ra_record()
        self.assertIsNone(self.parser.parse(record[:856]))
        self.assertIsNone(self.parser.parse(record[:-1]))
        self.assertIsNone(self.parser.parse(record[:1270] + b"YZ"))


if __name__ == "__main__":
    unittest.main()
