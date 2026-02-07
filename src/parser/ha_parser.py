#!/usr/bin/env python
from __future__ import annotations

"""
HAレコードパーサー: 地方競馬 払戻

NV-Link (UmaConn/地方競馬DATA) の払戻レコードをパースする。
HAレコードはJRA HR（中央競馬 払戻）に相当するが、フォーマットが異なる。

構造:
  ヘッダー (31バイト): RecordSpec(2) + DataKubun(1) + MakeDate(8) + KaisaiDate(8)
                       + JyoCD(2) + Kaiji(2) + Nichiji(2) + RaceNum(2)
                       + TorokuTosu(2) + SyussoTosu(2)
  フラグ領域 (32バイト): HatsubaiFlag(1) + Reserved(16) + Padding(15)
  払戻データ: 15バイト × N エントリー
    各エントリー: Kumi(2) + Pay(13)
    セクション区切り: 15バイトスペース
  末尾: 合計払戻(15バイト) + レコード区切り(\\r\\n)

レコード長: 1032バイト
"""


from src.utils.logger import get_logger


class HAParser:
    """
    HAレコードパーサー

    地方競馬 払戻
    レコード長: 1032 bytes
    VBテーブル名: HARAI_CHIHO (地方競馬用)
    """

    RECORD_TYPE = "HA"
    RECORD_LENGTH = 1032
    ENTRY_SIZE = 15  # kumi(2) + pay(13)
    HEADER_SIZE = 31  # RecordSpec through SyussoTosu
    FLAG_SIZE = 32  # HatsubaiFlag + reserved + padding

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def _parse_payout_entries(self, data: bytes, start: int) -> list[tuple[str, int]]:
        """払戻エントリーをパースする。

        Args:
            data: レコード全体のバイトデータ
            start: 払戻データの開始位置

        Returns:
            (kumi, pay) のリスト。kumi='00'は合計行。
        """
        entries = []
        pos = start
        # 末尾の \r\n (2バイト) + 合計行の後のパディングを考慮
        end = len(data) - 2  # Skip \r\n at end

        while pos + self.ENTRY_SIZE <= end:
            entry_bytes = data[pos : pos + self.ENTRY_SIZE]
            entry_str = self.decode_field(entry_bytes)

            # 空白エントリー = セクション区切り → スキップ
            if not entry_str:
                pos += self.ENTRY_SIZE
                continue

            kumi = self.decode_field(data[pos : pos + 2])
            pay_str = self.decode_field(data[pos + 2 : pos + self.ENTRY_SIZE])

            try:
                pay = int(pay_str) if pay_str else 0
            except ValueError:
                pay = 0

            entries.append((kumi, pay))
            pos += self.ENTRY_SIZE

        return entries

    def parse(self, data: bytes) -> dict | None:
        """
        HAレコードをパースしてフィールド辞書を返す

        Args:
            data: パース対象のバイトデータ

        Returns:
            フィールド名をキーとした辞書、エラー時はNone
        """
        try:
            # Strip trailing CRLF if present
            if data.endswith(b"\r\n"):
                data = data[:-2]
            elif data.endswith(b"\n"):
                data = data[:-1]

            if len(data) < self.HEADER_SIZE + self.FLAG_SIZE:
                self.logger.warning(
                    f"HAレコード長不足: expected>={self.HEADER_SIZE + self.FLAG_SIZE}, actual={len(data)}"
                )
                return None

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

            # 4. 開催年月日 (位置:12, 長さ:8)
            # ※ JRA HR では Year(4)+MonthDay(4) だが、NAR HA では KaisaiDate(8)
            result["KaisaiDate"] = self.decode_field(data[pos : pos + 8])
            pos += 8

            # 5. 競馬場コード (位置:20, 長さ:2)
            result["JyoCD"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 6. 開催回[第N回] (位置:22, 長さ:2)
            result["Kaiji"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 7. 開催日目[N日目] (位置:24, 長さ:2)
            result["Nichiji"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 8. レース番号 (位置:26, 長さ:2)
            result["RaceNum"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 9. 登録頭数 (位置:28, 長さ:2)
            result["TorokuTosu"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 10. 出走頭数 (位置:30, 長さ:2)
            result["SyussoTosu"] = self.decode_field(data[pos : pos + 2])
            pos += 2

            # 11. 発売フラグ (位置:32, 長さ:1)
            result["HatsubaiFlag"] = self.decode_field(data[pos : pos + 1])
            pos += 1

            # 12. 予約/フラグ領域 (位置:33, 長さ:31)
            # 16バイトのゼロ + 15バイトのスペース
            result["Reserved"] = self.decode_field(data[pos : pos + 31])
            pos += 31

            # pos = 63: 払戻データ開始
            # 15バイトエントリー: Kumi(2) + Pay(13)
            entries = self._parse_payout_entries(data, pos)

            # エントリーを結果辞書に格納
            # 通常エントリー（kumi != '00'）と合計行（kumi == '00'）を分離
            payout_entries = []
            for kumi, pay in entries:
                if kumi in ("00", "0", ""):
                    result["TotalPay"] = str(pay)  # Override default
                else:
                    payout_entries.append({"Kumi": kumi, "Pay": str(pay)})

            # 先頭の払戻エントリーをフラットフィールドとして格納
            # （DBテーブル互換のため）- デフォルト値を設定
            result.setdefault("TotalPay", "0")
            result["PayKumi1"] = ""
            result["PayAmount1"] = "0"
            result["PayKumi2"] = ""
            result["PayAmount2"] = "0"
            result["PayKumi3"] = ""
            result["PayAmount3"] = "0"

            if payout_entries:
                result["PayKumi1"] = payout_entries[0]["Kumi"]
                result["PayAmount1"] = payout_entries[0]["Pay"]
            if len(payout_entries) > 1:
                result["PayKumi2"] = payout_entries[1]["Kumi"]
                result["PayAmount2"] = payout_entries[1]["Pay"]
            if len(payout_entries) > 2:
                result["PayKumi3"] = payout_entries[2]["Kumi"]
                result["PayAmount3"] = payout_entries[2]["Pay"]

            # 全エントリー数を記録
            result["PayoutCount"] = str(len(payout_entries))

            return result

        except Exception as e:
            self.logger.exception(f"HAレコードパース中にエラー: {e}")
            return None
