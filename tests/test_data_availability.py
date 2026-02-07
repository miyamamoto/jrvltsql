#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test data availability for various periods and specs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.jvlink.wrapper import JVLinkWrapper
from src.jvlink.constants import *
from dotenv import load_dotenv
import os

def test_data_availability():
    """Test which periods and specs have data."""
    load_dotenv()

    sid = os.getenv("JVLINK_SID", "JLTSQL")
    print(f"Using SID: {sid}\n")

    # Test different periods (YYYYMMDD format)
    test_periods = [
        ("20241101", "2024-11-01 (November 2024)"),
        ("20241001", "2024-10-01 (October 2024)"),
        ("20240601", "2024-06-01 (June 2024)"),
        ("20240101", "2024-01-01 (January 2024)"),
        ("20231201", "2023-12-01 (December 2023)"),
    ]

    # Test different data specs
    test_specs = [
        ("RACE", "Race data (RA, SE, HR, WF, JG)"),
        ("DIFF", "Master data (UM, KS, CH, BR, BN, etc.)"),
        ("YSCH", "Schedule data"),
        ("SNAP", "Race card data"),
    ]

    print("=" * 80)
    print("JV-Link Data Availability Test")
    print("=" * 80)

    jv = JVLinkWrapper(sid=sid)

    try:
        # Initialize
        result = jv.jv_init()
        if result != 0:
            print(f"ERROR: JV-Link initialization failed: {result}")
            return

        print("OK - JV-Link initialized successfully\n")

        # Test each combination
        for from_date, period_desc in test_periods:
            print(f"\nTesting period: {period_desc}")
            print("-" * 60)

            for data_spec, spec_desc in test_specs:
                fromtime = f"{from_date}000000"  # YYYYMMDDHHMMSS

                try:
                    result_code, read_count, download_count, last_timestamp = jv.jv_open(
                        data_spec=data_spec,
                        fromtime=fromtime,
                        option=0  # Normal mode
                    )

                    if result_code == 0:
                        # Data available
                        print(f"  [{data_spec:6s}] SUCCESS - read:{read_count:5d}, download:{download_count:5d}")
                        if read_count > 0:
                            print(f"           ^-- DATA FOUND! This period has data!")
                            return True  # Found data!
                    elif result_code == -1:
                        # No new data
                        print(f"  [{data_spec:6s}] No new data since {from_date}")
                    else:
                        # Error
                        print(f"  [{data_spec:6s}] ERROR: code {result_code}")

                    # Close stream
                    try:
                        jv.jv_close()
                    except Exception:
                        pass

                except Exception as e:
                    print(f"  [{data_spec:6s}] EXCEPTION: {e}")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("Test completed - check results above")
    print("=" * 80)

    return False

if __name__ == "__main__":
    found = test_data_availability()
    sys.exit(0 if found else 1)
