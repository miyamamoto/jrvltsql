"""Parser for JC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class JCParserJRAVAN(BaseParser):
    """Parser for JC record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "JC"

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
            FieldDef("馬番", 35, 2, description="馬番"),
            FieldDef("Bamei", 37, 36, description="馬名"),
            FieldDef("負担重量", 73, 3, description="負担重量"),
            FieldDef("KisyuCode", 76, 5, description="騎手コード"),
            FieldDef("騎手名", 81, 34, description="騎手名"),
            FieldDef("騎手見習コード", 115, 1, description="騎手見習コード"),
            FieldDef("負担重量", 116, 3, description="負担重量"),
            FieldDef("KisyuCode", 119, 5, description="騎手コード"),
            FieldDef("騎手名", 124, 34, description="騎手名"),
            FieldDef("騎手見習コード", 158, 1, description="騎手見習コード"),
            FieldDef("RecordDelimiter", 159, 2, description="レコード区切"),
        ]
