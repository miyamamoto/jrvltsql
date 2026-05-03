# Scripts

This page lists the current operational scripts. Older script catalogues were
removed because they described non-current options.

| Script | Use |
| --- | --- |
| `quickstart.bat` | General Windows quickstart, SQLite-first. |
| `quickstart_postgres_timeseries.bat` | PostgreSQL setup/update plus official `TS_O1/TS_O2` odds. |
| `fetch_timeseries_postgres.bat` | Add official `TS_O1/TS_O2` odds to an existing PostgreSQL installation. |
| `daily_sync.bat` | Scheduled recent data sync. |
| `scripts/quickstart.py` | Python orchestration used by the batch wrappers. |
| `scripts/raceday_verify.py` | Race-day data health checks. |
| `tools/export_timeseries_csv.py` | Export stored time-series odds for inspection. |

For exact CLI options, run each script with `--help` where supported or use
`jltsql --help`.
