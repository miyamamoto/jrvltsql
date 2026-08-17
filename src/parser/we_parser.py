"""Parser for the official 42-byte WE weather/track announcement record.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from collections.abc import Mapping
from datetime import date
from typing import Any

from src.parser.base import BaseParser, FieldDef
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001


class WEParser(BaseParser):
    """Parser for WE record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "WE"
    RECORD_LENGTH = 42
    KEY_COLUMNS = (
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "HappyoTime",
        "HenkoID",
    )
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    HENKO_ID_VALUES = frozenset({"1", "2", "3"})
    WEATHER_CODES = frozenset("0123456")
    TRACK_CONDITION_CODES = frozenset("01234")
    BODY_FIELDS = (
        "TenkoState",
        "SibaBabaState",
        "DirtBabaState",
        "TenkoState2",
        "SibaBabaState2",
        "DirtBabaState2",
    )

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
            raise ValueError(f"WE {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"WE {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"WE {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"WE {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        """Validate the complete seven-part identity before coercion/storage."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("WE Year and MonthDay must form a real date") from error

        jyo_cd = record.get("JyoCD")
        if jyo_cd not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("WE JyoCD is not in official code table 2001")
        cls._require_fixed_integer("Kaiji", record.get("Kaiji"), 2)
        cls._require_fixed_integer("Nichiji", record.get("Nichiji"), 2)

        happyo_time = record.get("HappyoTime")
        if (
            not isinstance(happyo_time, str)
            or len(happyo_time) != 8
            or not happyo_time.isascii()
            or not happyo_time.isdigit()
        ):
            raise ValueError("WE HappyoTime must be exactly 8 ASCII digits")
        if happyo_time != "00000000":
            try:
                date(year, int(happyo_time[:2]), int(happyo_time[2:4]))
            except ValueError as error:
                raise ValueError("WE HappyoTime must contain a real MMDD date") from error
            hour = int(happyo_time[4:6])
            minute = int(happyo_time[6:])
            if hour > 23 or minute > 59:
                raise ValueError("WE HappyoTime must contain a real hhmm time")

        if record.get("HenkoID") not in cls.HENKO_ID_VALUES:
            raise ValueError("WE HenkoID must be one of 1, 2, or 3")

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one live row; historical erase keeps only key semantics."""

        cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status == "0":
            return

        for field_name in ("TenkoState", "TenkoState2"):
            if record.get(field_name) not in cls.WEATHER_CODES:
                raise ValueError(f"WE {field_name} is not an official weather code")
        for field_name in (
            "SibaBabaState",
            "DirtBabaState",
            "SibaBabaState2",
            "DirtBabaState2",
        ):
            if record.get(field_name) not in cls.TRACK_CONDITION_CODES:
                raise ValueError(f"WE {field_name} is not an official track code")

        if record["HenkoID"] == "2" and any(
            record.get(field_name) != "0"
            for field_name in (
                "SibaBabaState",
                "DirtBabaState",
                "SibaBabaState2",
                "DirtBabaState2",
            )
        ):
            raise ValueError("WE HenkoID 2 requires initial-value track fields")
        if record["HenkoID"] == "3" and any(
            record.get(field_name) != "0" for field_name in ("TenkoState", "TenkoState2")
        ):
            raise ValueError("WE HenkoID 3 requires initial-value weather fields")

    def parse(self, record: bytes) -> dict[str, Any]:
        """Parse and validate one official current or date-proven legacy row."""

        parsed = super().parse(record)
        self.validate_current_fields(parsed)
        return parsed

    def _define_fields(self) -> list[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("Year", 11, 4, convert_type="SMALLINT", description="開催年"),
            FieldDef("MonthDay", 15, 4, convert_type="MONTH_DAY", description="開催月日"),
            FieldDef("JyoCD", 19, 2, description="競馬場コード"),
            FieldDef("Kaiji", 21, 2, convert_type="SMALLINT", description="開催回[第N回]"),
            FieldDef("Nichiji", 23, 2, convert_type="SMALLINT", description="開催日目[N日目]"),
            FieldDef("HappyoTime", 25, 8, description="発表月日時分"),
            FieldDef("HenkoID", 33, 1, description="変更識別"),
            FieldDef("TenkoState", 34, 1, description="天候状態"),
            FieldDef("SibaBabaState", 35, 1, description="馬場状態・芝"),
            FieldDef("DirtBabaState", 36, 1, description="馬場状態・ダート"),
            FieldDef("TenkoState2", 37, 1, description="天候状態"),
            FieldDef("SibaBabaState2", 38, 1, description="馬場状態・芝"),
            FieldDef("DirtBabaState2", 39, 1, description="馬場状態・ダート"),
            FieldDef("RecordDelimiter", 40, 2, description="レコード区切"),
        ]
