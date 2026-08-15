# TM current-layout compatibility worklog

## Objective and minimum scope

- Bring jrvltsql's `TM` parser and accumulated/realtime persistence paths into
  exact agreement with the official JV-Data physical and mutation contracts.
- Audit both older and current official specifications plus the official
  developer community before choosing compatibility behavior.
- Preserve every official horse entry without weakening record-length,
  record-type, delimiter, key, transaction, or migration checks.
- Keep this iteration limited to `TM`; documentation/privacy/package cleanup,
  the final live acquisition proof, and release work remain later iterations.

## Repository and version identity

- Repository: `miyamamoto/jrvltsql`
- Dedicated worktree:
  `/home/keiba/scratch/20260816_jrvltsql_tm_layout`
- Branch: `agent/tm-current-layout-20260816`
- Base, initial HEAD, and initial `origin/master`:
  `b01a92634056e2bc574c92c257adea89f6b8b271`
- Latest published tag at start: `v1.6.10`
- Production/release status: this branch is an unreleased candidate. Release is
  downstream of all official-layout iterations and a fresh live-provider
  acquisition-to-database validation on final merged code.

## Dependency order

1. PR #180 (`DM`) was merged first as
   `b01a92634056e2bc574c92c257adea89f6b8b271`.
2. This `TM` iteration starts from that merge SHA and must merge before the next
   official-layout iteration starts.
3. Documentation/privacy/package cleanup, jrvltsql release, jrvltsql-nar work,
   and jvlink-mcp-server work remain later dependent iterations.

## Initial observed state

- The tracked compatibility audit records official `TM` length 141 and marks
  the implementation partial because it declares length 39 and reads only one
  of the 18 horse entries.
- `src/parser/tm_parser.py` accepts short input, places the delimiter at bytes
  38-39, and returns only `Umaban`/`TMScore` for the first slot.
- Native `NL_TM`/`RT_TM` tables are keyed per horse, while the standard schema
  already exposes the official wide `TAISENGATA_MINING` shape. Canonical table
  mapping, revision replacement, deletion, and legacy migration behavior still
  require implementation-level verification.
- Table metadata and comments currently mislabel TM as time-type/time-master;
  these are documentation correctness findings within the affected surface.

## Official and community re-audit

- JV-Data 4.8.0.2 and 4.9.0.1 specify the same 141-byte physical record:
  bytes 1-31 are the record/race header and `MakeHM`; 18 repeated six-byte
  entries start at byte 32; CR/LF is at bytes 140-141. Each entry is `Umaban`
  two bytes followed by `TMScore` four bytes.
- SDK 5.0.0 independently agrees in its C++, C#, and VB structures. The C#
  structure allocates a 141-byte buffer, iterates `32 + (6 * i)` for all 18
  entries, and reads the delimiter from byte 140.
- There is no old/current physical-layout split between the audited official
  generations. Version 4.0.0 added this format, and the repository's 39-byte
  shape is exactly the 31-byte prefix plus one entry plus CR/LF. It is a
  truncated reconstruction, not a supported historical JV-Data format.
- The score is an official four-byte fixed-point field representing 000.0 to
  100.0, with the rightmost digit as the tenths place. Blank unused horse slots
  use the documented space initial value.
- Official community support confirms accumulated DM/TM use `MING`, realtime
  TM uses `0B17`, and accumulated mining is the same prediction content as the
  realtime feed:
  <https://developer.jra-van.jp/t/topic/284> and
  <https://developer.jra-van.jp/t/topic/89>.
- Community correction history confirms mining revisions and deletions must be
  processed in delivery order and not collapsed using an importer timestamp:
  <https://developer.jra-van.jp/t/topic/95> and
  <https://developer.jra-van.jp/t/topic/91>.
- A 2026 official-community clarification says the app and Data Lab values for
  TM match, unlike the app's derived time-type display. Therefore this path
  must preserve the official TM score rather than apply an unpublished
  conversion: <https://developer.jra-van.jp/t/topic/856>.

## Validation and review policy

- Codex-only implementation and review; do not use Claude Code.
- Add the minimum paired red/green contract before changing production code,
  and record the actual base-code failure here.
- Validate the final immutable full SHA with focused and full suites, supported
  Python generations, disposable PostgreSQL coverage for storage behavior,
  critical lint/compile/static checks, and one aggregated exact-SHA review.
- Do not merge on a failed executable check, unresolved actionable finding,
  unresolved review thread, base/head drift, or dirty worktree.

## Red-first regression evidence

- Before changing production code, added `tests/test_tm_official_contract.py`
  against base-plus-worklog commit
  `adc885d2b474b0a07665b9cf86af81420b741438`.
- Command:
  `pytest -q -p no:cov -o addopts='' --basetemp=/tmp/jltsql-tm-red tests/test_tm_official_contract.py`
- Result: exit 1, `30 failed, 2 skipped in 0.64s`. The first failure was
  `assert TMParser.RECORD_LENGTH == 141`, with actual value 39. The remaining
  failures demonstrated acceptance of truncated/corrupt records, single-entry
  parsing, absent complete-snapshot revision/deletion, wrong standard mapping,
  lossy native score typing, and keyless/legacy standard tables not failing
  closed. This is the required proof that the new checks can reject the old
  unsafe behavior; the paired green run remains pending.
- The aggregated review of source candidate
  `46926792663fa4d51428db275b32c966583ed96e` found one additional migration
  gap: direct native import bypassed table initialization and allowed an old
  integer `TMScore` column to coerce `0201` to `201`. Before adding the native
  verification gate, the paired importer regression failed with
  `2 failed in 0.26s`; neither importer raised and both replaced the existing
  row. This is the red proof for the fail-closed native type check.

