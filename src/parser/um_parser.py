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
    レコード長: 1110 bytes (実際のJV-Data仕様に基づく)
    VBテーブル名: UMA
    """

    RECORD_TYPE = "UM"
    RECORD_LENGTH = 1110  # 正しいレコード長

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        try:
            # Shift-JISでデコード、空白を除去
            return data.decode("shift-jis", errors="ignore").strip()
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

            # 18-31. <3代血統情報> (位置:205, 長さ:644 = 14 * 46)
            # 各血統情報: 繁殖登録番号(10) + 馬名(36) = 46バイト
            # 1=父, 2=母, 3=父父, 4=父母, 5=母父, 6=母母, 7-14=曾祖父母
            ketto_pos = 204
            for i in range(1, 15):
                result[f"Ketto3InfoHansyokuNum{i}"] = self.decode_field(data[ketto_pos:ketto_pos+10])
                result[f"Ketto3InfoBamei{i}"] = self.decode_field(data[ketto_pos+10:ketto_pos+46])
                ketto_pos += 46

            # 32. 東西所属コード (位置:849, 長さ:1)
            result["TozaiCD"] = self.decode_field(data[848:849])

            # 33. 調教師コード (位置:850, 長さ:5)
            result["ChokyosiCode"] = self.decode_field(data[849:854])

            # 34. 調教師名略称 (位置:855, 長さ:8)
            result["ChokyosiRyakusyo"] = self.decode_field(data[854:862])

            # 35. 招待地域名 (位置:863, 長さ:20)
            result["Syotai"] = self.decode_field(data[862:882])

            # 36. 生産者コード (位置:883, 長さ:8)
            result["BreederCode"] = self.decode_field(data[882:890])

            # 37. 生産者名(法人格無) (位置:891, 長さ:72)
            result["BreederName"] = self.decode_field(data[890:962])

            # 38. 産地名 (位置:963, 長さ:20)
            result["SanchiName"] = self.decode_field(data[962:982])

            # 39. 馬主コード (位置:983, 長さ:6)
            result["BanusiCode"] = self.decode_field(data[982:988])

            # 40. 馬主名(法人格無) (位置:989, 長さ:64)
            result["BanusiName"] = self.decode_field(data[988:1052])

            # 41. 平地本賞金累計 (位置:1053, 長さ:9)
            result["RuikeiHonsyoHeiti"] = self.decode_field(data[1052:1061])

            # 42. 障害本賞金累計 (位置:1062, 長さ:9)
            result["RuikeiHonsyoSyogai"] = self.decode_field(data[1061:1070])

            # 43. 平地付加賞金累計 (位置:1071, 長さ:9)
            result["RuikeiFukaHeichi"] = self.decode_field(data[1070:1079])

            # 44. 障害付加賞金累計 (位置:1080, 長さ:9)
            result["RuikeiFukaSyogai"] = self.decode_field(data[1079:1088])

            # 45. 平地収得賞金累計 (位置:1089, 長さ:9)
            result["RuikeiSyutokuHeichi"] = self.decode_field(data[1088:1097])

            # 46. 障害収得賞金累計 (位置:1098, 長さ:9)
            result["RuikeiSyutokuSyogai"] = self.decode_field(data[1097:1106])

            # 47. レコード区切 (位置:1107, 長さ:2)
            result["Reserved_1107"] = self.decode_field(data[1106:1108])

            return result

        except Exception as e:
            self.logger.error(f"UMレコードパース中にエラー: {e}")
            return None
