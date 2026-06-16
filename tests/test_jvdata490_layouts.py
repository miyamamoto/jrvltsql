#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for layouts audited against JRA-VAN JV-Data490.xlsx.

The expected values below come from the official workbook's フォーマット sheet:
https://jra-van.jp/dlb/sdv/sdk/JV-Data490.xlsx
"""

from src.parser.av_parser import AVParser
from src.parser.h1_parser import H1Parser, _H1_ARRAYS
from src.parser.h6_parser import H6Parser
from src.parser.hc_parser import HCParser
from src.parser.hs_parser import HSParser
from src.parser.o1_parser import O1Parser
from src.parser.o2_parser import O2Parser
from src.parser.o3_parser import O3Parser
from src.parser.o4_parser import O4Parser
from src.parser.o5_parser import O5Parser
from src.parser.o6_parser import O6Parser


def test_official_record_lengths_from_jvdata490():
    assert H1Parser.RECORD_LENGTH == 28955
    assert H6Parser.RECORD_LENGTH == 102890
    assert O1Parser.RECORD_LENGTH == 962
    assert O2Parser.RECORD_LENGTH == 2042
    assert O3Parser.RECORD_LENGTH == 2654
    assert O4Parser.RECORD_LENGTH == 4031
    assert O5Parser.RECORD_LENGTH == 12293
    assert O6Parser.RECORD_LENGTH == 83285
    assert HCParser.RECORD_LENGTH == 60
    assert HSParser.RECORD_LENGTH == 200
    assert AVParser.RECORD_LENGTH == 78


def test_h1_array_offsets_match_jvdata490():
    # Workbook positions are 1-indexed; parser offsets are 0-indexed.
    expected = [
        ("Tansyo", 84 - 1, 28, 15, 2, 2),
        ("Fukusyo", 504 - 1, 28, 15, 2, 2),
        ("Wakuren", 924 - 1, 36, 15, 2, 2),
        ("Umaren", 1464 - 1, 153, 18, 4, 3),
        ("Wide", 4218 - 1, 153, 18, 4, 3),
        ("Umatan", 6972 - 1, 306, 18, 4, 3),
        ("Sanrenpuku", 12480 - 1, 816, 20, 6, 3),
    ]
    assert _H1_ARRAYS == expected


def test_h6_offsets_match_jvdata490():
    parser = H6Parser()
    assert parser.RECORD_LENGTH == 102890
    # 3連単票数 starts at workbook position 51.
    assert 50 + (4896 * 21) == 102866
    # Totals and CRLF positions are 0-indexed parser offsets.
    assert (102867 - 1, 102878 - 1, 102889 - 1) == (102866, 102877, 102888)


def test_hc_field_offsets_match_jvdata490():
    fields = {field.name: (field.start, field.length) for field in HCParser()._fields}
    assert fields["RecordSpec"] == (0, 2)
    assert fields["TresenKubun"] == (11, 1)
    assert fields["ChokyoDate"] == (12, 8)
    assert fields["ChokyoTime"] == (20, 4)
    assert fields["KettoNum"] == (24, 10)
    assert fields["HaronTime4"] == (34, 4)
    assert fields["LapTime1"] == (55, 3)
    assert fields["RecordDelimiter"] == (58, 2)


def test_av_field_offsets_match_jvdata490():
    fields = {field.name: (field.start, field.length) for field in AVParser()._fields}
    assert fields["RecordSpec"] == (0, 2)
    assert fields["MakeDate"] == (3, 8)
    assert fields["Year"] == (11, 4)
    assert fields["RaceNum"] == (25, 2)
    assert fields["HappyoTime"] == (27, 8)
    assert fields["Umaban"] == (35, 2)
    assert fields["Bamei"] == (37, 36)
    assert fields["JiyuKubun"] == (73, 3)
    assert fields["RecordDelimiter"] == (76, 2)
