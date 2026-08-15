#!/usr/bin/env python
"""CH trainer-master parser for the official current 3862-byte layout."""

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger


class CHParser:
    """Parse CH into one normalized header and three coupled result rows."""

    RECORD_TYPE = "CH"
    RECORD_LENGTH = 3862

    _RECENT_SUBFIELDS = (
        ("id", 0, 16),
        ("Hondai", 16, 60),
        ("Ryakusyo10", 76, 20),
        ("Ryakusyo6", 96, 12),
        ("Ryakusyo3", 108, 6),
        ("GradeCD", 114, 1),
        ("SyussoTosu", 115, 2),
        ("KettoNum", 117, 10),
        ("Bamei", 127, 36),
    )

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Strictly decode one byte-sliced CP932 field and trim padding."""
        return data.decode(ENCODING_JVDATA).strip()

    def _parse_recent_wins(self, data: bytes, result: dict[str, object]) -> None:
        for block in range(1, 4):
            start = 215 + 163 * (block - 1)
            for suffix, relative, size in self._RECENT_SUBFIELDS:
                result[f"SaikinJyusyo{block}_{suffix}"] = self.decode_field(
                    data[start + relative : start + relative + size]
                )

    def _parse_result_block(
        self,
        data: bytes,
        *,
        start: int,
        make_date: str,
        trainer_code: str,
        number: int,
    ) -> dict[str, str]:
        row = {
            "MakeDate": make_date,
            "ChokyosiCode": trainer_code,
            "Num": str(number),
            "SetYear": self.decode_field(data[start : start + 4]),
            "HonSyokinHeichi": self.decode_field(data[start + 4 : start + 14]),
            "HonSyokinSyogai": self.decode_field(data[start + 14 : start + 24]),
            "FukaSyokinHeichi": self.decode_field(data[start + 24 : start + 34]),
            "FukaSyokinSyogai": self.decode_field(data[start + 34 : start + 44]),
        }

        for rank in range(1, 7):
            offset = start + 44 + 6 * (rank - 1)
            row[f"HeichiChakukaisu{rank}"] = self.decode_field(data[offset : offset + 6])
        for rank in range(1, 7):
            offset = start + 80 + 6 * (rank - 1)
            row[f"SyogaiChakukaisu{rank}"] = self.decode_field(data[offset : offset + 6])
        for course in range(1, 21):
            course_start = start + 116 + 36 * (course - 1)
            for rank in range(1, 7):
                offset = course_start + 6 * (rank - 1)
                row[f"Jyo{course}Chakukaisu{rank}"] = self.decode_field(data[offset : offset + 6])
        for distance in range(1, 7):
            distance_start = start + 836 + 36 * (distance - 1)
            for rank in range(1, 7):
                offset = distance_start + 6 * (rank - 1)
                row[f"Kyori{distance}Chakukaisu{rank}"] = self.decode_field(
                    data[offset : offset + 6]
                )
        return row

    def parse(self, data: bytes) -> dict[str, object] | None:
        """Return the 42-field header plus three private normalized result rows."""
        try:
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(f"CHレコード長不正: expected={self.RECORD_LENGTH}, actual={len(data)}")
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("CHレコード種別不正")
                return None
            if data[3860:3862] != b"\r\n":
                self.logger.warning("CHレコード区切り不正")
                return None

            result: dict[str, object] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "ChokyosiCode": self.decode_field(data[11:16]),
                "DelKubun": self.decode_field(data[16:17]),
                "IssueDate": self.decode_field(data[17:25]),
                "DelDate": self.decode_field(data[25:33]),
                "BirthDate": self.decode_field(data[33:41]),
                "ChokyosiName": self.decode_field(data[41:75]),
                "ChokyosiNameKana": self.decode_field(data[75:105]),
                "ChokyosiRyakusyo": self.decode_field(data[105:113]),
                "ChokyosiNameEng": self.decode_field(data[113:193]),
                "SexCD": self.decode_field(data[193:194]),
                "TozaiCD": self.decode_field(data[194:195]),
                "Syotai": self.decode_field(data[195:215]),
            }
            self._parse_recent_wins(data, result)

            make_date = str(result["MakeDate"])
            trainer_code = str(result["ChokyosiCode"])
            result["_ch_seiseki_rows"] = [
                self._parse_result_block(
                    data,
                    start=704 + 1052 * (block - 1),
                    make_date=make_date,
                    trainer_code=trainer_code,
                    number=block,
                )
                for block in range(1, 4)
            ]
            result["RecordDelimiter"] = self.decode_field(data[3860:3862])
            return result
        except (UnicodeDecodeError, ValueError, TypeError) as error:
            self.logger.error(f"CHレコードパース中にエラー: {error}")
            return None
