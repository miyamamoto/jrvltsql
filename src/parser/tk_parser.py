#!/usr/bin/env python
"""TK special-registration parser for the official 21,657-byte layout."""

from typing import Any

from src.jvlink.constants import ENCODING_JVDATA
from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class TKParser:
    """Parse one TK race header and its complete 300-slot horse array."""

    RECORD_TYPE = "TK"
    RECORD_LENGTH = 21657

    _HORSE_START = 655
    _HORSE_LENGTH = 70
    _HORSE_COUNT = 300
    _HORSE_FIELDS = (
        ("RenbanNum", 0, 3),
        ("KettoNum", 3, 10),
        ("Bamei", 13, 36),
        ("UmaKigoCD", 49, 2),
        ("SexCD", 51, 1),
        ("TozaiCD", 52, 1),
        ("ChokyosiCode", 53, 5),
        ("ChokyosiRyakusyo", 58, 8),
        ("Futan", 66, 3),
        ("Koryu", 69, 1),
    )
    _RACE_KEY = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Strictly decode one byte-sliced CP932 field and trim padding."""
        return data.decode(ENCODING_JVDATA).strip()

    @staticmethod
    def _require_ascii_digits(name: str, value: str, length: int) -> None:
        if len(value) != length or not value.isascii() or not value.isdigit():
            raise ValueError(f"{name} must be exactly {length} ASCII digits")

    def _parse_horses(self, data: bytes, header: dict[str, Any]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for slot_number in range(1, self._HORSE_COUNT + 1):
            start = self._HORSE_START + self._HORSE_LENGTH * (slot_number - 1)
            block = data[start : start + self._HORSE_LENGTH]
            if block == b" " * self._HORSE_LENGTH:
                continue

            horse = {
                name: self.decode_field(block[relative : relative + size])
                for name, relative, size in self._HORSE_FIELDS
            }
            expected_number = f"{slot_number:03d}"
            if horse["RenbanNum"] != expected_number:
                raise ValueError(
                    f"registered-horse slot {slot_number} has sequence "
                    f"{horse['RenbanNum']!r}, expected {expected_number!r}"
                )
            rows.append(
                {
                    "MakeDate": str(header["MakeDate"]),
                    **{key: str(header[key]) for key in self._RACE_KEY},
                    **horse,
                }
            )
        return rows

    def parse(self, data: bytes) -> dict[str, Any] | None:
        """Return one header with private normalized registered-horse rows."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "TK record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("TK record type mismatch")
                return None
            if data[21655:21657] != b"\r\n":
                self.logger.warning("TK record delimiter mismatch: expected CR/LF")
                return None

            result: dict[str, Any] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "Year": self.decode_field(data[11:15]),
                "MonthDay": self.decode_field(data[15:19]),
                "JyoCD": self.decode_field(data[19:21]),
                "Kaiji": self.decode_field(data[21:23]),
                "Nichiji": self.decode_field(data[23:25]),
                "RaceNum": self.decode_field(data[25:27]),
                "YoubiCD": self.decode_field(data[27:28]),
                "TokuNum": self.decode_field(data[28:32]),
                "Hondai": self.decode_field(data[32:92]),
                "Fukudai": self.decode_field(data[92:152]),
                "Kakko": self.decode_field(data[152:212]),
                "HondaiEng": self.decode_field(data[212:332]),
                "FukudaiEng": self.decode_field(data[332:452]),
                "KakkoEng": self.decode_field(data[452:572]),
                "RaceRyakusyo10": self.decode_field(data[572:592]),
                "RaceRyakusyo6": self.decode_field(data[592:604]),
                "RaceRyakusyo3": self.decode_field(data[604:610]),
                "RaceMeiKubun": self.decode_field(data[610:611]),
                "JyusyoKaiji": self.decode_field(data[611:614]),
                "GradeCD": self.decode_field(data[614:615]),
                "SyubetuCD": self.decode_field(data[615:617]),
                "KigoCD": self.decode_field(data[617:620]),
                "JyuryoCD": self.decode_field(data[620:621]),
                "JyokenCD2": self.decode_field(data[621:624]),
                "JyokenCD3": self.decode_field(data[624:627]),
                "JyokenCD4": self.decode_field(data[627:630]),
                "JyokenCD5": self.decode_field(data[630:633]),
                "JyokenCDYoung": self.decode_field(data[633:636]),
                "Kyori": self.decode_field(data[636:640]),
                "TrackCD": self.decode_field(data[640:642]),
                "CourseKubun": self.decode_field(data[642:644]),
                "HandeHappyoDate": self.decode_field(data[644:652]),
                "TorokuTosu": self.decode_field(data[652:655]),
            }
            if result["DataKubun"] not in {"0", "1", "2"}:
                raise ValueError("DataKubun must be 0, 1, or 2")
            for name, length in (
                ("MakeDate", 8),
                ("Year", 4),
                ("MonthDay", 4),
                ("JyoCD", 2),
                ("Kaiji", 2),
                ("Nichiji", 2),
                ("RaceNum", 2),
                ("TorokuTosu", 3),
            ):
                self._require_ascii_digits(name, str(result[name]), length)

            rows = self._parse_horses(data, result)
            expected_count = int(str(result["TorokuTosu"]))
            if expected_count > self._HORSE_COUNT or len(rows) != expected_count:
                raise ValueError(
                    "TorokuTosu does not match populated registered-horse slots: "
                    f"expected={expected_count}, actual={len(rows)}"
                )
            if [int(row["RenbanNum"]) for row in rows] != list(range(1, expected_count + 1)):
                raise ValueError("registered-horse sequence must be contiguous from 001")
            result["_tk_registered_horse_rows"] = rows
            return result
        except (UnicodeDecodeError, ValueError, TypeError) as error:
            self.logger.error(f"TK record parse failed: {error}")
            return None
