#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test JV-Link with simple SID."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.jvlink.wrapper import JVLinkWrapper

def test_various_sids():
    """Test with various SID formats."""
    test_sids = [
        "JLTSQL",
        "TEST",
        "MyApp",
        " JLTSQL",  # With leading space (should fail with -103)
        "1UJC-VRFM-24YD-K2W4-4",  # Full service key (current)
    ]

    for sid in test_sids:
        print(f"\nTesting SID: '{sid}' (len={len(sid)})")
        print(f"First char: '{sid[0]}' (ord={ord(sid[0])})")

        try:
            jv = JVLinkWrapper(sid=sid)
            result = jv.jv_init()

            if result == 0:
                print(f"  -> SUCCESS! JV-Link initialized with SID='{sid}'")
                return True
            else:
                print(f"  -> FAILED with code: {result}")

        except Exception as e:
            print(f"  -> ERROR: {e}")

    return False

if __name__ == "__main__":
    success = test_various_sids()
    sys.exit(0 if success else 1)
