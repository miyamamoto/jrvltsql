#!/usr/bin/env python
"""Drop all tables in the keiba PostgreSQL database (debug helper)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.postgresql_handler import PostgreSQLDatabase

db = PostgreSQLDatabase({
    "host": "localhost", "port": 5432, "database": "keiba",
    "user": "postgres", "password": "postgres",
})
db.connect()
rows = db.fetch_all(
    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
)
for row in rows:
    name = row["table_name"]
    db.execute(f'DROP TABLE IF EXISTS "{name}" CASCADE')
    print(f"dropped {name}")
db.disconnect()
print(f"done: {len(rows)} tables dropped")
