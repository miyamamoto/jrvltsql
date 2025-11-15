"""Parser for CK record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class CKParser(BaseParser):
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
            FieldDef("HeichiHonsyokinTotal", 73, 9, description="平地本賞金累計"),
            FieldDef("SyogaiHonsyokinTotal", 82, 9, description="障害本賞金累計"),
            FieldDef("HeichiFukasyokinTotal", 91, 9, description="平地付加賞金累計"),
            FieldDef("SyogaiFukasyokinTotal", 100, 9, description="障害付加賞金累計"),
            FieldDef("HeichiSyutokuTotal", 109, 9, description="平地収得賞金累計"),
            FieldDef("SyogaiSyutokuTotal", 118, 9, description="障害収得賞金累計"),
            FieldDef("TotalChakuCount", 127, 3, description="総合着回数"),
            FieldDef("ChuoChakuCount", 145, 3, description="中央合計着回数"),
            FieldDef("SibaChoChaku", 163, 3, description="芝直・着回数"),
            FieldDef("SibaMigiChaku", 181, 3, description="芝右・着回数"),
            FieldDef("SibaHidariChaku", 199, 3, description="芝左・着回数"),
            FieldDef("DirtChoChaku", 217, 3, description="ダ直・着回数"),
            FieldDef("DirtMigiChaku", 235, 3, description="ダ右・着回数"),
            FieldDef("DirtHidariChaku", 253, 3, description="ダ左・着回数"),
            FieldDef("SyogaiChaku", 271, 3, description="障害・着回数"),
            FieldDef("SibaRyoChaku", 289, 3, description="芝良・着回数"),
            FieldDef("SibaYayaChaku", 307, 3, description="芝稍・着回数"),
            FieldDef("SibaOmoChaku", 325, 3, description="芝重・着回数"),
            FieldDef("SibaFuChaku", 343, 3, description="芝不・着回数"),
            FieldDef("DirtRyoChaku", 361, 3, description="ダ良・着回数"),
            FieldDef("DirtYayaChaku", 379, 3, description="ダ稍・着回数"),
            FieldDef("DirtOmoChaku", 397, 3, description="ダ重・着回数"),
            FieldDef("DirtFuChaku", 415, 3, description="ダ不・着回数"),
            FieldDef("SyogaiRyoChaku", 433, 3, description="障良・着回数"),
            FieldDef("SyogaiYayaChaku", 451, 3, description="障稍・着回数"),
            FieldDef("SyogaiOmoChaku", 469, 3, description="障重・着回数"),
            FieldDef("SyogaiFuChaku", 487, 3, description="障不・着回数"),
            FieldDef("Siba1200IkaChaku", 505, 3, description="芝1200以下・着回数"),
            FieldDef("Siba1201_1400Chaku", 523, 3, description="芝1201-1400・着回数"),
            FieldDef("Siba1401_1600Chaku", 541, 3, description="芝1401-1600・着回数"),
            FieldDef("Siba1601_1800Chaku", 559, 3, description="芝1601-1800・着回数"),
            FieldDef("Siba1801_2000Chaku", 577, 3, description="芝1801-2000・着回数"),
            FieldDef("Siba2001_2200Chaku", 595, 3, description="芝2001-2200・着回数"),
            FieldDef("Siba2201_2400Chaku", 613, 3, description="芝2201-2400・着回数"),
            FieldDef("Siba2401_2800Chaku", 631, 3, description="芝2401-2800・着回数"),
            FieldDef("Siba2801OverChaku", 649, 3, description="芝2801以上・着回数"),
            FieldDef("Dirt1200IkaChaku", 667, 3, description="ダ1200以下・着回数"),
            FieldDef("Dirt1201_1400Chaku", 685, 3, description="ダ1201-1400・着回数"),
            FieldDef("Dirt1401_1600Chaku", 703, 3, description="ダ1401-1600・着回数"),
            FieldDef("Dirt1601_1800Chaku", 721, 3, description="ダ1601-1800・着回数"),
            FieldDef("Dirt1801_2000Chaku", 739, 3, description="ダ1801-2000・着回数"),
            FieldDef("Dirt2001_2200Chaku", 757, 3, description="ダ2001-2200・着回数"),
            FieldDef("Dirt2201_2400Chaku", 775, 3, description="ダ2201-2400・着回数"),
            FieldDef("Dirt2401_2800Chaku", 793, 3, description="ダ2401-2800・着回数"),
            FieldDef("Dirt2801OverChaku", 811, 3, description="ダ2801以上・着回数"),
            FieldDef("SapporoSibaChaku", 829, 3, description="札幌芝・着回数"),
            FieldDef("HakodateSibaChaku", 847, 3, description="函館芝・着回数"),
            FieldDef("FukushimaSibaChaku", 865, 3, description="福島芝・着回数"),
            FieldDef("NiigataSibaChaku", 883, 3, description="新潟芝・着回数"),
            FieldDef("TokyoSibaChaku", 901, 3, description="東京芝・着回数"),
            FieldDef("NakayamaSibaChaku", 919, 3, description="中山芝・着回数"),
            FieldDef("ChukyoSibaChaku", 937, 3, description="中京芝・着回数"),
            FieldDef("KyotoSibaChaku", 955, 3, description="京都芝・着回数"),
            FieldDef("HanshinSibaChaku", 973, 3, description="阪神芝・着回数"),
            FieldDef("KokuraSibaChaku", 991, 3, description="小倉芝・着回数"),
            FieldDef("SapporoDirtChaku", 1009, 3, description="札幌ダ・着回数"),
            FieldDef("HakodateDirtChaku", 1027, 3, description="函館ダ・着回数"),
            FieldDef("FukushimaDirtChaku", 1045, 3, description="福島ダ・着回数"),
            FieldDef("NiigataDirtChaku", 1063, 3, description="新潟ダ・着回数"),
            FieldDef("TokyoDirtChaku", 1081, 3, description="東京ダ・着回数"),
            FieldDef("NakayamaDirtChaku", 1099, 3, description="中山ダ・着回数"),
            FieldDef("ChukyoDirtChaku", 1117, 3, description="中京ダ・着回数"),
            FieldDef("KyotoDirtChaku", 1135, 3, description="京都ダ・着回数"),
            FieldDef("HanshinDirtChaku", 1153, 3, description="阪神ダ・着回数"),
            FieldDef("KokuraDirtChaku", 1171, 3, description="小倉ダ・着回数"),
            FieldDef("SapporoSyogaiChaku", 1189, 3, description="札幌障・着回数"),
            FieldDef("HakodateSyogaiChaku", 1207, 3, description="函館障・着回数"),
            FieldDef("FukushimaSyogaiChaku", 1225, 3, description="福島障・着回数"),
            FieldDef("NiigataSyogaiChaku", 1243, 3, description="新潟障・着回数"),
            FieldDef("TokyoSyogaiChaku", 1261, 3, description="東京障・着回数"),
            FieldDef("NakayamaSyogaiChaku", 1279, 3, description="中山障・着回数"),
            FieldDef("ChukyoSyogaiChaku", 1297, 3, description="中京障・着回数"),
            FieldDef("KyotoSyogaiChaku", 1315, 3, description="京都障・着回数"),
            FieldDef("HanshinSyogaiChaku", 1333, 3, description="阪神障・着回数"),
            FieldDef("KokuraSyogaiChaku", 1351, 3, description="小倉障・着回数"),
            FieldDef("KyakusituKeiko", 1369, 3, description="脚質傾向"),
            FieldDef("RegisteredRaceCount", 1381, 3, description="登録レース数"),
            FieldDef("KisyuCode", 1384, 5, description="騎手コード"),
            FieldDef("KisyuName", 1389, 34, description="騎手名"),
            FieldDef("KisyuResultsInfo", 1423, 1220, description="<騎手本年･累計成績情報>"),
            FieldDef("ChokyosiCode", 3863, 5, description="調教師コード"),
            FieldDef("ChokyosiName", 3868, 34, description="調教師名"),
            FieldDef("ChokyosiResultsInfo", 3902, 1220, description="<調教師本年･累計成績情報>"),
            FieldDef("BanusiCode", 6342, 6, description="馬主コード"),
            FieldDef("BanusiName", 6348, 64, description="馬主名(法人格有)"),
            FieldDef("BanusiName_Co", 6412, 64, description="馬主名(法人格無)"),
            FieldDef("ResultsInfo", 6476, 60, description="<本年･累計成績情報>"),
            FieldDef("BreederCode", 6596, 8, description="生産者コード"),
            FieldDef("BreederName", 6604, 72, description="生産者名(法人格有)"),
            FieldDef("BreederName_Co", 6676, 72, description="生産者名(法人格無)"),
            FieldDef("ResultsInfo", 6748, 60, description="<本年･累計成績情報>"),
            FieldDef("RecordDelimiter", 6868, 2, description="レコード区切"),
        ]
