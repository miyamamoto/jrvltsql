#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export DISPLAY="${DISPLAY:-:1}"
export LANG="${LANG:-ja_JP.UTF-8}"
export LC_ALL="${LC_ALL:-ja_JP.UTF-8}"
export WINEPREFIX="${WINEPREFIX:-${JVLINK_WINEPREFIX:-${HOME}/.wine-jvlink}}"
export WINEARCH="${WINEARCH:-win64}"
export JVLINK_WINEPREFIX="${JVLINK_WINEPREFIX:-$WINEPREFIX}"
export JVLINK_WINEARCH="${JVLINK_WINEARCH:-$WINEARCH}"
export JVLINK_BRIDGE_EXE="${JVLINK_BRIDGE_EXE:-${PROJECT_ROOT}/tools/jvlink-bridge/bin/native/JVLinkBridge.exe}"
export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-wtsapi32=n,b}"
export JVLINK_WINE_GECKO_VERSION="${JVLINK_WINE_GECKO_VERSION:-2.47.4}"

INSTALLERS_DIR="${JVLINK_INSTALLERS_DIR:-${PROJECT_ROOT}/jvlink-installers}"

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_wine_jvlink.sh --auto
  scripts/setup_wine_jvlink.sh --bridge-only
  scripts/setup_wine_jvlink.sh [installer.exe]

Examples:
  scripts/setup_wine_jvlink.sh --auto
  scripts/setup_wine_jvlink.sh --bridge-only
  scripts/setup_wine_jvlink.sh /installers/JVLinkSetup.exe
  JVLINK_BRIDGE_SOURCE_EXE=/secure/JVLinkBridge.exe scripts/setup_wine_jvlink.sh --bridge-only
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
  configure_wine_computer_name
  repair_wine_prefix_dlls
  install_wtsapi32_shim
}

configure_wine_computer_name() {
  local computer_name key
  computer_name="${WINE_COMPUTERNAME:-}"
  if [ -z "$computer_name" ]; then
    computer_name="$(hostname | tr '[:lower:]' '[:upper:]' | tr -cd 'A-Z0-9-' | cut -c 1-15)"
  fi
  if [ -z "$computer_name" ]; then
    return 0
  fi

  for key in \
    'HKLM\System\CurrentControlSet\Control\ComputerName\ComputerName' \
    'HKLM\System\CurrentControlSet\Control\ComputerName\ActiveComputerName'
  do
    wine reg add "$key" /v ComputerName /t REG_SZ /d "$computer_name" /f >/dev/null
  done
  wine reg add 'HKLM\System\CurrentControlSet\Services\Tcpip\Parameters' /v Hostname /t REG_SZ /d "$computer_name" /f >/dev/null
  wine reg add 'HKLM\System\CurrentControlSet\Services\Tcpip\Parameters' /v "NV Hostname" /t REG_SZ /d "$computer_name" /f >/dev/null
}

copy_if_missing() {
  local src="$1"
  local dest="$2"

  if [ -f "$dest" ] || [ ! -f "$src" ]; then
    return 1
  fi

  mkdir -p "$(dirname "$dest")"
  cp -f "$src" "$dest"
  return 0
}

repair_wine_prefix_dlls() {
  local copied=0
  local src

  for src in \
    /opt/wine-stable/lib/wine/i386-windows/cryptbase.dll \
    /usr/lib/wine/i386-windows/cryptbase.dll \
    /usr/lib/i386-linux-gnu/wine/i386-windows/cryptbase.dll
  do
    if copy_if_missing "$src" "$WINEPREFIX/drive_c/windows/syswow64/cryptbase.dll"; then
      copied=1
      break
    fi
  done

  for src in \
    /opt/wine-stable/lib/wine/x86_64-windows/cryptbase.dll \
    /usr/lib/wine/x86_64-windows/cryptbase.dll \
    /usr/lib/x86_64-linux-gnu/wine/x86_64-windows/cryptbase.dll
  do
    if copy_if_missing "$src" "$WINEPREFIX/drive_c/windows/system32/cryptbase.dll"; then
      copied=1
      break
    fi
  done

  if [ "$copied" = "1" ]; then
    echo "Repaired missing Wine cryptbase.dll files in $WINEPREFIX"
  fi
}

