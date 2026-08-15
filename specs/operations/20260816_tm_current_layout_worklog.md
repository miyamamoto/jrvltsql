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

## Implementation and validation state

- No production changes yet.

## Next safe command and STOP conditions

- Next: finish the standard/native importer contract inspection, add the
  minimal official-layout/storage tests, and run them against this base.
- STOP if official sources disagree, a safe migration cannot preserve existing
  rows, any executable check fails on the candidate, or the branch/base drifts.
