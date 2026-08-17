# HR Official Contract Worklog

- Started: 2026-08-18 (Asia/Tokyo)
- Objective: audit and repair the HR payout/refund record parser, native and
  standard storage identity, validation, migration, cancellation semantics,
  importer/realtime behavior, metadata, tests, and public documentation against
  pinned official JV-Data sources.
- Minimum scope: HR only. Unrelated record types and generic refactors are
  excluded unless an HR correctness or data-integrity repair cannot be made
  safely without them.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_hr_official`; remove after
  merge.
- Branch: `agent/hr-official-contract-20260818`
- Base / production master at start:
  `c748da1b0ff9d3c39a1ab455112b9561b6343f39`
- Dependency: AV official-contract PR #210 merged first at the base SHA above.
- Package version at start: `2.0.0.dev0`.

## Review and implementation model

- This iteration covers payout identities, repeated ticket structures, status
  semantics, schema migration, and durable readback, so it is classified as a
  complex data-integrity change.
- Claude Code Fable will be attempted once for the implementation/audit if its
  authenticated session is available. If authentication or quota prevents it
  from reading or acting, that failure is not evidence and Codex continues as
  explicitly authorized by the user.
- Findings will be collected from official-source and independent critical
  reviewers before one repair batch. New validators/gates require a recorded
  red negative plus paired green positive before implementation is accepted.

## Required sequence

1. Re-derive HR physical length, every scalar/repeat span, ordered official key,
   DataKubun domain/history, payout/refund units and sentinels from pinned
   4.8/4.9 workbooks, SDK 5.0 manifest/source, and relevant official/community
   discussions.
2. Compare parser, native/standard/realtime schemas, mapping, importer/single
   paths, metadata, migration verification, docs, and every existing HR test.
3. Aggregate concrete findings; add the minimum failing contract test on the
   unchanged base and record the red result before changing validation/storage.
4. Implement one bounded HR repair and verify actual SQLite and fresh
   PostgreSQL durable storage, provider order, update/erase behavior, caller
   transactions, Dual orientation, unsafe-schema no-mutation, and readback.
5. Freeze an exact clean candidate, run focused/workflow/package gates, obtain
   independent critical reviews, resolve GitHub threads to zero, and merge only
   when all required checks are green.

## Current state

- A new clean worktree was created from freshly fetched `origin/master` at the
  base SHA above. No production code or test has been changed.
- AV PR #210 is merged at the base SHA. Its final candidate, local tests,
  independent reviews, GitHub checks, and unresolved-thread gate were green.

## Official-source audit and pre-implementation findings

- Pinned `JV-Data4802.xlsx` and `JV-Data4901.xlsx` rows 216-295, plus the
  tracked SDK 5.0 manifest, independently agree on a 719-byte HR record, 202
  expanded SDK leaves, status domain `0/1/2/9`, and ordered key
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`.
- The current parser reads only the first of the three official 16-byte
  reserved entries and drops six scalar leaves. Native `NL_HR`/`RT_HR`
  likewise expose only `Yobi1..3`.
- Standard `HARAI` has no primary key and no native-to-standard payout aliases.
  SQLite, PostgreSQL 16, and Dual probes reported successful imports while all
  sampled standard payout columns were `NULL`; repeated status `1 -> 2 -> 9`
  accumulated duplicate rows.
- HR has no record-specific pre-coercion validator. SQLite and PostgreSQL 16
  accepted malformed keys and payout values; a status-0 `RaceNum='1X'` was
  coerced to race 1 and deleted an unrelated valid row.
- HR is absent from strict schema preflight. Wrong/missing primary keys,
  nullable keys, wrong types, harmful extra uniqueness, and a deferrable
  PostgreSQL primary key were accepted until data loss or DML failure.
- PostgreSQL collapses same-key HR rows inside one bulk upsert. The durable
  final state is correct, but importer statistics undercount accepted provider
  operations; SQLite and sequential imports count them all.
- Official change history row 249 records the 2004 same-length reuse of an HR
  reserved span for trifecta data; official special-notes rows 97 and 134,
  rather than row 249, establish the 2004-08-14 availability boundary. No
  HR-specific official source proving a separate historical physical envelope
  was found. The project therefore uses the current 719-byte envelope as an
  explicit fail-closed policy instead of claiming an independently documented
  old parser: races before 2004-08-14 preserve bytes 604-717 as opaque data and
  reject trifecta-like canonical fields. The boundary is race date, not
  MakeDate.
