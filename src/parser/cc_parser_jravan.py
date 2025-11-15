"""Parser for CC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class CCParserJRAVAN(BaseParser):
    """Parser for CC record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "CC"

    def _define_fields(self) -> List[FieldDef]:
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
            FieldDef("RaceNum", 25, 2, convert_type="SMALLINT", description="レース番号"),
            FieldDef("発表月日時分", 27, 8, description="発表月日時分"),
            FieldDef("変更後_距離", 35, 4, description="変更後 距離"),
            FieldDef("変更後_トラックコード", 39, 2, description="変更後 トラックコード"),
            FieldDef("変更前_距離", 41, 4, description="変更前 距離"),
            FieldDef("変更前_トラックコード", 45, 2, description="変更前 トラックコード"),
            FieldDef("事由区分", 47, 1, description="事由区分"),
            FieldDef("RecordDelimiter", 48, 2, description="レコード区切"),
        ]
