# DM current-layout compatibility worklog

## Objective and minimum scope

- Bring jrvltsql's `DM` parser and both accumulated/realtime persistence paths
  into exact agreement with the official JV-Data physical contract.
- Re-audit both the older and current official specification generations before
  choosing compatibility behavior. Do not infer a legacy format from the
  repository's current 48-byte truncation.
- Preserve every official horse entry without weakening record-length,
  record-type, delimiter, primary-key, transaction, or migration checks.
- Keep this iteration limited to `DM`; the remaining official-layout gaps and
  the later documentation/privacy/package/release work stay in separate PRs.

## Repository and version identity

- Repository: `miyamamoto/jrvltsql`
- Dedicated worktree:
  `/home/keiba/scratch/20260816_jrvltsql_dm_layout`
- Branch: `agent/dm-current-layout-20260816`
- Base and initial HEAD:
  `7d360f34f6590100ab816af99474344b69295450`
- Initial `origin/master`:
  `7d360f34f6590100ab816af99474344b69295450`
- Latest published tag at start: `v1.6.10`
- Production/release status: this branch is an unreleased candidate. The final
  jrvltsql release remains downstream of all official-layout iterations and a
  fresh live-provider acquisition-to-database validation on final merged code.

## Dependency order

1. PR #179 (`CH`) was merged first as
   `7d360f34f6590100ab816af99474344b69295450`.
2. This `DM` iteration starts from that merge SHA and must merge before the next
   official-layout iteration starts.
3. Documentation/privacy/package cleanup, jrvltsql release, jrvltsql-nar work,
   and jvlink-mcp-server work remain later dependent iterations.

## Initial observed state

- The tracked compatibility audit records official `DM` length 303 and marks
  the implementation partial because its public length is 48 and it reads only
  one of 18 horse entries.
- `src/parser/dm_parser.py` currently declares `RECORD_LENGTH = 48`, accepts
  short input, and treats bytes 47-48 as the delimiter.
- Existing native tables already use one row per horse and include `Umaban` in
  the primary key. Standard-name schema and importer behavior still require
  independent inspection before an implementation decision.
- Official source material available for this iteration includes JV-Data
  4.8.0.2, JV-Data 4.9.0.1, and SDK 5.0.0 structure definitions. Exact offsets,
  generation differences, blank-entry behavior, and delimiter placement have
  not yet been fixed in this worklog.

## Official and community re-audit

- JV-Data 4.8.0.2 and 4.9.0.1 have the same DM contract. Both specify one
  303-byte physical record: bytes 1-11 header, bytes 12-27 race identity,
  bytes 28-31 `MakeHM`, 18 repeated 15-byte horse entries beginning at byte 32,
  and CR/LF at bytes 302-303. Each horse entry is `Umaban` 2,
  `DMTime` 5, `DMGosaP` 4, and `DMGosaM` 4 bytes.
- SDK 5.0.0 independently agrees in its C++, C#, and Python structures. The C#
  implementation allocates a 303-byte buffer and iterates
  `32 + (15 * i)` for all 18 `DMInfo` entries; the Python implementation uses
  the same one-based offsets and reads the delimiter from byte 302.
- No old/current DM physical-layout split appears between the two audited
  official generations. The 48-byte repository shape is exactly the 31-byte
  header plus one 15-byte entry plus CR/LF, so it is a truncated reconstruction,
  not a documented legacy JV-Data record. It must be rejected rather than
  treated as backwards compatibility.
- The official change history records naming/format-number changes around
  versions 4.0/4.1.1, but no 48-to-303 layout transition. The older 4.8.0.2
  workbook already carries the same 303-byte/18-entry definition as 4.9.0.1.
- The official developer community confirms that accumulated DM/TM are obtained
  through `MING`, realtime DM through `0B13`, and that accumulated and realtime
  prediction content is the same:
  <https://developer.jra-van.jp/t/topic/284> and
  <https://developer.jra-van.jp/t/topic/286>.
- Community correction history is operationally relevant. JRA-VAN support
  states that `DataKubun=3` and `DataKubun=7` should not change the prediction,
  but documented erroneous source rows were later corrected. Therefore storage
  must upsert a complete race revision rather than preserve only the first horse:
  <https://developer.jra-van.jp/t/topic/95>.
- A 2026 community clarification states that DataLab DM is the official
  predicted finishing time, while the consumer app may show a derived score.
  This implementation must preserve the five-byte JV-Data time and must not
  attempt the unpublished score conversion:
  <https://developer.jra-van.jp/t/topic/856>.

## Storage-path findings and decision

- Native `NL_DM` and `RT_DM` are already keyed per horse. They should receive
  one logical row for every populated entry in the 303-byte record.
- The repository's JRA-VAN standard schema already defines the official wide
  table `MINING` with 18 numbered entry groups, but reverse mapping currently
  points `NL_DM` to the non-schema alias `DATA_MASTER`. Canonical standard mode
  must target one wide `MINING` row per race.
- `MINING` currently lacks a primary key. Safe correction/upsert requires the
  six-field race identity key. Existing keyless tables cannot be made safe by
  silent append behavior and must be rejected for operator rebuild.
