#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
H6レコードパーサー: ６．票数6（3連単）

フルストラクト (JV_H6_HYOSU_SANRENTAN) = 102,890バイトをパースし、
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
  Total = 102,890

HYO_INFO4: kumi(6) + hyo(11) + ninki(4) = 21
"""

from datetime import date
from typing import Dict, List, Mapping, Optional
from uuid import uuid4

from src.parser.base import validate_fixed_record
from src.utils.logger import get_logger


class H6Parser:
    """
    H6レコードパーサー（フルストラクト対応）

    ６．票数6（3連単）
    レコード長: 102,890 bytes (JV_H6_HYOSU_SANRENTAN)
    parse() は1組合せを1行へ展開した List[Dict] を返す。
    """

    RECORD_TYPE = "H6"
    RECORD_LENGTH = 102890
    # データ区分（0:削除 2:前日売最終 4:最終 5:月曜最終 9:レース中止）
    DATA_KUBUN_VALUES = frozenset({"0", "2", "4", "5", "9"})
    # 発売フラグ（0:発売なし 1:発売前取消 3:発売後取消 7:発売あり）
    HATUBAI_FLAG_VALUES = frozenset({"0", "1", "3", "7"})
    KEY_CODE_WIDTHS = {"JyoCD": 2, "Kaiji": 2, "Nichiji": 2, "RaceNum": 2}
    COUNT_WIDTHS = {"TorokuTosu": 2, "SyussoTosu": 2}
    # 返還馬番情報は馬番01～18の位置ごとに 0:返還なし 1:返還あり を並べた固定長。
    REFUND_SPAN_WIDTH = 18
    COMBINATION_WIDTH = 6
    VOTE_WIDTH = 11
    FAVOURITE_WIDTH = 4
    # 人気順の取消表記は公式に4文字固定（'----':発売前取消 '****':発売後取消）。
    FAVOURITE_MARKERS = frozenset({"----", "****"})
    TOTAL_FIELDS = ("SanrentanHyoTotal", "SanrentanHenkanHyoTotal")
    # 組番が1件も無い snapshot（発売なし・レース中止）でも公式の票数合計は
    # 提供されるため、H1 の総計行（Kumi='TOTAL'）と同じ sentinel で1行だけ保持する。
    TOTAL_COMBINATION = "TOTAL"

    @staticmethod
    def _require_ascii_digits(field_name: str, value: object, width: int) -> str:
        if isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return value
        raise ValueError(f"H6 {field_name} must be exactly {width} ASCII digits")

    @classmethod
    def _require_date(cls, field_name: str, value: object) -> str:
        digits = cls._require_ascii_digits(field_name, value, 8)
        try:
            date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
        except ValueError as error:
            raise ValueError(f"H6 {field_name} must be a real YYYYMMDD date") from error
        return digits

    @classmethod
    def _require_race_day(cls, record: Mapping[str, object]) -> None:
        year = cls._require_ascii_digits("Year", record.get("Year"), 4)
        month_day = cls._require_ascii_digits("MonthDay", record.get("MonthDay"), 4)
        try:
            date(int(year), int(month_day[:2]), int(month_day[2:]))
        except ValueError as error:
            raise ValueError("H6 Year/MonthDay must be a real race day") from error

    @classmethod
    def _require_flag_span(cls, field_name: str, value: object, width: int) -> None:
        # 公式の初期値は 0 だが、提供データは未設定位置を空白で送ってくる。空白は
        # 提供値として保持し、それ以外の文字と桁落ちは拒否する。
        if not isinstance(value, str) or len(value) != width or set(value) - {"0", "1", " "}:
            raise ValueError(f"H6 {field_name} must be {width} positional 0/1 refund flags")

    @classmethod
    def _require_vote_total(cls, field_name: str, value: object) -> None:
        if value == "":
            # 提供データは合計エリアを空白で送ることがある（parse 後は空文字）。
            return
        cls._require_ascii_digits(field_name, value, cls.VOTE_WIDTH)

    @classmethod
    def _require_favourite(cls, value: object) -> None:
        """人気順は数字のほか '----':発売前取消 '****':発売後取消 空白:登録なし。"""

        if not isinstance(value, str):
            raise ValueError("H6 SanrentanNinki must be a provider value")
        if value == "" or value in cls.FAVOURITE_MARKERS:
            return
        cls._require_ascii_digits("SanrentanNinki", value, cls.FAVOURITE_WIDTH)

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
        """Validate one expanded H6 row against the official domain."""

        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status not in cls.DATA_KUBUN_VALUES:
            raise ValueError("H6 DataKubun is not an official code")
        cls.validate_key_fields(record)
        if status == "0":
            # 削除指示は本文を持たない。キーとヘッダのみが公式値。
            return

        for field_name, width in cls.COUNT_WIDTHS.items():
            cls._require_ascii_digits(field_name, record.get(field_name), width)
        if record.get("HatubaiFlag") not in cls.HATUBAI_FLAG_VALUES:
            raise ValueError("H6 HatubaiFlag is not an official sale flag")
        cls._require_flag_span("HenkanUma", record.get("HenkanUma"), cls.REFUND_SPAN_WIDTH)
        for field_name in cls.TOTAL_FIELDS:
            cls._require_vote_total(field_name, record.get(field_name))

        if "SanrentanKumi" not in record and "SanrentanHyo" not in record:
            # 合計エリアだけを持つ caller row。
            return
        if record.get("SanrentanKumi") == cls.TOTAL_COMBINATION:
            # 組番のない snapshot の合計行。組番票数と人気順は提供されない。
            if record.get("SanrentanHyo") not in ("", None) or record.get(
                "SanrentanNinki"
            ) not in ("", None):
                raise ValueError(
                    "H6 totals-only row must not carry a combination vote or favourite order"
                )
            return
        cls._require_ascii_digits(
            "SanrentanKumi", record.get("SanrentanKumi"), cls.COMBINATION_WIDTH
        )
        cls._require_ascii_digits("SanrentanHyo", record.get("SanrentanHyo"), cls.VOTE_WIDTH)
        cls._require_favourite(record.get("SanrentanNinki"))

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
        h["HenkanUma"] = self.decode_fixed_flags(data[32:50])
        return h

    def parse(self, data: bytes) -> Optional[List[Dict[str, str]]]:
        """Parse one official 102,890-byte H6 physical record."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            return self._parse_full(data)
        except Exception as e:
            self.logger.error(f"H6レコードパース中にエラー: {e}")
            return None

    def _parse_full(self, data: bytes) -> List[Dict[str, str]]:
        """Parse full 102,890-byte struct into multiple rows."""
        header = self._parse_header(data)
        header["_physical_record_id"] = uuid4().hex

        # Parse HyoTotal[2] × 11 bytes at position 102866
        total_hyo = self.decode_field(data[102866:102877])
        henkan_hyo = self.decode_field(data[102877:102888])
        header["SanrentanHyoTotal"] = total_hyo
        header["SanrentanHenkanHyoTotal"] = henkan_hyo

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
            rows.append(row)

        if rows:
            return rows
        totals_only = dict(header)
        totals_only["SanrentanKumi"] = self.TOTAL_COMBINATION
        totals_only["SanrentanHyo"] = ""
        totals_only["SanrentanNinki"] = ""
        return [totals_only]
