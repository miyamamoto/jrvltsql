"""Parser for the official current 60-byte HC hill-training record."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from src.parser import status_domain
from src.parser.base import FieldDef
from src.utils.logger import get_logger


class HCParser:
    """Parse one current JV-Data HC record without lossy coercion."""

    RECORD_TYPE = "HC"
    record_type = RECORD_TYPE
    RECORD_LENGTH = 60
    KEY_COLUMNS = ("TresenKubun", "ChokyoDate", "ChokyoTime", "KettoNum")
    FIELD_LAYOUT = (
        ("RecordSpec", 0, 2),
        ("DataKubun", 2, 1),
        ("MakeDate", 3, 8),
        ("TresenKubun", 11, 1),
        ("ChokyoDate", 12, 8),
        ("ChokyoTime", 20, 4),
        ("KettoNum", 24, 10),
        ("HaronTime4", 34, 4),
        ("LapTime4", 38, 3),
        ("HaronTime3", 41, 4),
        ("LapTime3", 45, 3),
        ("HaronTime2", 48, 4),
        ("LapTime2", 52, 3),
        ("LapTime1", 55, 3),
        ("RecordDelimiter", 58, 2),
    )
    TIME_WIDTHS = {
        "HaronTime4": 4,
        "LapTime4": 3,
        "HaronTime3": 4,
        "LapTime3": 3,
        "HaronTime2": 4,
        "LapTime2": 3,
        "LapTime1": 3,
    }

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self._fields = [FieldDef(name, start, width) for name, start, width in self.FIELD_LAYOUT]
        self._field_map = {field.name: field for field in self._fields}

    @staticmethod
    def _decode_field(data: bytes) -> str:
        return data.decode("cp932", errors="strict").strip()

    @staticmethod
    def _require_ascii_digits(field_name: str, value: object, width: int) -> str:
        if isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return value
        raise ValueError(f"HC {field_name} must be exactly {width} ASCII digits")

    @classmethod
    def _require_date(cls, field_name: str, value: object) -> str:
        digits = cls._require_ascii_digits(field_name, value, 8)
        try:
            date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        except ValueError as error:
            raise ValueError(f"HC {field_name} must be a real YYYYMMDD date") from error
        return digits

    @classmethod
    def _require_hhmm(cls, field_name: str, value: object) -> str:
        digits = cls._require_ascii_digits(field_name, value, 4)
        if int(digits[:2]) > 23 or int(digits[2:]) > 59:
            raise ValueError(f"HC {field_name} must be a real HHMM time")
        return digits

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        cls._require_date("MakeDate", record.get("MakeDate"))
        tresen = cls._require_ascii_digits("TresenKubun", record.get("TresenKubun"), 1)
        if tresen not in {"0", "1"}:
            raise ValueError("HC TresenKubun must be 0 (Miho) or 1 (Ritto)")
        cls._require_date("ChokyoDate", record.get("ChokyoDate"))
        cls._require_hhmm("ChokyoTime", record.get("ChokyoTime"))
        cls._require_ascii_digits("KettoNum", record.get("KettoNum"), 10)

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one current row before coercion or database mutation."""

        cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status == "0":
            # Project exact-delete policy: HC identity is sufficient for a
            # deletion command; every non-key body byte remains uninterpreted.
            return
        for field_name, width in cls.TIME_WIDTHS.items():
            cls._require_ascii_digits(field_name, record.get(field_name), width)

    @classmethod
    def _validate_envelope(cls, data: bytes) -> tuple[str, str]:
        if len(data) != cls.RECORD_LENGTH:
            raise ValueError(
                f"HC record length mismatch: expected={(cls.RECORD_LENGTH,)}, "
                f"actual={len(data)}"
            )
        if data[:2] != b"HC":
            raise ValueError(f"Record type mismatch: expected HC, got {data[:2]!r}")
        if data[-2:] != b"\r\n":
            raise ValueError("HC record delimiter must be CRLF")
        data_kubun = data[2:3].decode("ascii", errors="strict")
        make_date = data[3:11].decode("ascii", errors="strict")
        cls._require_date("MakeDate", make_date)
        status_domain.validate_data_kubun("HC", data_kubun, make_date=make_date)
        return data_kubun, make_date

    def parse(self, data: bytes) -> dict[str, object] | None:
        """Return a strict current HC row, or ``None`` for malformed input."""

        try:
            data_kubun, make_date = self._validate_envelope(data)
            if data_kubun == "0":
                result: dict[str, object] = {
                    "RecordSpec": "HC",
                    "DataKubun": data_kubun,
                    "MakeDate": make_date,
                    "TresenKubun": self._decode_field(data[11:12]),
                    "ChokyoDate": self._decode_field(data[12:20]),
                    "ChokyoTime": self._decode_field(data[20:24]),
                    "KettoNum": self._decode_field(data[24:34]),
                    **dict.fromkeys(self.TIME_WIDTHS, ""),
                    "RecordDelimiter": None,
                }
            else:
                result = {
                    field.name: (
                        None
                        if field.name == "RecordDelimiter"
                        else self._decode_field(data[field.start : field.start + field.length])
                    )
                    for field in self._fields
                }
            self.validate_current_fields(result, data_kubun=data_kubun)
            return result
        except Exception as error:
            self.logger.error(f"HCレコードパース中にエラー: {error}")
            return None

    def get_field_names(self) -> list[str]:
        return [field.name for field in self._fields]

    def get_field_def(self, field_name: str) -> FieldDef | None:
        return self._field_map.get(field_name)
