# PostgreSQL

jrvltsql can write directly to PostgreSQL for shared collection.

## Required Environment

```bat
set POSTGRES_HOST=<host>
set POSTGRES_PORT=5432
set POSTGRES_DATABASE=<database>
set POSTGRES_USER=<user>
set POSTGRES_PASSWORD=<password>
```

`POSTGRES_DB` is also accepted by some scripts as an alias for
`POSTGRES_DATABASE`.

## Quickstart

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

This loads race data and official one-year `TS_O1/TS_O2` odds into PostgreSQL.

## Daily Sync

```bat
daily_sync.bat --db postgresql --days-back 7 --days-forward 3
```

This keeps recent race cards, results, and related ordinary data current.

## SQLite Fallback

The example config defaults to SQLite. Use SQLite for local single-user work or
when PostgreSQL is not available.
