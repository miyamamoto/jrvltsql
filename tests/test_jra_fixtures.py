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
    "H1": (H1Parser, 317),   # Fixture files use flat format (317 bytes)
    "H6": (H6Parser, 78),    # Fixture files use flat format (78 bytes)
    "HC": (HCParser, 60),
    "HN": (HNParser, 251),
    "HS": (HSParser, 200),
    "HY": (HYParser, 123),
    "JG": (JGParser, 80),
    "KS": (KSParser, 772),
    "O1": (O1Parser, 107),    # Fixture files use legacy compact format (107 bytes)
    "O2": (O2Parser, 66),     # Fixture files use legacy compact format (66 bytes)
    "O3": (O3Parser, 70),     # Fixture files use legacy compact format (70 bytes)
    "O4": (O4Parser, 66),     # Fixture files use legacy compact format (66 bytes)
    "O5": (O5Parser, 68),     # Fixture files use legacy compact format (68 bytes)
    "O6": (O6Parser, 70),     # Fixture files use legacy compact format (70 bytes)
    "RA": (RAParser, 856),
    "RC": (RCParser, 241),
    "SE": (SEParser, 463),
    "SK": (SKParser, 78),
    "TK": (TKParser, 727),
    "TM": (TMParser, 39),
    "UM": (UMParser, 1110),
    "WF": (WFParser, 169),  # Historical fixture uses the obsolete compact layout.
    "YS": (YSParser, 146),
}
EXPANDED_RECORD_TYPES = {"O1", "O2", "O3", "O4", "O5", "O6"}


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
            # The historical SE fixture was reconstructed with the obsolete
            # 463-byte parser and has no official tail. Preserve its core-field
            # checks while the tail is covered by a dedicated 555-byte test.
            if record_type == "SE" and len(chunk) == 463:
                chunk = chunk.ljust(SEParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "WF" and len(chunk) == 169:
                chunk = chunk[:11].ljust(WFParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            records.append(chunk)
    return records


@pytest.mark.parametrize("record_type", list(PARSER_MAP.keys()))
class TestJRAFixtures:
    """実データフィクスチャを使ったJRAパーサーテスト"""

    def test_parse_returns_expected_shape(self, record_type):
        """parse()が期待する戻り値形状を返すことを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)
        assert len(records) > 0, f"No records loaded for {record_type}"

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            if record_type in EXPANDED_RECORD_TYPES:
                assert isinstance(result, list), (
                    f"{record_type} record {i}: parse() returned {type(result)}"
                )
                assert result, f"{record_type} record {i}: parse() returned an empty list"
            else:
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
            row = result[0] if isinstance(result, list) else result
            assert row["RecordSpec"] == record_type, (
                f"{record_type} record {i}: RecordSpec={row['RecordSpec']}"
            )

    def test_fields_not_all_empty(self, record_type):
        """少なくとも一部のフィールドに値が入っていることを確認"""
        parser_cls, record_length = PARSER_MAP[record_type]
        parser = parser_cls()
        records = load_fixture_records(record_type, record_length)

        for i, rec in enumerate(records):
            result = parser.parse(rec)
            row = result[0] if isinstance(result, list) else result
            non_empty = [k for k, v in row.items() if v and str(v).strip()]
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


class TestHCParserRealData:
    """HCパーサーの坂路調教レイアウト詳細テスト"""

    def setup_method(self):
        self.parser = HCParser()
        self.records = load_fixture_records("HC", 60)

    def test_uses_hanro_fields_not_trainer_stats(self):
        result = self.parser.parse(self.records[-1])

        assert "TresenKubun" in result
        assert "ChokyoDate" in result
        assert "ChokyoTime" in result
        assert "KettoNum" in result
        assert "HaronTime4" in result
        assert "LapTime1" in result
        assert "ChokyosiCode" not in result
        assert "HonSyokinHeichi" not in result

    def test_parses_official_hanro_positions(self):
        result = self.parser.parse(self.records[-1])

        assert result["RecordSpec"] == "HC"
        assert result["DataKubun"] == "1"
        assert result["MakeDate"] == "20240104"
        assert result["TresenKubun"] == "0"
        assert result["ChokyoDate"] == "20231201"
        assert result["ChokyoTime"] == "0759"
        assert result["KettoNum"] == "2021105492"
        assert result["HaronTime4"] == "0695"
        assert result["LapTime4"] == "177"
        assert result["HaronTime3"] == "0518"
        assert result["LapTime3"] == "187"
        assert result["HaronTime2"] == "0331"
        assert result["LapTime2"] == "167"
        assert result["LapTime1"] == "164"

    def test_nl_hc_schema_matches_hanro_fields(self):
        from src.database.schema import SCHEMAS

        schema = SCHEMAS["NL_HC"]
        assert "TresenKubun TEXT" in schema
        assert "HaronTime4 REAL" in schema
        assert "LapTime1 REAL" in schema
        assert "PRIMARY KEY (TresenKubun, ChokyoDate, ChokyoTime, KettoNum)" in schema
        assert "ChokyosiCode" not in schema
        assert "HonSyokinHeichi" not in schema

    def test_hanro_times_are_converted_for_nl_hc_insert(self):
        from src.importer.importer import convert_record_types

        parsed = self.parser.parse(self.records[-1])
        converted = convert_record_types(parsed, "NL_HC")

        assert converted["HaronTime4"] == 69.5
        assert converted["LapTime4"] == 17.7
        assert converted["HaronTime3"] == 51.8
        assert converted["LapTime3"] == 18.7
        assert converted["HaronTime2"] == 33.1
        assert converted["LapTime2"] == 16.7
        assert converted["LapTime1"] == 16.4


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


def test_se_storage_schemas_keep_all_three_opponent_slots():
    from src.database.schema import SCHEMAS

    for table_name in ("NL_SE", "RT_SE"):
        schema = SCHEMAS[table_name]
        for column in (
            "KettoNum1",
            "Bamei1",
            "KettoNum2",
            "Bamei2",
            "KettoNum3",
            "Bamei3",
        ):
            assert f"{column} TEXT" in schema
        assert "Reserved_462" not in schema
