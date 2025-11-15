"""Parser for O1 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Generated from jv_data_formats.json and JRA-VAN standard schema.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class O1Parser(BaseParser):
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
            FieldDef("HatsubaiFlag1", 39, 1, description="発売フラグ　単勝"),
            FieldDef("HatsubaiFlag2", 40, 1, description="発売フラグ　複勝"),
            FieldDef("HatsubaiFlag3", 41, 1, description="発売フラグ　枠連"),
            FieldDef("FukusyoChakubaraiKey", 42, 1, description="複勝着払キー"),
            FieldDef("TansyoOddsBlock", 43, 8, description="<単勝オッズ>"),
            FieldDef("FukusyoOddsBlock", 267, 12, description="<複勝オッズ>"),
            FieldDef("WakurenOddsBlock", 603, 9, description="<枠連オッズ>"),
            FieldDef("TansyoHyosuTotal", 927, 11, description="単勝票数合計"),
            FieldDef("FukusyoHyosuTotal", 938, 11, description="複勝票数合計"),
            FieldDef("WakurenHyosuTotal", 949, 11, description="枠連票数合計"),
            FieldDef("RecordDelimiter", 960, 2, description="レコード区切"),
        ]
