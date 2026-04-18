#!/usr/bin/env python
"""Comprehensive race day verification script.

Verifies both 蓄積系 (NL_) and 速報系 (RT_) data for today's JRA races.
Designed to be called via Claude Code /loop every 30 min:
    /loop 30m python scripts/raceday_verify.py --phase auto

JRA Saturday schedule (approx):
  10:05  1R start  (中山/阪神/小倉/中京 etc)
  11:45  4R start
  13:40  7R start
  15:25 10R start
  16:00 11R 重賞
  16:30 12R last race
  16:45+ last race finishes
  17:30+ NL_ payout records available (DIFFU)

Phase auto-detection (--phase auto):
  < 10:05  → pre        (before 1R: schema/master/entry check)
  10:05-14:00 → rt-check (1R~6R: RT_ realtime data verification)
  14:00-17:00 → nl-mid   (7R~12R: mid/late race NL_+RT_ checks)
  17:00-18:00 → post     (all races done: payout wait)
  18:00-20:00 → final    (payouts available: full consistency)
  20:00+       → quickstart (end-of-day: quickstart.bat test)

Usage:
    python scripts/raceday_verify.py --phase auto       # 現在時刻から自動判定 (/loop向け)
    python scripts/raceday_verify.py --phase pre        # 事前確認
    python scripts/raceday_verify.py --phase rt-check   # 速報確認 (レース後)
    python scripts/raceday_verify.py --phase nl-mid     # 蓄積系中間確認
    python scripts/raceday_verify.py --phase post       # 全レース終了後
    python scripts/raceday_verify.py --phase final      # 最終検証 (払戻込み)
    python scripts/raceday_verify.py --phase quickstart # quickstart.bat検証
    python scripts/raceday_verify.py --phase all        # 全phaseまとめて実行

Exits with code 0 if checks pass, 1 if issues found, 2 if fatal error.
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

# Windows CP932 console can't encode em dash and other Unicode chars
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "cp936", "cp950"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DB_PATH_DEFAULT = "data/keiba.db"

# ---------------------------------------------------------------------------
# Auto phase detection (/loop support)
# ---------------------------------------------------------------------------

# JRA Saturday time boundary → phase (upper bound exclusive)
_PHASE_SCHEDULE = [
    (10 * 60 + 5,   "pre"),        # < 10:05 before 1R
    (14 * 60,       "rt-check"),   # 10:05-14:00  1R~6R running
    (17 * 60,       "nl-mid"),     # 14:00-17:00  7R~12R + cooling down
    (18 * 60,       "post"),       # 17:00-18:00  races done, payouts pending
    (20 * 60,       "final"),      # 18:00-20:00  payouts available (DIFFU)
    (24 * 60,       "quickstart"), # 20:00+       end of day
]


def auto_detect_phase() -> str:
    """Detect appropriate verification phase based on current time (JRA Saturday)."""
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


def table_exists(con, name):
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def index_exists(con, name):
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
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
    """Verify all expected NL_ and RT_ tables exist (38 record types)."""
    print("--- [1] Schema Check ---")
    nl_required = [
        "NL_RA", "NL_SE", "NL_HR", "NL_H1", "NL_H6",
        "NL_O1", "NL_O2", "NL_O3", "NL_O4", "NL_O5", "NL_O6",
        "NL_WE", "NL_WH", "NL_TK",
        "NL_UM", "NL_KS", "NL_CH", "NL_BR", "NL_BN", "NL_RC",
        "NL_JC", "NL_TC",
    ]
    rt_required = [
        "RT_RA", "RT_SE", "RT_HR", "RT_H1", "RT_H6",
        "RT_O1", "RT_O2", "RT_O3", "RT_O4", "RT_O5", "RT_O6",
        "RT_WH", "RT_CC", "RT_JC",
    ]
    ts_required = [
        "TS_O1", "TS_O2", "TS_O3", "TS_O4", "TS_O5", "TS_O6",
    ]

    missing_nl = [t for t in nl_required if not table_exists(con, t)]
    missing_rt = [t for t in rt_required if not table_exists(con, t)]

    if missing_nl:
        print(f"  [MISS] NL_ missing: {missing_nl}")
        issues.append(f"Missing NL_ tables: {missing_nl}")
    else:
        print(f"  [OK]  NL_ tables: {len(nl_required)} all present")

    if missing_rt:
        print(f"  [MISS] RT_ missing: {missing_rt}")
        issues.append(f"Missing RT_ tables: {missing_rt}")
    else:
        print(f"  [OK]  RT_ tables: {len(rt_required)} all present")

    missing_ts = [t for t in ts_required if not table_exists(con, t)]
    if missing_ts:
        print(f"  [MISS] TS_ missing: {missing_ts}")
        issues.append(f"Missing TS_ tables: {missing_ts}")
    else:
        print(f"  [OK]  TS_ tables: {len(ts_required)} all present")


def check_db_integrity(con, issues):
    """SQLite integrity_check and quick_check."""
    print("\n--- [2] DB Integrity ---")
    try:
        result = con.execute("PRAGMA integrity_check").fetchone()
        if result and result[0] == "ok":
            print("  [OK]  PRAGMA integrity_check: ok")
        else:
            msg = result[0] if result else "unknown"
            print(f"  [FAIL] integrity_check: {msg}")
            issues.append(f"DB integrity_check failed: {msg}")

        # Check page count / free pages
        page_count = con.execute("PRAGMA page_count").fetchone()[0]
        page_size  = con.execute("PRAGMA page_size").fetchone()[0]
        free_pages = con.execute("PRAGMA freelist_count").fetchone()[0]
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        print(f"  [OK]  DB size: {db_size_mb:.1f} MB  (free pages: {free_pages})")
    except Exception as e:
        print(f"  [WARN] integrity_check error: {e}")


def check_index_health(con, issues):
    """Verify key indexes exist for query performance."""
    print("\n--- [3] Index Health ---")
    key_indexes = [
        "idx_nl_ra_date",
        "idx_nl_se_date",
        "idx_rt_ra_date",
        "idx_rt_se_date",
    ]
    rows = q_rows(con, "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
    existing = {r[0] for r in rows} if rows else set()

    missing = [idx for idx in key_indexes if idx not in existing]
    if missing:
        print(f"  [WARN] Missing indexes: {missing}")
        # Not a hard issue - just a warning
    else:
        print(f"  [OK]  Key indexes present")

    total_indexes = len(existing)
    print(f"  [INFO] Total indexes: {total_indexes}")


def check_nl_today(con, year, monthday, issues, label="NL_ 蓄積系"):
    """Check NL_ tables for today's race data."""
    print(f"\n--- [4] {label} ---")
    y, m = year, monthday

    checks = {
        "NL_RA  (race header) ": q(con, "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_SE  (starters)    ": q(con, "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_SE  (確定着順)    ": q(con, "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=? AND KakuteiJyuni='01'", (y, m)),
        "NL_H1  (payouts)     ": q(con, "SELECT COUNT(*) FROM NL_H1 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_H6  (3連単)       ": q(con, "SELECT COUNT(*) FROM NL_H6 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O1  (単勝odds)    ": q(con, "SELECT COUNT(*) FROM NL_O1 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O2  (複勝odds)    ": q(con, "SELECT COUNT(*) FROM NL_O2 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O3  (枠連odds)    ": q(con, "SELECT COUNT(*) FROM NL_O3 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O4  (馬連odds)    ": q(con, "SELECT COUNT(*) FROM NL_O4 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O5  (3連複odds)   ": q(con, "SELECT COUNT(*) FROM NL_O5 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_O6  (3連単odds)   ": q(con, "SELECT COUNT(*) FROM NL_O6 WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_WH  (track cond)  ": q(con, "SELECT COUNT(*) FROM NL_WH WHERE Year=? AND MonthDay=?", (y, m)),
        "NL_TK  (track info)  ": q(con, "SELECT COUNT(*) FROM NL_TK WHERE Year=? AND MonthDay=?", (y, m)),
    }

    for name, count in checks.items():
        if count is None:
            print(f"  [--]  {name}  TABLE MISSING")
        else:
            marker = "  [OK]" if count > 0 else "  [!] "
            print(f"{marker} {name}  {count:>6}")

    ra_count = checks.get("NL_RA  (race header) ")
    if ra_count is not None and ra_count == 0:
        issues.append("NL_RA: no race headers for today")

    # Venue/race count breakdown
    rows = q_rows(con, "SELECT JyoCD, COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=? GROUP BY JyoCD ORDER BY JyoCD", (y, m))
    if rows:
        venue_str = "  ".join(f"場{r[0]}:{r[1]}R" for r in rows)
        print(f"  [INFO] NL_RA 競馬場別: {venue_str}")

    return checks


def check_rt_today(con, year, monthday, issues, label="RT_ 速報系"):
    """Check RT_ tables for today's realtime data."""
    print(f"\n--- [5] {label} ---")
    y, m = year, monthday

    checks = {
        "RT_RA  (race 速報)   ": q(con, "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_SE  (着順 速報)   ": q(con, "SELECT COUNT(*) FROM RT_SE WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_H1  (払戻 速報)   ": q(con, "SELECT COUNT(*) FROM RT_H1 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_H6  (3連単速報)   ": q(con, "SELECT COUNT(*) FROM RT_H6 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O1  (単勝 速報)   ": q(con, "SELECT COUNT(*) FROM RT_O1 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O2  (複勝 速報)   ": q(con, "SELECT COUNT(*) FROM RT_O2 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O3  (枠連 速報)   ": q(con, "SELECT COUNT(*) FROM RT_O3 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O4  (馬連 速報)   ": q(con, "SELECT COUNT(*) FROM RT_O4 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O5  (3連複速報)   ": q(con, "SELECT COUNT(*) FROM RT_O5 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_O6  (3連単速報)   ": q(con, "SELECT COUNT(*) FROM RT_O6 WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_WH  (馬場 速報)   ": q(con, "SELECT COUNT(*) FROM RT_WH WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_CC  (取消 速報)   ": q(con, "SELECT COUNT(*) FROM RT_CC WHERE Year=? AND MonthDay=?", (y, m)),
        "RT_JC  (重勝 速報)   ": q(con, "SELECT COUNT(*) FROM RT_JC WHERE Year=? AND MonthDay=?", (y, m)),
    }

    for name, count in checks.items():
        if count is None:
            print(f"  [--]  {name}  TABLE MISSING")
        else:
            marker = "  [OK]" if count > 0 else "  [!] "
            print(f"{marker} {name}  {count:>6}")

    return checks


def check_rt_process_running(issues):
    """Check if the realtime monitoring process is active (lock file present)."""
    print("\n--- [6] Realtime Process Status ---")
    lock_file = Path(".locks/realtime_updater.lock")
    if lock_file.exists():
        try:
            pid = int(lock_file.read_text().strip())
            # Check if PID is alive
            if sys.platform == "win32":
                r = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True, text=True, timeout=5
                )
                alive = str(pid) in r.stdout
            else:
                try:
                    os.kill(pid, 0)
                    alive = True
                except OSError:
                    alive = False

            if alive:
                print(f"  [OK]  Realtime monitor running (PID {pid})")
            else:
                print(f"  [!]   Lock file exists but PID {pid} not running")
                issues.append(f"Realtime monitor lock stale (PID {pid} not found)")
        except (ValueError, IOError):
            print(f"  [!]   Lock file unreadable: {lock_file}")
            issues.append("Realtime monitor lock file unreadable")
    else:
        print(f"  [!]   No lock file: {lock_file}")
        print(f"        Start: python -m src.cli.main realtime start --specs 0B12,0B15,0B30-0B36")
        issues.append("Realtime monitor not running (no lock file)")


def check_rt_data_freshness(con, year, monthday, issues, stale_minutes=15):
    """Check how recently RT_ records were written (data freshness)."""
    print(f"\n--- [7] RT_ Data Freshness (stale if >{stale_minutes} min) ---")
    y, m = year, monthday

    # Use DB file mtime as proxy if no timestamp column
    db_path = None
    try:
        db_path = Path(con.execute("PRAGMA database_list").fetchone()[2])
    except Exception:
        pass

    # Check RT_RA row count progression (compare with report files)
    rt_ra_now = q(con, "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_se_now = q(con, "SELECT COUNT(*) FROM RT_SE WHERE Year=? AND MonthDay=?", (y, m)) or 0

    if db_path and db_path.exists():
        mtime = db_path.stat().st_mtime
        age_min = (time.time() - mtime) / 60
        marker = "[OK] " if age_min < stale_minutes else "[!]  "
        print(f"  {marker} DB last modified: {age_min:.1f} min ago")
        if age_min >= stale_minutes and rt_ra_now == 0:
            issues.append(f"DB not updated in {age_min:.0f} min and RT_RA=0 -- realtime may be stalled")
    else:
        print(f"  [INFO] Cannot check DB mtime")

    print(f"  [INFO] RT_RA today: {rt_ra_now}  RT_SE today: {rt_se_now}")

    # Check TS_O1 freshness — the best live signal (updates every ~60s during races)
    latest_ts = q(con, "SELECT MAX(HassoTime) FROM TS_O1 WHERE Year=? AND MonthDay=?", (y, m))
    ts_snaps  = q(con, "SELECT COUNT(DISTINCT HassoTime) FROM TS_O1 WHERE Year=? AND MonthDay=?", (y, m)) or 0
    if latest_ts:
        # HassoTime format MMDDHHMM: extract HH:MM for display
        h_str = str(latest_ts)
        hhmm = f"{h_str[4:6]}:{h_str[6:8]}" if len(h_str) >= 8 else h_str
        print(f"  [OK]  TS_O1 latest snapshot: {hhmm}  ({ts_snaps} snapshots today)")
    else:
        now_h = datetime.now().hour
        if now_h >= 10:
            print(f"  [!]   TS_O1 no snapshots yet after 10:00 (realtime odds not flowing)")

    # RT_RA count progression — only flag if actually 0 or dropped
    nl_ra_count = q(con, "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    if rt_ra_now == 0:
        print(f"  [!]   RT_RA still 0 -- no realtime data received yet")
    elif rt_ra_now >= nl_ra_count and nl_ra_count > 0:
        print(f"  [OK]  RT_RA={rt_ra_now} matches NL_RA={nl_ra_count} (all races loaded)")
    else:
        print(f"  [INFO] RT_RA={rt_ra_now} / NL_RA={nl_ra_count}")


def _find_latest_report(race_date):
    """Load the most recent raceday report JSON for comparison."""
    report_dir = Path("data")
    if not report_dir.exists():
        return None
    patterns = sorted(report_dir.glob(f"raceday_report_{race_date}_*.json"), reverse=True)
    if not patterns:
        return None
    try:
        return json.loads(patterns[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def check_race_count_by_venue(con, year, monthday, issues):
    """Verify each venue has a plausible number of races (typically 12R)."""
    print("\n--- [8] Race Count by Venue ---")
    y, m = year, monthday

    rows = q_rows(
        con,
        "SELECT JyoCD, COUNT(DISTINCT RaceNum) FROM NL_RA WHERE Year=? AND MonthDay=? GROUP BY JyoCD ORDER BY JyoCD",
        (y, m)
    )
    rt_rows = q_rows(
        con,
        "SELECT JyoCD, COUNT(DISTINCT RaceNum) FROM RT_RA WHERE Year=? AND MonthDay=? GROUP BY JyoCD ORDER BY JyoCD",
        (y, m)
    )

    if not rows and not rt_rows:
        print(f"  [!]   No race data for today in NL_RA or RT_RA")
        return

    venue_map = {}
    if rows:
        for jyo, cnt in rows:
            venue_map[jyo] = {"nl": cnt, "rt": 0}
    if rt_rows:
        for jyo, cnt in rt_rows:
            if jyo not in venue_map:
                venue_map[jyo] = {"nl": 0, "rt": 0}
            venue_map[jyo]["rt"] = cnt

    for jyo, counts in sorted(venue_map.items()):
        nl_c, rt_c = counts["nl"], counts["rt"]
        max_r = max(nl_c, rt_c)
        marker = "[OK] " if max_r >= 8 else "[!]  "  # at least 8R expected
        print(f"  {marker} 場{jyo}:  NL_={nl_c:2}R  RT_={rt_c:2}R")
        if max_r > 0 and max_r < 8:
            issues.append(f"場{jyo}: only {max_r}R recorded (expected ~12R)")


def check_odds_coverage(con, year, monthday, issues):
    """Check that all 6 odds types have data for active races.

    Note: real-time odds (0B30-0B36) go to TS_O* tables (timeseries snapshots),
    NOT RT_O* tables. RT_O* being empty is correct during live monitoring.
    Use check_ts_odds() to verify timeseries odds capture.
    """
    print("\n--- [9] Odds Coverage (NL_ final + RT_ speed-report) ---")
    y, m = year, monthday

    nl_tables = [
        ("NL_O1", "単勝"), ("NL_O2", "複勝"), ("NL_O3", "枠連"),
        ("NL_O4", "馬連"), ("NL_O5", "3連複"), ("NL_O6", "3連単"),
    ]
    for tbl, name in nl_tables:
        cnt = q(con, f"SELECT COUNT(*) FROM {tbl} WHERE Year=? AND MonthDay=?", (y, m))
        if cnt is None:
            print(f"  [--]  {tbl:8} ({name:5}) TABLE MISSING")
        elif cnt == 0:
            print(f"  [!]   {tbl:8} ({name:5})       0")
        else:
            print(f"  [OK]  {tbl:8} ({name:5})  {cnt:>6}")

    # RT_O* are intentionally empty — realtime odds route to TS_O* (timeseries)
    rt_o_total = sum(
        q(con, f"SELECT COUNT(*) FROM RT_O{i} WHERE Year=? AND MonthDay=?", (y, m)) or 0
        for i in range(1, 7)
    )
    print(f"  [INFO] RT_O1-O6 total: {rt_o_total} (expected 0 -- odds go to TS_O* timeseries)")


def check_ts_odds(con, year, monthday, issues):
    """Check TS_O* timeseries odds tables — HassoTime-keyed snapshots for ML.

    Real-time odds (0B30-0B36) are stored here with HassoTime as part of the
    primary key, preserving every broadcast snapshot (typically every 1-15 min).
    This is the primary source for ML odds-movement features.
    """
    print("\n--- [9b] TS_O* Timeseries Odds (ML用スナップショット) ---")
    y, m = year, monthday

    ts_tables = [
        ("TS_O1", "単複枠"),
        ("TS_O2", "馬連"),
        ("TS_O3", "ワイド"),
        ("TS_O4", "馬単"),
        ("TS_O5", "3連複"),
        ("TS_O6", "3連単"),
    ]

    any_data = False
    latest_hasso = None
    for tbl, name in ts_tables:
        cnt = q(con, f"SELECT COUNT(*) FROM {tbl} WHERE Year=? AND MonthDay=?", (y, m))
        if cnt is None:
            print(f"  [--]  {tbl} ({name}) TABLE MISSING")
            issues.append(f"TS_O* table missing: {tbl}")
            continue
        snaps = q(con,
            f"SELECT COUNT(DISTINCT HassoTime) FROM {tbl} WHERE Year=? AND MonthDay=?",
            (y, m)) or 0
        marker = "[OK] " if cnt > 0 else "[!]  "
        print(f"  {marker} {tbl} ({name:5})  rows={cnt:>6}  snapshots={snaps}")
        if cnt > 0:
            any_data = True
            h = q(con, f"SELECT MAX(HassoTime) FROM {tbl} WHERE Year=? AND MonthDay=?", (y, m))
            if h and (latest_hasso is None or str(h) > str(latest_hasso)):
                latest_hasso = h

    if latest_hasso:
        print(f"  [INFO] Most recent HassoTime: {latest_hasso}")

    if not any_data:
        now_h = datetime.now().hour
        if now_h >= 10:
            print("  [!]   TS_O* empty after 10:00 -- realtime monitor may not be running with 0B30-0B36")
            issues.append("TS_O* timeseries odds empty after 10:00 -- check realtime monitor specs")
        else:
            print("  [INFO] TS_O* empty (pre-race -- normal before 10:05)")


def check_se_results(con, year, monthday, issues):
    """Check race result completion — confirmed finishers (KakuteiJyuni='01' = winner)."""
    print("\n--- [10] Race Result Completion ---")
    y, m = year, monthday

    nl_ra_count = q(con, "SELECT COUNT(DISTINCT RaceNum||JyoCD) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    nl_winner   = q(con, "SELECT COUNT(*) FROM NL_SE WHERE Year=? AND MonthDay=? AND KakuteiJyuni='01'", (y, m)) or 0
    rt_winner   = q(con, "SELECT COUNT(*) FROM RT_SE WHERE Year=? AND MonthDay=? AND KakuteiJyuni='01'", (y, m)) or 0

    print(f"  [INFO] NL_RA distinct races today: {nl_ra_count}")
    print(f"  [INFO] NL_SE confirmed winners:    {nl_winner}")
    print(f"  [INFO] RT_SE confirmed winners:    {rt_winner}")

    if nl_ra_count > 0:
        # During live racing NL_SE winners stay 0 until DIFFU fetch (~17:30).
        # Use RT_SE as the authoritative source while racing is ongoing.
        effective_winner = rt_winner if rt_winner > nl_winner else nl_winner
        source = "RT_SE" if rt_winner > nl_winner else "NL_SE"
        completion = effective_winner / nl_ra_count * 100
        marker = "[OK] " if completion >= 80 else "[!]  "
        print(f"  {marker} Result completion: {effective_winner}/{nl_ra_count} races ({completion:.0f}%)  [{source}]")
        if completion < 50 and datetime.now().hour >= 17:
            issues.append(f"Race results only {completion:.0f}% complete after 17:00 -- fetch DIFFU")


def check_payout_completeness(con, year, monthday, issues):
    """Verify H1 (payout) record count matches RA race count."""
    print("\n--- [11] Payout Completeness ---")
    y, m = year, monthday

    ra_count = q(con, "SELECT COUNT(DISTINCT RaceNum||JyoCD) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    nl_h1    = q(con, "SELECT COUNT(*) FROM NL_H1 WHERE Year=? AND MonthDay=?", (y, m)) or 0
    nl_h6    = q(con, "SELECT COUNT(*) FROM NL_H6 WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_h1    = q(con, "SELECT COUNT(*) FROM RT_H1 WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_h6    = q(con, "SELECT COUNT(*) FROM RT_H6 WHERE Year=? AND MonthDay=?", (y, m)) or 0

    print(f"  [INFO] NL_RA races: {ra_count}   NL_H1: {nl_h1}   NL_H6: {nl_h6}")
    print(f"  [INFO] RT_H1: {rt_h1}   RT_H6: {rt_h6}")

    # After all races: H1 should roughly equal RA count
    now_h = datetime.now().hour
    if now_h >= 17 and ra_count > 0:
        if nl_h1 == 0 and rt_h1 == 0:
            issues.append("No payout data (H1) after 17:00 -- run fetch DIFFU or check realtime")
        elif nl_h1 < ra_count * 0.8:
            marker = "[!]  "
            print(f"  {marker} NL_H1 ({nl_h1}) << NL_RA ({ra_count}) -- payouts incomplete")
            issues.append(f"NL_H1 ({nl_h1}) incomplete vs NL_RA ({ra_count})")
        else:
            print(f"  [OK]  Payout data looks complete")


def check_duplicate_race_ids(con, year, monthday, issues):
    """Check for duplicate primary keys in NL_RA and RT_RA."""
    print("\n--- [12] Duplicate Race ID Check ---")
    y, m = year, monthday

    for tbl in ["NL_RA", "RT_RA"]:
        if not table_exists(con, tbl):
            print(f"  [--]  {tbl} TABLE MISSING")
            continue
        # Detect duplicate (Year, MonthDay, JyoCD, RaceNum)
        dupes = q(
            con,
            f"SELECT COUNT(*) FROM (SELECT Year,MonthDay,JyoCD,RaceNum FROM {tbl} "
            f"WHERE Year=? AND MonthDay=? GROUP BY Year,MonthDay,JyoCD,RaceNum HAVING COUNT(*)>1)",
            (y, m)
        ) or 0
        if dupes > 0:
            print(f"  [!]   {tbl}: {dupes} duplicate race keys found")
            issues.append(f"{tbl} has {dupes} duplicate race keys for today")
        else:
            print(f"  [OK]  {tbl}: no duplicate race IDs")


def check_nl_rt_consistency(con, year, monthday, issues):
    """Compare NL_ vs RT_ counts to detect sync issues."""
    print("\n--- [13] NL_ vs RT_ Consistency ---")
    y, m = year, monthday

    pairs = [
        ("NL_RA", "RT_RA", "race headers"),
        ("NL_SE", "RT_SE", "race entries"),
        ("NL_H1", "RT_H1", "payouts"),
    ]
    for nl_tbl, rt_tbl, label in pairs:
        nl_c = q(con, f"SELECT COUNT(*) FROM {nl_tbl} WHERE Year=? AND MonthDay=?", (y, m)) or 0
        rt_c = q(con, f"SELECT COUNT(*) FROM {rt_tbl} WHERE Year=? AND MonthDay=?", (y, m)) or 0
        total = nl_c + rt_c
        marker = "[OK] " if total > 0 else "[!]  "
        print(f"  {marker} {label:15}  NL_={nl_c:5}  RT_={rt_c:5}")

    # Warn if RT_ has data but NL_ is significantly behind
    nl_ra = q(con, "SELECT COUNT(*) FROM NL_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    rt_ra = q(con, "SELECT COUNT(*) FROM RT_RA WHERE Year=? AND MonthDay=?", (y, m)) or 0
    if nl_ra > 0 and rt_ra == 0:
        issues.append("RT_RA=0 but NL_RA has data -- realtime monitoring may not be running")
    if nl_ra == 0 and rt_ra == 0:
        issues.append("Both NL_RA and RT_RA=0 -- no race data at all")


def check_master_data(con, issues):
    """Check horse/jockey/trainer master tables."""
    print("\n--- [14] Master Data ---")
    um = q(con, "SELECT COUNT(*) FROM NL_UM") or 0
    ks = q(con, "SELECT COUNT(*) FROM NL_KS") or 0
    ch = q(con, "SELECT COUNT(*) FROM NL_CH") or 0 if table_exists(con, "NL_CH") else None
    print(f"  {'[OK] ' if um > 0 else '[!]  '} NL_UM  (horses)    {um:>8,}")
    print(f"  {'[OK] ' if ks > 0 else '[!]  '} NL_KS  (jockeys)   {ks:>8,}")
    if ch is not None:
        print(f"  {'[OK] ' if ch > 0 else '[!]  '} NL_CH  (trainers)  {ch:>8,}")
    if um == 0:
        issues.append("NL_UM (horse master) empty -- run setup fetch")
    if ks == 0:
        issues.append("NL_KS (jockey master) empty -- run setup fetch")


def check_cache_status(issues):
    """Check local NL_ / RT_ cache coverage."""
    print("\n--- [15] Local Cache Status ---")
    cache_dir = Path("data/cache")
    if not cache_dir.exists():
        print(f"  [!]   Cache directory not found: {cache_dir}")
        issues.append("Cache directory missing -- cache not initialized")
        return

    today_str = date.today().strftime("%Y%m%d")
    nl_dir = cache_dir / "nl"
    rt_dir = cache_dir / "rt"

    for kind, base_dir in [("NL_", nl_dir), ("RT_", rt_dir)]:
        if not base_dir.exists():
            print(f"  [!]   {kind} cache dir missing: {base_dir}")
            continue
        specs = [d.name for d in base_dir.iterdir() if d.is_dir()]
        if not specs:
            print(f"  [!]   {kind} cache: no spec dirs found")
            continue
        total_files = sum(len(list(d.glob("*.bin"))) for d in base_dir.iterdir() if d.is_dir())
        today_files = sum(len(list(d.glob(f"{today_str}.bin"))) for d in base_dir.iterdir() if d.is_dir())
        print(f"  [OK]  {kind} cache: {len(specs)} specs, {total_files} total bin files, {today_files} today")


def run_unit_tests(issues):
    """Run unit test suite (exclude integration/e2e)."""
    print("\n--- [16] Unit Tests ---")
    cmd = [sys.executable, "-m", "pytest", "tests/",
           "-q", "--tb=line",
           "--ignore=tests/unit/test_jvlink_bridge.py",
           "--ignore=tests/integration/",
           "--ignore=tests/e2e/",
           "--basetemp=C:/tmp/pytest-jrvl",
           "--no-header"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    lines = (r.stdout + r.stderr).strip().splitlines()
    for line in lines[-10:]:
        print(f"  {line}")
    if r.returncode != 0:
        issues.append(f"Unit tests failed (exit {r.returncode})")
        return False
    return True


def test_quickstart(db, issues):
    """Verify quickstart.bat and quickstart.py are healthy."""
    print("\n--- [17] quickstart.bat Smoke Test ---")
    qs  = Path("scripts/quickstart.py")
    bat = Path("scripts/quickstart.bat")

    for path in [qs, bat]:
        if not path.exists():
            print(f"  [MISS] {path} not found")
            issues.append(f"{path} missing")
            return

    # Python syntax check
    r = subprocess.run([sys.executable, "-m", "py_compile", str(qs)],
                       capture_output=True, timeout=10)
    if r.returncode == 0:
        print(f"  [OK]  quickstart.py syntax OK")
    else:
        print(f"  [FAIL] quickstart.py syntax error")
        issues.append("quickstart.py has syntax errors")
        return

    # JRA-only check (no NAR references)
    bat_text = bat.read_text(encoding="utf-8", errors="replace")
    if "NAR" in bat_text or "nar_v5" in bat_text:
        issues.append("quickstart.bat still contains NAR references")
        print("  [FAIL] quickstart.bat contains NAR references")
    else:
        print(f"  [OK]  quickstart.bat is JRA-only")

    # Check --option bug is fixed (should use --mode now)
    if "--option" in bat_text:
        print("  [!]   quickstart.bat uses --option (deprecated, should use --mode)")
        issues.append("quickstart.bat uses deprecated --option argument")
    else:
        print("  [OK]  quickstart.bat uses --mode correctly")

    # DB accessible
    if Path(db).exists():
        print(f"  [OK]  DB: {Path(db).resolve()}")
    else:
        print(f"  [!]   DB not found: {db}")


def _collect_ts_counts(con, year, monthday):
    """Return TS_O* row/snapshot counts for the report JSON."""
    if con is None:
        return {}
    y, m = year, monthday
    out = {}
    for i, name in enumerate(["単複枠", "馬連", "ワイド", "馬単", "3連複", "3連単"], 1):
        tbl = f"TS_O{i}"
        cnt = q(con, f"SELECT COUNT(*) FROM {tbl} WHERE Year=? AND MonthDay=?", (y, m)) or 0
        snaps = q(con, f"SELECT COUNT(DISTINCT HassoTime) FROM {tbl} WHERE Year=? AND MonthDay=?", (y, m)) or 0
        out[f"{tbl} ({name})"] = {"rows": cnt, "snapshots": snaps}
    return out


def write_report(phase, race_date, nl_checks, rt_checks, issues, report_path, con=None):
    """Write JSON report for this checkpoint."""
    year, monthday = race_date[:4], race_date[4:6] + race_date[6:8]
    report = {
        "phase": phase,
        "race_date": race_date,
        "timestamp": datetime.now().isoformat(),
        "issues_count": len(issues),
        "issues": issues,
        "nl": {k.strip(): v for k, v in (nl_checks or {}).items()},
        "rt": {k.strip(): v for k, v in (rt_checks or {}).items()},
        "ts": _collect_ts_counts(con, year, monthday),
    }
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Report: {report_path}")


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

def run_phase_pre(con, args, year, monthday, issues, nl_checks, rt_checks):
    check_schema(con, issues)
    check_db_integrity(con, issues)
    check_index_health(con, issues)
    check_master_data(con, issues)
    nl_checks.update(check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (pre-race)") or {})
    check_duplicate_race_ids(con, year, monthday, issues)

    if nl_checks.get("NL_RA  (race header) ") == 0 and args.fetch:
        print(f"\n[AUTO-FETCH] Fetching today's RACE entries (option=2)...")
        if run_fetch("RACE", args.date or date.today().strftime("%Y%m%d"),
                     args.date or date.today().strftime("%Y%m%d"), 2, args.db):
            nl_checks.update(check_nl_today(con, year, monthday, [], "NL_ after fetch") or {})

    run_unit_tests(issues)
    test_quickstart(args.db, issues)


def run_phase_rt_check(con, args, year, monthday, issues, nl_checks, rt_checks):
    rt_checks.update(check_rt_today(con, year, monthday, issues, "RT_ 速報系 (during races)") or {})
    nl_checks.update(check_nl_today(con, year, monthday, [], "NL_ 蓄積系") or {})
    check_rt_process_running(issues)
    check_rt_data_freshness(con, year, monthday, issues)
    check_odds_coverage(con, year, monthday, issues)
    check_ts_odds(con, year, monthday, issues)
    check_race_count_by_venue(con, year, monthday, issues)
    check_nl_rt_consistency(con, year, monthday, issues)
    check_duplicate_race_ids(con, year, monthday, issues)

    if rt_checks.get("RT_RA  (race 速報)   ") == 0:
        print("\n  [WARNING] RT_RA=0: realtime monitoring may not be running.")
        print("  Start: python -m src.cli.main realtime start --specs 0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36")
        issues.append("RT_RA=0: realtime monitoring likely not running")


def run_phase_nl_mid(con, args, year, monthday, issues, nl_checks, rt_checks):
    check_schema(con, issues)
    nl_checks.update(check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (mid-race)") or {})
    rt_checks.update(check_rt_today(con, year, monthday, issues, "RT_ 速報系 (mid-race)") or {})
    check_rt_process_running(issues)
    check_rt_data_freshness(con, year, monthday, issues)
    check_odds_coverage(con, year, monthday, issues)
    check_ts_odds(con, year, monthday, issues)
    check_race_count_by_venue(con, year, monthday, issues)
    check_se_results(con, year, monthday, issues)
    check_nl_rt_consistency(con, year, monthday, issues)

    if nl_checks.get("NL_RA  (race header) ") == 0 and args.fetch:
        print(f"\n[AUTO-FETCH] Fetching RACE data (option=1)...")
        if run_fetch("RACE", args.date or date.today().strftime("%Y%m%d"),
                     args.date or date.today().strftime("%Y%m%d"), 1, args.db):
            nl_checks.update(check_nl_today(con, year, monthday, [], "NL_ after fetch") or {})


def run_phase_post(con, args, year, monthday, issues, nl_checks, rt_checks):
    check_schema(con, issues)
    nl_checks.update(check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (post-race)") or {})
    rt_checks.update(check_rt_today(con, year, monthday, issues, "RT_ 速報系 (post-race)") or {})
    check_rt_data_freshness(con, year, monthday, issues, stale_minutes=60)
    check_race_count_by_venue(con, year, monthday, issues)
    check_se_results(con, year, monthday, issues)
    check_payout_completeness(con, year, monthday, issues)
    check_nl_rt_consistency(con, year, monthday, issues)
    check_master_data(con, issues)
    check_duplicate_race_ids(con, year, monthday, issues)

    race_date = args.date or date.today().strftime("%Y%m%d")
    if args.fetch:
        if (nl_checks.get("NL_H1  (payouts)     ") or 0) == 0:
            print(f"\n[AUTO-FETCH] Fetching DIFFU (payouts/results)...")
            run_fetch("DIFFU", race_date, race_date, 1, args.db)
        if (nl_checks.get("NL_RA  (race header) ") or 0) == 0:
            print(f"\n[AUTO-FETCH] Fetching RACE data...")
            run_fetch("RACE", race_date, race_date, 1, args.db)
        nl_checks.update(check_nl_today(con, year, monthday, [], "NL_ after fetch") or {})


def run_phase_final(con, args, year, monthday, issues, nl_checks, rt_checks):
    check_schema(con, issues)
    check_db_integrity(con, issues)
    nl_checks.update(check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (final)") or {})
    rt_checks.update(check_rt_today(con, year, monthday, issues, "RT_ 速報系 (final)") or {})
    check_odds_coverage(con, year, monthday, issues)
    check_ts_odds(con, year, monthday, issues)
    check_race_count_by_venue(con, year, monthday, issues)
    check_se_results(con, year, monthday, issues)
    check_payout_completeness(con, year, monthday, issues)
    check_nl_rt_consistency(con, year, monthday, issues)
    check_master_data(con, issues)
    check_duplicate_race_ids(con, year, monthday, issues)
    check_cache_status(issues)

    # Hard requirements for final phase
    if (nl_checks.get("NL_RA  (race header) ") or 0) == 0:
        issues.append("FINAL: NL_RA has no data for today")
    if (nl_checks.get("NL_H1  (payouts)     ") or 0) == 0:
        issues.append("FINAL: NL_H1 (payouts) empty -- run fetch DIFFU")
    if (rt_checks.get("RT_H1  (払戻 速報)   ") or 0) == 0:
        issues.append("FINAL: RT_H1 empty -- realtime payout data missing")

    run_unit_tests(issues)
    test_quickstart(args.db, issues)


def run_phase_quickstart(con, args, year, monthday, issues, nl_checks, rt_checks):
    if con:
        check_schema(con, issues)
        check_master_data(con, issues)
        check_nl_today(con, year, monthday, issues, "NL_ 蓄積系 (quickstart)")
        check_cache_status(issues)
    test_quickstart(args.db, issues)
    run_unit_tests(issues)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Race day comprehensive verification")
    parser.add_argument("--db", default=DB_PATH_DEFAULT)
    parser.add_argument("--date", default=None, help="YYYYMMDD (default: today)")
    parser.add_argument("--fetch", action="store_true", help="Auto-fetch missing NL_ data")
    parser.add_argument(
        "--phase", default="auto",
        choices=["pre", "rt-check", "nl-mid", "post", "final", "quickstart", "auto", "all"],
        help="Verification phase (auto=現在時刻から自動判定, all=全フェーズ)"
    )
    args = parser.parse_args()

    # Resolve auto phase
    if args.phase == "auto":
        args.phase = auto_detect_phase()
        print(f"[auto] Detected phase: {args.phase}  (current time: {datetime.now().strftime('%H:%M')})")

    phases_to_run = (
        ["pre", "rt-check", "nl-mid", "post", "final", "quickstart"]
        if args.phase == "all"
        else [args.phase]
    )

    race_date = args.date or date.today().strftime("%Y%m%d")
    if len(race_date) != 8 or not race_date.isdigit():
        print(f"[ERROR] --date must be YYYYMMDD, got: {race_date!r}")
        sys.exit(2)
    year      = race_date[:4]
    monthday  = race_date[4:6] + race_date[6:8]
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*65}")
    print(f"  Race Day Verification  [{now_str}]")
    print(f"  Phase: {args.phase:12s}  Date: {race_date}")
    print(f"  DB:    {Path(args.db).resolve()}")
    print(f"{'='*65}\n")

    # DB connection
    if not Path(args.db).exists():
        if args.phase not in ("quickstart", "all"):
            print(f"[ERROR] DB not found: {Path(args.db).resolve()}")
            print("  Run: python -m src.cli.main create-tables")
            sys.exit(2)
        print(f"[INFO] DB not found (OK for quickstart phase)")
    con = sqlite3.connect(args.db) if Path(args.db).exists() else None

    all_issues   = []
    nl_checks    = {}
    rt_checks    = {}

    phase_runners = {
        "pre":        run_phase_pre,
        "rt-check":   run_phase_rt_check,
        "nl-mid":     run_phase_nl_mid,
        "post":       run_phase_post,
        "final":      run_phase_final,
        "quickstart": run_phase_quickstart,
    }

    try:
        for phase in phases_to_run:
            if args.phase == "all":
                print(f"\n{'─'*65}")
                print(f"  === Running phase: {phase} ===")
                print(f"{'─'*65}")
            phase_issues = []
            phase_runners[phase](con, args, year, monthday, phase_issues, nl_checks, rt_checks)
            all_issues.extend(phase_issues)

        # Save report while con is still open (needed for TS_O* counts)
        report_dir = Path("data")
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f"raceday_report_{race_date}_{args.phase}.json"
        write_report(args.phase, race_date, nl_checks, rt_checks, all_issues, str(report_path), con=con)
    finally:
        if con:
            con.close()

    # Summary
    print(f"\n{'='*65}")
    if all_issues:
        print(f"[ISSUES: {len(all_issues)}]")
        for i, iss in enumerate(all_issues, 1):
            print(f"  {i:2}. {iss}")
        sys.exit(1)
    else:
        print("[ALL CHECKS PASSED]")
        sys.exit(0)


if __name__ == "__main__":
    main()
