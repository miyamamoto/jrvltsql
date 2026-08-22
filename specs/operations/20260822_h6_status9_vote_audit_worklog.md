# H6 status-9 vote-shape audit worklog — 2026-08-22

## Start state and objective

- Objective: before repeating the multi-hour five-year JRA `RACE` setup,
  independently determine whether official/provider H6 race-cancellation
  (`DataKubun=9`) records can retain a combination while returning the
  eleven-byte vote field as spaces, analogous to the H1 provider shape fixed
  by PR #240.  Do not relax H6 on analogy alone.
- Minimum scope: pinned current official H6 layout and cancellation note,
  existing registered-data replay evidence, available local raw-cache evidence,
  the current H6 parser/importer contract, and one bounded negative/positive
  reproduction if a real shape is established.  H1, H6 schema/key/storage,
  other record families, runtime dialog behavior, release versioning and the
  development provider retry are out of scope.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260822_jrvltsql_h6_status9_audit`.
- Branch: `audit/h6-status9-vote-20260822`.
- Base/start HEAD: `1ee2ccb3ee5c104a15177f57281004395e669bb7`, exact
  fetched `origin/master`, the squash merge of H1 PR #240.
- Related runtime merge: `miyamamoto/jrvltsql-wine-runtime` PR #30, merge
  `4851ef922bd927b541f8d74d88122181a6b1dcb5`.
- Implementation/audit agent: primary Codex.  No Claude session is used for
  this bounded evidence audit; if a data-contract change becomes necessary,
  its red-first implementation remains in this same iteration/worktree.

## Known evidence at start

- Pinned JV-Data Ver.4.9.0.1 gives H6 the official statuses
  `0/2/4/5/9`, an eleven-byte vote field, and the same cancellation-operation
  note as H1: status 9 is supplied after vote-count data was previously
  provided.
- Existing tracked registered-data inspection recorded at least one status-9
  H6 physical record expanding to all 4,896 ordered trifecta combinations.
  That older replay proved owner/child retention and status-0 removal but did
  not record whether each raw vote span was digits or spaces; it predates the
  present strict H6 caller validator and therefore is not proof that the
  current validator accepts the provider shape.
- Current `H6Parser.validate_current_fields()` requires every non-total
  combination `SanrentanHyo` in live statuses `2/4/5/9` to be exactly eleven
  ASCII digits.  Status 0 intentionally returns after key validation because
  delete bodies are opaque, and a totals-only status-9 snapshot is already
  supported.  No code change is justified until an exact combination-bearing
  blank-vote provider shape is established.
- Read-only scan of the 110 current `RACE` v2 raw-cache files (135,354
  length-prefixed records) found zero H1 or H6 status-9 records.  This is a
  negative availability result, not evidence that the shape cannot occur.

## STOP and evidence contract

1. Never infer H6 semantics solely from the H1 fix.  Require pinned official
   field semantics plus a provider/registered raw or normalized H6 instance.
2. Do not disclose race identity or raw provider bodies.  Record only status,
   field-shape counts, byte-class counts, hashes, and aggregate outcomes.
3. If a valid blank-vote shape is found, extend the existing H6 contract test
   once and prove it red on this exact base before changing production.  Pair
   it with statuses 2/4/5 and non-space whitespace negatives.
4. If no stronger evidence can be recovered, finish this as an audit-only
   worklog and retain the existing fail-closed validator.  A future provider
   failure then supplies the missing exact evidence; do not preemptively widen
   acceptance.
5. Stop on worktree drift, provider/DB mutation, a failed unrelated gate, or
   any need to start a new JV-Link acquisition.  This iteration is read-only
   until an evidence-backed red test exists.

Next safe action: inspect the pinned H6 layout fixture/workbook-derived oracle,
the registered-data replay history, and local immutable provider/cache sources
for an anonymized status-9 vote-byte distribution.  Then decide explicitly
whether production/test changes are justified.

## Read-only evidence closure

- The pinned current workbook
  `JV-Data仕様書_4.9.0.1.xlsx` has SHA-256
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`.
  Its H6 format rows 370 and 382--385 independently confirm status
  `0/2/4/5/9`, 4,896 21-byte trifecta slots, a six-byte combination, an
  eleven-byte vote and a four-byte favourite order.  The vote description
  distinguishes `ALL0` (pre-sale cancellation/no votes) from spaces
  (unregistered).  Special-note rows 255 and 276 say H1/H6 status 9 is
  supplied only after prior vote-count data.  These facts establish that an
  eleven-space vote is an official field value, but they do not establish
  that a combination-bearing H6 status-9 row uses that value.
