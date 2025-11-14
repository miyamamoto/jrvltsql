"""Parser for RA (Race) records.

This module parses RA record type which contains race details information.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class RAParser(BaseParser):
    """Parser for RA (Race) record type.

    RA records contain comprehensive race information including:
    - Race identification (year, date, track, race number)
    - Race name and grade
    - Course information (distance, track type)
    - Prize money
    - Race conditions and results
    - Lap times and corner positions

    Record Format:
        - Record type: "RA"
        - Fixed-length format (Shift_JIS encoding)
        - Total length: varies (typically 2000+ bytes)

    Examples:
        >>> parser = RAParser()
        >>> record = b"RA1202406010603081..."  # Raw JV-Data
        >>> data = parser.parse(record)
        >>> print(f"Race: {data['RaceName']}")
        >>> print(f"Distance: {data['Kyori']}m")
    """

    record_type = "RA"

    def _define_fields(self) -> List[FieldDef]:
        """Define RA record field structure.

        Field positions are based on JV-Data specification version 4.9+.

        Returns:
            List of field definitions
        """
        return [
            # レコードヘッダー (0-13)
            FieldDef("headRecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("headDataKubun", 2, 1, description="データ区分"),
            FieldDef("headMakeDate", 3, 8, description="データ作成年月日"),
            # フィラー 11-13
            # レース識別情報 (14-27)
            FieldDef("idYear", 11, 4, description="開催年"),
            FieldDef("idMonthDay", 15, 4, description="開催月日"),
            FieldDef("idJyoCD", 19, 2, description="競馬場コード"),
            FieldDef("idKaiji", 21, 2, description="開催回"),
            FieldDef("idNichiji", 23, 2, description="開催日目"),
            FieldDef("idRaceNum", 25, 2, description="レース番号"),
            # フィラー 27-28
            # レース名称 (28-188)
            FieldDef("RaceNameShort", 28, 20, description="レース名略称10文字"),
            FieldDef("RaceNameShort6", 48, 12, description="レース名略称6文字"),
            FieldDef("RaceNameShort3", 60, 6, description="レース名略称3文字"),
            FieldDef("RaceName", 66, 60, description="レース名本題"),
            FieldDef("RaceNameKana", 126, 60, description="レース名カナ"),
            FieldDef("RaceNameEng", 186, 120, description="レース名欧字"),
            # レース情報 (306-)
            FieldDef("GradeCD", 306, 1, description="グレードコード"),
            FieldDef("RaceName9", 307, 18, description="レース名9字"),
            FieldDef("RaceNameFukudai", 325, 60, description="レース名副題"),
            FieldDef("RaceNameKakko", 385, 60, description="レース名括弧内"),
            FieldDef("JyokenName5", 445, 60, description="競走条件名5歳以上"),
            FieldDef("JyokenName4", 505, 60, description="競走条件名4歳以上"),
            FieldDef("JyokenName3", 565, 60, description="競走条件名3歳以上"),
            FieldDef("JyokenName2", 625, 60, description="競走条件名2歳"),
            FieldDef("Jyoken5", 685, 3, description="競走条件コード5歳以上"),
            FieldDef("Jyoken4", 688, 3, description="競走条件コード4歳以上"),
            FieldDef("Jyoken3", 691, 3, description="競走条件コード3歳以上"),
            FieldDef("Jyoken2", 694, 3, description="競走条件コード2歳"),
            # コース情報 (697-)
            FieldDef("Kyori", 697, 4, "int", "距離メートル"),
            FieldDef("TrackCD", 701, 2, description="トラックコード"),
            FieldDef("CourseKubunCD", 703, 2, description="コース区分"),
            # フィラー 705-710
            # 賞金情報 (710-755)
            FieldDef("HondaiSyogaku1", 710, 9, "int", "本賞金1着"),
            FieldDef("HondaiSyogaku2", 719, 9, "int", "本賞金2着"),
            FieldDef("HondaiSyogaku3", 728, 9, "int", "本賞金3着"),
            FieldDef("HondaiSyogaku4", 737, 9, "int", "本賞金4着"),
            FieldDef("HondaiSyogaku5", 746, 9, "int", "本賞金5着"),
            FieldDef("FukaSyogaku1", 755, 9, "int", "付加賞金1着"),
            FieldDef("FukaSyogaku2", 764, 9, "int", "付加賞金2着"),
            FieldDef("FukaSyogaku3", 773, 9, "int", "付加賞金3着"),
            # レース状況 (782-)
            FieldDef("HassoTime", 782, 4, description="発走時刻HHMM"),
            FieldDef("HassoJikoku", 786, 8, description="発走時刻詳細"),
            # フィラー 794-814
            FieldDef("TorokuTosu", 814, 2, "int", "登録頭数"),
            FieldDef("SyussoTosu", 816, 2, "int", "出走頭数"),
            FieldDef("NyusenTosu", 818, 2, "int", "入線頭数"),
            FieldDef("TenkoCD", 820, 1, description="天候コード"),
            FieldDef("SibaBabaCD", 821, 2, description="芝馬場状態コード"),
            FieldDef("DirtBabaCD", 823, 2, description="ダート馬場状態コード"),
            # ラップタイム (825-975) - 200m×25区間
            FieldDef("LapTime01", 825, 3, description="ラップ1"),
            FieldDef("LapTime02", 828, 3, description="ラップ2"),
            FieldDef("LapTime03", 831, 3, description="ラップ3"),
            FieldDef("LapTime04", 834, 3, description="ラップ4"),
            FieldDef("LapTime05", 837, 3, description="ラップ5"),
            FieldDef("LapTime06", 840, 3, description="ラップ6"),
            FieldDef("LapTime07", 843, 3, description="ラップ7"),
            FieldDef("LapTime08", 846, 3, description="ラップ8"),
            FieldDef("LapTime09", 849, 3, description="ラップ9"),
            FieldDef("LapTime10", 852, 3, description="ラップ10"),
            FieldDef("LapTime11", 855, 3, description="ラップ11"),
            FieldDef("LapTime12", 858, 3, description="ラップ12"),
            FieldDef("LapTime13", 861, 3, description="ラップ13"),
            FieldDef("LapTime14", 864, 3, description="ラップ14"),
            FieldDef("LapTime15", 867, 3, description="ラップ15"),
            FieldDef("LapTime16", 870, 3, description="ラップ16"),
            FieldDef("LapTime17", 873, 3, description="ラップ17"),
            FieldDef("LapTime18", 876, 3, description="ラップ18"),
            FieldDef("LapTime19", 879, 3, description="ラップ19"),
            FieldDef("LapTime20", 882, 3, description="ラップ20"),
            FieldDef("LapTime21", 885, 3, description="ラップ21"),
            FieldDef("LapTime22", 888, 3, description="ラップ22"),
            FieldDef("LapTime23", 891, 3, description="ラップ23"),
            FieldDef("LapTime24", 894, 3, description="ラップ24"),
            FieldDef("LapTime25", 897, 3, description="ラップ25"),
            # コーナー通過順位 (900-)
            FieldDef("CornerInfo1", 900, 64, description="1コーナー通過順位"),
            FieldDef("CornerInfo2", 964, 64, description="2コーナー通過順位"),
            FieldDef("CornerInfo3", 1028, 64, description="3コーナー通過順位"),
            FieldDef("CornerInfo4", 1092, 64, description="4コーナー通過順位"),
            # その他 (1156-)
            FieldDef("RecordUpKubun", 1156, 1, description="レコード更新区分"),
            # Additional fields can be added as needed based on specification
        ]
