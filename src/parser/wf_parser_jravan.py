"""Parser for WF record - JRA-VAN Standard compliant.

This parser uses JRA-VAN standard field names and type conversions.
Auto-generated from jv_data_formats.json.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class WFParserJRAVAN(BaseParser):
    """Parser for WF record with JRA-VAN standard schema.

    Uses English/Romanized field names matching JRA-VAN standard database.
    """

    record_type = "WF"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),
            FieldDef("Year", 11, 4, convert_type="SMALLINT", description="開催年"),
            FieldDef("MonthDay", 15, 4, convert_type="MONTH_DAY", description="開催月日"),
            FieldDef("予備", 19, 2, description="予備"),
            FieldDef("<重勝式対象レース情報>", 21, 8, description="<重勝式対象レース情報>"),
            FieldDef("予備", 61, 6, description="予備"),
            FieldDef("重勝式発売票数", 67, 11, description="重勝式発売票数"),
            FieldDef("<有効票数情報>", 78, 11, description="<有効票数情報>"),
            FieldDef("返還フラグ", 133, 1, description="返還フラグ"),
            FieldDef("不成立フラグ", 134, 1, description="不成立フラグ"),
            FieldDef("的中無フラグ", 135, 1, description="的中無フラグ"),
            FieldDef("キャリーオーバー金額初期", 136, 15, description="キャリーオーバー金額初期"),
            FieldDef("キャリーオーバー金額残高", 151, 15, description="キャリーオーバー金額残高"),
            FieldDef("<重勝式払戻情報>", 166, 29, description="<重勝式払戻情報>"),
            FieldDef("RecordDelimiter", 7213, 2, description="レコード区切"),
        ]
