#!/usr/bin/env python
"""Non-interactive daily JRA sync for Windows task scheduling."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import __version__ as JLTSQL_VERSION
from src.database import create_database_from_config
from src.fetcher.summary import (
    STATUS_NO_DATA,
    SUMMARY_SCHEMA_VERSION,
    jvrtopen_entry,
    requirement_failures,
    summarize_jvopen_spec,
    summarize_jvrtopen_spec,
    write_summary_json,
)
from src.importer.batch import BatchProcessor
from src.realtime.oneshot import SUBSCRIPTION_ERROR_CODES, fetch_realtime_spec
from src.utils.config import load_config
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

SUMMARY_GENERATOR = "jltsql scripts/daily_update.py"

UPDATE_SPECS = [
    ("TOKU", 2),
    ("RACE", 2),
    # Master deltas keep UM/KS/CH/BR/BN current after the initial DIFN setup.
    ("DIFN", 1),
    ("TCVN", 2),
    ("RCVN", 2),
    # Training data is updated daily and must be collected incrementally.
    # HC=坂路調教, WC=ウッドチップ調教. option=1 is the incremental fetch.
    ("SLOP", 1),
    ("WOOD", 1),
    # MING=データマイニング予想 (DM レコード -> NL_DM)。SE の mining ブロック
    # (DMTime/DMJyuni/KyakusituKubun) と NL_DM を供給する。option=1 の
    # incremental。レース当日発表のため過去分の一括 backfill は不可
    # (前向きにのみ蓄積される)。
    ("MING", 1),
    # Speed-report specs fetched via JVRTOpen with a date key (option unused).
    # 0B11: 速報馬体重 (WH)。発走約 1 時間前から発表ごとにレコード追加・更新
    # (JV-Data 4.9.0.1 提供タイミング)。RT_WH は発表時刻 (HappyoTime) を
    # PRIMARY KEY に含むので発表ごとに 1 行。1 週間保存なので過去分 backfill は不可。
    ("0B11", 1),
    # 0B12: 速報レース情報・払戻 (RA/SE/HR 成績確定後), 0B15: 速報レース情報
    # (RA/SE/HR 出走馬名表～)。RT_* テーブルは PRIMARY KEY + INSERT OR REPLACE
    # なので再実行しても重複しない（冪等）。
    ("0B12", 1),
    ("0B15", 1),
    # 0B14: 速報開催情報・一括。WE(天候馬場状態)/
    # AV(出走取消・除外)/JC/TC/CC を供給する。WE は NL 蓄積が存在しない
    # 速報専用レコードで、RT_WE を埋める唯一の経路。RT_* は PRIMARY KEY +
    # INSERT OR REPLACE で冪等。レース当日発表のため過去分 backfill は不可
    # (前向きにのみ蓄積)。過去の馬場状態は RA レコード側(field50/51)が供給する。
    # RT_* は取得ごとの日付単位全置換 (現在状態)。いつ何を受け取ったかは
    # 0B11 と同じく取得ログ RT_CAPTURE_* に追記する (docs/capture_log.md)。
    ("0B14", 1),
    # 0B16 is event-keyed (JVWatchEvent), not YYYYMMDD-keyed.
    ("0B51", 1),
]

REALTIME_SPEC_PREFIX = "0B"

# JV-Link は未契約データ種別に対し購読エラーを返す (-111 契約無し / -114 未購読
# 一括 / -115 未購読当該)。MING 等の任意契約スペックが未購読でも日次同期を
# 止めないよう、これらは --ignore-jvopen-error-codes の指定に関わらず警告して
# スキップする。realtime 経路(JVRTOpen)も同じ3コードを処理する。
# 定義は src.realtime.oneshot.SUBSCRIPTION_ERROR_CODES (上で import)。

# Exit codes. 0 and 2 keep their earlier meaning and an uncaught exception
# still exits 1; 3 is only reachable through --require-records.
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REQUIRED_RECORDS_MISSING = 3


def _is_realtime_spec(spec: str) -> bool:
    """Return True for JVRTOpen speed-report specs (e.g., 0B12, 0B15)."""

    return spec.upper().startswith(REALTIME_SPEC_PREFIX)


def _iter_date_keys(from_date: str, to_date: str) -> list[str]:
    """Return inclusive YYYYMMDD keys between from_date and to_date."""

    start = datetime.strptime(from_date, "%Y%m%d")
    end = datetime.strptime(to_date, "%Y%m%d")
    if end < start:
        return []
    return [
        (start + timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range((end - start).days + 1)
    ]


def _sync_realtime_spec(
    database,
    spec: str,
    from_date: str,
    to_date: str,
    sid: str,
    jvlink=None,
    updater=None,
    ensure_tables: bool = True,
    jvrtopen_results: list | None = None,
    stats: dict | None = None,
) -> dict:
    """Fetch a JVRTOpen speed-report spec for each date key and upsert rows.

    The fetch itself is src.realtime.oneshot.fetch_realtime_spec (shared with
    ``jltsql realtime fetch``); this keeps daily_update's signature.
    """

    return fetch_realtime_spec(
        database,
        spec,
        _iter_date_keys(from_date, to_date),
        sid=sid,
        producer=SUMMARY_GENERATOR,
        jvlink=jvlink,
        updater=updater,
        ensure_tables=ensure_tables,
        jvrtopen_results=jvrtopen_results,
        stats=stats,
        log_prefix="[daily-sync]",
    )


def _select_update_specs(specs: str | None) -> list[tuple[str, int]]:
    """Resolve a comma-separated spec allowlist against UPDATE_SPECS."""

    if not specs:
        return UPDATE_SPECS
    options = {spec: option for spec, option in UPDATE_SPECS}
    selected: list[tuple[str, int]] = []
    for raw in specs.split(","):
        spec = raw.strip().upper()
        if not spec:
            continue
        if spec not in options:
            raise ValueError(f"Unsupported daily update spec: {spec}")
        selected.append((spec, options[spec]))
    return selected


def _force_incremental_options(specs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Use normal incremental JVOpen for task-scheduler smoke/recovery runs."""

    return [(spec, 1 if option == 2 else option) for spec, option in specs]


