"""Parser for the official 7,215-byte JV-Data WF (重勝式/WIN5) record.

The layout is pinned to JV-Data 4.8.0.2 / 4.9.0.1 (フォーマット ３０．重勝式)
and SDK 5.0.0 ``JV_WF_INFO``.  Ver.4.1.1 (2011-09-28) corrected the carryover
balance name and documented initial values plus the no-hit payout tuple;
Ver.4.2.0 (2012-02-21) made the initial carryover amount required for
statuses 1, 2 and 9.  Neither change altered a byte position or the length,
so this parser distinguishes them by the embedded data-creation date.
"""

import json
from datetime import date

from src.parser.base import validate_fixed_record
from src.parser.code_domains import OFFICIAL_JYO_CODES_2001
from src.utils.logger import get_logger


class WFParser:
    """Parse and validate every field of the current WF physical record."""

    RECORD_TYPE = "WF"
    RECORD_LENGTH = 7215
    RACE_COUNT = 5
    PAYOUT_COUNT = 243
    PAYOUT_LENGTH = 29

    # 公式データ区分: 1 詳細発表時, 2 対象1レース目確定時, 3 払戻発表時,
    # 7 成績(月曜・蓄積系のみ), 9 中止時, 0 該当レコード削除
    DATA_KUBUN_VALUES = frozenset({"0", "1", "2", "3", "7", "9"})
    ACCUMULATED_DATA_KUBUN_VALUES = DATA_KUBUN_VALUES
    # 速報系(0B51)は 7:成績(月曜) を提供しない
    REALTIME_DATA_KUBUN_VALUES = frozenset({"0", "1", "2", "3", "9"})
    # 状態別に「値を設定」する(○) / 「初期値を設定」する(-) / 混在(△) 項目群
    INITIAL_VALUE_STATUSES = frozenset({"1"})
    OPTIONAL_PAYLOAD_STATUSES = frozenset({"2", "9"})
    REQUIRED_PAYLOAD_STATUSES = frozenset({"3", "7"})
    FLAG_VALUES = frozenset({"0", "1"})
    FLAG_INITIAL_VALUE = "0"
    # Ver.4.2.0 (2012-02-21) から項番14 キャリーオーバー金額初期が 1/2/9 でも必須
    INITIAL_CARRYOVER_REQUIRED_FROM = date(2012, 2, 21)
    RESERVED_SPAN_WIDTHS = {"Yobi1": 2, "Yobi2": 6}
    # 特記事項: 重勝式中止時の払戻情報 (組番 / 払戻金 / 的中票数)
    CANCELLATION_PAYOUT = ("0000000000", "000000100", "0000000000")
    # コード表2001の掲載値から、初期値00と明示的な未使用値C4/F4/F6/
    # G4/G6/G8を除いた競馬場コード。廃止済みの競馬場・国も含むため
    # 「現在使用中」の集合ではない。公式追加時はmanifest/specと同時更新する。
    OFFICIAL_JYO_CODES = OFFICIAL_JYO_CODES_2001
    NO_HIT_PAY = "000000000"
    NO_HIT_VOTES = "0000000000"

    RACE_INFO_FIELDS = tuple(f"RaceInfo{index}" for index in range(1, RACE_COUNT + 1))
    YUKO_HYOSU_FIELDS = tuple(f"YukoHyosu{index}" for index in range(1, RACE_COUNT + 1))
    FLAG_FIELDS = ("HenkanFlag", "FuseirituFlag", "TekichuNasiFlag")
    # 項目名 -> 物理バイト幅 (可変桁数値: 1..width ASCII digits)
    NUMERIC_PAYLOAD_WIDTHS = {
        "HatubaiHyosu": 11,
        **{name: 11 for name in YUKO_HYOSU_FIELDS},
        "CarryOverStart": 15,
        "CarryOverBalance": 15,
    }
    PAYOUT_KUMI_WIDTH = 10
    PAYOUT_PAY_WIDTH = 9
    PAYOUT_VOTES_WIDTH = 10
    PAYOUT_KEYS = ("Kumi", "PayJyushosiki", "TekichuHyosu")

    def __init__(self):
        self.logger = get_logger(__name__)

    @staticmethod
    def decode_field(data: bytes) -> str:
        return data.decode("cp932", errors="strict").strip()

    # ------------------------------------------------------------------
    # Shared field validators (also used by the importer caller validator)
    # ------------------------------------------------------------------
    @staticmethod
    def _require_ascii_digits(name: str, value: object, width: int) -> None:
        if (
            not isinstance(value, str)
            or len(value) != width
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"WF {name} must be exactly {width} ASCII digits")

    @staticmethod
    def _require_optional_digits(name: str, value: object, width: int) -> None:
        """Require blank or 1..width ASCII digits (right-padded numeric text)."""
        if value == "":
            return
        if (
            not isinstance(value, str)
            or not 1 <= len(value) <= width
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError(f"WF {name} must be blank or up to {width} ASCII digits")

    @classmethod
    def _require_digits(cls, name: str, value: object, width: int) -> None:
        if value == "":
            raise ValueError(f"WF {name} is required for this DataKubun")
        cls._require_optional_digits(name, value, width)

    @staticmethod
    def _require_blank(name: str, value: object) -> None:
        if value != "":
            raise ValueError(f"WF {name} must keep its initial value for this DataKubun")

    @classmethod
    def _require_reserved_text(cls, name: str, value: object) -> None:
        """Require an optional reserved span to fit its physical CP932 field."""

        if value in (None, ""):
            return
        width = cls.RESERVED_SPAN_WIDTHS[name]
        if not isinstance(value, str):
            raise ValueError(f"WF {name} must be text or blank")
        try:
            encoded = value.encode("cp932", errors="strict")
        except UnicodeEncodeError as error:
            raise ValueError(f"WF {name} must be valid CP932 text") from error
        if len(encoded) > width:
            raise ValueError(f"WF {name} must fit in {width} CP932 byte(s)")

    @classmethod
    def _require_yyyymmdd(cls, name: str, value: object) -> date:
        """Require an actual Gregorian date, not merely eight digits."""
        cls._require_ascii_digits(name, value, 8)
        assert isinstance(value, str)
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        except ValueError as error:
            raise ValueError(f"WF {name} must be a real yyyymmdd date") from error

    @classmethod
    def _require_event_date(cls, year: object, month_day: object) -> date:
        """Require the (Year, MonthDay) key to be one real Gregorian date."""
        cls._require_ascii_digits("Year", year, 4)
        cls._require_ascii_digits("MonthDay", month_day, 4)
        assert isinstance(year, str) and isinstance(month_day, str)
        try:
            return date(int(year), int(month_day[:2]), int(month_day[2:]))
        except ValueError as error:
            raise ValueError("WF Year and MonthDay must form a real Gregorian date") from error

    @classmethod
    def _require_race_composite(cls, name: str, value: object) -> None:
        """Require JyoCD(2 code) + Kaiji(2) + Nichiji(2) + RaceNum(2)."""
        if not isinstance(value, str) or len(value) != 8 or not value.isascii():
            raise ValueError(f"WF {name} must be an 8-character race composite")
        jyo_cd, ordinal = value[:2], value[2:]
        if jyo_cd not in cls.OFFICIAL_JYO_CODES or not ordinal.isdigit():
            raise ValueError(
                f"WF {name} must use a pinned official venue code and six ASCII digits"
            )

    @classmethod
    def _require_flag(cls, name: str, value: object, *, availability: str) -> None:
        if availability == "initial":
            if value != cls.FLAG_INITIAL_VALUE:
                raise ValueError(f"WF {name} must keep its initial value 0")
            return
        if value not in cls.FLAG_VALUES:
            raise ValueError(f"WF {name} must be 0 or 1")

    @classmethod
    def _require_payout_tuple(
        cls,
        index: int,
        kumi: object,
        pay: object,
        votes: object,
        *,
        availability: str,
    ) -> None:
        """Require one payout slot to be fully blank or a complete tuple."""
        values = (kumi, pay, votes)
        if not all(isinstance(value, str) for value in values):
            raise ValueError(f"WF payout slot {index} must contain text values")
        if availability == "initial":
            if any(value != "" for value in values):
                raise ValueError(f"WF payout slot {index} must keep its initial value")
            return
        blank = [value == "" for value in values]
        if all(blank):
            if availability == "required":
                raise ValueError(f"WF payout slot {index} is required for this DataKubun")
            return
        if any(blank):
            raise ValueError(f"WF payout slot {index} is a partial tuple")
        cls._require_ascii_digits(f"payout slot {index} Kumi", kumi, cls.PAYOUT_KUMI_WIDTH)
        cls._require_optional_digits(
            f"payout slot {index} PayJyushosiki", pay, cls.PAYOUT_PAY_WIDTH
        )
        cls._require_optional_digits(
            f"payout slot {index} TekichuHyosu", votes, cls.PAYOUT_VOTES_WIDTH
        )

    @classmethod
    def initial_carryover_availability(cls, status: str, make_date: date) -> str:
        """Return the official 項番14 availability for this record version."""
        if make_date >= cls.INITIAL_CARRYOVER_REQUIRED_FROM:
            return "required"
        if status == "1":
            return "initial"
        if status in cls.OPTIONAL_PAYLOAD_STATUSES:
            return "optional"
        return "required"

    @classmethod
    def validate_body(
        cls, values: dict[str, object], payouts: list, status: str, make_date: date
    ) -> None:
        """Validate the state-dependent body of a non-delete WF record.

        ``values`` holds native parser field names; ``payouts`` holds 243
        (Kumi, PayJyushosiki, TekichuHyosu) tuples.  Availability follows the
        official legend: statuses 1 keep initial values (-), 2/9 may or may not
        set values (△), 3/7 set them (○); race composites and the initial
        carryover amount are set for every status (post-Ver.4.2.0).
        """
        for name in cls.RACE_INFO_FIELDS:
            cls._require_race_composite(name, values.get(name))
        for name in cls.RESERVED_SPAN_WIDTHS:
            cls._require_reserved_text(name, values.get(name))

        if status in cls.INITIAL_VALUE_STATUSES:
            availability = "initial"
        elif status in cls.OPTIONAL_PAYLOAD_STATUSES:
            availability = "optional"
        elif status in cls.REQUIRED_PAYLOAD_STATUSES:
            availability = "required"
        else:
            raise ValueError(f"WF DataKubun has unsupported value {status!r}")

        carryover_start = values.get("CarryOverStart")
        carryover_availability = cls.initial_carryover_availability(status, make_date)
        if carryover_availability == "required":
            cls._require_digits(
                "CarryOverStart", carryover_start, cls.NUMERIC_PAYLOAD_WIDTHS["CarryOverStart"]
            )
        elif carryover_availability == "optional":
            cls._require_optional_digits(
                "CarryOverStart", carryover_start, cls.NUMERIC_PAYLOAD_WIDTHS["CarryOverStart"]
            )
        else:
            cls._require_blank("CarryOverStart", carryover_start)

        payload_names = ("HatubaiHyosu", *cls.YUKO_HYOSU_FIELDS, "CarryOverBalance")
        for name in payload_names:
            width = cls.NUMERIC_PAYLOAD_WIDTHS[name]
            value = values.get(name)
            if availability == "initial":
                cls._require_blank(name, value)
            elif availability == "optional":
                cls._require_optional_digits(name, value, width)
            else:
                cls._require_digits(name, value, width)
        for name in cls.FLAG_FIELDS:
            cls._require_flag(name, values.get(name), availability=availability)

        if len(payouts) != cls.PAYOUT_COUNT:
            raise ValueError(f"WF payout information must contain exactly {cls.PAYOUT_COUNT} slots")
        for index, (kumi, pay, votes) in enumerate(payouts, start=1):
            slot_availability = availability
            if availability == "required" and index > 1:
                # Only the first slot is guaranteed; additional dead-heat
                # combinations occupy the following slots when present.
                slot_availability = "optional"
            cls._require_payout_tuple(index, kumi, pay, votes, availability=slot_availability)
        if status == "9" and any(any(value != "" for value in payout) for payout in payouts):
            if tuple(payouts[0]) != cls.CANCELLATION_PAYOUT or any(
                any(value != "" for value in payout) for payout in payouts[1:]
            ):
                raise ValueError(
                    "WF status 9 payout must be the documented cancellation tuple in slot 1"
                )
        if status in cls.REQUIRED_PAYLOAD_STATUSES and values.get("TekichuNasiFlag") == "1":
            for index, (kumi, pay, votes) in enumerate(payouts, start=1):
                if kumi == "":
                    continue
                if pay != cls.NO_HIT_PAY or votes != cls.NO_HIT_VOTES:
                    raise ValueError(
                        f"WF final no-hit payout slot {index} must retain Kumi with "
                        "zero PayJyushosiki and TekichuHyosu"
                    )

    def parse(self, data: bytes) -> dict[str, str] | None:
        try:
            validate_fixed_record(data, self.RECORD_TYPE, self.RECORD_LENGTH)
            result = {
                "RecordSpec": self.decode_field(data[0:2]),
                "DataKubun": self.decode_field(data[2:3]),
                "MakeDate": self.decode_field(data[3:11]),
                "Year": self.decode_field(data[11:15]),
                "MonthDay": self.decode_field(data[15:19]),
                "Yobi1": self.decode_field(data[19:21]),
            }
            status = result["DataKubun"]
            if status not in self.DATA_KUBUN_VALUES:
                raise ValueError(f"WF DataKubun has unsupported value {status!r}")
            make_date = self._require_yyyymmdd("MakeDate", result["MakeDate"])
            self._require_event_date(result["Year"], result["MonthDay"])

            for index in range(self.RACE_COUNT):
                start = 21 + index * 8
                result[f"RaceInfo{index + 1}"] = self.decode_field(data[start : start + 8])

            result["Yobi2"] = self.decode_field(data[61:67])
            result["HatubaiHyosu"] = self.decode_field(data[67:78])
            for index in range(self.RACE_COUNT):
                start = 78 + index * 11
                result[f"YukoHyosu{index + 1}"] = self.decode_field(data[start : start + 11])

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
                    (
                        self.decode_field(data[start : start + 10]),
                        self.decode_field(data[start + 10 : start + 19]),
                        self.decode_field(data[start + 19 : start + 29]),
                    )
                )

            # A status-0 row is an exact-key erase instruction. The provider
            # does not define its body, so only the header and key are
            # interpreted; every other status validates the state-dependent body.
            if status != "0":
                self.validate_body(result, payouts, status, make_date)

            result["PayoutsJson"] = json.dumps(
                [dict(zip(self.PAYOUT_KEYS, payout, strict=True)) for payout in payouts],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            result["RecordDelimiter"] = self.decode_field(data[7213:7215])
            return result
        except Exception as exc:
            self.logger.error(f"WFレコードパース中にエラー: {exc}")
            return None
