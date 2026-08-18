# HN official-contract closure worklog

## Start state (2026-08-18)

- Objective: close the remaining HN breeding-horse master contract before the
  `2.0.0.dev0` development-test prerelease.
- Minimal scope: HN official key/body validation, status-0 exact physical erase
  and provider ordering/statistics, strict native `NL_HN` and standard
  `HANSYOKU` schema preflight, backend/Dual evidence, and directly affected
  docs/tests. Do not add an `RT_HN` table; HN is an accumulated BLDN master.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_hn_official`.
- Branch: `agent/hn-official-contract-20260818`.
- Base and starting HEAD: `8408bcf7e3580b72f25c027a3a4e0a138343447b`
  (`origin/master`, inventory PR #216 squash merge).
- Production/release version under development: `2.0.0.dev0`; no prerelease
  has been published.
- Starting worktree was clean.
- Implementer: Codex. No Claude Code session has been started for this
  iteration.

## Prior completed boundary

- PR #172 / merge `6dc55078dba33a7f4582d67e816276c25be2700e`
  corrected the official current 251-byte layout, rejects the obsolete
  245-byte physical record, preserves all native and standard fields, and
  establishes `HansyokuNum` as the native/standard key.
- The current parser/layout work is retained. This iteration does not reopen
  already-proved offsets merely because the earlier test module is not named
  `test_hn_official_contract.py`.

## Confirmed gaps at start

- HN is absent from `_OFFICIAL_ERASE_KEY_COLUMNS`, the provider-order set, and
  official-operation statistics. Native and standard `1 -> 2 -> 0` therefore
  leave a status-0 tombstone instead of deleting the keyed record.
- `validate_import_record_header()` performs only shared header/status checks
  for HN. Caller-built key-only rows, missing body, and malformed key values can
  reach storage.
- HN has no dedicated exact native/standard schema verifier. Generic additive
  verification is insufficient for types/nullability, generated or extra
  columns, harmful constraints, and PostgreSQL PK usability.
- HN is accumulated-only (`BLDN`); realtime storage/processing is N/A and must
  remain explicitly rejected/not routed rather than creating a new table.

## Red-first and implementation plan

1. Add one compact HN official-contract module by extending/reusing the existing
   layout builder. First run it against this base and record the actual red
   failures for:
   - valid live caller body and malformed/missing key/body;
   - exact-key `1 -> 2 -> 0` erase/order/statistics across DataImporter,
     OptimizedDataImporter, and single-record entry where supported;
   - unsafe native/standard schemas, including extra required/generated or
     uniqueness/constraint/PK defects, rejected before mutation;
   - SQLite, fresh PostgreSQL, and Dual orientation boundaries.
2. Implement the smallest shared HN validator, physical erase dispatch, strict
   schema verifier, and transaction-safe preflight needed to turn those reds
   green. Status 0 validates only header/key and treats the body as opaque.
3. Run affected focused tests, fresh PostgreSQL and Dual probes, exact full-SHA
   review, GitHub checks, and unresolved-thread-zero gate. Aggregate findings
   before one repair batch.
4. Merge the HN PR, clean this worktree/branch, fetch latest master, then begin
   SK in a new worktree.

## Red-first evidence (2026-08-18)

- Added the compact uncommitted regression module
  `tests/test_hn_official_contract.py` before modifying production code.
- Command (repository-supported Python 3.12 environment):
  `uv run --python 3.12 --extra dev python -m pytest -q tests/test_hn_official_contract.py`.
- Base result at full SHA
  `689531763cae6292dfa1d761fdddd88d6b64314b`: **24 failed, 1 passed**,
  exit code 1.
  - four parser-domain negatives were accepted;
  - four caller-built key/body/alias negatives were accepted;
  - all eight batch native/standard, owned/caller-owned erase paths left a
    stored status-0 tombstone;
  - all four single-record erase paths left the row stored;
  - all four unsafe-extra-column schemas reached normal DML handling instead
    of raising `SchemaMigrationError` during preflight.
- The paired positive was the status-0 exact-key/opaque-body header policy; it
  remained green. This proves the new checks can say no without broadening the
  body requirements for deletion commands.
- An earlier invocation selected an unsupported global Python 3.10 and failed
  collection. It is not counted as red-first evidence; only the corrected
  Python 3.12 run above is authoritative.

- A second bounded base probe added unsupported UNIQUE, CHECK, and FOREIGN KEY
  constraints to otherwise current `NL_HN` schemas. All three cases failed the
  new regression because the base verifier did not raise `SchemaMigrationError`
  before DML (**3 failed**, exit code 1). This red is kept as the evidence for
  the exact constraint census rather than adding one test per reviewer
  hypothesis.

- The first workflow-equivalent full-suite run exposed a real interaction that
  the compact contract had not yet fixed: official blank optional HN text was
  converted to SQL `NULL`, which conflicts with the new distinction between a
  validated blank provider value and a missing caller field. That run ended
  with **9 failed, 3478 passed, 399 skipped**; all nine failures were the same
  incomplete/blank HN fixture class, not unrelated product regressions.
- Before changing the converter, the existing HN contract was minimally
  extended with
  `test_hn_blank_optional_text_remains_an_empty_provider_value`. Against that
  candidate the native and standard cases both failed at storage
  (**2 failed**, exit code 1) because `BameiKana` became `NULL`. Production was
  then changed only for the three officially blankable HN text fields
  (`BameiKana`, `BameiEng`, and `SanchiName`) so a present blank remains `""`;
  missing/`None` remains invalid. The paired test then passed **2/2**.

## Implemented contract and green evidence (2026-08-18)

- `HNParser` now validates the complete current 251-byte body, official
  fixed-width numeric/code domains, CP932 capacities, the exact ten-digit
  `HansyokuNum`, and real `MakeDate`; obsolete 245-byte input remains rejected.
  Status 0 validates the header/key from the original bytes and does not decode
  the nonkey body.
- Both importer classes and the single-record entry validate caller-built HN
  before coercion, resolve standard aliases without accepting conflicts, apply
  status 0 as a physical exact-key erase, and count provider operations in
  order. HN remains accumulated-only and no realtime table was added.
- `NL_HN` and `HANSYOKU` now use the same NOT NULL official identity/body
  contract. The dedicated verifier rejects wrong types/capacities/nullability,
  generated or extra columns, additional UNIQUE/CHECK/FK constraints, and
  unusable PostgreSQL primary keys before mutation. SchemaManager and both
  standard/native preflight paths use the same verifier, including Dual
  targets independently.
- SQLite affected selection:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py
  tests/test_current_record_validation.py tests/test_data_kubun_entry_contract.py
  tests/test_migration.py -m 'not postgresql'` => **239 passed**.