def _parse_ignored_error_codes(value: str | None) -> set[int]:
    if not value:
        return set()
    return {int(part.strip()) for part in value.split(",") if part.strip()}


def _error_code_from_exception(exc: Exception) -> int | None:
    match = re.search(r"code:\s*(-?\d+)", str(exc))
    return int(match.group(1)) if match else None


def _effective_option(spec: str, configured_option: int, from_date: str) -> int:
    """Apply quickstart's setup fallback for specs that need full refresh."""

    if spec != "DIFN" or configured_option != 1:
        return configured_option
    from_date_dt = datetime.strptime(from_date, "%Y%m%d")
    now = datetime.now()
    months_ago = (now.year * 12 + now.month) - (from_date_dt.year * 12 + from_date_dt.month)
    return 4 if months_ago > 11 else configured_option


def _parse_required_specs(value: str | None, selected: list[tuple[str, int]]) -> list[str]:
    """Resolve --require-records against the specs this run will fetch."""

    if not value:
        return []
    known = {spec for spec, _ in UPDATE_SPECS}
    selected_specs = {spec for spec, _ in selected}
    required: list[str] = []
    for raw in value.split(","):
        spec = raw.strip().upper()
        if not spec:
            continue
        if spec not in known:
            raise ValueError(f"Unsupported --require-records spec: {spec}")
        if spec not in selected_specs:
            raise ValueError(f"--require-records spec {spec} is not selected by --specs")
        if spec not in required:
            required.append(spec)
    return required


def _configure_logging(config, log_file: str | None) -> None:
    """Send this run's structured log to a file (console stays errors-only).

    The import-time default is console-only at ERROR, which dropped every
    JVOpen result. --log-file (relative to cwd) wins; otherwise the config's
    logging.file settings apply, resolved against PROJECT_ROOT, falling back
    to PROJECT_ROOT/logs/jltsql.log.
    """

    level = str(config.get("logging.level", "INFO"))
    log_to_file = bool(log_file) or bool(config.get("logging.file.enabled", True))
    if not log_file:
        # The config path (and the fallback) is anchored at the project root,
        # not the scheduler's cwd, which may be read-only.
        configured = Path(str(config.get("logging.file.path", "") or "logs/jltsql.log"))
        log_file = str(configured if configured.is_absolute() else PROJECT_ROOT / configured)
    try:
        setup_logging(
            level=level,
            log_file=log_file,
            log_to_console=True,
            log_to_file=log_to_file,
            console_level="ERROR",
        )
    except OSError as exc:
        # An unwritable log location must not stop the sync itself.
        print(
            f"[daily-sync] WARNING file logging disabled: {exc}",
            file=sys.stderr,
        )
        setup_logging(level=level, log_to_console=True, log_to_file=False, console_level="ERROR")


