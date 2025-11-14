"""Unit tests for JV-Data parsers."""

import pytest

from src.parser.base import BaseParser, FieldDef
from src.parser.factory import ParserFactory, get_parser_factory
from src.parser.hr_parser import HRParser
from src.parser.ra_parser import RAParser
from src.parser.se_parser import SEParser


class TestFieldDef:
    """Test cases for FieldDef class."""

    def test_field_def_creation(self):
        """Test field definition creation."""
        field = FieldDef("test_field", 0, 10, "str", "Test field")
        assert field.name == "test_field"
        assert field.start == 0
        assert field.length == 10
        assert field.type == "str"
        assert field.description == "Test field"

    def test_field_def_defaults(self):
        """Test field definition with defaults."""
        field = FieldDef("field", 5, 3)
        assert field.type == "str"
        assert field.description == ""


class TestBaseParser:
    """Test cases for BaseParser class."""

    def test_base_parser_cannot_instantiate(self):
        """Test that BaseParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseParser()

    def test_concrete_parser_requires_record_type(self):
        """Test that concrete parser must define record_type."""

        class InvalidParser(BaseParser):
            def _define_fields(self):
                return []

        with pytest.raises(ValueError):
            InvalidParser()


class TestRAParser:
    """Test cases for RA (Race) parser."""

    def test_parser_initialization(self):
        """Test RA parser initialization."""
        parser = RAParser()
        assert parser.record_type == "RA"
        assert len(parser._fields) > 0
        assert len(parser.get_field_names()) > 0

    def test_parse_ra_record(self):
        """Test parsing RA record."""
        parser = RAParser()

        # Create a minimal valid RA record (fixed-length)
        # Format: RecordSpec(2) + DataKubun(1) + MakeDate(8) + ...
        record = b"RA1"  # RecordSpec + DataKubun
        record += b"20240601"  # MakeDate
        record += b"2024"  # idYear (offset 11)
        record += b"0601"  # idMonthDay (offset 15)
        record += b"06"  # idJyoCD (offset 19)
        record += b"03"  # idKaiji (offset 21)
        record += b"08"  # idNichiji (offset 23)
        record += b"11"  # idRaceNum (offset 25)
        # Pad to reach minimum expected length
        record += b" " * (1200 - len(record))

        data = parser.parse(record)
        assert data is not None
        assert data["headRecordSpec"] == "RA"
        assert data["headDataKubun"] == "1"
        assert data["idYear"] == "2024"
        assert data["idMonthDay"] == "0601"
        assert data["idJyoCD"] == "06"
        assert data["idRaceNum"] == "11"

    def test_parse_invalid_record_type(self):
        """Test parsing with wrong record type."""
        parser = RAParser()
        record = b"SE1" + b" " * 1000

        with pytest.raises(ValueError, match="Record type mismatch"):
            parser.parse(record)

    def test_parse_empty_record(self):
        """Test parsing empty record."""
        parser = RAParser()

        with pytest.raises(ValueError, match="Empty record"):
            parser.parse(b"")

    def test_get_field_names(self):
        """Test getting field names."""
        parser = RAParser()
        field_names = parser.get_field_names()

        assert "headRecordSpec" in field_names
        assert "idYear" in field_names
        assert "RaceName" in field_names
        assert "Kyori" in field_names

    def test_get_field_def(self):
        """Test getting field definition."""
        parser = RAParser()
        field_def = parser.get_field_def("headRecordSpec")

        assert field_def is not None
        assert field_def.name == "headRecordSpec"
        assert field_def.start == 0
        assert field_def.length == 2

    def test_repr(self):
        """Test string representation."""
        parser = RAParser()
        repr_str = repr(parser)

        assert "RAParser" in repr_str
        assert "RA" in repr_str


class TestSEParser:
    """Test cases for SE (Race-Horse) parser."""

    def test_parser_initialization(self):
        """Test SE parser initialization."""
        parser = SEParser()
        assert parser.record_type == "SE"
        assert len(parser._fields) > 0

    def test_parse_se_record(self):
        """Test parsing SE record."""
        parser = SEParser()

        # Create a minimal valid SE record
        record = b"SE1"  # RecordSpec + DataKubun
        record += b"20240601"  # MakeDate
        record += b"2024"  # idYear (offset 11)
        record += b"0601"  # idMonthDay
        record += b"06"  # idJyoCD
        record += b"03"  # idKaiji
        record += b"08"  # idNichiji
        record += b"11"  # idRaceNum
        record += b"2024012345"  # KettoNum (offset 27, 10 bytes)
        record += b" " * (400 - len(record))

        data = parser.parse(record)
        assert data is not None
        assert data["headRecordSpec"] == "SE"
        assert data["KettoNum"] == "2024012345"


class TestHRParser:
    """Test cases for HR (Payout) parser."""

    def test_parser_initialization(self):
        """Test HR parser initialization."""
        parser = HRParser()
        assert parser.record_type == "HR"
        assert len(parser._fields) > 0

    def test_parse_hr_record(self):
        """Test parsing HR record."""
        parser = HRParser()

        # Create a minimal valid HR record
        record = b"HR1"  # RecordSpec + DataKubun
        record += b"20240601"  # MakeDate
        record += b"2024"  # idYear (offset 11)
        record += b"0601"  # idMonthDay
        record += b"06"  # idJyoCD
        record += b"03"  # idKaiji
        record += b"08"  # idNichiji
        record += b"11"  # idRaceNum
        record += b" " * (850 - len(record))

        data = parser.parse(record)
        assert data is not None
        assert data["headRecordSpec"] == "HR"


class TestParserFactory:
    """Test cases for ParserFactory."""

    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = ParserFactory()
        assert len(factory.supported_types()) == 3
        assert "RA" in factory.supported_types()
        assert "SE" in factory.supported_types()
        assert "HR" in factory.supported_types()

    def test_get_parser(self):
        """Test getting parser by type."""
        factory = ParserFactory()

        ra_parser = factory.get_parser("RA")
        assert ra_parser is not None
        assert isinstance(ra_parser, RAParser)

        se_parser = factory.get_parser("SE")
        assert se_parser is not None
        assert isinstance(se_parser, SEParser)

        hr_parser = factory.get_parser("HR")
        assert hr_parser is not None
        assert isinstance(hr_parser, HRParser)

    def test_get_parser_caching(self):
        """Test that parsers are cached."""
        factory = ParserFactory()

        parser1 = factory.get_parser("RA")
        parser2 = factory.get_parser("RA")

        assert parser1 is parser2  # Same instance

    def test_get_parser_unsupported(self):
        """Test getting parser for unsupported type."""
        factory = ParserFactory()
        parser = factory.get_parser("XX")

        assert parser is None

    def test_get_parser_empty_type(self):
        """Test getting parser with empty type."""
        factory = ParserFactory()
        parser = factory.get_parser("")

        assert parser is None

    def test_register_parser(self):
        """Test registering custom parser."""

        class CustomParser(BaseParser):
            record_type = "XX"

            def _define_fields(self):
                return [FieldDef("test", 0, 2)]

        factory = ParserFactory()
        factory.register_parser("XX", CustomParser)

        assert "XX" in factory.supported_types()
        parser = factory.get_parser("XX")
        assert parser is not None
        assert isinstance(parser, CustomParser)

    def test_register_invalid_parser(self):
        """Test registering non-BaseParser class."""

        class InvalidParser:
            pass

        factory = ParserFactory()

        with pytest.raises(ValueError, match="must inherit from BaseParser"):
            factory.register_parser("XX", InvalidParser)

    def test_parse_auto_detect(self):
        """Test auto-detection parsing."""
        factory = ParserFactory()

        # Create RA record
        record = b"RA1" + b"20240601" + b"2024" + b"0601" + b"06" + b"03" + b"08" + b"11"
        record += b" " * (1200 - len(record))

        data = factory.parse(record)
        assert data is not None
        assert data["headRecordSpec"] == "RA"

    def test_parse_invalid_record(self):
        """Test parsing invalid record."""
        factory = ParserFactory()

        # Too short
        assert factory.parse(b"R") is None

        # Empty
        assert factory.parse(b"") is None

    def test_repr(self):
        """Test string representation."""
        factory = ParserFactory()
        repr_str = repr(factory)

        assert "ParserFactory" in repr_str

    def test_get_global_factory(self):
        """Test getting global factory instance."""
        factory1 = get_parser_factory()
        factory2 = get_parser_factory()

        assert factory1 is factory2  # Singleton
