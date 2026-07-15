#!/usr/bin/env python
"""Non-interactive daily JRA sync for Windows task scheduling."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import create_database_from_config
from src.importer.batch import BatchProcessor
from src.utils.config import load_config

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
    ("0B14", 1),
    # 0B16 is event-keyed (JVWatchEvent), not YYYYMMDD-keyed.
    ("0B51", 1),
]

REALTIME_SPEC_PREFIX = "0B"

# JV-Link は未契約データ種別に対し購読エラーを返す (-111 契約無し / -114 未購読
# 一括 / -115 未購読当該)。MING 等の任意契約スペックが未購読でも日次同期を
# 止めないよう、これらは --ignore-jvopen-error-codes の指定に関わらず警告して
# スキップする。realtime 経路(JVRTOpen)も同じ3コードを処理する。
SUBSCRIPTION_ERROR_CODES = frozenset({-111, -114, -115})


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
) -> dict:
    """Fetch a JVRTOpen speed-report spec for each date key and upsert rows.

    Mirrors RealtimeMonitor._drain_key (open -> drain -> close per key) but
    runs once per daily sync instead of looping. Imports are idempotent
    because RealtimeUpdater uses INSERT OR REPLACE on primary keys.

    Args:
        database: Open database handler.
        spec: Realtime data spec (e.g., "0B12").
        from_date: Start date YYYYMMDD (inclusive).
        to_date: End date YYYYMMDD (inclusive).
        sid: JV-Link session ID.
        jvlink: Optional JV-Link wrapper override (tests).
        updater: Optional RealtimeUpdater override (tests).
    """

    from src.jvlink.bridge import JVLinkBridgeError
    from src.jvlink.wrapper import JVLinkError
    from src.database.schema import create_all_tables
    from src.realtime.updater import RealtimeUpdater, summarize_update_result

    if ensure_tables:
        create_all_tables(database)

    database.begin_transaction()

    owns_jvlink = jvlink is None
    if jvlink is None:
        from src.fetcher.realtime import RealtimeFetcher

        jvlink = RealtimeFetcher(sid=sid).jvlink
    if updater is None:
        updater = RealtimeUpdater(database=database)

    stats = {
        "records_fetched": 0,
        "records_parsed": 0,
        "records_imported": 0,
        "records_failed": 0,
    }

    try:
        if owns_jvlink:
            jvlink.jv_init()
        for key in _iter_date_keys(from_date, to_date):
            try:
                ret, _count = jvlink.jv_rt_open(spec, key)
            except (JVLinkError, JVLinkBridgeError) as exc:
                code = getattr(exc, "error_code", None)
                if code in SUBSCRIPTION_ERROR_CODES:
                    print(f"[daily-sync] {spec} not subscribed, skipping spec")
                    break
                raise
            if ret == -1:
                # No data published for this date key (normal).
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
                    try:
                        result = updater.process_record(buff)
                    except Exception as exc:  # noqa: BLE001 - drain, then fail closed
                        stats["records_failed"] += 1
                        print(
                            f"[daily-sync] {spec} {key} record failed: {exc}",
                            file=sys.stderr,
                        )
                        continue
                    successful, failed = summarize_update_result(result)
                    stats["records_parsed"] += len(successful) + failed
                    stats["records_imported"] += len(successful)
                    stats["records_failed"] += failed
            finally:
                try:
                    jvlink.jv_close()
                except Exception:
                    pass
        if stats["records_failed"]:
            raise RuntimeError(
                f"{spec} realtime import rejected " f"{stats['records_failed']} record(s)"
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


def main() -> int:
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
    args = parser.parse_args()

    config_path = args.config or str(PROJECT_ROOT / "config" / "config.yaml")
    config = load_config(config_path)
    database = create_database_from_config(config, db_type_override=args.db)

    to_date = (datetime.now() + timedelta(days=max(args.days_forward, 0))).strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=max(args.days_back, 1))).strftime("%Y%m%d")

    with database:
        processor = BatchProcessor(
            database=database,
            sid=config.get("jvlink.sid", "JLTSQL"),
            batch_size=1000,
            service_key=config.get("jvlink.service_key"),
            show_progress=False,
        )
        try:
            update_specs = _select_update_specs(args.specs)
        except ValueError as exc:
            print(f"[daily-sync] {exc}", file=sys.stderr)
            return 2
        if args.force_incremental:
            update_specs = _force_incremental_options(update_specs)
        ignored_error_codes = _parse_ignored_error_codes(args.ignore_jvopen_error_codes)

        for spec, option in update_specs:
            if _is_realtime_spec(spec):
                print(f"[daily-sync] {spec} {from_date}..{to_date} (realtime)")
                try:
                    stats = _sync_realtime_spec(
                        database=database,
                        spec=spec,
                        from_date=from_date,
                        to_date=to_date,
                        sid=config.get("jvlink.sid", "JLTSQL"),
                        ensure_tables=args.ensure_tables,
                    )
                except Exception as exc:
                    code = _error_code_from_exception(exc)
                    if code in ignored_error_codes or code in SUBSCRIPTION_ERROR_CODES:
                        print(
                            f"[daily-sync] {spec} skipped: JVOpen code {code} (unsubscribed/ignored)"
                        )
                        continue
                    raise
                print(
                    f"[daily-sync] {spec} fetched={stats.get('records_fetched', 0)} "
                    f"parsed={stats.get('records_parsed', 0)} "
                    f"imported={stats.get('records_imported', 0)} "
                    f"failed={stats.get('records_failed', 0)}"
                )
                continue
            option = _effective_option(spec, option, from_date)
            print(f"[daily-sync] {spec} {from_date}..{to_date} option={option}")
            try:
                stats = processor.process_date_range(
                    data_spec=spec,
                    from_date=from_date,
                    to_date=to_date,
                    option=option,
                    ensure_tables=args.ensure_tables,
                )
            except Exception as exc:
                code = _error_code_from_exception(exc)
                if code in ignored_error_codes or code in SUBSCRIPTION_ERROR_CODES:
                    print(f"[daily-sync] {spec} skipped: JVOpen code {code} (unsubscribed/ignored)")
                    continue
                raise
            print(
                f"[daily-sync] {spec} fetched={stats.get('records_fetched', 0)} "
                f"parsed={stats.get('records_parsed', 0)} imported={stats.get('records_imported', 0)} "
                f"failed={stats.get('records_failed', 0)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
