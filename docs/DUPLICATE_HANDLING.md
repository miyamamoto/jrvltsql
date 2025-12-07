# Duplicate Handling in JLTSQL

## Current Status

As of now, the JLTSQL database schema uses `INSERT OR REPLACE` for all imports but **does NOT have PRIMARY KEY constraints** defined on tables. This means:

- ✅ The importer uses INSERT OR REPLACE by default
- ❌ Without PRIMARY KEYs, duplicates CAN still be created
- ⚠️ Re-running quickstart.py with option=1 may insert duplicate records

## How INSERT OR REPLACE Works

In SQLite, `INSERT OR REPLACE` behavior depends on PRIMARY KEY or UNIQUE constraints:

### With PRIMARY KEY (Recommended)
```sql
CREATE TABLE NL_RA (
    Year INTEGER,
    MonthDay INTEGER,
    JyoCD TEXT,
    Kaiji INTEGER,
    Nichiji INTEGER,
    RaceNum INTEGER,
    -- other columns...
    PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
);
```
- INSERT OR REPLACE will **update** existing records with the same key
- Safe to re-run imports multiple times
- No duplicates created

### Without PRIMARY KEY (Current State)
```sql
CREATE TABLE NL_RA (
    Year INTEGER,
    MonthDay INTEGER,
    JyoCD TEXT,
    Kaiji INTEGER,
    Nichiji INTEGER,
    RaceNum INTEGER
    -- No PRIMARY KEY defined
);
```
- INSERT OR REPLACE behaves like regular INSERT
- **May create duplicate records** when re-importing
- Each import adds new rows

## Recommended Primary Keys

Based on JV-Data specification, here are recommended composite primary keys:

| Table | Primary Key Columns | Description |
|-------|-------------------|-------------|
| NL_RA | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum | Race Details |
| NL_SE | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban | Horse Race Results |
| NL_HR | Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum | Payout Info |
| NL_UM | KettoNum | Horse Master (by registration number) |
| NL_KS | KisyuCode | Jockey Master (by jockey code) |
| NL_CH | ChokyosiCode | Trainer Master (by trainer code) |
| NL_BR | BreederName_Co | Breeder Master |
| NL_BN | BanusiName_Co | Owner Master |

## Solutions

### Option 1: Add PRIMARY KEY Constraints (Recommended)

Modify `src/database/schema.py` to add PRIMARY KEY constraints:

```python
"NL_RA": """
    CREATE TABLE IF NOT EXISTS NL_RA (
        RecordSpec TEXT,
        DataKubun TEXT,
        MakeDate TEXT,
        Year INTEGER NOT NULL,
        MonthDay INTEGER NOT NULL,
        JyoCD TEXT NOT NULL,
        Kaiji INTEGER NOT NULL,
        Nichiji INTEGER NOT NULL,
        RaceNum INTEGER NOT NULL,
        -- other columns...
        PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)
    )
"""
```

**Note**: SQLite requires dropping and recreating tables to add PRIMARY KEYs if data already exists.

### Option 2: Use UNIQUE Indexes (Alternative)

Create UNIQUE indexes instead of PRIMARY KEYs:

```python
# Add to src/database/indexes.py
UNIQUE_INDEXES = {
    "NL_RA": [
        "CREATE UNIQUE INDEX IF NOT EXISTS uniq_nl_ra_race ON NL_RA(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)"
    ],
    # ... more tables
}
```

Benefits:
- Can be added without dropping tables
- Similar behavior to PRIMARY KEY for INSERT OR REPLACE
- Easier to implement on existing databases

### Option 3: Deduplication Query (Workaround)

If you've already imported duplicate data:

```sql
-- Example: Remove duplicates from NL_RA
DELETE FROM NL_RA
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM NL_RA
    GROUP BY Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
);
```

## Implementation Status

### ✅ Completed
- Modified `BaseDatabase.insert()` to use INSERT OR REPLACE by default
- Modified `BaseDatabase.insert_many()` to use INSERT OR REPLACE by default
- Added documentation in importer.py
- Added comprehensive documentation in schema.py

### ⚠️ Pending
- PRIMARY KEY constraints not yet added to tables
- UNIQUE indexes not yet created
- Migration script not provided

## Next Steps

1. **For New Databases**: Add PRIMARY KEY constraints to schema.py before creating tables
2. **For Existing Databases**: Use Option 2 (UNIQUE indexes) or recreate tables with PRIMARY KEYs
3. **For Duplicates**: Run deduplication queries to clean existing data

## Testing

To verify duplicate handling:

```python
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter

# Test with small dataset
db = SQLiteDatabase({"path": "./test.db"})
with db:
    importer = DataImporter(db)

    # Import once
    stats1 = importer.import_records(records)

    # Import again (should not create duplicates if PKs are set)
    stats2 = importer.import_records(records)

    # Check record count
    count = db.fetch_one("SELECT COUNT(*) as cnt FROM NL_RA")
    print(f"Total records: {count['cnt']}")
```

## References

- SQLite INSERT documentation: https://www.sqlite.org/lang_insert.html
- JV-Data specification: 公式JV-Data仕様書 Ver.4.9.0.1
