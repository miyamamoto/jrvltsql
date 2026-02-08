#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser compatibility tests for JRA and NAR data.

Tests that parsers correctly handle:
1. JRA standard records (proper field extraction)
2. NAR records (same format, different jyo_cd range)
3. Full-struct vs flat records (H1/H6 28955-byte structs vs 317-byte per-combination)
4. Edge cases (short records, empty fields, Japanese text)

Key finding: NV-Link returns full JV-Data structs (e.g., H1 = 28,955 bytes
with arrays for all bet type combinations), but our parsers expect
per-combination flat records (H1 = 317 bytes). This mismatch is documented
and tested here.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser.factory import ParserFactory, ALL_RECORD_TYPES
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fixtures.record_factory import (
    make_ra_record,
    make_se_record,
    make_h1_record_full,
    make_h1_record_flat,
    make_hr_record,
    make_wf_record,
    make_bn_record,
    make_ra_record_nar,
    make_h1_record_nar_full,
    make_record_header,
)


@pytest.fixture
def factory():
    return ParserFactory()


class TestRAParser:
    """RA (レース詳細) parser tests."""

    def test_parse_jra_ra_record(self, factory):
        """JRA RA record parses correctly."""
        data = make_ra_record(
            jyo_cd="05",  # 東京
            hondai="テスト東京記念",
            kyori="2000",
            hasso_time="1510",
        )
        parser = factory.get_parser("RA")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "RA"
        assert result["JyoCD"] == "05"
        assert result["Hondai"] == "テスト東京記念"
        assert result["Kyori"] == "2000"
        assert result["HassoTime"] == "1510"

    def test_parse_nar_ra_record(self, factory):
        """NAR RA record parses with same parser (format is identical)."""
        data = make_ra_record_nar(
            jyo_cd="55",  # 佐賀
            hondai="テスト佐賀記念",
            kyori="1400",
        )
        parser = factory.get_parser("RA")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "RA"
        assert result["JyoCD"] == "55"
        assert result["Hondai"] == "テスト佐賀記念"
        assert result["Kyori"] == "1400"

    def test_ra_record_length(self, factory):
        """RA record should be exactly 856 bytes."""
        data = make_ra_record()
        assert len(data) == 856
        parser = factory.get_parser("RA")
        assert parser.RECORD_LENGTH == 856

    def test_ra_all_jyo_codes(self, factory):
        """RA parser works with both JRA (01-10) and NAR (30-57) codes."""
        parser = factory.get_parser("RA")

        for jyo_cd in ["01", "05", "10", "30", "44", "55"]:
            data = make_ra_record(jyo_cd=jyo_cd)
            result = parser.parse(data)
            assert result is not None
            assert result["JyoCD"] == jyo_cd

    def test_ra_japanese_text_fields(self, factory):
        """RA parser correctly handles multi-byte Japanese text."""
        parser = factory.get_parser("RA")

        # Long Japanese name that fills the field
        long_name = "第１回テスト特別競走大会"  # 24 bytes in cp932
        data = make_ra_record(hondai=long_name)
        result = parser.parse(data)
        assert result is not None
        assert result["Hondai"] == long_name


class TestSEParser:
    """SE (馬毎レース情報) parser tests."""

    def test_parse_se_record(self, factory):
        """SE record parses correctly."""
        data = make_se_record(
            umaban="03",
            kettonum="2020100001",
            bamei="テストウマサン",
        )
        parser = factory.get_parser("SE")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "SE"
        assert result["Umaban"] == "03"
        assert result["KettoNum"] == "2020100001"
        assert result["Bamei"] == "テストウマサン"

    def test_se_record_length(self, factory):
        """SE record should be 463 bytes."""
        data = make_se_record()
        assert len(data) == 463


