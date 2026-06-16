"""Parser for AV record - scratched/excluded horse realtime data."""

from typing import List

from src.parser.base import BaseParser, FieldDef


class AVParser(BaseParser):
    """Parser for official 78-byte AV scratched/excluded horse records."""

    record_type = "AV"
    RECORD_TYPE = "AV"
    RECORD_LENGTH = 78

    @staticmethod
    def decode_field(data: bytes) -> str:
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def parse(self, record: bytes) -> dict:
        """Parse AV by byte offsets because Bamei is a multibyte cp932 field."""
        if not record:
            raise ValueError("Empty record")
        if self.decode_field(record[0:2]) != self.record_type:
            raise ValueError(
                f"Record type mismatch: expected {self.record_type}, "
                f"got {self.decode_field(record[0:2])}"
            )
        return {
            field.name: self.decode_field(record[field.start:field.start + field.length])
            for field in self._fields
        }

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