- The pinned official SDK document
  `JRA-VAN Data Lab.開発ガイド_4.2.2.pdf`, obtained from the official SDK
  distribution page <https://jra-van.jp/dlb/sdv/sdk.html>, has SHA-256
  `1792c6b6d3e06b7f782b402e924d61da0a4c8ef5c10b0cc520be35882bd7db57`.
  Section 1.2.2 states that provider data is compressed and encrypted and
  that software receives decrypted records from JV-Link.  The retained
  retained H6 provider object is consequently recorded only by anonymized
  metadata (2,442,161 bytes, SHA-256
  `14e28d4d366e0630b2d243972095f7c021a37c577e3ab4ac030c11cd123318e4`);
  it is not treated as an offline-decodable record source.  Calling
  `JVOpen`/`JVRead` merely to inspect it would violate this iteration's
  no-provider-acquisition/read-state-mutation boundary.
- A second read-only scan of every current local `RACE` cache member found
  110 v2 files, 135,354 well-formed length-prefixed records, zero malformed
  files, zero H1 status-9 records and zero H6 status-9 records.  No raw body or
  race identity was emitted.
- A read-only query of the active development PostgreSQL tables found zero
  `DataKubun=9` rows in both `public.nl_h6` and `public.rt_h6`.  The older
  tracked registered-data replay remains useful proof that one H6 status-9
  record expanded to 4,896 rows, but because its vote-byte distribution was
  not retained it cannot close the present question.
- Current production still accepts totals-only H6 cancellation snapshots,
  treats status 0 as key-only opaque deletion, and requires an eleven-digit
  vote for every combination-bearing live-status row.  No new provider shape
  contradicts that fail-closed boundary.

## Decision and verification

- This iteration is audit-only.  No parser, importer, schema or test is
  changed.  Permitting blank combination votes would broaden accepted input
  on an official possibility without the required provider instance; that is
  specifically disallowed by the STOP contract.  H6 therefore remains strict.
- This is not evidence that H6 can never emit the H1 shape.  If a future
  provider run returns an H6 status-9 combination with an empty normalized
  vote, that exact failure plus the original raw eleven-byte class is the
  trigger for one paired red-first H6 regression.
- The pre-closure worklog commit was
  `4f1b4c5c632690f02b8a161ee32985648ba74c26`; evidence closure was reviewed at
  `9d184da7e83d93a910aed01390107e7a9790ba17`, both based on
  `1ee2ccb3ee5c104a15177f57281004395e669bb7`.  The exact final PR head is
  intentionally recorded in the PR description and GitHub metadata because a
  tracked file cannot self-reference the commit that contains itself.
- The first local focused command accidentally selected an external Python
  3.10 `pytest` after `uv` had created a different environment and stopped at
  collection because Python 3.10 has no `enum.StrEnum`; it is not counted as a
  candidate test result.  All generated environment/coverage/cache artifacts
  were removed.  Re-running from the existing repository Python 3.13.5
  environment with the current worktree on `PYTHONPATH` passed the bounded H6
  contract: `158 passed, 13 skipped` (PostgreSQL opt-in cases excluded).  No
  ignored artifact remained in this worktree.

Next safe action: commit and push this audit conclusion, update PR #241 to the
exact candidate, make it ready for the repository's one native review, and
merge only after CI, review, unresolved-thread count and clean-worktree gates
are green.  Then release the next `2.0.0.dev` from the resulting master before
retrying the development provider through `ingestctl`.

## Provider-triggered repair continuation

- The audit-only decision above was merged as PR #241.  A subsequent real
  five-year development `RACE` setup supplied the exact missing evidence and
  therefore triggered the bounded repair contemplated by the STOP contract.
- Repository/worktree/branch:
  `miyamamoto/jrvltsql`,
  `/home/keiba/scratch/20260822_jrvltsql_h6_status9`,
  `fix/h6-status9-empty-votes-20260822`.
- Fresh fetched base/start HEAD:
  `18ddb16f664750e35b31527ae85ba09e540ca0a5`, the `v2.0.0.dev4` release
  commit on `origin/master`.
- Runtime under test reported `src.__version__ == 2.0.0.dev4` and used the
  same `src/parser/h6_parser.py` SHA-256 as this base,
  `9ccbc2cf8eca16a7b8a764d189ea989b7d521b708f2d0854eb2e8919ea8f57f8`.
- The real setup reached a combination-bearing H6 `DataKubun=9` row whose
  parser-normalized `SanrentanHyo` was `""`.  The importer then failed closed
  with `H6 SanrentanHyo must be exactly 11 ASCII digits`; no subsequent setup
  stage was started.  The sanitized local log is 76,748 bytes with SHA-256
  `2d40a17cf03d01899ad1a3fd36a83225f146dfb1a19794fc80b242922897e267`.
  Race identity and provider body bytes are intentionally not recorded.
