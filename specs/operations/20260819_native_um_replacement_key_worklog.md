# Native `NL_UM` replacement-key verification worklog

## Start state (2026-08-19)

- Objective: close the fail-open asymmetry where the native `NL_UM` storage
  path never called `_verify_replacement_key_constraints`, although every
  sibling native path (SE, WE, AV, HR, HS, HC, HN, TC, CC, JC, CS, WF) and the
  standard-name `UMA` / `COURSE` preflight do, and `docs/record_contracts.md`
  (UM section) already documents that both `NL_UM` and `UMA` reject tables
  with a non-official `UNIQUE`/exclusion constraint or a PostgreSQL primary key
  that `ON CONFLICT` cannot use. The documentation is the contract; the
  implementation was brought up to it. No documentation was weakened.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260819_jrvltsql_um_verifier`.
- Branch: `fix/native-um-replacement-key-verify-20260819`.
- Base and starting HEAD: `008b97c0e559474eda8888db91f3356f016f3b7b`
  (`origin/master`, PR #218 squash merge). Starting worktree was clean.
- Implementer: Claude Code, `claude-fable-5`. Session ids:
  `a81aff33-9ffe-4382-b0f9-7f740223a8fe` (red, first implementation, gates;
  stopped by the session usage limit while the first review batch was
  running — those reviewers were terminated before reporting) and
  `d1311482-9219-43f1-8192-24fb52e905cb` (continuation: review batch, repair
  batch, worklog, commit, push).
- The task file asked to read `AGENTS.md` at the repo root first. No
  `AGENTS.md` exists in this repository (`find . -iname AGENTS.md` and
  `git ls-files | grep -i agents` are both empty); the task file itself and the
  HN worklog procedure (`20260818_hn_official_contract_worklog.md`) were
  followed instead.
- Environment: repository `.venv` (Python 3.12.11), `uv 0.8.4`, Docker for the
  disposable PostgreSQL. `codex-cli 0.98.0` is installed but could not be used
  (see the review section).

## Confirmed gap at start

- `src/importer/importer.py` at base: `verify_XX_storage_schema()` for
  SE/WE/AV/HR/HS/HC/HN/TC/CC/JC/CS/WF each end with
  `_verify_replacement_key_constraints(database, table_name, "XX storage")`
  and are called once per table (cached in `_verified_XX_tables`) from
  `DataImporter.import_records`, `DataImporter.import_single_record` and
  `OptimizedDataImporter.import_records`; the standard preflight
  `_preflight_standard_schema_migrations` calls the verifier for
  `{"UMA", "COURSE"}` with label `"Standard UMA storage"` /
  `"Standard COURSE storage"`.
- No `verify_um_storage_schema` and no `_verified_um_tables` existed; native
  `NL_UM` went straight to `insert_many(use_replace=True)` /
  `insert_many_optimized` / `insert(use_replace=True)`.
- Sibling test placement: siblings each own `tests/test_XX_official_contract.py`.
  UM has no such module; UM's existing replacement-key contract tests for the
  standard `UMA` table (`test_um_standard_extra_unique_is_rejected_before_mutation`,
  `test_um_standard_dual_rejects_extra_unique_on_either_backend`,
  `test_um_postgresql_constraint_drift_is_rejected_before_mutation`) live in
  `tests/test_um_parser_layout.py`, so the native tests were added there rather
  than inventing a new layout.

## Red-first evidence (2026-08-19, base `008b97c…`, production code untouched)

Tests added to `tests/test_um_parser_layout.py` before any production change:

- `test_um_native_storage_keeps_distinct_keys_and_updates_exact_key`
  (SQLite, both importer classes) — paired positive: clean official
  `SCHEMAS["NL_UM"]` imports two registrations and updates one exact key.
- `test_um_native_extra_unique_is_rejected_before_mutation`
  (SQLite; entrypoints `data-batch` / `optimized-batch` / `single` ×
  owned / caller-owned transaction) — `PRIMARY KEY (KettoNum), UNIQUE (DelDate)`
  must raise `SchemaMigrationError` matching `UM storage NL_UM .*UNIQUE`,
  `sqlite_master` unchanged, `COUNT(*) == 0`.
- `test_um_native_dual_rejects_extra_unique_on_either_backend`
  (SQLite Dual, unsafe primary / unsafe secondary).
- `test_um_native_postgresql_constraint_drift_is_rejected_before_mutation`
  (PostgreSQL; three entrypoints × `extra-unique` /
  `deferrable-primary-key` = `PRIMARY KEY (KettoNum) DEFERRABLE INITIALLY
  DEFERRED`) — `pg_constraint` catalog unchanged, `COUNT(*) == 0`.
- `test_um_native_postgresql_key_roundtrip` (PostgreSQL, both importer
  classes) — paired positive.
- `test_um_native_mixed_dual_rejects_unsafe_target_before_either_mutates`
  (SQLite + PostgreSQL Dual in either orientation, `secondary_in_sync` stays
  `True`).

Command (SQLite only):
`.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider
tests/test_um_parser_layout.py -k native`

Result: **8 failed, 2 passed, 10 skipped** (skips = PostgreSQL-gated cases).
Every failure was `Failed: DID NOT RAISE <class
'src.database.migration.SchemaMigrationError'>`; the captured importer log
showed the rows being stored (`Import completed ... records_imported=2` /
`records_imported=1`, `Batch inserted ... table=NL_UM`):

```
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[owned-data-batch]
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[owned-optimized-batch]
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[owned-single]
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[caller-owned-data-batch]
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[caller-owned-optimized-batch]
FAILED tests/test_um_parser_layout.py::test_um_native_extra_unique_is_rejected_before_mutation[caller-owned-single]
FAILED tests/test_um_parser_layout.py::test_um_native_dual_rejects_extra_unique_on_either_backend[primary]
FAILED tests/test_um_parser_layout.py::test_um_native_dual_rejects_extra_unique_on_either_backend[secondary]
8 failed, 2 passed, 10 skipped, 133 deselected in 0.42s
```

Same command with the disposable PostgreSQL 16 enabled
(`JLTSQL_RUN_POSTGRESQL_INTEGRATION=1`, `POSTGRES_HOST=127.0.0.1`,
`POSTGRES_PORT=<published port>`, `POSTGRES_DB=jltsql_test`,
`POSTGRES_USER=jltsql`, throwaway password via env):

Result: **16 failed, 4 passed** — the eight SQLite failures above plus:

```
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[data-batch-extra-unique]
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[data-batch-deferrable-primary-key]
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[optimized-batch-extra-unique]
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[optimized-batch-deferrable-primary-key]
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[single-extra-unique]
FAILED tests/test_um_parser_layout.py::test_um_native_postgresql_constraint_drift_is_rejected_before_mutation[single-deferrable-primary-key]
FAILED tests/test_um_parser_layout.py::test_um_native_mixed_dual_rejects_unsafe_target_before_either_mutates[sqlite]
FAILED tests/test_um_parser_layout.py::test_um_native_mixed_dual_rejects_unsafe_target_before_either_mutates[postgresql]
16 failed, 4 passed, 133 deselected in 0.84s
```

The extra-unique PostgreSQL and mixed-Dual cases were `DID NOT RAISE` with
the row stored. The deferrable-PK cases reached the DML and PostgreSQL
answered `ON CONFLICT does not support deferrable unique constraints/exclusion
constraints as arbiters`, which the base importer logged as
`Batch insert failed, trying individual inserts` / `Failed to insert record`
and counted as `records_failed` instead of stopping with
`SchemaMigrationError` before DML. The four positives (SQLite and PostgreSQL
clean-`NL_UM` roundtrip, both importer classes) were green at base, so the
new negatives prove the gate can say no without breaking a clean table.

## First implementation (before review)

- `_UM_STORAGE_TABLES = frozenset({"NL_UM", "UMA"})` (mirroring the
  CS/`COURSE` pair) and `verify_um_storage_schema()` calling only
  `_verify_replacement_key_constraints(database, table_name, "UM storage")`,
  wrapped with `_snapshot_validation_transactions` /
  `_rollback_call_created_validation_transactions` like the newer siblings
  (HS/HC/HN/TC/CC); `_verified_um_tables` caches and the sibling-shaped call
  block immediately after the CS block in `DataImporter.import_records`,
  `DataImporter.import_single_record` and
  `OptimizedDataImporter.import_records`.
- Green at that point: `tests/test_um_parser_layout.py` with PostgreSQL
  **153 passed**; full CI-equivalent suite **3501 passed, 409 skipped,
  14 deselected, 20 subtests passed**; all lightweight gates passed.
- This shape was then reviewed (below) and repaired in one batch.

## Independent review batch (2026-08-19, one batch, read-only reviewers)

Three parallel read-only Claude reviewers on the first implementation
(correctness vs the sibling contract; PostgreSQL/SQLite behaviour with the
disposable PostgreSQL available for probing; test adequacy with mutation
probes on out-of-repo copies). A fourth, cross-model Codex pass was attempted
twice and could not run: the plugin's configured model requires a newer Codex
CLI (`gpt-5.6-sol` / codex-cli 0.98.0), and an explicit `codex exec -m gpt-5.4
-s read-only` returned `usage_limit_reached` (resets 2026-08-20). No Codex
finding exists; this is recorded as not run. DuckDB: zero references in
`src/`, `pyproject.toml`, `docs/`; the shared verifier fails closed for any
non-SQLite/non-PostgreSQL type (`SchemaMigrationError: ... cannot be
verified for database type`), and three test modules state DuckDB is outside
the supported matrix.

Accepted and repaired in one batch (all repairs red-first; see next section):

1. Correctness (should-fix) + DB (blocking): `verify_um_storage_schema` called
   only the replacement-key verifier, so it (a) never checked that the table
   exists — SQLite `PRAGMA index_list` on a missing `NL_UM` returns `[]`, the
   verifier returned `True` and the name was cached in `_verified_um_tables`
   although nothing had been inspected (confirmed by probe:
   `records_failed=1`, cache `{'NL_UM'}`), while PostgreSQL raised the
   misleading `UM storage primary key catalog mismatch for NL_UM: expected one
   primary key`; and (b) never checked *which* columns the primary key covers
   — the DB reviewer's probe showed `PRIMARY KEY (DelDate)` and a keyless
   `NL_UM` passing and three registrations collapsing into one row /
   duplicating on `INSERT OR REPLACE`, which is the very harm the docstring
   promised to prevent. Every sibling verifier calls `verify_table_schema`
   first (CS: table existence, `KettoNum`-only primary key, lossless text
   types/capacities). Repair: mirror CS — resolve `SCHEMAS[...] /
   JRAVAN_SCHEMAS[...]`, call `verify_table_schema(database, table_name,
   schema_sql)`, then `_verify_replacement_key_constraints`, all inside the
   existing snapshot/rollback wrapper. Resulting messages: `Required table does
   not exist: NL_UM`; `Schema verification failed for NL_UM: primary key
   existing=['deldate'], expected=['KettoNum']` (PostgreSQL) /
   `existing=['DelDate']` (SQLite); `... existing=[], expected=['KettoNum']`
   for keyless.
2. Test adequacy (should-fix ×2) + correctness (nit) : with `"UMA"` in
   `_UM_STORAGE_TABLES` the standard-name path changed in one scenario (a
   missing `UMA` table now aborted with `Required table does not exist: UMA`
   instead of the base soft `records_failed=1`), the CHANGELOG line
   over-claimed "standard path unchanged", and mutation probes showed the
   pre-existing standard tests would still pass if the standard preflight
   branch were deleted, because the per-record verifier's message satisfied
   the loose `match="UNIQUE"` / `"primary key"` regexes. Repair: the verifier
   is **native-only** (`_UM_STORAGE_TABLES = frozenset({"NL_UM"})`), the
   docstring states that standard `UMA` keeps its existing preflight and is
   intentionally not re-verified per record; the four pre-existing standard
   regexes were tightened (strengthened only) to `Standard UMA storage UMA
   .*UNIQUE` / `Standard UMA storage primary key for UMA`; a test pins
   `verify_um_storage_schema(db, "UMA") is False`. Task requirement "the
   standard-name `UMA` behaviour is unchanged" is therefore met literally
   (probe after repair: standard missing `UMA` on SQLite and PostgreSQL =>
   `records_failed=1`, no abort, no pending transaction — identical to base).
   The correctness reviewer had preferred keeping `UMA` for CS parity; the
   task's explicit no-change requirement for the standard path decided it.
3. DB (should-fix): the PostgreSQL rejection tests hard-coded
   `auto_commit=True` and rolled back before asserting, masking the connection
   contract. Repair: `auto_commit` owned/caller-owned parametrisation, no
   post-raise rollback, `has_pending_transaction() is False` asserted (the
   test now closes its own catalog-read transaction *before* the import so the
   assertion observes only what the importer left).
4. Correctness (nit) + test adequacy (nits): no missing-table / wrong-key
   negatives, no pre-existing-row-survives assertion, no non-UM-table
   assertion, native Dual test lacked `secondary_in_sync`, duplicated import
   helper, one 101-character line. Repair: added
   `test_um_native_missing_table_is_rejected_before_mutation` (3 entrypoints,
   SQLite), `test_um_native_missing_table_is_not_cached_as_verified` (both
   importer classes: a later-created unsafe table is still rejected by the same
   importer), `test_um_native_wrong_or_missing_key_is_rejected_before_mutation`
   (`wrong-key` / `keyless` × 3 entrypoints; a pre-inserted legacy row and
   `PRAGMA table_xinfo` must survive), the `wrong-primary-key` PostgreSQL
   drift param, `test_um_native_postgresql_missing_table_is_rejected_before_mutation`,
   `test_um_storage_verifier_covers_only_native_um_storage`; `secondary_in_sync`
   asserted in the native Dual test; one shared `_import_um_records(...,
   standard=)` helper with two thin wrappers; line wrapped.
5. CHANGELOG reworded to what is actually true (native `NL_UM` now rejects
   extra UNIQUE/exclusion, unusable PostgreSQL PK, non-`KettoNum`/keyless
   PK, and a missing table before replacement; parser behaviour and the
   standard `UMA` preflight unchanged).

Recorded as refuted or not repaired (reason):

- Sequence position / missed entry point — refuted: the calls sit right after
  the CS block, before the erase branches, buffering and `_flush_batch`;
  `OptimizedDataImporter` has no `import_single_record`; `src/importer/batch.py`
  delegates to `DataImporter.import_records`; `RealtimeUpdater` documents UM
  as not realtime and bypasses `DataImporter`; scripts/tools use only the
  three guarded entry points.
- Should be hooked in `SchemaManager` — not repaired: `schema.py` hooks only
  the `STRICT_*` family with a full column/capacity/unapproved-constraint
  contract; CS, WF and JG are absent too; UM's verifier is a replacement-key
  contract, so `jltsql init` cannot see UM drift (same as CS). Follow-up, not
  this iteration.
- Label / error shape — refuted: `"UM storage"` matches `"CS storage"` /
  `"HN storage"`; `SchemaMigrationError` is the sibling type.
- Transaction-wrapper risk — refuted: the snapshot is taken after the
  `_UM_STORAGE_TABLES` early return, caller-owned transactions are seen as
  pending and left alone, Dual targets handled identically to HN/TC/HS/HC/CC.
- Official `SCHEMAS["NL_UM"]` falsely rejected on PostgreSQL — refuted by
  probe (PG 16.14 `nl_um_pkey`: primary, unique, valid, ready, immediate,
  non-deferrable, non-deferred, validated => PASS; non-unique indexes
  tolerated; `indexes.py` defines none for UM). Case-folding / search_path —
  refuted: `to_regclass('nl_um')` and `to_regclass('NL_UM')` resolve alike and
  the DML PK lookup uses the same lower-cased lookup; a quoted mixed-case
  `"NL_UM"` is unreachable project-wide (`table_exists` is false for it too).
- `DEFERRABLE INITIALLY IMMEDIATE` slipping through — refuted: PostgreSQL
  sets `indimmediate=false` and `condeferrable=true`; both branches fire and
  `ON CONFLICT` rejects both DEFERRED and IMMEDIATE deferrable arbiters
  (probe).
- SQLite `PRAGMA index_list` origin ambiguity / version dependence — refuted:
  `pk` vs `u` vs `c` (incl. partial `CREATE UNIQUE INDEX`) distinguished,
  non-unique tolerated; Python ≥ 3.12 guarantees SQLite far newer than the
  3.8.9 that introduced `origin`.
- Dual ordering / `secondary_in_sync` — refuted by probe: all four
  SQLite/PostgreSQL orientation × bad-side combinations reject before either
  mutates, `sync=True`, both counts 0, no pending transaction.
- Catalog query cost — refuted: ~0.2 ms per call, once per table per importer
  instance.
- DML-time PK lookup swallowing catalog errors and emitting `ON CONFLICT DO
  NOTHING` (`postgresql_handler.py`) — pre-existing, outside the verifier's
  guarantee; not repaired.
- An interrupted `REINDEX INDEX CONCURRENTLY nl_um_pkey` leaves an invalid
  unique `*_ccnew` index that the verifier rejects — fail-closed and
  remediable by `DROP INDEX`; a docs line is a possible follow-up, not
  repaired here.
- `-k postgresql` hides the `[sqlite]` id of the mixed-Dual test — identical
  to the HN sibling; it skips without the opt-in, never falsely passes; the
  worklog commands use `-k native` / the whole module.
- Placement in `tests/test_um_parser_layout.py` — confirmed as the file where
  UM's equivalent standard tests already live (no
  `test_um_official_contract.py` exists).
- Native invalid `KettoNum` — the shared header validator is covered by the
  standard tests; not duplicated.
- The task's mention of DuckDB — see above; out of the supported matrix and
  fail-closed.

## Repair batch red-first and green evidence

- Reds against the first implementation, after adding the repair tests and
  before touching production code (SQLite + PostgreSQL enabled, `-k
  "missing_table or wrong_or_missing_key or ignores_unrelated or
  postgresql_constraint_drift"`): **20 failed, 15 passed** — the missing-table
  cases (SQLite ×3 entrypoints, cache ×2 importer classes, PostgreSQL ×3) and
  the wrong-key / keyless cases (SQLite ×6, PostgreSQL ×6) failed with `DID
  NOT RAISE` or a non-matching message; the extra-unique / deferrable cases
  with the new transaction assertions and the unrelated-table test passed.
  (One earlier iteration of the PostgreSQL drift test failed on
  `has_pending_transaction()` because the test's own catalog read had opened
  the transaction; the test was corrected to close its own read before the
  import — that is a test bug fix, not a weakened assertion.)
