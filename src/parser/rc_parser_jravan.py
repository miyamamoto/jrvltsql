"""Parser for RC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class RCParserJRAVAN(BaseParser):
    """Parser for RC record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "RC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("レコード識別区分", 11, 1, description="レコード識別区分"),
            FieldDef("Year", 12, 4, convert_type="SMALLINT", description="開催年"),
            FieldDef("MonthDay", 16, 4, convert_type="MONTH_DAY", description="開催月日"),
            FieldDef("JyoCD", 20, 2, description="競馬場コード"),
            FieldDef("Kaiji", 22, 2, convert_type="SMALLINT", description="開催回[第N回]"),
            FieldDef("Nichiji", 24, 2, convert_type="SMALLINT", description="開催日目[N日目]"),
            FieldDef("RaceNum", 26, 2, convert_type="SMALLINT", description="レース番号"),
            FieldDef("TokuNum", 28, 4, description="特別競走番号"),
            FieldDef("Hondai", 32, 60, description="競走名本題"),
            FieldDef("グレードコード", 92, 1, description="グレードコード"),
            FieldDef("競走種別コード", 93, 2, description="競走種別コード"),
            FieldDef("Kyori", 95, 4, convert_type="SMALLINT", description="距離"),
            FieldDef("TrackCD", 99, 2, description="トラックコード"),
            FieldDef("レコード区分", 101, 1, description="レコード区分"),
            FieldDef("レコードタイム", 102, 4, description="レコードタイム"),
            FieldDef("TenkoCD", 106, 1, description="天候コード"),
            FieldDef("SibaBabaCD", 107, 1, description="芝馬場状態コード"),
            FieldDef("DirtBabaCD", 108, 1, description="ダート馬場状態コード"),
            FieldDef("<レコード保持馬情報>", 109, 130, description="<レコード保持馬情報>"),
            FieldDef("RecordDelimiter", 499, 2, description="レコード区切"),
        ]
