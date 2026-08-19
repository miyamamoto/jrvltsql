"""JV-Link API interface.

Platform support:
- Windows (32-bit Python): direct COM via pywin32 (`JVLinkWrapper`)
- Windows (64-bit Python): `JVLinkBridge` subprocess
- Linux/Docker: `JVLinkBridge` subprocess through an external Wine runner
"""

import sys


def is_jvlink_available() -> bool:
    """Report whether a JV-Link transport can be used on this platform.

    Availability is transport-only: provider registration and subscription are
    established by `JVInit` / `JVOpen`, not by the presence of a transport.
    """
    if sys.platform == "win32":
        return True
    try:
        from src.jvlink.bridge import find_bridge_executable

        return find_bridge_executable() is not None
    except Exception:
        return False
