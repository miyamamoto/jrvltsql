"""Parser for TK record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class TKParserJRAVAN(BaseParser):
    """Parser for TK record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "TK"

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
            FieldDef("YoubiCD", 27, 1, description="曜日コード"),
            FieldDef("TokuNum", 28, 4, description="特別競走番号"),
            FieldDef("Hondai", 32, 60, description="競走名本題"),
            FieldDef("Fukudai", 92, 60, description="競走名副題"),
            FieldDef("Kakko", 152, 60, description="競走名カッコ内"),
            FieldDef("HondaiEng", 212, 120, description="競走名本題欧字"),
            FieldDef("FukudaiEng", 332, 120, description="競走名副題欧字"),
            FieldDef("KakkoEng", 452, 120, description="競走名カッコ内欧字"),
            FieldDef("Ryakusyo10", 572, 20, description="競走名略称10文字"),
            FieldDef("Ryakusyo6", 592, 12, description="競走名略称6文字"),
            FieldDef("Ryakusyo3", 604, 6, description="競走名略称3文字"),
            FieldDef("競走名区分", 610, 1, description="競走名区分"),
            FieldDef("重賞回次第N回", 611, 3, description="重賞回次[第N回]"),
            FieldDef("グレードコード", 614, 1, description="グレードコード"),
            FieldDef("競走種別コード", 615, 2, description="競走種別コード"),
            FieldDef("競走記号コード", 617, 3, description="競走記号コード"),
            FieldDef("重量種別コード", 620, 1, description="重量種別コード"),
            FieldDef("競走条件コード_2歳条件", 621, 3, description="競走条件コード 2歳条件"),
            FieldDef("競走条件コード_3歳条件", 624, 3, description="競走条件コード 3歳条件"),
            FieldDef("競走条件コード_4歳条件", 627, 3, description="競走条件コード 4歳条件"),
            FieldDef("競走条件コード_5歳以上条件", 630, 3, description="競走条件コード 5歳以上条件"),
            FieldDef("競走条件コード_最若年条件", 633, 3, description="競走条件コード 最若年条件"),
            FieldDef("Kyori", 636, 4, convert_type="SMALLINT", description="距離"),
            FieldDef("TrackCD", 640, 2, description="トラックコード"),
            FieldDef("CourseKubunCD", 642, 2, description="コース区分"),
            FieldDef("ハンデ発表日", 644, 8, description="ハンデ発表日"),
            FieldDef("TorokuTosu", 652, 3, convert_type="SMALLINT", description="登録頭数"),
            FieldDef("<登録馬毎情報>", 655, 70, description="<登録馬毎情報>"),
            FieldDef("RecordDelimiter", 21655, 2, description="レコード区切"),
        ]
