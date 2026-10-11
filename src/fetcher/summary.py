"""Machine-readable summary of what one fetch run got back from JV-Link.

A daily sync that receives nothing used to look identical to one that
received everything: JVOpen ``-1`` and ``read_count == 0`` were treated as
"no data" and the run exited 0, and the JVOpen result was never recorded.
This module turns the per-dataspec outcome into a JSON document so that the
caller (and downstream schedulers) can see what was asked for and what came
back.

Return-code meanings follow the JV-Link interface specification 4.9.0.1:

- JVOpen ``0`` = normal, ``-1`` = no matching data *or* the user chose to
  download a newly published JV-Link version, ``-2`` = setup dialog
  cancelled (p.54 "JVOpen/JVRTOpen" code table). ``-1`` is therefore not a
  proof that the provider has nothing; it is recorded, never interpreted.
- ``readcount`` / ``downloadcount`` / ``lastfiletimestamp`` (p.19).
- JVRTOpen shares the JVOpen code table (p.54).

The contract of the document is described in docs/fetch_summary.md.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

SUMMARY_SCHEMA_VERSION = 1

STATUS_OK = "ok"
STATUS_NO_DATA = "no_data"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"

KIND_JVOPEN = "jvopen"
KIND_JVRTOPEN = "jvrtopen"

# JVOpen/JVRTOpen の「エラーではない」戻り値 (IF 4.9.0.1 p.54)。
_NON_ERROR_OPEN_CODES = (0, -1)

# エラー文言は下流の stdout/stderr tail と同じく有限長にする。
_ERROR_TEXT_LIMIT = 500


def jvopen_entry(
    *,
    fromtime: str,
    jvopen_code: int | None,
    read_count: int | None = None,
    download_count: int | None = None,
    lastfiletimestamp: str | None = None,
    recovery: bool = False,
) -> dict:
    """One JVOpen call: the fromtime sent and the four values returned (p.17-19).

    ``recovery`` marks the re-open of an identical request after a corrupt
    file was deleted (JVRead -402, p.56); aggregates skip it.
    """
    return {
        "fromtime": fromtime,
        "jvopen_code": jvopen_code,
        "read_count": read_count,
        "download_count": download_count,
        "lastfiletimestamp": lastfiletimestamp,
        "recovery": recovery,
    }


def jvrtopen_entry(
    *, key: str, jvrtopen_code: int | None, fetch_id: str | None = None
) -> dict:
    """One JVRTOpen call: the key sent and the code returned (p.22, p.54).

    ``fetch_id`` names the RT_CAPTURE_FETCH row of a captured spec (0B11/0B14,
    docs/capture_log.md); it is None for other specs and for failed opens.
    """
    return {"key": key, "jvrtopen_code": jvrtopen_code, "fetch_id": fetch_id}


def aggregate_open_code(codes: Iterable[int | None]) -> int | None:
    """Collapse the codes of several opens into one headline code.

    The first error code wins; otherwise ``0`` if any open succeeded, ``-1``
    if every open reported no data, and ``None`` if nothing was opened.
    """
    seen = [code for code in codes if code is not None]
    if not seen:
        return None
    for code in seen:
        if code not in _NON_ERROR_OPEN_CODES:
            return code
    return 0 if 0 in seen else -1


def _sum_counts(values: Iterable[int | None]) -> int | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _latest_timestamp(values: Iterable[str | None]) -> str | None:
    # YYYYMMDDhhmmss は文字列比較で時刻順になる。空文字は「返らなかった」。
    present = [value for value in values if value]
    return max(present) if present else None


def _error_text(error: BaseException | None) -> str | None:
    if error is None:
        return None
    return f"{type(error).__name__}: {error}"[:_ERROR_TEXT_LIMIT]


def _status(
    *, error: BaseException | None, skipped: bool, has_records: bool
) -> str:
    if skipped:
        return STATUS_SKIPPED
    if error is not None:
        return STATUS_ERROR
    return STATUS_OK if has_records else STATUS_NO_DATA


def summarize_jvopen_spec(
    *,
    dataspec: str,
    option: int,
    from_date: str,
    to_date: str | None,
    opens: Sequence[Mapping],
    fetch_stats: Mapping,
    records_imported: int | None,
    records_out_of_range: int,
    elapsed_seconds: float,
    error: BaseException | None = None,
    skipped: bool = False,
    skipped_code: int | None = None,
) -> dict:
    """Summarize one JVOpen dataspec (all of its calendar-year chunks)."""
    all_opens = opens
    opens = [entry for entry in all_opens if not entry.get("recovery")]
    read_count = _sum_counts(entry.get("read_count") for entry in opens)
    jvopen_code = aggregate_open_code(entry.get("jvopen_code") for entry in opens)
    if skipped and skipped_code is not None:
        jvopen_code = skipped_code
    return {
        "kind": KIND_JVOPEN,
        "dataspec": dataspec,
        "option": option,
        "from_date": from_date,
        "to_date": to_date,
        "status": _status(error=error, skipped=skipped, has_records=bool(read_count)),
        "jvopen_code": jvopen_code,
        "fromtimes": [entry.get("fromtime") for entry in opens],
        "read_count": read_count,
        "download_count": _sum_counts(entry.get("download_count") for entry in opens),
        "lastfiletimestamp": _latest_timestamp(
            entry.get("lastfiletimestamp") for entry in opens
        ),
        "records_read": int(fetch_stats.get("records_fetched", 0) or 0),
        "records_parsed": int(fetch_stats.get("records_parsed", 0) or 0),
        "records_imported": records_imported,
        "records_failed": int(fetch_stats.get("records_failed", 0) or 0),
        "records_out_of_range": records_out_of_range,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "error": None if skipped else _error_text(error),
        "opens": [dict(entry) for entry in all_opens],
    }


def summarize_jvrtopen_spec(
    *,
    dataspec: str,
    from_date: str,
    to_date: str,
    opens: Sequence[Mapping],
    stats: Mapping,
    elapsed_seconds: float,
    error: BaseException | None = None,
    skipped: bool = False,
    skipped_code: int | None = None,
) -> dict:
    """Summarize one JVRTOpen speed-report dataspec (one open per date key).

    JVRTOpen has no readcount/downloadcount/lastfiletimestamp, so those are
    ``None`` and "has data" is judged on records actually read.
    """
    records_read = int(stats.get("records_fetched", 0) or 0)
    open_code = aggregate_open_code(entry.get("jvrtopen_code") for entry in opens)
    if skipped and skipped_code is not None:
        open_code = skipped_code
    return {
        "kind": KIND_JVRTOPEN,
        "dataspec": dataspec,
        "option": None,
        "from_date": from_date,
        "to_date": to_date,
        "status": _status(error=error, skipped=skipped, has_records=records_read > 0),
        "jvopen_code": open_code,
        "fromtimes": [],
        "read_count": None,
        "download_count": None,
        "lastfiletimestamp": None,
        "records_read": records_read,
        "records_parsed": int(stats.get("records_parsed", 0) or 0),
        "records_imported": (
            None
            if error is not None or skipped
            else int(stats.get("records_imported", 0) or 0)
        ),
        "records_failed": int(stats.get("records_failed", 0) or 0),
        "records_out_of_range": 0,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "error": None if skipped else _error_text(error),
        "opens": [dict(entry) for entry in opens],
    }


def spec_has_records(spec_summary: Mapping) -> bool:
    """Whether a dataspec got anything back.

    JVOpen specs are judged on ``read_count`` (files listed by JVOpen, p.19);
    JVRTOpen specs, which return no file count, on records read.
    """
    if spec_summary.get("status") in (STATUS_SKIPPED, STATUS_ERROR):
        return False
    if spec_summary.get("kind") == KIND_JVOPEN:
        return bool(spec_summary.get("read_count"))
    return bool(spec_summary.get("records_read"))


def requirement_failures(
    required_specs: Sequence[str], spec_summaries: Sequence[Mapping]
) -> list[dict]:
    """Return one entry per required dataspec that got nothing back."""
    by_spec = {summary["dataspec"]: summary for summary in spec_summaries}
    failures = []
    for spec in required_specs:
        summary = by_spec.get(spec)
        if summary is not None and spec_has_records(summary):
            continue
        failures.append(
            {
                "dataspec": spec,
                "status": summary.get("status") if summary else "not_run",
                "read_count": summary.get("read_count") if summary else None,
            }
        )
    return failures


def write_summary_json(path: str | os.PathLike, document: Mapping) -> None:
    """Write the summary atomically so a reader never sees a partial file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
