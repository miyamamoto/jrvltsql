# Linux/Wine JV-Link setup

`jrvltsql` can run JRA-VAN DataLab access on Linux through Wine and
`JVLinkBridge.exe`.

## Install JVLinkBridge.exe

If a private repository stores the bridge binary, place it at:

```bash
tools/jvlink-bridge/JVLinkBridge.exe
```

Then install it to the runtime path:

```bash
scripts/setup_wine_jvlink.sh --bridge-only
```

You can also pass an explicit source and target:

```bash
JVLINK_BRIDGE_SOURCE_EXE=/secure/JVLinkBridge.exe \
JVLINK_BRIDGE_EXE=/opt/jvlink-bridge/JVLinkBridge.exe \
scripts/setup_wine_jvlink.sh --bridge-only
```

If `gcc-mingw-w64-i686` is installed, the script can build the native bridge
from `tools/jvlink-bridge/bridge_native.c` by running
`scripts/build_jvlink_bridge_native.sh`.

## Install JV-Link into Wine

Place the JV-Link installer under `jvlink-installers/` or set
`JVLINK_INSTALLER`, then run:

```bash
JVLINK_SERVICE_KEY=... \
JVLINK_SET_SERVICE_KEY=1 \
scripts/setup_wine_jvlink.sh --auto
```

`JVLINK_SET_SERVICE_KEY=1` is required before the script writes the service key
into the Wine registry. Without it, the script installs/registers JV-Link but
leaves the key unchanged.

JRA-VAN DataLab is licensed per machine. Keep validation on the licensed host
and reuse the same `JVLINK_WINEPREFIX`; recreating or moving the prefix to a
different machine can invalidate downloads for that environment. Do not set
`JVLINK_SET_SERVICE_KEY=1` during routine runs unless the license must be
registered on that exact host/prefix.

Important environment variables:

```bash
JVLINK_BRIDGE_EXE=/path/to/JVLinkBridge.exe
JVLINK_WINE=wine
JVLINK_WINEPREFIX=$HOME/.wine-jvlink
JVLINK_WINEARCH=win64
JVLINK_AUTO_CLOSE_DIALOGS=1
JVLINK_SAVE_PATH_WIN='C:\ProgramData\JRA-VAN\Data Lab'
JRVLTSQL_POSTGRES_URL=postgresql://user:pass@host:5432/database
```

`JVLINK_AUTO_CLOSE_DIALOGS=1` is the default on Wine when `xdotool` and
`DISPLAY` are available. It closes the recurring `JRA-VANからのお知らせ`
dialog so headless `JVOpen` / `JVRTOpen` calls do not hang. Set
`JVLINK_AUTO_CLOSE_DIALOGS=0` when operating the JV-Link GUI manually.

If `JVOpen` / `JVRTOpen` returns `-301`, the COM bridge is working but
JRA-VAN authentication failed. Check that the licensed machine and
`JVLINK_WINEPREFIX` are the intended ones, and that the service key was
registered on that exact prefix. Because DataLab is licensed per machine,
do not keep retrying from a different host.
