#!/usr/bin/env python
"""Race day verification scheduler — per-race timing.

Runs raceday_verify.py at each JRA race checkpoint (approximately 15 min
after each race start, when results + RT_ data should have arrived).

JRA Saturday schedule (typical — 中山/阪神/小倉 etc):
  1R  10:05  → check at 10:20
  2R  10:40  → check at 10:55
  3R  11:15  → check at 11:30
  4R  11:45  → check at 12:05
  5R  12:20  → check at 12:35
  6R  12:55  → check at 13:15
  7R  13:40  → check at 13:55
  8R  14:15  → check at 14:35
  9R  14:50  → check at 15:10
 10R  15:25  → check at 15:45
 11R  16:00  → check at 16:20  (重賞多い)
 12R  16:35  → check at 16:55  (最終レース)
    ------
      17:30  → post-race NL_ update check
      18:30  → final check (払戻 DIFFU available)
      20:00  → quickstart smoke test

Usage:
    python scripts/raceday_scheduler.py                 # full day
    python scripts/raceday_scheduler.py --from 12:00    # skip morning
    python scripts/raceday_scheduler.py --dry-run       # print schedule only
    python scripts/raceday_scheduler.py --fetch         # auto-fetch missing data
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# (verify_time, phase, description)
# verify_time = ~15 min after race start, giving results time to arrive via RT_
RACE_CHECKPOINTS = [
    ("09:30", "pre",        "Pre-race: DB setup + schema + master data"),
    ("10:20", "rt-check",   "After 1R  (start ~10:05): first RT_ data"),
    ("10:55", "rt-check",   "After 2R  (start ~10:40)"),
    ("11:30", "rt-check",   "After 3R  (start ~11:15)"),
    ("12:05", "rt-check",   "After 4R  (start ~11:45)"),
    ("12:35", "rt-check",   "After 5R  (start ~12:20)"),
    ("13:15", "rt-check",   "After 6R  (start ~12:55)"),
    ("13:55", "nl-mid",     "After 7R  (start ~13:40): mid-race NL_ + RT_"),
    ("14:35", "nl-mid",     "After 8R  (start ~14:15)"),
    ("15:10", "nl-mid",     "After 9R  (start ~14:50)"),
    ("15:45", "nl-mid",     "After 10R (start ~15:25)"),
    ("16:20", "nl-mid",     "After 11R (start ~16:00): 重賞"),
    ("16:55", "post",       "After 12R (start ~16:35): 最終レース"),
    ("17:30", "post",       "Post-race: NL_ update + payout wait"),
    ("18:30", "final",      "Final: 払戻 (DIFFU) available"),
    ("20:00", "quickstart", "End-of-day: quickstart.bat smoke test"),
]


def hhmm_to_today(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)


def sleep_until(target_str: str) -> float:
    """Sleep until HH:MM. Returns seconds slept (0 if past)."""
    target = hhmm_to_today(target_str)
    diff = (target - datetime.now()).total_seconds()
    if diff <= 0:
        return 0.0

    mins = diff / 60
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Waiting until {target_str} ({mins:.0f} min)...",
        flush=True,
    )
    interval = 300  # heartbeat every 5 min
    slept = 0.0
    while slept < diff:
        chunk = min(interval, diff - slept)
        time.sleep(chunk)
        slept += chunk
        remaining = diff - slept
        if remaining > 60:
            print(
                f"  [{datetime.now().strftime('%H:%M')}] "
                f"{remaining / 60:.0f} min to {target_str}",
                flush=True,
            )
    return diff


def run_verify(phase: str, fetch: bool) -> int:
    """Run raceday_verify.py for the given phase."""
    sep = "=" * 65
    print(f"\n{sep}", flush=True)
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Verification — phase: {phase.upper()}",
        flush=True,
    )
    print(f"{sep}", flush=True)

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "raceday_verify.py"),
        "--phase", phase,
    ]
    if fetch:
        cmd.append("--fetch")

    print(f"$ {' '.join(cmd)}\n", flush=True)
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def print_schedule(from_hhmm: str | None, dry_run: bool):
    today = date.today()
    print(f"{'='*65}", flush=True)
    print(f"  Race Day Scheduler  —  {today} (JRA Saturday)", flush=True)
    if dry_run:
        print(f"  Mode : DRY RUN", flush=True)
    print(f"{'='*65}", flush=True)
    print(f"  {'TIME':6}  {'PHASE':12}  DESCRIPTION", flush=True)
    print(f"  {'-'*57}", flush=True)
    for t, phase, desc in RACE_CHECKPOINTS:
        skip = from_hhmm and t < from_hhmm
        flag = "SKIP " if skip else "     "
        print(f"  {t}  {flag}{phase:12}  {desc}", flush=True)
    print(flush=True)
    print(
        f"  Total checkpoints: {len(RACE_CHECKPOINTS)}"
        f" ({sum(1 for t,_,_ in RACE_CHECKPOINTS if not from_hhmm or t >= from_hhmm)} active)",
        flush=True,
    )
    print(flush=True)


def main():
    parser = argparse.ArgumentParser(description="Race day per-race verification scheduler")
    parser.add_argument("--from", dest="from_time", metavar="HH:MM", default=None,
                        help="Skip checkpoints before this time")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print schedule without running")
    parser.add_argument("--fetch", action="store_true",
                        help="Pass --fetch to raceday_verify.py (auto-fetch missing data)")
    args = parser.parse_args()

    print_schedule(args.from_time, args.dry_run)
    if args.dry_run:
        return

    ran = 0
    for target_time, phase, desc in RACE_CHECKPOINTS:
        if args.from_time and target_time < args.from_time:
            print(
                f"[{datetime.now().strftime('%H:%M')}] "
                f"Skip {phase} @ {target_time} (before --from {args.from_time})",
                flush=True,
            )
            continue

        # Already more than 10 min past? Skip.
        already_past = (datetime.now() - hhmm_to_today(target_time)).total_seconds()
        if already_past > 600:
            print(
                f"[{datetime.now().strftime('%H:%M')}] "
                f"Skip {phase} @ {target_time} ({already_past/60:.0f} min past)",
                flush=True,
            )
            continue

        sleep_until(target_time)

        rc = run_verify(phase, args.fetch)
        ran += 1

        status = {0: "PASSED", 1: "WARNING"}.get(rc, f"ERROR (exit {rc})")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {target_time} {phase} → {status}\n",
              flush=True)

    if ran == 0:
        print("No checkpoints remaining. Use --from HH:MM to start from a specific time.",
              flush=True)
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] All {ran} checkpoints complete.",
              flush=True)


if __name__ == "__main__":
    main()
