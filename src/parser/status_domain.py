"""Official JV-Data DataKubun domains shared by every ingestion boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Final


class DataKubunContext(StrEnum):
    """Validation context, not a registry of provider-channel availability."""

    ACCUMULATED = "accumulated"
    REALTIME = "realtime"


# The base/current contract covers every parser/importer record type, including
# formats that the provider distributes only through realtime calls. It must
# not be interpreted as an availability registry.
CURRENT_ACCUMULATED_DATA_KUBUN: Final[dict[str, frozenset[str]]] = {
    "AV": frozenset({"1", "2"}),
    "BN": frozenset({"0", "1", "2"}),
    "BR": frozenset({"0", "1", "2"}),
    "BT": frozenset({"0", "1", "2"}),
    "CC": frozenset({"1"}),
    "CH": frozenset({"0", "1", "2"}),
    "CK": frozenset({"0", "1", "2"}),
    "CS": frozenset({"0", "1", "2"}),
    "DM": frozenset({"0", "1", "2", "3", "7"}),
    "H1": frozenset({"0", "2", "4", "5", "9"}),
    "H6": frozenset({"0", "2", "4", "5", "9"}),
    "HC": frozenset({"0", "1"}),
    "HN": frozenset({"0", "1", "2"}),
    "HR": frozenset({"0", "1", "2", "9"}),
    "HS": frozenset({"0", "1"}),
    "HY": frozenset({"0", "1"}),
    "JC": frozenset({"1"}),
    "JG": frozenset({"0", "1"}),
    "KS": frozenset({"0", "1", "2"}),
    "O1": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "O2": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "O3": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "O4": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "O5": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "O6": frozenset({"0", "1", "2", "3", "4", "5", "9"}),
    "RA": frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "9", "A", "B"}),
    "RC": frozenset({"0", "1"}),
    "SE": frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "9", "A", "B"}),
    "SK": frozenset({"0", "1", "2"}),
    "TC": frozenset({"1"}),
    "TK": frozenset({"0", "1", "2"}),
    "TM": frozenset({"0", "1", "2", "3", "7"}),
    "UM": frozenset({"0", "1", "2", "3", "4", "9"}),
    "WC": frozenset({"0", "1"}),
    "WE": frozenset({"1"}),
    "WF": frozenset({"0", "1", "2", "3", "7", "9"}),
    "WH": frozenset({"1"}),
    "YS": frozenset({"0", "1", "2", "3", "9"}),
}

CURRENT_REALTIME_DATA_KUBUN: Final[dict[str, frozenset[str]]] = {
    **CURRENT_ACCUMULATED_DATA_KUBUN,
    "DM": frozenset({"0", "1", "2", "3"}),
    "TM": frozenset({"0", "1", "2", "3"}),
    "WF": frozenset({"0", "1", "2", "3", "9"}),
}


@dataclass(frozen=True)
class HistoricalDataKubun:
    """One old status whose same-length generation is bounded by MakeDate."""

    value: str
    valid_before_make_date: date


HISTORICAL_DATA_KUBUN: Final[dict[str, HistoricalDataKubun]] = {
    "AV": HistoricalDataKubun("0", date(2003, 7, 11)),
    "JC": HistoricalDataKubun("0", date(2003, 7, 11)),
    "RC": HistoricalDataKubun("2", date(2005, 9, 29)),
    "WE": HistoricalDataKubun("0", date(2003, 7, 11)),
    "WH": HistoricalDataKubun("0", date(2003, 7, 11)),
}

# UM status 9 was added in Ver.1.0.1 beta. An explicitly older MakeDate is
# therefore evidence against that otherwise-current value. Missing provenance
# keeps the current-only contract instead of inventing an older generation.
CURRENT_DATA_KUBUN_NOT_BEFORE: Final[dict[tuple[str, str], date]] = {("UM", "9"): date(2003, 4, 22)}


def _make_date(value: object) -> date | None:
    """Return a comparable provider MakeDate, or ``None`` when unproven."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 8 and value.isascii() and value.isdigit():
            return datetime.strptime(value, "%Y%m%d").date()
        return date.fromisoformat(value)
    except ValueError:
        return None


def _current_values(
    record_type: str,
    context: DataKubunContext | str,
) -> frozenset[str]:
    try:
        context = DataKubunContext(context)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Unknown DataKubun context: {context!r}") from error
    domains = (
        CURRENT_REALTIME_DATA_KUBUN
        if context is DataKubunContext.REALTIME
        else CURRENT_ACCUMULATED_DATA_KUBUN
    )
    try:
        return domains[record_type]
    except KeyError as error:
        raise ValueError(
            f"RecordSpec has no official DataKubun contract: {record_type!r}"
        ) from error


def validate_data_kubun(
    record_type: str,
    data_kubun: object,
    *,
    make_date: object = None,
    context: DataKubunContext | str = DataKubunContext.ACCUMULATED,
) -> str:
    """Validate one status against current or date-proven historical truth."""

    if not isinstance(data_kubun, str) or len(data_kubun) != 1:
        raise ValueError(
            f"{record_type} DataKubun must be one explicit character: " f"{data_kubun!r}"
        )
    context = DataKubunContext(context)
    if data_kubun in _current_values(record_type, context):
        not_before = CURRENT_DATA_KUBUN_NOT_BEFORE.get((record_type, data_kubun))
        explicit_make_date = _make_date(make_date)
        if (
            not_before is not None
            and explicit_make_date is not None
            and explicit_make_date < not_before
        ):
            raise ValueError(
                f"{record_type} DataKubun {data_kubun!r} was not defined for "
                f"MakeDate {explicit_make_date:%Y%m%d}"
            )
        return data_kubun

    historical = HISTORICAL_DATA_KUBUN.get(record_type)
    historical_make_date = _make_date(make_date)
    if (
        historical is not None
        and data_kubun == historical.value
        and historical_make_date is not None
        and historical_make_date < historical.valid_before_make_date
    ):
        return data_kubun

    raise ValueError(
        f"{record_type} DataKubun is not valid for {context.value}: " f"{data_kubun!r}"
    )


def _required_alias(
    record: Mapping[str, object],
    names: tuple[str, ...],
    label: str,
) -> str:
    aliases: tuple[tuple[str, object], ...] = tuple(
        (name, record[name]) for name in names if record.get(name) not in (None, "")
    )
    if not aliases:
        raise ValueError(f"{label} is required")
    if any(not isinstance(value, str) for _, value in aliases):
        raise ValueError(f"{label} aliases must be strings: {aliases!r}")
    values = {value for _, value in aliases}
    if len(values) != 1:
        raise ValueError(f"conflicting {label} aliases: {aliases!r}")
    value = aliases[0][1]
    assert isinstance(value, str)
    return value


def resolve_data_kubun_aliases(record: Mapping[str, object]) -> str:
    """Resolve the current and legacy names without inventing a default."""

    return _required_alias(record, ("DataKubun", "headDataKubun"), "DataKubun")


def validate_record_header(
    record: Mapping[str, object],
    *,
    context: DataKubunContext = DataKubunContext.ACCUMULATED,
) -> tuple[str, str]:
    """Resolve all accepted aliases and validate the official status domain."""

    record_type = _required_alias(
        record,
        ("レコード種別ID", "RecordSpec", "headRecordSpec"),
        "record-type (RecordSpec)",
    )
    data_kubun = resolve_data_kubun_aliases(record)
    validate_data_kubun(
        record_type,
        data_kubun,
        make_date=record.get("MakeDate"),
        context=context,
    )
    return record_type, data_kubun
