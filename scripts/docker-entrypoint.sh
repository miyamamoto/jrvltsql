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
export HOME="${JRVLTSQL_HOME:-/home/jrvltsql}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/app/.cache}"
export JRVLTSQL_CONFIG="${JRVLTSQL_CONFIG:-/app/config/config.yaml}"
export JRVLTSQL_CONFIG_EXAMPLE="${JRVLTSQL_CONFIG_EXAMPLE:-/app/config/config.yaml.example}"

mkdir -p "$WINEPREFIX" /app/data /app/logs /app/config "$HOME" "$XDG_CACHE_HOME"

if [ ! -f "$JRVLTSQL_CONFIG" ] && [ -f "$JRVLTSQL_CONFIG_EXAMPLE" ]; then
  cp "$JRVLTSQL_CONFIG_EXAMPLE" "$JRVLTSQL_CONFIG"
  config_dir="$(dirname "$JRVLTSQL_CONFIG")"
  config_uid="$(stat -c '%u' "$config_dir" 2>/dev/null || true)"
  config_gid="$(stat -c '%g' "$config_dir" 2>/dev/null || true)"
  if [ -n "$config_uid" ] && [ -n "$config_gid" ]; then
    chown "$config_uid:$config_gid" "$JRVLTSQL_CONFIG" 2>/dev/null || true
  fi
fi

if [ "$(id -u)" = "0" ]; then
  target_uid="${APP_UID:-}"
  target_gid="${APP_GID:-}"

  if [ -z "$target_uid" ] && [ -e "$WINEPREFIX" ]; then
    target_uid="$(stat -c '%u' "$WINEPREFIX")"
  fi
  if [ -z "$target_gid" ] && [ -e "$WINEPREFIX" ]; then
    target_gid="$(stat -c '%g' "$WINEPREFIX")"
  fi

  if [ -z "$target_uid" ] || [ "$target_uid" = "0" ]; then
    target_uid=1000
  fi
  if [ -z "$target_gid" ] || [ "$target_gid" = "0" ]; then
    target_gid="$target_uid"
  fi

  chown -R "$target_uid:$target_gid" /app/data /app/logs "$HOME" "$XDG_CACHE_HOME" 2>/tmp/jrvltsql-chown.log || true
  if [ ! -f "$WINEPREFIX/system.reg" ]; then
    chown -R "$target_uid:$target_gid" "$WINEPREFIX" 2>/tmp/jrvltsql-wineprefix-chown.log || true
  fi

  exec gosu "$target_uid:$target_gid" "$0" "$@"
fi

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


wait_wineserver() {
  local timeout_seconds="${1:-${JVLINK_WINESERVER_WAIT_SECONDS:-30}}"
  local status

  if command -v timeout >/dev/null 2>&1; then
    timeout "$timeout_seconds" wineserver -w || {
      status=$?
      if [ "$status" = "124" ]; then
        echo "wineserver still has active processes after ${timeout_seconds}s; continuing."
      fi
      return 0
    }
  else
    wineserver -w || true
  fi
}

verify_wine_prefix() {
  local syswow64="$WINEPREFIX/drive_c/windows/syswow64"

  if [ ! -f "$syswow64/kernel32.dll" ]; then
    echo "Wine prefix $WINEPREFIX has no 32-bit support:" >&2
    echo "  missing $syswow64/kernel32.dll" >&2
    echo "JV-Link and JVLinkBridge.exe are 32-bit, so no fetch can succeed." >&2
    return 1
  fi
}

init_wine() {
  if [ ! -f "$WINEPREFIX/system.reg" ]; then
    echo "Initializing Wine prefix at $WINEPREFIX"
    # wineboot must not see an X display: with one, Wine skips the 32-bit half
    # of a win64 prefix and syswow64 is left without kernel32.dll, which makes
    # the 32-bit JV-Link and JVLinkBridge.exe unusable.
    env -u DISPLAY WINEDLLOVERRIDES="mscoree,mshtml=" wineboot --init
    wait_wineserver
  fi

  # JV-Link and JVLinkBridge.exe are 32-bit. Stop here rather than let the
  # collector answer /health while every fetch fails as an opaque timeout.
  verify_wine_prefix || exit 1

  if [ ! -f "$WINEPREFIX/drive_c/windows/syswow64/JVDTLAB/JVDTLab.dll" ]; then
    cat >&2 <<'NOTICE'
JV-Link is not installed in this prefix.
Install it once by hand on the noVNC desktop and agree to the JRA-VAN terms
there; see docs/jvlink_manual_registration.md. Fetches fail closed until then.
NOTICE
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