def _jvopen_error_code(fetcher, exc: Exception) -> int | None:
    """The JV-Link code behind a failed spec: recorded by the fetcher, else parsed."""

    opens = fetcher.get_jvopen_results() if hasattr(fetcher, "get_jvopen_results") else []
    if opens and opens[-1].get("jvopen_code") not in (None, 0, -1):
        return opens[-1]["jvopen_code"]
    return _error_code_from_exception(exc)


def _report_spec(summary: dict) -> None:
    """Log one spec summary; a spec that got nothing back is logged as a warning."""

    fields = {
        key: summary[key]
        for key in (
            "dataspec",
            "kind",
            "option",
            "status",
            "jvopen_code",
            "fromtimes",
            "read_count",
            "download_count",
            "lastfiletimestamp",
            "records_read",
            "records_parsed",
            "records_imported",
            "records_failed",
            "records_out_of_range",
            "elapsed_seconds",
        )
    }
    logger.info("daily_update spec finished", **fields)
    if summary["status"] != STATUS_NO_DATA:
        return
    # IF 4.9.0.1 p.54: -1 also means "a newer JV-Link was published and the
    # user chose to download it", so no data is reported, not concluded.
    # Logged, not printed: TOKU/option-2 and off-day 0Bxx specs are often
    # legitimately empty, and --require-records is what turns "empty" into a
    # failure for the specs that must not be.
    logger.warning("daily_update spec returned no data", **fields)


def _sync_jvopen_spec(
    processor,
    spec: str,
    option: int,
    from_date: str,
    to_date: str,
    ensure_tables: bool,
    ignored_error_codes: set[int],
) -> tuple[dict, Exception | None]:
    """Run one JVOpen spec and summarize it; return the error to re-raise, if any."""

    started = time.monotonic()
    stats: dict = {}
    error: Exception | None = None
    skipped_code: int | None = None
    # A failure before JVOpen (schema setup, validation) must not report the
    # previous spec's opens and counters as this spec's.
    processor.fetcher.reset_statistics()
    try:
        stats = processor.process_date_range(
            data_spec=spec,
            from_date=from_date,
            to_date=to_date,
            option=option,
            ensure_tables=ensure_tables,
        )
    except Exception as exc:
        code = _jvopen_error_code(processor.fetcher, exc)
        if code in ignored_error_codes or code in SUBSCRIPTION_ERROR_CODES:
            print(f"[daily-sync] {spec} skipped: JVOpen code {code} (unsubscribed/ignored)")
            skipped_code = code
        else:
            error = exc
    fetcher = processor.fetcher
    completed = error is None and skipped_code is None
    summary = summarize_jvopen_spec(
        dataspec=spec,
        option=option,
        from_date=from_date,
        to_date=to_date,
        opens=fetcher.get_jvopen_results(),
        fetch_stats=stats if completed else fetcher.get_statistics(),
        records_imported=int(stats.get("records_imported", 0) or 0) if completed else None,
        records_out_of_range=fetcher.get_records_out_of_range(),
        elapsed_seconds=time.monotonic() - started,
        error=error,
        skipped=skipped_code is not None,
        skipped_code=skipped_code,
    )
    if completed:
        print(
            f"[daily-sync] {spec} fetched={stats.get('records_fetched', 0)} "
            f"parsed={stats.get('records_parsed', 0)} imported={stats.get('records_imported', 0)} "
            f"failed={stats.get('records_failed', 0)}"
        )
    return summary, error