- Green after the repair (native-only verifier + `verify_table_schema`):
  `tests/test_um_parser_layout.py` => **180 passed** with PostgreSQL enabled,
  **150 passed, 30 skipped** without.
- Full CI-equivalent suite, run alone (nothing else touching
  `.pytest-tmp`): `pytest tests --ignore=tests/integration --ignore=tests/e2e
  -m "not slow"` => **3513 passed, 424 skipped, 14 deselected, 20 subtests
  passed** (exit 0). Two earlier full-suite runs that overlapped with another
  pytest process on the shared `--basetemp=.pytest-tmp` produced unrelated
  `sqlite3.OperationalError: disk I/O error` / `tmp_path` setup errors in
  CS/HN/UM cases; each vanished when the run was repeated alone and is
  recorded here only so nobody mistakes it for a product regression.
- Fresh disposable PostgreSQL 16 (`postgres:16-alpine`, container
  `jltsql-um-verify-pg16`, tmpfs data directory, bound to `127.0.0.1` on an
  ephemeral published port, throwaway credentials via env only), opt-in
  enabled: `tests/test_um_parser_layout.py tests/test_cs_official_contract.py
  tests/test_hn_official_contract.py tests/test_migration.py
  tests/test_postgresql.py tests/test_dual_handler_transactions.py
  tests/test_importer.py tests/test_current_record_validation.py
  tests/test_data_kubun_entry_contract.py tests/test_expanded_record_storage.py
  tests/test_integration.py` => **663 passed**.