- Expanded HN SQLite contract after backend/Dual negatives:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py` =>
  **69 passed, 9 skipped**.
- Fresh disposable PostgreSQL 16, with opt-in integration enabled:
  `tests/test_hn_official_contract.py` => **44 passed**. This includes both
  importers, native/standard, `auto_commit=True/False`, provider order/exact
  erase, deferrable-PK rejection, and mixed SQLite/PostgreSQL Dual orientation.
- Final directly affected SQLite selection after fixture and blank-value
  closure:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py
  tests/test_parsers.py tests/test_rc_official_contract.py
  tests/test_tk_official_contract.py tests/test_ys_official_contract.py
  -m 'not postgresql'` => **449 passed, 17 skipped**.
- Final expanded fresh PostgreSQL 16 selection (HN, layout/current-status,
  migration, metadata, and directly adjacent contracts) => **294 passed,
  3 subtests passed**. A separate real PostgreSQL readback probe confirmed
  native and standard blank provider values remained empty strings rather than
  `NULL`.
- A manual public `SchemaManager` probe against an unsafe existing HN schema
  returned failure and preserved the exact before/after schema, confirming the
  strict verifier rejects before additive mutation.
- Final workflow-equivalent repository suite under locked Python 3.12:
  `uv run --python 3.12 --extra dev --extra postgres python -m pytest tests
  --ignore=tests/integration --ignore=tests/e2e -m 'not slow' -q` =>
  **3489 passed, 399 skipped, 14 deselected, 20 subtests passed**.
- `uv lock --check`, `scripts/validate_test_gate.py`, fatal flake8
  (`E9,F63,F7,F82`), and `mkdocs build --strict` all passed after the affected
  docs/code changes. These lightweight gates will be repeated after the final
  worklog edit and before freezing the candidate commit.
- The disposable PostgreSQL container is not production/provider state and
  will be removed before the candidate commit. No provider acquisition or real
  database was changed in this iteration.

## Next safe command and STOP conditions

- Next: repeat the lightweight final gates, remove the exact disposable
  PostgreSQL/container and documentation temp output, freeze a clean candidate
  full SHA, and request the single batched independent critical review before
  PR merge. The workflow-equivalent full suite itself is already green at the
  code state described above and need not be repeated unless the review repair
  changes production behavior.
- STOP on official workbook/SDK disagreement, repository drift, ambiguity about
  legacy 245-byte provenance, a schema migration that would mutate before
  rejection, or any need to access/change real provider state.
- Do not record credentials, connection strings, private provider identifiers,
  or raw secret-bearing logs.
