"""JV-Link API interface.

Platform support:
- Windows (32-bit Python): Direct COM via pywin32 (JVLinkWrapper)
- Windows (64-bit Python): C# bridge subprocess (JVLinkBridge)
- Linux/Docker: Not available (JV-Link COM requires Windows)
"""

import sys


def is_jvlink_available() -> bool:
    """Check if JV-Link COM operations are available on this platform."""
    return sys.platform == "win32"
