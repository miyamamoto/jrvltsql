"""Parser for WH record - Generated from reference schema.

This parser uses correct field positions calculated from schema field lengths.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class WHParser(BaseParser):
    """Parser for WH record with accurate field positions.

    Total record length: 40 bytes
    Fields: 16
    """

    record_type = "WH"

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
            FieldDef("HappyoTime", 25, 8, convert_type="TIME"),
            FieldDef("HenkoID", 33, 1),
            FieldDef("AtoTenkoCD", 34, 1),
            FieldDef("AtoSibaBabaCD", 35, 1),
            FieldDef("AtoDirtBabaCD", 36, 1),
            FieldDef("MaeTenkoCD", 37, 1),
            FieldDef("MaeSibaBabaCD", 38, 1),
            FieldDef("MaeDirtBabaCD", 39, 1),
        ]