- Official community topic 304 confirms that realtime HR popularity may remain
  blank until all finish positions are finalized. Validation must therefore
  allow blank popularity and must not make it a live-row requirement. Topic 64
  concerns H1/H6 sample flag handling and is not used as direct evidence for
  HR body semantics.

## Independent reviewers and Claude attempt

- Three read-only Codex reviews were run against exact base
  `c748da1b0ff9d3c39a1ab455112b9561b6343f39`. They independently reproduced
  the standard payout loss/keylessness and validation/schema fail-open classes;
  two used fresh disposable PostgreSQL 16 and removed their containers.
- Claude Code `2.1.233` was attempted with `--model fable --effort high` and
  session `1f0f6c64-7284-47c6-a1f5-5892d999a5f7` because this iteration
  changes validators, identity, and transaction-facing storage behavior. Its
  OAuth session had expired and could not refresh, so no Claude output is used
  as evidence. The temporary review worktree was removed. Codex continues as
  explicitly permitted by the user.

## Aggregated repair boundary

1. Parse and store all three reserved entries while preserving the legacy
   `Yobi1..3` names and adding `Yobi4..9`.
2. Add complete `HARAI` aliases and the exact non-null six-column primary key.
3. Validate HR key/body fields before coercion in both batch importers, the
   single-record path, and realtime; status 0 validates only its exact key and
   leaves the body opaque.
4. Strictly verify `NL_HR`, `RT_HR`, and `HARAI` types, capacities,
   nullability, exact PK, harmful uniqueness, and PostgreSQL PK usability on
   every migration target before unrelated additive mutation.
5. Count accepted same-key HR provider operations consistently with SQLite
   while preserving provider order and exact erase semantics.

## Red-first evidence on unchanged base

- Added one compact official contract fixture and test module before changing
  production code. Command:
  `.venv/bin/python -m pytest -q tests/test_hr_official_contract.py
  --basetemp=/tmp/jrvltsql-hr-red --no-cov`.
- Exact base result: `8 failed`. Concrete failures were missing `Yobi4`, four
  malformed keys accepted by the raw parser, status-0 `RaceNum='1X'` accepted
  by the importer header gate, standard `HARAI` retaining 4 rows instead of 2,
  and a wrong seven-column native PK accepted through DML. This is the required
  proof that the new checks can reject the previously green defects.
- A paired 2004 boundary contract was then added: a 2004-08-13 record must keep
  bytes 604-717 in `LegacyReserved604_717Hex` and leave canonical trifecta
  fields empty, while 2004-08-14 uses current trifecta fields. This policy
  preserves undocumented old bytes without asserting that they were always
  blank and prevents them from being mislabeled as trifecta payouts.
- A second official-oracle pass found no workbook or community rule that fixes
  status-9 HR body values as blank, zero, or populated payouts. The repair now
  preserves raw bytes 28-717 in `OpaqueStatus9Body28_717Hex`, stores only the
  six-part key and cancellation state in ordinary columns, and keeps caller-
  built status-9 bodies semantically opaque. This avoids asserting an
  undocumented cancellation payout layout while retaining raw audit evidence.

## STOP conditions

- Stop before mutation if official HR key, status, payout unit, sentinel, or
  repeated-entry semantics remain ambiguous.
- Stop on worktree drift outside this worklog before implementation starts.
- Stop before merge on failed required test, unsafe schema mutation, durable
  count/stat mismatch, unresolved review thread, dirty worktree, or absent
  exact-SHA evidence.
- Do not claim 64-bit SDK support without an installed official x64 runtime
  test, and do not publish private implementation provenance or local paths.

## Implementation and verification progress

- Implemented the aggregated HR boundary in the parser, native/realtime and
  standard schemas, both batch importers, the single-record path, realtime,
  schema metadata, history oracle, and public migration documentation.
- `NL_HR`, `RT_HR`, and `HARAI` now use the ordered six-part official key and
  reject nullable, wrong-type, wrong-capacity, extra-unique, exclusion, and
  unusable PostgreSQL primary-key layouts before DML. Existing incomplete HR
  tables remain a rebuild/reimport boundary rather than being additively
  blessed.
