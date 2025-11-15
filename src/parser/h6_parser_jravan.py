"""Parser for H6 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class H6ParserJRAVAN(BaseParser):
    """Parser for H6 record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "H6"

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
            FieldDef("TorokuTosu", 27, 2, convert_type="SMALLINT", description="登録頭数"),
            FieldDef("SyussoTosu", 29, 2, convert_type="SMALLINT", description="出走頭数"),
            FieldDef("発売フラグ　3連単", 31, 1, description="発売フラグ　3連単"),
            FieldDef("返還馬番情報(馬番01～18)", 32, 1, description="返還馬番情報(馬番01～18)"),
            FieldDef("<3連単票数>", 50, 21, description="<3連単票数>"),
            FieldDef("3連単票数合計", 102866, 11, description="3連単票数合計"),
            FieldDef("3連単返還票数合計", 102877, 11, description="3連単返還票数合計"),
            FieldDef("RecordDelimiter", 102888, 2, description="レコード区切"),
        ]
