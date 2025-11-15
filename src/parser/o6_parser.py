"""Parser for O6 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Generated from jv_data_formats.json and JRA-VAN standard schema.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class O6Parser(BaseParser):
    """Parser for O6 record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "O6"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("MakeDate", 0, 2, convert_type="DATE", description="レコード種別ID"),
            FieldDef("Year", 2, 1, convert_type="SMALLINT", description="データ区分"),
            FieldDef("MonthDay", 3, 8, convert_type="MONTH_DAY", description="データ作成年月日"),
            FieldDef("JyoCD", 11, 4, description="開催年"),
            FieldDef("Kaiji", 15, 4, convert_type="SMALLINT", description="開催月日"),
            FieldDef("Nichiji", 19, 2, convert_type="SMALLINT", description="競馬場コード"),
            FieldDef("RaceNum", 21, 2, convert_type="SMALLINT", description="開催回[第N回]"),
            FieldDef("Kumi", 23, 2, description="開催日目[N日目]"),
            FieldDef("Odds", 25, 2, convert_type="ODDS", description="レース番号"),
            FieldDef("Ninki", 27, 8, convert_type="SMALLINT", description="発表月日時分"),
            FieldDef("TorokuTosu", 35, 2, convert_type="SMALLINT", description="登録頭数"),
            FieldDef("SyussoTosu", 37, 2, convert_type="SMALLINT", description="出走頭数"),
            FieldDef("HatsubaiFlag8", 39, 1, description="発売フラグ　3連単"),
            FieldDef("SanrentanOddsBlock", 40, 17, description="<3連単オッズ>"),
            FieldDef("SanrentanHyosuTotal", 83272, 11, description="3連単票数合計"),
            FieldDef("RecordDelimiter", 83283, 2, description="レコード区切"),
        ]