def _sync_jvrtopen_spec(
    database,
    spec: str,
    from_date: str,
    to_date: str,
    sid: str,
    ensure_tables: bool,
    ignored_error_codes: set[int],
) -> tuple[dict, Exception | None]:
    """Run one JVRTOpen spec and summarize it; return the error to re-raise, if any."""

    started = time.monotonic()
    opens: list = []
    # Filled in place so the counts read before a failure survive it.
    stats: dict = {}
    error: Exception | None = None
    skipped_code: int | None = None
    # An exception means _sync_realtime_spec rolled the spec back.
    committed = True
    try:
        _sync_realtime_spec(
            database=database,
            spec=spec,
            from_date=from_date,
            to_date=to_date,
            sid=sid,
            ensure_tables=ensure_tables,
            jvrtopen_results=opens,
            stats=stats,
        )
    except Exception as exc:
        committed = False
        code = _error_code_from_exception(exc)
        if code in ignored_error_codes or code in SUBSCRIPTION_ERROR_CODES:
            print(f"[daily-sync] {spec} skipped: JVOpen code {code} (unsubscribed/ignored)")
            skipped_code = code
        else:
            error = exc
    if skipped_code is None and error is None and opens:
        # _sync_realtime_spec stops the spec on a subscription code and returns.
        last_code = opens[-1].get("jvrtopen_code")
        if last_code in SUBSCRIPTION_ERROR_CODES:
            skipped_code = last_code
    summary = summarize_jvrtopen_spec(
        dataspec=spec,
        from_date=from_date,
        to_date=to_date,
        opens=opens,
        stats=stats,
        elapsed_seconds=time.monotonic() - started,
        error=error,
        skipped=skipped_code is not None,
        skipped_code=skipped_code,
        committed=committed,
    )
    if error is None and skipped_code is None and stats:
        print(
            f"[daily-sync] {spec} fetched={stats.get('records_fetched', 0)} "
            f"parsed={stats.get('records_parsed', 0)} "
            f"imported={stats.get('records_imported', 0)} "
            f"failed={stats.get('records_failed', 0)}"
        )
    return summary, error


