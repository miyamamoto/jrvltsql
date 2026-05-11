#!/usr/bin/env python
"""Non-interactive daily JRA sync for Windows task scheduling."""

from __future__ import annotations

import argparse
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
]


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
    parser.add_argument("--db", default=None, choices=["sqlite", "postgresql"], help="Override database type")
    parser.add_argument("--ensure-tables", action="store_true", help="Create/migrate tables before sync")
    args = parser.parse_args()

    config_path = args.config or str(PROJECT_ROOT / "config" / "config.yaml")
    config = load_config(config_path)
    database = create_database_from_config(config, db_type_override=args.db)

    to_date = datetime.now().strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=max(args.days_back, 1))).strftime("%Y%m%d")

    with database:
        processor = BatchProcessor(
            database=database,
            sid=config.get("jvlink.sid", "JLTSQL"),
            batch_size=1000,
            service_key=config.get("jvlink.service_key"),
            show_progress=False,
        )
        for spec, option in UPDATE_SPECS:
            option = _effective_option(spec, option, from_date)
            print(f"[daily-sync] {spec} {from_date}..{to_date} option={option}")
            stats = processor.process_date_range(
                data_spec=spec,
                from_date=from_date,
                to_date=to_date,
                option=option,
                ensure_tables=args.ensure_tables,
            )
            print(
                f"[daily-sync] {spec} fetched={stats.get('records_fetched', 0)} "
                f"parsed={stats.get('records_parsed', 0)} imported={stats.get('records_imported', 0)} "
                f"failed={stats.get('records_failed', 0)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
