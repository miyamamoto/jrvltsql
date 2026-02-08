#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H1レコードパーサー: ５．票数１（全掛式）

フルストラクト (JV_H1_HYOSU_ZENKAKE) = 28,955バイトをパースし、
各賭式・組番ごとに展開した行リストを返す。

構造 (kmy-keiba structures.cs 準拠):
  head(11) + id(16) = 27
  TorokuTosu(2) + SyussoTosu(2) = 4
  HatubaiFlag[7]×1 = 7
  FukuChakuBaraiKey(1)
  HenkanUma[28]×1 = 28
  HenkanWaku[8]×1 = 8
  HenkanDoWaku[8]×1 = 8
  ── pos 83 (0-indexed) ──
  HyoTansyo[28]×15 = 420   (pos 83)
  HyoFukusyo[28]×15 = 420  (pos 503)
  HyoWakuren[36]×15 = 540  (pos 923)
  HyoUmaren[153]×18 = 2754 (pos 1463)
  HyoWide[153]×18 = 2754   (pos 4217)
  HyoUmatan[306]×18 = 5508 (pos 6971)
  HyoSanrenpuku[816]×20 = 16320 (pos 12479)
  HyoTotal[14]×11 = 154    (pos 28799)
  crlf(2)                   (pos 28953)
  Total = 28,955