## Implementation and validation state

- Replaced the 39-byte parser with an exact 141-byte byte-sliced parser. It
  validates record type, CR/LF, the TM `DataKubun` domain, numeric headers,
  horse number uniqueness/range, blank-slot consistency, and the documented
  000.0–100.0 score range; populated slots expand into native rows with one
  shared official wide record.
- Generalized the already-tested DM snapshot helpers to cover both mining
  formats. Native `NL_TM`/`RT_TM` revisions validate the whole replacement,
  delete the six-key race snapshot, and insert every current horse inside the
  caller transaction. `DataKubun=0` deletes the whole race, including realtime.
- Standard mode now canonically maps TM to keyed `TAISENGATA_MINING`, inserts
  one wide row, and refuses legacy-only `TIME_MASTER` or a keyless canonical
  table without modifying existing rows.
- Native schemas preserve the SDK's four-byte score as lossless text rather
  than silently exposing the implied-decimal digits as an unscaled integer.
  Each importer/updater verifies the native TM schema once per table before
  mutation, so legacy integer tables fail closed without per-record metadata
  query overhead. Corrected metadata and public data-support/audit text within
  this surface.
- Paired green run for the initial new contract: `30 passed, 2 skipped in
  0.59s`. After the native-type review fix, the complete TM module passes with
  `33 passed, 3 skipped`; related TM/DM/realtime/importer coverage passes with
  `141 passed, 6 skipped, 3 subtests passed in 1.60s`.
- Expanded SQLite/parser/importer/realtime/schema regression run after the
  migration-gate correction: `926 passed, 7 skipped, 3 subtests passed in
  3.12s`.
- Disposable PostgreSQL 16 ran the final corrected TM contract with integration
  enabled: `36 passed in 0.95s`. Both accumulated importer classes stored and
  revised native 18-to-17 rows, standard mode revised one wide row, realtime
  replaced 18-to-17 rows, and every path deleted the race. The disposable
  container was stopped and removed.
- Source candidate `46926792663fa4d51428db275b32c966583ed96e` passed the full
  Python 3.12 suite with `2183 passed, 57 skipped, 3 warnings, 6 subtests`, and
  a sequential Python 3.10 compatibility run with the same totals. This was
  superseded by the native-type review fix.
- Corrected source candidate `094a0b8ee5b87a222abae81b9cd3ee543ea05eba`
  passed the full Python 3.12 suite with `2186 passed, 57 skipped, 3 warnings,
  6 subtests`, and the sequential Python 3.10 compatibility run with the same
  totals. Its exact workflow selection passed with `864 passed, 2 skipped, 3
  warnings, 3 subtests` and 56% coverage. Candidate and exact base both report
  the same 77 mypy errors in 20 files.
- `git diff --check`, compileall, blocking flake8, and focused Black checks
  pass. The final worklog-only commit receives focused/static validation; its
  full SHA and exact results are recorded in PR metadata to avoid a
  self-referential evidence commit loop.

## Next safe command and STOP conditions

- PR #181 was opened at final pre-review head
  `ffbac21628d58fa84646bdce4b787fee181ca243`. Exact-head Actions test/lint
  passed; performance was intentionally skipped by the workflow. The single
  native Copilot review covered all 15 changed files.
- Aggregated review produced three actionable findings. Copilot found that both
  TM metadata entries omitted meeting number/day from the documented native
  key. Codex found that importer-supported `headRecordSpec` and Japanese
  record-type aliases bypassed mining snapshot/delete and TM schema guards.
  CodeRabbit found that a standalone realtime snapshot could delete the old
  race and return failure without rolling back when insertion failed.
- Red evidence before these review fixes:
  - metadata contract: `1 failed`; the documented key differed at index 2 and
    referenced neither meeting number nor meeting day;
  - combined alias/rollback selection: `5 failed, 2 passed`; both native
    importers retained stale horse 2 after a 17-horse alias-key revision, and
    both accepted the legacy integer score schema instead of raising;
  - isolated realtime failure after neutralizing an optional traceback-renderer
    incompatibility: `1 failed`; stored rows were 0 instead of the prior 18.
- The fix centralizes all three accepted record-type aliases, applies them to
  DM/TM storage and TM verification, records explicit transaction ownership in
  the database abstraction, and makes realtime mining replacement open and
  close a transaction only when no caller transaction is active. Owned
  rollback failure invalidates the connection; monitor-owned cycle boundaries
  remain owned by the monitor. Both NL_TM and RT_TM metadata now describe the
  complete conceptual native key.
- Paired green selection: `8 passed, 30 deselected`. Broader TM/DM/realtime/
  importer/database/metadata/monitor coverage: `213 passed, 10 skipped, 3
  subtests passed in 4.35s`.
- Non-actionable review items were not allowed to expand scope: trusted
  internal SQL identifiers remain parameterized for all values, and a helper
  rename was only stylistic. Two test-readability nits were folded into the
  already-required review commit without production impact.
- Next: commit the aggregated review fix, run full supported-Python,
  workflow-equivalent, disposable PostgreSQL, and static validation on the new
  immutable candidate, then push once without requesting a second Copilot
  review. Reply to and resolve every existing thread before the final gate.
- STOP if official sources disagree, a safe migration cannot preserve existing
  rows, any executable check fails on the candidate, or the branch/base drifts.
