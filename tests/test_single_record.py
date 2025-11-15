#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test single record parsing and import."""

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

def test_single_record():
    """Test parsing and importing a single record."""
    load_dotenv()

    sid = os.getenv("JVLINK_SID", "JLTSQL")
    print(f"Using SID: {sid}\n")

    # Initialize JV-Link
    jv = JVLinkWrapper(sid=sid)
    factory = ParserFactory()

    try:
        result = jv.jv_init()
        if result != 0:
            print(f"ERROR: JV-Link initialization failed: {result}")
            return False

        print("OK - JV-Link initialized\n")

        # Open stream
        result_code, read_count, download_count, last_timestamp = jv.jv_open(
            data_spec="RACE",
            fromtime="20240101000000",
            option=1
        )

        print(f"JVOpen result: code={result_code}, read={read_count}, download={download_count}")

        # Read first record
        result_code, data_bytes, filename = jv.jv_read()

        if result_code > 0:
            print(f"\nRead {result_code} bytes of data")
            data_str = data_bytes.decode('shift_jis')
            print(f"Record type: {data_str[:2]}")
            print(f"First 100 chars: {data_str[:100]}\n")

            # Parse record
            print("Parsing record...")
            record = factory.parse(data_bytes)
            print(f"Parsed fields: {len(record)} fields")
            print(f"Keys (first 10): {list(record.keys())[:10]}")
            print(f"Values (first 10): {list(record.values())[:10]}")

            # Check for record type field
            rec_type_jp = record.get('レコード種別ID')
            rec_type_en = record.get('headRecordSpec')
            print(f"\nRecord type (Japanese): {rec_type_jp}")
            print(f"Record type (English): {rec_type_en}")

            # Setup database
            print("\nSetting up database...")
            db_path = Path("data/test_single.db")
            if db_path.exists():
                db_path.unlink()

            database = SQLiteDatabase({"path": str(db_path)})
            with database:
                schema_mgr = SchemaManager(database)
                schema_mgr.create_all_tables()
                print("OK - Tables created")

                # Try to import
                print("\nImporting record...")
                importer = DataImporter(database)
                success = importer.import_single_record(record)
                print(f"Import result: {success}")

                stats = importer.get_statistics()
                print(f"Import stats: {stats}")

                # Check tables
                for table_name in ["NL_RA_RACE", "NL_SE_RACE_UMA", "NL_HR_PAY"]:
                    rows = database.fetch_all(f"SELECT COUNT(*) as cnt FROM {table_name}")
                    count = rows[0]['cnt'] if rows else 0
                    print(f"{table_name}: {count} records")

            return True
        else:
            print(f"No data read: code={result_code}")
            return False

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
    success = test_single_record()
    sys.exit(0 if success else 1)
