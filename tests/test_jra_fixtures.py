#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JRAパーサーの実データフィクスチャテスト

tests/fixtures/jra/ にある実データ（keiba.dbから再構成）を使って
各パーサーの parse() が正しくフィールドを抽出できることを検証する。

フィクスチャは scripts/extract_fixtures_from_db.py で生成。
データソース: JV-Link経由で取得したJRA実データ (keiba.db)
"""

import os
import pytest

# Parser imports
from src.parser.bn_parser import BNParser
from src.parser.br_parser import BRParser
from src.parser.ch_parser import CHParser
from src.parser.dm_parser import DMParser
from src.parser.h1_parser import H1Parser
from src.parser.h6_parser import H6Parser
from src.parser.hc_parser import HCParser
from src.parser.hn_parser import HNParser
from src.parser.hs_parser import HSParser
from src.parser.hy_parser import HYParser
from src.parser.jg_parser import JGParser
from src.parser.ks_parser import KSParser
from src.parser.o1_parser import O1Parser
from src.parser.o2_parser import O2Parser
from src.parser.o3_parser import O3Parser
from src.parser.o4_parser import O4Parser
from src.parser.o5_parser import O5Parser
from src.parser.o6_parser import O6Parser
from src.parser.ra_parser import RAParser
from src.parser.rc_parser import RCParser
from src.parser.se_parser import SEParser
from src.parser.sk_parser import SKParser
from src.parser.tk_parser import TKParser
from src.parser.tm_parser import TMParser
from src.parser.um_parser import UMParser
from src.parser.wf_parser import WFParser
from src.parser.ys_parser import YSParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "jra")

# Record type -> (ParserClass, record_length)
PARSER_MAP = {
    "BN": (BNParser, 387),
    "BR": (BRParser, 455),
    "CH": (CHParser, 592),
    "DM": (DMParser, 48),
    "H1": (H1Parser, 317),
    "H6": (H6Parser, 78),
    "HC": (HCParser, 60),
    "HN": (HNParser, 251),
    "HS": (HSParser, 200),
    "HY": (HYParser, 123),
    "JG": (JGParser, 80),
    "KS": (KSParser, 772),
    "O1": (O1Parser, 107),
    "O2": (O2Parser, 66),
    "O3": (O3Parser, 70),
    "O4": (O4Parser, 66),
    "O5": (O5Parser, 68),
    "O6": (O6Parser, 70),
    "RA": (RAParser, 856),
    "RC": (RCParser, 241),
    "SE": (SEParser, 463),
    "SK": (SKParser, 78),
    "TK": (TKParser, 727),
    "TM": (TMParser, 39),
    "UM": (UMParser, 1110),
    "WF": (WFParser, 169),
    "YS": (YSParser, 146),
}


def load_fixture_records(record_type, record_length):
    """Load fixture binary file and split into individual records."""
    filepath = os.path.join(FIXTURES_DIR, f"{record_type.lower()}_records.bin")
    if not os.path.exists(filepath):
        pytest.skip(f"Fixture file not found: {filepath}")
    with open(filepath, "rb") as f:
        data = f.read()
    records = []
    for i in range(0, len(data), record_length):
        chunk = data[i : i + record_length]
        if len(chunk) == record_length:
            records.append(chunk)
    return records


@pytest.mark.parametrize("record_type", list(PARSER_MAP.keys()))
class TestJRAFixtures:
    """実データフィクスチャを使ったJRAパーサーテスト"""

    def test_parse_returns_dict(self, record_type):
        """parse()が辞書を返すことを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)
        assert len(records) > 0, f"No records loaded for {record_type}"

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            assert isinstance(result, dict), (
                f"{record_type} record {i}: parse() returned {type(result)}"
            )

    def test_record_spec_matches(self, record_type):
        """RecordSpecフィールドがレコードタイプと一致することを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            assert result["RecordSpec"] == record_type, (
                f"{record_type} record {i}: RecordSpec={result['RecordSpec']}"
            )

    def test_fields_not_all_empty(self, record_type):
        """少なくとも一部のフィールドに値が入っていることを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            non_empty = [k for k, v in result.items() if v and str(v).strip()]
            assert len(non_empty) >= 3, (
                f"{record_type} record {i}: only {len(non_empty)} non-empty fields"
            )

    def test_all_records_parseable(self, record_type):
        """全レコードがエラーなくパースできることを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            assert result is not None, f"{record_type} record {i}: parse returned None"


class TestRAParserRealData:
    """RAパーサーの実データ詳細テスト"""

    def setup_method(self):
        self.parser = RAParser()
        self.records = load_fixture_records("RA", 856)

    def test_year_is_valid(self):
        for rec in self.records:
            result = self.parser.parse(rec)
            year = result["Year"]
            assert year.isdigit(), f"Year is not numeric: {year}"
            assert 1986 <= int(year) <= 2030, f"Year out of range: {year}"

    def test_jyo_code_is_valid(self):
        for rec in self.records:
            result = self.parser.parse(rec)
            jyo = result["JyoCD"]
            assert len(jyo) <= 2, f"JyoCD too long: {jyo}"

    def test_race_num_is_valid(self):
        for rec in self.records:
            result = self.parser.parse(rec)
            rnum = result["RaceNum"]
            if rnum.strip():
                assert rnum.isdigit(), f"RaceNum not numeric: {rnum}"
                assert 1 <= int(rnum) <= 12, f"RaceNum out of range: {rnum}"

    def test_kyori_is_numeric(self):
        for rec in self.records:
            result = self.parser.parse(rec)
            kyori = result["Kyori"]
            if kyori.strip():
                assert kyori.isdigit(), f"Kyori not numeric: {kyori}"


class TestSEParserRealData:
    """SEパーサーの実データ詳細テスト"""

    def setup_method(self):
        self.parser = SEParser()
        self.records = load_fixture_records("SE", 463)

    def test_bamei_is_not_empty(self):
        """馬名が空でないことを確認"""
        for rec in self.records:
            result = self.parser.parse(rec)
            bamei = result.get("Bamei", "")
            assert bamei.strip(), "Bamei is empty"

    def test_ketto_num_format(self):
        """血統登録番号のフォーマット確認"""
        for rec in self.records:
            result = self.parser.parse(rec)
            ketto = result.get("KettoNum", "")
            if ketto.strip():
                assert ketto.isdigit(), f"KettoNum not numeric: {ketto}"
                assert len(ketto) == 10, f"KettoNum wrong length: {len(ketto)}"
