"""Parser for WE record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class WEParserJRAVAN(BaseParser):
    """Parser for WE record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "WE"

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
            FieldDef("発表月日時分", 25, 8, description="発表月日時分"),
            FieldDef("変更識別", 33, 1, description="変更識別"),
            FieldDef("天候状態", 34, 1, description="天候状態"),
            FieldDef("馬場状態・芝", 35, 1, description="馬場状態・芝"),
            FieldDef("馬場状態・ダート", 36, 1, description="馬場状態・ダート"),
            FieldDef("天候状態", 37, 1, description="天候状態"),
            FieldDef("馬場状態・芝", 38, 1, description="馬場状態・芝"),
            FieldDef("馬場状態・ダート", 39, 1, description="馬場状態・ダート"),
            FieldDef("RecordDelimiter", 40, 2, description="レコード区切"),
        ]
