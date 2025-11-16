"""Parser for WC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class WCParser(BaseParser):
    """Parser for WC record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "WC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("TresenKubun", 11, 1, description="トレセン区分"),
            FieldDef("ChokyoDate", 12, 8, description="調教年月日"),
            FieldDef("ChokyoTime", 20, 4, description="調教時刻"),
            FieldDef("KettoNum", 24, 10, description="血統登録番号"),
            FieldDef("Course", 34, 1, description="コース"),
            FieldDef("BabaMawari", 35, 1, description="馬場周り"),
            FieldDef("reserved", 36, 1, description="予備"),
            FieldDef("HaronTime10Total", 37, 4, description="10ハロンタイム合計(2000M～0M)"),
            FieldDef("LapTime_2000M_1800M", 41, 3, description="ラップタイム(2000M～1800M)"),
            FieldDef("HaronTime9Total", 44, 4, description="9ハロンタイム合計(1800M～0M)"),
            FieldDef("LapTime_1800M_1600M", 48, 3, description="ラップタイム(1800M～1600M)"),
            FieldDef("HaronTime8Total", 51, 4, description="8ロンタイム合計(1600M～0M)"),
            FieldDef("LapTime_1600M_1400M", 55, 3, description="ラップタイム(1600M～1400M)"),
            FieldDef("HaronTime7Total", 58, 4, description="7ハロンタイム合計(1400M～0M)"),
            FieldDef("LapTime_1400M_1200M", 62, 3, description="ラップタイム(1400M～1200M)"),
            FieldDef("HaronTime6Total", 65, 4, description="6ハロンタイム合計(1200M～0M)"),
            FieldDef("LapTime_1200M_1000M", 69, 3, description="ラップタイム(1200M～1000M)"),
            FieldDef("HaronTime5Total", 72, 4, description="5ハロンタイム合計(1000M～0M)"),
            FieldDef("LapTime_1000M_800M", 76, 3, description="ラップタイム(1000M～800M)"),
            FieldDef("HaronTime4Total", 79, 4, description="4ハロンタイム合計(800M～0M)"),
            FieldDef("LapTime_800M_600M", 83, 3, description="ラップタイム(800M～600M)"),
            FieldDef("HaronTime3Total", 86, 4, description="3ハロンタイム合計(600M～0M)"),
            FieldDef("LapTime_600M_400M", 90, 3, description="ラップタイム(600M～400M)"),
            FieldDef("HaronTime2Total", 93, 4, description="2ハロンタイム合計(400M～0M)"),
            FieldDef("LapTime_400M_200M", 97, 3, description="ラップタイム(400M～200M)"),
            FieldDef("LapTime_200M_0M", 100, 3, description="ラップタイム(200M～0M)"),
            FieldDef("RecordDelimiter", 103, 2, description="レコード区切"),
        ]
