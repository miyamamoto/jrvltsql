# Standard UMA official-key repair worklog

## 2026-08-17 — iteration start

- Objective: make standard-schema UM ingestion preserve the official JV-Data
  identity by storing `KettoNum` and enforcing `PRIMARY KEY (KettoNum)` on
  `UMA`, with existing incompatible tables rejected before any mutation.
- Minimum scope: standard `UMA` DDL, schema/type/ordered-key verification,
  normal and optimized batch import, single-record import, SQLite and
  PostgreSQL persistence/idempotency, documentation, and red-first tests.
  Native `NL_UM` is already keyed correctly and must not change.
- Explicitly out of scope: CS/COURSE, WE/JC, SE/UMA_RACE, remaining physical
  DataKubun=0 erase paths, release metadata, tags, and releases. Those are
  separate dependent iterations after this PR.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated `$WORKSPACE/jrvltsql_um_key` checkout.
- Branch: `agent/um-standard-key-20260817`.
- Base/HEAD/origin master: `1f317f0d1caec67d4c9f4ad15181780990e5e8f3`
  (PR #203 squash merge).
- Published release remains v1.6.10; repository version remains unreleased
  `2.0.0.dev0`. This iteration does not authorize a release.
- Official oracle: JV-Data 4.8.0.2 and 4.9.0.1 both mark only `KettoNum` as
  the UM key; SDK 5.0.0 uses the same 10-byte field. The current standard
  `UMA` table omits both that column and a primary key, so a valid UM record
  cannot be stored in standard mode.
- Migration policy: inspect every existing target before `ALTER`, `INSERT`,
  `DELETE`, or `COMMIT`. Missing/wrong key, key type/capacity mismatch, or a
  keyless legacy table must raise `SchemaMigrationError` and leave the target,
  unrelated sentinel data, and caller transaction state unchanged. Do not
  auto-rebuild or infer already-lost identity.
- Red-first minimum: prove current standard UM import fails; prove a keyless or
  wrong-key existing `UMA` is rejected without mutation; then pair with fresh
  SQLite/PostgreSQL two-key coexistence, exact-key update/idempotency, both
  batch importers, single record, and caller-owned transaction controls.
- Implementation/review model: Codex. Claude Code is not counted because its
  configured quota is unavailable. Use independent Codex critical review on
  the frozen exact candidate.
- Next safe action: inspect the current standard mapping, schema migration and
  verification flow, extend an existing UM/standard-schema contract with the
  smallest red case, and run it against this exact base before production
  edits. STOP if the official key/type is uncertain, any proposed migration
  mutates an incompatible legacy table, or the scope expands into other record
  types.

## 2026-08-17 — red-first evidence on the base SHA

- Environment: locked `uv sync --frozen --all-extras` (Python 3.13.5).
- Command: `pytest -q tests/test_um_parser_layout.py -k 'standard_schema or
  standard_storage or wrong_key' --no-cov` against exact base
  `1f317f0d1caec67d4c9f4ad15181780990e5e8f3`.
- Result: expected red, `5 failed, 100 deselected`.
  - Schema contract raised `KeyError: 'KettoNum'`.
  - Both batch importers reported every valid standard UM row as an incomplete
    primary key and imported zero rows.
  - Both batch importers failed to reject an existing `UMA PRIMARY KEY
    (Bamei)` and performed many additive `ALTER TABLE` operations before
    returning, proving the preflight was fail-open while the expected schema
    declared no key.
- This red evidence binds both sides of the repair: a fresh table must persist
  and upsert by the official key, while an incompatible legacy table must be
  rejected before the first mutation.

## 2026-08-17 — actual PostgreSQL exposed the active-horse sentinel bug

- A disposable PostgreSQL 16 run of the new positive contract failed for both
  importers: each attempted to write the official active-horse `DelDate` value
  `00000000` into standard `UMA.DelDate DATE`, producing
  `date/time field value out of range` and importing zero rows. SQLite had
  accepted the invalid declared-type/value combination and therefore hid it.
- This is inside the minimum standard-UM persistence scope: fixing only the key
  would still leave normal current provider rows unstorable on PostgreSQL.
- Existing CH/KS official contracts already establish the lossless policy for
  this field: the provider's eight-character zero value is retained as text,
  not guessed into a date. A physical declared-type assertion was added first;
  before the schema edit it failed with `assert 'DATE' == 'VARCHAR(8)'`.
- Repair boundary: standard `UMA.DelDate` becomes `VARCHAR(8)` only. Valid
  `MakeDate` and `BirthDate` remain SQL dates, and native `NL_UM` is unchanged.

## 2026-08-17 — implementation and focused verification

- Production delta is limited to standard `JRAVAN_SCHEMAS["UMA"]`:
  `KettoNum VARCHAR(10)`, `PRIMARY KEY (KettoNum)`, and lossless
  `DelDate VARCHAR(8)`. Mapping and native `NL_UM` code did not change.
- SQLite focused bundle after implementation and formatting:
  `138 passed, 2 skipped`. It includes the complete 1609-byte parser layout,
  two-key coexistence, exact-key update, both batch importers, single-record
  caller rollback, incompatible-PK no-mutation, and generic migration suites.
- Fresh disposable PostgreSQL 16 after the sentinel repair: `2 passed,
  106 deselected`. Both importers stored two current UM rows, updated only the
  matching key, preserved `00000000`, and rejected an existing wrong-key table
  without schema or row changes. The container and its isolated schemas were
  removed after the run.
- `git diff --check` passes. File-scoped `ruff` still reports only pre-existing
  debt in the touched legacy files (typing `Dict`, import sorting, UTF-8 header,
  and `zip(strict=...)`); none was introduced by this delta. Required fatal
  lint/test gates will be run on the frozen candidate rather than mixing an
  unrelated style cleanup into this key repair.
- Public `docs/data_support.md` now states the official key, the zero deletion-
  date storage contract, and the operator backup/recreate/reimport boundary for
  old keyless or wrong-key `UMA` tables.
- Pre-freeze gates: `uv lock --check`, fail-closed test-gate validation,
  `compileall`, fatal flake8 (`E9,F63,F7,F82`, count 0), strict MkDocs, and
  `git diff --check` all passed. `flake8` and MkDocs were installed only into
  the ignored disposable worktree virtualenv; dependency manifests did not
  change.
- Next safe action: run affected importer/schema tests and documentation gates,
  inspect the final diff, commit a frozen candidate, then request one batched
  independent Codex critical review. STOP on any row-count/statistics mismatch,
  mutation of a legacy table, test failure, or candidate drift.

## 2026-08-17 — frozen-candidate critical review and batched repair

- Frozen candidate: `c1c6e55fa7f0d8640c0aec468c7397412a9b17a4`,
  clean at the start and end of both read-only reviews.
- Review method: two independent Codex critical reviewers, one bound to the
  official 4.8.0.2/4.9.0.1 + SDK 5.0 oracle and one attacking migration,
  transaction, Dual, and actual-database integrity. Claude Code remained
  unavailable and was not counted. Findings were collected before editing and
  repaired together to avoid a per-finding review loop.
- Adopted findings:
  1. The successful standard import silently discarded the compact 27x6
     placing-count leaves, four running-style leaves, and `TorokuRaceSu`.
  2. An extra `UNIQUE`/exclusion constraint, or a PostgreSQL deferrable or
     otherwise unusable primary key, could change replacement semantics after
     passing preflight and silently remove a different horse.
  3. Caller-built `KettoNum` values were not constrained to the official exact
     ten ASCII digits, so SQLite and PostgreSQL accepted different invalid
     identities.
- Red-first evidence on exact `c1c6e55...`: the combined focused selection
  produced `22 failed`; the additional compact-cardinality case separately
  failed because malformed `SogoChaku="001"` was imported successfully. The
  failures covered the missing schema column/readback, six extra-UNIQUE entry
  modes plus Dual, and short/long/alphabetic/non-ASCII keys through normal,
  optimized, and single-record entry points.
- Repair boundary:
  - Standard UM translation now expands all 27 compact 18-character groups to
    162 three-character columns and the 12-character running-style group to
    four columns. Present compact fields must have exact ASCII-digit
    cardinality and cannot conflict with pre-expanded fields.
  - Standard `UMA` now includes `TorokuRaceSu VARCHAR(3)`. A completeness test
    binds all 227 schema columns to parser output (excluding only the physical
    CRLF delimiter), not just selected sentinels.
  - The existing WF catalog verifier was generalized without weakening WF.
    Standard `UMA` preflight now rejects additional UNIQUE/exclusion indexes
    and requires one valid, ready, immediate, non-deferrable PostgreSQL primary
    key before any additive migration.
  - Shared import-header validation now requires UM `KettoNum` to be exactly
    ten ASCII digits before schema preflight or DML. It intentionally does not
    invent a semantic year/all-zero restriction unsupported by this iteration's
    official evidence.
- Green evidence after the batched repair:
  - UM file: `127 passed, 4 skipped` on SQLite.
  - Affected UM/migration/WF catalog selection: `164 passed, 6 skipped, 103
    deselected`.
  - Fresh disposable PostgreSQL 16: `5 passed, 127 deselected`, covering both
    batch importers' complete expanded-body readback, representative single
    record readback, extra UNIQUE rejection, deferrable-PK rejection, sentinel
    preservation, exact-key update, and old wrong-key no-mutation.
  - The PostgreSQL container was removed and its exact-name container listing
    was empty after cleanup. `git diff --check` and compileall passed.
- Final local gate on the repaired tree: full suite `2823 passed, 136 skipped,
  22 subtests passed` in 57.67 seconds. `uv lock --check`,
  `scripts/validate_test_gate.py`, compileall, fatal flake8
  (`E9,F63,F7,F82`), strict MkDocs, and `git diff --check` all passed.
- Exact committed code candidate
  `2026fbc84e6cc7c93aed6d85de1b75ff852c73be` was exported with
  `git archive`, built through isolated PEP 517 into wheel and sdist, and
  passed both the distribution-content gate and extracted-wheel init/SQLite
  bootstrap smoke. Both artifacts excluded `specs/`; the temporary archive
  and artifacts were removed after verification.
- Bounded final review of exact
  `9d068cf9f9198412729b11a281caa51a07964a8f` found no production
  P0/P1/P2 issue. Both reviewers independently read back all 227 standard
  columns on PostgreSQL; the migration reviewer also attacked extra/partial
  UNIQUE, exclusion, deferrable/invalid primary keys, both Dual backend
  orders, all entry/commit modes, and invalid keys without finding a bypass.
- The official-oracle reviewer did find one test-only false-green: each
  18-character placing group used one three-digit sentinel six times, so a
  deliberately mutated expander that copied first-place into places 2-6 still
  passed. This mutation was actually reproduced against the old fixture.
  The fixture now uses 162 distinct ordered sentinels (`001` through `162`),
  and the complete translation/readback expectations bind every rank. The UM
  file passes `127 passed, 5 skipped`; a fresh PostgreSQL 16 rerun of all five
  PostgreSQL UM contracts passes with the new first/middle/last values. The
  disposable container was removed afterward. Production source did not
  change for this test-oracle repair.
- Remaining iteration action: run final required local gates on one frozen
  full SHA, request one bounded two-reviewer confirmation of the repaired
  finding classes, then publish PR/review/merge only if the worktree is clean,
  tests are green, and unresolved GitHub threads are zero. Do not release from
  this iteration; the dependent key/erase/release work remains separate.

## 2026-08-17 — PR #204 review response

- PR #204 was opened from exact candidate
  `6cd699aa3bc9b82b902e06be2625243a02ad1e33`. GitHub lint, test, and Windows
  batch-syntax jobs passed; the performance job was conditionally skipped.
  CodeRabbit completed successfully. Copilot was requested once at PR creation
  but reported quota exhaustion and was not re-requested.
- CodeRabbit reported two test-only improvements after reviewing the complete
  change set. They were collected and handled in one batch: the DualDatabase
  unsafe-UNIQUE regression now exercises both the primary and secondary
  migration target, and the PostgreSQL fixture rolls back an aborted
  transaction before dropping its temporary schema. Production code was not
  changed by this response.
- Next safe action: run the UM-focused SQLite and disposable PostgreSQL tests,
  required static/documentation gates, commit and push one review-response
  candidate, reply to and resolve the inline thread, then require exact PR head,
  successful checks, unresolved thread count zero, and a clean worktree before
  merge. STOP on any focused failure or head/worktree drift.
- Review-response verification is green: the complete UM file passed `133
  passed` against SQLite and a fresh disposable PostgreSQL 16 instance. This
  includes the new primary/secondary Dual cases and all five PostgreSQL
  contracts. The exact-name PostgreSQL container was removed and its filtered
  container listing was empty afterward.
- `uv lock --check`, `scripts/validate_test_gate.py`, compileall, fatal flake8
  (`E9,F63,F7,F82`), strict MkDocs, and `git diff --check` all passed on the
  review-response tree. The MkDocs output directory was a disposable external
  `mktemp` directory and was deleted after the build.
- The response changed only the UM test file and this tracked worklog. The
  production source diff from `6cd699aa...` remains empty. Next safe action is
  one commit/push, exact-head CI, a courteous inline reply, thread resolution,
  and final merge gate; no broad review or full-suite replay is warranted for
  this test-only follow-up under the review-loop policy.
