# Architecture

jrvltsql is a Windows collector for JRA-VAN DataLab. It stores JRA data in
SQLite or PostgreSQL and can optionally mirror data into a shared PostgreSQL
database for downstream analytics.

## Scope

- JRA only.
- Windows 10/11.
- JRA-VAN DataLab and JV-Link.
- 32-bit Python is recommended because JV-Link is a 32-bit COM component.

NAR data is outside this repository.

## Components

| Component | Responsibility |
| --- | --- |
| `src/cli/main.py` | Click CLI entry point (`jltsql`). |
| `src/jvlink/` | JV-Link COM access and constants. |
| `src/parser/` | JRA-VAN record parsers. |
| `src/database/` | SQLite/PostgreSQL handlers and schemas. |
| `src/realtime/` | Realtime data collection. |
| `scripts/quickstart.py` | Non-interactive and interactive setup/update orchestration. |
| `quickstart.bat` | General SQLite-first quickstart. |
| `quickstart_postgres_timeseries.bat` | PostgreSQL + official time-series odds setup. |
| `daily_sync.bat` | Recent race-card/result sync for scheduled Windows tasks. |

## Data Stores

| Store | Use |
| --- | --- |
| SQLite | Local single-user storage and fallback. |
| PostgreSQL | Shared storage for multi-host analytics and downstream systems. |
| Binary cache | Local cache to avoid unnecessary JV-Link reads. |

`config/config.yaml.example` defaults to SQLite. PostgreSQL mode is selected
through CLI options or a local config file.

## Time-Series Odds

JRA-VAN long-retention time-series odds are:

| JVRTOpen spec | Stored tables | Coverage |
| --- | --- | --- |
| `0B41` | `TS_O1` | Win/place/bracket, one-year retention. |
| `0B42` | `TS_O2` | Quinella, one-year retention. |

Full-ticket realtime odds are `0B30` to `0B36`. They cover the race-week
retention window only. To evaluate wide, exacta, trio, and trifecta with
decision-time odds, keep collecting these specs during the racing week.

## Scheduling

Use Windows Task Scheduler to run `daily_sync.bat` for ordinary race data.
Use a separate realtime task or service for race-day `0B30` to `0B36`
collection when full-ticket decision odds are required.
