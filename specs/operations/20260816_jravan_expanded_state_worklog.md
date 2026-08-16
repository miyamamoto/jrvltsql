# Standard-schema expanded state worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: make the JRA-VAN standard-schema representation of expanded odds
  O1-O6 preserve the official physical-record header state and every child
  family, including cancellation `DataKubun=9` and erroneous-record erase `0`,
  without weakening normalized native storage.
- Minimum scope: inventory the current split header/child schemas and mappings,
  compare them with current and immediately prior official layouts, define a
  backward-compatible odds storage and migration contract, prove the present
  loss with a red-first test, implement it in ordinary and optimized importers,
  and complete one reviewed PR/merge. H1/H6 follows in its own iteration because
  H1 fans out into five differently shaped child tables.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated worktree for the branch below; its local absolute path is
  intentionally omitted from this tracked public record.
- Branch: `agent/jravan-expanded-state-20260816`.
- Base/initial HEAD/origin master full SHA:
  `71178e29e2715c3056fd39ae265c7dbed80298b2` (PR #188 merge).
- Dependency order: cancellation mutation semantics PR #188 is merged. Parser
  framing, final acquisition/release, NAR, and MCP-server iterations follow.
- Production/release version at start: tag and project version `v1.6.10` /
  `1.6.10`. This iteration does not release.
- Agent/model: Codex only. No Claude session or external coding agent is used.

## Plan and gates

- Re-read the current and immediately prior official H1/H6/O1-O6 physical
  record definitions and identify header fields that apply to all expanded
  children.
- Inventory `JRAVAN_SCHEMAS`, native-to-standard table mappings, migration code,
  ordinary/optimized importer routing, primary keys, and existing databases.
- Prefer an additive compatible representation. STOP if the only design would
  silently reinterpret existing child rows, destroy keys, or require an
  ambiguous backfill.
- Add the smallest failing test before changing production code. Pair the
  missing-state rejection with normal/cancellation storage and explicit erase.
- Run focused SQLite and isolated PostgreSQL tests, workflow-equivalent checks
  warranted by the change, and a bounded acquired-record replay at the exact
  candidate SHA.
- Request one GitHub-native Copilot review, perform Codex review, aggregate
  findings, require CI success, unresolved threads zero, local/remote full SHA
  equality, and a clean worktree before merge.

## Starting observation

- Native NL/RT schemas persist `DataKubun` on every normalized child row.
  The legacy standard-schema mapping routes expanded records to child tables
  whose schemas omit physical-header state, and the importer does not currently
  materialize the corresponding header tables. The exact scope, existing table
  compatibility, and safest repair are not yet assumed.

## Read-only schema inventory

- O1 is one physical record with one header plus separate horse and bracket
  arrays. The standard schema already has `ODDS_TANPUKUWAKU_HEAD`,
  `ODDS_TANPUKU`, and `ODDS_WAKU`; O2-O6 similarly have one `*_HEAD` and one
  child table each (`ODDS_SANREN` is the O5 child).
- The current reverse mapping instead selects a child table as the sole owner,
  refers to nonexistent `ODDS_SANRENPUKU`, `HYO_TANPUKU`, and
  `HYO_SANRENTAN` names, and never materializes the odds header tables. O1
  bracket rows are consequently coerced into the horse table and lose `Kumi`.
- Header and child standard schemas also lack uniqueness declarations. Generic
  replace/upsert behavior therefore cannot guarantee one current row per
  physical key. The compatible repair is additive: define official race/child
  keys in the importer contract and ensure matching unique indexes on existing
  clean tables. If duplicates prevent index creation, import must fail closed
  with an explicit rebuild/deduplication requirement rather than choose a row.
- H1/H6 share the header-loss class but require different field transforms and
  multiple vote child owners. They remain a release blocker and will be the
  immediately following PR, not silently folded into the odds implementation.

## Official and compatibility decision

- Current JV-Data Ver.4.9.0.1 and immediately prior Ver.4.8.0.2 define the same
  O1-O6 physical header, race key, announcement time, child array shapes, and
  cancellation/erase values relevant here. Historical change notes explain old
  availability and maximum-odds eras but do not collapse O1 horse and bracket
  arrays or move `DataKubun` into a child row.
- Preserve the public `JLTSQL_TO_JRAVAN` primary-child values, including the
  historical O5 alias, so existing table-name API consumers do not change.
  Add a separate importer-only owner mapping to each real `*_HEAD` table and
  keep every actual child name addressable in the forward mapping.
- Existing standard tables cannot safely be assigned an arbitrary surviving
  row when duplicate official keys already exist. Import creates additive
  unique indexes on clean tables and fails closed with a rebuild/deduplication
  requirement if an index cannot be created. No existing row is silently
  deleted during migration.

## Red-first evidence and implementation

- Before production changes, the O1 standard contract failed for both importer
  implementations: all four normalized rows were rejected against the sole
  child owner, so no physical header, horse rows, or bracket rows were stored.
- A separate negative test for the new integrity gate was run with the
  implementation temporarily stashed. Two existing identical official header
  keys were accepted (the expected `SchemaMigrationError` was not raised),
  proving that the previous path could not say no to an ambiguous old table.
- Implemented shared O1-O6 coupled storage. One header is upserted per physical
  race key, O1 horse and bracket rows route to their distinct tables, O2-O6
  route to their actual child tables, normalized `HassoTime` is translated to
  standard `HappyoTime`, and O5 uses actual `ODDS_SANREN` storage while keeping
  the legacy public alias.
- Ordinary and optimized importers use the same verifier, transformer, key
  indexes, partial-row-safe SQL upsert, ordered zero-erase, and rollback path.
  A zero record deletes every owned child before its header in one transaction;
  cancellation status 9 remains queryable in the header.
- Focused SQLite coverage passed 14 new mapping/storage/gate checks, followed by
  42 affected tests with 7 environment-gated skips. Fresh PostgreSQL 16
  coverage passed all 33 expanded-storage tests, including failure recovery
  after duplicate-key index rejection.
- A read-only acquired cancellation snapshot with 54 normalized O1 rows was
  replayed through both importers without recording its race identity. Each
  produced exactly one status header, 18 horse rows, and 36 bracket rows; the
  following physical zero erase removed all 55 stored rows.

## Aggregated pre-candidate review

- Codex review found that O1 total win/place votes occur on horse rows while
  total bracket-quinella votes occur on bracket rows. Replacing the header with
  the last expanded row therefore discarded the first two totals. The new
  assertion was executed before the repair and failed for both importers with
  `tan_votes=None` and `fuku_votes=None` instead of the physical-record values.
- Header values are now merged without allowing an absent value from one
  expanded portion to erase a value from another. The test uses a two-row
  batch so horse and bracket portions cross a real flush boundary; both
  importers then passed. This protects both intra-batch and inter-batch state.
- Review also found that the optimized path still issued one SQL statement per
  child row. Since one O6 physical record can expand to thousands of rows,
  writes are now grouped by column shape and sent through backend batch
  execution while retaining the same unique-key upsert and transaction.
- A forced child-table rejection test passed for both importers and left both
  header and child counts at zero, proving that the coupled transaction cannot
  expose a header-only partial write when a child batch fails.
- The broad pre-candidate suite completed with 2,354 passes, 75 environment
  skips, and two CLI test failures. Both failing CLI tests passed immediately
  in isolation, and the affected storage-plus-CLI ordering subset also passed;
  the changed expanded-storage tests are collected after those CLI tests and
  cannot leave their fixtures behind before them. This was recorded as a
  non-reproducing broad-suite anomaly, not represented as a fully green run.
- After the aggregated fixes, the focused mapping/storage suite passed 26 with
  10 environment-gated skips. Static fatal-error lint and diff whitespace
  checks passed. Exact-SHA tests and acquired replay remain to be rerun after
  the candidate commit is frozen.
- A fresh PostgreSQL 16 run passed all 33 expanded-storage tests after the
  batching/header repair. A read-only 54-row acquired cancellation snapshot
  was also selected from the registered historical database without exposing
  its race identity, replayed across an actual seven-row flush boundary through
  both standard importers, and produced one header, 18 horse rows, and 36
  bracket rows before a zero erase removed all 55 rows. A new provider fetch,
  rather than this stored-snapshot replay, remains mandatory at final release.

## Next safe command

- Complete Codex diff review and static checks, then freeze a candidate and run
  exact-SHA focused/PostgreSQL/acquired-snapshot evidence before PR creation.
