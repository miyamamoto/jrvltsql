#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check February database contents."""

import sqlite3
from pathlib import Path

db_path = Path("data/test_202402.db")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

print(f"Database: {db_path}")
print(f"Size: {db_path.stat().st_size / 1024:.1f} KB\n")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    print(f"Total tables: {len(tables)}\n")

    print("Tables with data:")
    print("-" * 60)

    total_records = 0
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  {table_name:20s}: {count:8,} records")
                total_records += count

                # Show sample record
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                print(f"      Columns: {len(columns)}")
        except Exception as e:
            print(f"  {table_name:20s}: ERROR - {e}")

    print("-" * 60)
    print(f"Total records: {total_records:,}\n")

    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
