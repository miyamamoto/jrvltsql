"""Parser for official JV-Data format 28 (DM time mining prediction)."""

from typing import Any

from src.jvlink.constants import ENCODING_JVDATA
from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class DMParser:
    """Expand one official 303-byte DM record into populated horse rows."""

    RECORD_TYPE = "DM"
    RECORD_LENGTH = 303
    record_type = RECORD_TYPE

    _HORSE_START = 31
    _HORSE_LENGTH = 15
    _HORSE_COUNT = 18
    _DATA_KUBUN_VALUES = {"0", "1", "2", "3", "7"}

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Decode one byte-sliced CP932 field strictly and trim padding."""
        return data.decode(ENCODING_JVDATA).strip()

    @staticmethod
    def _is_fixed_numeric(value: str, length: int) -> bool:
        return len(value) == length and all(char in "0123456789" for char in value)

    def parse(self, data: bytes) -> list[dict[str, Any]] | None:
        """Parse and expand an official DM record, or return ``None`` if invalid."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "DM record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("DM record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("DM record delimiter mismatch: expected CR/LF")
                return None

            base = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "Year": self.decode_field(data[11:15]),
                "MonthDay": self.decode_field(data[15:19]),
                "JyoCD": self.decode_field(data[19:21]),
                "Kaiji": self.decode_field(data[21:23]),
                "Nichiji": self.decode_field(data[23:25]),
                "RaceNum": self.decode_field(data[25:27]),
                "MakeHM": self.decode_field(data[27:31]),
            }
            if base["DataKubun"] not in self._DATA_KUBUN_VALUES:
                self.logger.warning(f"DM record has invalid DataKubun: {base['DataKubun']!r}")
                return None
            numeric_header_lengths = {
                "MakeDate": 8,
                "Year": 4,
                "MonthDay": 4,
                "Kaiji": 2,
                "Nichiji": 2,
                "RaceNum": 2,
                "MakeHM": 4,
            }
            for field_name, expected_length in numeric_header_lengths.items():
                value = base[field_name]
                if not self._is_fixed_numeric(value, expected_length):
                    self.logger.warning(f"DM record has invalid {field_name}: {value!r}")
                    return None

            wide_record = dict(base)
            populated_entries: list[dict[str, str]] = []
            seen_umaban: set[str] = set()
            for index in range(self._HORSE_COUNT):
                start = self._HORSE_START + index * self._HORSE_LENGTH
                entry = data[start : start + self._HORSE_LENGTH]
                number = index + 1
                horse = {
                    "Umaban": self.decode_field(entry[0:2]),
                    "DMTime": self.decode_field(entry[2:7]),
                    "DMGosaP": self.decode_field(entry[7:11]),
                    "DMGosaM": self.decode_field(entry[11:15]),
                }
                for field_name, value in horse.items():
                    wide_record[f"{field_name}{number}"] = value

                umaban = horse["Umaban"]
                if not umaban:
                    if any(value for field_name, value in horse.items() if field_name != "Umaban"):
                        self.logger.warning(f"DM empty horse slot {number} contains payload")
                        return None
                    continue
                if (
                    not self._is_fixed_numeric(umaban, 2)
                    or not 1 <= int(umaban) <= self._HORSE_COUNT
                ):
                    self.logger.warning(f"DM record has invalid Umaban: {umaban!r}")
                    return None
                if umaban in seen_umaban:
                    self.logger.warning(f"DM record has duplicate Umaban: {umaban}")
                    return None
                seen_umaban.add(umaban)

                for field_name, expected_length in (
                    ("DMTime", 5),
                    ("DMGosaP", 4),
                    ("DMGosaM", 4),
                ):
                    value = horse[field_name]
                    if not self._is_fixed_numeric(value, expected_length):
                        self.logger.warning(f"DM record has invalid {field_name}: {value!r}")
                        return None
                populated_entries.append(horse)

            if base["DataKubun"] == "0":
                if populated_entries:
                    self.logger.warning("DM delete record contains horse payload")
                    return None
                return [base]

            if populated_entries:
                snapshot_rows = [{**base, **horse} for horse in populated_entries]
                return [
                    {
                        **horse_row,
                        "_wide_record": wide_record,
                        "_dm_snapshot_rows": snapshot_rows,
                        "_dm_snapshot_index": index,
                    }
                    for index, horse_row in enumerate(snapshot_rows)
                ]

            self.logger.warning("DM record has no populated prediction entries")
            return None
        except Exception as exc:
            self.logger.error(f"DM record parse failed: {exc}")
            return None
