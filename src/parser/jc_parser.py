"""Parser for the official 161-byte JC jockey-change record."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from src.parser.base import BaseParser, FieldDef
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001


class JCParser(BaseParser):
    """Parser for JC record with accurate field positions.

    Total record length: 161 bytes
    Fields: 21
    """

    record_type = "JC"
    RECORD_LENGTH = 161
    KEY_COLUMNS = (
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
        "HappyoTime",
        "Umaban",
    )
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    MINARAI_CODES = frozenset({"0", "1", "2", "3", "4", "9"})
    TEXT_FIELD_WIDTHS = {
        "Bamei": 36,
        "AtoKisyuName": 34,
        "MaeKisyuName": 34,
    }

    @staticmethod
    def _require_date(field_name: str, value: object) -> date:
        if isinstance(value, date):
            return value
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"JC {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"JC {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"JC {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"JC {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        """Validate the complete official eight-part identity before coercion."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("JC Year and MonthDay must form a real date") from error

        if record.get("JyoCD") not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("JC JyoCD is not in official code table 2001")
        for field_name in ("Kaiji", "Nichiji", "RaceNum"):
            cls._require_fixed_integer(field_name, record.get(field_name), 2)

        happyo_time = record.get("HappyoTime")
        if (
            not isinstance(happyo_time, str)
            or len(happyo_time) != 8
            or not happyo_time.isascii()
            or not happyo_time.isdigit()
        ):
            raise ValueError("JC HappyoTime must be exactly 8 ASCII digits")
        if happyo_time != "00000000":
            try:
                date(year, int(happyo_time[:2]), int(happyo_time[2:4]))
            except ValueError as error:
                raise ValueError("JC HappyoTime must contain a real MMDD date") from error
            if int(happyo_time[4:6]) > 23 or int(happyo_time[6:]) > 59:
                raise ValueError("JC HappyoTime must contain a real hhmm time")

        umaban = cls._require_fixed_integer("Umaban", record.get("Umaban"), 2)
        if not 1 <= umaban <= 18:
            raise ValueError("JC Umaban must be between 01 and 18")

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one live row; a historical erase has an opaque body."""

        cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status == "0":
            return

        for field_name in ("AtoFutan", "MaeFutan"):
            value = record.get(field_name)
            if (
                not isinstance(value, str)
                or len(value) != 3
                or not value.isascii()
                or not value.isdigit()
            ):
                raise ValueError(f"JC {field_name} must be exactly 3 ASCII digits")
        for field_name in ("AtoKisyuCode", "MaeKisyuCode"):
            value = record.get(field_name)
            if (
                not isinstance(value, str)
                or len(value) != 5
                or not value.isascii()
                or not value.isdigit()
            ):
                raise ValueError(f"JC {field_name} must be exactly 5 ASCII digits")
        for field_name in ("AtoMinaraiCD", "MaeMinaraiCD"):
            if record.get(field_name) not in cls.MINARAI_CODES:
                raise ValueError(f"JC {field_name} is not an official apprentice code")
        for field_name, width in cls.TEXT_FIELD_WIDTHS.items():
            value = record.get(field_name)
            if value in (None, ""):
                continue
            if not isinstance(value, str):
                raise ValueError(f"JC {field_name} must be provider text")
            try:
                encoded = value.encode("cp932", errors="strict")
            except UnicodeEncodeError as error:
                raise ValueError(f"JC {field_name} is not CP932 encodable") from error
            if len(encoded) > width:
                raise ValueError(f"JC {field_name} exceeds its official {width}-byte span")

    def parse(self, record: bytes) -> dict[str, Any]:
        """Parse and validate one current or date-proven historical JC row."""

        parsed = super().parse(record)
        self.validate_current_fields(parsed)
        return parsed

    def _define_fields(self) -> list[FieldDef]:
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
            FieldDef("Umaban", 35, 2, convert_type="SMALLINT"),
            FieldDef("Bamei", 37, 36),
            FieldDef("AtoFutan", 73, 3),
            FieldDef("AtoKisyuCode", 76, 5),
            FieldDef("AtoKisyuName", 81, 34),
            FieldDef("AtoMinaraiCD", 115, 1),
            FieldDef("MaeFutan", 116, 3),
            FieldDef("MaeKisyuCode", 119, 5),
            FieldDef("MaeKisyuName", 124, 34),
            FieldDef("MaeMinaraiCD", 158, 1),
            FieldDef("RecordDelimiter", 159, 2),
        ]
