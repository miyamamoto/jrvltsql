"""Unit tests for HA (地方競馬 払戻) parser."""

import pytest
from src.parser.ha_parser import HAParser


class TestHAParser:
    """HAParser tests."""

    def setup_method(self):
        self.parser = HAParser()

    def _build_record(
        self,
        record_spec=b"HA",
        data_kubun=b"1",
        make_date=b"20240101",
        kaisai_date=b"20240115",
        jyo_cd=b"10",
        kaiji=b"01",
        nichiji=b"02",
        race_num=b"05",
        toroku_tosu=b"12",
        syusso_tosu=b"11",
        hatsubai_flag=b"1",
        reserved=b"\x00" * 16 + b" " * 15,
        payout_data=None,
    ):
        """Build a test HA record (1032 bytes)."""
        header = (
            record_spec
            + data_kubun
            + make_date
            + kaisai_date
            + jyo_cd
            + kaiji
            + nichiji
            + race_num
            + toroku_tosu
            + syusso_tosu
        )
        assert len(header) == 31

        flags = hatsubai_flag + reserved
        assert len(flags) == 32

        if payout_data is None:
            # Default: 2 payout entries + separator + total
            payout_data = (
                b"01" + b"         1000"   # Kumi=01, Pay=1000
                + b"02" + b"         2500"  # Kumi=02, Pay=2500
                + b" " * 15                 # separator
                + b"00" + b"         3500"  # TotalPay=3500
            )

        # Pad to make total 1032 bytes (1030 + \r\n)
        body = header + flags + payout_data
        padding_needed = 1030 - len(body)
        if padding_needed > 0:
            body += b" " * padding_needed
        body = body[:1030] + b"\r\n"
        assert len(body) == 1032
        return body

    def test_basic_parse(self):
        """Test basic HA record parsing."""
        record = self._build_record()
        result = self.parser.parse(record)

        assert result is not None
        assert result["RecordSpec"] == "HA"
        assert result["DataKubun"] == "1"
        assert result["MakeDate"] == "20240101"
        assert result["KaisaiDate"] == "20240115"
        assert result["JyoCD"] == "10"
        assert result["Kaiji"] == "01"
        assert result["Nichiji"] == "02"
        assert result["RaceNum"] == "05"
        assert result["TorokuTosu"] == "12"
        assert result["SyussoTosu"] == "11"
        assert result["HatsubaiFlag"] == "1"

    def test_payout_entries(self):
        """Test payout data extraction."""
        record = self._build_record()
        result = self.parser.parse(record)

        assert result is not None
        assert result["PayKumi1"] == "01"
        assert result["PayAmount1"] == "1000"
        assert result["PayKumi2"] == "02"
        assert result["PayAmount2"] == "2500"
        assert result["TotalPay"] == "3500"
        assert result["PayoutCount"] == "2"

    def test_single_payout(self):
        """Test with single payout entry."""
        payout = (
            b"03" + b"          500"  # Kumi=03, Pay=500
            + b" " * 15               # separator
            + b"00" + b"          500"  # TotalPay
        )
        record = self._build_record(payout_data=payout)
        result = self.parser.parse(record)

        assert result is not None
        assert result["PayKumi1"] == "03"
        assert result["PayAmount1"] == "500"
        assert result["PayKumi2"] == ""
        assert result["PayAmount2"] == "0"
        assert result["PayoutCount"] == "1"

    def test_three_payouts(self):
        """Test with three payout entries."""
        payout = (
            b"01" + b"          100"
            + b"02" + b"          200"
            + b"03" + b"          300"
            + b" " * 15
            + b"00" + b"          600"
        )
        record = self._build_record(payout_data=payout)
        result = self.parser.parse(record)

        assert result is not None
        assert result["PayKumi1"] == "01"
        assert result["PayAmount1"] == "100"
        assert result["PayKumi2"] == "02"
        assert result["PayAmount2"] == "200"
        assert result["PayKumi3"] == "03"
        assert result["PayAmount3"] == "300"
        assert result["PayoutCount"] == "3"

    def test_empty_payout(self):
        """Test with no payout entries (all spaces)."""
        payout = b" " * 60
        record = self._build_record(payout_data=payout)
        result = self.parser.parse(record)

        assert result is not None
        assert result["PayoutCount"] == "0"
        assert result["PayKumi1"] == ""
        assert result["PayAmount1"] == "0"
        assert result["TotalPay"] == "0"

    def test_record_too_short(self):
        """Test with record shorter than minimum."""
        result = self.parser.parse(b"HA" + b"\x00" * 10)
        assert result is None

    def test_record_with_lf_ending(self):
        """Test record ending with just \\n instead of \\r\\n."""
        record = self._build_record()
        # Replace \r\n with \n
        record = record[:-2] + b" \n"
        result = self.parser.parse(record)
        assert result is not None
        assert result["RecordSpec"] == "HA"

    def test_record_without_crlf(self):
        """Test record without trailing newline."""
        record = self._build_record()
        record = record[:-2] + b"  "
        result = self.parser.parse(record)
        assert result is not None

    def test_decode_field_cp932(self):
        """Test decode_field with cp932 encoding."""
        assert HAParser.decode_field(b"  test  ") == "test"
        assert HAParser.decode_field(b"") == ""
        assert HAParser.decode_field(b"   ") == ""

    def test_parser_attributes(self):
        """Test parser class attributes."""
        assert self.parser.RECORD_TYPE == "HA"
        assert self.parser.RECORD_LENGTH == 1032
        assert self.parser.ENTRY_SIZE == 15
        assert self.parser.HEADER_SIZE == 31
