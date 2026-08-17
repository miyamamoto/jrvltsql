# JV-Data DataKubun status-domain contract worklog

## 2026-08-17 — iteration start

- Objective: establish one official status-domain contract for all 38 current
  JV-Data record types, preserve documented historical status compatibility,
  and apply it before mutation at raw-parser, both historical importer, single
  record, and realtime caller-dictionary boundaries.
- Minimum scope: status presence, alias agreement, current/legacy allowed-value
  sets, accumulated-versus-realtime differences, and fail-before-mutation
  behavior. Missing primary-key columns and physical DataKubun=0 erase behavior
  remain separate follow-up iterations so this PR does not combine independent
  schema and mutation changes.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated `$WORKSPACE/jrvltsql_status_domain` checkout.
- Branch: `agent/status-domain-contract-20260817`.
- Base/HEAD/origin master:
  `91e71699cf7db148c1f59ee43370493bcaae5da9` (PR #202 merge).
- Published release remains v1.6.10. The repository version is the unreleased
  `2.0.0.dev0`; no tag or release is authorized by this iteration.
- Dependency order: merge this status-domain PR first; then repair missing
  official keys/standard storage; then implement the remaining physical erase
  paths; only after those and fresh provider-to-SQLite/PostgreSQL readback may
  final release preparation resume.
- Implementation uses Codex. The change is a fail-open validator and therefore
  requires red-first tests, an independently regenerated official status
  manifest, and one frozen-candidate critical review. No unavailable reviewer
  is counted as evidence.
- Known official-audit findings entering this iteration:
  raw invalid or missing status is accepted by many parsers and caller-dict
  paths; TC/CC accept a non-current erase status that realtime interprets as a
  delete; accumulated WF includes status 7 while realtime WF does not; and
  documented historical inputs require explicit compatibility for RC and
  pre-2003 WH/WE/AV/JC rather than an undocumented default-to-1 rule.
- Next safe action: independently bind every status set to the pinned official
  workbook/history evidence, design current/history/realtime contexts, then add
  one compact table-driven negative contract and paired valid controls before
  production changes. STOP on unknown provenance being treated as current,
  missing/blank defaulting to success, historical compatibility being removed,
  a caller-dict bypass, mutation before validation, or official-source
  uncertainty.

## 2026-08-17 — official oracle and implementation-boundary audit

- Candidate remains the unmodified base
  `91e71699cf7db148c1f59ee43370493bcaae5da9`; only this new worklog is
  untracked. Two independent Codex reviewers are reading the committed base.
- The pinned `JV-Data4901.xlsx` (`sha256`
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`)
  and `JV-Data4802.xlsx` define identical current DataKubun cells for all 38
  formats. The current accumulated domains contain 154 positive
  `(record_type, DataKubun)` pairs. SDK 5.0.0 binds every root record to the
  common 11-byte header, with DataKubun at byte 3 and MakeDate at bytes 4-11.
- The only explicit accumulated/realtime status-set differences are DM, TM,
  and WF: accumulated status 7 is not supplied in realtime. Realtime domains
  are therefore DM/TM `{0,1,2,3}` and WF `{0,1,2,3,9}`; no extra restriction
  is inferred from a timing table that does not explicitly prohibit exception
  statuses.
- Official history records two status-generation boundaries. RC status 2 was
  folded into status 1 in Ver.2.1.3 on 2005-09-29. WH/WE/AV/JC status 0 was
  removed in Ver.1.0.7 beta on 2003-07-11. A legacy-only value is accepted
  only when MakeDate is strictly before its boundary; missing or unreadable
  provenance is not treated as historical. TC/CC were added later and have no
  documented status-0 generation.
- All 38 parser implementations reach `validate_fixed_record`: 30 directly,
  BT/WC through `super`, and CC/CS/HC/JC/TC/WE through `BaseParser.parse`.
  The raw central gate is therefore the minimal complete boundary. Independent
  probes reproduced generic status `Z` parsing in 27 formats, direct TC/CC
  status-0 parsing, realtime TC/CC physical DELETE calls, and a missing TC
  status silently defaulting to an INSERT.
- The central design has two pure operations: validate a
  `(record_type, DataKubun, MakeDate, context)` tuple against the official
  table, and validate/resolve all accepted record-type and DataKubun aliases
  from a mapping. Missing, blank, conflicting, non-string, unknown, or
  out-of-domain values fail. Successful realtime validation canonicalizes
  `RecordSpec` and `DataKubun` before routing.
- Raw parser validation uses accumulated current domains plus only
  date-proven historical exceptions. Historical importers use the same
  contract. Realtime uses the realtime domains plus only date-proven
  historical exceptions, preserving replay of genuine old WH/WE/AV/JC/RC
  rows without admitting a current delete command.
- Required mutation order: raw gate before field parsing; batch import status
  before standard-schema preflight for the first row and before every
  table/schema/delete/flush action; single import before transaction and schema
  preflight; realtime parsed batch/single and the DM/TM snapshot shortcut before
  schema verification, cache write, or DB mutation.
- Red-first scope is compact rather than one test per reviewer hypothesis: one
  official fixture/pure-contract matrix (all 38, all 154 positives, invalid and
  blank negatives, history boundaries, realtime differences), one all-parser
  central-gate reachability/rejection matrix, and one entry-point matrix for
  both importers, single import, realtime batch/single, alias handling, and
  mutation-free TC/CC rejection. The existing missing-status-default test must
  be inverted because it certifies the bug.
- Next safe action: add only the oracle fixture and these tests, execute them
  against the unchanged base, and record the exact red result before editing
  production code.

## 2026-08-17 — red-first evidence on the unchanged base

- Added the reviewed status oracle fixture, fixture documentation, and compact
  status/header entry tests without changing production code.
- The official history also says the older data-mining format removed status 0
  in Ver.1.0.7 beta, while the current DM format again lists 0. No official
  reintroduction date was found. The fixture records this as unresolved and the
  production policy follows only the documented current row; it does not invent
  a historical interval.
- Red command (Python 3.12, external basetemp, no coverage):
  `pytest -q tests/test_current_record_validation.py tests/test_data_kubun_entry_contract.py tests/test_realtime.py -k 'status or data_kubun or current_record or invalid_first'`.
  Result on exact base `91e71699cf7db148c1f59ee43370493bcaae5da9`:
  `16 failed, 122 passed, 56 deselected, 11 subtests passed`.
- The failures prove the intended negative classes rather than a collection or
  fixture error: blank/unknown physical status did not raise; AV parsed status
  `Z`; all five post-boundary historical-only values remained accepted; both
  batch importers and single import stored a missing status; standard preflight
  added an unrelated RACE column before rejecting the row; and realtime still
  defaulted a missing status to INSERT.
- A separate exact TC/CC realtime negative returned `delete` where the test
  requires `validate` (`1 failed`). This directly records the pre-fix destructive
  behavior. JSON syntax validation of the oracle fixture passed with
  `python3 -m json.tool`.
- Paired controls already remained green in the same run: all 154 current
  workbook pairs passed the physical envelope, equal legacy aliases stored a
  canonical header in all three importer entry paths, and existing official
  parser/realtime positives remained green.
- Next safe action: implement the central status module and wire the proven
  boundaries once, then rerun only the affected focused tests before expanding.

## 2026-08-17 — central implementation and affected-suite green

- Added one production status-domain module containing the 38 current
  accumulated sets, the three explicit realtime overrides, five date-bounded
  historical values, and the UM not-before boundary. The code does not infer a
  DM legacy interval whose reintroduction date is absent from the official
  history.
- `validate_fixed_record` now checks the raw byte-3 value before field parsing.
  Both batch importers validate the first header before any standard-schema
  preflight and every later row before routing; single import validates before
  transaction ownership or migration. Missing/blank status no longer defaults
  to `1`.
- Realtime mapping inputs use the narrower realtime context, canonicalize equal
  aliases, reject a malformed header before cache/schema/DB work, and reject a
  mixed header-invalid batch atomically with `inserted=0`. DM/TM expanded-list
  shortcuts pass the same header gate before snapshot replacement.
- Initial focused green after implementation:
  `215 passed, 11 subtests passed` for the status, entry-point, and realtime
  files. Fatal flake8 (`E9,F63,F7,F82`) reported zero findings.
- The expanded affected run initially found 22 failures in tests that encoded
  a non-official generic status: the all-parser fixture used `1` for H1/H6,
  current RC tests used historical status `2` with a 2026 MakeDate, an SE
  layout fixture left byte 3 blank, and importer tests expected malformed rows
  to be skipped while later rows were stored. Production was not relaxed.
- Corrected those fixtures to official positives, kept caller-built invalid
  status negatives for writer coverage, and changed the generic malformed
  batch contract to fail before mutation. The repeated affected command then
  completed with `1350 passed, 67 skipped, 11 subtests passed` in 13.89s.
- Public `docs/data_support.md` now lists the grouped current domains, realtime
  differences, historical date boundaries, and fail-before-cache/schema/DB
  behavior. This is a behavior statement only; no unreleased support or
  platform claim is added.
- The first full-suite run exposed 19 additional stale mocks. They omitted
  DataKubun entirely, expected malformed headers to be skipped while later
  rows were stored, or used a fabricated record type to reach a database
  failure path. Each positive mock now carries an official status. Invalid
  batches use an explicit invalid status and expect pre-mutation failure; the
  synthetic transaction test now uses the real RA schema plus a rejecting
  SQLite trigger. This preserves the intended DB-failure assertion without a
  validator bypass.
- Final dirty-tree local verification at this stage: full pytest
  `2784 passed, 131 skipped, 22 subtests passed` in 56.29s; the previously
  failing targeted set `56 passed`; affected official/parser/importer/realtime
  set `1350 passed, 67 skipped, 11 subtests passed`; fatal flake8 zero;
  `uv lock --check`, new-file ruff/black, JSON parse, test-gate validation, and
  strict MkDocs build all passed. These results are not yet exact-commit review
  evidence; they justify freezing the first candidate.
- Current worktree remains intentionally dirty with this single iteration.
  No commit, push, PR, merge, tag, or release has occurred. Next safe action:
  inspect the complete diff, commit the worklog and implementation together,
  then run fresh SQLite/PostgreSQL mutation probes and independent review at
  that exact full SHA.

## 2026-08-17 — exact candidate review and aggregated repair

- Froze candidate `2ba07c6fb8f54ba79b84f3e4a7ecfa82b0919e37` and kept the
  worktree clean throughout three independent read-only Codex reviews. Claude
  Code was not used because its quota was unavailable; this follows the
  maintainer-authorized Codex fallback. The exact ordinary full suite completed
  with `2784 passed, 131 skipped, 22 subtests passed` in 71.78s.
- All three reviewers independently matched the production table to the
  official 38-format / 154-current-pair oracle. They also reconfirmed the
  DM/TM/WF realtime overrides, the RC and WH/WE/AV/JC historical boundaries,
  the UM status-9 not-before boundary, and the policy not to infer unknown RA
  or DM historical intervals.
- Aggregation retained four actionable implementation findings rather than
  repairing and re-reviewing one by one: first-header rejection did not unwind
  an already-active caller-owned importer transaction; a successful flush
  remained in importer statistics after rollback; the DM/TM list shortcut
  silently ignored rows outside or inconsistent with its snapshot metadata;
  and a non-enum context value could select the wider base domain.
- Before the repair, one compact regression selection produced exactly
  `8 failed, 2 passed`: context text did not select realtime, two importer
  statistics stayed at one after rollback, all three existing-transaction
  entry paths stayed pending, and both DM/TM mixed-list cases returned only the
  snapshot success. The two `auto_commit=True` streaming controls remained
  green and retained their earlier committed row.
- The repair normalizes the validation context, rolls back first-header
  failures that enter with a pending caller-owned transaction, restores batch
  statistics only after successful rollback, and verifies DM/TM expansion
  count/type/index/metadata/row content before snapshot replacement. It also
  corrects the opt-in PostgreSQL RC current-status fixture and WF atomic-error
  expectation.
- Public documentation now distinguishes per-record rejection from
  call-wide atomicity: `auto_commit=True` preserves completed batches and
  standard-schema preflight changes if a later streamed record is rejected;
  `auto_commit=False` rolls back the active call/sequence and its statistics.
  The 38-format base-domain table is explicitly not a provider availability
  table.
- Post-repair evidence so far: the exact red selection is now `10 passed`;
  affected SQLite tests are `439 passed, 24 skipped, 11 subtests passed`;
  focused live PostgreSQL official contracts are `24 passed`; and an
  independent live PostgreSQL probe passed both importers' same-call and
  cross-call rollback/statistics, single-record rollback, and DM mixed-list
  no-mutation contracts (`POSTGRES_REPAIR_CONTRACT_OK`).
- Enabling every opt-in PostgreSQL test exposed six failures before repair.
  Two were the stale RC fixture, one was the stale WF partial-success
  expectation, and those three are repaired here. The remaining three are an
  unrelated pre-existing RA/SE executable-metadata mismatch; they are not
  hidden as status-domain evidence and remain a separate release blocker for a
  later minimal iteration. No release may proceed while that blocker remains.
- Next safe action: run the final affected/full/static/document/package gates,
  freeze one repaired full SHA, and request one aggregated carry-forward review
  of that SHA. Do not merge on the parent review result.

## 2026-08-17 — carry-forward findings and second aggregated repair

- Froze the first repaired candidate as
  `6fe73c48880e1f1af81fe1e855e68c822a9a6c2e`. Its exact ordinary full suite
  completed with `2792 passed, 131 skipped, 22 subtests passed`; fatal flake8,
  test gate, lock, strict docs, and fresh wheel/sdist gates passed. No release
  decision was made because the separate PostgreSQL RA/SE metadata blocker is
  still open.
- Two independent Codex carry-forward reviews were aggregated before editing.
  First, the new first-header rollback boundary called
  `has_pending_transaction()` without recovery. If that state inspection
  failed, an already-written caller-owned row remained committable and the
  connection was not invalidated. Second, the realtime DM/TM shortcut selected
  its complete-snapshot contract only from the first row and its metadata. It
  therefore admitted reverse-order mixed lists, missing first-row metadata,
  metadata-consistent 19-row lists, a mixed delete, and a direct non-delete
  dictionary.
- Added one compact regression extension for each boundary before changing
  production. Against production at exact `6fe73c48880e1f1af81fe1e855e68c822a9a6c2e`,
  the targeted command produced exactly `5 failed`: three importer entry paths
  propagated the raw inspection error instead of invalidating, while both
  mining formats accepted one or more malformed list forms. Existing valid
  transaction and snapshot controls remained green.
- The second repair centralizes transaction-state inspection recovery. An
  unreadable state now invalidates the connection and raises
  `TransactionRecoveryError`; importer statistics or the active single-record
  checkpoint are restored before propagation. If invalidation also fails, the
  same fail-hard exception type retains both recovery contexts.
- Realtime now selects the DM/TM contract if either format occurs anywhere in
  the list. A non-delete list must contain one format and one status, exactly
  1–18 unique official horse numbers, shared complete metadata, contiguous
  expansion indexes, and exact row content. A metadata-free single status-0
  record remains the only delete form. Mixed lists, missing metadata, 19 rows,
  and direct non-delete dictionaries are rejected before schema or DB work;
  rejection preserves an existing caller transaction. Public documentation
  records these boundaries.
- Post-repair local evidence on the dirty repair tree:
  - original red selection: `5 passed`;
  - focused entry/realtime/DM/TM selection:
    `178 passed, 6 skipped, 11 subtests passed`;
  - expanded affected selection (current record validation, both importer
    entry contracts, importer, realtime, DM, TM):
    `314 passed, 6 skipped, 11 subtests passed`;
  - fatal flake8 for all changed Python files: zero findings;
    `git diff --check`: pass. Repository-wide advisory style debt remains
    outside the fatal gate and was not mechanically rewritten in this repair.
- A fresh disposable PostgreSQL 16 instance ran the existing DM/TM opt-in
  contracts with `6 passed, 78 deselected`. An independent actual-PostgreSQL
  probe then verified physical rollback plus connection invalidation after a
  state-inspection failure, valid 18-row and corrected 17-row snapshots,
  mutation-free metadata/mixed/direct rejection, and the final status-0 erase
  (`POSTGRES_REPAIR_BOUNDARIES_OK`). An initial version of that probe quoted an
  unquoted PostgreSQL table identifier and failed in the probe query itself;
  the corrected query passed on the unchanged repair tree. The disposable
  container was removed and its exact-name inventory is empty.
- No Claude session was used for this repair: the configured quota remained
  unavailable, and the maintainer-authorized independent Codex fallback was
  used. No push, PR update, merge, tag, or release has occurred.
- Next safe action: commit this repair and worklog together, run the final
  affected/full/static/docs/package gates on that exact clean full SHA, then
  obtain one bounded carry-forward critical review without changing the tree.

## 2026-08-17 — exact second candidate review and third aggregated repair

- Froze the second repaired candidate as
  `a587b034270d8f858812e8afc26e2fb572899d5c`. Its exact ordinary full suite
  completed with `2795 passed, 131 skipped, 22 subtests passed`. Three
  independent read-only Codex reviewers were used because Claude Code quota
  remained unavailable. Findings were collected before any edit, following
  the batched-review policy.
- The reviews retained three related boundaries. First,
  `process_parsed_records_batch` still bypassed complete DM/TM snapshot
  replacement, so a corrected 17-horse physical record could leave the stale
  eighteenth horse. Second, the metadata comparison checked only keys present
  in the metadata row, so omitted payload such as `DMTime` or `TMScore` was
  accepted and persisted as NULL. Third, a committed single-record statistics
  checkpoint could be mistaken for a later transaction and restored after an
  unreadable transaction state, under-counting already durable rows.
- Red-first evidence was kept compact by extending the existing transaction
  recovery and mining snapshot tests. Against exact production at
  `a587b034270d8f858812e8afc26e2fb572899d5c`, the focused selection produced
  exactly `5 failed`: three recovery-failure counter cases reported zero after
  a successful prior write, and both DM/TM accepted snapshot metadata with the
  payload key removed. Independent SQLite and PostgreSQL probes additionally
  reproduced the batch bypass: a 17-row correction returned success while the
  old eighteenth row remained, and a metadata-free non-delete row was stored.
- The third repair compares the normalized expanded and metadata rows in both
  directions. It partitions a flat realtime batch into complete 1–18-row
  mining physical operations, one-record erases, and adjacent non-mining
  operations, then applies them in provider order inside one atomic
  transaction. Multiple corrected snapshots are supported; an incomplete
  follower, direct non-delete row, or middle DB failure rejects/rolls back the
  whole batch with `inserted=0`. Successful `inserted` counts provider
  operations rather than final table cardinality.
- Importer recovery now associates rollback statistics with the active
  transaction generation. A stale checkpoint from a committed transaction is
  cleared without reducing its durable counters. If transaction inspection and
  connection invalidation both fail, existing counters are preserved because
  the pending state cannot safely be classified; the fail-hard
  `TransactionRecoveryError` remains the caller-visible result.
- Current dirty-tree evidence after the aggregated implementation and final
  compact test extensions: the original five red cases are now `5 passed`;
  the earlier affected SQLite selection completed with
  `463 passed, 42 skipped, 11 subtests passed`; the focused DM/TM set completed
  with `83 passed, 6 skipped`; actual PostgreSQL 16 DM/TM opt-in contracts
  completed with `6 passed`; and an independent actual-PostgreSQL statistics
  recovery probe returned `POSTGRES_STATS_RECOVERY_OK`. After the final compact
  extensions, the dirty-tree full suite completed with
  `2795 passed, 131 skipped, 22 subtests passed` in 58.44s. Fatal flake8,
  `git diff --check`, `uv lock --check`, strict MkDocs, the fail-closed test
  gate, fresh wheel/sdist content gate, and installed-wheel init smoke all
  passed. The disposable PostgreSQL container was removed and its exact-name
  inventory is empty. Final exact-SHA gates still need to be run after this
  worklog and documentation are committed.
- Claude Code was not invoked in this repair because its configured quota was
  unavailable. The maintainer-authorized Codex critical-review fallback was
  used. No push, PR, merge, tag, or release has occurred. The unrelated
  PostgreSQL RA/SE executable-metadata mismatch remains a later release blocker
  and is not claimed fixed by this status-domain iteration.
- Next safe action: run the full affected SQLite and live PostgreSQL selections,
  fatal/static/docs/package gates, stop the disposable PostgreSQL container,
  commit the complete third repair, and perform one final bounded review of the
  immutable full SHA. Do not open or merge the PR until that final review is
  GREEN.

## 2026-08-17 — final bounded review findings and fourth repair

- Committed and froze the third repair as exact
  `a18ec0316228e93bc2f299715cef61255bb35db6`. Its exact ordinary full suite was
  `2795 passed, 131 skipped, 22 subtests passed` in 57.29s. Fresh PostgreSQL 16
  DM/TM contracts were `6 passed`; fatal lint, lock, test gate, strict docs,
  fresh distribution content, and installed-wheel smoke were green on the same
  clean SHA.
- One bounded read-only Codex carry-forward review found two adjacent P1
  boundaries. A strict WF body rejection could issue a PostgreSQL catalog
  SELECT before the mining early return, leaving a call-created implicit
  transaction open; the next successful DM batch then treated it as caller
  owned and returned success without a durable commit. Separately, a caller
  could commit a single-record sequence, begin a new transaction, and have a
  header rejection rollback that new transaction while restoring the stale
  prior checkpoint, reducing statistics below the durable row count.
- Both checks were extended before production edits. On exact `a18ec031...`,
  the compact SQLite selection produced `3 failed, 2 passed`: the stale
  checkpoint reduced a durable count of one to statistics zero, and both DM/TM
  left the validation-created transaction pending. A fresh PostgreSQL 16 run
  of the mixed invalid-WF/valid-DM sequence produced `1 failed` at the required
  `pending is False` assertion.
- The fourth repair treats every pre-mutation body/header rejection as an
  atomic batch rejection. If no caller transaction existed at entry, it rolls
  back a lazy schema/catalog transaction created by the call; an existing
  caller transaction remains untouched on validation-only rejection. Mining
  structural rejection uses the same cleanup boundary. Single-record header
  rollback now restores statistics only when the checkpoint generation equals
  the active transaction generation; a stale checkpoint is discarded while
  already committed counters are retained.
- Initial post-repair evidence: compact SQLite controls are `4 passed`; actual
  PostgreSQL 16 mixed validation/mining plus native/standard single-record
  checkpoint controls are `5 passed`. The expanded affected SQLite selection
  is `463 passed, 42 skipped, 11 subtests passed`; the expanded live
  PostgreSQL DM/TM/WF selection is `22 passed, 178 deselected`. One stale
  SQLite WF test still expected a body-invalid batch to store its valid suffix;
  it was corrected to the established all-or-nothing strict-batch contract and
  the affected selection then passed. The dirty-tree ordinary full suite is
  `2795 passed, 131 skipped, 22 subtests passed` in 55.88s; fatal flake8,
  `git diff --check`, lock, test gate, and strict MkDocs are green. The
  disposable PostgreSQL container was removed and its exact-name inventory is
  empty. No push, PR, merge, tag, or release has occurred.
- Next safe action: commit this fourth repair, run the exact-SHA focused/full,
  PostgreSQL, docs, and package gates, then perform only a bounded delta review
  of the new immutable SHA. Do not broaden this into another whole-repository
  review.
