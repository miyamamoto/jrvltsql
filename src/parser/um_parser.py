#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UMレコードパーサー: １３．競走馬マスタ

このファイルはJV-Data仕様書 Ver.4.9.0.1に基づいて修正されました。
"""

from typing import Dict, Optional
from src.utils.logger import get_logger


class UMParser:
    """
    UMレコードパーサー

    １３．競走馬マスタ
    レコード長: 1577 bytes (JV-Data仕様書 4.5.1.2「フォーマット」シート)
    VBテーブル名: UMA
    """

    RECORD_TYPE = "UM"
    RECORD_LENGTH = 1577

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        try:
            # CP932でデコード、空白を除去
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        """
        UMレコードをパースしてフィールド辞書を返す

        Args:
            data: パース対象のバイトデータ

        Returns:
            フィールド名をキーとした辞書、エラー時はNone
        """
        try:
            # レコード長チェック (短いレコードも許容)
            if len(data) < 200:
                self.logger.warning(
                    f"UMレコード長不足: expected>={200}, actual={len(data)}"
                )

            # フィールド抽出
            result = {}

            # 1. レコード種別ID (位置:1, 長さ:2)
            result["RecordSpec"] = self.decode_field(data[0:2])

            # 2. データ区分 (位置:3, 長さ:1)
            result["DataKubun"] = self.decode_field(data[2:3])

            # 3. データ作成年月日 (位置:4, 長さ:8)
            result["MakeDate"] = self.decode_field(data[3:11])

            # 4. 血統登録番号 (位置:12, 長さ:10) - PRIMARY KEY
            result["KettoNum"] = self.decode_field(data[11:21])

            # 5. 競走馬抹消区分 (位置:22, 長さ:1)
            result["DelKubun"] = self.decode_field(data[21:22])

            # 6. 競走馬登録年月日 (位置:23, 長さ:8)
            result["RegDate"] = self.decode_field(data[22:30])

            # 7. 競走馬抹消年月日 (位置:31, 長さ:8)
            result["DelDate"] = self.decode_field(data[30:38])

            # 8. 生年月日 (位置:39, 長さ:8)
            result["BirthDate"] = self.decode_field(data[38:46])

            # 9. 馬名 (位置:47, 長さ:36)
            result["Bamei"] = self.decode_field(data[46:82])

            # 10. 馬名半角ｶﾅ (位置:83, 長さ:36)
            result["BameiKana"] = self.decode_field(data[82:118])

            # 11. 馬名欧字 (位置:119, 長さ:60)
            result["BameiEng"] = self.decode_field(data[118:178])

            # 12. JRA施設在きゅうフラグ (位置:179, 長さ:1)
            result["ZaikyuFlag"] = self.decode_field(data[178:179])

            # 13. 予備 (位置:180, 長さ:19)
            result["Reserved"] = self.decode_field(data[179:198])

            # 14. 馬記号コード (位置:199, 長さ:2)
            result["UmaKigoCD"] = self.decode_field(data[198:200])

            # 15. 性別コード (位置:201, 長さ:1)
            result["SexCD"] = self.decode_field(data[200:201])

            # 16. 品種コード (位置:202, 長さ:1)
            result["HinsyuCD"] = self.decode_field(data[201:202])

            # 17. 毛色コード (位置:203, 長さ:2)
            result["KeiroCD"] = self.decode_field(data[202:204])

            # 18. <3代血統情報> (位置:205, 繰返:14, 長さ:44 = 合計 616)
            # 各血統情報: 繁殖登録番号(8) + 馬名(36) = 44バイト
            # 1=父, 2=母, 3=父父, 4=父母, 5=母父, 6=母母, 7-14=曾祖父母
            ketto_pos = 204
            for i in range(1, 15):
                result[f"Ketto3InfoHansyokuNum{i}"] = self.decode_field(data[ketto_pos:ketto_pos+8])
                result[f"Ketto3InfoBamei{i}"] = self.decode_field(data[ketto_pos+8:ketto_pos+44])
                ketto_pos += 44

            # 19. 東西所属コード (位置:821, 長さ:1)
            result["TozaiCD"] = self.decode_field(data[820:821])

            # 20. 調教師コード (位置:822, 長さ:5)
            result["ChokyosiCode"] = self.decode_field(data[821:826])

            # 21. 調教師名略称 (位置:827, 長さ:8)
            result["ChokyosiRyakusyo"] = self.decode_field(data[826:834])

            # 22. 招待地域名 (位置:835, 長さ:20)
            result["Syotai"] = self.decode_field(data[834:854])

            # 23. 生産者コード (位置:855, 長さ:6)
            result["BreederCode"] = self.decode_field(data[854:860])

            # 24. 生産者名(法人格無) (位置:861, 長さ:70)
            result["BreederName"] = self.decode_field(data[860:930])

            # 25. 産地名 (位置:931, 長さ:20)
            result["SanchiName"] = self.decode_field(data[930:950])

            # 26. 馬主コード (位置:951, 長さ:6)
            result["BanusiCode"] = self.decode_field(data[950:956])

            # 27. 馬主名(法人格無) (位置:957, 長さ:64)
            result["BanusiName"] = self.decode_field(data[956:1020])

            # 28. 平地本賞金累計 (位置:1021, 長さ:9)
            result["RuikeiHonsyoHeiti"] = self.decode_field(data[1020:1029])

            # 29. 障害本賞金累計 (位置:1030, 長さ:9)
            result["RuikeiHonsyoSyogai"] = self.decode_field(data[1029:1038])

            # 30. 平地付加賞金累計 (位置:1039, 長さ:9)
            result["RuikeiFukaHeichi"] = self.decode_field(data[1038:1047])

            # 31. 障害付加賞金累計 (位置:1048, 長さ:9)
            result["RuikeiFukaSyogai"] = self.decode_field(data[1047:1056])

            # 32. 平地収得賞金累計 (位置:1057, 長さ:9)
            result["RuikeiSyutokuHeichi"] = self.decode_field(data[1056:1065])

            # 33. 障害収得賞金累計 (位置:1066, 長さ:9)
            result["RuikeiSyutokuSyogai"] = self.decode_field(data[1065:1074])

            # 34-60. 着回数（位置:1075-1560）
            # 各項目は 3 バイト × 繰返 6（1着/2着/3着/4着/5着/着外）＝ 18 バイト。
            # PC-KEIBA5 の jvd_um と同じく 18 バイトのまま 1 列に保持する
            # （6 個に割ると突合のたびに連結し直すことになるため）。
            # 34. 総合着回数 (位置:1075, 長さ:18)
            result["SogoChaku"] = self.decode_field(data[1074:1092])

            # 35. 中央合計着回数 (位置:1093, 長さ:18)
            result["ChuoGokeiChaku"] = self.decode_field(data[1092:1110])

            # 36. 芝直・着回数 (位置:1111, 長さ:18)
            result["SibaChokuChaku"] = self.decode_field(data[1110:1128])

            # 37. 芝右・着回数 (位置:1129, 長さ:18)
            result["SibaMigiChaku"] = self.decode_field(data[1128:1146])

            # 38. 芝左・着回数 (位置:1147, 長さ:18)
            result["SibaHidariChaku"] = self.decode_field(data[1146:1164])

            # 39. ダ直・着回数 (位置:1165, 長さ:18)
            result["DirtChokuChaku"] = self.decode_field(data[1164:1182])

            # 40. ダ右・着回数 (位置:1183, 長さ:18)
            result["DirtMigiChaku"] = self.decode_field(data[1182:1200])

            # 41. ダ左・着回数 (位置:1201, 長さ:18)
            result["DirtHidariChaku"] = self.decode_field(data[1200:1218])

            # 42. 障害・着回数 (位置:1219, 長さ:18)
            result["SyogaiChaku"] = self.decode_field(data[1218:1236])

            # 43. 芝良・着回数 (位置:1237, 長さ:18)
            result["SibaRyoChaku"] = self.decode_field(data[1236:1254])

            # 44. 芝稍・着回数 (位置:1255, 長さ:18)
            result["SibaYayaomoChaku"] = self.decode_field(data[1254:1272])

            # 45. 芝重・着回数 (位置:1273, 長さ:18)
            result["SibaOmoChaku"] = self.decode_field(data[1272:1290])

            # 46. 芝不・着回数 (位置:1291, 長さ:18)
            result["SibaFuryoChaku"] = self.decode_field(data[1290:1308])

            # 47. ダ良・着回数 (位置:1309, 長さ:18)
            result["DirtRyoChaku"] = self.decode_field(data[1308:1326])

            # 48. ダ稍・着回数 (位置:1327, 長さ:18)
            result["DirtYayaomoChaku"] = self.decode_field(data[1326:1344])

            # 49. ダ重・着回数 (位置:1345, 長さ:18)
            result["DirtOmoChaku"] = self.decode_field(data[1344:1362])

            # 50. ダ不・着回数 (位置:1363, 長さ:18)
            result["DirtFuryoChaku"] = self.decode_field(data[1362:1380])

            # 51. 障良・着回数 (位置:1381, 長さ:18)
            result["SyogaiRyoChaku"] = self.decode_field(data[1380:1398])

            # 52. 障稍・着回数 (位置:1399, 長さ:18)
            result["SyogaiYayaomoChaku"] = self.decode_field(data[1398:1416])

            # 53. 障重・着回数 (位置:1417, 長さ:18)
            result["SyogaiOmoChaku"] = self.decode_field(data[1416:1434])

            # 54. 障不・着回数 (位置:1435, 長さ:18)
            result["SyogaiFuryoChaku"] = self.decode_field(data[1434:1452])

            # 55. 芝16下・着回数 (位置:1453, 長さ:18)
            result["SibaShortChaku"] = self.decode_field(data[1452:1470])

            # 56. 芝22下・着回数 (位置:1471, 長さ:18)
            result["SibaMiddleChaku"] = self.decode_field(data[1470:1488])

            # 57. 芝22超・着回数 (位置:1489, 長さ:18)
            result["SibaLongChaku"] = self.decode_field(data[1488:1506])

            # 58. ダ16下・着回数 (位置:1507, 長さ:18)
            result["DirtShortChaku"] = self.decode_field(data[1506:1524])

            # 59. ダ22下・着回数 (位置:1525, 長さ:18)
            result["DirtMiddleChaku"] = self.decode_field(data[1524:1542])

            # 60. ダ22超・着回数 (位置:1543, 長さ:18)
            result["DirtLongChaku"] = self.decode_field(data[1542:1560])

            # 61. 脚質傾向 (位置:1561, 繰返:4, 長さ:3 = 12)
            result["KyakusituKeiko"] = self.decode_field(data[1560:1572])

            # 62. 登録レース数 (位置:1573, 長さ:3)
            result["TorokuRaceSu"] = self.decode_field(data[1572:1575])

            # 63. レコード区切 (位置:1576, 長さ:2)
            result["Reserved_1576"] = self.decode_field(data[1575:1577])

            return result

        except Exception as e:
            self.logger.error(f"UMレコードパース中にエラー: {e}")
            return None
