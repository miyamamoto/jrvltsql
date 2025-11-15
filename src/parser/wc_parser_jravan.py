"""Parser for WC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class WCParserJRAVAN(BaseParser):
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
            FieldDef("トレセン区分", 11, 1, description="トレセン区分"),
            FieldDef("調教年月日", 12, 8, description="調教年月日"),
            FieldDef("調教時刻", 20, 4, description="調教時刻"),
            FieldDef("KettoNum", 24, 10, description="血統登録番号"),
            FieldDef("コース", 34, 1, description="コース"),
            FieldDef("馬場周り", 35, 1, description="馬場周り"),
            FieldDef("予備", 36, 1, description="予備"),
            FieldDef("10ハロンタイム合計(2000M～0M)", 37, 4, description="10ハロンタイム合計(2000M～0M)"),
            FieldDef("LapTime(2000M～1800M)", 41, 3, description="ラップタイム(2000M～1800M)"),
            FieldDef("9ハロンタイム合計(1800M～0M)", 44, 4, description="9ハロンタイム合計(1800M～0M)"),
            FieldDef("LapTime(1800M～1600M)", 48, 3, description="ラップタイム(1800M～1600M)"),
            FieldDef("8ロンタイム合計(1600M～0M)", 51, 4, description="8ロンタイム合計(1600M～0M)"),
            FieldDef("LapTime(1600M～1400M)", 55, 3, description="ラップタイム(1600M～1400M)"),
            FieldDef("7ハロンタイム合計(1400M～0M)", 58, 4, description="7ハロンタイム合計(1400M～0M)"),
            FieldDef("LapTime(1400M～1200M)", 62, 3, description="ラップタイム(1400M～1200M)"),
            FieldDef("6ハロンタイム合計(1200M～0M)", 65, 4, description="6ハロンタイム合計(1200M～0M)"),
            FieldDef("LapTime(1200M～1000M)", 69, 3, description="ラップタイム(1200M～1000M)"),
            FieldDef("5ハロンタイム合計(1000M～0M)", 72, 4, description="5ハロンタイム合計(1000M～0M)"),
            FieldDef("LapTime(1000M～800M)", 76, 3, description="ラップタイム(1000M～800M)"),
            FieldDef("4ハロンタイム合計(800M～0M)", 79, 4, description="4ハロンタイム合計(800M～0M)"),
            FieldDef("LapTime(800M～600M)", 83, 3, description="ラップタイム(800M～600M)"),
            FieldDef("3ハロンタイム合計(600M～0M)", 86, 4, description="3ハロンタイム合計(600M～0M)"),
            FieldDef("LapTime(600M～400M)", 90, 3, description="ラップタイム(600M～400M)"),
            FieldDef("2ハロンタイム合計(400M～0M)", 93, 4, description="2ハロンタイム合計(400M～0M)"),
            FieldDef("LapTime(400M～200M)", 97, 3, description="ラップタイム(400M～200M)"),
            FieldDef("LapTime(200M～0M)", 100, 3, description="ラップタイム(200M～0M)"),
            FieldDef("RecordDelimiter", 103, 2, description="レコード区切"),
        ]
