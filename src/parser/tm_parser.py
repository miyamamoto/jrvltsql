"""Parser for official JV-Data format 29 (TM match-type mining prediction)."""

from typing import Any

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger


class TMParser:
    """Expand one official 141-byte TM record into populated horse rows."""

    RECORD_TYPE = "TM"
    RECORD_LENGTH = 141
    record_type = RECORD_TYPE

    _HORSE_START = 31
    _HORSE_LENGTH = 6
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
        """Parse and expand an official TM record, or return ``None`` if invalid."""
        try:
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "TM record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("TM record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("TM record delimiter mismatch: expected CR/LF")
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
                self.logger.warning(f"TM record has invalid DataKubun: {base['DataKubun']!r}")
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
                    self.logger.warning(f"TM record has invalid {field_name}: {value!r}")
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
                    "TMScore": self.decode_field(entry[2:6]),
                }
                for field_name, value in horse.items():
                    wide_record[f"{field_name}{number}"] = value

                umaban = horse["Umaban"]
                score = horse["TMScore"]
                if not umaban:
                    if score:
                        self.logger.warning(f"TM empty horse slot {number} contains payload")
                        return None
                    continue
                if (
                    not self._is_fixed_numeric(umaban, 2)
                    or not 1 <= int(umaban) <= self._HORSE_COUNT
                ):
                    self.logger.warning(f"TM record has invalid Umaban: {umaban!r}")
                    return None
                if umaban in seen_umaban:
                    self.logger.warning(f"TM record has duplicate Umaban: {umaban}")
                    return None
                seen_umaban.add(umaban)
                if not self._is_fixed_numeric(score, 4) or int(score) > 1000:
                    self.logger.warning(f"TM record has invalid TMScore: {score!r}")
                    return None
                populated_entries.append(horse)

            if base["DataKubun"] == "0":
                if populated_entries:
                    self.logger.warning("TM delete record contains horse payload")
                    return None
                return [base]

            if populated_entries:
                snapshot_rows = [{**base, **horse} for horse in populated_entries]
                return [
                    {
                        **horse_row,
                        "_wide_record": wide_record,
                        "_tm_snapshot_rows": snapshot_rows,
                        "_tm_snapshot_index": index,
                    }
                    for index, horse_row in enumerate(snapshot_rows)
                ]

            self.logger.warning("TM record has no populated prediction entries")
            return None
        except Exception as exc:
            self.logger.error(f"TM record parse failed: {exc}")
            return None