def _run_document(
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
    """Top-level summary document (contract: docs/fetch_summary.md)."""

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
        "generator": SUMMARY_GENERATOR,
        "jltsql_version": JLTSQL_VERSION,
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


def _exit_code_for(exc: BaseException) -> int:
    """The process exit code an exception escaping main() will produce."""

    if isinstance(exc, SystemExit):
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return 1


def _write_run_summary(path: str, document: dict, *, error_in_flight: bool) -> None:
    """Write the summary without masking the error that is already unwinding."""

    try:
        write_summary_json(path, document)
    except OSError as exc:
        print(f"[daily-sync] ERROR could not write --summary-json {path}: {exc}", file=sys.stderr)
        if not error_in_flight:
            raise


def _write_usage_error_summary(argv: list[str] | None, exc: SystemExit) -> None:
    """Write the summary for an argument argparse itself rejected.

    The real parse failed, so the path is recovered with a parser that knows
    only --summary-json. --help/--version (exit 0) write nothing.
    """

    exit_code = _exit_code_for(exc)
    if exit_code == 0:
        return
    probe = argparse.ArgumentParser(add_help=False)
    probe.add_argument("--summary-json", default=None)
    known, _ = probe.parse_known_args(argv)
    if not known.summary_json:
        return
    now = datetime.now().astimezone()
    _write_run_summary(
        known.summary_json,
        _run_document(
            started_at=now,
            from_date=None,
            to_date=None,
            required_specs=[],
            specs=[],
            failures=[],
            exit_code=exit_code,
            error=None,
        ),
        error_in_flight=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run daily JRA incremental sync")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--days-back", type=int, default=7, help="Fetch window size in days")
    parser.add_argument(
        "--days-forward", type=int, default=0, help="Fetch future card window size in days"
    )
    parser.add_argument(
        "--db", default=None, choices=["sqlite", "postgresql"], help="Override database type"
    )
    parser.add_argument(
        "--ensure-tables",
        dest="ensure_tables",
        action="store_true",
        default=True,
        help="Create/migrate tables before sync (default)",
    )
    parser.add_argument(
        "--no-ensure-tables",
        dest="ensure_tables",
        action="store_false",
        help="Skip table creation/migration before sync",
    )
    parser.add_argument(
        "--specs", default=None, help="Comma-separated subset of daily update specs"
    )
    parser.add_argument(
        "--force-incremental",
        action="store_true",
        help="Use JVOpen option=1 instead of option=2 for selected update specs",
    )
    parser.add_argument(
        "--ignore-jvopen-error-codes",
        default=None,
        help="Comma-separated JVOpen error codes to warn-and-skip for daily tasks",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        metavar="PATH",
        help="Write a per-spec JSON summary of JVOpen results and counts "
        "(docs/fetch_summary.md); written on failure too",
    )
    parser.add_argument(
        "--require-records",
        default=None,
        metavar="SPEC[,SPEC]",
        help="Exit 3 when any listed spec got nothing back "
        "(JVOpen read_count 0, or no records for a 0Bxx spec)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help="Structured log file (default: config logging.file.path, else ./logs/jltsql.log)",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        _write_usage_error_summary(argv, exc)
        raise

    started_at = datetime.now().astimezone()
    to_date = (datetime.now() + timedelta(days=max(args.days_forward, 0))).strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=max(args.days_back, 1))).strftime("%Y%m%d")
    summaries: list[dict] = []
    required_specs: list[str] = []
    failures: list[dict] = []
    error: BaseException | None = None
    exit_code = EXIT_OK
    # Everything after argument parsing runs inside this try so that the
    # summary is written on every exit path: usage errors, config/database
    # failures, JV-Link errors and interrupts alike.
    try:
        config_path = args.config or str(PROJECT_ROOT / "config" / "config.yaml")
        config = load_config(config_path)
        _configure_logging(config, args.log_file)

        try:
            update_specs = _select_update_specs(args.specs)
            required_specs = _parse_required_specs(args.require_records, update_specs)
        except ValueError as exc:
            print(f"[daily-sync] {exc}", file=sys.stderr)
            exit_code = EXIT_USAGE
            return exit_code
        if args.force_incremental:
            update_specs = _force_incremental_options(update_specs)
        ignored_error_codes = _parse_ignored_error_codes(args.ignore_jvopen_error_codes)

        database = create_database_from_config(config, db_type_override=args.db)
        sid = config.get("jvlink.sid", "JLTSQL")
        logger.info(
            "daily_update started",
            from_date=from_date,
            to_date=to_date,
            specs=[spec for spec, _ in update_specs],
            required_specs=required_specs,
            jltsql_version=JLTSQL_VERSION,
        )

        with database:
            processor = BatchProcessor(
                database=database,
                sid=sid,
                batch_size=1000,
                show_progress=False,
            )
            for spec, option in update_specs:
                if _is_realtime_spec(spec):
                    print(f"[daily-sync] {spec} {from_date}..{to_date} (realtime)")
                    summary, spec_error = _sync_jvrtopen_spec(
                        database,
                        spec,
                        from_date,
                        to_date,
                        sid,
                        args.ensure_tables,
                        ignored_error_codes,
                    )
                else:
                    option = _effective_option(spec, option, from_date)
                    print(f"[daily-sync] {spec} {from_date}..{to_date} option={option}")
                    summary, spec_error = _sync_jvopen_spec(
                        processor,
                        spec,
                        option,
                        from_date,
                        to_date,
                        args.ensure_tables,
                        ignored_error_codes,
                    )
                summaries.append(summary)
                _report_spec(summary)
                if spec_error is not None:
                    raise spec_error
        failures = requirement_failures(required_specs, summaries)
        if failures:
            exit_code = EXIT_REQUIRED_RECORDS_MISSING
            for failure in failures:
                logger.error("daily_update required spec got no records", **failure)
                print(
                    f"[daily-sync] ERROR required spec {failure['dataspec']} got no records "
                    f"(status={failure['status']} read_count={failure['read_count']})",
                    file=sys.stderr,
                )
        return exit_code
    except BaseException as exc:
        error = exc
        exit_code = _exit_code_for(exc)
        logger.error("daily_update failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        if args.summary_json:
            _write_run_summary(
                args.summary_json,
                _run_document(
                    started_at=started_at,
                    from_date=from_date,
                    to_date=to_date,
                    required_specs=required_specs,
                    specs=summaries,
                    failures=failures,
                    exit_code=exit_code,
                    error=error,
                ),
                error_in_flight=error is not None,
            )


if __name__ == "__main__":
    raise SystemExit(main())
