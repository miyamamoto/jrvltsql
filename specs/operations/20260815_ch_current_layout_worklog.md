# CH current-layout iteration worklog

## Scope and identity

- Started: 2026-08-15 JST
- Objective: reconcile the CH trainer-master parser and native/standard
  storage with the official 3862-byte JV-Data layout without losing any
  repeated recent-win or current/previous/cumulative result member.
- Minimum scope: CH physical parser, directly coupled native and standard
  storage contracts, importer fan-out only if the existing official standard
  schema requires it, fixtures, red-first byte/storage contracts,
  exact-full-SHA Codex review, PR, and merge.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_ch_layout`
- Branch: `agent/ch-current-layout-20260815`
- Base / initial HEAD: `e54991eb02f5fbee8c4e561bf1f54adb9be255ac`
  (merged `master`, PR #178).
- Dependency: BR iteration PR #178 is merged at the base SHA. CH starts from
  that merge and will not reuse BR candidate tests as CH evidence.
- Production/release version: no release is created by this iteration. The
  release remains gated on all official-layout and public-package cleanup
  iterations plus fresh acquisition on the final merged release candidate.
- Implementer/reviewer policy: Codex only. Claude Code is not used per the
  user's instruction.

## Starting evidence and questions

- Official JV-Data 4.8.0.2 and 4.9.0.1 both declare CH as 3862 bytes.
  SDK 5.0.0 independently sets `bSize = 3862`, reads three 163-byte
  `SAIKIN_JYUSYO_INFO` blocks from byte 216, three 1052-byte
  `HON_ZEN_RUIKEISEI_INFO` blocks from byte 705, and CRLF at bytes 3861-3862.
- The current parser publicly stops at 592 bytes, stores one recent-win block,
  only the opening portion of one result block, and treats bytes 591-592 as a
  delimiter even though those bytes are inside the first result block.
- The existing standard schema separates trainer header/recent-win data
  (`CHOKYO`) from repeated result rows (`CHOKYO_SEISEKI`). Before coding,
  determine the complete key/cardinality contract and whether the importer
  already supports safe one-record-to-multiple-table storage. Do not flatten
  blindly if that would break established standard-schema compatibility.
- Audit the native column-count/backend limits before selecting a flattened
  representation. Stop if SQLite/PostgreSQL cannot preserve all official
  members losslessly under the proposed schema.

## Red-first and validation requirements

- First add a minimal gap-free physical-layout contract that fails on the
  current parser: exact 3862-byte length/type/CRLF/strict-CP932 gates, three
  distinct recent-win blocks, three distinct result blocks, all six finish
  counts in every nested array, and no silent field omission.
- Add storage tests only after the canonical native/standard representation is
  established. They must prove ordinary and optimized importer behavior,
  key/idempotency, migration or fail-closed behavior, and row preservation on
  refusal.
- Final evidence must target one full candidate SHA and include focused tests,
  full suite, workflow-equivalent tests, static checks, temporary PostgreSQL,
  aggregated review, GitHub Actions, unresolved threads zero, and a clean
  worktree.

## Stop conditions

- Stop before implementation if the official repeated-cardinality, standard
  table/key contract, or backend column limit remains unresolved.
- Stop before merge for any failed required check, actionable P0/P1/P2
  finding, unresolved PR thread, head drift, or dirty worktree.
- Do not release or count synthetic/fixture/replay data as the final fresh
  provider acquisition gate.

## Representation decision and implementation

- Both official workbooks and SDK 5.0.0 agree on a gap-free physical layout:
  215 header bytes, three 163-byte recent-grade-win blocks, three 1052-byte
  result blocks, then CRLF. Each result block is 173 scalar values: setting
  year, four prize totals, six flat counts, six steeplechase counts, 20 venue
  arrays of six counts, and six distance arrays of six counts.
- The repository's generated standard schema and two public JRA-VAN-compatible
  DB references independently use one 42-column `CHOKYO` row plus three
  176-column `CHOKYO_SEISEKI` rows. The latter's key is trainer code plus
  sequence number. The implementation uses the same normalization for native
  storage as `NL_CH` plus `NL_CH_SEISEKI`; the widest table is 176 columns,
  below both PostgreSQL's 1600-column and the local SQLite build's 2000-column
  limits.
- `CHParser` now accepts exactly 3862 bytes, checks `CH`, CRLF, and strict
  CP932, emits all 42 header fields, and attaches exactly three private
  normalized result rows. The importer validates their complete field set,
  parent key, and sequence `1,2,3` before any mutation.
- Ordinary and optimized importers write one physical CH record as one atomic
  coupled group. Batch failure rolls back both tables; the per-record fallback
  also owns a transaction, so a child failure cannot leave an orphan header.
  Import statistics continue to count one physical record, not four DB rows.
- `CHOKYO` and `CHOKYO_SEISEKI` now have the missing primary keys and exact
  widths/types. All CH date fields are lossless eight-character strings, not
  SQL `DATE`, because active trainers legitimately carry `00000000` as the
  deletion date. Existing keyless standard tables fail closed before writes.
- Existing native `NL_CH` keeps its trainer-code key and can add the missing
  header columns without dropping its old inline fields. Those old result
  values are incomplete and are not guessed into the normalized child table;
  a complete current setup reimport is required after migration.

## Red-first and current validation evidence

- On base `e54991eb02f5fbee8c4e561bf1f54adb9be255ac`, the new contract produced
  `18 failed, 1 passed`. It exposed `592 != 3862`, acceptance of every corrupt
  physical case, missing repeated values/tables/keys, silent header-only
  writes, and absence of coupled rollback.
- After implementation the dedicated SQLite contract passed `25 passed`.
  The affected parser/schema/importer/migration/batch bundle passed
  `826 passed, 1 skipped`.
- A disposable PostgreSQL 16 container exercised both importers against both
  native and standard table pairs, preserving `00000000`, all three result
  rows, the final distance/count value, duplicate idempotency, and coupled
  rollback on a child `NOT NULL` failure: `29 passed`. The isolated schemas
  and container were removed afterward.

## 2026-08-16 continuation and aggregated Codex review

- Re-fetched `origin/master` before resuming. Worktree HEAD, branch base, and
  `origin/master` were still the same full SHA
  `e54991eb02f5fbee8c4e561bf1f54adb9be255ac`; the dirty paths were limited to
  the recorded CH implementation, tests, public support document, and audit
  worklogs.
- Re-read the SDK 5.0.0 C# contract at `JV_CH_CHOKYOSI.SetDataB`: buffer 3862,
  recent-win starts `216 + 163*i`, result starts `705 + 1052*i`, and CRLF starts
  3861. The two official workbooks independently report CH record length 3862
  on format row 708. `HON_ZEN_RUIKEISEI_INFO` confirms flat/steeple six-value
  groups, 20 venue groups, and six distance groups; no offset or cardinality
  difference was found.
- Aggregated code review found one contradictory implementation artifact:
  `schema_jravan.py` retained the obsolete keyless `CHOKYO_SEISEKI` literal and
  overrode it after dictionary construction. Although runtime lookup returned
  the corrected schema, the source exposed two incompatible contracts. The
  obsolete literal and post-dictionary override were replaced by the single
  `CHOKYO_SEISEKI_SCHEMA` entry.
- Added the missing direct `DataImporter.import_single_record` contract for
  native and standard storage. Both paths store one header and three result
  rows. Updated `docs/data_support.md` to expose the two-table CH storage,
  atomicity, current-only 3862-byte input, and rebuild requirement for obsolete
  standard tables.
- The post-review affected bundle passed `828 passed, 5 skipped`. A first full
  run reported five failures: three exact table-count expectations still
  assumed 42 NL / 75 total, while two CLI invocations exited 1 without a stable
  reproduction. The count contract was updated to 43 NL / 76 total. Both CLI
  tests passed in focused isolation, and the subsequent full suite passed
  `2096 passed, 51 skipped, 6 subtests`; therefore no CLI product change was
  made for a non-reproducible transient.
- The final uncommitted content was re-run in a disposable PostgreSQL 16
  container after the schema-source cleanup: `31 passed`. It covered ordinary
  and optimized importers, native and standard tables, all three child rows,
  exact `00000000` preservation, idempotency, and child-failure rollback. The
  explicitly named temporary container was removed after the run.
- Static evidence on the reviewed content: Black check for new/rewritten CH
  files, Ruff for those files, critical Flake8 (`E9,F63,F7,F82`) across
  `src tests`, `compileall`, and `git diff --check` all pass.

## Next safe commands

1. Review the complete staged diff and create one CH candidate commit.
2. Run the focused/full/workflow-equivalent/static commands required for
   that immutable full SHA and record the SHA in PR metadata rather than adding
   a self-referential worklog commit.
3. Run the exact-SHA Codex critical review, aggregate actionable findings once,
   then push/open the CH PR. Stop for any actionable finding, failed check,
   head drift, unresolved thread, or dirty worktree.

## Exact-SHA Codex findings and repair batch

- Candidate `37c784019d23fa4a5794b99eba83483c3b74bd07` passed the recorded exact-SHA
  local suites, then received one aggregated Codex CLI review with three
  actionable findings. The reviewer used `gpt-5.6-sol` at `xhigh`; Claude Code
  was not used.
- P1 was independently reproduced: a transient `table_exists` failure during
  CH child-schema preparation entered the ordinary importer's generic fallback,
  committed one `NL_CH` header, committed zero `NL_CH_SEISEKI` rows, and
  reported `records_imported=1`. This candidate must not be published.
- P2 performance evidence: 1000 CH inputs caused 2000 table-existence and 3000
  column/key metadata reads before insertion because the child schema was
  verified per physical record. Verification must be hoisted to once per
  batch/import call while row payload validation remains per record.
- P2 operational evidence: `raceday_verify.py` and `check_data_quality.py`
  could report a usable trainer master when `NL_CH` was populated but the new
  child table was missing, empty, orphaned, or not exactly three rows per
  trainer. The repair adds fail-closed existence/cardinality/orphan checks.
- Per the validator rule, regression tests for the coupled fallback,
  once-per-batch metadata verification, missing/incomplete/complete race-day
  checks, and missing/incomplete/complete data-quality checks are added before
  changing the implementation. The next command is the focused red run; its
  failure output must be recorded before implementing the repair batch.
- The focused run before implementation was red, as required: `6 failed`. The
  concrete assertions were child count `0 != 3`, ordinary and optimized
  metadata calls `{table_exists: 10, fetch_all: 15}` instead of `{2, 3}` for
  five records, and empty issue lists where missing/incomplete normalized CH
  storage had to be rejected. Separate orphan-path probes were also red
  (`2 failed`) before the validators changed.
- The repair verifies the child table once before a CH batch. A first transient
  catalog `DatabaseError` in the ordinary importer rolls back and retries only
  the coupled preflight; a second failure aborts before mutation. Per-record
  field/key/Num validation remains in place, and no generic header-only retry
  is reachable. The optimized importer caches the verified child contract for
  the current import call.
- Both operational checkers now require `NL_CH_SEISEKI`, reject trainers
  without exactly distinct `Num=1,2,3`, reject child rows without a parent, and
  turn an unreadable query/schema into a failure rather than a green result or
  crash. The paired missing/incomplete/orphan/unreadable and complete cases
  passed `8 passed`; the broader CH/importer/migration/schema bundle passed
  `107 passed, 7 skipped`.
- The original 1000-record probe improved from about 4.407 seconds and
  `{table_exists: 2000, fetch_all: 3000}` to 0.553 seconds and exactly
  two catalog-existence queries plus three metadata reads while reporting 1000 imported physical
  records and zero failures. Black on the maintained changed Python files,
  critical Ruff/Flake8-equivalent selectors across `src tests scripts`,
  `compileall`, and `git diff --check` pass on the repaired content.
- A disposable PostgreSQL 16 container then ran the complete CH contract,
  including the four PostgreSQL-native/standard and rollback cases plus the
  new SQLite regression cases: `34 passed`. The explicitly named temporary
  container was stopped and auto-removed. The repaired uncommitted content's
  full local suite passed `2104 passed, 51 skipped, 3 warnings, 6 subtests`.
  The warnings are the existing three `test_time_series.py` tests that return
  booleans; no new warning or failure was introduced.
- The exact-SHA Codex review of
  `f78bdcd7d9856d80e492ff973b96a50e30c7e139` found one further P2: the
  concrete SQLite/PostgreSQL `table_exists` compatibility methods suppress a
  catalog `DatabaseError` as `False`, so the ordinary importer's documented
  preflight retry was unreachable for a real backend query failure. Replacing
  the mock-level failure with a transient failure in SQLite `fetch_one`
  reproduced the defect before implementation: the new regression failed
  with `SchemaMigrationError` rather than retrying.
- Added a strict catalog-existence API that preserves query errors while
  retaining the existing compatibility semantics of `table_exists` for other
  callers. CH preflight and schema verification use the strict path; the
  ordinary importer can now distinguish a missing child table from an
  unreadable catalog and retry only the latter before any mutation. The paired
  regression plus migration contract passed `28 passed` after the fix.

## PR #179 aggregated review repair

- PR #179 was opened at
  `71763a6df90f940ece9487e739832212fffd4f6c`. GitHub Actions `test` and
  `lint` passed, GitHub Copilot reviewed all 24 changed files with no comment,
  and CodeRabbit raised three actionable threads after its review completed.
- Two code findings were independently reproduced. The optimized importer did
  not retry a transient concrete-backend catalog error. More importantly, if a
  child insert failed and the coupled rollback itself raised, the ordinary
  importer entered its generic parent-only fallback. The optimized importer
  did not enter that fallback, but both paths could leave an uncommitted parent
  on the connection for a later context-manager commit.
- Red-first evidence on the PR head was `3 failed, 1 passed`: optimized catalog
  retry aborted, ordinary rollback failure reported success after committing
  one parent, and optimized rollback failure left one visible parent. A
  tightened rollback-invalidation contract was separately red for both
  importers (`2 failed`) before implementation.
- Coupled rollback failure now invalidates the database session, which discards
  any uncommitted parent and prevents a later implicit commit. The ordinary
  importer also refuses to route any CH table through its generic single-table
  fallback. The optimized importer retries only its mutation-free catalog
  preflight once. The paired catalog and rollback regressions pass `4 passed`.
- The remaining actionable thread requested clearer worklog wording and was
  applied directly. Four review-body-only nitpicks about test comments,
  generated-column style, and named parser constants are non-behavioral and do
  not justify further candidate churn under the aggregated-review policy.

## Exact-candidate Codex review repair

- Codex CLI `0.147` (`gpt-5.6-sol`, `xhigh`, session
  `01a006fa-7870-7370-b6c6-1b3028864207`) reviewed exact candidate
  `6ad8cdf8a9233b7e8b9c59834680417f9d580def`. It found one P2 issue: the
  rollback-failure invalidation safely discarded the transaction but the
  documented `with database:` teardown then attempted a second transaction
  operation on the disconnected handler, masking the original error.
- Red-first evidence against that candidate was `3 failed`: ordinary and
  optimized batch imports surfaced `DatabaseError("No active connection")`
  instead of their `ImporterError`, and `import_single_record()` returned
  `False` before context teardown raised the same new error.
- `BaseDatabase.__exit__` now recognizes an already-invalidated session and
  skips its redundant commit/rollback. The connection remains closed, so the
  uncertain transaction cannot be reused or committed; an active connection
  retains the original context-manager behavior.
- The paired rollback regressions passed `3 passed`, and the existing database
  context/transaction tests passed `22 passed`. Full exact-SHA and PostgreSQL
  evidence will be recorded on PR #179 after the repair commit is created.
