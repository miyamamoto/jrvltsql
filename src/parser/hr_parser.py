#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HRレコードパーサー: ４．払戻

JV-Data仕様書 Ver.4.9.0.1に基づく払戻レコードのパース
払戻データは配列構造になっているため、最初の1件目を抽出する
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

            # 単勝払戻 (3件配列: 馬番2 + 払戻9 + 人気2 = 13バイト × 3 = 39バイト)
            # 最初の1件目のみ抽出
            result["TanUmaban"] = self.decode_field(data[pos:pos+2])
            result["TanPay"] = self.decode_field(data[pos+2:pos+11])
            result["TanNinki"] = self.decode_field(data[pos+11:pos+13])
            pos += 39  # 3件分スキップ

            # 複勝払戻 (5件配列: 馬番2 + 払戻9 + 人気2 = 13バイト × 5 = 65バイト)
            # 最初の1件目のみ抽出
            result["FukuUmaban"] = self.decode_field(data[pos:pos+2])
            result["FukuPay"] = self.decode_field(data[pos+2:pos+11])
            result["FukuNinki"] = self.decode_field(data[pos+11:pos+13])
            pos += 65  # 5件分スキップ

            # 枠連払戻 (3件配列: 組合せ2 + 払戻9 + 人気2 = 13バイト × 3 = 39バイト)
            # 最初の1件目のみ抽出
            result["WakuKumi"] = self.decode_field(data[pos:pos+2])
            result["WakuPay"] = self.decode_field(data[pos+2:pos+11])
            result["WakuNinki"] = self.decode_field(data[pos+11:pos+13])
            pos += 39  # 3件分スキップ

            # 馬連払戻 (3件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 3 = 48バイト)
            # 最初の1件目のみ抽出
            result["UmarenKumi"] = self.decode_field(data[pos:pos+4])
            result["UmarenPay"] = self.decode_field(data[pos+4:pos+13])
            result["UmarenNinki"] = self.decode_field(data[pos+13:pos+16])
            pos += 48  # 3件分スキップ

            # ワイド払戻 (7件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 7 = 112バイト)
            # 最初の1件目のみ抽出
            result["WideKumi"] = self.decode_field(data[pos:pos+4])
            result["WidePay"] = self.decode_field(data[pos+4:pos+13])
            result["WideNinki"] = self.decode_field(data[pos+13:pos+16])
            pos += 112  # 7件分スキップ

            # 予備 (3件配列: 16バイト × 3 = 48バイト)
            result["Yobi1"] = self.decode_field(data[pos:pos+4])
            result["Yobi2"] = self.decode_field(data[pos+4:pos+13])
            result["Yobi3"] = self.decode_field(data[pos+13:pos+16])
            pos += 48  # 3件分スキップ

            # 馬単払戻 (6件配列: 組合せ4 + 払戻9 + 人気3 = 16バイト × 6 = 96バイト)
            # 最初の1件目のみ抽出
            result["UmatanKumi"] = self.decode_field(data[pos:pos+4])
            result["UmatanPay"] = self.decode_field(data[pos+4:pos+13])
            result["UmatanNinki"] = self.decode_field(data[pos+13:pos+16])
            pos += 96  # 6件分スキップ

            # 三連複払戻 (3件配列: 組合せ6 + 払戻9 + 人気3 = 18バイト × 3 = 54バイト)
            # 最初の1件目のみ抽出
            result["SanrenfukuKumi"] = self.decode_field(data[pos:pos+6])
            result["SanrenfukuPay"] = self.decode_field(data[pos+6:pos+15])
            result["SanrenfukuNinki"] = self.decode_field(data[pos+15:pos+18])
            pos += 54  # 3件分スキップ

            # 三連単払戻 (6件配列: 組合せ6 + 払戻9 + 人気4 = 19バイト × 6 = 114バイト)
            # 最初の1件目のみ抽出
            result["SanrentanKumi"] = self.decode_field(data[pos:pos+6])
            result["SanrentanPay"] = self.decode_field(data[pos+6:pos+15])
            result["SanrentanNinki"] = self.decode_field(data[pos+15:pos+19])
            pos += 114  # 6件分スキップ

            # レコード区切 (2バイト)
            if pos < len(data):
                result["RecordDelimiter"] = self.decode_field(data[pos:pos+2])

            return result

        except Exception as e:
            self.logger.error(f"HRレコードパース中にエラー: {e}")
            return None
