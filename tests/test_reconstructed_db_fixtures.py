#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser value regressions reconstructed from stored database rows.

The binary files under ``tests/fixtures/reconstructed_db`` were generated from
already-parsed SQLite rows by ``scripts/reconstruct_fixtures_from_db.py``.
They preserve selected stored values for regression testing, but they are not
byte-preserved provider records and cannot establish physical offsets, lengths,
initial values, availability, or historical-layout compatibility.
"""

import os
import pytest

# Parser imports
from src.parser.bn_parser import BNParser
from src.parser.br_parser import BRParser
from src.parser.ch_parser import CHParser
from src.parser.dm_parser import DMParser
from src.parser.hc_parser import HCParser
from src.parser.hn_parser import HNParser
from src.parser.hs_parser import HSParser
from src.parser.hy_parser import HYParser
from src.parser.jg_parser import JGParser
from src.parser.ks_parser import KSParser
from src.parser.ra_parser import RAParser
from src.parser.rc_parser import RCParser
from src.parser.se_parser import SEParser
from src.parser.sk_parser import SKParser
from src.parser.tk_parser import TKParser
from src.parser.tm_parser import TMParser
from src.parser.ys_parser import YSParser

FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), "fixtures", "reconstructed_db"
)

# Record type -> (ParserClass, record_length)
PARSER_MAP = {
    "BN": (BNParser, BNParser.RECORD_LENGTH),
    "BR": (BRParser, BRParser.RECORD_LENGTH),
    "CH": (CHParser, CHParser.RECORD_LENGTH),
    "DM": (DMParser, DMParser.RECORD_LENGTH),
    "HN": (HNParser, 251),
    "HS": (HSParser, 200),
    "HY": (HYParser, 123),
    "JG": (JGParser, 80),
    "KS": (KSParser, KSParser.RECORD_LENGTH),
    "RA": (RAParser, RAParser.RECORD_LENGTH),
    "RC": (RCParser, RCParser.RECORD_LENGTH),
    "SE": (SEParser, 463),
    "SK": (SKParser, SKParser.RECORD_LENGTH),
    "TK": (TKParser, TKParser.RECORD_LENGTH),
    "TM": (TMParser, TMParser.RECORD_LENGTH),
    "YS": (YSParser, YSParser.RECORD_LENGTH),
}
# HC records are also excluded from the generic all-row positive matrix. Two
# reconstructed rows contain space-filled fixed numeric spans that are not
# valid current provider HC. The dedicated class below retains the one complete
# value reconstruction, while the official HC contract is authoritative.
# The old O1-O6 fixture files were reconstructed from already-expanded SQL
# rows, not preserved provider records. They cannot prove a physical parser
# contract; complete current layouts are covered in test_time_series.py.
# The 169-byte wf_records.bin is a repository-only compaction of the official
# 7,215-byte record with no historical-format provenance; it is not a positive
# WF fixture, and test_wf_official_contract.py proves it is rejected.
EXPANDED_RECORD_TYPES = {"DM", "TM"}
LEGACY_RECONSTRUCTED_LENGTHS = {
    "BN": 387,
    "BR": 455,
    "CH": 592,
    "DM": 48,
    "KS": 772,
    "RA": 856,
    "RC": 241,
    "SK": 78,
    "TK": 727,
    "TM": 39,
    "YS": 146,
}


def _has_complete_fixture_records(data, record_type, record_length):
    if not data or len(data) % record_length:
        return False
    marker = record_type.encode("ascii")
    return all(data[offset : offset + 2] == marker for offset in range(0, len(data), record_length))


def load_fixture_records(record_type, record_length):
    """Load fixture binary file and split into individual records."""
    filepath = os.path.join(FIXTURES_DIR, f"{record_type.lower()}_records.bin")
    if not os.path.exists(filepath):
        raise AssertionError(f"Required reconstructed fixture is missing: {filepath}")
    with open(filepath, "rb") as f:
        data = f.read()
    source_record_length = record_length
    legacy_length = LEGACY_RECONSTRUCTED_LENGTHS.get(record_type)
    if (
        legacy_length
        and not _has_complete_fixture_records(data, record_type, record_length)
        and _has_complete_fixture_records(data, record_type, legacy_length)
    ):
        source_record_length = legacy_length
    records = []
    for i in range(0, len(data), source_record_length):
        chunk = data[i : i + source_record_length]
        if len(chunk) == source_record_length:
            # The historical SE fixture was reconstructed with the obsolete
            # 463-byte parser and has no official tail. Preserve its core-field
            # checks while the tail is covered by a dedicated 555-byte test.
            if record_type == "SE" and len(chunk) == 463:
                chunk = chunk.ljust(SEParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "BN" and len(chunk) == 387:
                # This fixture was reconstructed through the former 387-byte
                # parser. Only its first 355 core bytes are position-compatible;
                # the full result arrays are covered by the official contract.
                chunk = chunk[:355].ljust(BNParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "BR" and len(chunk) == 455:
                # This fixture was reconstructed through the former 455-byte
                # parser. Only its first 423 core bytes are position-compatible;
                # the full result arrays are covered by the official contract.
                chunk = chunk[:423].ljust(BRParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "CH" and len(chunk) == 592:
                # This fixture was reconstructed through the obsolete parser,
                # whose result bytes start where current recent-win block 2
                # begins. Preserve only the position-compatible 378-byte prefix.
                chunk = chunk[:378].ljust(CHParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "DM" and len(chunk) == 48:
                # The historical fixture contains the correct header and first
                # 15-byte horse block, but was reconstructed to the obsolete
                # 48-byte parser length. Fill the remaining 17 official slots
                # with their documented space initial value.
                chunk = chunk[:46].ljust(DMParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "KS" and len(chunk) == 772:
                # The historical fixture used the repository's non-official
                # 772-byte reconstruction. Bytes 1-331 cover the compatible
                # header and first flat-ride block; synthesize documented
                # initial values for every remaining numeric field.
                current = bytearray(b" " * KSParser.RECORD_LENGTH)
                current[:331] = chunk[:331]
                for start, size in (
                    (331, 16), (347, 2), (349, 10), (395, 2), (397, 1),
                    (398, 16), (414, 2), (416, 10),
                    (462, 16), (478, 2), (480, 10),
                    (526, 16), (641, 2), (643, 10),
                    (689, 16), (804, 2), (806, 10),
                    (852, 16), (967, 2), (969, 10),
                ):
                    current[start : start + size] = b"0" * size
                current[1015:4171] = b"0" * 3156
                current[4171:4173] = b"\r\n"
                chunk = bytes(current)
            if record_type == "SK" and len(chunk) == 78:
                # This fixture was reconstructed from stored columns through
                # the obsolete one-pedigree parser. Preserve its core values
                # (header, key, body, and the first pedigree number) as a
                # synthetic current-shape record and fill the 13 remaining
                # ten-digit pedigree slots with their documented initial value
                # 0; the exact 208-byte contract is covered by
                # test_sk_parser_layout.py and test_sk_official_contract.py.
                chunk = chunk[:76] + b"0" * 130 + b"\r\n"
            if record_type == "TK" and len(chunk) == 727:
                # The historical fixture was reconstructed through the former
                # one-entry parser. Preserve the position-compatible header and
                # first 70-byte registered horse in a synthetic current record.
                current = bytearray(b" " * TKParser.RECORD_LENGTH)
                current[:725] = chunk[:725]
                current[652:655] = b"001"
                current[-2:] = b"\r\n"
                chunk = bytes(current)
            if record_type == "RA" and len(chunk) == 856:
                # This fixture was reconstructed with the repository's former
                # non-official 856-byte parser. Only its pre-array 713-byte
                # prefix is position-compatible. Keep those core-value checks
                # in a synthetic current record; the full arrays are covered
                # by test_ra_official_contract.py.
                chunk = chunk[:713].ljust(RAParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "RC" and len(chunk) == 241:
                # The historical fixture was reconstructed through the former
                # non-official 241-byte parser. Only bytes 1-93 precede its
                # shifted course fields; retain that compatible prefix and use
                # documented numeric initial values for bytes 94-109.
                current = bytearray(b" " * RCParser.RECORD_LENGTH)
                current[:93] = chunk[:93]
                current[93:109] = b"00" + b"0000" + b"00" + b"0" + b"0000" + b"000"
                current[-2:] = b"\r\n"
                chunk = bytes(current)
            if record_type == "TM" and len(chunk) == 39:
                # The historical fixture contains a correct header and first
                # six-byte horse block reconstructed through the obsolete
                # one-entry parser. Fill the other official slots with spaces.
                chunk = chunk[:37].ljust(TMParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            if record_type == "YS" and len(chunk) == 146:
                # The historical fixture contains the header and first complete
                # guidance block. Preserve that compatible prefix in a synthetic
                # current row; exact three-block coverage has its own contract.
                chunk = chunk[:144].ljust(YSParser.RECORD_LENGTH - 2, b" ") + b"\r\n"
            records.append(chunk)
    return records


def test_ch_legacy_fixture_preserves_only_the_position_compatible_prefix():
    record = load_fixture_records("CH", CHParser.RECORD_LENGTH)[0]
    parsed = CHParser().parse(record)

    assert parsed is not None
    assert parsed["SaikinJyusyo1_id"]
    assert parsed["SaikinJyusyo2_id"] == ""
    assert parsed["SaikinJyusyo3_Bamei"] == ""
    for row in parsed["_ch_seiseki_rows"]:
        payload = {
            key: value
            for key, value in row.items()
            if key not in {"MakeDate", "ChokyosiCode", "Num"}
        }
        assert set(payload.values()) == {""}


@pytest.mark.parametrize("record_type", list(PARSER_MAP.keys()))
class TestReconstructedDBFixtures:
    """Value regressions backed by reconstructed database-row fixtures."""

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


class TestHCParserReconstructedValues:
    """HC parser checks for values retained by the reconstruction."""

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

    def test_rejects_reconstructed_rows_with_blank_fixed_numeric_times(self):
        assert self.parser.parse(self.records[0]) is None
        assert self.parser.parse(self.records[1]) is None

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


class TestRAParserReconstructedValues:
    """RA parser plausibility checks for reconstructed stored values."""

    def setup_method(self):
        self.parser = RAParser()
        self.records = load_fixture_records("RA", RAParser.RECORD_LENGTH)

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


class TestSEParserReconstructedValues:
    """SE parser plausibility checks for reconstructed stored values."""

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


def test_sk_current_fixture_file_is_split_at_the_current_record_length(tmp_path, monkeypatch):
    record = b"SK" + b" " * (SKParser.RECORD_LENGTH - 4) + b"\r\n"
    (tmp_path / "sk_records.bin").write_bytes(record * 2)
    monkeypatch.setattr(
        "tests.test_reconstructed_db_fixtures.FIXTURES_DIR", str(tmp_path)
    )

    records = load_fixture_records("SK", PARSER_MAP["SK"][1])

    assert PARSER_MAP["SK"][1] == SKParser.RECORD_LENGTH
    assert records == [record, record]
