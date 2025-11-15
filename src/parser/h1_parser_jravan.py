"""Parser for H1 record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class H1ParserJRAVAN(BaseParser):
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
            FieldDef("発売フラグ　単勝", 31, 1, description="発売フラグ　単勝"),
            FieldDef("発売フラグ　複勝", 32, 1, description="発売フラグ　複勝"),
            FieldDef("発売フラグ　枠連", 33, 1, description="発売フラグ　枠連"),
            FieldDef("発売フラグ　馬連", 34, 1, description="発売フラグ　馬連"),
            FieldDef("発売フラグ　ワイド", 35, 1, description="発売フラグ　ワイド"),
            FieldDef("発売フラグ　馬単", 36, 1, description="発売フラグ　馬単"),
            FieldDef("発売フラグ　3連複", 37, 1, description="発売フラグ　3連複"),
            FieldDef("複勝着払キー", 38, 1, description="複勝着払キー"),
            FieldDef("返還馬番情報(馬番01～28)", 39, 1, description="返還馬番情報(馬番01～28)"),
            FieldDef("返還枠番情報(枠番1～8)", 67, 1, description="返還枠番情報(枠番1～8)"),
            FieldDef("返還同枠情報(枠番1～8)", 75, 1, description="返還同枠情報(枠番1～8)"),
            FieldDef("<単勝票数>", 83, 15, description="<単勝票数>"),
            FieldDef("<複勝票数>", 503, 15, description="<複勝票数>"),
            FieldDef("<枠連票数>", 923, 15, description="<枠連票数>"),
            FieldDef("<馬連票数>", 1463, 18, description="<馬連票数>"),
            FieldDef("<ワイド票数>", 4217, 18, description="<ワイド票数>"),
            FieldDef("<馬単票数>", 6971, 18, description="<馬単票数>"),
            FieldDef("<3連複票数>", 12479, 20, description="<3連複票数>"),
            FieldDef("単勝票数合計", 28799, 11, description="単勝票数合計"),
            FieldDef("複勝票数合計", 28810, 11, description="複勝票数合計"),
            FieldDef("枠連票数合計", 28821, 11, description="枠連票数合計"),
            FieldDef("馬連票数合計", 28832, 11, description="馬連票数合計"),
            FieldDef("ワイド票数合計", 28843, 11, description="ワイド票数合計"),
            FieldDef("馬単票数合計", 28854, 11, description="馬単票数合計"),
            FieldDef("3連複票数合計", 28865, 11, description="3連複票数合計"),
            FieldDef("単勝返還票数合計", 28876, 11, description="単勝返還票数合計"),
            FieldDef("複勝返還票数合計", 28887, 11, description="複勝返還票数合計"),
            FieldDef("枠連返還票数合計", 28898, 11, description="枠連返還票数合計"),
            FieldDef("馬連返還票数合計", 28909, 11, description="馬連返還票数合計"),
            FieldDef("ワイド返還票数合計", 28920, 11, description="ワイド返還票数合計"),
            FieldDef("馬単返還票数合計", 28931, 11, description="馬単返還票数合計"),
            FieldDef("3連複返還票数合計", 28942, 11, description="3連複返還票数合計"),
            FieldDef("RecordDelimiter", 28953, 2, description="レコード区切"),
        ]
