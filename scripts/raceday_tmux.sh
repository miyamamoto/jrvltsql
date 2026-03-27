#!/usr/bin/env bash
# raceday_tmux.sh - Launch race day monitoring in a tmux session.
#
# Creates 2 windows:
#   [0] monitor  -- jltsql realtime start (live RT_ data stream)
#   [1] status   -- watch jltsql status + cache info (split pane)
#
# Verification is triggered periodically by Claude Code /loop:
#   /loop 30m python scripts/raceday_verify.py --phase auto
#
# Usage:
#   bash scripts/raceday_tmux.sh          # start session and attach
#   bash scripts/raceday_tmux.sh --detach # start without attaching
#   bash scripts/raceday_tmux.sh --kill   # kill existing session
#
# Attach later:
#   tmux attach-session -t jrvltsql-raceday
#
# Switch windows inside tmux:
#   Ctrl-B 0/1   -- switch to window 0/1
#   Ctrl-B D     -- detach (session keeps running)

set -euo pipefail

SESSION="jrvltsql-raceday"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/data"
TODAY="$(date +%Y%m%d)"
PYTHON="${PYTHON:-python}"

# Parse args
DETACH=false
KILL_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --detach)   DETACH=true ;;
        --kill)     KILL_ONLY=true ;;
        -h|--help)
            sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'
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
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Create session + window 0: realtime monitor
# ----------------------------------------------------------------
tmux new-session -d -s "$SESSION" -n "monitor" -c "$PROJECT_ROOT"

tmux send-keys -t "$SESSION:monitor" \
    "echo '=== [0] Realtime Monitor ===' && \
     echo 'RT specs: $RT_SPECS' && \
     echo '' && \
     $PYTHON -m src.cli.main realtime start --specs $RT_SPECS" \
    Enter

# ----------------------------------------------------------------
# Window 1: Live DB status (split pane: top=status, bottom=cache)
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
# Focus on monitor window, attach
# ----------------------------------------------------------------
tmux select-window -t "$SESSION:monitor"

echo "tmux session '$SESSION' started:"
echo "  [0] monitor -- RT_ realtime data stream"
echo "  [1] status  -- DB status (60s) + cache info (120s)"
echo ""
echo "Verification is driven by Claude Code /loop:"
echo "  /loop 30m python scripts/raceday_verify.py --phase auto"
echo ""
echo "  Ctrl-B 0/1  switch window"
echo "  Ctrl-B D    detach"
echo "  tmux attach-session -t $SESSION   (re-attach)"
echo ""

if $DETACH; then
    echo "(--detach: session running in background)"
else
    tmux attach-session -t "$SESSION"
fi
