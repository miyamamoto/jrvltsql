"""Append-only capture log for the 0B11/0B14 speed reports.

RT_WH and the 0B14 tables (RT_WE/RT_AV/RT_JC/RT_TC/RT_CC) hold the current
state: 0B14 is replaced per race date on every fetch because JRA-VAN drops
withdrawn changes from later responses (JV-Data 4.9.0.1, データ提供タイミング
※1). That state cannot say what was known at an earlier moment. This log keeps,
for every JVRTOpen of a captured spec, one RT_CAPTURE_FETCH row and one
RT_CAPTURE_RECORD row per JVRead buffer (raw record plus parsed rows), stamped
in UTC. Rows are only inserted, inside the caller's transaction, so a fetch
that rolls back leaves no log either.

Contract: docs/capture_log.md.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src import __version__ as JLTSQL_VERSION
from src.jvlink.constants import ENCODING_JVDATA
from src.parser.factory import ParserFactory

CAPTURE_LOG_SPECS = frozenset({"0B11", "0B14"})
CAPTURE_FETCH_TABLE = "RT_CAPTURE_FETCH"
CAPTURE_RECORD_TABLE = "RT_CAPTURE_RECORD"

STATUS_COMPLETE = "complete"
STATUS_NO_DATA = "no_data"

RECORD_KEY_COLUMNS = (
    "Year",
    "MonthDay",
    "JyoCD",
    "Kaiji",
    "Nichiji",
    "RaceNum",
    "HappyoTime",
    "HenkoID",
    "Umaban",
)

# Byte spans (0-based, end exclusive) of the key fields, copied verbatim from
# the raw record. JV-Data 4.9.0.1 formats 101-106: every type starts with the
# same race-date header; a column a type does not have stays NULL (WE has no
# RaceNum, WH carries 18 horses so has no single Umaban).
_DATE_HEADER = {
    "Year": (11, 15),
    "MonthDay": (15, 19),
    "JyoCD": (19, 21),
    "Kaiji": (21, 23),
    "Nichiji": (23, 25),
}
_RACE_ANNOUNCEMENT = {**_DATE_HEADER, "RaceNum": (25, 27), "HappyoTime": (27, 35)}
RECORD_KEY_SPANS = {
    "WH": _RACE_ANNOUNCEMENT,
    "WE": {**_DATE_HEADER, "HappyoTime": (25, 33), "HenkoID": (33, 34)},
    "AV": {**_RACE_ANNOUNCEMENT, "Umaban": (35, 37)},
    "JC": {**_RACE_ANNOUNCEMENT, "Umaban": (35, 37)},
    "TC": _RACE_ANNOUNCEMENT,
    "CC": _RACE_ANNOUNCEMENT,
}

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"capture clock must be offset-aware, got {value!r}")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _decode_raw(buff: bytes) -> tuple[str, str]:
    """Return (encoding, text); bytes that are not CP932 are kept as hex."""
    try:
        return ENCODING_JVDATA, buff.decode(ENCODING_JVDATA)
    except UnicodeDecodeError:
        return "hex", buff.hex()


def _header(buff: bytes, start: int, end: int) -> str | None:
    try:
        value = buff[start:end].decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    return value or None


def _public_rows(parsed: Any) -> list[dict]:
    rows = parsed if isinstance(parsed, list) else [parsed] if parsed else []
    return [
        {key: value for key, value in row.items() if not str(key).startswith("_")}
        for row in rows
        if isinstance(row, dict)
    ]


def _record_keys(buff: bytes, record_spec: str | None) -> dict:
    spans = RECORD_KEY_SPANS.get(record_spec or "", {})
    return {
        column: _header(buff, *spans[column]) if column in spans else None
        for column in RECORD_KEY_COLUMNS
    }


class RealtimeCaptureFetch:
    """Log of one JVRTOpen (one dataspec and request key)."""

    def __init__(
        self,
        database,
        *,
        dataspec: str,
        request_key: str,
        producer: str,
        clock: Clock = utc_now,
        parser_factory: ParserFactory | None = None,
    ) -> None:
        self.database = database
        self.dataspec = dataspec
        self.request_key = request_key
        self.producer = producer
        self.fetch_id = uuid4().hex
        self._clock = clock
        self._parser_factory = parser_factory or ParserFactory()
        self.requested_at = _stamp(clock())
        self.opened_at: str | None = None
        self.jvrtopen_code: int | None = None
        self.record_count = 0

    def opened(self, jvrtopen_code: int) -> None:
        """Record the JVRTOpen return code; call right after JVRTOpen returns."""
        self.opened_at = _stamp(self._clock())
        self.jvrtopen_code = jvrtopen_code

    def append(self, buff: bytes) -> None:
        """Insert one JVRead buffer as received (raw and parsed rows)."""
        collected_at = _stamp(self._clock())
        self.record_count += 1
        try:
            rows = _public_rows(self._parser_factory.parse(buff))
        except Exception:  # noqa: BLE001 - the importer reports the rejection
            rows = []
        encoding, raw = _decode_raw(buff)
        record_spec = _header(buff, 0, 2)
        row = {
            "FetchId": self.fetch_id,
            "Seq": self.record_count,
            "CollectedAt": collected_at,
            "DataSpec": self.dataspec,
            "RequestKey": self.request_key,
            "RecordSpec": record_spec,
            "DataKubun": _header(buff, 2, 3),
            "MakeDate": _header(buff, 3, 11),
            **_record_keys(buff, record_spec),
            "RawEncoding": encoding,
            "RawRecord": raw,
            "RawSha256": hashlib.sha256(buff).hexdigest(),
            "RowsJson": (
                json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str) if rows else None
            ),
        }
        self.database.insert(CAPTURE_RECORD_TABLE, row, use_replace=False)

    def complete(self) -> None:
        """Insert the fetch row; call after the stream was read to the end."""
        if self.opened_at is None or self.jvrtopen_code is None:
            raise RuntimeError("capture fetch completed before JVRTOpen returned")
        self.database.insert(
            CAPTURE_FETCH_TABLE,
            {
                "FetchId": self.fetch_id,
                "DataSpec": self.dataspec,
                "RequestKey": self.request_key,
                "Status": STATUS_NO_DATA if self.jvrtopen_code == -1 else STATUS_COMPLETE,
                "JVRTOpenCode": self.jvrtopen_code,
                "RecordCount": self.record_count,
                "RequestedAt": self.requested_at,
                "OpenedAt": self.opened_at,
                "CompletedAt": _stamp(self._clock()),
                "Producer": self.producer,
                "JltsqlVersion": JLTSQL_VERSION,
            },
            use_replace=False,
        )


def begin_capture(
    database,
    dataspec: str,
    request_key: str,
    *,
    producer: str,
    clock: Clock = utc_now,
) -> RealtimeCaptureFetch | None:
    """Start a capture log for one JVRTOpen, or None for specs not captured.

    Call immediately before JVRTOpen, inside the transaction that imports the
    records.
    """
    if dataspec.upper() not in CAPTURE_LOG_SPECS:
        return None
    return RealtimeCaptureFetch(
        database,
        dataspec=dataspec.upper(),
        request_key=request_key,
        producer=producer,
        clock=clock,
    )
