#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export LANG="${LANG:-ja_JP.UTF-8}"
export LC_ALL="${LC_ALL:-ja_JP.UTF-8}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
export JVLINK_WINEPREFIX="${JVLINK_WINEPREFIX:-$WINEPREFIX}"
export JVLINK_WINEARCH="${JVLINK_WINEARCH:-$WINEARCH}"
export JVLINK_BRIDGE_EXE="${JVLINK_BRIDGE_EXE:-/app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe}"
export VNC_PORT="${VNC_PORT:-5900}"
export VNC_PUBLIC_PORT="${VNC_PUBLIC_PORT:-$VNC_PORT}"
export NOVNC_PUBLIC_PORT="${NOVNC_PUBLIC_PORT:-6080}"
export AUTO_DISMISS_JVLINK_DIALOGS="${AUTO_DISMISS_JVLINK_DIALOGS:-1}"
export JVLINK_DIALOG_WATCH_INTERVAL="${JVLINK_DIALOG_WATCH_INTERVAL:-1}"

mkdir -p "$WINEPREFIX" /app/data /app/logs

start_display() {
  if [ "${START_XVFB:-1}" != "1" ]; then
    return
  fi

  rm -f "/tmp/.X${DISPLAY#:}-lock"

  Xvfb "$DISPLAY" -screen 0 "${XVFB_SCREEN:-1280x800x24}" -nolisten tcp >/tmp/xvfb.log 2>&1 &
  export XVFB_PID=$!
  sleep 1

  fluxbox >/tmp/fluxbox.log 2>&1 &
  export FLUXBOX_PID=$!

  x11vnc -display "$DISPLAY" -forever -shared -rfbport "$VNC_PORT" -nopw >/tmp/x11vnc.log 2>&1 &
  export X11VNC_PID=$!

  websockify --web=/usr/share/novnc "${NOVNC_LISTEN:-0.0.0.0:6080}" "localhost:$VNC_PORT" >/tmp/novnc.log 2>&1 &
  export NOVNC_PID=$!
}

start_jvlink_dialog_watcher() {
  if [ "$AUTO_DISMISS_JVLINK_DIALOGS" != "1" ]; then
    return
  fi
  if ! command -v xdotool >/dev/null 2>&1; then
    echo "xdotool not found; JV-Link dialog auto-dismiss is disabled." >&2
    return
  fi

  (
    while true; do
      for title in '払戻情報表示設定' 'JRA-VAN Data Lab\.'; do
        for window_id in $(xdotool search --name "$title" 2>/dev/null || true); do
          window_name="$(xdotool getwindowname "$window_id" 2>/dev/null || true)"
          if [ -n "$window_name" ]; then
            echo "Auto-dismissing JV-Link dialog: $window_name" >>/tmp/jvlink-dialog-watcher.log
          fi
          xdotool windowactivate --sync "$window_id" key Return >>/tmp/jvlink-dialog-watcher.log 2>&1 || true
        done
      done
      sleep "$JVLINK_DIALOG_WATCH_INTERVAL"
    done
  ) &
  export JVLINK_DIALOG_WATCHER_PID=$!
}

init_wine() {
  if [ "${AUTO_INSTALL_JVLINK:-1}" = "1" ]; then
    scripts/setup_wine_jvlink.sh --auto || {
      echo "JV-Link automatic setup failed. Open noVNC and rerun scripts/setup_wine_jvlink.sh manually." >&2
    }
  else
    if [ ! -f "$WINEPREFIX/system.reg" ]; then
      echo "Initializing Wine prefix at $WINEPREFIX"
      wineboot --init || true
      wineserver -w || true
    fi
  fi
}

cleanup() {
  for pid in "${JVLINK_DIALOG_WATCHER_PID:-}" "${NOVNC_PID:-}" "${X11VNC_PID:-}" "${FLUXBOX_PID:-}" "${XVFB_PID:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

start_display
start_jvlink_dialog_watcher
init_wine

cat <<EOF
Wine desktop:
  noVNC: http://localhost:${NOVNC_PUBLIC_PORT}/vnc.html
  VNC:   localhost:${VNC_PUBLIC_PORT}
Wine prefix:
  $WINEPREFIX
JVLinkBridge:
  $JVLINK_BRIDGE_EXE
JV-Link dialog auto-dismiss:
  ${AUTO_DISMISS_JVLINK_DIALOGS}
EOF

exec "$@"
