# HR Official Contract Worklog

- Started: 2026-08-18 (Asia/Tokyo)
- Objective: audit and repair the HR payout/refund record parser, native and
  standard storage identity, validation, migration, cancellation semantics,
  importer/realtime behavior, metadata, tests, and public documentation against
  pinned official JV-Data sources.
- Minimum scope: HR only. Unrelated record types and generic refactors are
  excluded unless an HR correctness or data-integrity repair cannot be made
  safely without them.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_hr_official`; remove after
  merge.
- Branch: `agent/hr-official-contract-20260818`
- Base / production master at start:
  `c748da1b0ff9d3c39a1ab455112b9561b6343f39`
- Dependency: AV official-contract PR #210 merged first at the base SHA above.
- Package version at start: `2.0.0.dev0`.

## Review and implementation model

- This iteration covers payout identities, repeated ticket structures, status
  semantics, schema migration, and durable readback, so it is classified as a
  complex data-integrity change.
- Claude Code Fable will be attempted once for the implementation/audit if its
  authenticated session is available. If authentication or quota prevents it
  from reading or acting, that failure is not evidence and Codex continues as
  explicitly authorized by the user.
- Findings will be collected from official-source and independent critical
  reviewers before one repair batch. New validators/gates require a recorded
  red negative plus paired green positive before implementation is accepted.

## Required sequence

1. Re-derive HR physical length, every scalar/repeat span, ordered official key,
   DataKubun domain/history, payout/refund units and sentinels from pinned
   4.8/4.9 workbooks, SDK 5.0 manifest/source, and relevant official/community
   discussions.
2. Compare parser, native/standard/realtime schemas, mapping, importer/single
   paths, metadata, migration verification, docs, and every existing HR test.
3. Aggregate concrete findings; add the minimum failing contract test on the
   unchanged base and record the red result before changing validation/storage.
4. Implement one bounded HR repair and verify actual SQLite and fresh
   PostgreSQL durable storage, provider order, update/erase behavior, caller
   transactions, Dual orientation, unsafe-schema no-mutation, and readback.
5. Freeze an exact clean candidate, run focused/workflow/package gates, obtain
   independent critical reviews, resolve GitHub threads to zero, and merge only
   when all required checks are green.

## Current state

- A new clean worktree was created from freshly fetched `origin/master` at the
  base SHA above. No production code or test has been changed.
- AV PR #210 is merged at the base SHA. Its final candidate, local tests,
  independent reviews, GitHub checks, and unresolved-thread gate were green.

## Official-source audit and pre-implementation findings

- Pinned `JV-Data4802.xlsx` and `JV-Data4901.xlsx` rows 216-295, plus the
  tracked SDK 5.0 manifest, independently agree on a 719-byte HR record, 202
  expanded SDK leaves, status domain `0/1/2/9`, and ordered key
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`.
- The current parser reads only the first of the three official 16-byte
  reserved entries and drops six scalar leaves. Native `NL_HR`/`RT_HR`
  likewise expose only `Yobi1..3`.
- Standard `HARAI` has no primary key and no native-to-standard payout aliases.
  SQLite, PostgreSQL 16, and Dual probes reported successful imports while all
  sampled standard payout columns were `NULL`; repeated status `1 -> 2 -> 9`
  accumulated duplicate rows.
- HR has no record-specific pre-coercion validator. SQLite and PostgreSQL 16
  accepted malformed keys and payout values; a status-0 `RaceNum='1X'` was
  coerced to race 1 and deleted an unrelated valid row.
- HR is absent from strict schema preflight. Wrong/missing primary keys,
  nullable keys, wrong types, harmful extra uniqueness, and a deferrable
  PostgreSQL primary key were accepted until data loss or DML failure.
- PostgreSQL collapses same-key HR rows inside one bulk upsert. The durable
  final state is correct, but importer statistics undercount accepted provider
  operations; SQLite and sequential imports count them all.
- Official change history row 249 records the 2004 same-length reuse of an HR
  reserved span for trifecta data. The current provider still returns one
  719-byte layout for historical RACE setup. The contract will not invent an
  unsupported old physical parser: races before 2004-08-14 may carry the
  blank/zero non-sale representation, while nonblank trifecta-like payload for
  that period is rejected rather than mislabeled. The boundary is based on
  race date, not MakeDate.
- Official community topic 304 confirms that realtime HR popularity may remain
  blank until all finish positions are finalized. Validation must therefore
  allow blank popularity and must not make it a live-row requirement. Topic 64
  also supports storing the complete provider payload instead of filtering
  child values by flags.

## Independent reviewers and Claude attempt

- Three read-only Codex reviews were run against exact base
  `c748da1b0ff9d3c39a1ab455112b9561b6343f39`. They independently reproduced
  the standard payout loss/keylessness and validation/schema fail-open classes;
  two used fresh disposable PostgreSQL 16 and removed their containers.
- Claude Code `2.1.233` was attempted with `--model fable --effort high` and
  session `1f0f6c64-7284-47c6-a1f5-5892d999a5f7` because this iteration
  changes validators, identity, and transaction-facing storage behavior. Its
  OAuth session had expired and could not refresh, so no Claude output is used
  as evidence. The temporary review worktree was removed. Codex continues as
  explicitly permitted by the user.

## Aggregated repair boundary

