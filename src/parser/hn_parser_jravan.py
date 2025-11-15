"""Parser for HN record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HNParserJRAVAN(BaseParser):
    """Parser for HN record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "HN"

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
            FieldDef("予備", 21, 8, description="予備"),
            FieldDef("KettoNum", 29, 10, description="血統登録番号"),
            FieldDef("予備", 39, 1, description="予備"),
            FieldDef("Bamei", 40, 36, description="馬名"),
            FieldDef("馬名半角ｶﾅ", 76, 40, description="馬名半角ｶﾅ"),
            FieldDef("馬名欧字", 116, 80, description="馬名欧字"),
            FieldDef("生年", 196, 4, description="生年"),
            FieldDef("SexCD", 200, 1, description="性別コード"),
            FieldDef("HinsyuCD", 201, 1, description="品種コード"),
            FieldDef("KeiroCD", 202, 2, description="毛色コード"),
            FieldDef("繁殖馬持込区分", 204, 1, description="繁殖馬持込区分"),
            FieldDef("輸入年", 205, 4, description="輸入年"),
            FieldDef("産地名", 209, 20, description="産地名"),
            FieldDef("父馬繁殖登録番号", 229, 10, description="父馬繁殖登録番号"),
            FieldDef("母馬繁殖登録番号", 239, 10, description="母馬繁殖登録番号"),
            FieldDef("RecordDelimiter", 249, 2, description="レコード区切"),
        ]
