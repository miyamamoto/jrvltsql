#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NUレコードパーサー: NAR (地方競馬) 競走馬登録データ

このファイルはNAR DIFN スペックに基づいて作成されました。
レコード長: 64 bytes (推定)
サンプル: NU42005022021199603170000000000000000019940405新地タロウ
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class NUParser(BaseParser):
    """
    NUレコードパーサー

    NAR (地方競馬) 競走馬登録データ
    レコード長: 64 bytes (推定)
    対応データ種別: DIFN
    """

    record_type = "NU"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions for NU record.

        フィールド構造 (推定):
        - [0:2]   レコード種別: NU
        - [2:12]  馬ID: 10桁 (例: 4200502202)
        - [12:22] 登録番号: 10桁 (例: 1199603170)
        - [22:38] 予備: 16桁 (0埋め)
        - [38:46] 生年月日: 8桁 (YYYYMMDD形式, 例: 19940405)
        - [46:]   馬名: 残り全て (可変長, CP932エンコード, 約18バイト)

        Returns:
            List of FieldDef objects defining the record structure
        """
        return [
            # 1. レコード種別ID (位置:0, 長さ:2)
            FieldDef("RecordSpec", 0, 2, description="レコード種別"),

            # 2. 馬ID (位置:2, 長さ:10) - PRIMARY KEY
            FieldDef("UmaID", 2, 10, description="馬ID"),

            # 3. 登録番号 (位置:12, 長さ:10)
            FieldDef("TorokuNum", 12, 10, description="登録番号"),

            # 4. 予備 (位置:22, 長さ:16)
            FieldDef("Reserved", 22, 16, description="予備"),

            # 5. 生年月日 (位置:38, 長さ:8)
            FieldDef("BirthDate", 38, 8, convert_type="DATE", description="生年月日"),

            # 6. 馬名 (位置:46, 長さ:残り全て, 約18バイト)
            # 実際のレコード長64の場合、46+18=64バイト
            FieldDef("Bamei", 46, 18, description="馬名"),
        ]
