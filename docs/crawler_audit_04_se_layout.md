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

The parser now rejects inputs shorter than 555 bytes and exposes all three
opponent slots. Both `NL_SE` and `RT_SE` storage schemas contain the six
opponent registration/name columns. The JRA-VAN PostgreSQL `UMA_RACE` schema
already contained those columns. Schema-aware conversion now reads both the
native and JRA-VAN schema dictionaries, so unknown parser fields are filtered
before insert and all six opponent columns reach `UMA_RACE`.

Existing `NL_SE` and `RT_SE` tables are migrated additively. The four newly
missing columns are added without dropping rows. The obsolete `Reserved_462`
column is intentionally preserved in an already-created database because
destructive migration is disabled by default; a historical reimport replaces
the corrupted values in the corrected columns.

## Existing data recovery

The parser correction does not repair rows imported with the obsolete layout.
Rebuild the affected `RACE` range from the authoritative JRA-VAN setup/normal
data after deploying this parser. For a historical rebuild, use JVOpen option
3 or 4; subsequent updates use option 1.

```bash
jltsql fetch --from <YYYYMMDD> --to <YYYYMMDD> --spec RACE --option 4
```

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
- Direct SE parser/schema/import/migration regression suite: 17 passed,
  including a real SQLite insert through `use_jravan_schema=True` into
  `UMA_RACE` and additive migration of existing `NL_SE` / `RT_SE` rows.
- Full suite: 1,300 passed, 37 skipped, 14 failed. The same clean-base run had
  1,291 passed, 37 skipped, 16 failed. The remaining branch failures are
  existing Linux COM integration, date-filter fixture, fixed schema-count,
  HR migration, and stale HR column-count tests; none execute the changed SE
  parser/layout path.
- `ruff check` passed for `se_parser.py` and `schema_types.py`; `schema.py` and
  `importer.py` passed with their existing baseline rules excluded.
  `py_compile` and `git diff --check` passed.

## Independent review

The required independent `gpt-5.6-sol` review was repeated after each finding:

1. The first review found that JRA-VAN schema conversion only consulted the
   native schema dictionary and that the CRLF wording was ambiguous. Conversion
   now supports both schema dictionaries, and a real `UMA_RACE` insert verifies
   all three opponent slots.
2. The second review found that JRA-VAN `TIME` columns were not normalized and
   could therefore be dropped. `TIME` now maps to `TEXT`; a mechanical audit of
   all declared JRA-VAN SQL types reports no unsupported type.
3. The final review compared the offsets with JV-Data 4.9.0.1, reran the focused
   tests and `git diff --check`, and returned `APPROVED` with no findings.
