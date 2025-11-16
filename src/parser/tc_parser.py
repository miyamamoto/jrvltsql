"""Parser for TC record - Generated from reference schema.

This parser uses correct field positions calculated from schema field lengths.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class TCParser(BaseParser):
    """Parser for TC record with accurate field positions.

    Total record length: 43 bytes
    Fields: 14
    """

    record_type = "TC"

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
            FieldDef("AtoJi", 35, 2),
            FieldDef("AtoFun", 37, 2),
            FieldDef("MaeJi", 39, 2),
            FieldDef("MaeFun", 41, 2),
        ]
