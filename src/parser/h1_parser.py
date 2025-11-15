"""Parser for H1 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Generated from jv_data_formats.json and JRA-VAN standard schema.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class H1Parser(BaseParser):
    """Parser for H1 record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "H1"

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
            FieldDef("Umaban", 23, 2, convert_type="SMALLINT", description="開催日目[N日目]"),
            FieldDef("TanOdds", 25, 2, description="レース番号"),
            FieldDef("TanNinki", 27, 2, description="登録頭数"),
            FieldDef("FukuOddsLow", 29, 2, description="出走頭数"),
            FieldDef("FukuOddsHigh", 31, 1, description="発売フラグ　単勝"),
            FieldDef("FukuNinki", 32, 1, description="発売フラグ　複勝"),
            FieldDef("HatsubaiFlag3", 33, 1, description="発売フラグ　枠連"),
            FieldDef("HatsubaiFlag4", 34, 1, description="発売フラグ　馬連"),
            FieldDef("HatsubaiFlag5", 35, 1, description="発売フラグ　ワイド"),
            FieldDef("HatsubaiFlag6", 36, 1, description="発売フラグ　馬単"),
            FieldDef("HatsubaiFlag7", 37, 1, description="発売フラグ　3連複"),
            FieldDef("FukusyoChakubaraiKey", 38, 1, description="複勝着払キー"),
            FieldDef("HenkanUmabanInfo", 39, 1, description="返還馬番情報(馬番01～28)"),
            FieldDef("HenkanWakubanInfo", 67, 1, description="返還枠番情報(枠番1～8)"),
            FieldDef("HenkanDowakuInfo", 75, 1, description="返還同枠情報(枠番1～8)"),
            FieldDef("TansyoHyosuBlock", 83, 15, description="<単勝票数>"),
            FieldDef("FukusyoHyosuBlock", 503, 15, description="<複勝票数>"),
            FieldDef("WakurenHyosuBlock", 923, 15, description="<枠連票数>"),
            FieldDef("UmarenHyosuBlock", 1463, 18, description="<馬連票数>"),
            FieldDef("WideHyosuBlock", 4217, 18, description="<ワイド票数>"),
            FieldDef("UmatanHyosuBlock", 6971, 18, description="<馬単票数>"),
            FieldDef("SanrenfukuHyosuBlock", 12479, 20, description="<3連複票数>"),
            FieldDef("TansyoHyosuTotal", 28799, 11, description="単勝票数合計"),
            FieldDef("FukusyoHyosuTotal", 28810, 11, description="複勝票数合計"),
            FieldDef("WakurenHyosuTotal", 28821, 11, description="枠連票数合計"),
            FieldDef("UmarenHyosuTotal", 28832, 11, description="馬連票数合計"),
            FieldDef("WideHyosuTotal", 28843, 11, description="ワイド票数合計"),
            FieldDef("UmatanHyosuTotal", 28854, 11, description="馬単票数合計"),
            FieldDef("SanrenfukuHyosuTotal", 28865, 11, description="3連複票数合計"),
            FieldDef("TansyoHenkanTotal", 28876, 11, description="単勝返還票数合計"),
            FieldDef("FukusyoHenkanTotal", 28887, 11, description="複勝返還票数合計"),
            FieldDef("WakurenHenkanTotal", 28898, 11, description="枠連返還票数合計"),
            FieldDef("UmarenHenkanTotal", 28909, 11, description="馬連返還票数合計"),
            FieldDef("WideHenkanTotal", 28920, 11, description="ワイド返還票数合計"),
            FieldDef("UmatanHenkanTotal", 28931, 11, description="馬単返還票数合計"),
            FieldDef("SanrenfukuHenkanTotal", 28942, 11, description="3連複返還票数合計"),
            FieldDef("RecordDelimiter", 28953, 2, description="レコード区切"),
        ]
