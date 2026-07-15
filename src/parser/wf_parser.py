#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser for the official 7,215-byte JV-Data WF (WIN5) record."""

import json
from typing import Dict, Optional

from src.utils.logger import get_logger


class WFParser:
    """Parse all five active-vote counts and all 243 WIN5 payout slots."""

    RECORD_TYPE = "WF"
    RECORD_LENGTH = 7215
    PAYOUT_COUNT = 243
    PAYOUT_LENGTH = 29

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        try:
            return data.decode("cp932", errors="replace").strip()
        except Exception:
            return ""

    def parse(self, data: bytes) -> Optional[Dict[str, str]]:
        if len(data) < self.RECORD_LENGTH:
            self.logger.warning(
                f"WFレコード長不足: expected={self.RECORD_LENGTH}, actual={len(data)}"
            )
            return None

        try:
            result = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "Year": self.decode_field(data[11:15]),
                "MonthDay": self.decode_field(data[15:19]),
                "Yobi1": self.decode_field(data[19:21]),
            }

            for index in range(5):
                start = 21 + index * 8
                result[f"RaceInfo{index + 1}"] = self.decode_field(data[start:start + 8])

            result["Yobi2"] = self.decode_field(data[61:67])
            result["HatubaiHyosu"] = self.decode_field(data[67:78])
            for index in range(5):
                start = 78 + index * 11
                result[f"YukoHyosu{index + 1}"] = self.decode_field(data[start:start + 11])

            result.update(
                {
                    "HenkanFlag": self.decode_field(data[133:134]),
                    "FuseirituFlag": self.decode_field(data[134:135]),
                    "TekichuNasiFlag": self.decode_field(data[135:136]),
                    "CarryOverStart": self.decode_field(data[136:151]),
                    "CarryOverBalance": self.decode_field(data[151:166]),
                }
            )

            payouts = []
            for index in range(self.PAYOUT_COUNT):
                start = 166 + index * self.PAYOUT_LENGTH
                payouts.append(
                    {
                        "Kumi": self.decode_field(data[start:start + 10]),
                        "PayJyushosiki": self.decode_field(data[start + 10:start + 19]),
                        "TekichuHyosu": self.decode_field(data[start + 19:start + 29]),
                    }
                )
            result["PayoutsJson"] = json.dumps(
                payouts, ensure_ascii=False, separators=(",", ":")
            )
            result["RecordDelimiter"] = self.decode_field(data[7213:7215])
            return result
        except Exception as exc:
            self.logger.error(f"WFレコードパース中にエラー: {exc}")
            return None
