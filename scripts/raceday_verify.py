#!/usr/bin/env python
"""Comprehensive race day verification script.

Verifies both 蓄積系 (NL_) and 速報系 (RT_) data for today's JRA races.
Designed to be called at multiple checkpoints throughout race day.

JRA Saturday schedule (approx):
  10:05  1R start  → RT_ data ~10:20
  11:45  4R start  → RT_ data ~12:00
  13:40  7R start  → RT_ data ~13:55
  15:25 10R start  → RT_ data ~15:40
  16:00 11R 重賞   → RT_ data ~16:18
  16:30 12R last   → RT_ data ~16:47
  17:30+ NL_ payouts available

Usage:
    python scripts/raceday_verify.py --phase pre        # 事前確認
    python scripts/raceday_verify.py --phase rt-check   # 速報確認 (レース後)
    python scripts/raceday_verify.py --phase nl-mid     # 蓄積系中間確認
    python scripts/raceday_verify.py --phase post       # 全レース終了後
    python scripts/raceday_verify.py --phase final      # 最終検証 (払戻込み)
    python scripts/raceday_verify.py --phase quickstart # quickstart.bat検証
    python scripts/raceday_verify.py --phase auto       # 現在時刻からphaseを自動判定 (/loop向け)

Exits with code 0 if checks pass, 1 if issues found, 2 if fatal error.
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path


DB_PATH_DEFAULT = "data/keiba.db"

# ---------------------------------------------------------------------------
# Auto phase detection (/loop support)
# ---------------------------------------------------------------------------

# JRA Saturday time → phase mapping
_PHASE_SCHEDULE = [
    (10 * 60,       "pre"),        # ~10:00 before races start
    (13 * 60,       "rt-check"),   # 10:00-13:00 early races (1R~4R)
    (16 * 60 + 30,  "nl-mid"),     # 13:00-16:30 mid races (7R~11R)
    (18 * 60,       "post"),       # 16:30-18:00 all races done
    (20 * 60,       "final"),      # 18:00-20:00 payouts available
    (24 * 60,       "quickstart"), # 20:00+ end of day
]


def auto_detect_phase() -> str:
    """Detect appropriate verification phase based on current time (JRA Saturday schedule)."""
    now = datetime.now()
    t = now.hour * 60 + now.minute
    for threshold, phase in _PHASE_SCHEDULE:
        if t < threshold:
            return phase
    return "quickstart"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def q(con, sql, params=()):
    try:
        row = con.execute(sql, params).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return None  # table/column missing


def q_rows(con, sql, params=()):
    try:
        return con.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return None


def table_exists(con, table):
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def run_fetch(spec, from_date, to_date, option, db):
    cmd = [sys.executable, "-m", "src.cli.main", "fetch",
           "--from", from_date, "--to", to_date,
           "--spec", spec, "--option", str(option),
           "--db", db, "--no-progress"]
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, timeout=600)
    return r.returncode == 0


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_schema(con, issues):
    """Verify all expected NL_ and RT_ tables exist."""
    print("--- Schema Check ---")
    nl_required = ["NL_RA", "NL_SE", "NL_H1", "NL_H6", "NL_HR",
                   "NL_O1", "NL_O2", "NL_O3", "NL_O4", "NL_O5", "NL_O6",
                   "NL_WE", "NL_WH", "NL_UM", "NL_KS", "NL_TK"]
    rt_required = ["RT_RA", "RT_SE", "RT_H1", "RT_H6",
                   "RT_O1", "RT_O2", "RT_O3", "RT_O4", "RT_O5", "RT_O6",
                   "RT_WH", "RT_CC", "RT_JC"]

    missing_nl = [t for t in nl_required if not table_exists(con, t)]
    missing_rt = [t for t in rt_required if not table_exists(con, t)]

    if missing_nl:
        print(f"  [MISS] NL_ missing: {missing_nl}")
        issues.append(f"Missing NL_ tables: {missing_nl}")
    else:
        print(f"  [OK]  NL_ tables: {len(nl_required)} present")

    if missing_rt:
        print(f"  [MISS] RT_ missing: {missing_rt}")
        issues.append(f"Missing RT_ tables: {missing_rt}")
    else:
        print(f"  [OK]  RT_ tables: {len(rt_required)} present")


def check_nl_today(con, year, monthday, issues, label="NL_ 蓄積系"):
    """Check NL_ tables for today's race data."""
    print(f"\n--- {label} ---")
    y, m = year, monthday

    checks = {
        "NL_RA  (race header)": q(con, "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_SE  (starters)   ": q(con, "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_SE  (確定着順)   ": q(con, "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=? AND KakuteiJyuni='01'", (y, m)),
        "NL_H1  (payouts)    ": q(con, "SELECT COUNT(*) FROM NL_H1 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_H6  (3連単)      ": q(con, "SELECT COUNT(*) FROM NL_H6 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O1  (単勝odds)   ": q(con, "SELECT COUNT(*) FROM NL_O1 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_WH  (track cond) ": q(con, "SELECT COUNT(*) FROM NL_WH WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_TK  (track info) ": q(con, "SELECT COUNT(*) FROM NL_TK WHERE Year=? AND MonthDay=?", (y, m)),
    }

    for name, count in checks.items():
        if count is None:
            print(f"  {name}  TABLE MISSING")
        else:
            marker = "  " if count > 0 else "  [!]"
            print(f"{marker} {name}  {count:>6}")

    ra_count = checks.get("NL_RA  (race header)")
    if ra_count is not None and ra_count == 0:
        issues.append("NL_RA: no race headers for today")

    # Venue breakdown
    rows = q_rows(con, "SELECT JyoCD, COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=? GROUP BY JyoCD", (y, m))
    if rows:
        venue_str = ", ".join(f"場{r[0]}:{r[1]}R" for r in rows)
        print(f"  NL_RA  競馬場別         {venue_str}")

    return checks


def check_rt_today(con, year, monthday, issues, label="RT_ 速報系"):
    """Check RT_ tables for today's realtime data."""
    print(f"\n--- {label} ---")
    y, m = year, monthday

    checks = {
        "RT_RA  (race 速報)  ": q(con, "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_SE  (着順 速報)  ": q(con, "SELECT COUNT(*) FROM RT_SE WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_H1  (払戻 速報)  ": q(con, "SELECT COUNT(*) FROM RT_H1 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_H6  (3連単速報)  ": q(con, "SELECT COUNT(*) FROM RT_H6 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O1  (単勝 速報)  ": q(con, "SELECT COUNT(*) FROM RT_O1 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O5  (3連複速報)  ": q(con, "SELECT COUNT(*) FROM RT_O5 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O6  (3連単速報)  ": q(con, "SELECT COUNT(*) FROM RT_O6 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_WH  (馬場 速報)  ": q(con, "SELECT COUNT(*) FROM RT_WH WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_CC  (取消 速報)  ": q(con, "SELECT COUNT(*) FROM RT_CC WHERE Year=? AND MonthDay=?", (y, m)),
    }

    for name, count in checks.items():
        if count is None:
            print(f"  {name}  TABLE MISSING")
        else:
            marker = "  " if count > 0 else "  [!]"
            print(f"{marker} {name}  {count:>6}")

    return checks


def check_nl_rt_consistency(con, year, monthday, issues):
    """Compare NL_ vs RT_ counts to detect sync issues."""
    print("\n--- NL_ vs RT_ Consistency ---")
    y, m = year, monthday

    nl_ra = q(con, "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_ra = q(con, "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    nl_h1 = q(con, "SELECT COUNT(*) FROM NL_H1 WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_h1 = q(con, "SELECT COUNT(*) FROM RT_H1 WHERE Year=? AND MonthDay=?", (y, m)) or 0

    print(f"  NL_RA={nl_ra:4}  RT_RA={rt_ra:4}  {'OK' if nl_ra > 0 or rt_ra > 0 else '[!] both zero'}")
    print(f"  NL_H1={nl_h1:4}  RT_H1={rt_h1:4}  {'OK' if nl_h1 > 0 or rt_h1 > 0 else '[!] no payouts yet'}")

    if nl_ra > 0 and rt_ra == 0:
        issues.append("RT_RA=0 but NL_RA has data - realtime monitoring may not be running")
    if nl_ra == 0 and rt_ra == 0:
        issues.append("Both NL_RA and RT_RA=0 for today - no race data at all")


def check_master_data(con, issues):
    """Check horse/jockey master tables."""
    print("\n--- Master Data ---")
    um = q(con, "SELECT COUNT(*) FROM NL_UM") or 0
    ks = q(con, "SELECT COUNT(*) FROM NL_KS") or 0
    print(f"  NL_UM  (horses)    {um:>8,}")
    print(f"  NL_KS  (jockeys)   {ks:>8,}")
    if um == 0:
        issues.append("NL_UM (horse master) is empty - run setup fetch")
    if ks == 0:
        issues.append("NL_KS (jockey master) is empty - run setup fetch")


def run_unit_tests(issues):
    """Run unit test suite."""
    print("\n--- Unit Tests ---")
    cmd = [sys.executable, "-m", "pytest", "tests/",
           "-q", "--tb=line",
           "--ignore=tests/unit/test_jvlink_bridge.py",
           "--ignore=tests/unit/test_nvlink_bridge.py",
           "--ignore=tests/integration/",
           "--ignore=tests/e2e/",
           "--basetemp=C:/tmp/pytest-jrvl",
           "--no-header"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    # Print last few lines
    lines = (r.stdout + r.stderr).strip().splitlines()
    for line in lines[-8:]:
        print(f"  {line}")
    if r.returncode != 0:
        issues.append(f"Unit tests failed (exit {r.returncode}) - see output above")
        return False
    return True


def test_quickstart(db, issues):
    """Verify quickstart.bat flow (dry run via quickstart.py --check)."""
    print("\n--- quickstart.bat Smoke Test ---")
    # Check that quickstart.py exists and is importable
    qs = Path("scripts/quickstart.py")
    bat = Path("scripts/quickstart.bat")
    if not qs.exists():
        print(f"  [MISS] scripts/quickstart.py not found")
        issues.append("scripts/quickstart.py missing")
        return
    if not bat.exists():
        print(f"  [MISS] scripts/quickstart.bat not found")
        issues.append("scripts/quickstart.bat missing")
        return

    # Syntax check
    r = subprocess.run([sys.executable, "-m", "py_compile", str(qs)],
                       capture_output=True, timeout=10)
    if r.returncode == 0:
        print(f"  [OK]  scripts/quickstart.py syntax OK")
    else:
        print(f"  [FAIL] scripts/quickstart.py syntax error: {r.stderr.decode()}")
        issues.append("quickstart.py has syntax errors")
        return

    # Check bat references valid scripts
    bat_text = bat.read_text(encoding="utf-8", errors="replace")
    if "NAR" in bat_text or "nar_v5" in bat_text:
        issues.append("quickstart.bat still contains NAR references")
        print("  [FAIL] quickstart.bat contains NAR references")
    else:
        print(f"  [OK]  scripts/quickstart.bat is JRA-only")

    # Check DB is accessible
    if Path(db).exists():
        print(f"  [OK]  DB exists: {Path(db).resolve()}")
    else:
        print(f"  [!]   DB not found: {db} (will be created on first run)")


def write_report(phase, race_date, nl_checks, rt_checks, issues, report_path):
    """Write JSON report for this checkpoint."""
    report = {
        "phase": phase,
        "race_date": race_date,
        "timestamp": datetime.now().isoformat(),
        "issues_count": len(issues),
        "issues": issues,
        "nl": {k.strip(): v for k, v in (nl_checks or {}).items()},
        "rt": {k.strip(): v for k, v in (rt_checks or {}).items()},
    }
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Report saved: {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Race day comprehensive verification")
    parser.add_argument("--db", default=DB_PATH_DEFAULT)
    parser.add_argument("--date", default=None, help="YYYYMMDD (default: today)")
    parser.add_argument("--fetch", action="store_true", help="Auto-fetch missing NL_ data")
    parser.add_argument("--phase", default="auto",
                        choices=["pre", "rt-check", "nl-mid", "post", "final", "quickstart", "auto"],
                        help="Verification phase (auto=現在時刻から自動判定)")
    args = parser.parse_args()

    # Resolve auto phase
    if args.phase == "auto":
        args.phase = auto_detect_phase()
        print(f"[auto] Detected phase: {args.phase} (based on {datetime.now().strftime('%H:%M')})")

    race_date = args.date or date.today().strftime("%Y%m%d")
    year = race_date[:4]
    monthday = race_date[4:6] + race_date[6:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*65}")
    print(f"  Race Day Verification  [{now}]")
    print(f"  Phase: {args.phase:12s}  Date: {race_date}")
    print(f"  DB:    {Path(args.db).resolve()}")
    print(f"{'='*65}\n")

    issues = []
    nl_checks = {}
    rt_checks = {}

    # DB must exist (except quickstart phase)
    if not Path(args.db).exists():
        if args.phase == "quickstart":
            print(f"[INFO] DB not found yet (OK for quickstart check)")
        else:
            print(f"[ERROR] DB not found: {Path(args.db).resolve()}")
            print("  Run: python -m src.cli.main create-tables")
            sys.exit(2)

    if Path(args.db).exists():
        con = sqlite3.connect(args.db)
    else:
        con = None

    try:
        # === PRE PHASE: before races ===
        if args.phase == "pre":
            check_schema(con, issues)
            check_master_data(con, issues)
            nl_checks = check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (pre-race)")

            if nl_checks.get("NL_RA  (race header)") == 0:
                if args.fetch:
                    print(f"\n[AUTO-FETCH] Fetching today's RACE entries (option=2)...")
                    ok = run_fetch("RACE", race_date, race_date, 2, args.db)
                    if ok:
                        issues = [i for i in issues if "NL_RA" not in i]
                        nl_checks = check_nl_today(con, year, monthday, [], "NL_ 蓄積系 (after fetch)")

            run_unit_tests(issues)
            test_quickstart(args.db, issues)

        # === RT-CHECK PHASE: after each race (速報確認) ===
        elif args.phase == "rt-check":
            rt_checks = check_rt_today(con, year, monthday, issues, "RT_ 速報系")
            nl_checks = check_nl_today(con, year, monthday, [], "NL_ 蓄積系")
            check_nl_rt_consistency(con, year, monthday, issues)

            # RT_RA が0なら監視が動いていない可能性
            if rt_checks.get("RT_RA  (race 速報)") == 0:
                print("\n  [WARNING] RT_RA=0: realtime monitoring may not be running.")
                print("  Start with: python -m src.cli.main realtime start --specs 0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36")
                issues.append("RT_RA=0: check if realtime monitoring is running")

        # === NL-MID PHASE: mid-race NL_ refresh ===
        elif args.phase == "nl-mid":
            check_schema(con, issues)
            nl_checks = check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (mid-race)")
            rt_checks = check_rt_today(con, year, monthday, issues, "RT_ 速報系 (mid-race)")
            check_nl_rt_consistency(con, year, monthday, issues)

            if args.fetch and nl_checks.get("NL_RA  (race header)") == 0:
                print(f"\n[AUTO-FETCH] Fetching RACE data (option=1)...")
                ok = run_fetch("RACE", race_date, race_date, 1, args.db)
                if ok:
                    nl_checks = check_nl_today(con, year, monthday, [], "NL_ 蓄積系 (after fetch)")

        # === POST PHASE: all races done, fetch payouts ===
        elif args.phase == "post":
            check_schema(con, issues)
            nl_checks = check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (post-race)")
            rt_checks = check_rt_today(con, year, monthday, issues, "RT_ 速報系 (post-race)")
            check_nl_rt_consistency(con, year, monthday, issues)
            check_master_data(con, issues)

            # Fetch payouts if missing
            if args.fetch:
                if (nl_checks.get("NL_H1  (payouts)    ") or 0) == 0:
                    print(f"\n[AUTO-FETCH] Fetching DIFFU (payouts/results)...")
                    run_fetch("DIFFU", race_date, race_date, 1, args.db)
                if (nl_checks.get("NL_RA  (race header)") or 0) == 0:
                    print(f"\n[AUTO-FETCH] Fetching RACE data...")
                    run_fetch("RACE", race_date, race_date, 1, args.db)
                nl_checks = check_nl_today(con, year, monthday, [], "NL_ after fetch")

        # === FINAL PHASE: complete verification + unit tests ===
        elif args.phase == "final":
            check_schema(con, issues)
            nl_checks = check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (final)")
            rt_checks = check_rt_today(con, year, monthday, issues, "RT_ 速報系 (final)")
            check_nl_rt_consistency(con, year, monthday, issues)
            check_master_data(con, issues)

            # Hard requirements for final
            if (nl_checks.get("NL_RA  (race header)") or 0) == 0:
                issues.append("FINAL: NL_RA has no data for today")
            if (nl_checks.get("NL_H1  (payouts)    ") or 0) == 0:
                issues.append("FINAL: NL_H1 (payouts) empty - DIFFU fetch needed")
            if (rt_checks.get("RT_H1  (払戻 速報)  ") or 0) == 0:
                issues.append("FINAL: RT_H1 empty - realtime payout data missing")

            run_unit_tests(issues)
            test_quickstart(args.db, issues)

        # === QUICKSTART PHASE: test quickstart.bat ===
        elif args.phase == "quickstart":
            if con:
                check_schema(con, issues)
                check_master_data(con, issues)
            test_quickstart(args.db, issues)
            run_unit_tests(issues)

    finally:
        if con:
            con.close()

    # --- Save report ---
    report_dir = Path("data")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"raceday_report_{race_date}_{args.phase}.json"
    write_report(args.phase, race_date, nl_checks, rt_checks, issues, str(report_path))

    # --- Summary ---
    print(f"\n{'='*65}")
    if issues:
        print(f"[ISSUES: {len(issues)}]")
        for i, iss in enumerate(issues, 1):
            print(f"  {i:2}. {iss}")
        sys.exit(1)
    else:
        print("[ALL CHECKS PASSED]")
        sys.exit(0)


if __name__ == "__main__":
    main()
