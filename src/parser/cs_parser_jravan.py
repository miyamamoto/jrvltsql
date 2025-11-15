"""Parser for CS record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class CSParserJRAVAN(BaseParser):
    """Parser for CS record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "CS"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("JyoCD", 11, 2, description="競馬場コード"),
            FieldDef("Kyori", 13, 4, convert_type="SMALLINT", description="距離"),
            FieldDef("TrackCD", 17, 2, description="トラックコード"),
            FieldDef("コース改修年月日", 19, 8, description="コース改修年月日"),
            FieldDef("コース説明", 27, 6800, description="コース説明"),
            FieldDef("RecordDelimiter", 6827, 2, description="レコード区切"),
        ]
