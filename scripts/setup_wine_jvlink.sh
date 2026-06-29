#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win32}"

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_wine_jvlink.sh [installer.exe]

Examples:
  scripts/setup_wine_jvlink.sh /installers/JVLinkSetup.exe
  JVLINK_DLL='C:\JRA-VAN\Data Lab\JVDTLab.dll' scripts/setup_wine_jvlink.sh

Open noVNC first if the installer needs mouse input:
  http://localhost:6080/vnc.html
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

mkdir -p "$WINEPREFIX"

echo "Initializing Wine prefix: $WINEPREFIX"
wineboot --init || true
wineserver -w || true

if [ $# -gt 0 ]; then
  installer="$1"
  if [ ! -f "$installer" ]; then
    echo "Installer not found: $installer" >&2
    exit 1
  fi
  echo "Running installer: $installer"
  wine "$installer"
  wineserver -w || true
fi

if [ -n "${JVLINK_DLL:-}" ]; then
  echo "Registering JV-Link DLL from JVLINK_DLL: $JVLINK_DLL"
  wine regsvr32 "$JVLINK_DLL"
  wineserver -w || true
  exit 0
fi

candidate="$(find "$WINEPREFIX/drive_c" /installers -iname 'JVDTLab.dll' -print -quit 2>/dev/null || true)"
if [ -n "$candidate" ]; then
  win_path="$(winepath -w "$candidate" 2>/dev/null || printf '%s' "$candidate")"
  echo "Registering detected JV-Link DLL: $win_path"
  wine regsvr32 "$win_path"
  wineserver -w || true
else
  echo "JVDTLab.dll was not found. If the installer completed, this may be OK."
  echo "To register manually, set JVLINK_DLL to a Windows path and rerun this script."
fi