- Raw status 9 retains bytes 28-717 only in the opaque audit field; every
  ordinary body/payout column is explicitly cleared on replacement. A fresh
  PostgreSQL probe caught that the single-record update path initially retained
  old payout columns, and the common cleaner was repaired before this candidate
  was accepted.
- Fresh disposable PostgreSQL 16 verification passed `63` HR contract cases,
  including native/standard, regular/optimized/single, auto-commit true/false,
  provider order, status-9 clearing, realtime, unsafe schema, and both Dual
  orientations. The dedicated container was removed after the run.
- SQLite affected coverage passed `323` tests with `23` skips and `9` subtests.
  The first full suite then exposed eight legacy tests and one performance
  fixture that still treated a header-plus-spaces HR envelope or partial caller
  dictionary as valid. Those fixtures were changed to construct complete
  official HR records; the validator was not weakened. The final Python 3.12
  suite passed `3200` tests, skipped `277`, and passed `20` subtests.
- Workflow-equivalent fatal flake8 (`E9,F63,F7,F82`) reports `0`; the workflow
  test-gate validator passes; `uv lock --check` passes. Full Ruff remains an
  advisory legacy-debt report and was not used to reformat unrelated files.
- A fresh PEP 517 wheel and sdist build passed the distribution-content gate
  and extracted-wheel SQLite init smoke. The wheel had `100` members and the
  sdist `121`; both contained zero `specs/` entries and zero removed
  `crawler_audit_*` documents. Strict MkDocs build also passed.
- Actual provider acquisition is intentionally not credited to this HR
  candidate; the cumulative release candidate must
  repeat the pinned-SHA fresh-download, parse, EOF/close, and durable
  SQLite/PostgreSQL readback gate before release.

## Published candidate

- Initial implementation commit:
  `d5db5de839b40fb9d8b9867d729e615913473b28`.
- Draft PR: `miyamamoto/jrvltsql#211`, targeting `master` from
  `agent/hr-official-contract-20260818`.
- The branch was pushed only after confirming `origin/master` remained the
  recorded base, the worktree was clean, and the local test/package evidence
  above was complete. Independent Codex review is the next gate; do not mark
  the PR ready or merge before its findings are aggregated and resolved.

## Aggregated review of published candidate

- Three independent read-only Codex reviews examined exact candidate
  `0a07e3d21121945632fca527afcb71d848cc9b97`. GitHub `lint`, `test`, and
  `windows-batch-syntax` were successful, the conditional performance job was
  intentionally skipped, and unresolved review threads were zero. The single
  requested GitHub Copilot review returned quota exhaustion, so it supplied no
  correctness evidence. The PR remained draft and was not mergeable by policy.
- P1 findings accepted as one repair batch:
  1. nonempty native HR tables with an exact non-null key but missing payout or
     audit columns were additively altered and the unrecoverable historical
     values silently became `NULL`;
  2. a status-0 exact erase was rejected when the caller supplied a nonempty
     status-9 audit field, contradicting full body opacity;
  3. integer horse/combination identifiers passed validation and lost leading
     zeroes (`0711` became `711`);
  4. PostgreSQL HR nullability verification searched only `current_schema()`
     and rejected a valid relation resolved later in `search_path`;
  5. E2E check E-5 passed when no status-1/2 HR row existed, so the check could
     still certify an unmeasured scope.
- P2 findings were also adopted where they strengthen the same official
  contract: all nine reserved subfields use text storage, the three reserved
  flag positions require official value `0`, the HR repeat oracle is bound to
  SDK top-level start/count/stride and nested widths with first/middle/last
  parser sentinels, and history/community citations distinguish official fact
  from project policy.

### Review red-first evidence

- Production remained at exact `0a07e3d21121945632fca527afcb71d848cc9b97`
  while the minimum regression assertions were added. SQLite command covering
  HR storage, migration, and E2E returned `17 failed, 28 passed, 25 skipped`.
  The failures included missing-column migration, reserved flag `1`, integer
  `WideKumi2`/`Yobi8`, native reserved-value truncation, status-0 opaque-field
  rejection across the existing entrypoint matrix, and empty-scope E-5.
