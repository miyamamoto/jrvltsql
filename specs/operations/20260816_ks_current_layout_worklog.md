# KS current-layout implementation worklog

## Iteration identity

- Objective: replace the partial KS jockey-master implementation with an
  official-layout, lossless, fail-closed implementation and storage contract.
- Minimum scope: KS parser, native/standard schemas and mappings only where the
  official current record requires them, accumulated importer behavior,
  compatibility fixtures/tests, public support documentation, and this audit
  evidence. No unrelated partial format is changed in this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260816_jrvltsql_ks_layout`
- Branch: `agent/ks-current-layout-20260816`
- Base/full SHA: `888e3cb4d572320512da6da4854c5cc6b66bb37d`
- Previous dependent merge: PR #181, TM official-layout merge
  `888e3cb4d572320512da6da4854c5cc6b66bb37d`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release-lock or publication iteration.
- Agent/model: Codex only, per the user's explicit instruction to continue the
  review with Codex. No Claude session is used.

## Starting observations

- The tracked official compatibility audit marks KS as `partial`: the public
  parser length is 772 bytes while JV-Data 4.9.0.1 documents 4173 bytes.
- The current implementation stops inside the repeated jockey-performance
  region and therefore cannot prove that the complete current record was
  consumed or stored.
- Official JV-Data 4.8.0.2, 4.9.0.1, and SDK 5.0.0 definitions, plus relevant
  official developer-community corrections, must be compared before choosing
  whether any historical/current dual layout is legitimate.

## Official and community evidence

- JV-Data 4.8.0.2 and 4.9.0.1 both specify one 4,173-byte KS layout: 264-byte
  identity header, two 67-byte first-ride blocks, two 64-byte first-win blocks,
  three 163-byte recent-grade-win blocks, three 1,052-byte current/previous/
  career result blocks, then CR/LF at bytes 4,172-4,173. SDK 5.0.0 C#, C++ and
  VB structures use the same offsets and cardinalities. No official evidence
  establishes the repository's 772-byte shape as a historical JV-Data layout.
- The version history changes KS naming/descriptions and later adds explanatory
  notes, but shows no KS physical-length transition. Therefore this iteration
  rejects 772 bytes instead of treating it as a supported old version.
- Developer-community topic 79 records the official answer that JRA-VAN does
  not transform variant characters; the parser must preserve the delivered
  CP932 text rather than normalize names. Topic 290 confirms setup mode can
  resend all master rows. Topic 91 confirms delivery order matters when a
  delete and replacement share a key, so KS delete/upsert processing must
  preserve physical order. Topic 78 is a useful warning that a race-row jockey
  reference is not proof that a particular KS master was delivered; it does
  not alter the physical KS format.
- Primary/relevant sources:
  - `https://jra-van.jp/dlb/sdv/sdk/JV-Data4901.pdf`
  - `https://developer.jra-van.jp/t/topic/79`
  - `https://developer.jra-van.jp/t/topic/290`
  - `https://developer.jra-van.jp/t/topic/91`
  - `https://developer.jra-van.jp/t/topic/78`

## Red-first evidence

- Added `tests/test_ks_official_contract.py` before production changes and ran
  `python3 -m pytest tests/test_ks_official_contract.py --basetemp=$WORKSPACE/pytest_ks_red --no-cov -q`.
  Result on unchanged production code: `23 failed, 1 passed, 2 skipped`.
  Concrete failures included `KSParser.RECORD_LENGTH == 772`, acceptance of the
  old 772-byte/truncated/corrupt inputs, missing normalized result storage,
  missing standard `KISYU` key, and no coupled delete behavior.
- Before extending the race-day completeness gate, ran its two new negative/
  positive contracts against the old check. Result: `2 failed`; the old gate
  neither required `NL_KS_SEISEKI` nor rejected a two-row jockey result set.
  After implementation the same two tests passed.
- During the final Codex diff review, a rollback failure was found to be able to
  fall through to the generic parent-only batch retry. Added
  `test_ks_coupled_failure_never_enters_parent_only_batch_fallback` before the
  fix. It failed with `DID NOT RAISE DatabaseError` and logged the individual
  insert fallback. After blocking coupled KS records from that fallback, the
  same test passed.

## Implementation and decisions

- `KSParser` now requires exactly 4,173 bytes, `KS`, valid CR/LF, strict CP932,
  DataKubun `0/1/2`, and the documented ASCII-digit fields. The official table
  defines `0` as every numeric field's initial value, so zero-filled optional
  groups remain valid while malformed/spaced numeric payloads do not silently
  convert. Text is decoded as delivered; no character normalization is added.
- The 67 stored header fields contain both first rides, both first wins, and all
  three recent graded wins. The three 1,052-byte result blocks are normalized
  to exactly 176 columns in `NL_KS_SEISEKI` / `KISYU_SEISEKI`, keyed by
  `(KisyuCode, Num)`. Identifier-like numeric text retains leading zeroes;
  counts and monetary aggregates use integer types of sufficient width.