- Direct PostgreSQL probes (own throwaway schema, dropped afterwards), native
  `DataImporter`: `PRIMARY KEY (KettoNum), UNIQUE (DelDate)` => `UM storage
  NL_UM has unsupported additional UNIQUE/exclusion indexes:
  ['nl_um_deldate_key']`; `PRIMARY KEY (KettoNum) DEFERRABLE` and `...
  DEFERRABLE INITIALLY DEFERRED` => `UM storage primary key for NL_UM must be
  valid, ready, immediate, non-deferrable, and usable by ON CONFLICT`; missing
  table => `Required table does not exist: NL_UM`; keyless / `PRIMARY KEY
  (DelDate)` => `Schema verification failed for NL_UM: primary key
  existing=[] / ['deldate'], expected=['KettoNum']`; each with `COUNT(*) == 0`
  and no pending transaction; the official schema => 1 row imported. Standard
  mode with no `UMA` table => `records_failed=1`, no abort, no pending
  transaction on both backends (identical to base).
- `python scripts/validate_test_gate.py` => `TEST GATE PASS`.
- Fatal flake8 `flake8 src tests scripts tools --isolated --count
  --select=E9,F63,F7,F82 --show-source --statistics` => `0`.
- `uv lock --check` => pass (`Resolved 50 packages`).
- `git diff --check` => clean.
- Advisory: `ruff check` on the three touched Python files reports exactly the
  same pre-existing findings before and after (0 new); `black --diff` on
  `tests/test_um_parser_layout.py` touches only two pre-existing hunks (the
  `CHAKU` comprehension and the standard Dual test signature), none of the
  added code; both importer modules were already not black-clean at base.
