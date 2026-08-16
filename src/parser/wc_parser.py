"""Parser for the official current 105-byte WC woodchip-training record.

The layout is pinned to JV-Data 4.9.0.1 and SDK 5.0.0 ``JV_WC_WOOD``.
JV-Data 4.7.0.1 added availability notes but did not change this layout.
"""

from src.parser.base import BaseParser, FieldDef
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WCParser(BaseParser):
    """Parse every field and reject malformed current WC physical records."""

    record_type = "WC"
    RECORD_LENGTH = 105
    DATA_KUBUN_VALUES = frozenset({"0", "1"})
    TRESEN_KUBUN_VALUES = frozenset({"0", "1"})
    COURSE_VALUES = frozenset({"0", "1", "2", "3", "4"})
    BABA_MAWARI_VALUES = frozenset({"0", "1"})
    KEY_FIXED_FIELDS = (
        ("MakeDate", 8),
        ("ChokyoDate", 8),
        ("ChokyoTime", 4),
        ("KettoNum", 10),
    )
    TIME_FIXED_FIELDS = (
        ("HaronTime10Total", 4),
        ("LapTime_2000M_1800M", 3),
        ("HaronTime9Total", 4),
        ("LapTime_1800M_1600M", 3),
        ("HaronTime8Total", 4),
        ("LapTime_1600M_1400M", 3),
        ("HaronTime7Total", 4),
        ("LapTime_1400M_1200M", 3),
        ("HaronTime6Total", 4),
        ("LapTime_1200M_1000M", 3),
        ("HaronTime5Total", 4),
        ("LapTime_1000M_800M", 3),
        ("HaronTime4Total", 4),
        ("LapTime_800M_600M", 3),
        ("HaronTime3Total", 4),
        ("LapTime_600M_400M", 3),
        ("HaronTime2Total", 4),
        ("LapTime_400M_200M", 3),
        ("LapTime_200M_0M", 3),
    )

    @staticmethod
    def _require_ascii_digits(name: str, value: object, width: int) -> None:
        if (
            not isinstance(value, str)
            or len(value) != width
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"WC {name} must be exactly {width} ASCII digits")

    def parse(self, record: bytes) -> dict[str, str] | None:
        """Return a validated current WC row, or ``None`` for invalid input."""
        try:
            result = super().parse(record)
            # CRLF is a structural field. BaseParser strips it to None after the
            # fixed-record validator has already proved the exact bytes.
            result["RecordDelimiter"] = ""
            data_kubun = result["DataKubun"]
            if data_kubun not in self.DATA_KUBUN_VALUES:
                raise ValueError("WC DataKubun must be 0 or 1")
            for name, width in self.KEY_FIXED_FIELDS:
                self._require_ascii_digits(name, result[name], width)
            if result["TresenKubun"] not in self.TRESEN_KUBUN_VALUES:
                raise ValueError("WC TresenKubun must be 0 or 1")

            # A status-0 row is an exact-key delete instruction. The provider
            # does not require its unused body to be blank, so do not interpret
            # or reject that body beyond the physical CP932/CRLF boundary.
            if data_kubun == "1":
                if result["Course"] not in self.COURSE_VALUES:
                    raise ValueError("WC Course must be in 0..4")
                if result["BabaMawari"] not in self.BABA_MAWARI_VALUES:
                    raise ValueError("WC BabaMawari must be 0 or 1")
                for name, width in self.TIME_FIXED_FIELDS:
                    self._require_ascii_digits(name, result[name], width)
            return result
        except Exception as error:
            logger.error(f"WC record parse failed: {error}")
            return None

    def _define_fields(self) -> list[FieldDef]:
        """Define field positions with JRA-VAN standard names and types.

        Returns:
            List of FieldDef objects with type conversion settings
        """
        return [
            FieldDef("RecordSpec", 0, 2, description="レコード種別ID"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, description="データ作成年月日"),
            FieldDef("TresenKubun", 11, 1, description="トレセン区分"),
            FieldDef("ChokyoDate", 12, 8, description="調教年月日"),
            FieldDef("ChokyoTime", 20, 4, description="調教時刻"),
            FieldDef("KettoNum", 24, 10, description="血統登録番号"),
            FieldDef("Course", 34, 1, description="コース"),
            FieldDef("BabaMawari", 35, 1, description="馬場周り"),
            FieldDef("reserved", 36, 1, description="予備"),
            FieldDef("HaronTime10Total", 37, 4, description="10ハロンタイム合計(2000M～0M)"),
            FieldDef("LapTime_2000M_1800M", 41, 3, description="ラップタイム(2000M～1800M)"),
            FieldDef("HaronTime9Total", 44, 4, description="9ハロンタイム合計(1800M～0M)"),
            FieldDef("LapTime_1800M_1600M", 48, 3, description="ラップタイム(1800M～1600M)"),
            FieldDef("HaronTime8Total", 51, 4, description="8ロンタイム合計(1600M～0M)"),
            FieldDef("LapTime_1600M_1400M", 55, 3, description="ラップタイム(1600M～1400M)"),
            FieldDef("HaronTime7Total", 58, 4, description="7ハロンタイム合計(1400M～0M)"),
            FieldDef("LapTime_1400M_1200M", 62, 3, description="ラップタイム(1400M～1200M)"),
            FieldDef("HaronTime6Total", 65, 4, description="6ハロンタイム合計(1200M～0M)"),
            FieldDef("LapTime_1200M_1000M", 69, 3, description="ラップタイム(1200M～1000M)"),
            FieldDef("HaronTime5Total", 72, 4, description="5ハロンタイム合計(1000M～0M)"),
            FieldDef("LapTime_1000M_800M", 76, 3, description="ラップタイム(1000M～800M)"),
            FieldDef("HaronTime4Total", 79, 4, description="4ハロンタイム合計(800M～0M)"),
            FieldDef("LapTime_800M_600M", 83, 3, description="ラップタイム(800M～600M)"),
            FieldDef("HaronTime3Total", 86, 4, description="3ハロンタイム合計(600M～0M)"),
            FieldDef("LapTime_600M_400M", 90, 3, description="ラップタイム(600M～400M)"),
            FieldDef("HaronTime2Total", 93, 4, description="2ハロンタイム合計(400M～0M)"),
            FieldDef("LapTime_400M_200M", 97, 3, description="ラップタイム(400M～200M)"),
            FieldDef("LapTime_200M_0M", 100, 3, description="ラップタイム(200M～0M)"),
            FieldDef("RecordDelimiter", 103, 2, description="レコード区切"),
        ]