class TestH1Parser:
    """H1 (票数1 全掛式) parser tests.

    IMPORTANT: NV-Link returns the full 28,955-byte H1 struct (JV_H1_HYOSU_ZENKAKE),
    containing arrays for all bet combinations (28 tansho, 153 umaren, etc.).
    Our current parser expects 317-byte flat records with single entries per bet type.

    This is a known format mismatch documented in issue #027.
    """

    def test_h1_flat_record_parse(self, factory):
        """H1 flat record (317 bytes) parses correctly with current parser."""
        data = make_h1_record_flat(
            jyo_cd="05",
            tan_uma="03",
            tan_hyo="00000012345",
        )
        parser = factory.get_parser("H1")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "H1"
        assert result["TanUma"] == "03"
        assert result["TanHyo"] == "00000012345"

    def test_h1_full_record_size(self):
        """Full H1 record from NV-Link is 28,955 bytes."""
        data = make_h1_record_full()
        assert len(data) == 28955

    def test_h1_full_record_header_parse(self, factory):
        """Parser can at least read header from full 28,955-byte record."""
        data = make_h1_record_full(
            jyo_cd="55",
            race_num="05",
            toroku_tosu="09",
        )
        parser = factory.get_parser("H1")
        result = parser.parse(data)

        # Parser reads first 317 bytes - header fields should be correct
        assert result is not None
        assert result["RecordSpec"] == "H1"
        assert result["JyoCD"] == "55"
        assert result["RaceNum"] == "05"
        assert result["TorokuTosu"] == "09"

    def test_h1_full_record_data_misalignment(self, factory):
        """Document that full H1 struct misaligns with flat parser.

        When the full 28,955-byte record is fed to the 317-byte parser,
        fields after HenkanUma3 (position 42) are misaligned because
        the flat parser expects single entries while the full struct
        has arrays (28 HenkanUma entries, not 3).
        """
        data = make_h1_record_full(jyo_cd="55")
        parser = factory.get_parser("H1")
        result = parser.parse(data)

        assert result is not None
        # Header fields are correct
        assert result["RecordSpec"] == "H1"
        assert result["JyoCD"] == "55"

        # But TanUma reads from position 42-43, which in the full struct
        # is HenkanUma[3] and HenkanUma[4], not the first TanSho entry.
        # The first TanSho in the full struct starts at position 83.
        # This documents the known misalignment.
        assert result["TanUma"] is not None  # Will have some value, but wrong

    def test_h1_nar_full_record_format(self):
        """NAR H1 full record has identical format to JRA."""
        nar_data = make_h1_record_nar_full(jyo_cd="55")
        jra_data = make_h1_record_full(jyo_cd="05")

        assert len(nar_data) == len(jra_data) == 28955
        # Only jyo_cd differs
        assert nar_data[19:21] == b'55'
        assert jra_data[19:21] == b'05'

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "raw_dumps", "nar_H1_001.bin"
        )),
        reason="Real NAR data dump not available"
    )
    def test_h1_real_nar_data(self, factory):
        """Parse real NAR H1 data from NV-Link dump."""
        dump_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "raw_dumps", "nar_H1_001.bin"
        )
        with open(dump_path, "rb") as f:
            data = f.read()

        assert len(data) == 28955

        parser = factory.get_parser("H1")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "H1"
        # JyoCD should be NAR range (30-57)
        jyo = int(result["JyoCD"])
        assert 30 <= jyo <= 57, f"NAR JyoCD should be 30-57, got {jyo}"


class TestHRParser:
    """HR (払戻) parser tests."""

    def test_hr_record_parse(self, factory):
        """HR record parses correctly."""
        data = make_hr_record(jyo_cd="05")
        parser = factory.get_parser("HR")
        result = parser.parse(data)

        assert result is not None
        assert result["RecordSpec"] == "HR"


class TestAllParsersBasic:
    """Basic tests for all 41 parsers."""

    RECORD_LENGTHS = {
        'BN': 387, 'BR': 455, 'CH': 592, 'DM': 48,
        'H1': 317, 'H6': 78, 'HC': 60, 'HN': 251, 'HR': 719,
        'HS': 200, 'HY': 123,
        'JG': 80, 'KS': 772,
        'HA': 1032,
        'O1': 107, 'O2': 66, 'O3': 70, 'O4': 66, 'O5': 68, 'O6': 70,
        'RA': 856, 'RC': 241, 'SE': 463, 'SK': 78,
        'TK': 727, 'TM': 39,
        'UM': 1110, 'WF': 169, 'YS': 146,
    }

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_loads(self, factory, record_type):
        """Every parser can be loaded."""
        parser = factory.get_parser(record_type)
        assert parser is not None, f"Failed to load {record_type} parser"

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_has_parse_method(self, factory, record_type):
        """Every parser has a callable parse method."""
        parser = factory.get_parser(record_type)
        assert hasattr(parser, 'parse')
        assert callable(parser.parse)

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_handles_minimal_data(self, factory, record_type):
        """Parser handles minimal valid data without crashing."""
        parser = factory.get_parser(record_type)
        record_len = getattr(parser, 'RECORD_LENGTH', 100)

        # Create minimal data with correct record spec
        data = record_type.encode('cp932')
        data += b'1'  # DataKubun
        data += b'20260101'  # MakeDate
        data += b' ' * (record_len - len(data))

        # Should not raise
        result = parser.parse(data)
        if result is not None:
            assert result.get("RecordSpec") == record_type

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_handles_empty_data(self, factory, record_type):
        """Parser handles empty data gracefully (returns None or raises ValueError)."""
        parser = factory.get_parser(record_type)
        try:
            result = parser.parse(b"")
            # Should return None
        except (ValueError, IndexError):
            pass  # Acceptable to raise on empty data

    @pytest.mark.parametrize("record_type", ALL_RECORD_TYPES)
    def test_parser_handles_short_data(self, factory, record_type):
        """Parser handles data shorter than expected without crashing."""
        parser = factory.get_parser(record_type)
        short_data = record_type.encode('cp932') + b'1' + b'20260101'
        # Should not raise (may return None or partial data)
        try:
            result = parser.parse(short_data)
        except Exception:
            pytest.fail(f"{record_type} parser crashed on short data")


