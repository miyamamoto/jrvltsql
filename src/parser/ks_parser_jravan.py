"""Parser for KS record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class KSParserJRAVAN(BaseParser):
    """Parser for KS record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "KS"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("KisyuCode", 11, 5, description="騎手コード"),
            FieldDef("騎手抹消区分", 16, 1, description="騎手抹消区分"),
            FieldDef("騎手免許交付年月日", 17, 8, description="騎手免許交付年月日"),
            FieldDef("騎手免許抹消年月日", 25, 8, description="騎手免許抹消年月日"),
            FieldDef("生年月日", 33, 8, description="生年月日"),
            FieldDef("騎手名", 41, 34, description="騎手名"),
            FieldDef("予備", 75, 34, description="予備"),
            FieldDef("騎手名半角ｶﾅ", 109, 30, description="騎手名半角ｶﾅ"),
            FieldDef("KisyuRyakusyo", 139, 8, description="騎手名略称"),
            FieldDef("騎手名欧字", 147, 80, description="騎手名欧字"),
            FieldDef("性別区分", 227, 1, description="性別区分"),
            FieldDef("騎乗資格コード", 228, 1, description="騎乗資格コード"),
            FieldDef("騎手見習コード", 229, 1, description="騎手見習コード"),
            FieldDef("騎手東西所属コード", 230, 1, description="騎手東西所属コード"),
            FieldDef("招待地域名", 231, 20, description="招待地域名"),
            FieldDef("所属調教師コード", 251, 5, description="所属調教師コード"),
            FieldDef("所属調教師名略称", 256, 8, description="所属調教師名略称"),
            FieldDef("<初騎乗情報>", 264, 67, description="<初騎乗情報>"),
            FieldDef("<初勝利情報>", 398, 64, description="<初勝利情報>"),
            FieldDef("<最近重賞勝利情報>", 526, 163, description="<最近重賞勝利情報>"),
            FieldDef("<本年･前年･累計成績情報>", 1015, 1052, description="<本年･前年･累計成績情報>"),
            FieldDef("RecordDelimiter", 4171, 2, description="レコード区切"),
        ]
