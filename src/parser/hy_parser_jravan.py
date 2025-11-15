"""Parser for HY record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HYParserJRAVAN(BaseParser):
    """Parser for HY record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "HY"

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
            FieldDef("Bamei", 21, 36, description="馬名"),
            FieldDef("馬名の意味由来", 57, 64, description="馬名の意味由来"),
            FieldDef("RecordDelimiter", 121, 2, description="レコード区切"),
        ]