- The failed fetch rolled back its incomplete raw-cache write, so the exact
  physical record is not retained in the public cache.  The paired regression
  must therefore combine the observed canonical provider value with the
  pinned official eleven-space initial value and must reject non-space
  whitespace at the parser boundary, as the merged H1 repair does.
- Minimum implementation scope: extend the existing H6 official-contract test
  once, prove the status-9 provider blank red on this exact base, permit only
  the canonical empty vote for combination-bearing status 9, reject the same
  value for statuses 2/4/5 and reject `None`/caller whitespace/non-space raw
  whitespace, preserve storage as SQL `NULL`, update the H6 public contract,
  and rerun the bounded H6 suite.  Schema/key/snapshot semantics and every
  other record family remain out of scope.
- Implementation agent: primary Codex.  No Claude session is used because the
  H1 implementation is already a reviewed same-contract reference and this is
  a two-boundary parser/validator parity repair rather than a new gate design.

Next safe action: add the paired H6 regression only, run it against this
unchanged base and record the exact red, then change production and docs.

## Red-first evidence and implementation

- Added one paired regression to the existing H6 official-contract module and
  ran only that test before changing production.  On exact base
  `18ddb16f664750e35b31527ae85ba09e540ca0a5` it failed once at the intended
  assertion: `validate_h6_record(cancelled, "NL_H6")` raised
  `SchemaMigrationError: H6 SanrentanHyo must be exactly 11 ASCII digits`
  (`1 failed`).
- The same test binds the positive and negative boundaries: physical eleven
  ASCII spaces become `SanrentanHyo=""` only for status 9; physical tabs are
  rejected; statuses 2/4/5 reject the canonical empty value; caller `None`,
  one space and eleven spaces are rejected; and successful native storage must
  retain the status/combination while writing SQL `NULL` for the numeric vote.
- Production now mirrors the reviewed H1 contract.  The physical parser
  compares the original eleven bytes before `strip()` can erase their class,
  and the caller validator permits the empty canonical form only when
  `DataKubun=9`.  No schema, identity, snapshot or transaction code changed.

Next safe action: run the paired green, the complete bounded H6 module and
strict docs/lint checks, then commit and publish one repair PR before rebuilding
the runtime image or repeating provider acquisition.

## Local verification before publication

- Python 3.13.5 paired regression after production change: `1 passed`.
- Complete H6 module without PostgreSQL opt-in: `159 passed, 13 skipped`.
- The same complete H6 module against a fresh disposable PostgreSQL 16:
  `168 passed, 4 skipped`.
- Independent PostgreSQL 16 storage probe for the new provider shape imported
  three expanded status-9 combinations with `records_imported=3`,
  `records_failed=0`; all three `SanrentanHyo` values were SQL `NULL`, the
  stored status remained `9`, and no transaction was pending on return.
- Adjacent H6 parser/expanded-storage selection:
  `21 passed, 4 skipped, 96 deselected`.
- Workflow-equivalent fatal flake8 selection returned zero findings;
  `mkdocs build --strict`, `python -m compileall`, and `git diff --check`
  succeeded.  Ruff's repository-wide pyupgrade/style debt is advisory in the
  current workflow and predates this four-file delta; it is not represented as
  a release gate.
- The dedicated PostgreSQL container, pytest/coverage/cache artifacts and
  strict-documentation output were removed.  No provider retry, runtime image
  rebuild or subsequent acquisition stage was started.

Next safe action: inspect the four-file diff and worktree hygiene, commit and
push once, create one draft PR with the red/green evidence, then obtain the
repository's single native review and exact-head CI/thread/clean gate.

## Native review closure

- Draft PR #243 was published at exact head
  `ff4d100d41f2efb02092825c9a64dbfb1a67e8db`.  Its initial test, lint and
  Windows syntax checks all passed.  After the draft was marked ready, the
  single requested GitHub-native Copilot review, Codex review and CodeRabbit
  review completed on that same SHA; no review thread was created.
- The review text nevertheless exposed two concrete unthreaded boundaries,
  which were reproduced before changing production:
  1. a fixed-width vote field containing a tab adjacent to ten digits was
     returned by `H6Parser.parse()` because only the all-whitespace result was
     compared with the raw bytes; and
  2. `RT_H6` was absent from `RealtimeUpdater.STRICT_RECORD_TABLES`, so a
     caller-built live status with `SanrentanHyo=""` returned `success=True`.
  The extended existing H6 tests on exact `ff4d100d...` produced **2 failed**:
  the mixed-whitespace parser assertion received three rows, and the realtime
  assertion observed `True is False`.  This is the red-first evidence for the
  review correction.  A caller tab already failed in `validate_h6_record`; it
  was added to the existing malformed set as direct coverage, with no new
  production exception.
