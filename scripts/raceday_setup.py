#!/usr/bin/env python
"""Pre-race DB setup: create tables + fetch historical data.

Run this before race day to pre-populate the database.

Usage:
    python scripts/raceday_setup.py [--db PATH] [--from-date YYYYMMDD]
"""

import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


def run(cmd: list, description: str) -> bool:
    print(f"\n[{description}]")
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, timeout=900)
    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode})")
        return False
    print("  OK")
    return True


def main():
    parser = argparse.ArgumentParser(description="Pre-race DB setup")
    parser.add_argument("--db", default="data/keiba.db")
    parser.add_argument("--from-date", default=None,
                        help="Historical data start date YYYYMMDD (default: 2 weeks ago)")
    args = parser.parse_args()

    today = date.today()
    yesterday = (today - timedelta(days=1)).strftime("%Y%m%d")
    from_date = args.from_date or (today - timedelta(days=14)).strftime("%Y%m%d")

    print(f"{'='*60}")
    print(f"  Pre-race DB Setup")
    print(f"  DB: {Path(args.db).resolve()}")
    print(f"  Historical range: {from_date} → {yesterday}")
    print(f"{'='*60}")

    base = [sys.executable, "-m", "src.cli.main"]

    steps = [
        # 1. Create tables
        (base + ["create-tables", "--db", args.db],
         "Create DB tables"),

        # 2. Create indexes
        (base + ["create-indexes", "--db", args.db],
         "Create DB indexes"),

        # 3. Fetch RACE data (race headers + entries)
        (base + ["fetch", "--from", from_date, "--to", yesterday,
                 "--spec", "RACE", "--option", "1", "--db", args.db],
         f"Fetch RACE data ({from_date}→{yesterday})"),

        # 4. Fetch DIFF (latest diff update)
        (base + ["fetch", "--from", from_date, "--to", yesterday,
                 "--spec", "DIFF", "--option", "1", "--db", args.db],
         f"Fetch DIFF data (payouts, odds)"),
    ]

    all_ok = True
    for cmd, desc in steps:
        ok = run(cmd, desc)
        if not ok:
            all_ok = False
            print(f"  [WARN] Step failed, continuing...")

    # Final verification
    print(f"\n{'='*60}")
    verify_cmd = [sys.executable, "scripts/raceday_verify.py",
                  "--db", args.db, "--phase", "pre"]
    run(verify_cmd, "Post-setup verification")

    if all_ok:
        print("\n[SETUP COMPLETE] Database is ready for race day.")
    else:
        print("\n[SETUP COMPLETE WITH WARNINGS] Check output above for issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