- Fresh PostgreSQL 16 then ran only the new later-`search_path` contract on the
  unchanged production code and returned `2 failed, 66 deselected` for native
  and standard storage. This proves the new verifier regression can say no on
  the old implementation rather than only exercising a green path.

### Aggregated repair and provisional verification

- Native `Yobi1..9` are now text; caller horse/combination identifiers require
  exact-width ASCII strings; element 6 of the three ticket flag arrays requires
  `0`; reserved subfields remain CP932 text without invented numeric meaning.
  Status 0 returns immediately after status/key validation and ignores every
  body and audit alias.
- Existing native HR tables no longer allow any missing column during strict
  preflight. PostgreSQL nullability uses the relation selected by
  `to_regclass`, matching the key/type/constraint verifiers across the full
  visible `search_path`. E-5 now requires a nonempty eligible scope as well as
  zero bad payouts.
- On the repaired working tree, official-oracle/HR/SQLite coverage passed
  `119` tests with `25` skips; the full affected selection passed `703` with
  `32` skips and `9` subtests. Fresh PostgreSQL 16 passed `73` HR cases. The
  full Python 3.12 suite passed `3207`, skipped `279`, and passed `20`
  subtests. Fatal flake8 reported `0`, the test gate and `uv lock --check`
  passed, and strict MkDocs passed. These runs precede the repair commit and
  are provisional; exact clean-SHA verification and package gates remain
  required before ready/merge.

## Exact repair candidate verification

- Aggregated repair commit:
  `9e50098c966a9480d16b03ecd922efb1f5a660c9`. A fresh fetch confirmed
  `origin/master` remained
  `c748da1b0ff9d3c39a1ab455112b9561b6343f39`; the repair candidate worktree
  was clean and `git diff --check HEAD^ HEAD` passed.
- Exact-SHA Python 3.12 full suite: `3207 passed, 279 skipped, 20 subtests
  passed`. Exact-SHA fresh PostgreSQL 16 HR/storage/migration/E2E selection:
  `73 passed`. The disposable PostgreSQL container was stopped and removed
  after the run.
- Exact-SHA workflow and documentation gates: fatal flake8
  `E9,F63,F7,F82 = 0`, `scripts/validate_test_gate.py = PASS`,
  `uv lock --check = PASS`, and strict MkDocs build = PASS.
- A fresh `git archive` of the exact repair commit was built through isolated
  PEP 517 into wheel and sdist. The distribution-content gate and extracted-
  wheel init/SQLite bootstrap smoke both passed. The wheel contained `100`
  members and the sdist `121`; each contained zero `specs/` entries and zero
  removed `crawler_audit_*` documents. Temporary build and documentation
  directories were deleted after verification.
- This exact repair commit still requires one bounded carry-forward review of
  the reviewed findings, followed by final PR-head CI/thread/clean gates. No
  release or provider-acquisition claim is made by this iteration.

## Bounded carry-forward finding

- Three independent Codex reviewers examined exact candidate
  `c5385c5ada7b27dc1372cc762034c2c62129a554` and agreed on one new P1
  over-rejection. The repair applied the official reserved-six rule to all six
  flag arrays, although JV-Data4901/4802 rows 234, 243, and 252 reserve only
  `FuseirituFlag6`, `TokubaraiFlag6`, and `HenkanFlag6`. The sixth elements of
  `HenkanUma`, `HenkanWaku`, and `HenkanDoWaku` are ordinary refund targets and
  may be `1`.
- Red-first evidence on unchanged candidate `c5385c5...`: a compact raw/parser
  plus caller-validator regression for `HenkanUma6`, `HenkanWaku6`, and
  `HenkanDoWaku6` returned `3 failed`; each parser call returned `None` after
  logging `reserved and must be 0`.
- The bounded repair limits the reserved-six rule to the three official ticket
  flag arrays, retains negative coverage for all three reserved fields, adds
  positive raw/caller coverage for all three refund-target arrays, and narrows
  the public documentation wording accordingly. Exact green verification and
  a final bounded review remain required before this PR can leave draft state.
- After the repair, the HR SQLite selection passed `54` tests and skipped `25`.
  Its existing native/standard × DataImporter/OptimizedDataImporter/single ×
  owned/caller transaction matrix now writes and reads back all three valid
  sixth refund-target flags as `1`. A fresh disposable PostgreSQL 16 instance
  ran the same affected selection with PostgreSQL integration enabled and
  passed `79` tests, including native and standard durable readback of those
  flags. The exact-name container was then stopped and removed.