1. Parse and store all three reserved entries while preserving the legacy
   `Yobi1..3` names and adding `Yobi4..9`.
2. Add complete `HARAI` aliases and the exact non-null six-column primary key.
3. Validate HR key/body fields before coercion in both batch importers, the
   single-record path, and realtime; status 0 validates only its exact key and
   leaves the body opaque.
4. Strictly verify `NL_HR`, `RT_HR`, and `HARAI` types, capacities,
   nullability, exact PK, harmful uniqueness, and PostgreSQL PK usability on
   every migration target before unrelated additive mutation.
5. Count accepted same-key HR provider operations consistently with SQLite
   while preserving provider order and exact erase semantics.

## Red-first evidence on unchanged base

- Added one compact official contract fixture and test module before changing
  production code. Command:
  `.venv/bin/python -m pytest -q tests/test_hr_official_contract.py
  --basetemp=/tmp/jrvltsql-hr-red --no-cov`.
- Exact base result: `8 failed`. Concrete failures were missing `Yobi4`, four
  malformed keys accepted by the raw parser, status-0 `RaceNum='1X'` accepted
  by the importer header gate, standard `HARAI` retaining 4 rows instead of 2,
  and a wrong seven-column native PK accepted through DML. This is the required
  proof that the new checks can reject the previously green defects.
- A paired 2004 boundary contract was then added: a 2004-08-13 record must keep
  bytes 604-717 in `LegacyReserved604_717Hex` and leave canonical trifecta
  fields empty, while 2004-08-14 uses current trifecta fields. This policy
  preserves undocumented old bytes without asserting that they were always
  blank and prevents them from being mislabeled as trifecta payouts.
- A second official-oracle pass found no workbook or community rule that fixes
  status-9 HR body values as blank, zero, or populated payouts. The repair now
  preserves raw bytes 28-717 in `OpaqueStatus9Body28_717Hex`, stores only the
  six-part key and cancellation state in ordinary columns, and keeps caller-
  built status-9 bodies semantically opaque. This avoids asserting an
  undocumented cancellation payout layout while retaining raw audit evidence.

## STOP conditions

- Stop before mutation if official HR key, status, payout unit, sentinel, or
  repeated-entry semantics remain ambiguous.
- Stop on worktree drift outside this worklog before implementation starts.
- Stop before merge on failed required test, unsafe schema mutation, durable
  count/stat mismatch, unresolved review thread, dirty worktree, or absent
  exact-SHA evidence.
- Do not claim 64-bit SDK support without an installed official x64 runtime
  test, and do not publish private implementation provenance or local paths.

## Implementation and verification progress

- Implemented the aggregated HR boundary in the parser, native/realtime and
  standard schemas, both batch importers, the single-record path, realtime,
  schema metadata, history oracle, and public migration documentation.
- `NL_HR`, `RT_HR`, and `HARAI` now use the ordered six-part official key and
  reject nullable, wrong-type, wrong-capacity, extra-unique, exclusion, and
  unusable PostgreSQL primary-key layouts before DML. Existing incomplete HR
  tables remain a rebuild/reimport boundary rather than being additively
  blessed.
- Raw status 9 retains bytes 28-717 only in the opaque audit field; every
  ordinary body/payout column is explicitly cleared on replacement. A fresh
  PostgreSQL probe caught that the single-record update path initially retained
  old payout columns, and the common cleaner was repaired before this candidate
  was accepted.
- Fresh disposable PostgreSQL 16 verification passed `63` HR contract cases,
  including native/standard, regular/optimized/single, auto-commit true/false,
  provider order, status-9 clearing, realtime, unsafe schema, and both Dual
  orientations. The dedicated container was removed after the run.
- SQLite affected coverage passed `323` tests with `23` skips and `9` subtests.
  The first full suite then exposed eight legacy tests and one performance
  fixture that still treated a header-plus-spaces HR envelope or partial caller
  dictionary as valid. Those fixtures were changed to construct complete
  official HR records; the validator was not weakened. The final Python 3.12
  suite passed `3200` tests, skipped `277`, and passed `20` subtests.
- Workflow-equivalent fatal flake8 (`E9,F63,F7,F82`) reports `0`; the workflow
  test-gate validator passes; `uv lock --check` passes. Full Ruff remains an
  advisory legacy-debt report and was not used to reformat unrelated files.
- A fresh PEP 517 wheel and sdist build passed the distribution-content gate
  and extracted-wheel SQLite init smoke. The wheel had `100` members and the
  sdist `121`; both contained zero `specs/` entries and zero removed
  `crawler_audit_*` documents. Strict MkDocs build also passed.
- Actual provider acquisition is intentionally not credited to this HR
  candidate; the cumulative release candidate must
  repeat the pinned-SHA fresh-download, parse, EOF/close, and durable
  SQLite/PostgreSQL readback gate before release.

## Published candidate

- Initial implementation commit:
  `d5db5de839b40fb9d8b9867d729e615913473b28`.
- Draft PR: `miyamamoto/jrvltsql#211`, targeting `master` from
  `agent/hr-official-contract-20260818`.
- The branch was pushed only after confirming `origin/master` remained the
  recorded base, the worktree was clean, and the local test/package evidence
  above was complete. Independent Codex review is the next gate; do not mark
  the PR ready or merge before its findings are aggregated and resolved.