install_wtsapi32_shim() {
  local source_c="${PROJECT_ROOT}/tools/wine-shims/wtsapi32_shim.c"
  local source_def="${PROJECT_ROOT}/tools/wine-shims/wtsapi32.def"
  local target="$WINEPREFIX/drive_c/windows/syswow64/wtsapi32.dll"
  local build_dir

  if [ ! -f "$source_c" ] || [ ! -f "$source_def" ]; then
    return 0
  fi
  if ! command_exists i686-w64-mingw32-gcc; then
    echo "i686-w64-mingw32-gcc not found; skipping WTSAPI32 Wine shim." >&2
    return 0
  fi

  mkdir -p "$(dirname "$target")"
  build_dir="$(mktemp -d)"
  i686-w64-mingw32-gcc -shared -o "$build_dir/wtsapi32.dll" "$source_c" "$source_def" -Wl,--kill-at
  cp -f "$build_dir/wtsapi32.dll" "$target"
  chmod 644 "$target" 2>/dev/null || true
  rm -rf "$build_dir"
  echo "Installed Wine WTSAPI32 shim: $target"
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

enabled_env() {
  case "${1:-0}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

log_says_agent_already_running() {
  local log_path="${1:-}"
  if [ ! -f "$log_path" ]; then
    return 1
  fi
  python3 - "$log_path" <<'PY'
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes()
for encoding in ("utf-8", "cp932", "shift_jis"):
    try:
        text = raw.decode(encoding)
        break
    except UnicodeDecodeError:
        continue
else:
    text = raw.decode("utf-8", errors="replace")

lower = text.lower()
if "already" in lower or "すでに" in text:
    raise SystemExit(0)
raise SystemExit(1)
PY
}

bridge_target() {
  printf '%s\n' "$JVLINK_BRIDGE_EXE"
}

find_bridge_source() {
  local candidate
  local target

  target="$(bridge_target)"
  if [ -n "${JVLINK_BRIDGE_SOURCE_EXE:-}" ] && [ -f "$JVLINK_BRIDGE_SOURCE_EXE" ]; then
    printf '%s\n' "$JVLINK_BRIDGE_SOURCE_EXE"
    return
  fi

  for candidate in \
    "${PROJECT_ROOT}/tools/jvlink-bridge/bin/native/JVLinkBridge.exe" \
    "${PROJECT_ROOT}/tools/jvlink-bridge/JVLinkBridge.exe" \
    "${INSTALLERS_DIR}/JVLinkBridge.exe" \
    "${INSTALLERS_DIR}/jvlink-bridge/JVLinkBridge.exe"
  do
    if [ -f "$candidate" ] && [ "$candidate" != "$target" ]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
}

build_bridge_if_possible() {
  local build_script="${PROJECT_ROOT}/scripts/build_jvlink_bridge_native.sh"

  if [ ! -x "$build_script" ]; then
    return 1
  fi
  if ! command_exists i686-w64-mingw32-gcc; then
    return 1
  fi

  echo "Building JVLinkBridge.exe with MinGW..."
  "$build_script"
}

install_jvlink_bridge() {
  local target
  local source

  target="$(bridge_target)"
  mkdir -p "$(dirname "$target")"

  if [ -f "$target" ]; then
    echo "JVLinkBridge.exe already installed: $target"
    return 0
  fi

  source="$(find_bridge_source)"
  if [ -n "$source" ]; then
    echo "Installing JVLinkBridge.exe: $source -> $target"
    cp -f "$source" "$target"
    chmod 755 "$target" 2>/dev/null || true
    return 0
  fi

  if build_bridge_if_possible; then
    if [ -f "$target" ]; then
      chmod 755 "$target" 2>/dev/null || true
      echo "JVLinkBridge.exe built: $target"
      return 0
    fi
    source="$(find_bridge_source)"
    if [ -n "$source" ]; then
      echo "Installing built JVLinkBridge.exe: $source -> $target"
      cp -f "$source" "$target"
      chmod 755 "$target" 2>/dev/null || true
      return 0
    fi
  fi

  cat >&2 <<EOF
JVLinkBridge.exe is not available.

Provide one of the following and rerun this script:
  - set JVLINK_BRIDGE_SOURCE_EXE=/path/to/JVLinkBridge.exe
  - place JVLinkBridge.exe at ${PROJECT_ROOT}/tools/jvlink-bridge/JVLinkBridge.exe
  - install gcc-mingw-w64-i686 so ${PROJECT_ROOT}/scripts/build_jvlink_bridge_native.sh can build it

Target path:
  $target
EOF

  if [ "${JVLINK_ALLOW_MISSING_BRIDGE:-0}" = "1" ]; then
    echo "JVLINK_ALLOW_MISSING_BRIDGE=1 is set; continuing without JVLinkBridge.exe." >&2
    return 0
  fi
  return 1
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

install_wine_gecko() {
  if ! enabled_env "${JVLINK_INSTALL_WINE_GECKO:-1}"; then
    return 0
  fi
  if ! command_exists curl; then
    echo "Skipping Wine Gecko install because curl is not available." >&2
    return 0
  fi

  local version="${JVLINK_WINE_GECKO_VERSION:-2.47.4}"
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/wine"
  local marker="$WINEPREFIX/.wine-gecko-${version}-x86.installed"
  local msi="$cache_dir/wine-gecko-${version}-x86.msi"
  local url="${JVLINK_WINE_GECKO_URL:-https://dl.winehq.org/wine/wine-gecko/${version}/wine-gecko-${version}-x86.msi}"

  if [ -f "$marker" ]; then
    return 0
  fi

  mkdir -p "$cache_dir"
  if [ ! -s "$msi" ]; then
    echo "Downloading Wine Gecko x86: $url"
    curl -L --fail --retry 3 -o "$msi" "$url"
  fi

  echo "Installing Wine Gecko x86 into prefix"
  if wine msiexec /i "$msi" /qn >/tmp/wine-gecko-install.log 2>&1; then
    wineserver -w || true
    touch "$marker"
  else
    echo "Wine Gecko install failed; HTML dialogs may not render. See /tmp/wine-gecko-install.log" >&2
    return 1
  fi
}

register_jvlink_agent_service() {
  local agent_path='C:\Program Files (x86)\JRA-VAN\Data Lab\JVLinkAgent.exe'
  local appid='{FC990E87-4D02-4C29-9367-B8D245F513F5}'
  local root

  if [ ! -f "$WINEPREFIX/drive_c/Program Files (x86)/JRA-VAN/Data Lab/JVLinkAgent.exe" ]; then
    return 0
  fi

  for root in 'HKLM\Software\Classes' 'HKCU\Software\Classes'; do
    wine_reg_add "$root\\AppID\\JVLinkAgent.EXE" /v AppID /t REG_SZ /d "$appid" /f || true
    wine_reg_add "$root\\AppID\\$appid" /ve /t REG_SZ /d JVLinkAgent /f || true
    wine_reg_add "$root\\AppID\\$appid" /v LocalService /t REG_SZ /d JVLinkAgent /f || true
    wine_reg_add "$root\\Typelib\\{C776BA35-EE5E-4B36-AB38-20734FF9C8A4}\\1.0" /ve /t REG_SZ /d 'JVLinkAgent 1.0 Type Library' /f || true
    wine_reg_add "$root\\Typelib\\{C776BA35-EE5E-4B36-AB38-20734FF9C8A4}\\1.0\\0\\win32" /ve /t REG_SZ /d "$agent_path" /f || true
    wine_reg_add "$root\\Typelib\\{C776BA35-EE5E-4B36-AB38-20734FF9C8A4}\\1.0\\FLAGS" /ve /t REG_SZ /d 8 /f || true
    wine_reg_add "$root\\Typelib\\{C776BA35-EE5E-4B36-AB38-20734FF9C8A4}\\1.0\\HELPDIR" /ve /t REG_SZ /d 'C:\Program Files (x86)\JRA-VAN\Data Lab' /f || true
  done

  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v DisplayName /t REG_SZ /d JVLinkAgent /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v ErrorControl /t REG_DWORD /d 1 /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v ImagePath /t REG_SZ /d "\"$agent_path\"" /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v ObjectName /t REG_SZ /d LocalSystem /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v PreshutdownTimeout /t REG_DWORD /d 180000 /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v Start /t REG_DWORD /d 2 /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v Type /t REG_DWORD /d 16 /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' /v WOW64 /t REG_DWORD /d 1 /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\Eventlog\Application\JVLinkAgent' /v EventMessageFile /t REG_EXPAND_SZ /d "$agent_path" /f
  wine_reg_add 'HKLM\System\CurrentControlSet\Services\Eventlog\Application\JVLinkAgent' /v TypesSupported /t REG_DWORD /d 7 /f
}

start_jvlink_agent_service() {
  if ! enabled_env "${JVLINK_START_AGENT:-1}"; then
    return 0
  fi
  if ! wine reg query 'HKLM\System\CurrentControlSet\Services\JVLinkAgent' >/dev/null 2>&1; then
    return 0
  fi

  echo "Starting JVLinkAgent service"
  wine net start JVLinkAgent >/tmp/jvlink-agent-start.log 2>&1 || {
    if log_says_agent_already_running /tmp/jvlink-agent-start.log; then
      echo "JVLinkAgent service is already running"
      return 0
    fi
    echo "JVLinkAgent service start failed; see /tmp/jvlink-agent-start.log" >&2
    return 1
  }
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
  if [ -f "$WINEPREFIX/drive_c/Program Files (x86)/JRA-VAN/Data Lab/MSFLXGRD.OCX" ]; then
    echo "Registering JV-Link support OCX: C:\\Program Files (x86)\\JRA-VAN\\Data Lab\\MSFLXGRD.OCX"
    wine regsvr32 /s 'C:\Program Files (x86)\JRA-VAN\Data Lab\MSFLXGRD.OCX'
  fi
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
import subprocess

from src.jvlink.bridge import JVLinkBridge

service_key = re.sub(r"[^A-Za-z0-9]", "", os.environ["JVLINK_SERVICE_KEY"])

registry_targets = [
    (r"HKLM\Software\JRA-VAN Data Lab.\uid_pass", "servicekey"),
    (r"HKLM\Software\WOW6432Node\JRA-VAN Data Lab.\uid_pass", "servicekey"),
    (r"HKCU\Software\JRA-VAN Data Lab.\uid_pass", "servicekey"),
    (r"HKLM\SOFTWARE\JRA-VAN\JV-Link", "ServiceKey"),
    (r"HKLM\SOFTWARE\WOW6432Node\JRA-VAN\JV-Link", "ServiceKey"),
    (r"HKCU\Software\JRA-VAN\JV-Link", "ServiceKey"),
]
uid_pass_targets = [
    r"HKLM\Software\JRA-VAN Data Lab.\uid_pass",
    r"HKLM\Software\WOW6432Node\JRA-VAN Data Lab.\uid_pass",
    r"HKCU\Software\JRA-VAN Data Lab.\uid_pass",
]

wineprefix = os.environ.get("WINEPREFIX") or os.environ.get("JVLINK_WINEPREFIX") or ""
marker = os.path.join(wineprefix, ".jvlink-service-key") if wineprefix else ""
previous = None
if marker and os.path.exists(marker):
    with open(marker, "r", encoding="utf-8") as handle:
        previous = handle.read().strip()
force_reset = os.environ.get("JVLINK_FORCE_RESET_REGISTRATION", "").lower() in {"1", "true", "yes", "on"}
reset_on_change = os.environ.get("JVLINK_RESET_REGISTRATION_ON_KEY_CHANGE", "1").lower() in {"1", "true", "yes", "on"}
should_reset = force_reset or (reset_on_change and previous is not None and previous != service_key)

bridge = JVLinkBridge()
try:
    if should_reset:
        for reg_path in uid_pass_targets:
            for value_name, value in (("ukey", ""), ("messagekey", "00000000000000")):
                subprocess.run(
                    ["wine", "reg", "add", reg_path, "/v", value_name, "/t", "REG_SZ", "/d", value, "/f"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        print("JV-Link registration state reset for service key change")
    code = bridge.jv_set_service_key(service_key)
    for reg_path, value_name in registry_targets:
        subprocess.run(
            ["wine", "reg", "add", reg_path, "/v", value_name, "/t", "REG_SZ", "/d", service_key, "/f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    print(f"JV-Link service key setup returned code={code}")
    if marker:
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(service_key)
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

  install_jvlink_bridge
  wine_boot
  install_wine_gecko

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
  register_jvlink_agent_service
  start_jvlink_agent_service
  configure_service_key_if_possible
}

manual_setup() {
  install_jvlink_bridge
  wine_boot
  install_wine_gecko

  if [ $# -gt 0 ]; then
    run_installer "$1"
  fi

  register_dll "$(detect_dll)"
  register_jvlink_agent_service
  start_jvlink_agent_service
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
  --bridge-only)
    install_jvlink_bridge
    ;;
  *)
    manual_setup "$@"
    ;;
esac
