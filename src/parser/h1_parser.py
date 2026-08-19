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

from datetime import date
from typing import Dict, List, Mapping, Optional
from uuid import uuid4

from src.parser.base import validate_fixed_record
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
    parse() は1組合せを1行へ展開した List[Dict] を返す。
    """

    RECORD_TYPE = "H1"
    RECORD_LENGTH = 28955
    # ５．票数１ のデータ区分。1/3 は公式に存在しない。
    DATA_KUBUN_VALUES = frozenset({"0", "2", "4", "5", "9"})
    # 発売フラグ（0:発売なし 1:発売前取消 3:発売後取消 7:発売あり）
    HATUBAI_FLAG_VALUES = frozenset({"0", "1", "3", "7"})
    HATUBAI_FLAG_FIELDS = tuple(f"HatubaiFlag{slot}" for slot in range(1, 8))
    # 複勝着払キー（0:複勝発売なし 2:2着まで払い 3:3着まで払い）
    FUKU_CHAKU_BARAI_KEY_VALUES = frozenset({"0", "2", "3"})
    KEY_CODE_WIDTHS = {"JyoCD": 2, "Kaiji": 2, "Nichiji": 2, "RaceNum": 2}
    COUNT_WIDTHS = {"TorokuTosu": 2, "SyussoTosu": 2}
    # 返還情報は馬番/枠番の位置ごとに 0:返還なし 1:返還あり を並べた固定長。
    REFUND_SPAN_WIDTHS = {"HenkanUma": 28, "HenkanWaku": 8, "HenkanDoWaku": 8}
    COMBINATION_WIDTHS = {
        "Tansyo": 2,
        "Fukusyo": 2,
        "Wakuren": 2,
        "Umaren": 4,
        "Wide": 4,
        "Umatan": 4,
        "Sanrenpuku": 6,
    }
    FAVOURITE_WIDTHS = {
        "Tansyo": 2,
        "Fukusyo": 2,
        "Wakuren": 2,
        "Umaren": 3,
        "Wide": 3,
        "Umatan": 3,
        "Sanrenpuku": 3,
    }
    VOTE_WIDTH = 11
    TOTAL_BET_TYPE = "Total"
    TOTAL_COMBINATION = "TOTAL"
    TOTAL_FIELDS = tuple(_TOTAL_NAMES)

    @staticmethod
    def _require_ascii_digits(field_name: str, value: object, width: int) -> str:
        if isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return value
        raise ValueError(f"H1 {field_name} must be exactly {width} ASCII digits")

    @classmethod
    def _require_date(cls, field_name: str, value: object) -> str:
        digits = cls._require_ascii_digits(field_name, value, 8)
        try:
            date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        except ValueError as error:
            raise ValueError(f"H1 {field_name} must be a real YYYYMMDD date") from error
        return digits

    @classmethod
    def _require_race_day(cls, record: Mapping[str, object]) -> None:
        year = cls._require_ascii_digits("Year", record.get("Year"), 4)
        month_day = cls._require_ascii_digits("MonthDay", record.get("MonthDay"), 4)
        try:
            date(int(year), int(month_day[:2]), int(month_day[2:]))
        except ValueError as error:
            raise ValueError("H1 Year/MonthDay must be a real race day") from error

    @classmethod
    def _require_flag_span(cls, field_name: str, value: object, width: int) -> None:
        # 公式の初期値は 0 だが、提供データは未設定位置を空白で送ってくる（本リポジトリ
        # の H1/H6 返還エリアの無損失 pin が実測済み）。空白は提供値として保持し、
        # それ以外の文字と桁落ちは拒否する。
        if not isinstance(value, str) or len(value) != width or set(value) - {"0", "1", " "}:
            raise ValueError(f"H1 {field_name} must be {width} positional 0/1 refund flags")

    @classmethod
    def _require_vote_total(cls, field_name: str, value: object) -> None:
        if value == "":
            # 提供データは合計エリアを空白で送ることがある（parse 後は空文字）。
            return
        cls._require_ascii_digits(field_name, value, cls.VOTE_WIDTH)

    @classmethod
    def _require_favourite(cls, value: object, width: int) -> None:
        """人気順は数字のほか 全桁'-':発売前取消 全桁'*':発売後取消 空白:登録なし。"""

        if not isinstance(value, str):
            raise ValueError("H1 Ninki must be a provider value")
        if value == "":
            return
        text = value.strip()
        if text in {"-" * width, "*" * width}:
            # 取消マーカーは項目幅ぶんの繰り返しで届く（実データの3桁票数系は
            # '***'）。幅の違うマーカーは桁落ちなので拒否する。
            return
        if len(text) == width and text.isascii() and text.isdigit():
            return
        raise ValueError(
            f"H1 Ninki must be {width} ASCII digits, a cancel marker, or blank"
        )

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        """The official race key identifies the record regardless of status."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        cls._require_race_day(record)
        for field_name, width in cls.KEY_CODE_WIDTHS.items():
            cls._require_ascii_digits(field_name, record.get(field_name), width)

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one expanded H1 row against the official domain."""

        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status not in cls.DATA_KUBUN_VALUES:
            raise ValueError("H1 DataKubun is not an official code")
        cls.validate_key_fields(record)
        if status == "0":
            # 削除指示は本文を持たない。キーとヘッダのみが公式値。
            return

        for field_name, width in cls.COUNT_WIDTHS.items():
            cls._require_ascii_digits(field_name, record.get(field_name), width)
        for field_name in cls.HATUBAI_FLAG_FIELDS:
            if record.get(field_name) not in cls.HATUBAI_FLAG_VALUES:
                raise ValueError(f"H1 {field_name} is not an official sale flag")
        if record.get("FukuChakuBaraiKey") not in cls.FUKU_CHAKU_BARAI_KEY_VALUES:
            raise ValueError("H1 FukuChakuBaraiKey is not an official code")
        for field_name, width in cls.REFUND_SPAN_WIDTHS.items():
            cls._require_flag_span(field_name, record.get(field_name), width)

        bet_type = record.get("BetType")
        if bet_type == cls.TOTAL_BET_TYPE:
            if record.get("Kumi") != cls.TOTAL_COMBINATION:
                raise ValueError("H1 total row must carry the TOTAL combination")
            for field_name in cls.TOTAL_FIELDS:
                cls._require_vote_total(field_name, record.get(field_name))
        elif bet_type in cls.COMBINATION_WIDTHS:
            cls._require_ascii_digits(
                "Kumi", record.get("Kumi"), cls.COMBINATION_WIDTHS[bet_type]
            )
            cls._require_ascii_digits("Hyo", record.get("Hyo"), cls.VOTE_WIDTH)
            cls._require_favourite(record.get("Ninki"), cls.FAVOURITE_WIDTHS[bet_type])
        else:
            raise ValueError("H1 BetType is not an official 賭式")

        for field_name in cls.TOTAL_FIELDS:
            if field_name in record and bet_type != cls.TOTAL_BET_TYPE:
                cls._require_vote_total(field_name, record.get(field_name))

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        return data.decode("cp932", errors="strict").strip()

    @staticmethod
    def decode_fixed_flags(data: bytes) -> str:
        """Decode positional one-byte flags without shifting blank entries."""
        return data.decode("cp932", errors="strict")

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
        h["HenkanUma"] = self.decode_fixed_flags(data[39:67])
        h["HenkanWaku"] = self.decode_fixed_flags(data[67:75])
        h["HenkanDoWaku"] = self.decode_fixed_flags(data[75:83])
        return h

    def parse(self, data: bytes) -> Optional[List[Dict[str, str]]]:
        """Parse one official 28,955-byte H1 physical record."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            return self._parse_full(data)
        except Exception as e:
            self.logger.error(f"H1レコードパース中にエラー: {e}")
            return None

    def _parse_full(self, data: bytes) -> List[Dict[str, str]]:
        """Parse full 28,955-byte struct into multiple rows."""
        header = self._parse_header(data)
        header["_physical_record_id"] = uuid4().hex

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
            total_row["Kumi"] = "TOTAL"
            total_row["Hyo"] = ""
            total_row["Ninki"] = ""
            total_row.update(totals)
            rows.append(total_row)

        return rows if rows else [header]
