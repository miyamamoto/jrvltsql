# Executable metadata contract worklog

## 2026-08-17 — start

- Objective: make every `TABLE_METADATA` entry describe the executable SQL
  schema exactly, so SQLite MCP metadata and PostgreSQL `COMMENT ON COLUMN`
  target real columns and primary keys. This is one metadata/MCP correctness
  iteration; it does not change provider record layouts or claim release
  readiness.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260817_jrvltsql_ra_se_metadata`.
- Branch: `agent/ra-se-metadata-20260817`.
- Base and initial HEAD:
  `0ca68a7c1ab3eb6fe7a40bb60bc2800a5ea16993` (PR #205 merge,
  `origin/master`).
- Production/release line: unreleased `2.0.0.dev0`; no tag or release is
  authorized by this iteration.
- Trigger: the prior live PostgreSQL sweep exposed failing RA/SE metadata
  comments. An exhaustive read-only comparison found that 61 of 74 metadata
  tables have a column/type or primary-key mismatch against
  `schema_types.get_table_column_types()` /
  `get_table_primary_key_columns()`. Most mismatches use Japanese display
  labels that are not executable column identifiers; SQLite stores those
  stale labels while PostgreSQL rejects them.
- Minimum implementation scope:
  1. add one red-first exhaustive metadata-vs-DDL contract;
  2. bind every metadata entry to the complete executable column/type/key
     contract while preserving table-level Japanese description and purpose;
  3. ensure SQLite reapplication removes stale column metadata for that table;
  4. verify representative SQLite retrieval and fresh PostgreSQL comments,
     then run affected/full/package gates on an exact clean SHA.
- Review model: Claude Code quota is unavailable in this environment, so the
  maintainer-authorized independent Codex critical-review fallback will be
  used. The final immutable candidate requires two independent bounded Codex
  reviews because this changes an MCP-visible contract and a fail-closed
  metadata gate.
- STOP conditions: an executable schema has no deterministic metadata owner;
  the repair would change provider data or table DDL; a preflight can mutate
  real data; any new P0/P1; failed exact-SHA SQLite/PostgreSQL/full/package
  gate; unresolved PR thread; or worktree/SHA drift.
- Next safe command: extend the existing metadata consistency test with one
  exhaustive exact column/type/key assertion and run it against this base to
  record the expected red before production edits.

## 2026-08-17 — red-first evidence and aggregate repair

- The exhaustive contract was added before production changes. On unchanged
  base `0ca68a7c1ab3eb6fe7a40bb60bc2800a5ea16993` it failed with
  `1 failed`; the assertion reported 61 mismatched metadata tables out of 74.
  This proves the check rejects display-only columns rather than merely
  accepting the current fixture.
- A second existing reapplication test was extended to seed one legacy
  display-only SQLite metadata row. The test-only patch was applied to an
  immutable archive of the same base and failed at `assert stale_rows == []`
  (`1 failed`). The temporary archive was moved to trash afterward.
- The aggregate repair now derives complete column names, normalized types,
  logical nullability, primary keys, and configured index columns from the
  executable schema. Existing descriptions/examples are retained only when
  they already address a physical column; newly bound columns use the physical
  identifier as a safe description. Table-level Japanese descriptions and
  purposes remain unchanged.
- SQLite metadata reapplication deletes the prior column-metadata set for that
  one table before inserting the complete executable set, preventing stale
  pseudo-columns from surviving `INSERT OR REPLACE`.
- Post-change SQLite metadata tests pass `24 passed, 5 skipped`; the test now
  creates all executable tables, applies all 74 metadata entries, and compares
  every stored column set. A fresh disposable PostgreSQL 16 run passes
  `29 passed`, including creation of all schemas and executable
  `COMMENT ON TABLE/COLUMN` application for every metadata table. The
  container `jrvltsql-metadata-pg16-0ca68a7` was stopped and auto-removed.
- The affected schema/official-contract selection passes `400 passed, 65
  skipped`. One TM test still asserted the retired Japanese display key; it
  was updated to the existing physical `NATIVE_KEY` contract. No provider data,
  table DDL, parser, importer, or release claim changed.
- The pre-candidate ordinary full suite passes `2917 passed, 167 skipped, 14
  deselected, 22 subtests passed`. Lock validation, the fail-closed test gate,
  fatal Flake8, compileall, focused Ruff, strict MkDocs, and `git diff --check`
  pass. A broad Black invocation attempted to reformat thousands of unrelated
  legacy metadata lines; that mechanical output was explicitly discarded and
  the reviewed minimal patch was reapplied. The rebuilt focused metadata/TM
  selection passes `67 passed, 8 skipped` with a compact `212 insertions / 43
  deletions` production/test/docs delta rather than the unrelated formatter
  churn.
- Remaining before candidate freeze: run full tests, fatal/static/docs/package
  gates; commit the complete worklog; repeat the fresh PostgreSQL metadata
  contract on the immutable full SHA; and obtain two independent bounded Codex
  critical reviews. STOP on any executable-column mismatch, stale SQLite row,
  PostgreSQL comment failure, full-suite failure, or reviewer P0/P1.
