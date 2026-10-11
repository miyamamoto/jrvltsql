"""One bounded fetch of date-keyed JVRTOpen speed-report specs.

``jltsql realtime start`` is a resident loop; collectors that run one command
per request need a fetch that opens each date key once, imports, and returns.
This module holds that fetch for ``scripts/daily_update.py`` and
``jltsql realtime fetch`` (docs/CLI.md, docs/fetch_summary.md).
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from datetime import datetime, timedelta

from src.fetcher.summary import jvrtopen_entry
from src.realtime.capture_log import begin_capture

# Specs whose JVRTOpen key is a race date (JV-Link IF 4.9.0.1 p.22 開催日単位,
# JV-Data 4.9.0.1 提供単位). 0B16 is event-keyed and the odds specs
# (0B20/0B3x/0B4x) are race-keyed; they have their own commands.
DATE_KEYED_REALTIME_SPECS = ("0B11", "0B12", "0B13", "0B14", "0B15", "0B17", "0B51")

# JV-Link returns these for an unsubscribed/invalid request (-111/-114/-115);
# the spec is skipped, not failed.
SUBSCRIPTION_ERROR_CODES = frozenset({-111, -114, -115})


def iter_date_keys(from_date: str, to_date: str) -> list[str]:
    """Return inclusive YYYYMMDD keys between from_date and to_date."""
    start = datetime.strptime(from_date, "%Y%m%d")
    end = datetime.strptime(to_date, "%Y%m%d")
    if end < start:
        return []
    return [
        (start + timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range((end - start).days + 1)
    ]


def fetch_realtime_spec(
    database,
    spec: str,
    date_keys: Iterable[str],
    *,
    sid: str,
    producer: str,
    jvlink=None,
    updater=None,
    ensure_tables: bool = True,
    jvrtopen_results: list | None = None,
    stats: dict | None = None,
    log_prefix: str = "[realtime-fetch]",
) -> dict:
    """Open each date key of one speed-report spec once and upsert its rows.

    Mirrors RealtimeMonitor._drain_key (open -> drain -> close per key) but
    runs once. Imports are idempotent because RealtimeUpdater uses INSERT OR
    REPLACE on primary keys. For 0B11/0B14 every open and every buffer is also
    appended to the capture log (src.realtime.capture_log) in the same
    transaction. The whole spec is one transaction: any rejected record or
    transport error rolls it back and raises.

    Args:
        database: Open database handler.
        spec: Realtime data spec (e.g., "0B12").
        date_keys: JVRTOpen keys (YYYYMMDD), opened in order.
        sid: JV-Link session ID.
        producer: Written to RT_CAPTURE_FETCH.Producer.
        jvlink: Optional JV-Link wrapper override (tests).
        updater: Optional RealtimeUpdater override (tests).
        jvrtopen_results: Optional list that receives the key, JVRTOpen code
            and capture fetch id of every open (src.fetcher.summary.jvrtopen_entry).
        stats: Optional counter dict to update in place, so a caller still
            sees what was read when this raises part-way.
        log_prefix: Prefix of the lines printed for operators.
    """

    from src.database.migration import require_current_primary_key
    from src.database.schema import create_all_tables
    from src.jvlink.bridge import JVLinkBridgeError
    from src.jvlink.wrapper import JVLinkError
    from src.realtime.updater import RealtimeUpdater, summarize_update_result

    if ensure_tables:
        create_all_tables(database)
    if spec == "0B11":
        # Fail before JVRTOpen: a legacy RT_WH key would overwrite earlier
        # announcements, and its migration is an operator step.
        require_current_primary_key(database, "RT_WH")

    database.begin_transaction()

    owns_jvlink = jvlink is None
    if jvlink is None:
        from src.fetcher.realtime import RealtimeFetcher

        jvlink = RealtimeFetcher(sid=sid).jvlink
    if updater is None:
        updater = RealtimeUpdater(database=database)

    if stats is None:
        stats = {}
    stats.update(
        {
            "records_fetched": 0,
            "records_parsed": 0,
            "records_imported": 0,
            "records_failed": 0,
        }
    )
    # The caller's list receives one entry per JVRTOpen call, including the
    # calls made before a failure; the counter dict keeps its shape.
    record_open = jvrtopen_results.append if jvrtopen_results is not None else (lambda entry: None)

    try:
        if owns_jvlink:
            jvlink.jv_init()
        for key in date_keys:
            capture = begin_capture(database, spec, key, producer=producer)
            try:
                ret, _count = jvlink.jv_rt_open(spec, key)
            except (JVLinkError, JVLinkBridgeError) as exc:
                code = getattr(exc, "error_code", None)
                record_open(jvrtopen_entry(key=key, jvrtopen_code=code))
                if code in SUBSCRIPTION_ERROR_CODES:
                    print(f"{log_prefix} {spec} not subscribed, skipping spec")
                    break
                raise
            fetch_id = None
            if capture is not None and ret >= -1:
                capture.opened(ret)
                fetch_id = capture.fetch_id
            record_open(jvrtopen_entry(key=key, jvrtopen_code=ret, fetch_id=fetch_id))
            if ret == -1:
                # No data published for this date key (normal).
                if capture is not None:
                    capture.complete()
                continue
            if ret < -1:
                raise RuntimeError(f"{spec} {key} JVRTOpen failed: {ret}")
            try:
                if spec == "0B14":
                    updater.replace_date_snapshot(key)
                while True:
                    ret_code, buff, _fname = jvlink.jv_read()
                    if ret_code == 0:
                        break
                    if ret_code == -1:
                        # File switch; keep reading.
                        continue
                    if ret_code < 0:
                        raise RuntimeError(f"{spec} {key} JVRead failed: {ret_code}")
                    if not buff:
                        raise RuntimeError(f"{spec} {key} JVRead returned no buffer")
                    stats["records_fetched"] += 1
                    if capture is not None:
                        capture.append(buff)
                    try:
                        result = updater.process_record(buff)
                    except Exception as exc:  # noqa: BLE001 - drain, then fail closed
                        stats["records_failed"] += 1
                        print(
                            f"{log_prefix} {spec} {key} record failed: {exc}",
                            file=sys.stderr,
                        )
                        continue
                    successful, failed = summarize_update_result(result)
                    stats["records_parsed"] += len(successful) + failed
                    stats["records_imported"] += len(successful)
                    stats["records_failed"] += failed
                if capture is not None:
                    capture.complete()
            finally:
                try:
                    jvlink.jv_close()
                except Exception:
                    pass
        if stats["records_failed"]:
            raise RuntimeError(
                f"{spec} realtime import rejected {stats['records_failed']} record(s)"
            )
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        if owns_jvlink:
            try:
                jvlink.jv_close()
            except Exception:
                pass
    return stats


# --- ``jltsql realtime fetch`` -------------------------------------------------

FETCH_GENERATOR = "jltsql realtime fetch"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_REQUIRED_RECORDS_MISSING = 3


class FetchUsageError(ValueError):
    """An argument the fetch refuses before touching config, DB or JV-Link."""


def _date_key(value: str, option: str) -> str:
    try:
        datetime.strptime(value, "%Y%m%d")
    except (TypeError, ValueError) as exc:
        raise FetchUsageError(f"{option} must be a real date in YYYYMMDD: {value!r}") from exc
    if len(value) != 8:
        raise FetchUsageError(f"{option} must be a real date in YYYYMMDD: {value!r}")
    return value


def resolve_window(date: str | None, from_date: str | None, to_date: str | None) -> tuple[str, str]:
    """``--date D`` or ``--from-date A --to-date B`` (inclusive), nothing else."""
    if date is not None:
        if from_date is not None or to_date is not None:
            raise FetchUsageError("use either --date or --from-date/--to-date, not both")
        key = _date_key(date, "--date")
        return key, key
    if from_date is None or to_date is None:
        raise FetchUsageError("a window is required: --date, or --from-date and --to-date")
    start = _date_key(from_date, "--from-date")
    end = _date_key(to_date, "--to-date")
    if end < start:
        raise FetchUsageError(f"--to-date {end} is before --from-date {start}")
    return start, end


def resolve_specs(raw: str) -> list[str]:
    specs = list(dict.fromkeys(part.strip().upper() for part in raw.split(",") if part.strip()))
    if not specs:
        raise FetchUsageError("--specs is empty")
    unsupported = [spec for spec in specs if spec not in DATE_KEYED_REALTIME_SPECS]
    if unsupported:
        raise FetchUsageError(
            f"unsupported spec(s) {','.join(unsupported)}: realtime fetch takes the "
            f"date-keyed JVRTOpen specs {','.join(DATE_KEYED_REALTIME_SPECS)}"
        )
    return specs


def resolve_required(raw: str | None, specs: list[str]) -> list[str]:
    if not raw:
        return []
    required = list(dict.fromkeys(part.strip().upper() for part in raw.split(",") if part.strip()))
    unselected = [spec for spec in required if spec not in specs]
    if unselected:
        raise FetchUsageError(
            f"--require-records spec(s) {','.join(unselected)} are not selected by --specs"
        )
    return required


def build_document(
    *,
    started_at: datetime,
    from_date: str | None,
    to_date: str | None,
    required_specs: list[str],
    specs: list[dict],
    failures: list[dict],
    exit_code: int,
    error: BaseException | None,
) -> dict:
    """Schema-1 summary document (docs/fetch_summary.md)."""
    from src import __version__ as jltsql_version
    from src.fetcher.summary import SUMMARY_SCHEMA_VERSION

    if error is not None:
        outcome = "error"
    elif exit_code == EXIT_USAGE:
        outcome = "usage_error"
    elif failures:
        outcome = "required_records_missing"
    else:
        outcome = "ok"
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generator": FETCH_GENERATOR,
        "jltsql_version": jltsql_version,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "from_date": from_date,
        "to_date": to_date,
        "required_specs": required_specs,
        "outcome": outcome,
        "exit_code": exit_code,
        "error": None if error is None else f"{type(error).__name__}: {error}"[:500],
        "requirement_failures": failures,
        "specs": specs,
    }


def run_realtime_fetch(
    database,
    specs: list[str],
    from_date: str,
    to_date: str,
    *,
    required_specs: list[str],
    sid: str,
    ensure_tables: bool,
    summaries: list[dict],
) -> list[dict]:
    """Fetch each spec once over the window; return the requirement failures.

    Spec summaries are appended to ``summaries`` as they finish, so a caller
    still has them when a spec raises (the spec's transaction is rolled back
    and the error re-raised; later specs do not run).
    """
    import time

    from src.fetcher.summary import requirement_failures, summarize_jvrtopen_spec

    date_keys = iter_date_keys(from_date, to_date)
    for spec in specs:
        started = time.monotonic()
        opens: list[dict] = []
        stats: dict = {}
        error: Exception | None = None
        skipped_code: int | None = None
        try:
            fetch_realtime_spec(
                database,
                spec,
                date_keys,
                sid=sid,
                producer=FETCH_GENERATOR,
                ensure_tables=ensure_tables,
                jvrtopen_results=opens,
                stats=stats,
            )
        except Exception as exc:
            error = exc
        if error is None and opens and opens[-1].get("jvrtopen_code") in SUBSCRIPTION_ERROR_CODES:
            skipped_code = opens[-1]["jvrtopen_code"]
        summaries.append(
            summarize_jvrtopen_spec(
                dataspec=spec,
                from_date=from_date,
                to_date=to_date,
                opens=opens,
                stats=stats,
                elapsed_seconds=time.monotonic() - started,
                error=error,
                skipped=skipped_code is not None,
                skipped_code=skipped_code,
            )
        )
        if error is not None:
            raise error
        print(
            f"[realtime-fetch] {spec} fetched={stats.get('records_fetched', 0)} "
            f"parsed={stats.get('records_parsed', 0)} "
            f"imported={stats.get('records_imported', 0)} "
            f"failed={stats.get('records_failed', 0)}"
        )
    return requirement_failures(required_specs, summaries)
