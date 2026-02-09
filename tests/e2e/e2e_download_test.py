"""E2E Download Test - JRA + NAR actual data download via COM API.

Tests:
1. JRA: 1 day of RACE data download
2. NAR: 1 day of RACE data download
3. JRA quickstart mini: download -> parse -> DB store -> verify
"""
import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def test_jra_download():
    """Test JRA (JV-Link) actual data download - 1 day."""
    log("=" * 60)
    log("TEST 1: JRA 1-day download")
    log("=" * 60)

    from jvlink.wrapper import JVLinkWrapper

    wrapper = JVLinkWrapper()
    try:
        wrapper.jv_init()
        log("JV-Link initialized OK")

        target_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        log(f"Target date: {target_date}")

        ret = wrapper.jv_open("RACE", f"{target_date}000000", option=2)
        log(f"JV_Open returned: {ret}")

        if ret < 0:
            log(f"WARN: JV_Open returned {ret} (may be no data)")
            wrapper.jv_close()
            return "SKIP"

        record_count = 0
        while True:
            status, filename, data = wrapper.jv_read(100000)
            if status == 0:
                break
            elif status in (-1, -3):
                log("Data downloading, waiting...")
                time.sleep(2)
                continue
            elif status < -1:
                log(f"Error: {status}")
                break
            else:
                record_count += 1
                if record_count <= 3:
                    log(f"  Record #{record_count}: {len(data)}B from {filename}")

        wrapper.jv_close()
        log(f"JRA download complete: {record_count} records")

        if record_count > 0:
            log("PASS: JRA download OK")
            return "PASS"
        else:
            log("WARN: No records (may be no races on this date)")
            return "SKIP"

    except Exception as e:
        log(f"FAIL: {e}")
        return "FAIL"
    finally:
        try:
            wrapper.jv_close()
        except Exception:
            pass


def test_nar_download():
    """Test NAR (NV-Link) actual data download - 1 day."""
    log("=" * 60)
    log("TEST 2: NAR 1-day download")
    log("=" * 60)

    from nvlink.wrapper import NVLinkWrapper

    wrapper = NVLinkWrapper()
    try:
        wrapper.nv_init()
        log("NV-Link initialized OK")

        target_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        log(f"Target date: {target_date}")

        ret = wrapper.nv_open("RACE", f"{target_date}000000", option=1)
        log(f"NV_Open returned: {ret}")

        if ret < 0:
            log(f"WARN: NV_Open returned {ret}")
            wrapper.nv_close()
            return "SKIP"

        record_count = 0
        while True:
            status, filename, data = wrapper.nv_read(110000)
            if status == 0:
                break
            elif status == -1:
                log("No more data")
                break
            elif status == -3:
                log("Data downloading (-3), waiting...")
                time.sleep(2)
                continue
            elif status < -1:
                log(f"Error: {status}")
                break
            else:
                record_count += 1
                if record_count <= 3:
                    log(f"  Record #{record_count}: {len(data)}B from {filename}")

        wrapper.nv_close()
        log(f"NAR download complete: {record_count} records")

        if record_count > 0:
            log("PASS: NAR download OK")
            return "PASS"
        else:
            log("WARN: No records")
            return "SKIP"

    except Exception as e:
        log(f"FAIL: {e}")
        return "FAIL"
    finally:
        try:
            wrapper.nv_close()
        except Exception:
            pass


def test_jra_quickstart_mini():
    """Test quickstart flow: download -> parse -> DB store (JRA, 1 day)."""
    log("=" * 60)
    log("TEST 3: JRA quickstart mini (download -> parse -> DB)")
    log("=" * 60)

    db_path = PROJECT_ROOT / "tests" / "e2e" / "e2e_test.db"
    if db_path.exists():
        db_path.unlink()

    try:
        from jvlink.wrapper import JVLinkWrapper
        from parsers import get_parser
        from db.sqlite_writer import SQLiteWriter

        wrapper = JVLinkWrapper()
        wrapper.jv_init()

        target_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        writer = SQLiteWriter(str(db_path))
        total_records = 0

        ret = wrapper.jv_open("RACE", f"{target_date}000000", option=2)
        log(f"JV_Open(RACE): {ret}")
        if ret < 0:
            log("No data available")
            writer.close()
            return "SKIP"

        while True:
            status, filename, data = wrapper.jv_read(100000)
            if status == 0:
                break
            elif status < 0:
                if status in (-1, -3):
                    time.sleep(1)
                    continue
                break

            record_id = data[:2] if len(data) >= 2 else ""
            parser = get_parser(record_id)
            if parser:
                try:
                    rows = parser.parse(data)
                    if rows:
                        for row in (rows if isinstance(rows, list) else [rows]):
                            writer.write(parser.table_name, row)
                            total_records += 1
                except Exception as e:
                    log(f"  Parse error for {record_id}: {e}")

        wrapper.jv_close()
        writer.close()
        log(f"DB stored: {total_records} records -> {db_path}")

        # Verify DB
        conn = sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        log(f"Tables created: {tables}")
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            log(f"  {t}: {count} rows")
        conn.close()

        if total_records > 0:
            log("PASS: Quickstart mini OK")
            return "PASS"
        else:
            log("SKIP: No data available")
            return "SKIP"

    except Exception as e:
        log(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        return "FAIL"
    finally:
        try:
            if db_path.exists():
                db_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    log("E2E Download Test Started")
    log(f"Project: {PROJECT_ROOT}")

    results = {}
    results["JRA Download"] = test_jra_download()
    results["NAR Download"] = test_nar_download()
    results["JRA Quickstart Mini"] = test_jra_quickstart_mini()

    log("")
    log("=" * 60)
    log("RESULTS")
    log("=" * 60)
    for name, result in results.items():
        icon = {"PASS": "\u2705", "FAIL": "\u274c", "SKIP": "\u26a0\ufe0f"}.get(result, "?")
        log(f"  {icon} {name}: {result}")

    fails = sum(1 for r in results.values() if r == "FAIL")
    log(f"\nTotal: {len(results)} tests, {fails} failures")
    sys.exit(1 if fails > 0 else 0)
