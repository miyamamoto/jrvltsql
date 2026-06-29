#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win32}"
export JVLINK_WINEPREFIX="${JVLINK_WINEPREFIX:-$WINEPREFIX}"
export JVLINK_WINEARCH="${JVLINK_WINEARCH:-$WINEARCH}"
export JVLINK_BRIDGE_EXE="${JVLINK_BRIDGE_EXE:-/app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe}"
export VNC_PORT="${VNC_PORT:-5900}"
export VNC_PUBLIC_PORT="${VNC_PUBLIC_PORT:-$VNC_PORT}"
export NOVNC_PUBLIC_PORT="${NOVNC_PUBLIC_PORT:-6080}"

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

init_wine() {
  if [ ! -f "$WINEPREFIX/system.reg" ]; then
    echo "Initializing Wine prefix at $WINEPREFIX"
    wineboot --init || true
    wineserver -w || true
  fi

  if [ "${RUN_JVLINK_INSTALLER:-0}" = "1" ] && [ -n "${JVLINK_INSTALLER:-}" ]; then
    echo "Running JV-Link installer: $JVLINK_INSTALLER"
    wine "$JVLINK_INSTALLER"
    wineserver -w || true
  fi

  if [ "${REGISTER_JVLINK_DLL:-0}" = "1" ] && [ -n "${JVLINK_DLL:-}" ]; then
    echo "Registering JV-Link DLL: $JVLINK_DLL"
    wine regsvr32 "$JVLINK_DLL"
    wineserver -w || true
  fi
}

cleanup() {
  for pid in "${NOVNC_PID:-}" "${X11VNC_PID:-}" "${FLUXBOX_PID:-}" "${XVFB_PID:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

start_display
init_wine

cat <<EOF
Wine desktop:
  noVNC: http://localhost:${NOVNC_PUBLIC_PORT}/vnc.html
  VNC:   localhost:${VNC_PUBLIC_PORT}
Wine prefix:
  $WINEPREFIX
JVLinkBridge:
  $JVLINK_BRIDGE_EXE
EOF

exec "$@"
