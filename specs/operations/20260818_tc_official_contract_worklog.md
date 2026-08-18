# TC official contract iteration worklog

## Start state (2026-08-18)

- Objective: bind the JRA `TC` start-time-change record to the pinned official
  physical layout, status/key/body domains, native/standard/realtime storage,
  exact schema preflight, provider ordering, and durable transaction semantics.
- Minimal scope: `TC` only. The adjacent `CC` record remains a separate later
  iteration even where implementation helpers may ultimately be shared.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_tc_official`.
- Branch: `agent/tc-official-contract-20260818`.
- Base and starting HEAD: `282e03a5cba06fdc42d4d651ee7624b27dadad01`
  (`origin/master`, HC PR #213 squash merge).
- Package version: `2.0.0.dev0`; latest published release remains `v1.6.10`.
  This iteration is not itself a release or production-adoption claim.
- Dependency order: HC is merged; TC is independent of the later CC iteration.
- Working tree was clean at creation.

## Planned contract and evidence

1. Re-derive the TC byte spans, total length, ordered key, status domain,
   history, and delivery context from the pinned JV-Data 4.8/4.9 workbooks and
   SDK 5 source/manifest before changing production code.
2. Extend or add one compact official-contract test module. New/changed
   validators and schema gates must first be shown red on the exact base, with
   paired valid green cases. Avoid a test function per reviewer hypothesis.
3. Cover direct/factory parsing; caller aliases; native `NL_TC`; standard
   `HASSOU_JIKOKU_CHANGE`; `RT_TC`; both batch importers; single-record import;
   SQLite, fresh PostgreSQL, Dual orientation, caller-owned transactions,
   exact-key coexistence/update behavior, and fail-before-mutation migration.
4. Update executable metadata, public support/migration documentation, release
   notes/changelog, and this worklog only to the degree required by the proven
   TC contract.
5. Freeze one full candidate SHA, aggregate independent official-oracle and
   critical reviews, apply at most one consolidated repair batch, then run the
   required focused/workflow/package gates before opening and merging one PR.

## Coding-agent choice

- Complex fail-closed validator/schema/migration work qualifies for Claude
  Fable under `AGENTS.md`. Planned CLI model is `--model fable` with session id
  `eabbe5e2-34f9-4fe1-b4f9-a85d3976f230`; the same session will be resumed for
  review repairs. If Claude authentication/quota prevents useful execution,
  the failure will be recorded and Codex will implement with independent Codex
  reviews rather than silently changing the gate.

### Claude execution result

- Claude Code `2.1.233` was invoked with `--model fable` and session id
  `eabbe5e2-34f9-4fe1-b4f9-a85d3976f230` after the start-worklog commit. It
  exited before reading or editing the repository because the OAuth session was
  expired and could not be refreshed. The CLI also printed non-fatal warnings
  about obsolete `Write(...)` permission-rule spellings in the parent Claude
  settings. No Claude implementation or review evidence exists for this
  iteration. Codex will implement the bounded contract and require independent
  official-oracle and critical Codex review as the recorded fallback.

## Known preliminary risks (not yet official findings)

- Current `TCParser` has no TC-specific key/body validator.
- Native/realtime tables use a six-column race key while standard
  `HASSOU_JIKOKU_CHANGE` currently has no primary key; official key membership
  must be re-derived before deciding whether either layout is correct.
- Key columns and field types are not currently protected by a TC-specific
  strict schema verifier.

## Next safe command and STOP conditions

- Next: extract the TC workbook/SDK oracle and compare it mechanically with
  parser/schema/importer/realtime mappings, then write the smallest red-first
  contract before production edits.
- STOP if HEAD/worktree drifts outside this worklog, pinned official artifacts
  disagree materially, a required real-backend proof cannot be isolated, or a
  destructive/provider operation would be required without new authority.
- No credentials, provider identifiers, or connection strings belong in this
  worklog.

## Official oracle and red-first evidence (2026-08-18)

- Pinned sources were re-read from the locally archived artifacts. SHA-256:
  `JV-Data4802.xlsx` =
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`,
  `JV-Data4901.xlsx` =
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`,
  SDK 5.0.0 `JVData_Struct.cs` =
  `605057bb211eb6a94056a54496f3dd30f864ac2ad140fcfc8840ac8a6ed9e4fe`.
- Both workbook format sheets rows 1509-1528 and SDK `JV_TC_INFO` agree:
  record length 45 bytes; current status is only `1`; the ordered official key
  is `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`; announcement time is
  MDHM at bytes 28-35; changed and prior HHMM values occupy bytes 36-39 and
  40-43; CRLF is bytes 44-45. TC was added 2004-05-25 in Ver.1.1.6. Current
  provider contexts are 0B14/0B16, with 0B14 a complete date snapshot.
- Two independent read-only Codex triages of exact master `282e03a...` both
  ranked TC first. Each reproduced malformed HHMM/MDHM or JyoCD values being
  stored and duplicate standard rows because `HASSOU_JIKOKU_CHANGE` was
  keyless; both recommended keeping CC as the next separate iteration.
- Added compact `tests/test_tc_official_contract.py` plus
  `tc_contract_4901.json` without production edits. After correcting one test
  harness import and one SQLite DDL placement error, the exact base run was:
  `33 failed, 5 passed`. Representative red evidence: parser span lacked
  `RecordDelimiter`; malformed dates/codes/times did not raise; standard
  revision left two rows; schema/nullability/constraint defects were accepted;
  batch/single/realtime caller validation did not fail closed. The valid
  current-status and zero-initialized time controls remained green.
- Exact red command:
  `python -m pytest -q -o addopts='' --basetemp /tmp/jrvltsql-tc-red2 tests/test_tc_official_contract.py`.

## Implementation and backend evidence (2026-08-18)

- Implemented a strict TC parser that binds all 15 physical spans, validates
  fixed-width source text before legacy numeric conversion, accepts only the
  official status `1`, requires real dates/official JyoCD/HHMM values, and
  preserves the official all-zero initial time representations.
- Changed `NL_TC`, `RT_TC`, and `HASSOU_JIKOKU_CHANGE` to the same six-part
  ordered primary key and complete NOT NULL storage contract. Added exact
  type/capacity/nullability/column/constraint preflight to both importers,
  single-record import, realtime dictionaries, standard preflight, and public
  native schema creation. The standard legacy `COMMENT` table is rejected
  rather than guessed as the TC owner.
- Kept the provider distinction explicit: TC has no status-0 record deletion.
  Completed `0B14` responses continue to replace all five date-snapshot tables
  atomically; `0B16` remains event-scoped.
- The compact SQLite contract reached `57 passed, 35 PostgreSQL skipped` after
  expanding both importer classes, auto-commit modes, single/realtime, exact
  schema negatives, and a public SchemaManager preflight pair. Existing
  snapshot/HappyoTime/realtime alias fixtures that had built incomplete TC rows
  were updated to valid complete current records; production strictness was not
  relaxed.
- A dedicated disposable PostgreSQL 16 instance was started only for this
  iteration. Native/standard, DataImporter/OptimizedDataImporter/single,
  auto-commit true/false, same-key provider revisions, realtime rejection,
  unsafe constraint/type/key schemas, and SQLite/PostgreSQL Dual orientation
  reached `92 passed`. PostgreSQL reported both accepted provider operations
  while retaining exactly the revised row, matching SQLite semantics.
- The non-E2E/non-integration full suite completed with `3394 passed, 369
  skipped, 20 subtests passed`. Its first run exposed three shared parser tests
  that still treated a blank TC body as a positive fixture; those tests were
  corrected to carry the official six-key identity and valid announcement and
  before/after times, after which the full suite passed without relaxing the
  production validator.
- The affected parser/importer/migration/realtime selection completed with
  `271 passed, 37 skipped, 9 subtests passed`; the shared all-parser module
  separately completed with `292 passed` after the TC fixture correction.
- Fatal Python lint (`E9,F63,F7,F82`), the repository test-gate validator,
  `uv lock --check`, `git diff --check`, and Black checks for the new TC parser
  and official-contract module all passed. The older shared parser test module
  is not globally Black-clean on the base, so it was deliberately not
  mechanically reformatted beyond the TC fixture block.
- The final disposable PostgreSQL container was removed after the green run;
  no test database or container from this iteration remains active.
- A fresh `git archive` source tree produced the real
  `jltsql-2.0.0.dev0` wheel and sdist. The distribution-content gate passed
  both artifacts, and the extracted-wheel smoke completed `init`, configuration
  display/version, and SQLite table creation using only modules from the wheel.
  Temporary build/install directories were removed after verification.
- Public support/migration documentation, the release draft/changelog,
  executable metadata, and the official-fixture catalog now describe the TC
  contract and rebuild/reimport boundary. No release or production adoption is
  claimed by this candidate.

## Independent review and consolidated repair (2026-08-18)

- Three independent read-only reviews targeted exact clean candidate
  `c5953c8777fa9a592fad8a66dc17b12dba268bc6`: official workbook/SDK oracle,
  SQLite/fresh PostgreSQL/Dual data-integrity attack, and test/package mutant
  review. The official 45-byte/15-span/status-1/six-key/provider-context oracle
  remained correct, but the reviewers found four grouped implementation gaps
  and three test-oracle gaps.
- The implementation gaps were: caller `datetime` values passing the DATE-only
  MakeDate contract; secondary-only legacy `COMMENT` escaping Dual preflight;
  generated/identity official columns and comment-obfuscated SQLite CHECKs
  escaping strict schema validation; and the first invalid direct realtime TC
  opening a lazy PostgreSQL catalog transaction before validation. The test
  gaps were: nullable body columns not explicitly asserted, stale same-date TC
  races not read back after 0B14 replacement, and 0B16 non-replacement not
  bound to monitor behavior.
- Tests were extended before the implementation repair. Exact c595 production
  with those tests failed `12` SQLite cases and `19` cases with fresh
  PostgreSQL enabled. Separately, the test reviewer proved the old 0B14 test
  false-green with a mutation that disabled only the RT_TC date deletion; the
  expanded two-race survivor assertion turns that mutant red.
- One consolidated repair now rejects `datetime`, inspects every concrete Dual
  migration target, rejects generated/identity/hidden official columns,
  lexes SQLite DDL without comments or quoted tokens before CHECK detection,
  and validates direct realtime TC input before any catalog read. Existing
  tests were expanded rather than adding one function per review hypothesis.
- Repair verification is green: SQLite TC/realtime `66 passed, 39 skipped`;
  fresh PostgreSQL 16 TC contract `104 passed`; affected official/importer/
  migration/realtime selection `1413 passed, 309 skipped, 9 subtests passed`;
  and the non-E2E/non-integration full suite `3402 passed, 373 skipped, 20
  subtests passed`. Fatal lint, test gate, lock check, Black on the new TC files,
  and diff check also pass. The repair PostgreSQL container and red/green logs
  were removed.

## Final next safe command and STOP conditions

- Commit the consolidated repair and freeze a clean full SHA. Ask the same
  reviewers only for bounded closure of their recorded findings, then rerun the
  git-archive wheel/sdist content and installed-wheel smoke gates on that final
  immutable candidate. If closure is green, push one PR, resolve every review
  thread, verify the required checks on the exact PR head, and merge before the
  separate CC iteration begins.
- STOP on any non-worklog external drift, backend divergence, unresolved
  correctness/data-integrity finding, or recovery state that cannot be proven
  safe without additional authority.
