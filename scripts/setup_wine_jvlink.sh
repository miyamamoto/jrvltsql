#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
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
  JVLINK_USE_GUI_INSTALLER=1 scripts/setup_wine_jvlink.sh --auto
  JVLINK_SET_SERVICE_KEY=1 JVLINK_SERVICE_KEY='XXXX...' scripts/setup_wine_jvlink.sh
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

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

wine_reg_add() {
  wine reg add "$@" >/dev/null
}

normalize_service_key() {
  printf '%s' "${1:-}" | tr -cd '[:alnum:]'
}

service_key_setup_enabled() {
  case "${JVLINK_SET_SERVICE_KEY:-0}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

write_jvlink_registry() {
  local install_path="${JVLINK_INSTALL_PATH_WIN:-C:\\Program Files (x86)\\JRA-VAN\\Data Lab}"
  local save_path="${JVLINK_SAVE_PATH_WIN:-C:\\ProgramData\\JRA-VAN\\Data Lab}"
  local install_date
  local root

  install_date="$(date '+%m/%d/%y %H:%M:%S')"

  mkdir -p "$WINEPREFIX/drive_c/ProgramData/JRA-VAN/Data Lab/event"

  for root in \
    'HKLM\Software\JRA-VAN Data Lab.' \
    'HKLM\Software\WOW6432Node\JRA-VAN Data Lab.'
  do
    wine_reg_add "$root\\server_info" /v campaignurl /t REG_SZ /d 'http://jra-van.jp/dlb/index.html' /f
    wine_reg_add "$root\\server_info" /v datahost /t REG_SZ /d 'datalab.cdn.jra-van.ne.jp' /f
    wine_reg_add "$root\\server_info" /v datapath /t REG_SZ /d '/datalab/' /f
    wine_reg_add "$root\\server_info" /v dataport /t REG_DWORD /d 80 /f
    wine_reg_add "$root\\server_info" /v realhost /t REG_SZ /d 'reallab.jra-van.ne.jp' /f
    wine_reg_add "$root\\server_info" /v realpath /t REG_SZ /d '/Browsing/GateServlet/' /f
    wine_reg_add "$root\\server_info" /v realport /t REG_DWORD /d 80 /f
    wine_reg_add "$root\\server_info" /v serverhost /t REG_SZ /d 'authlab.jra-van.ne.jp' /f
    wine_reg_add "$root\\server_info" /v serverpath /t REG_SZ /d '/Browsing/JVServlet/' /f
    wine_reg_add "$root\\server_info" /v serverport /t REG_DWORD /d 80 /f
    wine_reg_add "$root\\server_info" /v verupurl /t REG_SZ /d 'http://jra-van.jp/dlb/sft/jv.html' /f

    wine_reg_add "$root\\uid_pass" /v agentport /t REG_DWORD /d 6531 /f
    wine_reg_add "$root\\uid_pass" /v installdate /t REG_SZ /d "$install_date" /f
    wine_reg_add "$root\\uid_pass" /v installpath /t REG_SZ /d "$install_path" /f
    wine_reg_add "$root\\uid_pass" /v messagekey /t REG_SZ /d '00000000000000' /f
    wine_reg_add "$root\\uid_pass" /v payflag /t REG_SZ /d '2' /f
    wine_reg_add "$root\\uid_pass" /v promotionkey /t REG_SZ /d 'PRLW2502GVANCD07P' /f
    wine_reg_add "$root\\uid_pass" /v saveflag /t REG_SZ /d '1' /f
    wine_reg_add "$root\\uid_pass" /v savepath /t REG_SZ /d "$save_path" /f
    wine_reg_add "$root\\uid_pass" /v servicekey /t REG_SZ /d '' /f
    wine_reg_add "$root\\uid_pass" /v ukey /t REG_SZ /d '' /f
  done
}

copy_unshield_payload() {
  local payload_dir="$1"
  local program_dir="$WINEPREFIX/drive_c/Program Files (x86)/JRA-VAN/Data Lab"
  local com_dir="$WINEPREFIX/drive_c/windows/syswow64/JVDTLAB"

  mkdir -p "$program_dir" "$com_dir"

  cp -f "$payload_dir/JV-Link/JVDTLab.dll" "$com_dir/JVDTLab.dll"
  cp -f "$payload_dir/JV-LinkAgent/JVLinkAgent.exe" "$program_dir/JVLinkAgent.exe"
  cp -f "$payload_dir/JV-LinkEnv/"*.exe "$program_dir"/
  cp -f "$payload_dir/SelfReg____________/MSFLXGRD.OCX" "$program_dir/MSFLXGRD.OCX"
  cp -f "$payload_dir/Remove/"* "$program_dir"/
}

extract_installshield_payload() {
  local setup_exe="$1"
  local work_dir="$2"
  local marker="$work_dir/marker"
  local disk_dir=""
  local setup_pid
  local i

  touch "$marker"
  WINEDEBUG=-all wine "$setup_exe" /s >/tmp/jvlink-installshield-extract.log 2>&1 &
  setup_pid=$!

  for i in $(seq 1 "${JVLINK_EXTRACT_TIMEOUT_SECONDS:-60}"); do
    disk_dir="$(find "$WINEPREFIX/drive_c/users" -path '*/Temp/*/Disk1/data1.cab' -newer "$marker" -printf '%h\n' 2>/dev/null | head -n 1)"
    if [ -n "$disk_dir" ]; then
      break
    fi
    sleep 1
  done

  kill "$setup_pid" 2>/dev/null || true
  pkill -f '[J]VLinkSetup.exe' 2>/dev/null || true

  if [ -z "$disk_dir" ]; then
    echo "JV-Link InstallShield payload was not extracted." >&2
    return 1
  fi

  mkdir -p "$work_dir/payload"
  unshield -d "$work_dir/payload" x "$disk_dir/data1.cab" >/tmp/jvlink-unshield.log
  printf '%s\n' "$work_dir/payload"
}

install_jvlink_extracted() {
  local installer="$1"
  local work_dir="$2"
  local setup_exe
  local payload_dir
  local dll_path

  if ! command_exists 7z || ! command_exists unshield; then
    echo "7z and unshield are required for non-GUI JV-Link installation." >&2
    return 1
  fi

  mkdir -p "$work_dir/outer"
  7z x -y "-o$work_dir/outer" "$installer" >/tmp/jvlink-7z.log

  setup_exe="$(find "$work_dir/outer" -maxdepth 2 -iname 'JVLinkSetup.exe' -print -quit)"
  if [ -z "$setup_exe" ]; then
    echo "JVLinkSetup.exe was not found inside $installer." >&2
    return 1
  fi

  payload_dir="$(extract_installshield_payload "$setup_exe" "$work_dir")"
  if [ -z "$payload_dir" ] || [ ! -f "$payload_dir/JV-Link/JVDTLab.dll" ]; then
    echo "JVDTLab.dll was not found in the extracted JV-Link payload." >&2
    return 1
  fi

  copy_unshield_payload "$payload_dir"
  write_jvlink_registry

  dll_path="$WINEPREFIX/drive_c/windows/syswow64/JVDTLAB/JVDTLab.dll"
  echo "Registering extracted JV-Link DLL: $(winepath -w "$dll_path")"
  wine regsvr32 /s "$(winepath -w "$dll_path")"
  wineserver -w || true
}

run_installer() {
  local installer="$1"
  local installer_lower="${installer,,}"
  local installer_args=()
  local work_dir

  if [ ! -f "$installer" ]; then
    echo "Installer not found: $installer" >&2
    return 1
  fi

  if [[ "$installer_lower" == *.exe ]] && [ "${JVLINK_USE_GUI_INSTALLER:-0}" != "1" ]; then
    echo "Extracting and installing JV-Link without GUI: $installer"
    work_dir="$(mktemp -d)"
    install_jvlink_extracted "$installer" "$work_dir"
    return
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
  if ! service_key_setup_enabled; then
    echo "Skipping JVLINK_SERVICE_KEY registration. Set JVLINK_SET_SERVICE_KEY=1 to opt in."
    return 0
  fi

  echo "Configuring JV-Link service key from JVLINK_SERVICE_KEY"
  python3 - <<'PY'
import os
import re

from src.jvlink.bridge import JVLinkBridge

service_key = re.sub(r"[^A-Za-z0-9]", "", os.environ["JVLINK_SERVICE_KEY"])

bridge = JVLinkBridge()
try:
    code = bridge.jv_set_service_key(service_key)
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
