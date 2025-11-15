"""Parser for BN record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class BNParserJRAVAN(BaseParser):
    """Parser for BN record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "BN"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("BanusiCode", 11, 6, description="馬主コード"),
            FieldDef("馬主名(法人格有)", 17, 64, description="馬主名(法人格有)"),
            FieldDef("馬主名(法人格無)", 81, 64, description="馬主名(法人格無)"),
            FieldDef("馬主名半角ｶﾅ", 145, 50, description="馬主名半角ｶﾅ"),
            FieldDef("馬主名欧字", 195, 100, description="馬主名欧字"),
            FieldDef("Fukusyoku", 295, 60, description="服色標示"),
            FieldDef("<本年･累計成績情報>", 355, 60, description="<本年･累計成績情報>"),
            FieldDef("RecordDelimiter", 475, 2, description="レコード区切"),
        ]
