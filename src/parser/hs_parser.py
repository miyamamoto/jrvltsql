"""Parser for the official current 200-byte HS horse-sale record."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from src.parser import status_domain
from src.parser.base import FieldDef
from src.utils.logger import get_logger


class HSParser:
    """Parse the current JV-Data 4.9.0.1 HS physical layout only."""

    RECORD_TYPE = "HS"
    record_type = RECORD_TYPE
    RECORD_LENGTH = 200
    CURRENT_LAYOUT_VERSION = 200
    KEY_COLUMNS = ("KettoNum", "SaleCode", "FromDate")
    FIELD_LAYOUT = (
        ("RecordSpec", 0, 2),
        ("DataKubun", 2, 1),
        ("MakeDate", 3, 8),
        ("KettoNum", 11, 10),
        ("HansyokuFNum", 21, 10),
        ("HansyokuMNum", 31, 10),
        ("BirthYear", 41, 4),
        ("SaleCode", 45, 6),
        ("SaleHostName", 51, 40),
        ("SaleName", 91, 80),
        ("FromDate", 171, 8),
        ("ToDate", 179, 8),
        ("Barei", 187, 1),
        ("Price", 188, 10),
        ("RecordDelimiter", 198, 2),
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self._fields = [FieldDef(name, start, width) for name, start, width in self.FIELD_LAYOUT]
        self._field_map = {field.name: field for field in self._fields}

    @staticmethod
    def decode_field(data: bytes) -> str:
        return data.decode("cp932", errors="strict").strip()

    @staticmethod
    def _require_ascii_digits(
        field_name: str,
        value: object,
        *,
        widths: tuple[int, ...],
        allow_int: bool = False,
    ) -> str:
        if allow_int and isinstance(value, int) and not isinstance(value, bool):
            if 0 <= value < 10 ** max(widths):
                return str(value)
        if isinstance(value, str) and len(value) in widths and value.isascii() and value.isdigit():
            return value
        expected = " or ".join(str(width) for width in widths)
        raise ValueError(f"HS {field_name} must be {expected} ASCII digits")

    @classmethod
    def _require_date_or_zero(cls, field_name: str, value: object) -> None:
        digits = cls._require_ascii_digits(field_name, value, widths=(8,))
        if digits == "00000000":
            return
        try:
            date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        except ValueError as error:
            raise ValueError(f"HS {field_name} must be a real YYYYMMDD date or 00000000") from error

    @staticmethod
    def _require_optional_cp932(field_name: str, value: object, width: int) -> None:
        if value in (None, ""):
            return
        if not isinstance(value, str):
            raise ValueError(f"HS {field_name} must be provider text")
        try:
            encoded = value.encode("cp932", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError(f"HS {field_name} is not CP932 encodable") from error
        if len(encoded) > width:
            raise ValueError(f"HS {field_name} exceeds its official {width}-byte span")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        cls._require_date_or_zero("MakeDate", record.get("MakeDate"))
        cls._require_ascii_digits("KettoNum", record.get("KettoNum"), widths=(10,))
        cls._require_ascii_digits("SaleCode", record.get("SaleCode"), widths=(6,))
        cls._require_date_or_zero("FromDate", record.get("FromDate"))

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate current semantics before any importer coercion or mutation."""

        cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status == "0":
            # Project exact-erase policy: the provider does not need to supply
            # decodable non-key bytes for a deletion command.
            return

        for field_name in ("HansyokuFNum", "HansyokuMNum"):
            cls._require_ascii_digits(field_name, record.get(field_name), widths=(8, 10))
        cls._require_ascii_digits("BirthYear", record.get("BirthYear"), widths=(4,), allow_int=True)
        cls._require_optional_cp932("SaleHostName", record.get("SaleHostName"), 40)
        cls._require_optional_cp932("SaleName", record.get("SaleName"), 80)
        cls._require_date_or_zero("ToDate", record.get("ToDate"))
        cls._require_ascii_digits("Barei", record.get("Barei"), widths=(1,), allow_int=True)
        cls._require_ascii_digits(
            "Price",
            record.get("Price"),
            widths=tuple(range(1, 11)),
            allow_int=True,
        )

    @staticmethod
    def _validate_envelope(data: bytes) -> tuple[str, str]:
        if len(data) != HSParser.RECORD_LENGTH:
            raise ValueError(
                f"HS record length mismatch: expected={(HSParser.RECORD_LENGTH,)}, "
                f"actual={len(data)}"
            )
        if data[:2] != b"HS":
            raise ValueError(f"Record type mismatch: expected HS, got {data[:2]!r}")
        if data[-2:] != b"\r\n":
            raise ValueError("HS record delimiter must be CRLF")
        data_kubun = data[2:3].decode("ascii", errors="strict")
        make_date = data[3:11].decode("ascii", errors="strict")
        HSParser._require_date_or_zero("MakeDate", make_date)
        status_domain.validate_data_kubun("HS", data_kubun, make_date=make_date)
        return data_kubun, make_date

    def parse(self, data: bytes) -> dict[str, object] | None:
        """Parse one current HS record, returning ``None`` on invalid input."""

        try:
            data_kubun, make_date = self._validate_envelope(data)
            if data_kubun == "0":
                # Decode only the three official identity components. Every
                # non-key physical byte remains opaque by repository policy.
                result: dict[str, object] = {
                    "RecordSpec": "HS",
                    "DataKubun": data_kubun,
                    "MakeDate": make_date,
                    "KettoNum": self.decode_field(data[11:21]),
                    "HansyokuFNum": "",
                    "HansyokuMNum": "",
                    "BirthYear": "",
                    "SaleCode": self.decode_field(data[45:51]),
                    "SaleHostName": "",
                    "SaleName": "",
                    "FromDate": self.decode_field(data[171:179]),
                    "ToDate": "",
                    "Barei": "",
                    "Price": "",
                    "RecordDelimiter": "",
                    "CurrentLayoutVersion": self.CURRENT_LAYOUT_VERSION,
                }
            else:
                # Slice before decoding so multibyte text cannot shift offsets.
                result = {
                    field.name: self.decode_field(data[field.start : field.start + field.length])
                    for field in self._fields
                }
                result["CurrentLayoutVersion"] = self.CURRENT_LAYOUT_VERSION
            self.validate_current_fields(result, data_kubun=data_kubun)
            return result
        except Exception as error:
            self.logger.error(f"HSレコードパース中にエラー: {error}")
            return None

    def get_field_names(self) -> list[str]:
        return [field.name for field in self._fields]

    def get_field_def(self, field_name: str) -> FieldDef | None:
        return self._field_map.get(field_name)
