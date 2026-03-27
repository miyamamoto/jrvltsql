#!/usr/bin/env bash
# raceday_tmux.sh — Race day monitoring tmux session.
#
# Creates 3 windows:
#   [0] monitor   — jltsql realtime start  (live RT_ data stream, runs all day)
#   [1] scheduler — raceday_scheduler.py   (verify after each of 12 races + post)
#   [2] status    — watch jltsql status + cache info (split pane)
#
# Code auto-fix + PR creation is handled by Claude Code /loop:
#   /loop 35m
#   Run python scripts/raceday_verify.py --phase auto, read the JSON report in
#   data/raceday_report_*.json, and if there are issues: diagnose the root cause,
#   fix the code, create a branch and PR with gh pr create. Report what you found.
#
# Usage:
#   bash scripts/raceday_tmux.sh               # start + attach
#   bash scripts/raceday_tmux.sh --detach      # start without attaching
#   bash scripts/raceday_tmux.sh --from 12:00  # skip morning scheduler checkpoints
#   bash scripts/raceday_tmux.sh --fetch       # auto-fetch missing data in scheduler
#   bash scripts/raceday_tmux.sh --kill        # kill existing session
#
# Re-attach:
#   tmux attach-session -t jrvltsql-raceday
#
# Inside tmux:
#   Ctrl-B 0/1/2   switch window
#   Ctrl-B D       detach (keeps running)
#   Ctrl-B [       scroll (q to exit)

set -euo pipefail

SESSION="jrvltsql-raceday"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/data"
TODAY="$(date +%Y%m%d)"
PYTHON="${PYTHON:-python}"

DETACH=false
KILL_ONLY=false
FROM_TIME=""
FETCH_FLAG=""

for arg in "$@"; do
    case "$arg" in
        --detach)    DETACH=true ;;
        --kill)      KILL_ONLY=true ;;
        --fetch)     FETCH_FLAG="--fetch" ;;
        --from=*)    FROM_TIME="${arg#--from=}" ;;
        --from)      ;;  # next arg handled below, not supported in this loop
        -h|--help)
            sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
    esac
done

# Kill existing session
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Killing existing session: $SESSION"
    tmux kill-session -t "$SESSION"
fi
$KILL_ONLY && { echo "Session killed."; exit 0; }

mkdir -p "$LOG_DIR"

RT_SPECS="0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36"
SCHED_ARGS="$FETCH_FLAG"
[[ -n "$FROM_TIME" ]] && SCHED_ARGS="$SCHED_ARGS --from $FROM_TIME"

echo "============================================================"
echo "  JRVLTSQL Race Day tmux Session — $TODAY"
echo "  Project : $PROJECT_ROOT"
echo "  Session : $SESSION"
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Window 0: Realtime monitor (RT_ live stream)
# ----------------------------------------------------------------
tmux new-session -d -s "$SESSION" -n "monitor" -c "$PROJECT_ROOT"
tmux send-keys -t "$SESSION:monitor" \
    "echo '=== [0] Realtime Monitor — RT_ live stream ===' \
     && echo 'specs: $RT_SPECS' && echo '' \
     && $PYTHON -m src.cli.main realtime start --specs $RT_SPECS" \
    Enter

# ----------------------------------------------------------------
# Window 1: Per-race verification scheduler
# ----------------------------------------------------------------
tmux new-window -t "$SESSION" -n "scheduler" -c "$PROJECT_ROOT"
SCHED_LOG="$LOG_DIR/raceday_scheduler_$TODAY.log"
tmux send-keys -t "$SESSION:scheduler" \
    "echo '=== [1] Per-race Verification Scheduler ===' \
     && echo 'Log: $SCHED_LOG' && echo '' \
     && $PYTHON scripts/raceday_scheduler.py $SCHED_ARGS \
        2>&1 | tee '$SCHED_LOG'" \
    Enter

# ----------------------------------------------------------------
# Window 2: Live DB status (split: top=status, bottom=cache)
# ----------------------------------------------------------------
tmux new-window -t "$SESSION" -n "status" -c "$PROJECT_ROOT"
tmux send-keys -t "$SESSION:status" \
    "watch -n 60 '$PYTHON -m src.cli.main status'" \
    Enter
tmux split-window -t "$SESSION:status" -v -p 35 -c "$PROJECT_ROOT"
tmux send-keys -t "$SESSION:status.1" \
    "watch -n 120 '$PYTHON -m src.cli.main cache info'" \
    Enter

# ----------------------------------------------------------------
# Focus monitor, attach
# ----------------------------------------------------------------
tmux select-window -t "$SESSION:monitor"

echo "Session '$SESSION' started:"
echo "  [0] monitor   — RT_ realtime stream"
echo "  [1] scheduler — per-race verify (16 checkpoints today)"
echo "  [2] status    — DB status + cache info"
echo ""
echo "Also run in Claude Code for code auto-fix + PR:"
echo '  /loop 35m'
echo '  Run python scripts/raceday_verify.py --phase auto, then read'
echo '  data/raceday_report_*.json. If issues exist: diagnose, fix the'
echo '  code, commit to a new branch, and create a PR with gh pr create.'
echo ""
echo "Ctrl-B 0/1/2 = switch  |  Ctrl-B D = detach"
echo "tmux attach-session -t $SESSION  (re-attach)"
echo ""

$DETACH && { echo "(--detach: running in background)"; exit 0; }
tmux attach-session -t "$SESSION"