- `tests/test_public_setup_contract.py tests/test_distribution_contents.py`
  (they read `CHANGELOG.md`) => **43 passed**.
- `mkdocs build --strict` was not run: no file under `docs/` was changed
  (`CHANGELOG.md` is not in the mkdocs nav).

## Final change summary

`src/importer/importer.py`: `_UM_STORAGE_TABLES = frozenset({"NL_UM"})`;
`verify_um_storage_schema()` (schema lookup, `verify_table_schema`,
`_verify_replacement_key_constraints(..., "UM storage")`, snapshot/rollback
wrapper); `_verified_um_tables` cache; sibling-shaped call block after the CS
block in `DataImporter.import_records` and `DataImporter.import_single_record`.
`src/importer/importer_optimized.py`: import, cache attribute, same block in
`OptimizedDataImporter.import_records`. `tests/test_um_parser_layout.py`:
native contract tests listed above plus the tightened standard regexes.
`CHANGELOG.md`: one `Fixed` entry. No sibling path refactored, no parser
change, no DDL change, no documentation weakened, `SchemaManager` untouched.

## Residual risk

- `SchemaManager` / `jltsql init` still cannot see `NL_UM` drift (only the
  import fails closed) — same as CS/WF/JG; candidate follow-up.
- The verifier's guarantee ends at verification time; the pre-existing
  DML-time PK lookup in `postgresql_handler.py` swallowing catalog errors is
  untouched.
- The disposable PostgreSQL evidence is from PostgreSQL 16 only.

## Closure

- Disposable container `jltsql-um-verify-pg16` (and its tmpfs data) removed
  after the final PostgreSQL run; no `kps_*` / `jrdb-*` container, volume,
  scheduler, or provider state was touched. Iteration-generated
  `.pytest-tmp/`, `htmlcov/`, `.coverage` were removed if present. No
  credentials or connection strings are recorded here.
- Next: Devin opens the PR from
  `fix/native-um-replacement-key-verify-20260819`; this iteration does not
  open or merge it, does not amend, and does not force-push.
