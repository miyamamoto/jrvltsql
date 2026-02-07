#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test setup download to get initial data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.jvlink.wrapper import JVLinkWrapper
from dotenv import load_dotenv
import os

def test_setup_download():
    """Test setup download (option=1) to get initial data."""
    load_dotenv()

    sid = os.getenv("JVLINK_SID", "JLTSQL")
    print(f"Using SID: {sid}\n")

    print("=" * 80)
    print("JV-Link Setup Download Test (option=1)")
    print("=" * 80)
    print("\nThis will download initial data from JRA-VAN servers.")
    print("Testing with recent period and small data spec first...\n")

    jv = JVLinkWrapper(sid=sid)

    try:
        # Initialize
        result = jv.jv_init()
        if result != 0:
            print(f"ERROR: JV-Link initialization failed: {result}")
            return False

        print("OK - JV-Link initialized successfully\n")

        # Test configurations (recent period, smaller data specs first)
        test_configs = [
            # (data_spec, fromtime, option, description)
            ("YSCH", "20241001000000", 1, "Schedule data - October 2024 (SETUP)"),
            ("RACE", "20241001000000", 1, "Race data - October 2024 (SETUP)"),
            ("DIFF", "20241001000000", 1, "Master data - October 2024 (SETUP)"),
        ]

        for data_spec, fromtime, option, description in test_configs:
            print(f"\nTesting: {description}")
            print("-" * 60)
            print(f"  Data spec: {data_spec}")
            print(f"  From time: {fromtime}")
            print(f"  Option:    {option} ({'SETUP' if option == 1 else 'NORMAL'})")

            try:
                result_code, read_count, download_count, last_timestamp = jv.jv_open(
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option
                )

                print(f"\n  Result:")
                print(f"    Code:      {result_code}")
                print(f"    Read:      {read_count}")
                print(f"    Download:  {download_count}")
                print(f"    Timestamp: {last_timestamp}")

                if result_code == 0 and (read_count > 0 or download_count > 0):
                    print(f"\n  >>> SUCCESS! Data available!")
                    print(f"  >>> Read count: {read_count}, Download count: {download_count}")

                    # Try to read first few records
                    print(f"\n  Attempting to read first 5 records...")
                    for i in range(5):
                        try:
                            result_code, data_bytes, filename = jv.jv_read()
                            if result_code > 0:
                                # Successfully read data
                                data_str = data_bytes.decode('cp932', errors='ignore') if data_bytes else ''
                                preview = data_str[:80] + "..." if len(data_str) > 80 else data_str
                                print(f"    Record {i+1}: [{result_code} bytes] {preview}")
                            elif result_code == 0:
                                print(f"    End of data (read {i} records)")
                                break
                            elif result_code == -1:
                                print(f"    File switch, continuing...")
                                continue
                            else:
                                print(f"    Read error: {result_code}")
                                break
                        except Exception as e:
                            print(f"    Read exception: {e}")
                            import traceback
                            traceback.print_exc()
                            break

                    # Close stream
                    jv.jv_close()
                    print(f"\n  Stream closed.")
                    return True  # Success!

                elif result_code == -1:
                    print(f"  No new data available")
                else:
                    print(f"  ERROR or no data: code {result_code}")

                # Close stream
                try:
                    jv.jv_close()
                except Exception:
                    pass

            except Exception as e:
                print(f"  EXCEPTION: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

    return False

if __name__ == "__main__":
    success = test_setup_download()
    sys.exit(0 if success else 1)