"""

from typing import Dict, List, Optional, Union
from src.utils.logger import get_logger


# Array definitions: (bet_type, start_0indexed, count, entry_size, kumi_len, ninki_len)
# HYO_INFO1: kumi(2) + hyo(11) + ninki(2) = 15
# HYO_INFO2: kumi(4) + hyo(11) + ninki(3) = 18
# HYO_INFO3: kumi(6) + hyo(11) + ninki(3) = 20
_H1_ARRAYS = [
    ("Tansyo",      83,   28, 15, 2, 2),
    ("Fukusyo",    503,   28, 15, 2, 2),
    ("Wakuren",    923,   36, 15, 2, 2),
    ("Umaren",    1463,  153, 18, 4, 3),
    ("Wide",      4217,  153, 18, 4, 3),
    ("Umatan",    6971,  306, 18, 4, 3),
    ("Sanrenpuku", 12479, 816, 20, 6, 3),
]

_TOTAL_NAMES = [
    "TanHyoTotal", "FukuHyoTotal", "WakuHyoTotal",
    "UmarenHyoTotal", "WideHyoTotal", "UmatanHyoTotal", "SanrenfukuHyoTotal",
    "TanHenkanHyoTotal", "FukuHenkanHyoTotal", "WakuHenkanHyoTotal",
    "UmarenHenkanHyoTotal", "WideHenkanHyoTotal", "UmatanHenkanHyoTotal",
    "SanrenfukuHenkanHyoTotal",
]


class H1Parser:
    """
    H1レコードパーサー（フルストラクト対応）

    ５．票数１（全掛式）
    レコード長: 28,955 bytes (JV_H1_HYOSU_ZENKAKE)
    旧レコード長: 317 bytes (フラット1組合せ分) — 後方互換のためフォールバック対応

    parse() は List[Dict] を返す（フルストラクト時、1組合せ = 1行）。
    フラットレコード時は単一 Dict を返す（後方互換）。
    """

    RECORD_TYPE = "H1"
    RECORD_LENGTH = 28955
    RECORD_LENGTH_FLAT = 317

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def _parse_header(self, data: bytes) -> Dict[str, str]:
        """Parse common header fields (first 83 bytes)."""
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
        for i in range(7):
            h[f"HatubaiFlag{i+1}"] = self.decode_field(data[31+i:32+i])
        h["FukuChakuBaraiKey"] = self.decode_field(data[38:39])
        # HenkanUma[28], HenkanWaku[8], HenkanDoWaku[8] — stored as concatenated strings
        h["HenkanUma"] = self.decode_field(data[39:67])
        h["HenkanWaku"] = self.decode_field(data[67:75])
        h["HenkanDoWaku"] = self.decode_field(data[75:83])
        return h

    def parse(self, data: bytes) -> Optional[Union[Dict[str, str], List[Dict[str, str]]]]:
        """
        H1レコードをパースする。

        28,955バイトのフルストラクトの場合: List[Dict] を返す（各組合せ1行）。
        317バイトのフラットレコードの場合: 単一 Dict を返す（後方互換）。
        """
        try:
            if len(data) >= self.RECORD_LENGTH:
                return self._parse_full(data)
            elif len(data) >= self.RECORD_LENGTH_FLAT:
                return self._parse_flat(data)
            else:
                self.logger.warning(
                    f"H1レコード長不足: actual={len(data)}"
                )
                # Try flat parse anyway for short records
                return self._parse_flat(data)
        except Exception as e:
            self.logger.error(f"H1レコードパース中にエラー: {e}")
            return None

    def _parse_full(self, data: bytes) -> List[Dict[str, str]]:
        """Parse full 28,955-byte struct into multiple rows."""
        header = self._parse_header(data)

        # Parse HyoTotal[14] × 11 bytes at position 28799
        totals = {}
        for i, name in enumerate(_TOTAL_NAMES):
            offset = 28799 + (11 * i)
            totals[name] = self.decode_field(data[offset:offset + 11])

        rows = []
        for bet_type, start, count, entry_size, kumi_len, ninki_len in _H1_ARRAYS:
            for i in range(count):
                offset = start + (entry_size * i)
                kumi = self.decode_field(data[offset:offset + kumi_len])
                hyo = self.decode_field(data[offset + kumi_len:offset + kumi_len + 11])
                ninki = self.decode_field(data[offset + kumi_len + 11:offset + kumi_len + 11 + ninki_len])

                # Skip empty entries (all spaces or zeros)
                if not kumi or kumi == "0" * kumi_len:
                    continue

                row = dict(header)
                row["BetType"] = bet_type
                row["Kumi"] = kumi
                row["Hyo"] = hyo
                row["Ninki"] = ninki
                rows.append(row)

        # Also emit a summary row with totals (BetType='Total')
        if totals:
            total_row = dict(header)
            total_row["BetType"] = "Total"
            total_row["Kumi"] = ""
            total_row["Hyo"] = ""
            total_row["Ninki"] = ""
            total_row.update(totals)
            rows.append(total_row)

        return rows if rows else [header]

    def _parse_flat(self, data: bytes) -> Optional[Dict[str, str]]:
        """Parse legacy 317-byte flat record (single combination)."""
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
        for i in range(7):
            result[f"HatubaiFlag{i+1}"] = self.decode_field(data[31+i:32+i])
        result["FukuChakuBaraiKey"] = self.decode_field(data[38:39])
        result["HenkanUma1"] = self.decode_field(data[39:40])
        result["HenkanUma2"] = self.decode_field(data[40:41])
        result["HenkanUma3"] = self.decode_field(data[41:42])
        result["TanUma"] = self.decode_field(data[42:44])
        result["TanHyo"] = self.decode_field(data[44:55])
        result["TanNinki"] = self.decode_field(data[55:57])
        result["FukuUma"] = self.decode_field(data[57:59])
        result["FukuHyo"] = self.decode_field(data[59:70])
        result["FukuNinki"] = self.decode_field(data[70:72])
        result["WakuKumi"] = self.decode_field(data[72:74])
        result["WakuHyo"] = self.decode_field(data[74:85])
        result["WakuNinki"] = self.decode_field(data[85:87])
        result["UmarenKumi"] = self.decode_field(data[87:91])
        result["UmarenHyo"] = self.decode_field(data[91:102])
        result["UmarenNinki"] = self.decode_field(data[102:105])
        result["WideKumi"] = self.decode_field(data[105:109])
        result["WideHyo"] = self.decode_field(data[109:120])
        result["WideNinki"] = self.decode_field(data[120:123])
        result["UmatanKumi"] = self.decode_field(data[123:127])
        result["UmatanHyo"] = self.decode_field(data[127:138])
        result["UmatanNinki"] = self.decode_field(data[138:141])
        result["SanrenfukuKumi"] = self.decode_field(data[141:147])
        result["SanrenfukuHyo"] = self.decode_field(data[147:158])
        result["SanrenfukuNinki"] = self.decode_field(data[158:161])
        result["TanHyoTotal"] = self.decode_field(data[161:172])
        result["FukuHyoTotal"] = self.decode_field(data[172:183])
        result["WakuHyoTotal"] = self.decode_field(data[183:194])
        result["UmarenHyoTotal"] = self.decode_field(data[194:205])
        result["WideHyoTotal"] = self.decode_field(data[205:216])
        result["UmatanHyoTotal"] = self.decode_field(data[216:227])
        result["SanrenfukuHyoTotal"] = self.decode_field(data[227:238])
        result["TanHenkanHyoTotal"] = self.decode_field(data[238:249])
        result["FukuHenkanHyoTotal"] = self.decode_field(data[249:260])
        result["WakuHenkanHyoTotal"] = self.decode_field(data[260:271])
        result["UmarenHenkanHyoTotal"] = self.decode_field(data[271:282])
        result["WideHenkanHyoTotal"] = self.decode_field(data[282:293])
        result["UmatanHenkanHyoTotal"] = self.decode_field(data[293:304])
        result["SanrenfukuHenkanHyoTotal"] = self.decode_field(data[304:315])
        result["RecordDelimiter"] = self.decode_field(data[315:317])
        return result
