# Crawler audit #04: SE repeated opponents and tail offsets

## Finding

`src/parser/se_parser.py` treated SE (horse race information) as a 463-byte
record. JV-Data 4.9.0.1 defines it as 555 bytes including the trailing CRLF.
The JRA JVRead/bridge path passes those bytes through without stripping CRLF,
so this parser requires all 555 bytes. This differs from the NAR TSV-cache
reader, which reconstructs a 553-byte record without CRLF.

The official `winner/opponent horse information` block is 46 bytes repeated
three times. The previous parser read only the first block and started
`TimeDiff` 92 bytes too early. This made the second and third opponent strings
look like the time difference, mining values, and running style.

## Correct layout

| Field | Official position | Python slice |
|---|---:|---|
| Opponent 1 registration/name | 394 / 404 | `[393:403]` / `[403:439]` |
| Opponent 2 registration/name | 440 / 450 | `[439:449]` / `[449:485]` |
| Opponent 3 registration/name | 486 / 496 | `[485:495]` / `[495:531]` |
| Time difference | 532 | `[531:535]` |
| Record update category | 536 | `[535:536]` |
| Mining category/time | 537 / 538 | `[536:537]` / `[537:542]` |
| Mining error +/- | 543 / 547 | `[542:546]` / `[546:550]` |
| Mining rank | 551 | `[550:552]` |
| Running style | 553 | `[552:553]` |
| CRLF | 554 | passed through by JVRead/bridge |

The parser now requires exactly 555 bytes, including the trailing CRLF, and
exposes all three opponent slots. Both `NL_SE` and `RT_SE` storage schemas
contain the six opponent registration/name columns. The JRA-VAN PostgreSQL
`UMA_RACE` schema already contained those columns. Schema-aware conversion now
reads both the native and JRA-VAN schema dictionaries, so unknown parser fields
are filtered before insert and all six opponent columns reach `UMA_RACE`.

Existing `NL_SE` and `RT_SE` tables are migrated additively. The four newly
missing columns are added without dropping rows. The obsolete `Reserved_462`
column is intentionally preserved in an already-created database. Startup
migrations never drop tables; primary-key changes fail closed. Preparation runs
on historical fetches, `create-tables`, and realtime-monitor startup even when
no table is missing.

## Existing data recovery

The parser correction does not repair rows imported with the obsolete layout.
`NL_SE` is the authoritative historical table: rebuild its affected `RACE`
range from JRA-VAN setup/normal data after deploying this parser. For a
historical rebuild, use JVOpen option 3 or 4; subsequent updates use option 1.

```bash
jltsql fetch --from <YYYYMMDD> --to <YYYYMMDD> --spec RACE --option 4
```

`RT_SE` has a different recovery policy. `RACE` imports never rewrite it, and
JRA-VAN realtime records are retained for only one week. Stop the realtime
monitor, back up the database, remove rows that were imported by the obsolete
parser, and restart the monitor to replay only the still-available `0B12` /
`0B15` window. Older corrupted `RT_SE` rows are unrecoverable and must be
discarded; do not copy them into `NL_SE`, features, or ratings. `NL_SE` remains
the historical source of truth.

Validate `TimeDiff`, `DMKubun`, `DMJyuni`, and `KyakusituKubun` domains after
reimport, and reconcile race/runner key counts before rebuilding features.
Do not reuse features or ratings derived from the corrupted SE tail.

## Tests

- Synthetic 555-byte official-layout test covers all three repeated blocks,
  every tail field, and CRLF.
- A 463-byte record is rejected.
- Historical 463-byte fixture records are explicitly padded only for their
  pre-tail core-field tests; they are not accepted as authoritative tail data.
- `NL_SE` and `RT_SE` schema tests require all six opponent columns.
- Direct parser/schema/import/migration/cache regression suite: 76 passed,
  including a real SQLite insert through `use_jravan_schema=True` into
  `UMA_RACE`, additive migration of existing `NL_SE` / `RT_SE` rows, and the
  all-tables-present realtime startup path. It also verifies that a failure in
  a later setup year rolls back rows imported in earlier years and that cache
  parser failures are counted rather than silently discarded.
- Full suite: 1,339 passed, 43 skipped, 0 failed, 3 pre-existing pytest return
  warnings.
- SQLite setup rollback is exercised against a real temporary database. The
  pg8000 and psycopg transaction-boundary tests use mocked driver connections
  and verify `BEGIN` / `COMMIT` / `ROLLBACK` ordering; a live PostgreSQL server
  was not used by this audit.
- `py_compile` and `git diff --check` passed. Repository-wide `ruff check`
  still reports pre-existing baseline violations outside this audit's scope.

## Independent review

The required independent `gpt-5.6-sol` review was repeated after each finding:

1. The first review found that JRA-VAN schema conversion only consulted the
   native schema dictionary and that the CRLF wording was ambiguous. Conversion
   now supports both schema dictionaries, and a real `UMA_RACE` insert verifies
   all three opponent slots.
2. The second review found that JRA-VAN `TIME` columns were not normalized and
   could therefore be dropped. `TIME` now maps to `TEXT`; a mechanical audit of
   all declared JRA-VAN SQL types reports no unsupported type.
3. The third review found that an existing `RT_SE` was not migrated by the
   production realtime startup path, that the recovery procedure conflated
   `NL_SE` and `RT_SE`, and that the Python bridge test covered only the
   consumer. Realtime startup now migrates unconditionally and fails closed;
   the recovery policies are separated above.
4. The bridge producer is owned by the separate `jrvltsql-wine-runtime`
   repository. Its native bridge uses the JVRead return length when base64
   encoding and does not trim CRLF. This repository verifies the 555-byte
   Python consumer handoff; a producer-side executable contract test must be
   reviewed and released with the runtime repository, not silently duplicated
   here.
5. The fourth review found that `DataImporter` committed each internal batch,
   so a later rejected record could leave earlier rows persisted. Imports now
   disable internal commits and commit only after the complete data spec has
   passed fetch and import failure checks. A real SQLite regression test proves
   that the earlier row is rolled back.
6. The fifth review found two remaining fail-closed gaps: option-3 setup ranges
   committed each yearly memory-control chunk, and cache-hit parser failures
   were omitted from fetch statistics. The split setup now uses one outer
   transaction across all yearly chunks, and cache replay maintains fetched,
   parsed, and failed counters. Both paths have regression tests and the full
   suite passes after the fixes.
7. The sixth review found that pg8000 still autocommitted when callers selected
   `auto_commit=False`, and that backend transaction tests were incomplete.
   `BatchProcessor` now always establishes the driver transaction before an
   import, while only committing when requested. The pg8000 handler tracks the
   transaction state so nested yearly chunks share one transaction. Regression
   tests cover caller-managed transactions and split rollback for both pg8000
   and psycopg driver paths; the live-server limitation is stated above.
8. The final independent review reran the scoped transaction and cache tests
   (`20 passed, 2 skipped`), confirmed the caller-managed and split transaction
   boundaries, and returned `VERDICT: APPROVED` with no actionable findings.