- Expanded-parser metadata can follow the established WH design: emit native
  horse rows carrying one shared `_wide_record`; ordinary and optimized
  importers deduplicate that physical record only when targeting `MINING`.
- Official `DataKubun=0` deletes the whole physical race record. A blank horse
  array therefore must retain only race identity and delete all matching
  `NL_DM`/`RT_DM` rows (or the one `MINING` row); it must not fail open because
  `Umaban` is absent.

## Validation and review policy

- Codex-only implementation and review; do not use Claude Code.
- If a validator, migration gate, or fail-closed check changes, add the minimum
  paired failing/passing regression first and run it against the old code to
  record the actual red result.
- Validate the final immutable full SHA with focused and full suites, both
  supported Python generations, disposable PostgreSQL coverage where storage
  behavior is affected, critical lint/compile/static checks, and one aggregated
  exact-SHA Codex review.
- Do not merge on a failed executable check, unresolved actionable finding,
  unresolved review thread, base/head drift, or dirty worktree.

## Red-first regression evidence

- Before changing production code, added `tests/test_dm_official_contract.py`
  against base implementation commit
  `be480c28f8ee394ea604ebefe50a52af982838c4` (the worklog-start commit).
- Command:
  `pytest -q -p no:cov -o addopts='' --basetemp=/tmp/jltsql-dm-red tests/test_dm_official_contract.py`
- Result: exit 1, `27 failed in 0.61s`; there were no passing cases. The first
  failure was the explicit physical-length contract
  `assert DMParser.RECORD_LENGTH == 303` with actual value 48. Subsequent
  failures demonstrated acceptance of truncated/corrupt records, one-entry
  parsing, absent expanded revision/delete semantics, `MINING` not being the
  canonical standard mapping, and the missing `MINING` primary key.
- This is the required proof that the new parser/storage/migration checks can
  reject the old unsafe behavior. The paired green run remains required after
  implementation.
- A second focused red run covered two contract details discovered while
  closing the initial failures. Official format 28 says a delete record's
  repeated fields use their `sp` initial value, and SDK 5.0.0 exposes each
  five-byte `DMTime` as a string. Before the corresponding implementation,
  the three focused cases failed: a populated `DataKubun=0` record was
  accepted, `MINING.DMTime1` resolved as `REAL`, and the stored value `10501`
  was changed to `1050.1`. Command:
  `pytest -q -p no:cov -o addopts='' --basetemp=/tmp/jltsql-dm-red2`
  with the three named DM tests; result exit 1, `3 failed in 0.25s`.
- After implementation, the complete new contract module passed with
  `28 passed in 0.58s` using
  `pytest -q -p no:cov -o addopts='' --basetemp=/tmp/jltsql-dm-green2
  tests/test_dm_official_contract.py`.
- Before adding the legacy-name migration gate, a paired standard-mode test
  against a database containing only `DATA_MASTER` failed for both importers:
  neither raised, and each fell through to a missing-`MINING` insert/fallback.
  Command targeted
  `test_dm_standard_import_refuses_legacy_data_master_without_row_loss`;
  result exit 1, `2 failed in 0.27s`. This proves the new fail-closed gate is
  not a vacuous check.
- Exact candidate `fcda5db6da6155aa155955960c48bcaeef1b8613` exposed one
  additional snapshot-revision defect during the aggregated code-path review.
  A later official 18-slot DM record can leave a slot blank, but native
  `NL_DM` and `RT_DM` upserts retained the prior horse row. Before changing
  production code, the existing accumulated/realtime revision tests were
  tightened so horse 02 disappears from the corrected physical record.
  Command targeted the accumulated revision test and realtime revision test;
  result exit 1, `3 failed, 2 passed in 0.24s`. Both accumulated importer
  classes and realtime retained horse 02, while both standard `MINING` cases
  passed. This is the red proof for race-snapshot replacement; PostgreSQL is
  covered by the same test module after implementation.

## Implementation and validation state

- Changed the parser to require exactly 303 bytes and CR/LF, validate the
  DM-specific `DataKubun` domain `0/1/2/3/7`, validate fixed-width numeric
  header/prediction fields, reject duplicate/out-of-range horses and malformed
  blank slots, and expand all populated slots with one shared `_wide_record`.
- Native `NL_DM`/`RT_DM` now receive one row per populated horse. Standard mode
  canonically maps `DM` to one keyed `MINING` wide row. The standard DM time
  columns now preserve SDK 5.0.0's five-byte string instead of applying the
  previous divide-by-ten numeric conversion.
- The aggregated review of candidate
  `fcda5db6da6155aa155955960c48bcaeef1b8613` found that per-horse upserts did
  not remove a horse omitted by a later complete physical record. Parser
  metadata now carries the complete native snapshot plus one leader index.
  Both accumulated importers and realtime replace `NL_DM`/`RT_DM` by the six
  race keys, validate every row before deletion, and insert the complete
  replacement inside the caller's transaction. Only the leader processes a
  physical record, including when an expanded record crosses a setup chunk
  boundary. `import_single_record` also replaces the full snapshot.
