#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test JV-Link initialization."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.jvlink.wrapper import JVLinkWrapper
from dotenv import load_dotenv
import os

def test_jvlink():
    """Test JV-Link connection."""
    load_dotenv()

    service_key = os.getenv("JVLINK_SERVICE_KEY")
    if not service_key:
        print("ERROR: JVLINK_SERVICE_KEY not found in .env file")
        return False

    print(f"Service Key: {service_key}")
    print("Attempting to initialize JV-Link...")

    try:
        jv = JVLinkWrapper(sid=service_key)
        print("OK - JVLinkWrapper created")

        # Try to initialize
        result = jv.jv_init()
        print(f"jv_init() returned: {result}")

        if result == 0:
            print("OK - JV-Link initialized successfully!")

            # Try to get status
            try:
                status = jv.jv_status()
                print(f"JV-Link status: {status}")
            except Exception as e:
                print(f"Status check error: {e}")

            return True
        else:
            print(f"ERROR - JV-Link initialization failed with code: {result}")
            return False

    except Exception as e:
        print(f"ERROR - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jvlink()
    sys.exit(0 if success else 1)
