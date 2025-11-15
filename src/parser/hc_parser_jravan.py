"""Parser for HC record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HCParserJRAVAN(BaseParser):
    """Parser for HC record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "HC"

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
            FieldDef("4ハロンタイム合計(800M～0M)", 34, 4, description="4ハロンタイム合計(800M～0M)"),
            FieldDef("LapTime(800M～600M)", 38, 3, description="ラップタイム(800M～600M)"),
            FieldDef("3ハロンタイム合計(600M～0M)", 41, 4, description="3ハロンタイム合計(600M～0M)"),
            FieldDef("LapTime(600M～400M)", 45, 3, description="ラップタイム(600M～400M)"),
            FieldDef("2ハロンタイム合計(400M～0M)", 48, 4, description="2ハロンタイム合計(400M～0M)"),
            FieldDef("LapTime(400M～200M)", 52, 3, description="ラップタイム(400M～200M)"),
            FieldDef("LapTime(200M～0M)", 55, 3, description="ラップタイム(200M～0M)"),
            FieldDef("RecordDelimiter", 58, 2, description="レコード区切"),
        ]
