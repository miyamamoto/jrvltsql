#!/usr/bin/env python
"""CK parser for the complete official current 6,870-byte layout."""

from __future__ import annotations

from typing import Any

from src.jvlink.constants import ENCODING_JVDATA
from src.parser.base import validate_fixed_record
from src.parser.converters import ConversionError, convert_value
from src.utils.logger import get_logger


class CKParser:
    """Parse one CK record into a compatibility parent and complete child rows."""

    record_type = "CK"
    RECORD_TYPE = "CK"
    RECORD_LENGTH = 6870

    _UMA_GROUPS = (
        ("ChakuSogo", 100, 1),
        ("ChakuChuo", 118, 1),
        ("ChakuKaisuBa", 136, 7),
        ("ChakuKaisuJyotai", 262, 12),
        ("ChakuKaisuSibaKyori", 478, 9),
        ("ChakuKaisuDirtKyori", 640, 9),
        ("ChakuKaisuJyoSiba", 802, 10),
        ("ChakuKaisuJyoDirt", 982, 10),
        ("ChakuKaisuJyoSyogai", 1162, 10),
    )
    _COMPATIBILITY_COUNT_NAMES = (
        "TotalChakuCount",
        "ChuoChakuCount",
        "SibaChoChaku",
        "SibaMigiChaku",
        "SibaHidariChaku",
        "DirtChoChaku",
        "DirtMigiChaku",
        "DirtHidariChaku",
        "SyogaiChaku",
        "SibaRyoChaku",
        "SibaYayaChaku",
        "SibaOmoChaku",
        "SibaFuChaku",
        "DirtRyoChaku",
        "DirtYayaChaku",
        "DirtOmoChaku",
        "DirtFuChaku",
        "SyogaiRyoChaku",
        "SyogaiYayaChaku",
        "SyogaiOmoChaku",
        "SyogaiFuChaku",
        "Siba1200IkaChaku",
        "Siba1201_1400Chaku",
        "Siba1401_1600Chaku",
        "Siba1601_1800Chaku",
        "Siba1801_2000Chaku",
        "Siba2001_2200Chaku",
        "Siba2201_2400Chaku",
        "Siba2401_2800Chaku",
        "Siba2801OverChaku",
        "Dirt1200IkaChaku",
        "Dirt1201_1400Chaku",
        "Dirt1401_1600Chaku",
        "Dirt1601_1800Chaku",
        "Dirt1801_2000Chaku",
        "Dirt2001_2200Chaku",
        "Dirt2201_2400Chaku",
        "Dirt2401_2800Chaku",
        "Dirt2801OverChaku",
        "SapporoSibaChaku",
        "HakodateSibaChaku",
        "FukushimaSibaChaku",
        "NiigataSibaChaku",
        "TokyoSibaChaku",
        "NakayamaSibaChaku",
        "ChukyoSibaChaku",
        "KyotoSibaChaku",
        "HanshinSibaChaku",
        "KokuraSibaChaku",
        "SapporoDirtChaku",
        "HakodateDirtChaku",
        "FukushimaDirtChaku",
        "NiigataDirtChaku",
        "TokyoDirtChaku",
        "NakayamaDirtChaku",
        "ChukyoDirtChaku",
        "KyotoDirtChaku",
        "HanshinDirtChaku",
        "KokuraDirtChaku",
        "SapporoSyogaiChaku",
        "HakodateSyogaiChaku",
        "FukushimaSyogaiChaku",
        "NiigataSyogaiChaku",
        "TokyoSyogaiChaku",
        "NakayamaSyogaiChaku",
        "ChukyoSyogaiChaku",
        "KyotoSyogaiChaku",
        "HanshinSyogaiChaku",
        "KokuraSyogaiChaku",
    )

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        return data.decode(ENCODING_JVDATA, errors="strict").strip()

    @staticmethod
    def _require_digits(name: str, value: str) -> None:
        if not value.isascii() or not value.isdigit():
            raise ValueError(f"{name} must contain only ASCII digits")

    def _parent_key(self, data: bytes) -> dict[str, str]:
        return {
            "Year": self.decode_field(data[11:15]),
            "MonthDay": self.decode_field(data[15:19]),
            "JyoCD": self.decode_field(data[19:21]),
            "Kaiji": self.decode_field(data[21:23]),
            "Nichiji": self.decode_field(data[23:25]),
            "RaceNum": self.decode_field(data[25:27]),
            "KettoNum": self.decode_field(data[27:37]),
        }

    def _parse_uma_rows(self, data: bytes, key: dict[str, str]) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        uma_start = 27
        for group_name, relative_start, count in self._UMA_GROUPS:
            for number in range(1, count + 1):
                start = uma_start + relative_start + 18 * (number - 1)
                row = {
                    **key,
                    "EntityKubun": "UMA",
                    "PeriodNum": "0",
                    "MetricKubun": group_name,
                    "BucketNum": str(number),
                }
                for rank in range(1, 7):
                    offset = start + 3 * (rank - 1)
                    row[f"Count{rank}"] = self.decode_field(data[offset : offset + 3])
                rows.append(row)

        row = {
            **key,
            "EntityKubun": "UMA",
            "PeriodNum": "0",
            "MetricKubun": "Kyakusitu",
            "BucketNum": "1",
        }
        for rank in range(1, 5):
            offset = 1369 + 3 * (rank - 1)
            row[f"Count{rank}"] = self.decode_field(data[offset : offset + 3])
        row["Count5"] = ""
        row["Count6"] = ""
        rows.append(row)
        return rows

    def _parse_hon_ruikei(
        self,
        data: bytes,
        *,
        start: int,
        key: dict[str, str],
        actor_type: str,
        number: int,
    ) -> tuple[dict[str, str], list[dict[str, str]]]:
        summary = {
            **key,
            "EntityKubun": actor_type,
            "PeriodNum": str(number),
            "HonSyokinTotal": "",
            "FukaSyokin": "",
        }
        count_rows: list[dict[str, str]] = []
        cursor = start
        for name, width in (
            ("SetYear", 4),
            ("HonSyokinHeichi", 10),
            ("HonSyokinSyogai", 10),
            ("FukaSyokinHeichi", 10),
            ("FukaSyokinSyogai", 10),
        ):
            summary[name] = self.decode_field(data[cursor : cursor + width])
            cursor += width
        for group, count, width in (
            ("ChakuKaisuSiba", 1, 5),
            ("ChakuKaisuDirt", 1, 5),
            ("ChakuKaisuSyogai", 1, 4),
            ("ChakuKaisuSibaKyori", 9, 4),
            ("ChakuKaisuDirtKyori", 9, 4),
            ("ChakuKaisuJyoSiba", 10, 4),
            ("ChakuKaisuJyoDirt", 10, 4),
            ("ChakuKaisuJyoSyogai", 10, 3),
        ):
            for index in range(1, count + 1):
                row = {
                    **key,
                    "EntityKubun": actor_type,
                    "PeriodNum": str(number),
                    "MetricKubun": group,
                    "BucketNum": str(index),
                }
                for rank in range(1, 7):
                    row[f"Count{rank}"] = self.decode_field(data[cursor : cursor + width])
                    cursor += width
                count_rows.append(row)
        if cursor != start + 1220:
            raise ValueError("CK professional result block width mismatch")
        if len(count_rows) != 51:
            raise ValueError("CK professional count row cardinality mismatch")
        return summary, count_rows

    def _parse_sei_ruikei(
        self,
        data: bytes,
        *,
        start: int,
        key: dict[str, str],
        actor_type: str,
        number: int,
    ) -> tuple[dict[str, str], dict[str, str]]:
        summary = {
            **key,
            "EntityKubun": actor_type,
            "PeriodNum": str(number),
            "HonSyokinHeichi": "",
            "HonSyokinSyogai": "",
            "FukaSyokinHeichi": "",
            "FukaSyokinSyogai": "",
        }
        cursor = start
        for name, width in (("SetYear", 4), ("HonSyokinTotal", 10), ("FukaSyokin", 10)):
            summary[name] = self.decode_field(data[cursor : cursor + width])
            cursor += width
        row = {
            **key,
            "EntityKubun": actor_type,
            "PeriodNum": str(number),
            "MetricKubun": "ChakuKaisu",
            "BucketNum": "1",
        }
        for rank in range(1, 7):
            row[f"Count{rank}"] = self.decode_field(data[cursor : cursor + 6])
            cursor += 6
        if cursor != start + 60:
            raise ValueError("CK owner/breeder result block width mismatch")
        return summary, row

    def parse(self, data: bytes) -> dict[str, Any] | None:
        """Return the compatibility parent plus all official normalized rows."""
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            result: dict[str, Any] = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": convert_value(self.decode_field(data[3:11]), "DATE"),
                "Year": convert_value(self.decode_field(data[11:15]), "SMALLINT"),
                "MonthDay": convert_value(self.decode_field(data[15:19]), "MONTH_DAY"),
                "JyoCD": self.decode_field(data[19:21]),
                "Kaiji": convert_value(self.decode_field(data[21:23]), "SMALLINT"),
                "Nichiji": convert_value(self.decode_field(data[23:25]), "SMALLINT"),
                "RaceNum": convert_value(self.decode_field(data[25:27]), "SMALLINT"),
                "KettoNum": self.decode_field(data[27:37]),
                "Bamei": self.decode_field(data[37:73]),
                "HeichiHonsyokinTotal": self.decode_field(data[73:82]),
                "SyogaiHonsyokinTotal": self.decode_field(data[82:91]),
                "HeichiFukasyokinTotal": self.decode_field(data[91:100]),
                "SyogaiFukasyokinTotal": self.decode_field(data[100:109]),
                "HeichiSyutokuTotal": self.decode_field(data[109:118]),
                "SyogaiSyutokuTotal": self.decode_field(data[118:127]),
            }
            if result["DataKubun"] not in {"0", "1", "2"}:
                raise ValueError("CK DataKubun must be 0, 1, or 2")

            key = self._parent_key(data)
            for name, value in key.items():
                self._require_digits(name, value)
            if result["DataKubun"] == "0":
                result["_ck_chaku_rows"] = []
                result["_ck_ruikei_rows"] = []
                return result

            for name in (
                "HeichiHonsyokinTotal",
                "SyogaiHonsyokinTotal",
                "HeichiFukasyokinTotal",
                "SyogaiFukasyokinTotal",
                "HeichiSyutokuTotal",
                "SyogaiSyutokuTotal",
            ):
                self._require_digits(name, str(result[name]))
            uma_rows = self._parse_uma_rows(data, key)
            if len(uma_rows) != 70:
                raise ValueError("CK horse count row cardinality mismatch")
            for name, row in zip(self._COMPATIBILITY_COUNT_NAMES, uma_rows[:-1], strict=True):
                result[name] = row["Count1"]
            result["KyakusituKeiko"] = uma_rows[-1]["Count1"]
            result["RegisteredRaceCount"] = self.decode_field(data[1381:1384])
            self._require_digits("RegisteredRaceCount", result["RegisteredRaceCount"])

            result.update(
                {
                    "KisyuCode": self.decode_field(data[1384:1389]),
                    "KisyuName": self.decode_field(data[1389:1423]),
                    "KisyuResultsInfo": self.decode_field(data[1423:2643]),
                    "ChokyosiCode": self.decode_field(data[3863:3868]),
                    "ChokyosiName": self.decode_field(data[3868:3902]),
                    "ChokyosiResultsInfo": self.decode_field(data[3902:5122]),
                    "BanusiCode": self.decode_field(data[6342:6348]),
                    "BanusiName": self.decode_field(data[6348:6412]),
                    "BanusiName_Co": self.decode_field(data[6412:6476]),
                    "BanusiResultsInfo": self.decode_field(data[6476:6536]),
                    "BreederCode": self.decode_field(data[6596:6604]),
                    "BreederName": self.decode_field(data[6604:6676]),
                    "BreederName_Co": self.decode_field(data[6676:6748]),
                    "BreederResultsInfo": self.decode_field(data[6748:6808]),
                    "RecordDelimiter": self.decode_field(data[6868:6870]),
                }
            )
            professional = [
                self._parse_hon_ruikei(
                    data,
                    start=start + 1220 * (number - 1),
                    key=key,
                    actor_type=actor_type,
                    number=number,
                )
                for actor_type, start in (("KISYU", 1423), ("CHOKYOSI", 3902))
                for number in range(1, 3)
            ]
            owners = [
                self._parse_sei_ruikei(
                    data,
                    start=start + 60 * (number - 1),
                    key=key,
                    actor_type=actor_type,
                    number=number,
                )
                for actor_type, start in (("BANUSI", 6476), ("BREEDER", 6748))
                for number in range(1, 3)
            ]
            result["_ck_chaku_rows"] = [
                *uma_rows,
                *(row for _, rows in professional for row in rows),
                *(row for _, row in owners),
            ]
            result["_ck_ruikei_rows"] = [
                *(summary for summary, _ in professional),
                *(summary for summary, _ in owners),
            ]
            if len(result["_ck_chaku_rows"]) != 278:
                raise ValueError("CK normalized count row cardinality mismatch")
            if len(result["_ck_ruikei_rows"]) != 8:
                raise ValueError("CK normalized summary row cardinality mismatch")
            for row_number, row in enumerate(result["_ck_chaku_rows"], start=1):
                last_rank = (
                    4 if row["EntityKubun"] == "UMA" and row["MetricKubun"] == "Kyakusitu" else 6
                )
                for rank in range(1, last_rank + 1):
                    self._require_digits(
                        f"CK count row {row_number} rank {rank}",
                        row[f"Count{rank}"],
                    )
            for row_number, row in enumerate(result["_ck_ruikei_rows"], start=1):
                for name in (
                    "SetYear",
                    "HonSyokinHeichi",
                    "HonSyokinSyogai",
                    "FukaSyokinHeichi",
                    "FukaSyokinSyogai",
                    "HonSyokinTotal",
                    "FukaSyokin",
                ):
                    value = row[name]
                    if value:
                        self._require_digits(f"CK summary row {row_number} {name}", value)
            return result
        except (ConversionError, UnicodeDecodeError, ValueError, TypeError) as error:
            self.logger.error(f"CKレコードパース中にエラー: {error}")
            return None
