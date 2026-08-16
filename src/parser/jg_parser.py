#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JGレコードパーサー: ３１．競走馬除外情報

Current layout verified against 公式JV-Data仕様書 Ver.4.8.0.2 / Ver.4.9.0.1
(３１．競走馬除外情報, 80 bytes) and the SDK 5.0.0 ``JV_JG_JOGAIBA`` structure.
Ver.4.1.1 only appended the initial value of item 10 (血統登録番号); the
80-byte layout has never changed since JG was added in Ver.4.1.0.
"""

from typing import Dict, Optional

from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class JGParser:
    """
    JGレコードパーサー

    ３１．競走馬除外情報
    レコード長: 80 bytes
    SDK構造体名: JV_JG_JOGAIBA
    """

    RECORD_TYPE = "JG"
    RECORD_LENGTH = 80

    # 公式データ区分: 1=初期値, 0=該当レコード削除(提供ミスなどの理由による)
    DATA_KUBUN_VALUES = frozenset({"0", "1"})
    # 公式出走区分: 初期値0, 1:投票馬 2:締切での除外馬 4:再投票馬 5:再投票除外馬
    # 6:馬番を付さない出走取消馬 9:取消馬
    SYUSSO_KUBUN_VALUES = frozenset({"0", "1", "2", "4", "5", "6", "9"})
    # 公式除外状態区分: 初期値0, 1:非抽選馬 2:非当選馬
    JYOGAI_STATE_KUBUN_VALUES = frozenset({"0", "1", "2"})
    # 固定桁の数値項目 (項目名, バイト数)。位置固定・ゼロ埋めのASCII数字のみ。
    NUMERIC_FIXED_FIELDS = (
        ("MakeDate", 8),
        ("Year", 4),
        ("MonthDay", 4),
        ("Kaiji", 2),
        ("Nichiji", 2),
        ("RaceNum", 2),
        ("KettoNum", 10),
        ("Num", 3),
    )

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをフィールド単位で厳密にデコードして文字列に変換"""
        return data.decode("cp932", errors="strict").strip()

    @staticmethod
    def _require_ascii_digits(name: str, value: str, width: int) -> None:
        if len(value) != width or not value.isascii() or not value.isdigit():
            raise ValueError(f"JG {name} must be exactly {width} ASCII digits")

    @staticmethod
    def _require_code(name: str, value: str, allowed: frozenset, *, allow_blank: bool) -> None:
        if value == "" and allow_blank:
            return
        if value not in allowed:
            raise ValueError(f"JG {name} has undefined value {value!r}")

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        """
        JGレコードをパースしてフィールド辞書を返す

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
            if result["DataKubun"] not in self.DATA_KUBUN_VALUES:
                raise ValueError("JG DataKubun must be 0 or 1")

            # 3. データ作成年月日 (位置:4, 長さ:8)
            result["MakeDate"] = self.decode_field(data[3:11])

            # 4. 開催年 (位置:12, 長さ:4)
            result["Year"] = self.decode_field(data[11:15])

            # 5. 開催月日 (位置:16, 長さ:4)
            result["MonthDay"] = self.decode_field(data[15:19])

            # 6. 競馬場コード (位置:20, 長さ:2) <コード表 2001>
            result["JyoCD"] = self.decode_field(data[19:21])

            # 7. 開催回[第N回] (位置:22, 長さ:2)
            result["Kaiji"] = self.decode_field(data[21:23])

            # 8. 開催日目[N日目] (位置:24, 長さ:2)
            result["Nichiji"] = self.decode_field(data[23:25])

            # 9. レース番号 (位置:26, 長さ:2)
            result["RaceNum"] = self.decode_field(data[25:27])

            # 10. 血統登録番号 (位置:28, 長さ:10)
            result["KettoNum"] = self.decode_field(data[27:37])

            # 11. 馬名 (位置:38, 長さ:36)
            result["Bamei"] = self.decode_field(data[37:73])

            # 12. 出馬投票受付順番 (位置:74, 長さ:3) - 同一馬の追加/再投票順で公式キー
            result["Num"] = self.decode_field(data[73:76])

            # 13. 出走区分 (位置:77, 長さ:1)
            result["SyussoKubun"] = self.decode_field(data[76:77])

            # 14. 除外状態区分 (位置:78, 長さ:1)
            result["JyogaiStateKubun"] = self.decode_field(data[77:78])

            # 15. レコード区切 (位置:79, 長さ:2)
            result["RecordDelimiter"] = self.decode_field(data[78:80])

            # 公式キー8項目と数値固定項目は削除レコードでも設定される。
            for name, width in self.NUMERIC_FIXED_FIELDS:
                self._require_ascii_digits(name, result[name], width)
            jyo_cd = result["JyoCD"]
            if len(jyo_cd) != 2 or not jyo_cd.isascii() or not jyo_cd.isalnum():
                raise ValueError("JG JyoCD must be a 2-character code")

            # DataKubun=0 はキーのみの本文を許容する。DataKubun=1 は現行の
            # 公式コード値のみ受け付ける。
            key_only_body = result["DataKubun"] == "0"
            self._require_code(
                "SyussoKubun",
                result["SyussoKubun"],
                self.SYUSSO_KUBUN_VALUES,
                allow_blank=key_only_body,
            )
            self._require_code(
                "JyogaiStateKubun",
                result["JyogaiStateKubun"],
                self.JYOGAI_STATE_KUBUN_VALUES,
                allow_blank=key_only_body,
            )

            return result

        except Exception as e:
            self.logger.error(f"JGレコードパース中にエラー: {e}")
            return None
