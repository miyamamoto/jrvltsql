"""Parser for RA record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class RAParserJRAVAN(BaseParser):
    """Parser for RA record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "RA"

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
            FieldDef("変更前グレードコード", 615, 1, description="変更前グレードコード"),
            FieldDef("競走種別コード", 616, 2, description="競走種別コード"),
            FieldDef("競走記号コード", 618, 3, description="競走記号コード"),
            FieldDef("重量種別コード", 621, 1, description="重量種別コード"),
            FieldDef("競走条件コード_2歳条件", 622, 3, description="競走条件コード 2歳条件"),
            FieldDef("競走条件コード_3歳条件", 625, 3, description="競走条件コード 3歳条件"),
            FieldDef("競走条件コード_4歳条件", 628, 3, description="競走条件コード 4歳条件"),
            FieldDef("競走条件コード_5歳以上条件", 631, 3, description="競走条件コード 5歳以上条件"),
            FieldDef("競走条件コード_最若年条件", 634, 3, description="競走条件コード 最若年条件"),
            FieldDef("競走条件名称", 637, 60, description="競走条件名称"),
            FieldDef("Kyori", 697, 4, convert_type="SMALLINT", description="距離"),
            FieldDef("変更前距離", 701, 4, description="変更前距離"),
            FieldDef("TrackCD", 705, 2, description="トラックコード"),
            FieldDef("変更前トラックコード", 707, 2, description="変更前トラックコード"),
            FieldDef("CourseKubunCD", 709, 2, description="コース区分"),
            FieldDef("変更前コース区分", 711, 2, description="変更前コース区分"),
            FieldDef("Honsyokin", 713, 8, convert_type="PRIZE_MONEY", description="本賞金"),
            FieldDef("変更前本賞金", 769, 8, description="変更前本賞金"),
            FieldDef("Fukasyokin", 809, 8, convert_type="PRIZE_MONEY", description="付加賞金"),
            FieldDef("変更前付加賞金", 849, 8, description="変更前付加賞金"),
            FieldDef("HassoTime", 873, 4, convert_type="TIME", description="発走時刻"),
            FieldDef("変更前発走時刻", 877, 4, description="変更前発走時刻"),
            FieldDef("TorokuTosu", 881, 2, convert_type="SMALLINT", description="登録頭数"),
            FieldDef("SyussoTosu", 883, 2, convert_type="SMALLINT", description="出走頭数"),
            FieldDef("NyusenTosu", 885, 2, convert_type="SMALLINT", description="入線頭数"),
            FieldDef("TenkoCD", 887, 1, description="天候コード"),
            FieldDef("SibaBabaCD", 888, 1, description="芝馬場状態コード"),
            FieldDef("DirtBabaCD", 889, 1, description="ダート馬場状態コード"),
            FieldDef("LapTime", 890, 3, description="ラップタイム"),
            FieldDef("障害マイルタイム", 965, 4, description="障害マイルタイム"),
            FieldDef("HaronTimeS3", 969, 3, convert_type="LAP_TIME", description="前3ハロン"),
            FieldDef("HaronTimeS4", 972, 3, convert_type="LAP_TIME", description="前4ハロン"),
            FieldDef("HaronTimeL3", 975, 3, convert_type="LAP_TIME", description="後3ハロン"),
            FieldDef("HaronTimeL4", 978, 3, convert_type="LAP_TIME", description="後4ハロン"),
            FieldDef("<コーナー通過順位>", 981, 72, description="<コーナー通過順位>"),
            FieldDef("レコード更新区分", 1269, 1, description="レコード更新区分"),
            FieldDef("RecordDelimiter", 1270, 2, description="レコード区切"),
        ]
