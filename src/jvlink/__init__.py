"""JV-Link API interface.

Platform support:
- Windows (32-bit Python): Direct COM via pywin32 (JVLinkWrapper)
- Windows (64-bit Python): JVLinkBridge subprocess
- Linux/Docker: JVLinkBridge subprocess via Wine
"""

import sys


def is_jvlink_available() -> bool:
    """Check if JV-Link COM operations are available on this platform."""
    if sys.platform == "win32":
        return True
    try:
        from src.jvlink.bridge import find_bridge_executable

        return find_bridge_executable() is not None
    except Exception:
        return False
