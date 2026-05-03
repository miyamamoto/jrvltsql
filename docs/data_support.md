# Supported Data Matrix

This page lists the JRA-VAN data families that jrvltsql currently supports.
It is intended to make the collection scope explicit in the same operational
style as update-data matrices in tools such as EveryDB2.

jrvltsql is JRA-only. NAR data is outside this repository.

## Reading This Page

| Mark | Meaning |
| --- | --- |
| Supported | Parser, schema, and importer/updater path exist. |
| Operational | A maintained command or batch file is provided. |
| Parser/schema only | Record parser and table exist, but no recommended operational flow is documented. |
| Not supported | Outside the current jrvltsql scope. |

The implementation source of truth is:

- `src/jvlink/constants.py`
- `src/parser/factory.py`
- `src/database/table_mappings.py`
- `src/database/schema.py`
- `src/cli/main.py`

## Acquisition Families

| Family | JV-Link API | Option/spec | Operational command | Key/range | Status |
| --- | --- | --- | --- | --- | --- |
| Normal accumulated data | `JVOpen` | option `1` | `jltsql fetch --spec <SPEC> --option 1` | `FromTime` style date range | Supported |
| This-week data | `JVOpen` | option `2` | `quickstart.bat`, `daily_sync.bat`, `jltsql fetch --option 2` | Current race week | Supported for `TOKU`, `RACE`, `TCVN`, `RCVN` |
| Setup data | `JVOpen` | option `3` / `4` | `quickstart.bat`, `jltsql fetch --option 3/4` | Initial historical setup | Supported for the accumulated specs listed below |
| Realtime race/event data | `JVRTOpen` | `0B11` to `0B17` | `jltsql realtime start --specs <SPEC>` | `YYYYMMDD` | Supported for listed record types |
| Realtime odds/votes | `JVRTOpen` | `0B20`, `0B30` to `0B36` | `jltsql realtime timeseries --spec <SPEC>` | `YYYYMMDDJJRR` | Supported, one-week JRA-VAN retention |
| Official historical odds time-series | `JVRTOpen` | `0B41`, `0B42` | `quickstart_postgres_timeseries.bat`, `fetch_timeseries_postgres.bat`, `jltsql realtime odds-timeseries` | `YYYYMMDDJJRR` | Supported, about one-year JRA-VAN retention |

## JVOpen Accumulated Data

| Data spec | Alias | Description | Main record types | Stored tables | Option 1 | Option 2 | Option 3/4 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TOKU` | - | Special registration | `TK` | `NL_TK` | Yes | Yes | Yes | Included in standard/full quickstart. |
| `RACE` | - | Race card, results, payouts, final odds, votes, WIN5, exclusions | `RA`, `SE`, `HR`, `H1`, `H6`, `O1`-`O6`, `WF`, `JG` | `NL_RA`, `NL_SE`, `NL_HR`, `NL_H1`, `NL_H6`, `NL_O1`-`NL_O6`, `NL_WF`, `NL_JG` | Yes | Yes | Yes | Core race data. Final odds are stored here, not decision-time odds. |
| `DIFF` | `DIFN` | Accumulated master diffs | `UM`, `KS`, `CH`, `BR`, `BN`, `RC` | `NL_UM`, `NL_KS`, `NL_CH`, `NL_BR`, `NL_BN`, `NL_RC` | Yes | No | Yes | `DIFN` is accepted as the current alias. |
| `BLOD` | `BLDN` | Bloodline data | `HN`, `SK`, `BT` | `NL_HN`, `NL_SK`, `NL_BT` | Yes | No | Yes | `BLDN` is accepted as the current alias. |
| `MING` | - | Data-mining predictions | `DM`, `TM` | `NL_DM`, `NL_TM` | Yes | No | Yes | Included in full quickstart. |
| `SLOP` | - | Hill-training related data | `HC` | `NL_HC` | Yes | No | Yes | Included in standard/full quickstart. |
| `WOOD` | - | Woodchip-training related data | `WC` | `NL_WC` | Yes | No | Yes | Included in standard/full quickstart. |
| `YSCH` | - | Race schedule | `YS` | `NL_YS` | Yes | No | Yes | Used for race calendar maintenance. |
| `HOSE` | `HOSN` | Sales price data | `HS` | `NL_HS` | Yes | No | Yes | `HOSN` is accepted as the current alias. |
| `HOYU` | - | Horse-name meaning/origin | `HY` | `NL_HY` | Yes | No | Yes | Included in standard/full quickstart. |
| `COMM` | - | Course/commentary information | `CS` | `NL_CS` | Yes | No | Yes | Included in full quickstart. |
| `SNAP` | - | Race-card snapshot data | Returned record types vary | Existing `NL_*` tables by record type | Yes | No | Yes | Accepted by validation; not used by default quickstart. |
| `O1`-`O6` | - | Final odds by bet type | `O1`-`O6` | `NL_O1`-`NL_O6` | Yes | No | Yes | Usually obtained through `RACE`; use time-series commands for decision-time odds. |
| `TCVN` | - | Special-registration supplementation | Multiple master/race records | Existing `NL_*` tables by record type | No | Yes | No | Used by this-week update mode. |
| `RCVN` | - | Race-info supplementation | Multiple master/race records | Existing `NL_*` tables by record type | No | Yes | No | Used by this-week update mode. |

## JVRTOpen Realtime Race/Event Data

| Data spec | Description | Expected record types | Stored tables | Key format | Status |
| --- | --- | --- | --- | --- | --- |
| `0B11` | Realtime horse weight | `WH` | `RT_WH` | `YYYYMMDD` | Supported |
| `0B12` | Realtime race result / payout updates after result confirmation | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | Supported |
| `0B13` | Realtime time-type data-mining prediction | `DM` | `RT_DM` | `YYYYMMDD` | Supported |
| `0B14` | Realtime event/weather/track-change bundle | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `YYYYMMDD` | Supported |
| `0B15` | Realtime race-card/race updates from entry-list stage onward | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | Supported |
| `0B16` | Realtime event-change stream | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `YYYYMMDD` | Supported if provided by JV-Link for the event |
| `0B17` | Realtime match-type data-mining prediction | `TM` | `RT_TM` | `YYYYMMDD` | Supported |
| `0B51` | Realtime WIN5 | `WF` | `NL_WF` parser/schema exists; no `RT_WF` operational table | `YYYYMMDD` or WIN5 event key | Parser/schema only |

## JVRTOpen Odds And Votes

| Data spec | Description | Expected record types | Stored tables in normal realtime mode | Stored tables in time-series mode | Key format | JRA-VAN retention | Operational command |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `0B20` | Realtime vote counts | `H1`, `H6` | `RT_H1`, `RT_H6` | Not applicable | `YYYYMMDDJJRR` | About one week | Parser/schema supported; no recommended batch helper |
| `0B30` | Realtime odds, all bet types | `O1`-`O6` | `RT_O1`-`RT_O6` | `TS_O1`-`TS_O6` | `YYYYMMDDJJRR` | About one week | `jltsql realtime odds-sokuho-timeseries` |
| `0B31` | Realtime odds, win/place/bracket | `O1` | `RT_O1` | `TS_O1` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B31` |
| `0B32` | Realtime odds, quinella | `O2` | `RT_O2` | `TS_O2` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B32` |
| `0B33` | Realtime odds, wide | `O3` | `RT_O3` | `TS_O3` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B33` |
| `0B34` | Realtime odds, exacta | `O4` | `RT_O4` | `TS_O4` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B34` |
| `0B35` | Realtime odds, trio | `O5` | `RT_O5` | `TS_O5` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B35` |
| `0B36` | Realtime odds, trifecta | `O6` | `RT_O6` | `TS_O6` | `YYYYMMDDJJRR` | About one week | `jltsql realtime timeseries --spec 0B36` |
| `0B41` | Official historical odds time-series, win/place/bracket | `O1` | Not recommended | `TS_O1` | `YYYYMMDDJJRR` | About one year | `jltsql realtime odds-timeseries` |
| `0B42` | Official historical odds time-series, quinella | `O2` | Not recommended | `TS_O2` | `YYYYMMDDJJRR` | About one year | `jltsql realtime odds-timeseries` |

