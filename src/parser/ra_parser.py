#!/usr/bin/env python
"""Parser for the official 1,272-byte JV-Data RA race-detail record."""

from src.jvlink.constants import ENCODING_JVDATA
from src.utils.logger import get_logger


class RAParser:
    """Parse one complete current RA record without dropping repeated fields."""

    RECORD_TYPE = "RA"
    RECORD_LENGTH = 1272

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """Strictly decode one byte-sliced CP932 field and trim padding."""
        return data.decode(ENCODING_JVDATA).strip()

    @staticmethod
    def decode_corner_order(data: bytes) -> str:
        """Decode corner order while preserving the official leading marker."""
        return data.decode(ENCODING_JVDATA).rstrip(" ")

    def parse(self, data: bytes) -> dict[str, str] | None:
        """Return a complete RA field dictionary, or ``None`` when invalid."""
        try:
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    "RA record length mismatch: "
                    f"expected={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None
            if data[:2] != self.RECORD_TYPE.encode("ascii"):
                self.logger.warning("RA record type mismatch")
                return None
            if data[-2:] != b"\r\n":
                self.logger.warning("RA record delimiter mismatch: expected CR/LF")
                return None

            result: dict[str, str] = {}
            result["RecordSpec"] = self.decode_field(data[0:2])
            result["DataKubun"] = self.decode_field(data[2:3])
            result["MakeDate"] = self.decode_field(data[3:11])
            result["Year"] = self.decode_field(data[11:15])
            result["MonthDay"] = self.decode_field(data[15:19])
            result["JyoCD"] = self.decode_field(data[19:21])
            result["Kaiji"] = self.decode_field(data[21:23])
            result["Nichiji"] = self.decode_field(data[23:25])
            result["RaceNum"] = self.decode_field(data[25:27])
            result["YoubiCD"] = self.decode_field(data[27:28])
            result["TokuNum"] = self.decode_field(data[28:32])
            result["Hondai"] = self.decode_field(data[32:92])
            result["Fukudai"] = self.decode_field(data[92:152])
            result["Kakko"] = self.decode_field(data[152:212])
            result["HondaiEng"] = self.decode_field(data[212:332])
            result["FukudaiEng"] = self.decode_field(data[332:452])
            result["KakkoEng"] = self.decode_field(data[452:572])
            result["Ryakusyo10"] = self.decode_field(data[572:592])
            result["Ryakusyo6"] = self.decode_field(data[592:604])
            result["Ryakusyo3"] = self.decode_field(data[604:610])
            result["Kubun"] = self.decode_field(data[610:611])
            result["Nkai"] = self.decode_field(data[611:614])
            result["GradeCD"] = self.decode_field(data[614:615])
            result["GradeCDBefore"] = self.decode_field(data[615:616])
            result["SyubetuCD"] = self.decode_field(data[616:618])
            result["KigoCD"] = self.decode_field(data[618:621])
            result["JyuryoCD"] = self.decode_field(data[621:622])
            result["JyokenCD1"] = self.decode_field(data[622:625])
            result["JyokenCD2"] = self.decode_field(data[625:628])
            result["JyokenCD3"] = self.decode_field(data[628:631])
            result["JyokenCD4"] = self.decode_field(data[631:634])
            result["JyokenCD5"] = self.decode_field(data[634:637])
            result["JyokenName"] = self.decode_field(data[637:697])
            result["Kyori"] = self.decode_field(data[697:701])
            result["KyoriBefore"] = self.decode_field(data[701:705])
            result["TrackCD"] = self.decode_field(data[705:707])
            result["TrackCDBefore"] = self.decode_field(data[707:709])
            result["CourseKubunCD"] = self.decode_field(data[709:711])
            result["CourseKubunCDBefore"] = self.decode_field(data[711:713])

            result["Honsyokin1"] = self.decode_field(data[713:721])
            result["Honsyokin2"] = self.decode_field(data[721:729])
            result["Honsyokin3"] = self.decode_field(data[729:737])
            result["Honsyokin4"] = self.decode_field(data[737:745])
            result["Honsyokin5"] = self.decode_field(data[745:753])
            result["Honsyokin6"] = self.decode_field(data[753:761])
            result["Honsyokin7"] = self.decode_field(data[761:769])
            result["HonsyokinBefore1"] = self.decode_field(data[769:777])
            result["HonsyokinBefore2"] = self.decode_field(data[777:785])
            result["HonsyokinBefore3"] = self.decode_field(data[785:793])
            result["HonsyokinBefore4"] = self.decode_field(data[793:801])
            result["HonsyokinBefore5"] = self.decode_field(data[801:809])
            result["Fukasyokin1"] = self.decode_field(data[809:817])
            result["Fukasyokin2"] = self.decode_field(data[817:825])
            result["Fukasyokin3"] = self.decode_field(data[825:833])
            result["Fukasyokin4"] = self.decode_field(data[833:841])
            result["Fukasyokin5"] = self.decode_field(data[841:849])
            result["FukasyokinBefore1"] = self.decode_field(data[849:857])
            result["FukasyokinBefore2"] = self.decode_field(data[857:865])
            result["FukasyokinBefore3"] = self.decode_field(data[865:873])

            result["HassoTime"] = self.decode_field(data[873:877])
            result["HassoTimeBefore"] = self.decode_field(data[877:881])
            result["TorokuTosu"] = self.decode_field(data[881:883])
            result["SyussoTosu"] = self.decode_field(data[883:885])
            result["NyusenTosu"] = self.decode_field(data[885:887])
            result["TenkoCD"] = self.decode_field(data[887:888])
            result["SibaBabaCD"] = self.decode_field(data[888:889])
            result["DirtBabaCD"] = self.decode_field(data[889:890])

            result["LapTime1"] = self.decode_field(data[890:893])
            result["LapTime2"] = self.decode_field(data[893:896])
            result["LapTime3"] = self.decode_field(data[896:899])
            result["LapTime4"] = self.decode_field(data[899:902])
            result["LapTime5"] = self.decode_field(data[902:905])
            result["LapTime6"] = self.decode_field(data[905:908])
            result["LapTime7"] = self.decode_field(data[908:911])
            result["LapTime8"] = self.decode_field(data[911:914])
            result["LapTime9"] = self.decode_field(data[914:917])
            result["LapTime10"] = self.decode_field(data[917:920])
            result["LapTime11"] = self.decode_field(data[920:923])
            result["LapTime12"] = self.decode_field(data[923:926])
            result["LapTime13"] = self.decode_field(data[926:929])
            result["LapTime14"] = self.decode_field(data[929:932])
            result["LapTime15"] = self.decode_field(data[932:935])
            result["LapTime16"] = self.decode_field(data[935:938])
            result["LapTime17"] = self.decode_field(data[938:941])
            result["LapTime18"] = self.decode_field(data[941:944])
            result["LapTime19"] = self.decode_field(data[944:947])
            result["LapTime20"] = self.decode_field(data[947:950])
            result["LapTime21"] = self.decode_field(data[950:953])
            result["LapTime22"] = self.decode_field(data[953:956])
            result["LapTime23"] = self.decode_field(data[956:959])
            result["LapTime24"] = self.decode_field(data[959:962])
            result["LapTime25"] = self.decode_field(data[962:965])
            result["SyogaiMileTime"] = self.decode_field(data[965:969])
            result["HaronTimeS3"] = self.decode_field(data[969:972])
            result["HaronTimeS4"] = self.decode_field(data[972:975])
            result["HaronTimeL3"] = self.decode_field(data[975:978])
            result["HaronTimeL4"] = self.decode_field(data[978:981])

            result["Corner1"] = self.decode_field(data[981:982])
            result["Syukaisu1"] = self.decode_field(data[982:983])
            result["Jyuni1"] = self.decode_corner_order(data[983:1053])
            result["Corner2"] = self.decode_field(data[1053:1054])
            result["Syukaisu2"] = self.decode_field(data[1054:1055])
            result["Jyuni2"] = self.decode_corner_order(data[1055:1125])
            result["Corner3"] = self.decode_field(data[1125:1126])
            result["Syukaisu3"] = self.decode_field(data[1126:1127])
            result["Jyuni3"] = self.decode_corner_order(data[1127:1197])
            result["Corner4"] = self.decode_field(data[1197:1198])
            result["Syukaisu4"] = self.decode_field(data[1198:1199])
            result["Jyuni4"] = self.decode_corner_order(data[1199:1269])
            result["RecordUpKubun"] = self.decode_field(data[1269:1270])
            result["Crlf"] = self.decode_field(data[1270:1272])

            # Backward-compatible names used by the native schema and callers.
            result["LapTime"] = result["LapTime1"]
            result["Haron3F"] = result["HaronTimeS3"]
            result["Haron4F"] = result["HaronTimeS4"]
            result["Haron3L"] = result["HaronTimeL3"]
            result["Haron4L"] = result["HaronTimeL4"]
            result["Corner"] = result["Corner1"]
            result["Syukaisu"] = result["Syukaisu1"]
            result["TsukaJyuni"] = result["Jyuni1"]
            result["TsukaJyuni2"] = result["Jyuni2"]
            result["TsukaJyuni3"] = result["Jyuni3"]
            result["TsukaJyuni4"] = result["Jyuni4"]
            return result
        except Exception as exc:
            self.logger.error(f"RA record parse failed: {exc}")
            return None
