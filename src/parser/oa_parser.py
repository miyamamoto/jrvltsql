#!/usr/bin/env python
"""
OAレコードパーサー: 地方競馬 オッズ

NV-Link (UmaConn/地方競馬DATA) のオッズレコードをパースする。
OAレコードはJRA O1-O6（中央競馬 オッズ）に相当するが、フォーマットが異なる。

構造 (推定):
  ヘッダー: RecordSpec(2) + DataKubun(1) + MakeDate(8) + KaisaiDate(8)
           + JyoCD(2) + Kaiji(2) + Nichiji(2) + RaceNum(2)
  オッズデータ: OddsType + Kumi + Odds + Ninki の繰り返し

レコード長: 不明（実データで確認が必要）

Note:
  現時点ではヘッダー部分のみパースし、オッズ本体は今後実データを確認して実装する。
"""

from src.utils.logger import get_logger


class OAParser:
    """
    OAレコードパーサー

    地方競馬 オッズ
    """

    RECORD_TYPE = "OA"
    HEADER_SIZE = 27  # RecordSpec(2) + DataKubun(1) + MakeDate(8) + KaisaiDate(8) + JyoCD(2) + Kaiji(2) + Nichiji(2) + RaceNum(2)

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        """バイトデータをデコードして文字列に変換"""
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def parse(self, data: bytes) -> "dict | None":
        """
        OAレコードをパースしてフィールド辞書を返す。

        現時点ではヘッダー情報のみパースする。
        オッズ本体のパースは実データのフォーマット確認後に実装予定。

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

            if len(data) < self.HEADER_SIZE:
                self.logger.warning(
                    f"OAレコード長不足: expected>={self.HEADER_SIZE}, actual={len(data)}"
                )
                return None

            result = {}
            pos = 0

            result["RecordSpec"] = self.decode_field(data[pos:pos + 2])
            pos += 2

            result["DataKubun"] = self.decode_field(data[pos:pos + 1])
            pos += 1

            result["MakeDate"] = self.decode_field(data[pos:pos + 8])
            pos += 8

            result["KaisaiDate"] = self.decode_field(data[pos:pos + 8])
            pos += 8

            result["JyoCD"] = self.decode_field(data[pos:pos + 2])
            pos += 2

            result["Kaiji"] = self.decode_field(data[pos:pos + 2])
            pos += 2

            result["Nichiji"] = self.decode_field(data[pos:pos + 2])
            pos += 2

            result["RaceNum"] = self.decode_field(data[pos:pos + 2])
            pos += 2

            # TODO: オッズ本体のパースは実データのフォーマット確認後に実装
            # 暫定的にヘッダーのみ返す
            result["OddsType"] = ""
            result["Kumi"] = ""
            result["Odds"] = 0.0
            result["Ninki"] = 0

            self.logger.debug(
                "OAレコードパース (ヘッダーのみ)",
                kaisai_date=result.get("KaisaiDate"),
                jyo_cd=result.get("JyoCD"),
                race_num=result.get("RaceNum"),
                data_length=len(data),
            )

            return result

        except Exception as e:
            self.logger.exception(f"OAレコードパース中にエラー: {e}")
            return None
