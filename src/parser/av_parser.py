"""Parser for the official AV scratched/excluded-horse record."""

from collections.abc import Mapping
from datetime import date
from typing import Any, List

from src.parser.base import BaseParser, FieldDef, validate_fixed_record
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001


class AVParser(BaseParser):
    """Parser for official 78-byte AV scratched/excluded horse records."""

    record_type = "AV"
    RECORD_TYPE = "AV"
    RECORD_LENGTH = 78
    KEY_COLUMNS = (
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
        "Umaban",
    )
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    REASON_CODES = frozenset({"", "000", "001", "002", "003"})

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
            raise ValueError(f"AV {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"AV {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"AV {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"AV {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        """Validate the complete official seven-part identity before coercion."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("AV Year and MonthDay must form a real date") from error

        if record.get("JyoCD") not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("AV JyoCD is not in official code table 2001")
        for field_name in ("Kaiji", "Nichiji", "RaceNum"):
            cls._require_fixed_integer(field_name, record.get(field_name), 2)

        umaban = cls._require_fixed_integer("Umaban", record.get("Umaban"), 2)
        if not 1 <= umaban <= 18:
            raise ValueError("AV Umaban must be between 01 and 18")

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one live AV row; a date-proven historical erase is opaque."""

        cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status == "0":
            return

        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        happyo_time = record.get("HappyoTime")
        if (
            not isinstance(happyo_time, str)
            or len(happyo_time) != 8
            or not happyo_time.isascii()
            or not happyo_time.isdigit()
        ):
            raise ValueError("AV HappyoTime must be exactly 8 ASCII digits")
        if happyo_time != "00000000":
            try:
                date(year, int(happyo_time[:2]), int(happyo_time[2:4]))
            except ValueError as error:
                raise ValueError("AV HappyoTime must contain a real MMDD date") from error
            if int(happyo_time[4:6]) > 23 or int(happyo_time[6:]) > 59:
                raise ValueError("AV HappyoTime must contain a real hhmm time")

        bamei = record.get("Bamei")
        if bamei not in (None, ""):
            if not isinstance(bamei, str):
                raise ValueError("AV Bamei must be provider text")
            try:
                encoded = bamei.encode("cp932", errors="strict")
            except UnicodeEncodeError as error:
                raise ValueError("AV Bamei is not CP932 encodable") from error
            if len(encoded) > 36:
                raise ValueError("AV Bamei exceeds its official 36-byte span")

        if record.get("JiyuKubun") not in cls.REASON_CODES:
            raise ValueError("AV JiyuKubun is not an official reason code")

    @staticmethod
    def decode_field(data: bytes) -> str:
        return data.decode("cp932", errors="strict").strip()

    def parse(self, record: bytes) -> dict[str, Any]:
        """Parse AV by byte offsets because Bamei is a multibyte cp932 field."""
        if not record:
            raise ValueError("Empty record")
        validate_fixed_record(record, self.record_type, self.RECORD_LENGTH)
        if self.decode_field(record[0:2]) != self.record_type:
            raise ValueError(
                f"Record type mismatch: expected {self.record_type}, "
                f"got {self.decode_field(record[0:2])}"
            )
        parsed = {
            field.name: self.decode_field(record[field.start : field.start + field.length])
            for field in self._fields
        }
        self.validate_current_fields(parsed)
        return parsed

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions from JRA-VAN JV-Data490."""
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, description="データ作成年月日"),
            FieldDef("Year", 11, 4, description="開催年"),
            FieldDef("MonthDay", 15, 4, description="開催月日"),
            FieldDef("JyoCD", 19, 2, description="競馬場コード"),
            FieldDef("Kaiji", 21, 2, description="開催回"),
            FieldDef("Nichiji", 23, 2, description="開催日目"),
            FieldDef("RaceNum", 25, 2, description="レース番号"),
            FieldDef("HappyoTime", 27, 8, description="発表月日時分"),
            FieldDef("Umaban", 35, 2, description="馬番"),
            FieldDef("Bamei", 37, 36, description="馬名"),
            FieldDef("JiyuKubun", 73, 3, description="事由区分"),
            FieldDef("RecordDelimiter", 76, 2, description="レコード区切"),
        ]
