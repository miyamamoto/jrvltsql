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
