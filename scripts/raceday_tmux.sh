#!/usr/bin/env bash
# raceday_tmux.sh - Launch race day monitoring in a tmux session.
#
# Creates 3 windows:
#   [0] monitor  -- jltsql realtime start (live RT_ data stream)
#   [1] verify   -- raceday_scheduler.py  (auto-runs verify at checkpoints)
#   [2] status   -- watch jltsql status   (DB row counts, refreshes every 60s)
#
# Usage:
#   bash scripts/raceday_tmux.sh              # start session and attach
#   bash scripts/raceday_tmux.sh --detach     # start without attaching
#   bash scripts/raceday_tmux.sh --from 12:00 # skip early phases
#   bash scripts/raceday_tmux.sh --kill       # kill existing session
#
# Attach later:
#   tmux attach-session -t jrvltsql-raceday
#
# Switch windows inside tmux:
#   Ctrl-B 0/1/2   -- switch to window 0/1/2
#   Ctrl-B D       -- detach (session keeps running)

set -euo pipefail

SESSION="jrvltsql-raceday"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/data"
TODAY="$(date +%Y%m%d)"
PYTHON="${PYTHON:-python}"

# Parse args
DETACH=false
FROM_TIME=""
KILL_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --detach)   DETACH=true ;;
        --kill)     KILL_ONLY=true ;;
        --from)     shift; FROM_TIME="$1" ;;
        --from=*)   FROM_TIME="${arg#--from=}" ;;
        -h|--help)
            sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
    esac
done

# Kill existing session
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Killing existing session: $SESSION"
    tmux kill-session -t "$SESSION"
fi

if $KILL_ONLY; then
    echo "Session killed."
    exit 0
fi

mkdir -p "$LOG_DIR"

# RT_ specs for realtime monitor
RT_SPECS="0B12,0B15,0B30,0B31,0B32,0B33,0B34,0B35,0B36"

# Scheduler args
SCHED_ARGS=""
if [[ -n "$FROM_TIME" ]]; then
    SCHED_ARGS="--from $FROM_TIME"
fi

echo "============================================================"
echo "  JRVLTSQL Race Day tmux Session"
echo "  Project : $PROJECT_ROOT"
echo "  Session : $SESSION"
echo "  Log dir : $LOG_DIR"
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Create session + window 0: realtime monitor
# ----------------------------------------------------------------
tmux new-session -d -s "$SESSION" -n "monitor" -c "$PROJECT_ROOT"

tmux send-keys -t "$SESSION:monitor" \
    "echo '=== Window 0: Realtime Monitor ===' && \
     echo 'RT specs: $RT_SPECS' && \
     echo '' && \
     $PYTHON -m src.cli.main realtime start --specs $RT_SPECS" \
    Enter

# ----------------------------------------------------------------
# Window 1: Verification scheduler
# ----------------------------------------------------------------
tmux new-window -t "$SESSION" -n "verify" -c "$PROJECT_ROOT"

SCHED_CMD="$PYTHON scripts/raceday_scheduler.py $SCHED_ARGS"
tmux send-keys -t "$SESSION:verify" \
    "echo '=== Window 1: Verification Scheduler ===' && \
     echo 'Log: $LOG_DIR/raceday_scheduler_$TODAY.log' && \
     echo '' && \
     $SCHED_CMD 2>&1 | tee '$LOG_DIR/raceday_scheduler_$TODAY.log'" \
    Enter

# ----------------------------------------------------------------
# Window 2: Live DB status (split pane)
# ----------------------------------------------------------------
tmux new-window -t "$SESSION" -n "status" -c "$PROJECT_ROOT"

# Top pane: jltsql status (every 60s)
tmux send-keys -t "$SESSION:status" \
    "watch -n 60 '$PYTHON -m src.cli.main status'" \
    Enter

# Bottom pane: cache info (every 120s)
tmux split-window -t "$SESSION:status" -v -p 35 -c "$PROJECT_ROOT"
tmux send-keys -t "$SESSION:status.1" \
    "watch -n 120 '$PYTHON -m src.cli.main cache info'" \
    Enter

# ----------------------------------------------------------------
# Focus on monitor window, attach
# ----------------------------------------------------------------
tmux select-window -t "$SESSION:monitor"

echo "tmux session '$SESSION' started with 3 windows:"
echo "  [0] monitor -- realtime data stream (RT_)"
echo "  [1] verify  -- verification scheduler (auto at checkpoints)"
echo "  [2] status  -- live DB status / cache info"
echo ""
echo "Commands:"
echo "  Ctrl-B 0/1/2  switch window"
echo "  Ctrl-B D      detach (session keeps running)"
echo "  Ctrl-B [      scroll mode (q to exit)"
echo ""
echo "Re-attach later:"
echo "  tmux attach-session -t $SESSION"
echo ""

if $DETACH; then
    echo "(--detach: not attaching. Session is running in background.)"
else
    tmux attach-session -t "$SESSION"
fi
