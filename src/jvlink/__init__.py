"""JV-Link API interface.

Platform support:
- Windows (32-bit Python): Direct COM via pywin32 (JVLinkWrapper)
- Windows (64-bit Python): C# bridge subprocess (JVLinkBridge)
- Linux: Wine + JVLinkBridge.exe (via bridge.py)
"""

import sys


def is_jvlink_available() -> bool:
    """Check if direct COM (pywin32) is available.

    This checks for native Windows COM support only.
    For Wine-based bridge availability, use bridge.find_bridge_executable().
    """
    return sys.platform == "win32"
