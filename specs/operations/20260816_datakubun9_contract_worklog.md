# DataKubun=9 cancellation contract worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: reconcile cancellation/deletion handling with the current official
  JV-Data `DataKubun=9` contract at every historical and realtime import path.
- Minimum scope: identify which record types define `9` as cancellation,
  distinguish state values that must remain queryable from explicit physical
  erases, verify primary-key and rollback behavior, add
  one minimal red-first regression contract, implement the shared policy, run
  focused and necessary broader tests, and complete one reviewed PR/merge.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated worktree for the branch below; its local absolute path is
  intentionally omitted from this tracked public record.
- Branch: `agent/datakubun9-contract-20260816`.
- Base/initial HEAD/origin master full SHA:
  `d2935dff76a96a1b9e4045f48ea07257663651c0` (PR #187 merge).
- Dependency order: JVOpen dataspec contract PR #187 is merged. Parser framing,
  release versioning/publication, NAR follow-up, and MCP-server follow-up remain
  later iterations.
- Production/release version at start: tag and project version `v1.6.10` /
  `1.6.10`. This iteration does not release.
- Agent/model: Codex only. No Claude session or external coding agent is used.

## Plan and gates

- Re-read the current SDK archive's record-specific DataKubun definitions and
  change history; do not infer one universal meaning from the shared header.
- Recheck current official notices and community/staff discussions for later
  cancellation-semantic changes. Official record definitions remain controlling.
- Inventory parser output, table mappings, primary keys, historical import,
  optimized/native import, realtime upsert/delete, and expanded child-row paths.
- Before changing a check/policy, extend the smallest existing regression test
  and run it against the current production code to prove the fail-open behavior.
  Pair every rejection/deletion case with a retained-state or normal-data case.
- Freeze one candidate, run affected SQLite/PostgreSQL/importer/realtime tests,
  workflow-equivalent checks as warranted, and a bounded actual-acquisition
  proof if this change can alter stored provider data.
- Request one GitHub-native Copilot review, use Codex review, aggregate findings,
  require unresolved threads zero, successful CI, exact local/remote head
  equality, and a clean worktree before merge.
- STOP on conflicting official record definitions, missing keys that make a
  delete ambiguous, partial expanded-row deletion, rollback failure, provider
  cleanup failure, base drift, or any unresolved actionable review finding.

## Starting question

- The repository already has partial realtime tests for `DataKubun=9`, but the
  prior official compatibility audit identified payout/vote/odds families as a
  remaining area requiring record-specific verification. No finding is accepted
  until the current official definitions and every importer path are rechecked.

## Official and observed evidence

- The current SDK-bundled JV-Data specification Ver.4.9.0.1 defines
  `9:レース中止` and `0:該当レコード削除(提供ミスなどの理由による)` separately
  for HR, H1, H6, and O1 through O6. The immediately prior Ver.4.8.0.2 contains
  the same definitions, so this is not a newly introduced meaning.
- The current specification's cancellation-operation note says that H1/H6 are
  provided with DataKubun 9 after prior vote-count publication and O1-O6 are
  provided with DataKubun 9 after prior odds publication. It separately says
  that HR is not normally provided for a cancelled meeting, while the HR record
  format still reserves 9 for race cancellation. The format-specific definition
  remains authoritative if such a record is received.
- A current official web copy of Ver.4.9.0.1 corroborates the SDK material. A
  search of the official developer community and public implementation
  discussions found no later notice redefining 9 as physical deletion; the
  relevant community material instead continues to direct implementers to the
  JV-Data specification for record semantics.
- A read-only aggregate check of the available historical JRA database found
  DataKubun 9 rows in H1, H6, and every O1-O6 table. Across those rows, every
  normalized child primary-key component was populated (zero blank child keys).
  HR had no DataKubun 9 row, consistent with the cancellation-operation note.
  No race identity or provider payload was recorded here.
- Current historical importers naturally retain DataKubun 9 when a normalized
  row has a complete key. The realtime single-row dispatcher instead treats 9
  as deletion outside RA/SE/WF, and its batch path bypasses mutation dispatch.
  Historical DataKubun 0 is also not applied uniformly: an exact-key row can be
  upserted with status 0, while a header-only expanded-record erase can be
  skipped for an incomplete child key, leaving stale rows.
- `headDataKubun` is a legacy flattened name for the same record-header field,
  not a separate provider mutation channel. Current parsers emit `DataKubun`;
  both names must resolve to the same record-specific meaning for compatibility.

## Implementation decision before tests

- Define one shared set of record families whose DataKubun is domain state:
  RA, SE, HR, H1, H6, O1-O6, and WF. For those families, 9 is retained by
  upsert and only 0 requests physical erase.
- Expanded H1/H6/O1-O6 erases use the six-part race key because one physical
  JV-Data record is normalized into multiple child rows. RA/HR use the same
  race key, SE adds Umaban, and WF uses Year/MonthDay.
- Preserve provider order around erases by flushing a pending table batch before
  deletion. If a realtime bulk call contains an erase, use ordered single-row
  dispatch for that call; ordinary odds batches retain the optimized path.
- Reject conflicting simultaneous `DataKubun` and legacy `headDataKubun` values
  rather than guessing which status controls a destructive mutation.
- Red-first coverage will exercise current and legacy cancellation names,
  realtime single and batch paths, and historical exact/expanded erase behavior
  through both importer implementations. Positive cancellation retention and
  zero-only deletion are paired in the same contract.

## Red-first evidence and implementation

- Before changing production code, the focused contract run failed as intended:
  legacy RA `headDataKubun=9` dispatched delete; HR/H1/H6/O1-O6
  `DataKubun=9` dispatched delete; conflicting current/legacy values were not
  rejected; realtime batch erase was rejected as an incomplete child row; and
  historical expanded erase was skipped, leaving the prior snapshot. The
  substantive result was 14 failed assertions with the pre-fix implementation
  (plus passing RA/SE/WF controls). One optimized-statistics exact-dict mismatch
  was a test-only assertion issue and was narrowed to the three contract fields
  before implementation.
- Implemented one record-specific policy for RA/SE/HR/H1/H6/O1-O6/WF. Current
  and legacy header names now resolve identically and conflicting simultaneous
  values fail closed. DataKubun 9 takes the insert/upsert path for these record
  families; DataKubun 0 takes the physical-record erase path.
- Historical ordinary and optimized import loops flush the target table before
  a zero erase, apply the correct physical key, preserve provider order, and
  count the erase as one processed physical record. Realtime bulk processing
  falls back to ordered dispatch only when destructive mutation is present;
  ordinary bulk odds ingestion remains batched.
- A final Codex diff review found that the legacy alias selected the correct
  realtime operation but was dropped before persistence. Tightening the
  existing legacy test first reproduced `KeyError: 'DataKubun'`; the shared
  metadata normalizer is now also used by realtime writes, and the same test
  passes while proving that only canonical `DataKubun=9` reaches storage.
- First post-fix focused run: 6 passed with 12 subtests. This covers both
  historical importer implementations, realtime single/bulk paths, current and
  legacy names, cancellation retention, zero erase, and alias conflict rejection.
- Provider-order coverage then ran ordinary -> zero erase -> cancellation in one
  call and confirmed the final cancellation state for both importer
  implementations and realtime batch processing. A later zero erase removed the
  exact RA row and every normalized O1 child row.
- Backend coverage on a fresh isolated PostgreSQL 16 instance passed all 17
  expanded-storage tests, including ordinary/optimized importers, realtime bulk,
  native normalized tables, and the standard-name RACE table. SQLite affected
  coverage passed 91 tests with 7 environment-gated skips and 12 subtests.
- An acquired historical cancellation snapshot was replayed without recording
  its race identity: all 54 actual normalized O1 rows had complete keys, both
  historical and realtime paths retained all 54 with DataKubun 9, and a
  header-only zero erase removed all rows from both targets.
- Full local suite on the candidate worktree passed: 2,342 tests, 72
  environment-gated skips, 15 subtests, and three pre-existing pytest warnings.
  No test failed.
- After the legacy-persistence repair, the affected SQLite set passed again:
  91 tests, 7 environment-gated skips, and 12 subtests. Syntax compilation,
  diff whitespace validation, and the workflow's fatal flake8 selector also
  passed on the implementation tree. Exact-SHA workflow, PostgreSQL, and actual
  snapshot replay evidence will be attached to the PR after the candidate is
  committed.

## Boundary discovered for a later iteration

- `use_jravan_schema=True` has legacy split child tables for expanded vote/odds
  records. Several child schemas intentionally omit the record-header
  DataKubun, and the current mapping does not materialize their separate header
  tables. Native NL/RT storage, realtime storage, and standard-name RACE are
  covered here, but this iteration does not claim that the legacy split
  H1/H6/O1-O6 representation can expose cancellation status.
- That pre-existing structural mismatch is broader than mutation dispatch and
  will be handled as a separate standard-schema storage iteration before
  release. Until then it remains a release blocker, not an accepted omission.

## Next safe command

- Freeze and commit the reviewed implementation tree, then run the required
  focused/workflow-equivalent, PostgreSQL, and bounded acquired-snapshot checks
  against that full candidate SHA before opening or merging the PR.
