"""Parser for the official TC start-time-change record."""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, List

from src.parser.base import BaseParser, FieldDef
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001


class TCParser(BaseParser):
    """Parser for TC record with accurate field positions.

    Total record length: 45 bytes
    Fields: 15
    """

    record_type = "TC"
    RECORD_LENGTH = 45
    KEY_COLUMNS = (
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
    )
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001

    @staticmethod
    def _require_date(field_name: str, value: object) -> date:
        if isinstance(value, datetime):
            raise ValueError(f"TC {field_name} must not contain a time component")
        if isinstance(value, date):
            return value
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"TC {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"TC {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"TC {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"TC {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> int:
        """Validate the complete official six-part race identity before coercion."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        if year < 1000:
            raise ValueError("TC Year must remain a four-digit Gregorian year")
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("TC Year and MonthDay must form a real date") from error
        if record.get("JyoCD") not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("TC JyoCD is not in official code table 2001")
        for field_name in ("Kaiji", "Nichiji", "RaceNum"):
            cls._require_fixed_integer(field_name, record.get(field_name), 2)
        return year

    @staticmethod
    def _require_mdhm(value: object, year: int) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError("TC HappyoTime must be exactly 8 ASCII digits")
        if value == "00000000":
            return
        try:
            date(year, int(value[:2]), int(value[2:4]))
        except ValueError as error:
            raise ValueError("TC HappyoTime must contain a real MMDD date") from error
        if int(value[4:6]) > 23 or int(value[6:]) > 59:
            raise ValueError("TC HappyoTime must contain a real hhmm time")

    @staticmethod
    def _require_hhmm_part(field_name: str, value: object, maximum: int) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 2
            or not value.isascii()
            or not value.isdigit()
            or int(value) > maximum
        ):
            raise ValueError(f"TC {field_name} is not a valid two-digit time component")

    @classmethod
    def validate_current_fields(cls, record: Mapping[str, object]) -> None:
        """Validate one current live TC row; the official status domain is only 1."""

        year = cls.validate_key_fields(record)
        cls._require_mdhm(record.get("HappyoTime"), year)
        for field_name in ("AtoJi", "MaeJi"):
            cls._require_hhmm_part(field_name, record.get(field_name), 23)
        for field_name in ("AtoFun", "MaeFun"):
            cls._require_hhmm_part(field_name, record.get(field_name), 59)

    def parse(self, record: bytes) -> dict[str, Any]:
        """Parse and strictly validate one current 45-byte TC record."""

        parsed = super().parse(record)
        # BaseParser intentionally converts numeric fields for the public
        # parsed shape. Validate the original fixed-width text as well so a
        # lossy converter can never turn ``20A6`` into a plausible key.
        raw_fields = {
            field.name: record[field.start : field.start + field.length]
            .decode("cp932", errors="strict")
            .strip()
            for field in self._fields
            if field.name != "RecordDelimiter"
        }
        self.validate_current_fields(raw_fields)
        self.validate_current_fields(parsed)
        return parsed

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions calculated from schema.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2),
            FieldDef("DataKubun", 2, 1),
            FieldDef("MakeDate", 3, 8, convert_type="DATE"),
            FieldDef("Year", 11, 4, convert_type="SMALLINT"),
            FieldDef("MonthDay", 15, 4, convert_type="MONTH_DAY"),
            FieldDef("JyoCD", 19, 2),
            FieldDef("Kaiji", 21, 2, convert_type="SMALLINT"),
            FieldDef("Nichiji", 23, 2, convert_type="SMALLINT"),
            FieldDef("RaceNum", 25, 2, convert_type="SMALLINT"),
            FieldDef("HappyoTime", 27, 8, description="発表月日時分(MMDDhhmm)"),
            FieldDef("AtoJi", 35, 2),
            FieldDef("AtoFun", 37, 2),
            FieldDef("MaeJi", 39, 2),
            FieldDef("MaeFun", 41, 2),
            FieldDef("RecordDelimiter", 43, 2),
        ]
