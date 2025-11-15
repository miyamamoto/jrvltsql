"""Parser for UM record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class UMParserJRAVAN(BaseParser):
    """Parser for UM record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "UM"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("KettoNum", 11, 10, description="血統登録番号"),
            FieldDef("競走馬抹消区分", 21, 1, description="競走馬抹消区分"),
            FieldDef("競走馬登録年月日", 22, 8, description="競走馬登録年月日"),
            FieldDef("競走馬抹消年月日", 30, 8, description="競走馬抹消年月日"),
            FieldDef("生年月日", 38, 8, description="生年月日"),
            FieldDef("Bamei", 46, 36, description="馬名"),
            FieldDef("馬名半角ｶﾅ", 82, 36, description="馬名半角ｶﾅ"),
            FieldDef("馬名欧字", 118, 60, description="馬名欧字"),
            FieldDef("JRA施設在きゅうフラグ", 178, 1, description="JRA施設在きゅうフラグ"),
            FieldDef("予備", 179, 19, description="予備"),
            FieldDef("UmaKigoCD", 198, 2, description="馬記号コード"),
            FieldDef("SexCD", 200, 1, description="性別コード"),
            FieldDef("HinsyuCD", 201, 1, description="品種コード"),
            FieldDef("KeiroCD", 202, 2, description="毛色コード"),
            FieldDef("<3代血統情報>", 204, 46, description="<3代血統情報>"),
            FieldDef("TozaiCD", 848, 1, description="東西所属コード"),
            FieldDef("ChokyosiCode", 849, 5, description="調教師コード"),
            FieldDef("ChokyosiRyakusyo", 854, 8, description="調教師名略称"),
            FieldDef("招待地域名", 862, 20, description="招待地域名"),
            FieldDef("生産者コード", 882, 8, description="生産者コード"),
            FieldDef("生産者名(法人格無)", 890, 72, description="生産者名(法人格無)"),
            FieldDef("産地名", 962, 20, description="産地名"),
            FieldDef("BanusiCode", 982, 6, description="馬主コード"),
            FieldDef("馬主名(法人格無)", 988, 64, description="馬主名(法人格無)"),
            FieldDef("平地本賞金累計", 1052, 9, description="平地本賞金累計"),
            FieldDef("障害本賞金累計", 1061, 9, description="障害本賞金累計"),
            FieldDef("平地付加賞金累計", 1070, 9, description="平地付加賞金累計"),
            FieldDef("障害付加賞金累計", 1079, 9, description="障害付加賞金累計"),
            FieldDef("平地収得賞金累計", 1088, 9, description="平地収得賞金累計"),
            FieldDef("障害収得賞金累計", 1097, 9, description="障害収得賞金累計"),
            FieldDef("総合着回数", 1106, 3, description="総合着回数"),
            FieldDef("中央合計着回数", 1124, 3, description="中央合計着回数"),
            FieldDef("芝直・着回数", 1142, 3, description="芝直・着回数"),
            FieldDef("芝右・着回数", 1160, 3, description="芝右・着回数"),
            FieldDef("芝左・着回数", 1178, 3, description="芝左・着回数"),
            FieldDef("ダ直・着回数", 1196, 3, description="ダ直・着回数"),
            FieldDef("ダ右・着回数", 1214, 3, description="ダ右・着回数"),
            FieldDef("ダ左・着回数", 1232, 3, description="ダ左・着回数"),
            FieldDef("障害・着回数", 1250, 3, description="障害・着回数"),
            FieldDef("芝良・着回数", 1268, 3, description="芝良・着回数"),
            FieldDef("芝稍・着回数", 1286, 3, description="芝稍・着回数"),
            FieldDef("芝重・着回数", 1304, 3, description="芝重・着回数"),
            FieldDef("芝不・着回数", 1322, 3, description="芝不・着回数"),
            FieldDef("ダ良・着回数", 1340, 3, description="ダ良・着回数"),
            FieldDef("ダ稍・着回数", 1358, 3, description="ダ稍・着回数"),
            FieldDef("ダ重・着回数", 1376, 3, description="ダ重・着回数"),
            FieldDef("ダ不・着回数", 1394, 3, description="ダ不・着回数"),
            FieldDef("障良・着回数", 1412, 3, description="障良・着回数"),
            FieldDef("障稍・着回数", 1430, 3, description="障稍・着回数"),
            FieldDef("障重・着回数", 1448, 3, description="障重・着回数"),
            FieldDef("障不・着回数", 1466, 3, description="障不・着回数"),
            FieldDef("芝16下・着回数", 1484, 3, description="芝16下・着回数"),
            FieldDef("芝22下・着回数", 1502, 3, description="芝22下・着回数"),
            FieldDef("芝22超・着回数", 1520, 3, description="芝22超・着回数"),
            FieldDef("ダ16下・着回数", 1538, 3, description="ダ16下・着回数"),
            FieldDef("ダ22下・着回数", 1556, 3, description="ダ22下・着回数"),
            FieldDef("ダ22超・着回数", 1574, 3, description="ダ22超・着回数"),
            FieldDef("脚質傾向", 1592, 3, description="脚質傾向"),
            FieldDef("登録レース数", 1604, 3, description="登録レース数"),
            FieldDef("RecordDelimiter", 1607, 2, description="レコード区切"),
        ]
