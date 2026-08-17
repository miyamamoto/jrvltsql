#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HRレコードパーサー: ４．払戻

JV-Data仕様書 Ver.4.9.0.1に基づく払戻レコードのパース
払戻データは配列構造のため全要素を抽出する (複勝5件・ワイド7件など)
"""

from collections.abc import Mapping
from datetime import date
from typing import Dict, Optional

from src.parser.base import validate_fixed_record
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001
from src.utils.logger import get_logger


class HRParser:
    """
    HRレコードパーサー

    ４．払戻
    レコード長: 719 bytes (JV-Data仕様書 Ver.4.9.0.1による正確な長さ)
    VBテーブル名: HARAI

    配列構造 (JV-Data仕様書より):
    - 単勝払戻: 3件 (馬番2 + 払戻9 + 人気2 = 13バイト × 3 = 39バイト)
    - 複勝払戻: 5件 (馬番2 + 払戻9 + 人気2 = 13バイト × 5 = 65バイト)
    - 枠連払戻: 3件 (組合せ2 + 払戻9 + 人気2 = 13バイト × 3 = 39バイト)
    - 馬連払戻: 3件 (組合せ4 + 払戻9 + 人気3 = 16バイト × 3 = 48バイト)
    - ワイド払戻: 7件 (組合せ4 + 払戻9 + 人気3 = 16バイト × 7 = 112バイト)
    - 予備: 3件 (16バイト × 3 = 48バイト)
    - 馬単払戻: 6件 (組合せ4 + 払戻9 + 人気3 = 16バイト × 6 = 96バイト)
    - 三連複払戻: 3件 (組合せ6 + 払戻9 + 人気3 = 18バイト × 3 = 54バイト)
    - 三連単払戻: 6件 (組合せ6 + 払戻9 + 人気4 = 19バイト × 6 = 114バイト)
    """

    RECORD_TYPE = "HR"
    RECORD_LENGTH = 719  # JV-Data仕様書 Ver.4.9.0.1による正確な長さ
    KEY_COLUMNS = ("Year", "MonthDay", "JyoCD", "Kaiji", "Nichiji", "RaceNum")
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    SANRENTAN_AVAILABLE_FROM = date(2004, 8, 14)
    LEGACY_RESERVED_FIELD = "LegacyReserved604_717Hex"
    STATUS9_OPAQUE_FIELD = "OpaqueStatus9Body28_717Hex"

    PAYOUT_GROUPS = (
        ("Tan", "TanUmaban", "TanPay", "TanNinki", 3, 2, 9, 2),
        ("Fuku", "FukuUmaban", "FukuPay", "FukuNinki", 5, 2, 9, 2),
        ("Waku", "WakuKumi", "WakuPay", "WakuNinki", 3, 2, 9, 2),
        ("Umaren", "UmarenKumi", "UmarenPay", "UmarenNinki", 3, 4, 9, 3),
        ("Wide", "WideKumi", "WidePay", "WideNinki", 7, 4, 9, 3),
        ("Umatan", "UmatanKumi", "UmatanPay", "UmatanNinki", 6, 4, 9, 3),
        (
            "Sanrenfuku",
            "SanrenfukuKumi",
            "SanrenfukuPay",
            "SanrenfukuNinki",
            3,
            6,
            9,
            3,
        ),
        (
            "Sanrentan",
            "SanrentanKumi",
            "SanrentanPay",
            "SanrentanNinki",
            6,
            6,
            9,
            4,
        ),
    )

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        return data.decode("cp932", errors="strict").strip()

    @staticmethod
    def _require_date(field_name: str, value: object) -> date:
        if isinstance(value, date):
            return value
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"HR {field_name} must be exactly 8 ASCII digits")
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:]))
        except ValueError as error:
            raise ValueError(f"HR {field_name} must be a real YYYYMMDD date") from error

    @staticmethod
    def _require_fixed_integer(field_name: str, value: object, width: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"HR {field_name} must be an official {width}-digit integer")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return value
        elif isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
            return int(value)
        raise ValueError(f"HR {field_name} must be an official {width}-digit integer")

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> date:
        """Validate the complete official six-part identity before coercion."""

        cls._require_date("MakeDate", record.get("MakeDate"))
        year = cls._require_fixed_integer("Year", record.get("Year"), 4)
        month_day = cls._require_fixed_integer("MonthDay", record.get("MonthDay"), 4)
        try:
            race_date = date(year, month_day // 100, month_day % 100)
        except ValueError as error:
            raise ValueError("HR Year and MonthDay must form a real date") from error
        if record.get("JyoCD") not in cls.OFFICIAL_JYO_CODES:
            raise ValueError("HR JyoCD is not in official code table 2001")
        for field_name in ("Kaiji", "Nichiji", "RaceNum"):
            cls._require_fixed_integer(field_name, record.get(field_name), 2)
        return race_date

    @classmethod
    def _require_bit(cls, field_name: str, value: object) -> None:
        if value not in ("0", "1", 0, 1):
            raise ValueError(f"HR {field_name} must be an official 0/1 flag")

    @classmethod
    def _require_optional_digits(
        cls, field_name: str, value: object, width: int, *, fixed: bool
    ) -> None:
        if value in (None, ""):
            return
        if isinstance(value, bool):
            raise ValueError(f"HR {field_name} must contain ASCII digits")
        if isinstance(value, int):
            if 0 <= value < 10**width:
                return
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            if len(value) == width if fixed else len(value) <= width:
                return
        qualifier = "exactly" if fixed else "at most"
        raise ValueError(f"HR {field_name} must contain {qualifier} {width} ASCII digits")

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one HR record while keeping status-0 bodies opaque."""

        race_date = cls.validate_key_fields(record)
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        opaque_status9 = record.get(cls.STATUS9_OPAQUE_FIELD)
        if opaque_status9 not in (None, ""):
            if (
                not isinstance(opaque_status9, str)
                or len(opaque_status9) != 1380
                or not opaque_status9.isascii()
                or any(character not in "0123456789abcdefABCDEF" for character in opaque_status9)
            ):
                raise ValueError(
                    f"HR {cls.STATUS9_OPAQUE_FIELD} must be exactly 1380 hexadecimal characters"
                )
            if status != "9":
                raise ValueError(f"HR {cls.STATUS9_OPAQUE_FIELD} is only valid for DataKubun 9")
        if status in {"0", "9"}:
            return

        for field_name in ("TorokuTosu", "SyussoTosu"):
            cls._require_fixed_integer(field_name, record.get(field_name), 2)
        for prefix, count in (
            ("FuseirituFlag", 9),
            ("TokubaraiFlag", 9),
            ("HenkanFlag", 9),
            ("HenkanUma", 28),
            ("HenkanWaku", 8),
            ("HenkanDoWaku", 8),
        ):
            for index in range(1, count + 1):
                cls._require_bit(f"{prefix}{index}", record.get(f"{prefix}{index}"))

        for (
            _,
            first,
            pay,
            popularity,
            count,
            first_width,
            pay_width,
            popularity_width,
        ) in cls.PAYOUT_GROUPS:
            if first.startswith("Sanrentan") and race_date < cls.SANRENTAN_AVAILABLE_FROM:
                for index in range(1, count + 1):
                    suffix = "" if index == 1 else str(index)
                    for field_name in (
                        f"{first}{suffix}",
                        f"{pay}{suffix}",
                        f"{popularity}{suffix}",
                    ):
                        if record.get(field_name) not in (None, ""):
                            raise ValueError(
                                "HR pre-2004-08-14 bytes 604-717 must use the "
                                "opaque legacy field, not canonical trifecta fields"
                            )
                continue
            for index in range(1, count + 1):
                suffix = "" if index == 1 else str(index)
                cls._require_optional_digits(
                    f"{first}{suffix}",
                    record.get(f"{first}{suffix}"),
                    first_width,
                    fixed=True,
                )
                cls._require_optional_digits(
                    f"{pay}{suffix}",
                    record.get(f"{pay}{suffix}"),
                    pay_width,
                    fixed=True,
                )
                # Official support confirms realtime popularity can be blank
                # before all finish positions are finalized.
                cls._require_optional_digits(
                    f"{popularity}{suffix}",
                    record.get(f"{popularity}{suffix}"),
                    popularity_width,
                    fixed=True,
                )

        for index, widths in enumerate(((4, 9, 3),) * 3):
            for offset, width in enumerate(widths, start=1):
                field_name = f"Yobi{index * 3 + offset}"
                cls._require_optional_digits(field_name, record.get(field_name), width, fixed=True)

        legacy = record.get(cls.LEGACY_RESERVED_FIELD)
        if legacy not in (None, ""):
            if (
                not isinstance(legacy, str)
                or len(legacy) != 228
                or not legacy.isascii()
                or any(character not in "0123456789abcdefABCDEF" for character in legacy)
            ):
                raise ValueError(
                    f"HR {cls.LEGACY_RESERVED_FIELD} must be exactly 228 hexadecimal characters"
                )
            if race_date >= cls.SANRENTAN_AVAILABLE_FROM:
                raise ValueError(f"HR {cls.LEGACY_RESERVED_FIELD} is only valid before 2004-08-14")

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        """
        HRレコードをパースしてフィールド辞書を返す

        Args:
            data: パース対象のバイトデータ

        Returns:
            フィールド名をキーとした辞書、エラー時はNone
        """
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)

            # フィールド抽出
            result = {}
            pos = 0

            # 1. レコード種別ID (位置:1, 長さ:2)
            result["RecordSpec"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 2. データ区分 (位置:3, 長さ:1)
            result["DataKubun"] = self.decode_field(data[pos : pos + 1])
            pos += 1

            # 3. データ作成年月日 (位置:4, 長さ:8)
            result["MakeDate"] = self.decode_field(data[pos : pos + 8])
            pos += 8

            # 4. 開催年 (位置:12, 長さ:4)
            result["Year"] = self.decode_field(data[pos : pos + 4])
            pos += 4

            # 5. 開催月日 (位置:16, 長さ:4)
            result["MonthDay"] = self.decode_field(data[pos : pos + 4])
            pos += 4

            # 6. 競馬場コード (位置:20, 長さ:2)
            result["JyoCD"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 7. 開催回[第N回] (位置:22, 長さ:2)
            result["Kaiji"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 8. 開催日目[N日目] (位置:24, 長さ:2)
            result["Nichiji"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 9. レース番号 (位置:26, 長さ:2)
            result["RaceNum"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 10. 登録頭数 (位置:28, 長さ:2)
            result["TorokuTosu"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 11. 出走頭数 (位置:30, 長さ:2)
            result["SyussoTosu"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 12-20. 不成立フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"FuseirituFlag{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # 21-29. 特払フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"TokubaraiFlag{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # 30-38. 返還フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"HenkanFlag{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # 39-66. 返還馬番情報 (各1バイト × 28)
            for i in range(1, 29):
                result[f"HenkanUma{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # 67-74. 返還枠番情報 (各1バイト × 8)
            for i in range(1, 9):
                result[f"HenkanWaku{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # 75-82. 返還同枠情報 (各1バイト × 8) - JV-Data仕様書: 位置95, 8バイト
            for i in range(1, 9):
                result[f"HenkanDoWaku{i}"] = self.decode_field(data[pos : pos + 1])
                pos += 1

            # ここから配列データ
            # pos = 102 at this point (JV-Data仕様書: 単勝払戻は位置103から、0始まりで102)

            # 払戻配列はすべての要素を抽出する。
            # 1件目は後方互換のため接尾辞なし (TanUmaban)、2件目以降は
            # 番号付き (TanUmaban2, TanUmaban3, ...)。
            # 複勝は最大5頭、ワイドは最大7組が同時に払い戻されるため、
            # 1件目のみの抽出では的中の大半を取りこぼす (2026-06-11 修正、
            # jrvltsql-nar#6 と同型)。

            def _entry_suffix(index: int) -> str:
                return "" if index == 1 else str(index)

            def _extract_array(prefix_a, prefix_b, prefix_c, count, len_a, len_b, len_c, start):
                p = start
                for i in range(1, count + 1):
                    sfx = _entry_suffix(i)
                    result[f"{prefix_a}{sfx}"] = self.decode_field(data[p : p + len_a])
                    result[f"{prefix_b}{sfx}"] = self.decode_field(
                        data[p + len_a : p + len_a + len_b]
                    )
                    result[f"{prefix_c}{sfx}"] = self.decode_field(
                        data[p + len_a + len_b : p + len_a + len_b + len_c]
                    )
                    p += len_a + len_b + len_c
                return p

            # 単勝払戻 (3件配列: 馬番2 + 払戻9 + 人気2 = 13バイト × 3)
            pos = _extract_array("TanUmaban", "TanPay", "TanNinki", 3, 2, 9, 2, pos)

            # 複勝払戻 (5件配列: 馬番2 + 払戻9 + 人気2 = 13バイト × 5)
            pos = _extract_array("FukuUmaban", "FukuPay", "FukuNinki", 5, 2, 9, 2, pos)

            # 枠連払戻 (3件配列: 組合せ2 + 払戻9 + 人気2 = 13バイト × 3)
            pos = _extract_array("WakuKumi", "WakuPay", "WakuNinki", 3, 2, 9, 2, pos)

            # 馬連払戻 (3件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 3)
            pos = _extract_array("UmarenKumi", "UmarenPay", "UmarenNinki", 3, 4, 9, 3, pos)

            # ワイド払戻 (7件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 7)
            pos = _extract_array("WideKumi", "WidePay", "WideNinki", 7, 4, 9, 3, pos)

            # 予備 (3件配列: 16バイト × 3 = 48バイト)
            for index in range(3):
                start = pos + index * 16
                base = index * 3 + 1
                result[f"Yobi{base}"] = self.decode_field(data[start : start + 4])
                result[f"Yobi{base + 1}"] = self.decode_field(data[start + 4 : start + 13])
                result[f"Yobi{base + 2}"] = self.decode_field(data[start + 13 : start + 16])
            pos += 48

            # 馬単払戻 (6件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 6)
            pos = _extract_array("UmatanKumi", "UmatanPay", "UmatanNinki", 6, 4, 9, 3, pos)

            # 三連複払戻 (3件配列: 組合せ6 + 払戻9 + 人気3 = 18バイト × 3)
            pos = _extract_array(
                "SanrenfukuKumi", "SanrenfukuPay", "SanrenfukuNinki", 3, 6, 9, 3, pos
            )

            # 三連単払戻 (6件配列: 組合せ6 + 払戻9 + 人気4 = 19バイト × 6)
            pos = _extract_array("SanrentanKumi", "SanrentanPay", "SanrentanNinki", 6, 6, 9, 4, pos)

            race_date = date(
                int(result["Year"]),
                int(result["MonthDay"][:2]),
                int(result["MonthDay"][2:]),
            )
            if result["DataKubun"] == "9":
                result[self.STATUS9_OPAQUE_FIELD] = data[27:717].hex()
                preserved = {
                    "RecordSpec",
                    "DataKubun",
                    "MakeDate",
                    *self.KEY_COLUMNS,
                    self.STATUS9_OPAQUE_FIELD,
                }
                for field_name in tuple(result):
                    if field_name not in preserved:
                        result[field_name] = ""
                result[self.LEGACY_RESERVED_FIELD] = ""
            elif race_date < self.SANRENTAN_AVAILABLE_FROM:
                result[self.STATUS9_OPAQUE_FIELD] = ""
                result[self.LEGACY_RESERVED_FIELD] = data[603:717].hex()
                for index in range(1, 7):
                    suffix = "" if index == 1 else str(index)
                    for prefix in ("SanrentanKumi", "SanrentanPay", "SanrentanNinki"):
                        result[f"{prefix}{suffix}"] = ""
            else:
                result[self.STATUS9_OPAQUE_FIELD] = ""
                result[self.LEGACY_RESERVED_FIELD] = ""

            # レコード区切 (2バイト)
            if pos < len(data):
                result["RecordDelimiter"] = self.decode_field(data[pos : pos + 2])

            self.validate_current_fields(result)

            return result

        except Exception as e:
            self.logger.error(f"HRレコードパース中にエラー: {e}")
            return None
