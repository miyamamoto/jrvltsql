"""Unit tests for NU (地方競馬 競走馬登録) parser."""

from src.parser.nu_parser import NUParser


class TestNUParser:
    """NUParser tests."""

    def setup_method(self):
        self.parser = NUParser()

    def _build_record(
        self,
        record_spec="NU",
        uma_id="4200502202",
        toroku_num="1199603170",
        reserved="0000000000000000",
        birth_date="19940405",
        bamei="新地タロウ          ",
    ):
        """Build a test NU record (64 bytes, cp932)."""
        # Encode in cp932 for Japanese characters
        raw = (
            record_spec
            + uma_id
            + toroku_num
            + reserved
            + birth_date
            + bamei
        )
        data = raw.encode("cp932")
        # Pad/truncate to 64 bytes
        if len(data) < 64:
            data += b" " * (64 - len(data))
        return data[:64]

    def test_basic_parse(self):
        """Test basic NU record parsing."""
        record = self._build_record()
        result = self.parser.parse(record)

        assert result is not None
        assert result["RecordSpec"] == "NU"
        assert result["UmaID"] == "4200502202"
        assert result["TorokuNum"] == "1199603170"
        assert result["BirthDate"] is not None

    def test_bamei_field(self):
        """Test horse name (bamei) extraction."""
        record = self._build_record(bamei="新地タロウ          ")
        result = self.parser.parse(record)

        assert result is not None
        # cp932 encoded name should be decoded
        assert "新地タロウ" in result["Bamei"] or "タロウ" in result.get("Bamei", "")

    def test_reserved_field(self):
        """Test reserved field."""
        record = self._build_record()
        result = self.parser.parse(record)

        assert result is not None
        assert result["Reserved"].strip("0") == "" or result["Reserved"] == "0000000000000000"

    def test_parser_attributes(self):
        """Test parser class attributes."""
        assert self.parser.record_type == "NU"

    def test_field_count(self):
        """Test number of defined fields."""
        fields = self.parser._define_fields()
        assert len(fields) == 6  # RecordSpec, UmaID, TorokuNum, Reserved, BirthDate, Bamei

    def test_different_horse(self):
        """Test with different horse data."""
        record = self._build_record(
            uma_id="5100301001",
            toroku_num="2200100001",
            birth_date="20010315",
            bamei="テストホース          ",
        )
        result = self.parser.parse(record)

        assert result is not None
        assert result["UmaID"] == "5100301001"
        assert result["TorokuNum"] == "2200100001"
        assert result["BirthDate"] is not None
