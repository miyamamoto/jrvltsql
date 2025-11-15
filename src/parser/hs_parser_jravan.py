"""Parser for HS record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class HSParserJRAVAN(BaseParser):
    """Parser for HS record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "HS"

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
            FieldDef("父馬_繁殖登録番号", 21, 10, description="父馬 繁殖登録番号"),
            FieldDef("母馬_繁殖登録番号", 31, 10, description="母馬 繁殖登録番号"),
            FieldDef("生年", 41, 4, description="生年"),
            FieldDef("主催者・市場コード", 45, 6, description="主催者・市場コード"),
            FieldDef("主催者名称", 51, 40, description="主催者名称"),
            FieldDef("市場の名称", 91, 80, description="市場の名称"),
            FieldDef("市場の開催期間(開始日)", 171, 8, description="市場の開催期間(開始日)"),
            FieldDef("市場の開催期間(終了日)", 179, 8, description="市場の開催期間(終了日)"),
            FieldDef("取引時の競走馬の年齢", 187, 1, description="取引時の競走馬の年齢"),
            FieldDef("取引価格", 188, 10, description="取引価格"),
            FieldDef("RecordDelimiter", 198, 2, description="レコード区切"),
        ]
