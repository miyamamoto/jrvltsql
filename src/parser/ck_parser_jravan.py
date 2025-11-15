"""Parser for CK record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class CKParserJRAVAN(BaseParser):
    """Parser for CK record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "CK"

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
            FieldDef("KettoNum", 27, 10, description="血統登録番号"),
            FieldDef("Bamei", 37, 36, description="馬名"),
            FieldDef("平地本賞金累計", 73, 9, description="平地本賞金累計"),
            FieldDef("障害本賞金累計", 82, 9, description="障害本賞金累計"),
            FieldDef("平地付加賞金累計", 91, 9, description="平地付加賞金累計"),
            FieldDef("障害付加賞金累計", 100, 9, description="障害付加賞金累計"),
            FieldDef("平地収得賞金累計", 109, 9, description="平地収得賞金累計"),
            FieldDef("障害収得賞金累計", 118, 9, description="障害収得賞金累計"),
            FieldDef("総合着回数", 127, 3, description="総合着回数"),
            FieldDef("中央合計着回数", 145, 3, description="中央合計着回数"),
            FieldDef("芝直・着回数", 163, 3, description="芝直・着回数"),
            FieldDef("芝右・着回数", 181, 3, description="芝右・着回数"),
            FieldDef("芝左・着回数", 199, 3, description="芝左・着回数"),
            FieldDef("ダ直・着回数", 217, 3, description="ダ直・着回数"),
            FieldDef("ダ右・着回数", 235, 3, description="ダ右・着回数"),
            FieldDef("ダ左・着回数", 253, 3, description="ダ左・着回数"),
            FieldDef("障害・着回数", 271, 3, description="障害・着回数"),
            FieldDef("芝良・着回数", 289, 3, description="芝良・着回数"),
            FieldDef("芝稍・着回数", 307, 3, description="芝稍・着回数"),
            FieldDef("芝重・着回数", 325, 3, description="芝重・着回数"),
            FieldDef("芝不・着回数", 343, 3, description="芝不・着回数"),
            FieldDef("ダ良・着回数", 361, 3, description="ダ良・着回数"),
            FieldDef("ダ稍・着回数", 379, 3, description="ダ稍・着回数"),
            FieldDef("ダ重・着回数", 397, 3, description="ダ重・着回数"),
            FieldDef("ダ不・着回数", 415, 3, description="ダ不・着回数"),
            FieldDef("障良・着回数", 433, 3, description="障良・着回数"),
            FieldDef("障稍・着回数", 451, 3, description="障稍・着回数"),
            FieldDef("障重・着回数", 469, 3, description="障重・着回数"),
            FieldDef("障不・着回数", 487, 3, description="障不・着回数"),
            FieldDef("芝1200以下・着回数", 505, 3, description="芝1200以下・着回数"),
            FieldDef("芝1201-1400・着回数", 523, 3, description="芝1201-1400・着回数"),
            FieldDef("芝1401-1600・着回数", 541, 3, description="芝1401-1600・着回数"),
            FieldDef("芝1601-1800・着回数", 559, 3, description="芝1601-1800・着回数"),
            FieldDef("芝1801-2000・着回数", 577, 3, description="芝1801-2000・着回数"),
            FieldDef("芝2001-2200・着回数", 595, 3, description="芝2001-2200・着回数"),
            FieldDef("芝2201-2400・着回数", 613, 3, description="芝2201-2400・着回数"),
            FieldDef("芝2401-2800・着回数", 631, 3, description="芝2401-2800・着回数"),
            FieldDef("芝2801以上・着回数", 649, 3, description="芝2801以上・着回数"),
            FieldDef("ダ1200以下・着回数", 667, 3, description="ダ1200以下・着回数"),
            FieldDef("ダ1201-1400・着回数", 685, 3, description="ダ1201-1400・着回数"),
            FieldDef("ダ1401-1600・着回数", 703, 3, description="ダ1401-1600・着回数"),
            FieldDef("ダ1601-1800・着回数", 721, 3, description="ダ1601-1800・着回数"),
            FieldDef("ダ1801-2000・着回数", 739, 3, description="ダ1801-2000・着回数"),
            FieldDef("ダ2001-2200・着回数", 757, 3, description="ダ2001-2200・着回数"),
            FieldDef("ダ2201-2400・着回数", 775, 3, description="ダ2201-2400・着回数"),
            FieldDef("ダ2401-2800・着回数", 793, 3, description="ダ2401-2800・着回数"),
            FieldDef("ダ2801以上・着回数", 811, 3, description="ダ2801以上・着回数"),
            FieldDef("札幌芝・着回数", 829, 3, description="札幌芝・着回数"),
            FieldDef("函館芝・着回数", 847, 3, description="函館芝・着回数"),
            FieldDef("福島芝・着回数", 865, 3, description="福島芝・着回数"),
            FieldDef("新潟芝・着回数", 883, 3, description="新潟芝・着回数"),
            FieldDef("東京芝・着回数", 901, 3, description="東京芝・着回数"),
            FieldDef("中山芝・着回数", 919, 3, description="中山芝・着回数"),
            FieldDef("中京芝・着回数", 937, 3, description="中京芝・着回数"),
            FieldDef("京都芝・着回数", 955, 3, description="京都芝・着回数"),
            FieldDef("阪神芝・着回数", 973, 3, description="阪神芝・着回数"),
            FieldDef("小倉芝・着回数", 991, 3, description="小倉芝・着回数"),
            FieldDef("札幌ダ・着回数", 1009, 3, description="札幌ダ・着回数"),
            FieldDef("函館ダ・着回数", 1027, 3, description="函館ダ・着回数"),
            FieldDef("福島ダ・着回数", 1045, 3, description="福島ダ・着回数"),
            FieldDef("新潟ダ・着回数", 1063, 3, description="新潟ダ・着回数"),
            FieldDef("東京ダ・着回数", 1081, 3, description="東京ダ・着回数"),
            FieldDef("中山ダ・着回数", 1099, 3, description="中山ダ・着回数"),
            FieldDef("中京ダ・着回数", 1117, 3, description="中京ダ・着回数"),
            FieldDef("京都ダ・着回数", 1135, 3, description="京都ダ・着回数"),
            FieldDef("阪神ダ・着回数", 1153, 3, description="阪神ダ・着回数"),
            FieldDef("小倉ダ・着回数", 1171, 3, description="小倉ダ・着回数"),
            FieldDef("札幌障・着回数", 1189, 3, description="札幌障・着回数"),
            FieldDef("函館障・着回数", 1207, 3, description="函館障・着回数"),
            FieldDef("福島障・着回数", 1225, 3, description="福島障・着回数"),
            FieldDef("新潟障・着回数", 1243, 3, description="新潟障・着回数"),
            FieldDef("東京障・着回数", 1261, 3, description="東京障・着回数"),
            FieldDef("中山障・着回数", 1279, 3, description="中山障・着回数"),
            FieldDef("中京障・着回数", 1297, 3, description="中京障・着回数"),
            FieldDef("京都障・着回数", 1315, 3, description="京都障・着回数"),
            FieldDef("阪神障・着回数", 1333, 3, description="阪神障・着回数"),
            FieldDef("小倉障・着回数", 1351, 3, description="小倉障・着回数"),
            FieldDef("脚質傾向", 1369, 3, description="脚質傾向"),
            FieldDef("登録レース数", 1381, 3, description="登録レース数"),
            FieldDef("KisyuCode", 1384, 5, description="騎手コード"),
            FieldDef("騎手名", 1389, 34, description="騎手名"),
            FieldDef("<騎手本年･累計成績情報>", 1423, 1220, description="<騎手本年･累計成績情報>"),
            FieldDef("ChokyosiCode", 3863, 5, description="調教師コード"),
            FieldDef("調教師名", 3868, 34, description="調教師名"),
            FieldDef("<調教師本年･累計成績情報>", 3902, 1220, description="<調教師本年･累計成績情報>"),
            FieldDef("BanusiCode", 6342, 6, description="馬主コード"),
            FieldDef("馬主名(法人格有)", 6348, 64, description="馬主名(法人格有)"),
            FieldDef("馬主名(法人格無)", 6412, 64, description="馬主名(法人格無)"),
            FieldDef("<本年･累計成績情報>", 6476, 60, description="<本年･累計成績情報>"),
            FieldDef("生産者コード", 6596, 8, description="生産者コード"),
            FieldDef("生産者名(法人格有)", 6604, 72, description="生産者名(法人格有)"),
            FieldDef("生産者名(法人格無)", 6676, 72, description="生産者名(法人格無)"),
            FieldDef("<本年･累計成績情報>", 6748, 60, description="<本年･累計成績情報>"),
            FieldDef("RecordDelimiter", 6868, 2, description="レコード区切"),
        ]
