"""Parser for JC record - Generated from reference schema.

This parser uses correct field positions calculated from schema field lengths.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class JCParser(BaseParser):
    """Parser for JC record with accurate field positions.

    Total record length: 159 bytes
    Fields: 20
    """

    record_type = "JC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions calculated from schema.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2),
            FieldDef("DataKubun", 2, 1),
            FieldDef("MakeDate", 3, 8, convert_type="DATE"),
            FieldDef("Year", 11, 4, convert_type="SMALLINT"),
            FieldDef("MonthDay", 15, 4, convert_type="MONTH_DAY"),
            FieldDef("JyoCD", 19, 2),
            FieldDef("Kaiji", 21, 2, convert_type="SMALLINT"),
            FieldDef("Nichiji", 23, 2, convert_type="SMALLINT"),
            FieldDef("RaceNum", 25, 2, convert_type="SMALLINT"),
            FieldDef("HappyoTime", 27, 8, convert_type="TIME"),
            FieldDef("Umaban", 35, 2, convert_type="SMALLINT"),
            FieldDef("Bamei", 37, 36),
            FieldDef("AtoFutan", 73, 3),
            FieldDef("AtoKisyuCode", 76, 5),
            FieldDef("AtoKisyuName", 81, 34),
            FieldDef("AtoMinaraiCD", 115, 1),
            FieldDef("MaeFutan", 116, 3),
            FieldDef("MaeKisyuCode", 119, 5),
            FieldDef("MaeKisyuName", 124, 34),
            FieldDef("MaeMinaraiCD", 158, 1),
        ]
