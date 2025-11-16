"""Parser for AV record - Generated from reference schema.

This parser uses correct field positions calculated from schema field lengths.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class AVParser(BaseParser):
    """Parser for AV record with accurate field positions.

    Total record length: 140 bytes
    Fields: 4
    """

    record_type = "AV"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions calculated from schema.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("KettoNum", 0, 10),
            FieldDef("SaleHostName", 10, 40),
            FieldDef("SaleName", 50, 80),
            FieldDef("Price", 130, 10),
        ]
