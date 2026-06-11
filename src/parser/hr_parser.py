#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HRレコードパーサー: ４．払戻

JV-Data仕様書 Ver.4.9.0.1に基づく払戻レコードのパース
払戻データは配列構造のため全要素を抽出する (複勝5件・ワイド7件など)
"""

from typing import Dict, Optional
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

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        try:
            # cp932でデコード、空白を除去
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        """
        HRレコードをパースしてフィールド辞書を返す

        Args:
            data: パース対象のバイトデータ

        Returns:
            フィールド名をキーとした辞書、エラー時はNone
        """
        try:
            # レコード長チェック（最小限のデータがあるかどうか）
            if len(data) < 100:
                self.logger.warning(
                    f"HRレコード長不足: expected>={self.RECORD_LENGTH}, actual={len(data)}"
                )
                return None

            # フィールド抽出
            result = {}
            pos = 0

            # 1. レコード種別ID (位置:1, 長さ:2)
            result["RecordSpec"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 2. データ区分 (位置:3, 長さ:1)
            result["DataKubun"] = self.decode_field(data[pos:pos+1])
            pos += 1

            # 3. データ作成年月日 (位置:4, 長さ:8)
            result["MakeDate"] = self.decode_field(data[pos:pos+8])
            pos += 8

            # 4. 開催年 (位置:12, 長さ:4)
            result["Year"] = self.decode_field(data[pos:pos+4])
            pos += 4

            # 5. 開催月日 (位置:16, 長さ:4)
            result["MonthDay"] = self.decode_field(data[pos:pos+4])
            pos += 4

            # 6. 競馬場コード (位置:20, 長さ:2)
            result["JyoCD"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 7. 開催回[第N回] (位置:22, 長さ:2)
            result["Kaiji"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 8. 開催日目[N日目] (位置:24, 長さ:2)
            result["Nichiji"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 9. レース番号 (位置:26, 長さ:2)
            result["RaceNum"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 10. 登録頭数 (位置:28, 長さ:2)
            result["TorokuTosu"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 11. 出走頭数 (位置:30, 長さ:2)
            result["SyussoTosu"] = self.decode_field(data[pos:pos+2])
            pos += 2

            # 12-20. 不成立フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"FuseirituFlag{i}"] = self.decode_field(data[pos:pos+1])
                pos += 1

            # 21-29. 特払フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"TokubaraiFlag{i}"] = self.decode_field(data[pos:pos+1])
                pos += 1

            # 30-38. 返還フラグ (各1バイト × 9)
            for i in range(1, 10):
                result[f"HenkanFlag{i}"] = self.decode_field(data[pos:pos+1])
                pos += 1

            # 39-66. 返還馬番情報 (各1バイト × 28)
            for i in range(1, 29):
                result[f"HenkanUma{i}"] = self.decode_field(data[pos:pos+1])
                pos += 1

            # 67-74. 返還枠番情報 (各1バイト × 8)
            for i in range(1, 9):
                result[f"HenkanWaku{i}"] = self.decode_field(data[pos:pos+1])
                pos += 1

            # 75-82. 返還同枠情報 (各1バイト × 8) - JV-Data仕様書: 位置95, 8バイト
            for i in range(1, 9):
                result[f"HenkanDoWaku{i}"] = self.decode_field(data[pos:pos+1])
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
                    result[f"{prefix_a}{sfx}"] = self.decode_field(data[p:p + len_a])
                    result[f"{prefix_b}{sfx}"] = self.decode_field(data[p + len_a:p + len_a + len_b])
                    result[f"{prefix_c}{sfx}"] = self.decode_field(
                        data[p + len_a + len_b:p + len_a + len_b + len_c]
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
            result["Yobi1"] = self.decode_field(data[pos:pos+4])
            result["Yobi2"] = self.decode_field(data[pos+4:pos+13])
            result["Yobi3"] = self.decode_field(data[pos+13:pos+16])
            pos += 48  # 3件分スキップ

            # 馬単払戻 (6件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 6)
            pos = _extract_array("UmatanKumi", "UmatanPay", "UmatanNinki", 6, 4, 9, 3, pos)

            # 三連複払戻 (3件配列: 組合せ6 + 払戻9 + 人気3 = 18バイト × 3)
            pos = _extract_array("SanrenfukuKumi", "SanrenfukuPay", "SanrenfukuNinki", 3, 6, 9, 3, pos)

            # 三連単払戻 (6件配列: 組合せ6 + 払戻9 + 人気4 = 19バイト × 6)
            pos = _extract_array("SanrentanKumi", "SanrentanPay", "SanrentanNinki", 6, 6, 9, 4, pos)

            # レコード区切 (2バイト)
            if pos < len(data):
                result["RecordDelimiter"] = self.decode_field(data[pos:pos+2])

            return result

        except Exception as e:
            self.logger.error(f"HRレコードパース中にエラー: {e}")
            return None
