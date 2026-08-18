"""Parser for the official CC course-change record."""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, List

from src.parser.base import BaseParser, FieldDef
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001, OFFICIAL_TRACK_CODES_2009


class CCParser(BaseParser):
    """Parser for CC record with accurate field positions.

    Total record length: 50 bytes
    Fields: 16
    """

    record_type = "CC"
    RECORD_LENGTH = 50
    KEY_COLUMNS = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    OFFICIAL_TRACK_CODES = OFFICIAL_TRACK_CODES_2009
    REASON_CODES = frozenset({"0", "1", "2", "3", "4"})

    @staticmethod
    def _require_date(field_name: str, value: object) -> date:
        if isinstance(value, datetime):
            raise ValueError(f"CC {field_name} must not contain a time component")
        if isinstance(value, date):
            return value
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"CC {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"CC {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"CC {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"CC {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> int:
        """Validate the complete official six-part race identity."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        if year < 1000:
            raise ValueError("CC Year must remain a four-digit Gregorian year")
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("CC Year and MonthDay must form a real date") from error
        if record.get("JyoCD") not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("CC JyoCD is not in official code table 2001")
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
            raise ValueError("CC HappyoTime must be exactly 8 ASCII digits")
        if value == "00000000":
            return
        try:
            date(year, int(value[:2]), int(value[2:4]))
        except ValueError as error:
            raise ValueError("CC HappyoTime must contain a real MMDD date") from error
        if int(value[4:6]) > 23 or int(value[6:]) > 59:
            raise ValueError("CC HappyoTime must contain a real hhmm time")

    @classmethod
    def _require_distance(cls, field_name: str, value: object) -> None:
        cls._require_fixed_integer(field_name, value, 4)

    @classmethod
    def validate_current_fields(cls, record: Mapping[str, object]) -> None:
        """Validate one current live CC row; the official status domain is only 1."""

        year = cls.validate_key_fields(record)
        cls._require_mdhm(record.get("HappyoTime"), year)
        for field_name in ("AtoKyori", "MaeKyori"):
            cls._require_distance(field_name, record.get(field_name))
        for field_name in ("AtoTruckCD", "MaeTruckCD"):
            if record.get(field_name) not in cls.OFFICIAL_TRACK_CODES:
                raise ValueError(f"CC {field_name} is not in official code table 2009")
        if record.get("JiyuCD") not in cls.REASON_CODES:
            raise ValueError("CC JiyuCD must be an official value from 0 through 4")

    def parse(self, record: bytes) -> dict[str, Any]:
        """Parse and strictly validate one current 50-byte CC record."""

        parsed = super().parse(record)
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
            FieldDef("AtoKyori", 35, 4),
            FieldDef("AtoTruckCD", 39, 2),
            FieldDef("MaeKyori", 41, 4),
            FieldDef("MaeTruckCD", 45, 2),
            FieldDef("JiyuCD", 47, 1),
            FieldDef("RecordDelimiter", 48, 2),
        ]
