#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test SE record import (with digit-starting column names)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.database.sqlite_handler import SQLiteDatabase
from src.database.schema import SchemaManager
from src.importer.importer import DataImporter
from dotenv import load_dotenv
import os

def test_se_record():
    """Test importing SE record with digit-starting columns."""
    load_dotenv()

    sid = os.getenv("JVLINK_SID", "JLTSQL")
    print(f"Using SID: {sid}\n")

    jv = JVLinkWrapper(sid=sid)
    factory = ParserFactory()

    try:
        result = jv.jv_init()
        if result != 0:
            print(f"ERROR: JV-Link initialization failed: {result}")
            return False

        print("OK - JV-Link initialized\n")

        # Open stream for RACE data
        result_code, read_count, download_count, last_timestamp = jv.jv_open(
            data_spec="RACE",
            fromtime="20240101000000",
            option=1
        )

        print(f"JVOpen result: code={result_code}, read={read_count}\n")

        # Read records until we find an SE record
        se_found = False
        for i in range(100):  # Try up to 100 records
            result_code, data_bytes, filename = jv.jv_read()

            if result_code <= 0:
                print(f"No more data: code={result_code}")
                break

            data_str = data_bytes.decode('shift_jis')
            rec_type = data_str[:2]

            if rec_type == 'SE':
                print(f"Found SE record! (record #{i+1})")
                print(f"First 150 chars: {data_str[:150]}\n")

                # Parse record
                print("Parsing SE record...")
                record = factory.parse(data_bytes)
                print(f"Parsed {len(record)} fields")

                # Check for digit-starting columns
                digit_cols = [k for k in record.keys() if k and k[0].isdigit()]
                print(f"Found {len(digit_cols)} digit-starting columns: {digit_cols[:5]}...\n")

                # Setup database
                print("Setting up database...")
                db_path = Path("data/test_se.db")
                if db_path.exists():
                    db_path.unlink()

                database = SQLiteDatabase({"path": str(db_path)})
                with database:
                    schema_mgr = SchemaManager(database)
                    schema_mgr.create_all_tables()
                    print("OK - Tables created\n")

                    # Import the SE record
                    print("Importing SE record...")
                    importer = DataImporter(database)
                    success = importer.import_single_record(record)

                    if success:
                        print("✓ SUCCESS - SE record imported!")

                        # Verify
                        rows = database.fetch_all("SELECT COUNT(*) as cnt FROM NL_SE")
                        count = rows[0]['cnt'] if rows else 0
                        print(f"NL_SE table now has {count} record(s)\n")

                        se_found = True
                        break
                    else:
                        print("✗ FAILED - SE record import failed")
                        stats = importer.get_statistics()
                        print(f"Stats: {stats}")
                        return False

        if not se_found:
            print("No SE record found in first 100 records")
            return False

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            jv.jv_close()
        except:
            pass

if __name__ == "__main__":
    success = test_se_record()
    sys.exit(0 if success else 1)
