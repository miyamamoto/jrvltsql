"""Canonical JV-Data values with explicit units.

The fixed-width parser keeps the provider representation in the original
fields.  These helpers add unambiguous, typed values for downstream users.
Malformed values fail closed instead of having non-numeric characters
silently removed.
"""

from __future__ import annotations

from typing import Any

SE_CONTRACT_VERSION = 2

def _unsigned_digits(value: Any, width: int) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) != width or not text.isascii() or not text.isdigit():
        return None
    return int(text)


def _scaled_unsigned(
    value: Any,
    width: int,
    scale: float,
    *,
    zero_is_missing: bool = False,
    sentinels: tuple[int, ...] = (),
) -> float | None:
    parsed = _unsigned_digits(value, width)
    if parsed is None or parsed in sentinels or (zero_is_missing and parsed == 0):
        return None
    return parsed * scale


def _msss_seconds(value: Any) -> float | None:
    """Convert provider ``MSSS`` (minutes, seconds, tenths) to seconds."""
    parsed = _unsigned_digits(value, 4)
    if parsed is None or parsed == 0:
        return None
    minutes, second_tenths = divmod(parsed, 1000)
    if second_tenths >= 600:
        return None
    return minutes * 60.0 + second_tenths / 10.0


def _body_weight_kg(value: Any) -> int | None:
    parsed = _unsigned_digits(value, 3)
    return parsed if parsed not in (None, 0, 999) else None


def _signed_weight_change(value: Any, sign: Any) -> int | None:
    parsed = _unsigned_digits(value, 3)
    if parsed is None or parsed == 999:
        return None
    sign_text = "" if sign is None else str(sign).strip()
    if sign_text == "+":
        return parsed
    if sign_text == "-":
        return -parsed
    if sign_text == "" and parsed == 0:
        return 0
    return None


def _signed_tenths(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) != 4 or not text.isascii():
        return None
    if text[0] not in "+-" or not text[1:].isdigit():
        return None
    magnitude = int(text[1:]) / 10.0
    return -magnitude if text[0] == "-" else magnitude


def _msshh_seconds(value: Any) -> float | None:
    """Convert provider ``MSSHH`` mining time to elapsed seconds."""
    parsed = _unsigned_digits(value, 5)
    if parsed is None or parsed == 0 or parsed == 99999:
        return None
    minutes, second_hundredths = divmod(parsed, 10000)
    if second_hundredths >= 6000:
        return None
    return minutes * 60.0 + second_hundredths / 100.0


def _prize_yen(value: Any, data_kubun: Any) -> int | None:
    parsed = _unsigned_digits(value, 8)
    if parsed is None:
        return None
    if parsed == 0 and str(data_kubun or "").strip() != "7":
        return None
    return parsed * 100


def canonicalize_se_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Return canonical SE fields without changing provider raw fields."""
    return {
        "ParserContractVersion": SE_CONTRACT_VERSION,
        "ProviderFutanRaw": record.get("Futan") or None,
        "ProviderFutanBeforeRaw": record.get("FutanBefore") or None,
        "ProviderBaTaijyuRaw": record.get("BaTaijyu") or None,
        "ProviderZogenFugoRaw": record.get("ZogenFugo") or None,
        "ProviderZogenSaRaw": record.get("ZogenSa") or None,
        "ProviderRaceTimeRaw": record.get("Time") or None,
        "ProviderOddsRaw": record.get("Odds") or None,
        "ProviderHonsyokinRaw": record.get("Honsyokin") or None,
        "ProviderFukasyokinRaw": record.get("Fukasyokin") or None,
        "ProviderHaronTimeL4Raw": record.get("HaronTimeL4") or None,
        "ProviderHaronTimeL3Raw": record.get("HaronTimeL3") or None,
        "ProviderTimeDiffRaw": record.get("TimeDiff") or None,
        "ProviderDMTimeRaw": record.get("DMTime") or None,
        "ProviderDMGosaPRaw": record.get("DMGosaP") or None,
        "ProviderDMGosaMRaw": record.get("DMGosaM") or None,
        "FutanKg": _scaled_unsigned(
            record.get("Futan"), 3, 0.1, zero_is_missing=True, sentinels=(999,)
        ),
        "FutanBeforeKg": _scaled_unsigned(
            record.get("FutanBefore"), 3, 0.1, zero_is_missing=True, sentinels=(999,)
        ),
        "BaTaijyuKg": _body_weight_kg(record.get("BaTaijyu")),
        "ZogenSaKg": _signed_weight_change(
            record.get("ZogenSa"), record.get("ZogenFugo")
        ),
        "RaceTimeSeconds": _msss_seconds(record.get("Time")),
        "OddsMultiplier": _scaled_unsigned(
            record.get("Odds"), 4, 0.1, zero_is_missing=True
        ),
        "HonsyokinYen": _prize_yen(record.get("Honsyokin"), record.get("DataKubun")),
        "FukasyokinYen": _prize_yen(
            record.get("Fukasyokin"), record.get("DataKubun")
        ),
        "HaronTimeL4Seconds": _scaled_unsigned(
            record.get("HaronTimeL4"),
            3,
            0.1,
            zero_is_missing=True,
            sentinels=(999,),
        ),
        "HaronTimeL3Seconds": _scaled_unsigned(
            record.get("HaronTimeL3"),
            3,
            0.1,
            zero_is_missing=True,
            sentinels=(999,),
        ),
        "TimeDiffSeconds": _signed_tenths(record.get("TimeDiff")),
        "DMTimeSeconds": _msshh_seconds(record.get("DMTime")),
        "DMGosaPSeconds": _scaled_unsigned(
            record.get("DMGosaP"), 4, 0.01, zero_is_missing=True
        ),
        "DMGosaMSeconds": _scaled_unsigned(
            record.get("DMGosaM"), 4, 0.01, zero_is_missing=True
        ),
    }
