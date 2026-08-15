# WH official horse-weight layout worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: replace the incorrect WE-like 40-byte `WH` implementation with
  the official 847-byte horse-weight record, expand up to 18 horse entries,
  and align NL/RT persistence contracts without silently writing incompatible
  legacy tables.
- Minimum scope: `WHParser`, exact WH fixtures/tests, `NL_WH`/`RT_WH` schemas
  and primary-key routing, directly affected metadata/index/docs, and explicit
  operator guidance for the incompatible old physical schema.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_wh_layout`
- Branch: `agent/wh-official-layout-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `56acaaf9498742b74f9c7cf86325611c96a34b50`
- Previous merges: PR #165 `fc5d4fb08533021b5fbc83e39a499e92ef8929b6`;
  PR #166 `56acaaf9498742b74f9c7cf86325611c96a34b50`.
- Reviewer: Codex. Claude Code and external coding agents are not used.

## Official old/current contract

- Published JV-Data 4.9.0.1 format 101 defines `WH` as exactly 847 bytes:
  35-byte header/race/announcement section, 18 repeated 45-byte horse-weight
  entries, and CR/LF at bytes 846-847.
- Each horse entry is `Umaban(2)`, `Bamei(36)`, `BaTaijyu(3)`,
  `ZogenFugo(1)`, and `ZogenSa(3)`. The official generated Python structure
  uses the same offsets and repetition.
- JV-Data 4.8.0.2 was checked separately and defines the same 847-byte,
  18-entry layout. There is no pre/post-2023 WH fork to support; accepting the
  current 40-byte weather layout as legacy would accept a format that was never
  official WH.
- Data-spec `0B11` maps to format 101 / record type `WH` (速報馬体重).

## Initial repository finding and safety

- `src/parser/wh_parser.py` is a duplicate of the 40-byte WE weather-change
  shape: it has no `RaceNum` or horse fields and reports a 40-byte length.
- `NL_WH` and `RT_WH` repeat the same wrong weather columns and primary key.
  A parser-only repair would therefore discard weights or fail insertion.
- Correct expanded storage needs one row per non-empty horse entry with at
  least race identity, announcement time, and horse number in its key.
- The existing schema migrator is additive and deliberately refuses primary
  key replacement. Do not weaken that gate or silently drop existing tables.
  If the expected WH primary key changes, old physical tables must fail closed
  with explicit operator migration guidance because their rows do not contain
  valid WH horse-weight data.

## Contract decision and red-first evidence

- NL/RT WH is a latest-state table, not a `TS_*` history table. The official
  key marks the race identity; after expanding the 18-entry array, `Umaban` is
  appended. `HappyoTime` remains stored evidence but is not part of the key, so
  a corrected announcement replaces the prior row for the same race/horse.
- `BaTaijyu` and `ZogenSa` are stored as integers in kg. This preserves the
  official `000`/`999` sentinel values and avoids the repository's legacy
  tenth-unit conversion that applies only to `REAL` columns.
- The format layout is unchanged in JV-Data 4.8.0.2 and 4.9.0.1. Separately,
  the official change history says DataKubun `0` deletion was removed in
  version 1.0.7 beta (2003-07-11). Current `1` rows and old `0` rows therefore
  share the same 847-byte parser; an empty old `0` record is retained as a
  race-level delete instruction, while an empty current `1` record is invalid.
- Before production edits, command
  `pytest -q tests/test_wh_official_contract.py --basetemp=/tmp/jrvltsql-wh-red2-pytest`
  exited 1 with **9 failures**: official parsing returned the 16-field weather
  dict, all four invalid-boundary cases were accepted, the old delete contract
  was unavailable, schema columns/key were wrong, storage could not consume
  expanded rows, and the legacy table did not yet conflict with the expected
  schema. This is the recorded red side of the validator/parser repair.
- A second official-name boundary was found before its repair:
  `JRAVAN_TO_JLTSQL` mapped WH to nonexistent weather table name `BABA` rather
  than `BATAIJYU`. The isolated mapping test exited 1 (`assert 'BABA' not in
  JRAVAN_TO_JLTSQL`). Correcting only the name would still drop all 18 weight
  slots because the native representation is expanded while official
  `BATAIJYU` is wide. The standard-schema storage test was therefore run
  before adding the adapter and exited 1 with an empty stored result (both
  expanded rows were rejected as incomplete).
