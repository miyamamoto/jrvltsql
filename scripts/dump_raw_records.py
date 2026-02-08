#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dump raw record bytes from NV-Link/JV-Link for format analysis.

This script fetches records and saves raw bytes to files for offline analysis.
Must be run in GUI context (VNC) on Windows with NV-Link installed.

Usage (on A6 via VNC):
    venv32\\Scripts\\python.exe scripts/dump_raw_records.py --source nar --spec RACE --from 20260207 --to 20260208
    venv32\\Scripts\\python.exe scripts/dump_raw_records.py --source nar --spec DIFN --from 20260207 --to 20260208
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def dump_records(source: str, spec: str, from_date: str, to_date: str, output_dir: str):
    """Fetch and dump raw record bytes."""
    os.makedirs(output_dir, exist_ok=True)

    if source == "nar":
        from src.nvlink.wrapper import NVLinkWrapper
        wrapper = NVLinkWrapper(sid="DUMP")
        wrapper.set_service_key("L5KJ-C55Y-7B6U-YJYK-R")
        result = wrapper.nv_open(spec, from_date + "000000", 2)
        print(f"NVOpen result: {result}")
    else:
        import win32com.client
        jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
        jvlink.JVSetServiceKey("0UJC-VRFM-34A0-23PH-4")
        result = jvlink.JVOpen(spec, from_date + "000000", 2, 0, 0, "")
        print(f"JVOpen result: {result}")

    counts = {}
    record_num = 0

    while True:
        if source == "nar":
            ret, buff, filename = wrapper.nv_read()
        else:
            nv_result = jvlink.JVRead("", 50000, "")
            ret = nv_result[0]
            if ret > 0:
                buff_str = nv_result[1]
                try:
                    buff = buff_str.encode('latin-1')
                except:
                    buff = buff_str.encode('cp932', errors='replace')
                filename = nv_result[3] if len(nv_result) > 3 else ""
            else:
                buff = None
                filename = None

        if ret == 0 or ret == -1:
            if ret == 0:
                break
            continue  # file switch
        elif ret < 0:
            print(f"Error: {ret}")
            break

        record_type = buff[:2].decode('ascii', errors='replace')
        counts[record_type] = counts.get(record_type, 0) + 1
        count = counts[record_type]

        # Save first 5 records of each type
        if count <= 5:
            fname = os.path.join(output_dir, f"{source}_{record_type}_{count:03d}.bin")
            with open(fname, 'wb') as f:
                f.write(buff)
            print(f"Saved {fname} ({len(buff)} bytes)")

        record_num += 1
        if record_num % 100 == 0:
            print(f"  Processed {record_num} records...")

    if source == "nar":
        wrapper.nv_close()
    else:
        jvlink.JVClose()

    print(f"\nTotal records: {record_num}")
    print(f"By type: {counts}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump raw record bytes")
    parser.add_argument("--source", choices=["jra", "nar"], required=True)
    parser.add_argument("--spec", required=True, help="Data spec (RACE, DIFN, etc.)")
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--output", default="data/raw_dumps", help="Output directory")
    args = parser.parse_args()
    dump_records(args.source, args.spec, args.from_date, args.to_date, args.output)
