"""Parser for BR record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class BRParserJRAVAN(BaseParser):
    """Parser for BR record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "BR"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("生産者コード", 11, 8, description="生産者コード"),
            FieldDef("生産者名(法人格有)", 19, 72, description="生産者名(法人格有)"),
            FieldDef("生産者名(法人格無)", 91, 72, description="生産者名(法人格無)"),
            FieldDef("生産者名半角ｶﾅ", 163, 72, description="生産者名半角ｶﾅ"),
            FieldDef("生産者名欧字", 235, 168, description="生産者名欧字"),
            FieldDef("生産者住所自治省名", 403, 20, description="生産者住所自治省名"),
            FieldDef("<本年･累計成績情報>", 423, 60, description="<本年･累計成績情報>"),
            FieldDef("RecordDelimiter", 543, 2, description="レコード区切"),
        ]
