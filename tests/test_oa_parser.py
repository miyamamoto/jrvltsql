"""Tests for OA (NAR Odds) parser."""

import pytest


class TestOAParser:
    """Test OA parser basic functionality."""

    def setup_method(self):
        from src.parser.oa_parser import OAParser
        self.parser = OAParser()

    def test_parse_minimal_header(self):
        """Test parsing minimal OA header data."""
        # 27 bytes: RecordSpec(2) + DataKubun(1) + MakeDate(8) + KaisaiDate(8) + JyoCD(2) + Kaiji(2) + Nichiji(2) + RaceNum(2)
        data = b"OA1202602092026020944010101"
        result = self.parser.parse(data)
        assert result is not None
        assert result["RecordSpec"] == "OA"
        assert result["DataKubun"] == "1"
        assert result["MakeDate"] == "20260209"
        assert result["KaisaiDate"] == "20260209"
        assert result["JyoCD"] == "44"
        assert result["Kaiji"] == "01"
        assert result["Nichiji"] == "01"
        assert result["RaceNum"] == "01"
        # Stub fields
        assert result["OddsType"] == ""
        assert result["Kumi"] == ""
        assert result["Odds"] == 0.0
        assert result["Ninki"] == 0

    def test_parse_short_data_returns_none(self):
        """Test that short data returns None."""
        data = b"OA1"
        result = self.parser.parse(data)
        assert result is None

    def test_parse_empty_data(self):
        """Test that empty data returns None."""
        data = b""
        result = self.parser.parse(data)
        assert result is None

    def test_parse_with_crlf(self):
        """Test parsing data with CRLF at end."""
        data = b"OA1202602092026020944010101\r\n"
        result = self.parser.parse(data)
        assert result is not None
        assert result["RecordSpec"] == "OA"

    def test_record_type(self):
        """Test record type attribute."""
        assert self.parser.RECORD_TYPE == "OA"


class TestOAParserFactoryIntegration:
    """Test OA parser integration with ParserFactory."""

    def test_factory_loads_oa_parser(self):
        """Test that ParserFactory can load OA parser."""
        from src.parser.factory import get_parser_factory
        factory = get_parser_factory()
        parser = factory.get_parser("OA")
        assert parser is not None
        assert parser.RECORD_TYPE == "OA"
