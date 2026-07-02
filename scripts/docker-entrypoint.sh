#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export LANG="${LANG:-ja_JP.UTF-8}"
export LC_ALL="${LC_ALL:-ja_JP.UTF-8}"
export WINEPREFIX="${WINEPREFIX:-/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
export JVLINK_WINEPREFIX="${JVLINK_WINEPREFIX:-$WINEPREFIX}"
export JVLINK_WINEARCH="${JVLINK_WINEARCH:-$WINEARCH}"
export JVLINK_BRIDGE_EXE="${JVLINK_BRIDGE_EXE:-/opt/jvlink-bridge/JVLinkBridge.exe}"
export JVLINK_INSTALLERS_DIR="${JVLINK_INSTALLERS_DIR:-/installers}"
export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-wtsapi32=n,b}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "${WINEPREFIX}" "${JVLINK_INSTALLERS_DIR}" /app/data/cache /app/logs /opt/jvlink-bridge
    chown -R jra:jra "${WINEPREFIX}" /app/data /app/logs /opt/jvlink-bridge 2>/tmp/jrvltsql-chown.log || true
    chmod -R ug+rwX /app/data /app/logs 2>/tmp/jrvltsql-chmod.log || true
    exec gosu jra "$0" "$@"
fi

mkdir -p "${WINEPREFIX}" /app/data/cache /app/logs /opt/jvlink-bridge

start_desktop() {
    if [ "${START_XVFB:-1}" != "1" ]; then
        return
    fi

    local screen="${VNC_RESOLUTION:-1280x800}x24"
    local vnc_port="${VNC_PORT:-5900}"
    local novnc_port="${NOVNC_PORT:-6080}"

    Xvfb "${DISPLAY}" -screen 0 "${screen}" -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &
    sleep 0.5
    fluxbox >/tmp/fluxbox.log 2>&1 &
    x11vnc -display "${DISPLAY}" -forever -shared -rfbport "${vnc_port}" -nopw -listen 0.0.0.0 -o /tmp/x11vnc.log -bg >/tmp/x11vnc-start.log 2>&1
    websockify --web=/usr/share/novnc/ "${novnc_port}" "localhost:${vnc_port}" >/tmp/novnc.log 2>&1 &

    echo "[desktop] noVNC is listening on container port ${novnc_port}."
}

start_jvlink_terms_watcher() {
    case "${JVLINK_AUTO_ACCEPT_TERMS:-1}" in
        1|true|TRUE|yes|YES|on|ON) ;;
        *) return ;;
    esac
    if ! command -v xdotool >/dev/null 2>&1; then
        return
    fi

    (
        set +e
        interval="${JVLINK_DIALOG_WATCH_INTERVAL_SECONDS:-1.0}"
        while true; do
            for win in $(xdotool search --onlyvisible --name "ご注意事項" 2>/dev/null || true); do
                xdotool windowactivate --sync "$win" 2>/dev/null || true
                xdotool mousemove --window "$win" 360 266 click 1 2>/dev/null || true
                sleep 1.5
                for ie in $(xdotool search --onlyvisible --name "Wine Internet Explorer" 2>/dev/null || true); do
                    xdotool windowclose "$ie" 2>/dev/null || true
                done
                sleep 0.2
                xdotool windowactivate --sync "$win" 2>/dev/null || true
                xdotool mousemove --window "$win" 306 310 click 1 2>/dev/null || true
                sleep 0.2
                xdotool mousemove --window "$win" 279 373 click 1 2>/dev/null || true
                echo "[jvlink-terms-watcher] accepted terms dialog"
            done
            for win in $(xdotool search --onlyvisible --name "セットアップ" 2>/dev/null || true); do
                xdotool windowactivate --sync "$win" 2>/dev/null || true
                xdotool mousemove --window "$win" 50 146 click 1 2>/dev/null || true
                sleep 0.2
                xdotool mousemove --window "$win" 273 259 click 1 2>/dev/null || true
                echo "[jvlink-terms-watcher] accepted setup dialog"
            done
            sleep "$interval"
        done
    ) >/tmp/jvlink-terms-watcher.log 2>&1 &
}

start_desktop
start_jvlink_terms_watcher

if [ "${AUTO_SETUP_JVLINK:-1}" = "1" ]; then
    if ! /app/scripts/setup_wine_jvlink.sh --auto; then
        if [ "${REQUIRE_JVLINK_INSTALL:-0}" = "1" ]; then
            echo "[entrypoint] JV-Link setup failed and REQUIRE_JVLINK_INSTALL=1." >&2
            exit 1
        fi
        echo "[entrypoint] JV-Link setup failed; continuing because REQUIRE_JVLINK_INSTALL!=1." >&2
    fi
fi

if [ "$#" -eq 0 ]; then
    set -- python /app/scripts/collector_service.py --kind jra --host 0.0.0.0 --port "${JRA_COLLECTOR_SERVICE_PORT:-8081}"
fi

exec "$@"
