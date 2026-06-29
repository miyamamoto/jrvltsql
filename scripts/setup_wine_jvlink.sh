#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win32}"
export JVLINK_WINEPREFIX="${JVLINK_WINEPREFIX:-$WINEPREFIX}"
export JVLINK_WINEARCH="${JVLINK_WINEARCH:-$WINEARCH}"
export JVLINK_BRIDGE_EXE="${JVLINK_BRIDGE_EXE:-/app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe}"
export WINEDEBUG="${WINEDEBUG:--all}"

INSTALLERS_DIR="${JVLINK_INSTALLERS_DIR:-/installers}"

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_wine_jvlink.sh --auto
  scripts/setup_wine_jvlink.sh [installer.exe]

Examples:
  scripts/setup_wine_jvlink.sh --auto
  scripts/setup_wine_jvlink.sh /installers/JVLinkSetup.exe
  JVLINK_INSTALLER=/installers/JVLinkSetup.exe scripts/setup_wine_jvlink.sh --auto
  JVLINK_INSTALLER_ARGS='/S' scripts/setup_wine_jvlink.sh --auto
  JVLINK_DLL='C:\JRA-VAN\Data Lab\JVDTLab.dll' scripts/setup_wine_jvlink.sh

Open noVNC first if the installer needs mouse input:
  http://localhost:6080/vnc.html
EOF
}

is_placeholder() {
  case "${1:-}" in
    ""|\$\{*\}) return 0 ;;
    *) return 1 ;;
  esac
}

wine_boot() {
  mkdir -p "$WINEPREFIX"

  echo "Initializing Wine prefix: $WINEPREFIX"
  wineboot --init || true
  wineserver -w || true
}

jvlink_registered() {
  grep -Eiq 'JVDTLab\.JVLink|JVDTLab\.dll|JRA-VAN.*JV-Link' \
    "$WINEPREFIX/system.reg" "$WINEPREFIX/user.reg" "$WINEPREFIX/userdef.reg" 2>/dev/null
}

find_installer() {
  if [ -n "${JVLINK_INSTALLER:-}" ]; then
    printf '%s\n' "$JVLINK_INSTALLER"
    return
  fi

  find "$INSTALLERS_DIR" -maxdepth 2 -type f \
    \( -iname '*JV*Link*.exe' \
       -o -iname '*JVDT*.exe' \
       -o -iname '*JRA*VAN*.exe' \
       -o -iname '*.msi' \
       -o -iname '*.exe' \) \
    -print 2>/dev/null | sort | head -n 1
}

run_installer() {
  local installer="$1"
  local installer_lower="${installer,,}"
  local installer_args=()

  if [ ! -f "$installer" ]; then
    echo "Installer not found: $installer" >&2
    return 1
  fi

  if [ -n "${JVLINK_INSTALLER_ARGS:-}" ]; then
    # shellcheck disable=SC2206
    installer_args=(${JVLINK_INSTALLER_ARGS})
  fi

  echo "Running installer: $installer"
  if [[ "$installer_lower" == *.msi ]]; then
    wine msiexec /i "$installer" "${installer_args[@]}"
  else
    wine "$installer" "${installer_args[@]}"
  fi
  wineserver -w || true
}

detect_dll() {
  if [ -n "${JVLINK_DLL:-}" ]; then
    printf '%s\n' "$JVLINK_DLL"
    return
  fi

  find "$WINEPREFIX/drive_c" "$INSTALLERS_DIR" -iname 'JVDTLab.dll' -print -quit 2>/dev/null || true
}

register_dll() {
  local candidate="$1"
  local win_path

  if [ -z "$candidate" ]; then
    echo "JVDTLab.dll was not found. If the installer completed, this may be OK."
    echo "To register manually, set JVLINK_DLL to a Windows path and rerun this script."
    return 0
  fi

  win_path="$candidate"
  if [[ "$candidate" != [A-Za-z]:\\* && "$candidate" != \\\\* ]]; then
    win_path="$(winepath -w "$candidate" 2>/dev/null || printf '%s' "$candidate")"
  fi

  echo "Registering JV-Link DLL: $win_path"
  wine regsvr32 /s "$win_path"
  wineserver -w || true
}

configure_service_key() {
  if is_placeholder "${JVLINK_SERVICE_KEY:-}"; then
    return 0
  fi

  echo "Configuring JV-Link service key from JVLINK_SERVICE_KEY"
  python3 - <<'PY'
from src.jvlink.bridge import JVLinkBridge

bridge = JVLinkBridge()
try:
    code = bridge.jv_set_service_key(__import__("os").environ["JVLINK_SERVICE_KEY"])
    print(f"JV-Link service key setup returned code={code}")
finally:
    bridge.cleanup()
PY
}

configure_service_key_if_possible() {
  if is_placeholder "${JVLINK_SERVICE_KEY:-}"; then
    return 0
  fi

  if jvlink_registered || [ -n "$(detect_dll)" ]; then
    configure_service_key
  else
    echo "Skipping JVLINK_SERVICE_KEY setup because JV-Link COM is not registered yet."
  fi
}

auto_setup() {
  local installer
  local dll

  wine_boot

  if jvlink_registered; then
    echo "JV-Link registry entries already exist."
  else
    installer="$(find_installer)"
    if [ -n "$installer" ]; then
      run_installer "$installer"
    else
      echo "No JV-Link installer found under $INSTALLERS_DIR."
      echo "Place the installer there or set JVLINK_INSTALLER."
    fi
  fi

  dll="$(detect_dll)"
  register_dll "$dll"
  configure_service_key_if_possible
}

manual_setup() {
  wine_boot

  if [ $# -gt 0 ]; then
    run_installer "$1"
  fi

  register_dll "$(detect_dll)"
  configure_service_key_if_possible
}

case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
  --auto)
    auto_setup
    ;;
  *)
    manual_setup "$@"
    ;;
esac
