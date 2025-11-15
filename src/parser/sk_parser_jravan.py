"""Parser for SK record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class SKParserJRAVAN(BaseParser):
    """Parser for SK record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "SK"

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
            FieldDef("生年月日", 21, 8, description="生年月日"),
            FieldDef("SexCD", 29, 1, description="性別コード"),
            FieldDef("HinsyuCD", 30, 1, description="品種コード"),
            FieldDef("KeiroCD", 31, 2, description="毛色コード"),
            FieldDef("産駒持込区分", 33, 1, description="産駒持込区分"),
            FieldDef("輸入年", 34, 4, description="輸入年"),
            FieldDef("生産者コード", 38, 8, description="生産者コード"),
            FieldDef("産地名", 46, 20, description="産地名"),
            FieldDef("3代血統_繁殖登録番号", 66, 10, description="3代血統 繁殖登録番号"),
            FieldDef("RecordDelimiter", 206, 2, description="レコード区切"),
        ]
