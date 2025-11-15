"""Parser for SE record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class SEParserJRAVAN(BaseParser):
    """Parser for SE record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "SE"

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
            FieldDef("枠番", 27, 1, description="枠番"),
            FieldDef("馬番", 28, 2, description="馬番"),
            FieldDef("KettoNum", 30, 10, description="血統登録番号"),
            FieldDef("Bamei", 40, 36, description="馬名"),
            FieldDef("UmaKigoCD", 76, 2, description="馬記号コード"),
            FieldDef("SexCD", 78, 1, description="性別コード"),
            FieldDef("HinsyuCD", 79, 1, description="品種コード"),
            FieldDef("KeiroCD", 80, 2, description="毛色コード"),
            FieldDef("Barei", 82, 2, convert_type="SMALLINT", description="馬齢"),
            FieldDef("TozaiCD", 84, 1, description="東西所属コード"),
            FieldDef("ChokyosiCode", 85, 5, description="調教師コード"),
            FieldDef("ChokyosiRyakusyo", 90, 8, description="調教師名略称"),
            FieldDef("BanusiCode", 98, 6, description="馬主コード"),
            FieldDef("馬主名(法人格無)", 104, 64, description="馬主名(法人格無)"),
            FieldDef("Fukusyoku", 168, 60, description="服色標示"),
            FieldDef("予備", 228, 60, description="予備"),
            FieldDef("負担重量", 288, 3, description="負担重量"),
            FieldDef("変更前負担重量", 291, 3, description="変更前負担重量"),
            FieldDef("ブリンカー使用区分", 294, 1, description="ブリンカー使用区分"),
            FieldDef("予備", 295, 1, description="予備"),
            FieldDef("KisyuCode", 296, 5, description="騎手コード"),
            FieldDef("変更前騎手コード", 301, 5, description="変更前騎手コード"),
            FieldDef("KisyuRyakusyo", 306, 8, description="騎手名略称"),
            FieldDef("変更前騎手名略称", 314, 8, description="変更前騎手名略称"),
            FieldDef("騎手見習コード", 322, 1, description="騎手見習コード"),
            FieldDef("変更前騎手見習コード", 323, 1, description="変更前騎手見習コード"),
            FieldDef("BaTaijyu", 324, 3, convert_type="SMALLINT", description="馬体重"),
            FieldDef("ZogenFugo", 327, 1, description="増減符号"),
            FieldDef("ZogenSa", 328, 3, convert_type="SMALLINT", description="増減差"),
            FieldDef("異常区分コード", 331, 1, description="異常区分コード"),
            FieldDef("NyusenJyuni", 332, 2, convert_type="SMALLINT", description="入線順位"),
            FieldDef("KakuteiJyuni", 334, 2, convert_type="SMALLINT", description="確定着順"),
            FieldDef("DochakuKubun", 336, 1, description="同着区分"),
            FieldDef("同着頭数", 337, 1, description="同着頭数"),
            FieldDef("走破タイム", 338, 4, description="走破タイム"),
            FieldDef("ChakusaCD", 342, 3, description="着差コード"),
            FieldDef("＋着差コード", 345, 3, description="＋着差コード"),
            FieldDef("＋＋着差コード", 348, 3, description="＋＋着差コード"),
            FieldDef("1コーナーでの順位", 351, 2, description="1コーナーでの順位"),
            FieldDef("2コーナーでの順位", 353, 2, description="2コーナーでの順位"),
            FieldDef("3コーナーでの順位", 355, 2, description="3コーナーでの順位"),
            FieldDef("4コーナーでの順位", 357, 2, description="4コーナーでの順位"),
            FieldDef("単勝オッズ", 359, 4, description="単勝オッズ"),
            FieldDef("単勝人気順", 363, 2, description="単勝人気順"),
            FieldDef("獲得本賞金", 365, 8, description="獲得本賞金"),
            FieldDef("獲得付加賞金", 373, 8, description="獲得付加賞金"),
            FieldDef("予備", 381, 3, description="予備"),
            FieldDef("予備", 384, 3, description="予備"),
            FieldDef("後4ハロンタイム", 387, 3, description="後4ハロンタイム"),
            FieldDef("後3ハロンタイム", 390, 3, description="後3ハロンタイム"),
            FieldDef("<1着馬(相手馬)情報>", 393, 46, description="<1着馬(相手馬)情報>"),
            FieldDef("タイム差", 531, 4, description="タイム差"),
            FieldDef("レコード更新区分", 535, 1, description="レコード更新区分"),
            FieldDef("マイニング区分", 536, 1, description="マイニング区分"),
            FieldDef("マイニング予想走破タイム", 537, 5, description="マイニング予想走破タイム"),
            FieldDef("マイニング予想誤差(信頼度)＋", 542, 4, description="マイニング予想誤差(信頼度)＋"),
            FieldDef("マイニング予想誤差(信頼度)－", 546, 4, description="マイニング予想誤差(信頼度)－"),
            FieldDef("マイニング予想順位", 550, 2, description="マイニング予想順位"),
            FieldDef("今回レース脚質判定", 552, 1, description="今回レース脚質判定"),
            FieldDef("RecordDelimiter", 553, 2, description="レコード区切"),
        ]
