"""Parser for HC record - hill training (HANRO) data."""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HCParser(BaseParser):
    """Parser for HC hill training records.

    HC is returned by the SLOP data spec and corresponds to JRA-VAN's
    HANRO table. The record contains hill training timestamps and furlong
    split times, not trainer master/statistics fields.
    """

    RECORD_TYPE = "HC"
    RECORD_LENGTH = 60
    record_type = "HC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names."""
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, description="データ作成年月日"),
            FieldDef("TresenKubun", 11, 1, description="トレセン区分"),
            FieldDef("ChokyoDate", 12, 8, description="調教年月日"),
            FieldDef("ChokyoTime", 20, 4, description="調教時刻"),
            FieldDef("KettoNum", 24, 10, description="血統登録番号"),
            FieldDef("HaronTime4", 34, 4, description="4ハロンタイム合計(800M～0M)"),
            FieldDef("LapTime4", 38, 3, description="ラップタイム(800M～600M)"),
            FieldDef("HaronTime3", 41, 4, description="3ハロンタイム合計(600M～0M)"),
            FieldDef("LapTime3", 45, 3, description="ラップタイム(600M～400M)"),
            FieldDef("HaronTime2", 48, 4, description="2ハロンタイム合計(400M～0M)"),
            FieldDef("LapTime2", 52, 3, description="ラップタイム(400M～200M)"),
            FieldDef("LapTime1", 55, 3, description="ラップタイム(200M～0M)"),
            FieldDef("RecordDelimiter", 58, 2, description="レコード区切"),
        ]
