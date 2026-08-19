#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""公式オッズレコード（O1-O6）共通のドメイン検証。

一次資料は公式JV-Data仕様書 Ver.4.9.0.1「７．オッズ1（単複枠）」〜
「１２．オッズ6（3連単）」。O1-O6 は次の公式値を共有する。

- データ区分: 1:中間 2:前日売最終 3:最終 4:確定 5:確定(月曜) 9:レース中止
  0:該当レコード削除（提供ミスなどの理由による）
- 発売フラグ: 0:発売なし 1:発売前取消 3:発売後取消 7:発売あり
- オッズ・人気順は数値のほかに公式の記号値を持つ。
  "0…0":無投票 / "-…-":発売前取消 / "*…*":発売後取消 / 空白:登録なし
  桁数はレコードと項目ごとに異なるため、桁落ちした記号値は受け付けない。
- 票数合計は11バイト（返還分票数を含む）
"""

from datetime import date
from typing import Mapping

# データ区分（0:削除 1:中間 2:前日売最終 3:最終 4:確定 5:確定(月曜) 9:レース中止）
DATA_KUBUN_VALUES = frozenset({"0", "1", "2", "3", "4", "5", "9"})
# 発売フラグ（0:発売なし 1:発売前取消 3:発売後取消 7:発売あり）
SALE_FLAG_VALUES = frozenset({"0", "1", "3", "7"})
# 複勝着払キー（0:複勝発売なし 2:2着まで払い 3:3着まで払い）
PLACE_PAYOUT_KEY_VALUES = frozenset({"0", "2", "3"})
KEY_CODE_WIDTHS = {"JyoCD": 2, "Kaiji": 2, "Nichiji": 2, "RaceNum": 2}
COUNT_WIDTHS = {"TorokuTosu": 2, "SyussoTosu": 2}
# 発表月日時分（月日時分各2桁）。中間オッズのみ設定されるため空白も公式値。
ANNOUNCED_TIME_WIDTH = 8
VOTE_TOTAL_WIDTH = 11
# 組合せを1件も持たない snapshot（発売なし・レース中止・削除）でも公式の
# 票数合計は提供されるため、H1/H6 と同じ sentinel で1行だけ保持する。
TOTAL_COMBINATION = "TOTAL"
CANCELLED_MARKER_CHARACTERS = ("-", "*")


def require_ascii_digits(record_type: str, field_name: str, value: object, width: int) -> str:
    """Require an exact-width ASCII digit run as the official layout defines."""

    if isinstance(value, str) and len(value) == width and value.isascii() and value.isdigit():
        return value
    raise ValueError(f"{record_type} {field_name} must be exactly {width} ASCII digits")


def require_date(record_type: str, field_name: str, value: object) -> str:
    digits = require_ascii_digits(record_type, field_name, value, 8)
    try:
        date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
    except ValueError as error:
        raise ValueError(f"{record_type} {field_name} must be a real YYYYMMDD date") from error
    return digits


def require_race_day(record_type: str, record: Mapping[str, object]) -> None:
    year = require_ascii_digits(record_type, "Year", record.get("Year"), 4)
    month_day = require_ascii_digits(record_type, "MonthDay", record.get("MonthDay"), 4)
    try:
        date(int(year), int(month_day[:2]), int(month_day[2:]))
    except ValueError as error:
        raise ValueError(f"{record_type} Year/MonthDay must be a real race day") from error


def require_announced_time(record_type: str, value: object) -> None:
    """発表月日時分は中間オッズのみ設定される。空白は提供値として許す。"""

    if value in ("", None):
        return
    digits = require_ascii_digits(record_type, "HassoTime", value, ANNOUNCED_TIME_WIDTH)
    try:
        date(2000, int(digits[:2]), int(digits[2:4]))
    except ValueError as error:
        raise ValueError(f"{record_type} HassoTime must start with a real MMDD") from error
    if int(digits[4:6]) > 23 or int(digits[6:]) > 59:
        raise ValueError(f"{record_type} HassoTime must end with a real hhmm")


def require_marker_or_digits(record_type: str, field_name: str, value: object, width: int) -> None:
    """オッズ・人気順は数値／取消記号／空白（登録なし）のいずれか。"""

    if not isinstance(value, str):
        raise ValueError(f"{record_type} {field_name} must be a provider value")
    if value == "":
        # 登録なし（公式初期値は空白）。parse 後は空文字になる。
        return
    if value in tuple(character * width for character in CANCELLED_MARKER_CHARACTERS):
        return
    require_ascii_digits(record_type, field_name, value, width)


def require_vote_total(record_type: str, field_name: str, value: object) -> None:
    if value in ("", None):
        # 提供データは合計エリアを空白で送ることがある（parse 後は空文字）。
        return
    require_ascii_digits(record_type, field_name, value, VOTE_TOTAL_WIDTH)


def validate_key_fields(record_type: str, record: Mapping[str, object]) -> None:
    """The official race key identifies the record regardless of status."""

    require_date(record_type, "MakeDate", record.get("MakeDate"))
    require_race_day(record_type, record)
    for field_name, width in KEY_CODE_WIDTHS.items():
        require_ascii_digits(record_type, field_name, record.get(field_name), width)


def validate_header_fields(
    record_type: str,
    record: Mapping[str, object],
    *,
    sale_flag_fields: tuple[str, ...],
    total_fields: tuple[str, ...],
) -> None:
    """Validate the fields every O1-O6 snapshot row repeats from the header."""

    for field_name, width in COUNT_WIDTHS.items():
        require_ascii_digits(record_type, field_name, record.get(field_name), width)
    require_announced_time(record_type, record.get("HassoTime"))
    for field_name in sale_flag_fields:
        if record.get(field_name) not in SALE_FLAG_VALUES:
            raise ValueError(f"{record_type} {field_name} is not an official sale flag")
    for field_name in total_fields:
        require_vote_total(record_type, field_name, record.get(field_name))


def validate_totals_only_row(
    record_type: str,
    record: Mapping[str, object],
    *,
    body_fields: tuple[str, ...],
) -> None:
    """The totals sentinel keeps the official totals and nothing else."""

    for field_name in body_fields:
        if record.get(field_name) not in ("", None):
            raise ValueError(
                f"{record_type} totals-only row must not carry {field_name}"
            )


class OddsCombinationValidationMixin:
    """O2-O6 が共有する「1組合せ＝1行」の公式ドメイン検証。

    サブクラスは RECORD_TYPE / SALE_FLAG_FIELDS / COMBINATION_WIDTH /
    ODDS_WIDTHS / FAVOURITE_WIDTH / TOTAL_FIELDS を公式仕様どおりに定義する。
    """

    FAVOURITE_FIELD = "Ninki"

    @classmethod
    def _body_fields(cls) -> tuple[str, ...]:
        return tuple(name for name, _ in cls.ODDS_WIDTHS) + (cls.FAVOURITE_FIELD,)

    @classmethod
    def validate_key_fields(cls, record: Mapping[str, object]) -> None:
        validate_key_fields(cls.RECORD_TYPE, record)

    @classmethod
    def validate_current_fields(
        cls,
        record: Mapping[str, object],
        *,
        data_kubun: str | None = None,
    ) -> None:
        """Validate one expanded odds row against the official domain."""

        record_type = cls.RECORD_TYPE
        status = data_kubun if data_kubun is not None else record.get("DataKubun")
        if status not in DATA_KUBUN_VALUES:
            raise ValueError(f"{record_type} DataKubun is not an official code")
        cls.validate_key_fields(record)
        if status == "0":
            # 削除指示は本文もヘッダも持たないため、レースキーだけを検証する。
            return

        validate_header_fields(
            record_type,
            record,
            sale_flag_fields=cls.SALE_FLAG_FIELDS,
            total_fields=cls.TOTAL_FIELDS,
        )
        if record.get("Kumi") == TOTAL_COMBINATION:
            validate_totals_only_row(record_type, record, body_fields=cls._body_fields())
            return
        require_ascii_digits(record_type, "Kumi", record.get("Kumi"), cls.COMBINATION_WIDTH)
        for field_name, width in cls.ODDS_WIDTHS:
            require_marker_or_digits(record_type, field_name, record.get(field_name), width)
        require_marker_or_digits(
            record_type,
            cls.FAVOURITE_FIELD,
            record.get(cls.FAVOURITE_FIELD),
            cls.FAVOURITE_WIDTH,
        )