- Both accumulated importers flush pending same-table rows before a
  `DataKubun=0` race delete, preserve caller-owned transaction control, and
  reset expanded-record deduplication state after the delete. Realtime deletes
  use the same six race keys before requiring `Umaban`.
- Standard-mode migration refuses a keyless `MINING`, numeric DM time columns,
  and legacy-only `DATA_MASTER`; tests verify pre-existing rows survive all
  three refusals.
- Updated the current official compatibility audit, public data-support text,
  DM schema metadata, current parser fixtures, and parser compatibility lengths.
- Focused SQLite/parser/realtime run:
  `823 passed, 3 subtests passed in 1.50s`. The later expanded focused run,
  including metadata and all migration refusals, passed with
  `851 passed, 6 skipped, 3 subtests passed in 2.09s`.
- A disposable PostgreSQL 16 container ran the complete DM contract module
  with integration enabled before the snapshot-review fix:
  `36 passed in 0.94s`. Both importer classes stored 18 native rows and one
  standard row, replaced a revision, preserved raw five-byte times, and
  deleted the complete race. The container was stopped and removed.
- Immutable candidate `fcda5db6da6155aa155955960c48bcaeef1b8613` passed the
  full Python 3.12 suite with `2152 passed, 53 skipped, 3 warnings, 6 subtests`
  and a sequential Python 3.10 compatibility rerun with the same totals. The
  workflow-equivalent covered subset passed with
  `864 passed, 2 skipped, 3 warnings, 3 subtests`. Its blocking flake8,
  compileall, and diff checks passed. Candidate mypy and exact-base mypy both
  reported the same pre-existing 79 errors, so this candidate introduced zero
  new mypy findings.
- After the stale-horse fix, the complete DM module passed locally with
  `35 passed, 2 skipped in 0.67s`; related importer/realtime coverage passed
  with `88 passed, 2 skipped, 3 subtests in 0.52s`. Disposable PostgreSQL 16
  passed the then-current module with `36 passed in 0.78s`, including 18-to-17
  horse revision replacement for both importer classes. The final candidate
  adds one direct `import_single_record` assertion and therefore still needs
  its immutable-SHA PostgreSQL/full-suite rerun.
- Replacement code candidate
  `3d7d96c68423572992361d15914d5ae024a92970` passed both full suites:
  Python 3.12 and Python 3.10 each reported
  `2153 passed, 53 skipped, 3 warnings, 6 subtests`. The exact workflow test
  selection passed with `864 passed, 2 skipped, 3 warnings, 3 subtests` and
  56% aggregate coverage. PostgreSQL 16 passed the DM module with
  `37 passed`; blocking flake8 reported zero, compileall/diff/changed-file
  Black checks passed, and mypy remained the same 79 errors in 20 files as
  the exact base comparison (zero newly introduced findings).
- The final Codex-only review then required explicit PostgreSQL evidence for
  the realtime path instead of inferring it from the shared helper. No new
  production-code defect was found. Candidate
  `55466bbd1b7d1da0c8e9bc5d143dee679d3a0d5b` added only that integration
  contract and passed the complete DM module on PostgreSQL 16 with
  `38 passed in 0.94s`: `RT_DM` replaced 18 rows with a 17-row revision,
  removed the omitted horse, and deleted the race inside explicit caller
  transactions. Its non-PostgreSQL focused module passed with
  `35 passed, 3 skipped in 0.70s`.
- `python3 -m compileall -q src tests`, `git diff --check`, Black checks for the
  new parser/test, and the workflow's blocking flake8 selection
  `E9,F63,F7,F82` all passed.
- `scripts/validate_schema_parser.py --all` remains exit 1 with its tracked
  static-introspection limitations: it cannot infer dict-literal/list-expanded
  output for DM, WH, odds, or votes, and still reports the pre-existing broad
  HR/SE/WF mismatches. It is not treated as green evidence; the executable DM
  parser/storage contracts above replace its DM false negative for this scope.
- The production/test candidate is clean at
  `55466bbd1b7d1da0c8e9bc5d143dee679d3a0d5b`; no actionable Codex finding
  remains. This worklog evidence update will create a documentation-only final
  PR head. Per the no-self-reference rule, that head SHA and its final test
  evidence belong in PR metadata rather than another self-recording commit.

## Next safe commands

1. Commit this worklog-only evidence update and run the final immutable head's
   full Python 3.10/3.12 suites, PostgreSQL DM module, workflow-equivalent
   coverage selection, and blocking lint/static checks.
2. Fetch `origin/master`, push, open the DM PR, and record the final full SHA
   and exact results in PR metadata.
3. Inspect checks, annotations, review comments, and unresolved threads once;
   merge only if the final gate is green and the worktree is clean.

## STOP conditions

- Official generations disagree in a way that cannot be distinguished safely
  from the record itself.
- Standard-name storage requires a destructive or ambiguous migration not
  bounded to the DM tables.
- A test failure reveals coupling outside the stated DM scope.
- Credentials or a remote state change would be required before the local
  contract can be established.