- The parser now skips unregistered all-space combination slots, then requires
  every registered vote span to be exactly eleven ASCII digits or, only for
  status 9, exactly eleven ASCII spaces.  Realtime raw, parsed-record and batch
  routes now include `RT_H6` in the shared strict validator and strict schema
  verifier before coercion or DML.  Status-9 blank votes remain accepted and
  stored as SQL `NULL`.
- Paired parser/realtime review regression: **2 passed**.
- Complete SQLite H6 contract after the review correction:
  **159 passed, 13 skipped**.
- Complete H6 contract with a fresh disposable PostgreSQL 16:
  **168 passed, 4 skipped**.  The dedicated container was removed immediately
  after the run.

Additional bounded checks on the same review-correction content:

- Adjacent expanded H6 storage selection: **9 passed, 4 skipped, 56
  deselected**.
- `tests/test_realtime.py -k H6` selected no test and exited with pytest's
  no-tests-selected status, so it is deliberately not counted as evidence;
  the raw, single parsed-record and batch realtime paths are exercised in the
  H6 official-contract module above.
- Python 3.12 `compileall`: passed.
- Fatal-only flake8 selection (`E9,F63,F7,F82`): passed.
- Strict MkDocs build: passed.
- `git diff --check`: passed.

Next safe action: remove only the generated local test/docs artifacts, commit
the aggregated review correction, push it to PR #243, and perform the
exact-head CI/thread/clean gate without requesting another review.

## Outdated-thread audit after the first repair push

- The first aggregated correction was committed and pushed as
  `3010910ea54b149769c392df32edf8651fc8212e`.  Exact-head SQLite H6 was
  **159 passed, 13 skipped**; compileall, fatal-only flake8 and diff-check
  passed.
- The authoritative GraphQL thread audit then found one unresolved thread
  marked outdated.  Its location had moved, but the contract finding was
  still valid: a physical status-0 erase with a registered combination and a
  noncanonical vote span was rejected before erase even though every non-key
  status-0 byte is intentionally opaque.
- Red-first on exact production `3010910...`, after extending two existing H6
  tests only: **2 failed**.  Direct parser output was `None`, and the realtime
  erase result was `None`, leaving the seeded row at risk of remaining stale.
- The parser now builds a status-0 interpretation view that preserves the
  exact envelope and six-field race identity while masking bytes 27 through
  the byte before CRLF.  The central fixed-record/status gate therefore still
  validates the original type, status, MakeDate, race key, length and CRLF,
  while neither CP932 decoding nor body validation can suppress the keyed
  erase.  Live statuses continue to validate the complete physical body.
- Paired status-0 parser/realtime regression after repair: **2 passed**.
- Complete SQLite H6 contract after repair: **159 passed, 13 skipped**.
- Python 3.12 compileall, fatal-only flake8 and diff-check: passed.

Next safe action: commit and push this final thread correction, reply to and
resolve only the verified GraphQL thread, then perform one exact-head CI,
thread-zero and clean-worktree gate.  Do not request another automated review.

## Exact-head CI oracle correction

- The status-0 thread repair was pushed as
  `b5ce4b6ab9e98ad8b1be5cc9792d5ef8bc7cb3ad`; the verified GraphQL thread was
  replied to with its red/green evidence and resolved.
- Exact-head GitHub test job executed and failed (therefore it is not waived):
  **1 failed, 4,714 passed, 503 skipped, 14 deselected, 21 subtests passed**.
  The sole failure was the pre-existing generic
  `test_cancellation_status_is_upserted_for_realtime_state_records` subtest,
  which still classified H6 `DataKubun=0` as retained state and expected an
  insert.  The H6 official contract and implementation have long defined it
  as physical exact erase; strict H6 validation merely made the stale oracle
  observable.  This also explains why the earlier filename selection
  `tests/test_realtime.py -k H6` selected nothing: the H6 case was hidden under
  a generic unittest subtest name.
- Removed only H6 from that generic retained-state matrix.  The real-table H6
  official test remains the positive exact-erase oracle, including the newly
  added opaque physical-body case.  No production behavior changed for this
  CI correction.
- Corrected generic realtime unittest: **1 passed, 8 subtests passed**.
- Complete SQLite H6 contract remained **159 passed, 13 skipped**; fatal-only
  flake8 and diff-check passed.

Next safe action: commit/push once, and require the new exact-head CI plus
thread-zero/clean gate before merge.