## Ready-state review findings

- Marking exact candidate `10f168f89391c19dc367c714413afca401fa959c`
  ready triggered one GitHub Codex thread and two CodeRabbit correctness
  threads. The PR was returned to draft before any further edit.
- The GitHub Codex finding was accepted as a project-policy/data-retention
  defect, not as a new official-format claim. Whole-record strict CP932 and
  field decoding ran before the status-9 and pre-2004 opaque branches, so
  bytes explicitly promised as lossless hex could discard the record first.
  The same root affected status-0 raw deletes, whose body is declared
  uninterpreted.
- Red-first evidence on unchanged `10f168f...`: status 9 with invalid CP932 at
  offset 102 and a 2004-08-13 record with the same class at offset 603 both
  returned `None`; all 12 SQLite storage/entrypoint cases rejected a status-0
  raw body before exact erase. Together with the revised E-5 contract, the
  compact selection returned `18 failed, 6 passed`.
- CodeRabbit correctly identified that E-5 must not treat every status-1/2 row
  as a normal positive single-win payout. Official rows 229, 238, 260, and 261
  do not establish zero yen as valid for non-established or special-refund
  pools, so the suggested simple exclusion was narrowed further: one shared
  SQL scope now requires both flags zero and an actual winning horse number;
  within that same scope, NULL, blank, zero, and negative payouts are failures.
  Flagged-only/no-sale-only scope therefore remains unmeasured and fails rather
  than producing an empty-scope green result.
- The repair keeps the generic fixed-record validator strict. HR constructs a
  validation view that masks only the already-selected opaque byte ranges,
  parses header/key from original strict bytes, and generates hex exclusively
  from the untouched raw record. Current interpreted payouts, legacy prefix,
  record ID, status, MakeDate, six-part key, and CRLF remain fail-closed.
- The immediate repaired selection passed `24` tests; the full affected SQLite
  selection passed `64` and skipped `25`. A fresh disposable PostgreSQL 16
  instance passed all `88` affected tests, including native/standard durable
  readback of an opaque status-9 body, and was removed. CodeRabbit's second
  thread was also adopted by making the E-5 harness assert its imported script
  symbols and exactly one E-5 result, so a script-contract break cannot surface
  as an opaque lookup failure. These results precede the repair commit; exact
  candidate review and GitHub thread resolution remain required before
  ready/merge.

## Exact opaque-policy candidate and CI follow-up

- The aggregated opaque-policy/E-5 repair was committed and pushed as exact
  candidate `d21c4a13c67c7a4fcc492adf9fb10f8a3b184607`. Its affected SQLite
  selection passed `64` tests with `25` skips, a fresh PostgreSQL 16 selection
  passed `89` tests, fatal flake8 and the fail-closed test gate passed, and the
  disposable database was removed. Three independent bounded Codex reviews
  returned P0/P1/P2 = 0. All three GitHub review threads were answered with the
  relevant official/project-policy boundary and resolved.
- GitHub Actions run `32079318069` was not waived: its Linux `test` job executed
  and failed, while `lint` and `windows-batch-syntax` succeeded and performance
  was the intentional zero-step PR skip. The exact failure was
  `test_all_factory_parsers_reach_the_central_status_gate`: HR alone reached
  `validate_data_kubun` twice. The parser used `validate_fixed_record` both for
  the fixed-record envelope and again for the status/date-specific CP932 view.
  The second call was redundant; its only intended duty was strict decoding of
  the masked interpretation view.
- Red evidence is the exact d21 CI assertion: the observed status-gate sequence
  contained a duplicate `HR` and differed from the all-38 oracle at index 14.
  The repair retains the first `validate_fixed_record` call, so HR still reaches
  the central fail-closed status gate exactly once, and narrows the second pass
  to `ENCODING_JVDATA` strict decode. The previously failing central-gate test
  plus all HR contract tests then passed `53` with `25` skips. The complete
  GitHub-equivalent Linux suite passed `3208`, skipped `273`, deselected `14`,
  and passed `20` subtests with 78% coverage. A new exact commit, push, CI, and
  final clean/thread gate remain required before merge.
