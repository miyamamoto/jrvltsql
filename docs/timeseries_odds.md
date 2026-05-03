# Time-Series Odds

This repository supports two different JRA-VAN realtime odds paths.
For the full supported-data matrix, including non-odds data specs, see
[Supported data](data_support.md).

| Purpose | JVRTOpen spec | Stored tables | Retention | Notes |
| --- | --- | --- | --- | --- |
| Official long history | `0B41` | `TS_O1` | About one year | Win/place/bracket time-series odds. |
| Official long history | `0B42` | `TS_O2` | About one year | Quinella time-series odds. |
| Race-week sokuho | `0B30` | `TS_O1` to `TS_O6` | About one week | All ticket types in one stream. |
| Race-week sokuho | `0B31` to `0B36` | `TS_O1` to `TS_O6` | About one week | Ticket-specific realtime odds streams. |

## Commands

Official long-history time-series odds:

```bat
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db postgresql
```

Race-week all-ticket sokuho accumulation:

```bat
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
```

PostgreSQL quickstart for race data plus official `TS_O1/TS_O2`:

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

`quickstart.bat` can run this PostgreSQL time-series quickstart as an optional
follow-up after the ordinary setup. The PostgreSQL time-series quickstart also
asks whether to register `daily_sync.bat` in Windows Task Scheduler.

## Important Constraints

- JRA-VAN does not provide long-retention historical time-series odds for every
  ticket type.
- The collector stores raw time-series odds. Downstream consumers should choose
  their own decision snapshot timing from `HassoTime`.
- `HassoTime` is an announced timestamp, not necessarily equal to post time.
