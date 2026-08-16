#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYレコードパーサー: ２４．馬名の意味由来

Current layout verified against the official SDK 5.0.0 structure definition.
"""

from typing import Dict, Optional

from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class HYParser:
    """
    HYレコードパーサー

    ２４．馬名の意味由来
    レコード長: 123 bytes
    VBテーブル名: BAMEIORIGIN
    """

    RECORD_TYPE = "HY"
    RECORD_LENGTH = 123

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        return data.decode("cp932", errors="strict").strip()

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        """
        HYレコードをパースしてフィールド辞書を返す

        Args:
            data: パース対象のバイトデータ

        Returns:
            フィールド名をキーとした辞書、エラー時はNone
        """
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)

            # フィールド抽出
            result = {}

            # 1. レコード種別ID (位置:1, 長さ:2)
            result["RecordSpec"] = self.decode_field(data[0:2])

            # 2. データ区分 (位置:3, 長さ:1)
            result["DataKubun"] = self.decode_field(data[2:3])

            # 3. データ作成年月日 (位置:4, 長さ:8)
            result["MakeDate"] = self.decode_field(data[3:11])

            # 4. 血統登録番号 (位置:12, 長さ:10)
            result["KettoNum"] = self.decode_field(data[11:21])

            # 5. 馬名 (位置:22, 長さ:36)
            result["Bamei"] = self.decode_field(data[21:57])

            # 6. 馬名の意味由来 (位置:58, 長さ:64)
            result["Origin"] = self.decode_field(data[57:121])

            # 7. レコード区切 (位置:122, 長さ:2)
            result["RecordDelimiter"] = self.decode_field(data[121:123])

            return result

        except Exception as e:
            self.logger.error(f"HYレコードパース中にエラー: {e}")
            return None
