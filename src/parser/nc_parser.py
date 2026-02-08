#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NCレコードパーサー: NAR (地方競馬) 競馬場マスタ

NVDファイルから取得されるレコード。
先頭2バイトが "NC" のレコード。
"""

from typing import List

from src.parser.base import BaseParser, FieldDef


class NCParser(BaseParser):
    """
    NCレコードパーサー

    NAR (地方競馬) 競馬場マスタ
    対応データ種別: DIFN
    """

    record_type = "NC"

    def _define_fields(self) -> List[FieldDef]:
        """Define field positions for NC record.

        フィールド構造 (共通ヘッダ + 競馬場マスタ):
        - [0:2]   レコード種別: NC (共通ヘッダ)
        - [2:3]   データ区分: 1桁 (共通ヘッダ)
        - [3:11]  データ作成年月日: 8桁 YYYYMMDD (共通ヘッダ)
        - [11:13] 競馬場コード: 2桁
        - [13:33] 競馬場名: 20桁 (CP932)
        - [33:53] 競馬場名略称: 20桁 (CP932)
        - [53:93] 競馬場名英字: 40桁
        - [93:133] 所在地: 40桁 (CP932)
        - [133:143] 電話番号: 10桁
        - [143:145] レコード区切: 2桁 (CRLF)

        Returns:
            List of FieldDef objects defining the record structure
        """
        return [
            # 共通ヘッダ
            FieldDef("RecordSpec", 0, 2, description="レコード種別"),
            FieldDef("DataKubun", 2, 1, description="データ区分"),
            FieldDef("MakeDate", 3, 8, convert_type="DATE", description="データ作成年月日"),

            # 競馬場マスタ固有フィールド
            FieldDef("JyoCD", 11, 2, description="競馬場コード"),
            FieldDef("JyoName", 13, 20, description="競馬場名"),
            FieldDef("JyoName_Ryaku", 33, 20, description="競馬場名略称"),
            FieldDef("JyoName_Eng", 53, 40, description="競馬場名英字"),
            FieldDef("Address", 93, 40, description="所在地"),
            FieldDef("TelNum", 133, 10, description="電話番号"),
            FieldDef("RecordDelimiter", 143, 2, description="レコード区切"),
        ]