class TestNARJRAFormatCompatibility:
    """Verify that NAR and JRA use identical record formats.

    NV-Link (NAR) uses the same JV-Data record format as JV-Link (JRA).
    The only differences are:
    - JyoCD range: JRA=01-10, NAR=30-57
    - Table names: JRA=NL_XX, NAR=NL_XX_NAR

    Record byte layouts are identical.
    """

    def test_ra_format_identical(self, factory):
        """RA format is identical between JRA and NAR."""
        parser = factory.get_parser("RA")

        jra_data = make_ra_record(jyo_cd="05", hondai="中央テスト")
        nar_data = make_ra_record(jyo_cd="55", hondai="地方テスト")

        jra_result = parser.parse(jra_data)
        nar_result = parser.parse(nar_data)

        assert jra_result is not None
        assert nar_result is not None

        # Same fields exist
        assert set(jra_result.keys()) == set(nar_result.keys())

        # Different values for jyo-specific fields
        assert jra_result["JyoCD"] == "05"
        assert nar_result["JyoCD"] == "55"

    def test_h1_format_identical(self):
        """H1 full record format is identical between JRA and NAR."""
        jra = make_h1_record_full(jyo_cd="05")
        nar = make_h1_record_full(jyo_cd="55")

        assert len(jra) == len(nar) == 28955

        # Structure is the same, only content differs
        # Header structure
        assert jra[0:2] == nar[0:2] == b'H1'
        assert jra[27:29] == nar[27:29]  # TorokuTosu at same position

    def test_crlf_termination(self):
        """All records end with CRLF."""
        for record_fn in [make_ra_record, make_se_record, make_hr_record,
                          make_h1_record_flat, make_h1_record_full,
                          make_wf_record, make_bn_record]:
            data = record_fn()
            assert data[-2:] == b'\r\n', f"{record_fn.__name__} missing CRLF"


class TestH1FullStructParsing:
    """Tests for parsing the full 28,955-byte H1 struct.

    Documents the expected field positions for a potential future
    full-struct parser.
    """

    def test_full_struct_field_positions(self):
        """Verify field positions in full H1 struct match kmy-keiba spec."""
        data = make_h1_record_full(
            year="2026",
            month_day="0207",
            jyo_cd="55",
            kaiji="19",
            nichiji="01",
            race_num="01",
            toroku_tosu="09",
            syusso_tosu="09",
        )

        # Header (1-indexed positions from spec, converted to 0-indexed)
        assert data[0:2].decode('ascii') == "H1"     # RecordSpec
        assert data[2:3].decode('ascii') == "4"       # DataKubun
        assert data[3:11].decode('ascii') == "20260101"  # MakeDate (default)
        assert data[11:15].decode('ascii') == "2026"  # Year
        assert data[15:19].decode('ascii') == "0207"  # MonthDay
        assert data[19:21].decode('ascii') == "55"    # JyoCD
        assert data[21:23].decode('ascii') == "19"    # Kaiji
        assert data[23:25].decode('ascii') == "01"    # Nichiji
        assert data[25:27].decode('ascii') == "01"    # RaceNum
        assert data[27:29].decode('ascii') == "09"    # TorokuTosu
        assert data[29:31].decode('ascii') == "09"    # SyussoTosu

        # HatubaiFlag (7 flags, 1 byte each, position 32-38)
        for i in range(7):
            assert data[31 + i:32 + i] == b'7'

        # FukuChakuBaraiKey (position 39)
        assert data[38:39] == b'3'

        # HenkanUma x28 (position 40-67)
        # HenkanWaku x8 (position 68-75)
        # HenkanDoWaku x8 (position 76-83)

        # TanSho array starts at position 84 (0-indexed: 83)
        # Each entry: umaban(2) + hyo(11) + ninki(2) = 15 bytes
        # 28 entries = 420 bytes
        assert data[83:85].decode('ascii') == "01"  # First horse number

        # FukuSho starts at 83 + 420 = 503
        assert data[503:505].decode('ascii') == "01"

        # CRLF at end
        assert data[28953:28955] == b'\r\n'

    def test_full_struct_tansho_array(self):
        """TanSho array in full struct has 28 entries of 15 bytes each."""
        data = make_h1_record_full(syusso_tosu="10")

        # TanSho starts at byte 83
        for i in range(10):
            offset = 83 + (15 * i)
            umaban = data[offset:offset + 2].decode('ascii')
            assert umaban == f"{i+1:02d}", f"TanSho[{i}] umaban should be {i+1:02d}"

            hyo = data[offset + 2:offset + 13].decode('ascii').strip()
            assert hyo.isdigit(), f"TanSho[{i}] hyo should be numeric"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
