"""Parser for RT_RC record - Jockey Change Information (Real-time).

RT_RC: リアルタイム騎手変更情報
This is different from NL_RC which is course record information.
0B41 is official historical odds time-series, not jockey change data.
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class RTRCParser(BaseParser):
    """Parser for RT_RC record - Real-time Jockey Change Information.

    Record Type: RC (Real-time)
    Total record length: 109 bytes
    Fields: 15

    Note: RT_RC is jockey change information (騎手変更情報) for real-time data.
    This is different from NL_RC which is course record information (コースレコード).
    """

    record_type = "RC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions for RT_RC record.

        Field structure for realtime jockey-change records:
        - RecordSpec (2): Record type "RC"
        - DataKubun (1): Data classification
        - MakeDate (8): Data creation date (YYYYMMDD)
        - Year (4): Year of race
        - MonthDay (4): Month and day (MMDD)
        - JyoCD (2): Venue code
        - Kaiji (2): Meeting number
        - Nichiji (2): Day number
        - RaceNum (2): Race number
        - Umaban (2): Horse number
        - KisyuCode (5): New jockey code
        - KisyuName (34): New jockey name
        - MaeKisyuCode (5): Previous jockey code
        - MaeKisyuName (34): Previous jockey name
        - HenkouJiyuCD (2): Change reason code

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2),
            FieldDef("DataKubun", 2, 1),
            FieldDef("MakeDate", 3, 8, convert_type="DATE"),
            FieldDef("Year", 11, 4),  # TEXT in schema
            FieldDef("MonthDay", 15, 4),  # TEXT in schema
            FieldDef("JyoCD", 19, 2),
            FieldDef("Kaiji", 21, 2),  # TEXT in schema
            FieldDef("Nichiji", 23, 2),  # TEXT in schema
            FieldDef("RaceNum", 25, 2),  # TEXT in schema
            FieldDef("Umaban", 27, 2),  # TEXT in schema
            FieldDef("KisyuCode", 29, 5),
            FieldDef("KisyuName", 34, 34),
            FieldDef("MaeKisyuCode", 68, 5),
            FieldDef("MaeKisyuName", 73, 34),
            FieldDef("HenkouJiyuCD", 107, 2),
        ]
