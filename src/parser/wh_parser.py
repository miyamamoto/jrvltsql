"""Parser for official JV-Data format 101 (WH horse weight)."""

from typing import Any

from src.jvlink.constants import ENCODING_JVDATA
from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class WHParser:
    """Expand one 847-byte WH record into one row per populated horse."""

    RECORD_TYPE = "WH"
    RECORD_LENGTH = 847
    record_type = RECORD_TYPE

    _HORSE_START = 35
    _HORSE_LENGTH = 45
    _HORSE_COUNT = 18

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Decode one byte-sliced CP932 field strictly and trim padding."""
        return data.decode(ENCODING_JVDATA).strip()

    def parse(self, data: bytes) -> list[dict[str, Any]] | None:
        """Parse and expand an official WH record, or return ``None`` if invalid."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "WH record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("WH record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("WH record delimiter mismatch: expected CR/LF")
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
                "HappyoTime": self.decode_field(data[27:35]),
            }
            if base["DataKubun"] not in {"0", "1"}:
                self.logger.warning(f"WH record has invalid DataKubun: {base['DataKubun']!r}")
                return None
            numeric_header_lengths = {
                "MakeDate": 8,
                "Year": 4,
                "MonthDay": 4,
                "Kaiji": 2,
                "Nichiji": 2,
                "RaceNum": 2,
                "HappyoTime": 8,
            }
            for field_name, expected_length in numeric_header_lengths.items():
                value = base[field_name]
                if len(value) != expected_length or any(char not in "0123456789" for char in value):
                    self.logger.warning(f"WH record has invalid {field_name}: {value!r}")
                    return None

            wide_record = dict(base)
            populated_entries: list[dict[str, str]] = []
            seen_umaban = set()
            for index in range(self._HORSE_COUNT):
                start = self._HORSE_START + index * self._HORSE_LENGTH
                entry = data[start : start + self._HORSE_LENGTH]
                number = index + 1
                horse = {
                    "Umaban": self.decode_field(entry[0:2]),
                    "Bamei": self.decode_field(entry[2:38]),
                    "BaTaijyu": self.decode_field(entry[38:41]),
                    "ZogenFugo": self.decode_field(entry[41:42]),
                    "ZogenSa": self.decode_field(entry[42:45]),
                }
                for field_name, value in horse.items():
                    wide_record[f"{field_name}{number}"] = value

                umaban = horse["Umaban"]
                if umaban in {"", "00"}:
                    if any(value for field_name, value in horse.items() if field_name != "Umaban"):
                        self.logger.warning(f"WH empty horse slot {number} contains payload")
                        return None
                    continue
                if (
                    len(umaban) != 2
                    or any(char not in "0123456789" for char in umaban)
                    or not 1 <= int(umaban) <= self._HORSE_COUNT
                ):
                    self.logger.warning(f"WH record has invalid Umaban: {umaban!r}")
                    return None
                if umaban in seen_umaban:
                    self.logger.warning(f"WH record has duplicate Umaban: {umaban}")
                    return None
                seen_umaban.add(umaban)

                for field_name in ("BaTaijyu", "ZogenSa"):
                    value = horse[field_name]
                    if value and (
                        len(value) != 3 or any(char not in "0123456789" for char in value)
                    ):
                        self.logger.warning(f"WH record has invalid {field_name}: {value!r}")
                        return None
                if horse["BaTaijyu"] == "001":
                    self.logger.warning("WH record uses reserved BaTaijyu value: 001")
                    return None
                if horse["ZogenFugo"] not in {"", "+", "-"}:
                    self.logger.warning(f"WH record has invalid ZogenFugo: {horse['ZogenFugo']!r}")
                    return None
                populated_entries.append(horse)

            if populated_entries:
                return [
                    {**base, **horse, "_wide_record": wide_record} for horse in populated_entries
                ]

            # DataKubun=0 existed before JV-Data 1.0.7 beta (2003-07-11).
            # Preserve its race identity so RealtimeUpdater can delete every
            # expanded horse row without inventing an Umaban.
            if base["DataKubun"] == "0":
                return [base]

            self.logger.warning("WH record has no populated horse-weight entries")
            return None
        except Exception as exc:
            self.logger.error(f"WH record parse failed: {exc}")
            return None
