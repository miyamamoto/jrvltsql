#!/usr/bin/env python
"""Race day verification scheduler.

Sleeps until each checkpoint time and runs raceday_verify.py --phase <phase>.
Designed to run inside a tmux pane (window: verify).

JRA Saturday schedule:
  09:30  pre         -- pre-race DB/schema check
  12:00  rt-check    -- mid-race realtime data check (after 4R)
  14:00  nl-mid      -- NL_ data mid-day check
  17:00  post        -- all races done, NL_ payouts check
  18:30  final       -- full consistency + payout check
  20:00  quickstart  -- quickstart.bat smoke test

Usage:
    python scripts/raceday_scheduler.py
    python scripts/raceday_scheduler.py --from 12:00   # skip phases before 12:00
    python scripts/raceday_scheduler.py --dry-run      # print schedule, no sleep/run
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# (HH:MM, phase-name, description)
CHECKPOINTS = [
    ("09:30", "pre",        "Pre-race DB check"),
    ("12:00", "rt-check",   "Mid-race RT_ data check (after 4R ~11:45)"),
    ("14:00", "nl-mid",     "NL_ mid-day check (7R ~13:40)"),
    ("17:00", "post",       "Post-race check (all 12R done ~16:30)"),
    ("18:30", "final",      "Final check with payouts (NL_ 払戻 available)"),
    ("20:00", "quickstart", "quickstart.bat smoke test"),
]


def hhmm_to_today(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)


def sleep_until(target_time_str: str) -> float:
    """Sleep until HH:MM today. Returns seconds slept (0 if already past)."""
    target = hhmm_to_today(target_time_str)
    diff = (target - datetime.now()).total_seconds()
    if diff <= 0:
        return 0.0
    mins = diff / 60
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] "
        f"Sleeping until {target_time_str} ({mins:.0f} min)...",
        flush=True,
    )
    # Print a dot every 5 minutes to show we're alive
    interval = 300  # 5 min
    slept = 0.0
    while slept < diff:
        chunk = min(interval, diff - slept)
        time.sleep(chunk)
        slept += chunk
        remaining = diff - slept
        if remaining > 30:
            print(
                f"  [{datetime.now().strftime('%H:%M')}] "
                f"waiting... ({remaining/60:.0f} min to go)",
                flush=True,
            )
    return diff


def run_verify(phase: str) -> int:
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] Phase: {phase.upper()}",
        flush=True,
    )
    print(f"{sep}", flush=True)
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "raceday_verify.py"),
        "--phase", phase,
    ]
    print(f"$ {' '.join(cmd)}\n", flush=True)
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def print_schedule(from_hhmm: str | None, dry_run: bool):
    today = date.today()
    print(f"{'='*60}", flush=True)
    print(f"  Race Day Verification Scheduler", flush=True)
    print(f"  Date : {today}  (JRA Saturday)", flush=True)
    if dry_run:
        print(f"  Mode : DRY RUN (no sleep, no verification)", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  {'TIME':6}  {'PHASE':12}  DESCRIPTION", flush=True)
    print(f"  {'-'*54}", flush=True)
    for t, phase, desc in CHECKPOINTS:
        skip = from_hhmm and t < from_hhmm
        marker = "SKIP" if skip else "    "
        print(f"  {t}   {marker} {phase:12}  {desc}", flush=True)
    print(flush=True)


def main():
    parser = argparse.ArgumentParser(description="Race day verification scheduler")
    parser.add_argument(
        "--from", dest="from_time", metavar="HH:MM", default=None,
        help="Skip phases scheduled before this time (e.g. --from 12:00)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print schedule without sleeping or running verification",
    )
    args = parser.parse_args()

    print_schedule(args.from_time, args.dry_run)

    if args.dry_run:
        return

    ran = 0
    for target_time, phase, desc in CHECKPOINTS:
        # Skip phases explicitly before --from time
        if args.from_time and target_time < args.from_time:
            print(
                f"[{datetime.now().strftime('%H:%M')}] Skipping {phase} (before --from {args.from_time})",
                flush=True,
            )
            continue

        # Skip phases that are already more than 5 minutes past
        target_dt = hhmm_to_today(target_time)
        already_past_secs = (datetime.now() - target_dt).total_seconds()
        if already_past_secs > 300:
            print(
                f"[{datetime.now().strftime('%H:%M')}] Skipping {phase} "
                f"(scheduled {target_time}, already {already_past_secs/60:.0f} min past)",
                flush=True,
            )
            continue

        sleep_until(target_time)

        rc = run_verify(phase)
        ran += 1

        status = {0: "PASSED", 1: "WARNING (issues found)"}.get(rc, f"ERROR (exit {rc})")
        print(
            f"\n[{datetime.now().strftime('%H:%M:%S')}] {phase} -> {status}",
            flush=True,
        )
        print(flush=True)

    if ran == 0:
        print(
            "No checkpoints remaining today. "
            "Use --from HH:MM to start from a specific time.",
            flush=True,
        )
    else:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"All {ran} scheduled phases complete.",
            flush=True,
        )


if __name__ == "__main__":
    main()
