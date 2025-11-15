"""Parser for BT record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class BTParserJRAVAN(BaseParser):
    """Parser for BT record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "BT"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("繁殖登録番号", 11, 10, description="繁殖登録番号"),
            FieldDef("系統ID", 21, 30, description="系統ID"),
            FieldDef("系統名", 51, 36, description="系統名"),
            FieldDef("系統説明", 87, 6800, description="系統説明"),
            FieldDef("RecordDelimiter", 6887, 2, description="レコード区切"),
        ]