- After the layout/storage repair but before value-domain validation, the
  isolated invalid-boundary test exited 1 with **7 failures**: unsupported
  DataKubun `2`, out-of-range horse `19`, duplicate horse `01`, nonnumeric
  weight, invalid change sign, nonnumeric change amount, and payload in a slot
  without a horse number were all accepted. Existing official and blank-slot
  cases remained green. These failures are the red side of the WH value-domain
  checks added in the same implementation batch.
- A subsequent line-by-line value-domain review found two official boundary
  cases before the final parser change. The focused command exited 1 with
  **2 failures**: unused entries initialized with official horse number `00`
  were rejected, while reserved body weight `001` was accepted. The parser now
  treats blank/`00` horse numbers as empty only when the rest of that slot is
  blank, and accepts body weight only as blank, `000`, `002`-`998`, or `999`.
- The final header-domain audit added one representative corrupt `MakeDate`
  case before implementation; it failed (`WHParser.parse` returned rows) and
  now passes after enforcing exact ASCII-digit widths for every numeric header
  field. `JyoCD` remains a two-byte code rather than being incorrectly assumed
  numeric.

## Implementation and current verification

- `WHParser` now enforces the exact 847-byte/CRLF boundary, slices CP932 fields
  by byte, expands non-empty horse slots for native NL/RT storage, and carries
  a private complete wide representation for `BATAIJYU` standard-name import.
- Native `NL_WH` / `RT_WH` use one row per race/horse, integer kg/sentinel
  fields, and official race identity plus horse number as the primary key.
  Corrected announcements replace the current row and preserve `HappyoTime`.
- Official `BATAIJYU` now has the official race primary key and byte-shaped
  date/time text. Both importer implementations select the wide representation
  only for that target; native and realtime paths discard private metadata.
- Pre-2003 DataKubun `0` with no horse slots is preserved for race-level
  realtime deletion. Current empty DataKubun `1` records fail closed.
- The actual realtime path is covered end to end: ParserFactory expands an old
  valid WH record into two `RT_WH` rows, then a matching pre-2003 empty
  DataKubun `0` record deletes the race back to zero rows. The isolated test
  passed.
- Expanded focused command covering WH, parser compatibility, all schemas and
  mappings, realtime routing, indexes, metadata, migration,
  regular/optimized import and expanded storage:
  `pytest -q tests/test_wh_official_contract.py tests/test_parsers.py
  tests/test_parser.py tests/test_parser_compatibility.py tests/test_realtime.py
  tests/test_indexes.py tests/test_metadata_application.py tests/test_migration.py
  tests/test_all_schemas.py tests/test_table_mappings.py tests/test_importer.py
  tests/test_importer_clean_record.py tests/test_expanded_record_storage.py
  --basetemp=/tmp/jrvltsql-wh-focused2-pytest` passed **814**, skipped 8,
  subtests passed 3.
- The final contract test after all header/value-domain changes passed **24**
  with the opt-in PostgreSQL case skipped. The full local suite before the
  final numeric-header check passed **1852**, skipped 45, with 5 subtests and
  three pre-existing `PytestReturnNotNoneWarning` warnings; it must be rerun on
  the committed full SHA before merge.
- An isolated `postgres:16-alpine` container on loopback port 55439 verified
  real PostgreSQL native `NL_WH` and standard `BATAIJYU` create/import/upsert:
  **1 passed**. The container was started with `--rm`, stopped, and confirmed
  absent; existing KPS databases were not contacted.
- Full fatal `flake8`, targeted `ruff`, `black`, `compileall`, and
  `git diff --check` passed. A
  direct mypy invocation still reports the repository's established baseline
  errors in imported logger/database/importer modules; it reported no WH-parser
  error and is not represented as a green gate.

## Next safe command

Stage and inspect the complete diff including new files, commit it, then run
the expanded focused suite, workflow-equivalent suite, full local suite,
static checks, and isolated PostgreSQL integration against the candidate full
SHA. Record that SHA and evidence on the PR, then perform final Codex review.

## STOP conditions

- Do not preserve weather-field aliases as official WH values.
- Do not silently overwrite/drop an existing `NL_WH` or `RT_WH` table.
- Do not merge without red-first official-layout evidence, parser/storage
  focused tests, full tests, Codex final review, and unresolved thread count 0.
