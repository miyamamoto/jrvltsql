"""Parser for O1 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class O1ParserJRAVAN(BaseParser):
    """Parser for O1 record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "O1"

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
            FieldDef("TorokuTosu", 35, 2, convert_type="SMALLINT", description="登録頭数"),
            FieldDef("SyussoTosu", 37, 2, convert_type="SMALLINT", description="出走頭数"),
            FieldDef("発売フラグ　単勝", 39, 1, description="発売フラグ　単勝"),
            FieldDef("発売フラグ　複勝", 40, 1, description="発売フラグ　複勝"),
            FieldDef("発売フラグ　枠連", 41, 1, description="発売フラグ　枠連"),
            FieldDef("複勝着払キー", 42, 1, description="複勝着払キー"),
            FieldDef("<単勝オッズ>", 43, 8, description="<単勝オッズ>"),
            FieldDef("<複勝オッズ>", 267, 12, description="<複勝オッズ>"),
            FieldDef("<枠連オッズ>", 603, 9, description="<枠連オッズ>"),
            FieldDef("単勝票数合計", 927, 11, description="単勝票数合計"),
            FieldDef("複勝票数合計", 938, 11, description="複勝票数合計"),
            FieldDef("枠連票数合計", 949, 11, description="枠連票数合計"),
            FieldDef("RecordDelimiter", 960, 2, description="レコード区切"),
        ]
