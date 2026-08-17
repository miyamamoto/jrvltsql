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

## 2026-08-17 — independent review aggregation and red-first closure

- Exact clean candidate `d64d6c0dbe6f87ef188e2e36dac31aeafd1c6c89`
  was reviewed independently by two Codex critical reviewers because Claude
  Code remained unavailable. Both returned `NEEDS_CHANGES`; no P0 was found.
- The findings were aggregated before further production edits:
  1. metadata covered only 74 entries, not the complete disjoint union of 80
     native and 54 standard executable schemas;
  2. application checked table existence only, so a wrong column set/type/key
     could receive misleading metadata before failure or be accepted;
  3. Dual mode selected the primary backend syntax and could report success
     while PostgreSQL rejected mirrored SQLite statements;
  4. index extraction checked columns but not the index target table;
  5. the MCP-visible physical metadata contract still exported version 1.0.0
     and did not define logical-nullability/index-column semantics;
  6. the exhaustive test reused production extractors and therefore was not a
     sufficiently independent database oracle.
- Test-only regressions were added while production remained the exact
  `d64d6c0...` commit. The local selection failed `4 failed`: missing metadata
  entries, MCP version 1.0.0, schema-drift application returning true, and the
  index-target validator accepting `NL_RA` metadata bound to an `NL_SE` index.
  The initial index run exposed a missing `pytest` import in the new test; after
  fixing the test itself, it failed for the intended reason (`DID NOT RAISE`).
- A fresh disposable PostgreSQL 16 instance then failed both intended live
  regressions: an otherwise complete `NL_RA` with `Year TEXT` and a one-column
  primary key returned true and overwrote its sentinel table comment; Dual
  mode returned true and wrote 122 SQLite metadata rows while PostgreSQL had
  zero column comments. The container was removed after the red evidence.
- One aggregate production repair is now authorized: cover all 134 schemas,
  independently preflight exact catalog columns/type families/logical
  nullability/ordered key before mutation, route Dual targets through their
  backend-specific implementation, validate index ownership, and export MCP
  metadata contract 2.0 with precise semantics. No provider layout, table DDL,
  acquisition behavior, or runtime release-readiness claim is changed; the
  public metadata contract and its release documentation are intentionally
  changed by this iteration.
- Next safe command: implement the aggregate repair without broad formatting,
  then run the exact six red cases plus paired canonical positives before
  expanding to the affected and full suites.

## 2026-08-17 — aggregate repair implementation and pre-freeze verification

- Production now synthesizes metadata owners for the complete 134-table union
  while preserving existing table-level descriptions where available. The
  public column contract remains the executable physical identifier/type/key
  shape; generic descriptions on newly covered tables are intentionally not
  claimed to be an official semantic glossary.
- The metadata application path now reads the live SQLite or PostgreSQL
  catalog and requires an exact column set, normalized MCP type family,
  portable logical nullability, and ordered primary key before any metadata
  mutation. SQLite primary-key columns are logically non-null even where raw
  `PRAGMA table_info.notnull` is zero. Dual mode preflights every connected
  target and then calls each backend's own metadata writer instead of mirroring
  SQLite syntax to PostgreSQL.
- Index extraction now rejects a statement whose `ON` target differs from the
  metadata owner even when the referenced column name exists in both tables.
  MCP export version is 2.0.0 and explicitly defines `nullable` and `indexes`
  semantics; the latter is a distinct column union, not complete index DDL.
- Paired local verification after implementation:
  - metadata SQLite selection, including all 134 live PRAGMA schemas:
    `26 passed, 8 deselected`;
  - affected metadata/official contracts: `661 passed, 78 skipped`;
  - fresh disposable PostgreSQL 16 metadata contract: `34 passed`, covering
    all 134 catalogs/comments, wrong type/nullability/key rejection, and
    backend-specific Dual application; the container was removed;
  - ordinary full suite: `2934 passed, 175 skipped, 22 subtests passed`;
  - `uv lock --check`, fail-closed test-gate validation, fatal Flake8,
    compileall, focused Ruff, strict MkDocs, and `git diff --check`: pass;
  - fresh wheel/sdist build, distribution content gate, and isolated wheel
    init smoke: pass. Pre-freeze artifact hashes were
    wheel `c0394713e45039a4839b63e2d40acd80ae1846881c8c479bd82724386df87b76`
    and sdist `c97d6a66545c0525884ce5a942ec8dd099e101d617270eef37364dcab7015d3b`.
- This remains a metadata/MCP iteration only. It makes no SDK acquisition,
  64-bit compatibility, provider-data, full release-readiness, or release
  claim. The package version remains the already established unreleased
  `2.0.0.dev0`; only the nested MCP metadata contract version becomes 2.0.0.
- Remaining: rerun the extended Dual no-mutation case on fresh PostgreSQL,
  inspect the final diff/worktree, commit one repair candidate, repeat focused
  DB/package gates on that exact SHA, then request one bounded closure pass
  from the same two independent Codex reviewers.

### Catalog type fail-closed refinement

- Before candidate freeze, the new PostgreSQL negative was split into one
  existing test with three independent subcases (unknown type, wrong logical
  nullability, wrong ordered key). This exposed a real fail-open in the new
  type normalizer: PostgreSQL `INTERVAL` was treated as integer because of an
  `INT` prefix check. On the unfixed implementation the live test failed
  `1 failed, 1 passed, 2 subtests passed` at `unknown-type` because metadata
  application returned true.
- The normalizer now accepts only explicit catalog type tokens/families. The
  same fresh PostgreSQL test passes `1 passed, 3 subtests passed`. The extended
  Dual test also passes on fresh PostgreSQL and proves that a drifted secondary
  is rejected before the canonical SQLite metadata description changes.

### Exact candidate verification and PostgreSQL test isolation

- Candidate `99aea9e0743688c0c106943046ca2e909bb04b6b` was frozen clean. Its
  ordinary full suite passed `2934 passed, 175 skipped, 22 subtests passed`.
- The first exact-SHA PostgreSQL file run exposed a test-isolation error, not a
  production failure: the extended Dual test intentionally committed a drifted
  `NL_RA`, while `tearDown` dropped it without committing; psycopg disconnect
  rolled the cleanup back and later tests observed the drifted table. The run
  therefore failed 2 of 34 tests with `NL_RA.year actual=text`.
- The shared PostgreSQL test teardown now commits its explicit table drops.
  A new fresh PostgreSQL 16 container then passed the complete metadata file:
  `34 passed, 3 subtests passed`. This is a test-only isolation correction;
  production sources remain byte-identical to candidate `99aea9e...`.
- Next safe command: commit the test/worklog-only isolation correction, run
  the focused SQLite/PostgreSQL/static/package gates on the resulting clean
  full SHA (without repeating the unaffected full suite), then begin the two
  bounded independent closure reviews.