Important operational constraints:

- `0B41` and `0B42` are the only official long-retention historical
  time-series odds feeds.
- Wide, exacta, trio, and trifecta decision-time odds require race-week
  accumulation through `0B30` or `0B33` to `0B36`.
- Time-series odds commands save expanded one-row-per-combination rows in
  `TS_O*` tables and preserve `HassoTime`.
- `NL_O*` tables contain final odds. They are useful for historical reference
  but must not be treated as decision-time odds.

## Parser And Table Coverage

jrvltsql currently has parser and schema coverage for these 38 JRA record
types:

| Record types | Stored tables |
| --- | --- |
| `RA`, `SE`, `HR` | `NL_RA`, `NL_SE`, `NL_HR` |
| `UM`, `KS`, `CH`, `BR`, `BN` | `NL_UM`, `NL_KS`, `NL_CH`, `NL_BR`, `NL_BN` |
| `HN`, `SK`, `BT`, `RC` | `NL_HN`, `NL_SK`, `NL_BT`, `NL_RC` |
| `O1`, `O2`, `O3`, `O4`, `O5`, `O6` | `NL_O1`, `NL_O2`, `NL_O3`, `NL_O4`, `NL_O5`, `NL_O6` |
| `H1`, `H6` | `NL_H1`, `NL_H6` |
| `YS`, `TK`, `CS` | `NL_YS`, `NL_TK`, `NL_CS` |
| `WE`, `WH`, `AV`, `JC`, `TC`, `CC` | `NL_WE`, `NL_WH`, `NL_AV`, `NL_JC`, `NL_TC`, `NL_CC` |
| `DM`, `TM`, `WF`, `JG` | `NL_DM`, `NL_TM`, `NL_WF`, `NL_JG` |
| `HC`, `HS`, `HY`, `WC`, `CK` | `NL_HC`, `NL_HS`, `NL_HY`, `NL_WC`, `NL_CK` |

Realtime mirrors exist for the supported realtime record families as `RT_*`.
Odds time-series mirrors exist as `TS_O1` to `TS_O6`.

## Out Of Scope

| Item | Status | Reason |
| --- | --- | --- |
| NAR / local racing | Not supported | This repository is JRA-only. Use a separate NAR collector/repository. |
| Long-retention historical time-series for wide/exacta/trio/trifecta | Not available from JRA-VAN official long-history specs | Must be accumulated during the current race week via `0B30` or `0B33`-`0B36`. |
| Investment decision snapshots | Downstream concern | jrvltsql stores raw/final/time-series records; strategy systems choose decision timing from stored data. |

## Reference

- [EveryDB2 manual: update data type settings](https://everydb.iwinz.net/edb2_manual/05-UpdateData.html)
