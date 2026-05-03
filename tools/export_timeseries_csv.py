#!/usr/bin/env python3
"""Export TS_O1/TS_O2 rows from the configured PostgreSQL database to CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pg8000.dbapi as pgdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import load_config


TABLES = ("TS_O1", "TS_O2")


def _normalise_date(value: str) -> str:
    text = value.replace("-", "").strip()
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"invalid date: {value}")
    return text


def _postgres_config(config_path: str) -> dict:
    config = load_config(config_path)
    pg = config.get("databases.postgresql") or config.get("database.postgresql") or {}
    if not pg:
        raise RuntimeError("PostgreSQL configuration not found")
    return pg


def export_table(
    conn,
    table_name: str,
    start_date: str,
    end_date: str,
    output_dir: Path,
    batch_size: int,
) -> int:
    source_table = table_name.lower()
    out_path = output_dir / f"{table_name}.csv"
    date_expr = "CAST(year AS TEXT) || LPAD(CAST(monthday AS TEXT), 4, '0')"
    query = f"""
        SELECT *
        FROM {source_table}
        WHERE {date_expr} >= %s
          AND {date_expr} <= %s
        ORDER BY year, monthday, jyocd, racenum
    """

    total = 0
    cur = conn.cursor()
    try:
        cur.execute(query, (start_date, end_date))
        columns = [desc[0] for desc in cur.description]
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(columns)
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                writer.writerows(rows)
                total += len(rows)
    finally:
        cur.close()
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tables", default="TS_O1,TS_O2")
    parser.add_argument("--batch-size", type=int, default=100_000)
    args = parser.parse_args()

    start_date = _normalise_date(args.start_date)
    end_date = _normalise_date(args.end_date)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    requested_tables = tuple(t.strip().upper() for t in args.tables.split(",") if t.strip())
    invalid = sorted(set(requested_tables) - set(TABLES))
    if invalid:
        raise SystemExit(f"unsupported tables: {', '.join(invalid)}")

    pg = _postgres_config(args.config)
    conn = pgdb.connect(
        host=pg.get("host", "localhost"),
        port=int(pg.get("port", 5432)),
        database=pg.get("database", "keiba"),
        user=pg.get("user", "postgres"),
        password=pg.get("password", ""),
    )
    try:
        grand_total = 0
        for table in requested_tables:
            count = export_table(conn, table, start_date, end_date, output_dir, args.batch_size)
            grand_total += count
            print(f"{table}: exported {count:,} rows")
        print(f"total: {grand_total:,} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
