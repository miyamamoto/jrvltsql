#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UMレコードパーサー: １３．競走馬マスタ

このファイルはJV-Data仕様書 Ver.4.9.0.1に基づいて修正されました。
"""

from typing import Dict, Optional

from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class UMParser:
    """
    UMレコードパーサー

    １３．競走馬マスタ
    レコード長: 1609 bytes (JV-Data仕様書 Ver.4.9.0.1「フォーマット」シート)
    VBテーブル名: UMA
    """

    RECORD_TYPE = "UM"
    RECORD_LENGTH = 1609

    # 項番63 レコード区切の位置。レコード全体が仕様どおりに並んでいるかを
    # 1 箇所で検算するために使う（ここが CR/LF なら手前の全項目が正しく閉じている）
    RECORD_DELIMITER_START = 1607

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
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            # レコード長チェック: 仕様の 1609 バイト以外は取り込まない。
            # 旧仕様（1577 バイト等）のレコードを部分抽出すると、壊れた
            # 競走馬マスタ行が黙って保存されてしまうため None で拒否する。
            if len(data) != self.RECORD_LENGTH:
                self.logger.warning(
                    f"UMレコード長不正: expected={self.RECORD_LENGTH}, "
                    f"actual={len(data)}. 仕様世代の異なるレコードの可能性があるため破棄"
                )
                return None

            # レイアウト検算: 項番63 レコード区切が CRLF かを見る。
            # 仕様世代がずれたレコードを掴んでいると、ここが CRLF にならない
            # （旧仕様1577バイトのレコードを本パーサで読むと、この位置は着回数の途中）。
            delimiter = data[self.RECORD_DELIMITER_START:self.RECORD_LENGTH]
            if delimiter != b"\r\n":
                self.logger.warning(
                    "UMレコードのレコード区切が CRLF ではない: "
                    f"pos={self.RECORD_DELIMITER_START} actual={delimiter!r}. "
                    "仕様世代の異なるレコードの可能性があるため破棄"
                )
                return None

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

            # 18. <3代血統情報> (位置:205, 繰返:14, 長さ:46 = 合計 644)
            # 各血統情報: 繁殖登録番号(10) + 馬名(36) = 46バイト
            # 1=父, 2=母, 3=父父, 4=父母, 5=母父, 6=母母, 7-14=曾祖父母
            ketto_pos = 204
            for i in range(1, 15):
                result[f"Ketto3InfoHansyokuNum{i}"] = self.decode_field(data[ketto_pos:ketto_pos+10])
                result[f"Ketto3InfoBamei{i}"] = self.decode_field(data[ketto_pos+10:ketto_pos+46])
                ketto_pos += 46

            # 19. 東西所属コード (位置:849, 長さ:1)
            result["TozaiCD"] = self.decode_field(data[848:849])

            # 20. 調教師コード (位置:850, 長さ:5)
            result["ChokyosiCode"] = self.decode_field(data[849:854])

            # 21. 調教師名略称 (位置:855, 長さ:8)
            result["ChokyosiRyakusyo"] = self.decode_field(data[854:862])

            # 22. 招待地域名 (位置:863, 長さ:20)
            result["Syotai"] = self.decode_field(data[862:882])

            # 23. 生産者コード (位置:883, 長さ:8)
            result["BreederCode"] = self.decode_field(data[882:890])

            # 24. 生産者名(法人格無) (位置:891, 長さ:72)
            result["BreederName"] = self.decode_field(data[890:962])

            # 25. 産地名 (位置:963, 長さ:20)
            result["SanchiName"] = self.decode_field(data[962:982])

            # 26. 馬主コード (位置:983, 長さ:6)
            result["BanusiCode"] = self.decode_field(data[982:988])

            # 27. 馬主名(法人格無) (位置:989, 長さ:64)
            result["BanusiName"] = self.decode_field(data[988:1052])

            # 28. 平地本賞金累計 (位置:1053, 長さ:9)
            result["RuikeiHonsyoHeiti"] = self.decode_field(data[1052:1061])

            # 29. 障害本賞金累計 (位置:1062, 長さ:9)
            result["RuikeiHonsyoSyogai"] = self.decode_field(data[1061:1070])

            # 30. 平地付加賞金累計 (位置:1071, 長さ:9)
            result["RuikeiFukaHeichi"] = self.decode_field(data[1070:1079])

            # 31. 障害付加賞金累計 (位置:1080, 長さ:9)
            result["RuikeiFukaSyogai"] = self.decode_field(data[1079:1088])

            # 32. 平地収得賞金累計 (位置:1089, 長さ:9)
            result["RuikeiSyutokuHeichi"] = self.decode_field(data[1088:1097])

            # 33. 障害収得賞金累計 (位置:1098, 長さ:9)
            result["RuikeiSyutokuSyogai"] = self.decode_field(data[1097:1106])

            # 34-60. 着回数
            # 各項目は 3バイト × 繰返6（1着/2着/3着/4着/5着/着外）＝ 18バイト。
            # PC-KEIBA5 の jvd_um と同じく 18バイトのまま 1 列に保持する
            # （6個に割ると突合のたびに連結し直すことになるため）。
            # 34. 総合着回数 (位置:1107, 繰返:6, 長さ:3 = 18)
            result["SogoChaku"] = self.decode_field(data[1106:1124])

            # 35. 中央合計着回数 (位置:1125, 繰返:6, 長さ:3 = 18)
            result["ChuoGokeiChaku"] = self.decode_field(data[1124:1142])

            # <馬場別着回数>
            # 36. 芝直・着回数 (位置:1143, 繰返:6, 長さ:3 = 18)
            result["SibaChokuChaku"] = self.decode_field(data[1142:1160])

            # 37. 芝右・着回数 (位置:1161, 繰返:6, 長さ:3 = 18)
            result["SibaMigiChaku"] = self.decode_field(data[1160:1178])

            # 38. 芝左・着回数 (位置:1179, 繰返:6, 長さ:3 = 18)
            result["SibaHidariChaku"] = self.decode_field(data[1178:1196])

            # 39. ダ直・着回数 (位置:1197, 繰返:6, 長さ:3 = 18)
            result["DirtChokuChaku"] = self.decode_field(data[1196:1214])

            # 40. ダ右・着回数 (位置:1215, 繰返:6, 長さ:3 = 18)
            result["DirtMigiChaku"] = self.decode_field(data[1214:1232])

            # 41. ダ左・着回数 (位置:1233, 繰返:6, 長さ:3 = 18)
            result["DirtHidariChaku"] = self.decode_field(data[1232:1250])

            # 42. 障害・着回数 (位置:1251, 繰返:6, 長さ:3 = 18)
            result["SyogaiChaku"] = self.decode_field(data[1250:1268])

            # <馬場状態別着回数>
            # 43. 芝良・着回数 (位置:1269, 繰返:6, 長さ:3 = 18)
            result["SibaRyoChaku"] = self.decode_field(data[1268:1286])

            # 44. 芝稍・着回数 (位置:1287, 繰返:6, 長さ:3 = 18)
            result["SibaYayaomoChaku"] = self.decode_field(data[1286:1304])

            # 45. 芝重・着回数 (位置:1305, 繰返:6, 長さ:3 = 18)
            result["SibaOmoChaku"] = self.decode_field(data[1304:1322])

            # 46. 芝不・着回数 (位置:1323, 繰返:6, 長さ:3 = 18)
            result["SibaFuryoChaku"] = self.decode_field(data[1322:1340])

            # 47. ダ良・着回数 (位置:1341, 繰返:6, 長さ:3 = 18)
            result["DirtRyoChaku"] = self.decode_field(data[1340:1358])

            # 48. ダ稍・着回数 (位置:1359, 繰返:6, 長さ:3 = 18)
            result["DirtYayaomoChaku"] = self.decode_field(data[1358:1376])

            # 49. ダ重・着回数 (位置:1377, 繰返:6, 長さ:3 = 18)
            result["DirtOmoChaku"] = self.decode_field(data[1376:1394])

            # 50. ダ不・着回数 (位置:1395, 繰返:6, 長さ:3 = 18)
            result["DirtFuryoChaku"] = self.decode_field(data[1394:1412])

            # 51. 障良・着回数 (位置:1413, 繰返:6, 長さ:3 = 18)
            result["SyogaiRyoChaku"] = self.decode_field(data[1412:1430])

            # 52. 障稍・着回数 (位置:1431, 繰返:6, 長さ:3 = 18)
            result["SyogaiYayaomoChaku"] = self.decode_field(data[1430:1448])

            # 53. 障重・着回数 (位置:1449, 繰返:6, 長さ:3 = 18)
            result["SyogaiOmoChaku"] = self.decode_field(data[1448:1466])

            # 54. 障不・着回数 (位置:1467, 繰返:6, 長さ:3 = 18)
            result["SyogaiFuryoChaku"] = self.decode_field(data[1466:1484])

            # <距離別着回数>
            # 55. 芝16下・着回数 (位置:1485, 繰返:6, 長さ:3 = 18)
            result["SibaShortChaku"] = self.decode_field(data[1484:1502])

            # 56. 芝22下・着回数 (位置:1503, 繰返:6, 長さ:3 = 18)
            result["SibaMiddleChaku"] = self.decode_field(data[1502:1520])

            # 57. 芝22超・着回数 (位置:1521, 繰返:6, 長さ:3 = 18)
            result["SibaLongChaku"] = self.decode_field(data[1520:1538])

            # 58. ダ16下・着回数 (位置:1539, 繰返:6, 長さ:3 = 18)
            result["DirtShortChaku"] = self.decode_field(data[1538:1556])

            # 59. ダ22下・着回数 (位置:1557, 繰返:6, 長さ:3 = 18)
            result["DirtMiddleChaku"] = self.decode_field(data[1556:1574])

            # 60. ダ22超・着回数 (位置:1575, 繰返:6, 長さ:3 = 18)
            result["DirtLongChaku"] = self.decode_field(data[1574:1592])

            # 61. 脚質傾向 (位置:1593, 繰返:4, 長さ:3 = 12)
            result["KyakusituKeiko"] = self.decode_field(data[1592:1604])

            # 62. 登録レース数 (位置:1605, 長さ:3)
            result["TorokuRaceSu"] = self.decode_field(data[1604:1607])

            # 63. レコード区切 (位置:1608, 長さ:2)
            result["Reserved_1608"] = self.decode_field(data[1607:1609])

            return result

        except Exception as e:
            self.logger.error(f"UMレコードパース中にエラー: {e}")
            return None
