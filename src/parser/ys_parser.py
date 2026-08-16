#!/usr/bin/env python
"""Parser for the official 382-byte JV-Data YS schedule record."""

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger


class YSParser:
    """Parse one complete schedule row with all three graded-race guides."""

    RECORD_TYPE = "YS"
    RECORD_LENGTH = 382

    _GUIDANCE_FIELDS = (
        ("TokuNum", 0, 4),
        ("Hondai", 4, 60),
        ("Ryakusyo10", 64, 20),
        ("Ryakusyo6", 84, 12),
        ("Ryakusyo3", 96, 6),
        ("Nkai", 102, 3),
        ("GradeCD", 105, 1),
        ("SyubetuCD", 106, 2),
        ("KigoCD", 108, 3),
        ("JyuryoCD", 111, 1),
        ("Kyori", 112, 4),
        ("TrackCD", 116, 2),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Strictly decode one byte-sliced CP932 field and trim its padding."""
        return data.decode(ENCODING_JVDATA).strip()

    def parse(self, data: bytes) -> dict[str, str] | None:
        """Return every official YS field, or ``None`` for invalid framing."""
        try:
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "YS record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("YS record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("YS record delimiter mismatch: expected CR/LF")
                return None

            result: dict[str, str] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "Year": self.decode_field(data[11:15]),
                "MonthDay": self.decode_field(data[15:19]),
                "JyoCD": self.decode_field(data[19:21]),
                "Kaiji": self.decode_field(data[21:23]),
                "Nichiji": self.decode_field(data[23:25]),
                "YoubiCD": self.decode_field(data[25:26]),
            }
            for number in range(1, 4):
                start = 26 + 118 * (number - 1)
                for suffix, relative, size in self._GUIDANCE_FIELDS:
                    result[f"Jyusyo{number}{suffix}"] = self.decode_field(
                        data[start + relative : start + relative + size]
                    )
            result["RecordDelimiter"] = self.decode_field(data[380:382])
            return result
        except (UnicodeDecodeError, ValueError) as error:
            self.logger.warning(f"YS record parse failed: {error}")
            return None
