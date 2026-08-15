# Change-record HappyoTime contract worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: align AV/WE/CC/JC/TC announcement-time parser output and
  JRA-VAN standard-name storage with the current official 8-byte
  `MMDDhhmm` contract without silently accepting incompatible tables.
- Minimum scope: the five affected parsers, their native/standard schemas,
  focused SQLite/PostgreSQL regression tests, migration guidance, and directly
  affected documentation.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_happyo_time`
- Branch: `agent/happyo-time-contract-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `d0b4ad32c0b2ebd01405269375906783e7a99e74`
- Related issue: #168.
- Dependency: PR #167 is merged at
  `d0b4ad32c0b2ebd01405269375906783e7a99e74` and supplies the already-correct
  `BATAIJYU.HappyoTime` reference contract.
- Reviewer and implementer: Codex. Claude Code is not used.

## Initial observed gap

- AV and WE parsers currently preserve their official 8-byte value, while
  standard `TORIKESI_JYOGAI` and `TENKO_BABA` declare `TIMESTAMP`.
- CC, JC, and TC currently convert the 8-byte field to `datetime.time`, losing
  the official month/day component; their standard tables also declare
  `TIMESTAMP`.
- Native NL/RT tables use text columns, so removal of the lossy parser
  conversion should preserve the official value without a native type change.
- Four reverse mappings point to aliases for which no standard schema exists:
  `NL_AV -> AVOIDENCE`, `NL_WE -> WEATHER`, `NL_JC -> JOCKEY_CHANGE`, and
  `NL_TC -> COMMENT`. `NL_CC -> COURSE_CHANGE` is already correct. The
  standard-name importer therefore cannot persist four of the five formats.
- `verify_table_schema()` checks column names and primary keys but not an
  incompatible existing column type. An old `TIMESTAMP` column is therefore
  accepted even though PostgreSQL cannot store `MMDDhhmm` in it and SQLite's
  affinity can discard a leading zero.

## Official specification verification

- Current artifact: JRA-VAN Data Lab SDK 5.0.0 64-bit, published 2026-08-04,
  downloaded from
  `https://jra-van.jp/dlb/sdv/sdk/JVDTLABSDK500_64bit.zip`.
- Archive SHA-256:
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`.
- Extracted official `JVData_Struct.py` SHA-256:
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`.
- `JV_WE_WEATHER`, `JV_AV_INFO`, `JV_JC_INFO`, `JV_TC_INFO`, and
  `JV_CC_INFO` all declare `HappyoTime: MDHM`; the SDK slices exactly eight
  bytes at repository-equivalent offsets 25 (WE) and 27 (the other four).
  `MDHM` is four two-character strings: month, day, hour, minute; it has no
  year and is not a SQL timestamp.
- Historical JV-Data 4.8.0.2 and its change history retain the same eight-byte
  発表月日時分 layout. Format identifiers were renumbered in 2011, but no
  pre/post layout fork for this field exists. One parser/storage contract is
  therefore valid for both old and current records.
- The same current SDK audit found six odds header formats O1-O6 also use
  `MDHM`, while their JRA-VAN standard HEAD schemas declared `TIMESTAMP`.
  Their homogeneous schema contract is included in this iteration so every
  standard `HappyoTime` declaration is lossless. Their separate importer-path
  and native `HassoTime` naming design is not changed here.

## Red-first evidence

- Before any parser, schema, mapping, or validator implementation change:
  `python3 -m pytest -q tests/test_happyo_time_contract.py
  --basetemp=/tmp/jrvltsql-happyo-red-20260815` exited 1 with **14 failed,
  4 passed, 1 skipped**.
- The failures demonstrated all required negative paths: CC/JC/TC returned
  `datetime.time(9, 30)` instead of `06150930`; all five standard schemas were
  `TIMESTAMP`; four official reverse mappings were absent; SQLite standard
  import failed; and a legacy temporal column was incorrectly accepted by
  schema verification. The paired lossless `TEXT` verification case passed.

## Next safe command

Implement the smallest shared correction, then rerun the focused contract and
migration tests with a fresh `--basetemp`. Do not silently rewrite an existing
temporal column.

## Implementation and focused verification

- CC/JC/TC no longer apply the lossy `TIME` converter. AV/WE remain raw
  strings; all five now return exact `MMDDhhmm`.
- All 12 JRA-VAN standard schemas with `HappyoTime` now declare `VARCHAR(8)`.
- Official reverse mappings select the five change-notification table names;
  legacy forward aliases remain available. WE's six native state names are
  translated only when targeting standard `TENKO_BABA`.
- Schema verification now rejects an existing non-text type when expected
  schema requires lossless text. It also fails when the required actual type
  cannot be measured; a compatible legacy `TEXT` column remains accepted.
- `python3 -m pytest -q tests/test_happyo_time_contract.py
  tests/test_migration.py --basetemp=/tmp/jrvltsql-happyo-green2-20260815`:
  **46 passed, 1 skipped** (the gated PostgreSQL test).
- Isolated PostgreSQL 16 container `jrvltsql-happyo-pg-20260815`, bound only to
  `127.0.0.1:55439`, was used for actual storage. The PostgreSQL/change/WH
  selection completed with **7 passed, 41 deselected** before the explicit
  legacy-type PostgreSQL case was added.
- After adding that explicit real-PostgreSQL negative case,
  `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1 ... python3 -m pytest -q
  tests/test_happyo_time_contract.py -k postgresql
  --basetemp=/tmp/jrvltsql-happyo-pg2-20260815` completed with **2 passed,
  21 deselected**. It proves both exact `06150930` storage and rejection of an
  actual PostgreSQL `TIMESTAMP` legacy column.

## Current handoff state

- Worktree is intentionally dirty with this iteration's implementation,
  regression tests, documentation, and this worklog; no unrelated paths are
  modified.
- Next safe command: run workflow-equivalent lint/test checks, inspect the
  complete diff, then create the first candidate commit. After the full SHA is
  fixed, run exact-SHA focused/full/PostgreSQL tests and Codex review before
  push/PR.

## STOP conditions

- Do not infer a full calendar year for a field that contains only `MMDDhhmm`.
- Do not silently coerce or rewrite an existing incompatible standard-name
  table without a tested migration/fail-closed contract.
- Do not merge without exact-SHA focused/full tests, real PostgreSQL coverage,
  final Codex review, and unresolved review thread count zero.
