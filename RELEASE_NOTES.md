# jrvltsql v1.4.0 Release Notes

## Highlights

### PostgreSQL time-series odds workflow

- Added `quickstart_postgres_timeseries.bat` for PostgreSQL race-data setup plus
  official `TS_O1/TS_O2` time-series odds ingestion.
- Added `fetch_timeseries_postgres.bat` for adding time-series odds to an
  existing PostgreSQL installation.
- Added `daily_sync.bat` for scheduled recent race-card/result synchronization.

### Expanded odds storage

- Expanded JRA-VAN time-series odds records into one row per ticket combination.
- Added direct storage of expanded `TS_O1` to `TS_O6` rows.
- Added multi-row PostgreSQL inserts for expanded time-series odds rows.

### Data correctness

- Fixed JRA-VAN time-series odds key generation.
- Normalized blank and unavailable odds placeholders before PostgreSQL writes.
- Updated tests so O1 to O6 expanded parser outputs are treated as `list[dict]`.

### Documentation cleanup

- Added current architecture, PostgreSQL, time-series odds, and scripts docs.
- Removed stale script README files.
- Replaced downstream-system-specific naming with collector-generic wording.

## Requirements

- Windows 10/11 for real JV-Link collection.
- Python 3.12.
- JRA-VAN DataLab and JV-Link.
- PostgreSQL is optional but required for shared time-series odds collection.

## Upgrade

```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

For PostgreSQL time-series odds setup:

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

For time-series-only backfill:

```bat
fetch_timeseries_postgres.bat 20250426 20260412
```
