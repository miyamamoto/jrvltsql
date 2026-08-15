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
2. Run the required focused/full/workflow-equivalent/static commands again on
   that immutable full SHA and record the SHA in PR metadata rather than adding
   a self-referential worklog commit.
3. Run the exact-SHA Codex critical review, aggregate actionable findings once,
   then push/open the CH PR. Stop for any actionable finding, failed check,
   head drift, unresolved thread, or dirty worktree.
