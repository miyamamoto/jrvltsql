#!/usr/bin/env python
"""KS jockey-master parser for the official current 4,173-byte layout."""

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger


class KSParser:
    """Parse one KS master into a header and three normalized result rows."""

    RECORD_TYPE = "KS"
    RECORD_LENGTH = 4173

    _FIRST_RIDE_SUBFIELDS = (
        ("Hatukijyoid", 0, 16),
        ("SyussoTosu", 16, 2),
        ("KettoNum", 18, 10),
        ("Bamei", 28, 36),
        ("KakuteiJyuni", 64, 2),
        ("IJyoCD", 66, 1),
    )
    _FIRST_WIN_SUBFIELDS = (
        ("Hatusyoriid", 0, 16),
        ("SyussoTosu", 16, 2),
        ("KettoNum", 18, 10),
        ("Bamei", 28, 36),
    )
    _RECENT_SUBFIELDS = (
        ("SaikinJyusyoid", 0, 16),
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
        """Strictly decode one byte-sliced CP932 field and trim its padding."""
        return data.decode(ENCODING_JVDATA).strip()

    @staticmethod
    def _require_digits(name: str, value: str) -> None:
        if not value.isascii() or not value.isdigit():
            raise ValueError(f"{name} must contain only ASCII digits")

    def _parse_repeated_header(self, data: bytes, result: dict[str, object]) -> None:
        for block in range(1, 3):
            start = 264 + 67 * (block - 1)
            for suffix, relative, size in self._FIRST_RIDE_SUBFIELDS:
                field_name = f"HatuKiJyo{block}{suffix}"
                value = self.decode_field(data[start + relative : start + relative + size])
                result[field_name] = value
                if suffix in {"Hatukijyoid", "SyussoTosu", "KettoNum", "KakuteiJyuni", "IJyoCD"}:
                    self._require_digits(field_name, value)

        for block in range(1, 3):
            start = 398 + 64 * (block - 1)
            for suffix, relative, size in self._FIRST_WIN_SUBFIELDS:
                field_name = f"HatuSyori{block}{suffix}"
                value = self.decode_field(data[start + relative : start + relative + size])
                result[field_name] = value
                if suffix in {"Hatusyoriid", "SyussoTosu", "KettoNum"}:
                    self._require_digits(field_name, value)

        for block in range(1, 4):
            start = 526 + 163 * (block - 1)
            for suffix, relative, size in self._RECENT_SUBFIELDS:
                field_name = f"SaikinJyusyo{block}{suffix}"
                value = self.decode_field(data[start + relative : start + relative + size])
                result[field_name] = value
                if suffix in {"SaikinJyusyoid", "SyussoTosu", "KettoNum"}:
                    self._require_digits(field_name, value)

    def _parse_result_block(
        self,
        data: bytes,
        *,
        start: int,
        make_date: str,
        jockey_code: str,
        number: int,
    ) -> dict[str, str]:
        row = {
            "MakeDate": make_date,
            "KisyuCode": jockey_code,
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

        for field_name, value in row.items():
            if field_name not in {"MakeDate", "KisyuCode"}:
                self._require_digits(field_name, value)
        return row

    def parse(self, data: bytes) -> dict[str, object] | None:
        """Return the complete header plus three private normalized result rows."""
        try:
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    f"KSレコード長不正: expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("KSレコード種別不正")
                return None
            if data[4171:4173] != b"\r\n":
                self.logger.warning("KSレコード区切り不正")
                return None

            result: dict[str, object] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "KisyuCode": self.decode_field(data[11:16]),
                "DelKubun": self.decode_field(data[16:17]),
                "IssueDate": self.decode_field(data[17:25]),
                "DelDate": self.decode_field(data[25:33]),
                "BirthDate": self.decode_field(data[33:41]),
                "KisyuName": self.decode_field(data[41:75]),
                "reserved": self.decode_field(data[75:109]),
                "KisyuNameKana": self.decode_field(data[109:139]),
                "KisyuRyakusyo": self.decode_field(data[139:147]),
                "KisyuNameEng": self.decode_field(data[147:227]),
                "SexCD": self.decode_field(data[227:228]),
                "SikakuCD": self.decode_field(data[228:229]),
                "MinaraiCD": self.decode_field(data[229:230]),
                "TozaiCD": self.decode_field(data[230:231]),
                "Syotai": self.decode_field(data[231:251]),
                "ChokyosiCode": self.decode_field(data[251:256]),
                "ChokyosiRyakusyo": self.decode_field(data[256:264]),
            }
            if result["DataKubun"] not in {"0", "1", "2"}:
                raise ValueError("DataKubun must be 0, 1, or 2")
            for field_name in (
                "MakeDate",
                "KisyuCode",
                "DelKubun",
                "IssueDate",
                "DelDate",
                "BirthDate",
                "SexCD",
                "SikakuCD",
                "MinaraiCD",
                "TozaiCD",
                "ChokyosiCode",
            ):
                self._require_digits(field_name, str(result[field_name]))

            self._parse_repeated_header(data, result)
            make_date = str(result["MakeDate"])
            jockey_code = str(result["KisyuCode"])
            result["_ks_seiseki_rows"] = [
                self._parse_result_block(
                    data,
                    start=1015 + 1052 * (block - 1),
                    make_date=make_date,
                    jockey_code=jockey_code,
                    number=block,
                )
                for block in range(1, 4)
            ]
            result["RecordDelimiter"] = self.decode_field(data[4171:4173])
            return result
        except (UnicodeDecodeError, ValueError, TypeError) as error:
            self.logger.error(f"KSレコードパース中にエラー: {error}")
            return None
