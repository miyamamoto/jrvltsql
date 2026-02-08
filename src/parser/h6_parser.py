#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H6レコードパーサー: ６．票数6（3連単）

フルストラクト (JV_H6_HYOSU_SANRENTAN) = 102,900バイトをパースし、
各組番ごとに展開した行リストを返す。

構造 (kmy-keiba structures.cs 準拠):
  head(11) + id(16) = 27
  TorokuTosu(2) + SyussoTosu(2) = 4
  HatubaiFlag(1)
  HenkanUma[18]×1 = 18
  ── pos 50 (0-indexed) ──
  HyoSanrentan[4896]×21 = 102,816  (pos 50)
  HyoTotal[2]×11 = 22              (pos 102866)
  crlf(2)                           (pos 102888)
  Total = 102,900

HYO_INFO4: kumi(6) + hyo(11) + ninki(4) = 21
"""

from typing import Dict, List, Optional, Union
from src.utils.logger import get_logger


class H6Parser:
    """
    H6レコードパーサー（フルストラクト対応）

    ６．票数6（3連単）
    レコード長: 102,900 bytes (JV_H6_HYOSU_SANRENTAN)
    旧レコード長: 78 bytes (フラット1組合せ分) — 後方互換のためフォールバック対応

    parse() は List[Dict] を返す（フルストラクト時、1組合せ = 1行）。
    フラットレコード時は単一 Dict を返す（後方互換）。
    """

    RECORD_TYPE = "H6"
    RECORD_LENGTH = 102900
    RECORD_LENGTH_FLAT = 78

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def _parse_header(self, data: bytes) -> Dict[str, str]:
        """Parse common header fields (first 50 bytes)."""
        h = {}
        h["RecordSpec"] = self.decode_field(data[0:2])
        h["DataKubun"] = self.decode_field(data[2:3])
        h["MakeDate"] = self.decode_field(data[3:11])
        h["Year"] = self.decode_field(data[11:15])
        h["MonthDay"] = self.decode_field(data[15:19])
        h["JyoCD"] = self.decode_field(data[19:21])
        h["Kaiji"] = self.decode_field(data[21:23])
        h["Nichiji"] = self.decode_field(data[23:25])
        h["RaceNum"] = self.decode_field(data[25:27])
        h["TorokuTosu"] = self.decode_field(data[27:29])
        h["SyussoTosu"] = self.decode_field(data[29:31])
        h["HatubaiFlag"] = self.decode_field(data[31:32])
        h["HenkanUma"] = self.decode_field(data[32:50])
        return h

    def parse(self, data: bytes) -> Optional[Union[Dict[str, str], List[Dict[str, str]]]]:
        """
        H6レコードをパースする。

        102,900バイトのフルストラクトの場合: List[Dict] を返す。
        78バイトのフラットレコードの場合: 単一 Dict を返す（後方互換）。
        """
        try:
            if len(data) >= self.RECORD_LENGTH:
                return self._parse_full(data)
            elif len(data) >= self.RECORD_LENGTH_FLAT:
                return self._parse_flat(data)
            else:
                self.logger.warning(
                    f"H6レコード長不足: actual={len(data)}"
                )
                return self._parse_flat(data)
        except Exception as e:
            self.logger.error(f"H6レコードパース中にエラー: {e}")
            return None

    def _parse_full(self, data: bytes) -> List[Dict[str, str]]:
        """Parse full 102,900-byte struct into multiple rows."""
        header = self._parse_header(data)

        # Parse HyoTotal[2] × 11 bytes at position 102866
        total_hyo = self.decode_field(data[102866:102877])
        henkan_hyo = self.decode_field(data[102877:102888])

        rows = []
        # HyoSanrentan[4896] × 21 bytes starting at position 50
        for i in range(4896):
            offset = 50 + (21 * i)
            kumi = self.decode_field(data[offset:offset + 6])
            hyo = self.decode_field(data[offset + 6:offset + 17])
            ninki = self.decode_field(data[offset + 17:offset + 21])

            # Skip empty entries
            if not kumi or kumi == "000000":
                continue

            row = dict(header)
            row["SanrentanKumi"] = kumi
            row["SanrentanHyo"] = hyo
            row["SanrentanNinki"] = ninki
            row["SanrentanHyoTotal"] = total_hyo
            row["SanrentanHenkanHyoTotal"] = henkan_hyo
            rows.append(row)

        return rows if rows else [header]

    def _parse_flat(self, data: bytes) -> Optional[Dict[str, str]]:
        """Parse legacy 78-byte flat record (single combination)."""
        result = {}
        result["RecordSpec"] = self.decode_field(data[0:2])
        result["DataKubun"] = self.decode_field(data[2:3])
        result["MakeDate"] = self.decode_field(data[3:11])
        result["Year"] = self.decode_field(data[11:15])
        result["MonthDay"] = self.decode_field(data[15:19])
        result["JyoCD"] = self.decode_field(data[19:21])
        result["Kaiji"] = self.decode_field(data[21:23])
        result["Nichiji"] = self.decode_field(data[23:25])
        result["RaceNum"] = self.decode_field(data[25:27])
        result["TorokuTosu"] = self.decode_field(data[27:29])
        result["SyussoTosu"] = self.decode_field(data[29:31])
        result["HatubaiFlag"] = self.decode_field(data[31:32])
        result["HenkanUma"] = self.decode_field(data[32:33])
        result["SanrentanKumi"] = self.decode_field(data[33:39])
        result["SanrentanHyo"] = self.decode_field(data[39:50])
        result["SanrentanNinki"] = self.decode_field(data[50:54])
        result["SanrentanHyoTotal"] = self.decode_field(data[54:65])
        result["SanrentanHenkanHyoTotal"] = self.decode_field(data[65:76])
        result["RecordDelimiter"] = self.decode_field(data[76:78])
        return result