- Native and standard importers verify the keyed parent and child schemas before
  mutation, validate exact child cardinality/fields/parent revision, and apply
  parent plus children in one transaction. DataKubun `0` deletes children then
  parent. Physical delete/replacement order is retained in a batch. A rollback
  whose success cannot be confirmed invalidates/raises and cannot enter the
  parent-only generic fallback.
- The race-day gate now fails closed for a missing/unreadable KS result table,
  missing or non-`1,2,3` result rows, orphan rows, and parent/child MakeDate
  disagreement. The all-table counts and native/standard mapping/metadata were
  updated for the additional normalized table.
- No old/current dispatch was added. Both reviewed official document versions
  and SDK 5.0.0 use the same physical layout; accepting the repository's
  reconstructed 772-byte shape as provider input would hide data loss. The old
  fixture is used only to synthesize a current-shape regression record from its
  position-compatible prefix.

## Verification on the working-tree candidate

- Supported runtime: an isolated `uv` environment using CPython `3.12.11` and
  `.[dev,postgres]`. `python-dotenv` and `flake8` were installed only in the
  ignored test environment because the full legacy test collection imports the
  former while CI installs the latter separately; no dependency declaration was
  changed in this KS iteration.
- Workflow-equivalent selection under Python 3.12:
  `864 passed, 2 skipped, 3 subtests passed` with coverage, in 36.16 seconds.
- Full Python 3.12 suite after updating the one-table count contract:
  `2221 passed, 59 skipped, 6 subtests passed` in 46.10 seconds. The three
  warnings are pre-existing pytest warnings for test functions that return a
  boolean. An earlier full run exposed the three stale table-count expectations;
  two transient CLI assertions passed both in immediate isolation and in the
  clean full rerun.
- Final focused parser/schema/importer/race-day/E2E group:
  `75 passed, 8 skipped`. Final KS-only SQLite group: `31 passed, 4 skipped`.
- Disposable PostgreSQL 16 final run with integration opt-in:
  `35 passed`. This covered native and standard schemas, both importers,
  idempotent storage, physical new/delete/replacement order, and child-write
  failure rollback without a surviving parent. The exact disposable container
  was removed after the run.
- `compileall`, `git diff --check`, Black check on the new/replaced KS files,
  and the workflow's blocking flake8 selection
  `E9,F63,F7,F82` all passed. A broad Ruff diagnostic still reports existing
  repository-wide modernization/style findings in legacy files; no new
  correctness or undefined-name finding remains in this scope.

## Codex review disposition

- Rechecked every top-level offset and all repeated sub-offsets against the SDK
  C# setters and the 4.9.0.1 format table. The 264/134/128/489/3156/2 byte
  regions are gap-free and total 4,173 bytes; each result block consumes all
  1,052 bytes and 173 payload fields.
- Confirmed official initial-value semantics support the strict numeric checks,
  and that names preserve internal spaces/CP932 bytes while only fixed-width
  padding is stripped.
- Confirmed both schemas have the required keys and lossless text types for
  zero dates/identifiers, PostgreSQL BIGINT for ten-digit prize aggregates, and
  no persisted delimiter/private metadata.
- The only actionable finding in this review was the parent-only retry after an
  unconfirmed coupled rollback. It was reproduced red, fixed, and reverified as
  described above. No unresolved local finding remains.
- This is not a release candidate. A fresh real provider acquisition through
  parse and database verification remains mandatory after all remaining format
  gaps are complete and before any release. Package exclusion of tracked
  `specs/` is also reserved for the later release iteration.

## Plan and gates

- Extract the exact byte layout, repeated groups, data-kind domains, delimiter,
  and version history from official sources; compare every implemented field
  and schema column rather than trusting the current parser names.
- Inspect community reports for KS corrections, delivery order, deletion, or
  historical layout changes and distinguish authoritative facts from
  inferences.
- Add the minimum failing contract to the unchanged production implementation
  and record its actual red result before modifying parser/storage checks.
- Implement one complete current contract, or explicit old/current dispatch
  only if official evidence establishes more than one valid physical layout.
- Validate the immutable candidate with focused/full tests, supported Python,
  disposable PostgreSQL where storage changes require it, exact-head CI, one
  aggregated review, unresolved threads zero, and a clean worktree.
- STOP on conflicting official evidence, a schema migration that can lose
  existing rows, any executable failure, base drift, or unresolved actionable
  finding.

## Next safe command

- Commit the reviewed KS candidate, record its full SHA in the PR evidence,
  fetch `origin/master` to check for drift, push, open one focused PR, request
  the single native Copilot review, and merge only after exact-head tests,
  unresolved threads zero, acceptable CI, and a clean worktree are confirmed.
