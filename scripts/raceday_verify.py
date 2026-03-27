#!/usr/bin/env python
"""Race day verification script.

Checks whether today's JRA race data is correctly stored in the database.
Designed to be called periodically throughout race day.

Usage:
    python scripts/raceday_verify.py [--db PATH] [--date YYYYMMDD] [--fetch]

Exits with code 0 if all checks pass, non-zero if issues found.
"""

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_today() -> str:
    return date.today().strftime("%Y%m%d")

def get_today_year_monthday() -> tuple[str, str]:
    d = date.today()
    return d.strftime("%Y"), d.strftime("%m%d")


def check_table(con: sqlite3.Connection, table: str) -> int:
    try:
        row = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return -1  # table missing


def check_today_races(con: sqlite3.Connection, year: str, monthday: str) -> dict:
    """Check if today's races are in RA and SE tables."""
    results = {}

    # RA (race header) for today
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?",
            (year, monthday)
        ).fetchone()
        results["NL_RA_today"] = row[0] if row else 0
    except sqlite3.OperationalError:
        results["NL_RA_today"] = -1

    # SE (race entries / starters) for today
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=?",
            (year, monthday)
        ).fetchone()
        results["NL_SE_today"] = row[0] if row else 0
    except sqlite3.OperationalError:
        results["NL_SE_today"] = -1

    # RT_RA (realtime race) for today
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?",
            (year, monthday)
        ).fetchone()
        results["RT_RA_today"] = row[0] if row else 0
    except sqlite3.OperationalError:
        results["RT_RA_today"] = -1

    # H1 payouts for today
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM NL_H1 WHERE Year=? AND MonthDay=?",
            (year, monthday)
        ).fetchone()
        results["NL_H1_today"] = row[0] if row else 0
    except sqlite3.OperationalError:
        results["NL_H1_today"] = -1

    return results


def run_fetch(spec: str, from_date: str, to_date: str, option: int, db: str) -> bool:
    """Run CLI fetch command. Returns True if successful."""
    cmd = [
        sys.executable, "-m", "src.cli.main",
        "fetch",
        "--from", from_date,
        "--to", to_date,
        "--spec", spec,
        "--option", str(option),
        "--db", db,
        "--no-progress",
    ]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, timeout=600)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Race day verification")
    parser.add_argument("--db", default="data/keiba.db", help="SQLite DB path")
    parser.add_argument("--date", default=None, help="Race date YYYYMMDD (default: today)")
    parser.add_argument("--fetch", action="store_true", help="Auto-fetch missing data")
    parser.add_argument("--phase", choices=["pre", "mid", "post", "final"], default="mid",
                        help="Verification phase")
    args = parser.parse_args()

    race_date = args.date or get_today()
    year = race_date[:4]
    monthday = race_date[4:6] + race_date[6:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"  Race Day Verification  [{now}]")
    print(f"  Date: {race_date}  Phase: {args.phase}")
    print(f"  DB:   {Path(args.db).resolve()}")
    print(f"{'='*60}\n")

    db_path = Path(args.db)
    issues = []

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path.resolve()}")
        print("  Run: python -m src.cli.main create-tables --db data/keiba.db")
        sys.exit(2)

    con = sqlite3.connect(db_path)
    try:
        # 1. Overall table counts
        print("--- Overall Table Counts ---")
        key_tables = ["NL_RA", "NL_SE", "NL_UM", "NL_KS", "NL_H1", "NL_O1"]
        for t in key_tables:
            count = check_table(con, t)
            if count == -1:
                print(f"  {t:15s}  MISSING")
                issues.append(f"Table {t} does not exist")
            else:
                print(f"  {t:15s}  {count:>10,} rows")

        # 2. Today's race data
        print(f"\n--- Today's Data ({race_date}) ---")
        today_data = check_today_races(con, year, monthday)
        for key, count in today_data.items():
            status = f"{count:>6} rows" if count >= 0 else "  N/A (table missing)"
            print(f"  {key:20s}  {status}")

        # Phase-specific checks
        if args.phase == "pre":
            # Before races: need at least RA entries for today
            if today_data.get("NL_RA_today", 0) == 0:
                issues.append("NL_RA: no race headers for today (entries not yet fetched)")
                if args.fetch:
                    print(f"\n[AUTO-FETCH] Fetching today RACE data (option=2)...")
                    ok = run_fetch("RACE", race_date, race_date, 2, args.db)
                    issues.clear() if ok else None
                    if ok:
                        new_count = check_table(con, "NL_RA")
                        print(f"  Fetch complete. NL_RA total: {new_count:,}")

        elif args.phase in ("mid", "post"):
            # During/after races: check results are coming in
            ra_today = today_data.get("NL_RA_today", 0)
            se_today = today_data.get("NL_SE_today", 0)
            if ra_today == 0:
                issues.append("NL_RA: no race headers for today")
            if se_today == 0:
                issues.append("NL_SE: no race entries for today")
            if args.fetch and (ra_today == 0 or se_today == 0):
                print(f"\n[AUTO-FETCH] Fetching RACE data (option=1)...")
                ok = run_fetch("RACE", race_date, race_date, 1, args.db)
                if ok:
                    today_data = check_today_races(con, year, monthday)
                    print(f"  After fetch: RA={today_data['NL_RA_today']}, SE={today_data['NL_SE_today']}")

        elif args.phase == "final":
            # After all races: need payouts too
            ra_today = today_data.get("NL_RA_today", 0)
            h1_today = today_data.get("NL_H1_today", 0)
            if ra_today == 0:
                issues.append("NL_RA: no race data for today")
            if h1_today == 0:
                issues.append("NL_H1: no payout data for today (H1 fetch needed)")
                if args.fetch:
                    print(f"\n[AUTO-FETCH] Fetching DIFFU (payouts) data...")
                    ok = run_fetch("DIFFU", race_date, race_date, 1, args.db)
                    if ok:
                        today_data = check_today_races(con, year, monthday)
                        print(f"  After fetch: H1={today_data['NL_H1_today']}")

        # 3. Summary
        print(f"\n{'='*60}")
        if issues:
            print(f"[ISSUES FOUND: {len(issues)}]")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            sys.exit(1)
        else:
            print("[OK] All checks passed.")
            sys.exit(0)

    finally:
        con.close()


if __name__ == "__main__":
    main()
