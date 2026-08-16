#!/usr/bin/env python
"""Parser for the official 501-byte JV-Data RC record master."""

from src.jvlink.constants import ENCODING_JVDATA
from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class RCParser:
    """Parse one complete current RC record, including all three tied holders."""

    RECORD_TYPE = "RC"
    RECORD_LENGTH = 501

    _HOLDER_FIELDS = (
        ("KettoNum", 0, 10),
        ("Bamei", 10, 36),
        ("UmaKigoCD", 46, 2),
        ("SexCD", 48, 1),
        ("ChokyosiCode", 49, 5),
        ("ChokyosiName", 54, 34),
        ("Futan", 88, 3),
        ("KisyuCode", 91, 5),
        ("KisyuName", 96, 34),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Strictly decode one byte-sliced CP932 field and trim its padding."""
        return data.decode(ENCODING_JVDATA).strip()

    def parse(self, data: bytes) -> dict[str, str] | None:
        """Return every official RC field, or ``None`` for invalid framing."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "RC record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("RC record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("RC record delimiter mismatch: expected CR/LF")
                return None

            result: dict[str, str] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "RecInfoKubun": self.decode_field(data[11:12]),
                "Year": self.decode_field(data[12:16]),
                "MonthDay": self.decode_field(data[16:20]),
                "JyoCD": self.decode_field(data[20:22]),
                "Kaiji": self.decode_field(data[22:24]),
                "Nichiji": self.decode_field(data[24:26]),
                "RaceNum": self.decode_field(data[26:28]),
                "TokuNum": self.decode_field(data[28:32]),
                "Hondai": self.decode_field(data[32:92]),
                "GradeCD": self.decode_field(data[92:93]),
                "SyubetuCD": self.decode_field(data[93:95]),
                "Kyori": self.decode_field(data[95:99]),
                "TrackCD": self.decode_field(data[99:101]),
                "RecKubun": self.decode_field(data[101:102]),
                "RecTime": self.decode_field(data[102:106]),
                "TenkoCD": self.decode_field(data[106:107]),
                "SibaBabaCD": self.decode_field(data[107:108]),
                "DirtBabaCD": self.decode_field(data[108:109]),
            }

            for number in range(1, 4):
                start = 109 + 130 * (number - 1)
                for suffix, relative, size in self._HOLDER_FIELDS:
                    result[f"RecUma{suffix}{number}"] = self.decode_field(
                        data[start + relative : start + relative + size]
                    )

            result["Crlf"] = self.decode_field(data[499:501])
            return result
        except (UnicodeDecodeError, ValueError) as error:
            self.logger.warning(f"RC record parse failed: {error}")
            return None
