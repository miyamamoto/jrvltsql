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
