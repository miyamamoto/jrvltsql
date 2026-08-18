# CC official contract iteration worklog

## Start state (2026-08-18)

- Objective: bind the JRA `CC` course-change record to the pinned official
  physical layout, current status/key/body domains, native/standard/realtime
  storage, exact schema preflight, provider ordering, and transaction safety.
- Minimal scope: `CC` only. Do not fold unrelated HC/HS/TC cleanup or later
  record formats into this iteration.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_cc_official`.
- Branch: `agent/cc-official-contract-20260818`.
- Base and starting HEAD: `6e9a9f500f2353d7b423e5f1e12b07c30275f8d1`
  (`origin/master`, TC PR #214 squash merge).
- Package version: `2.0.0.dev0`; latest published release remains `v1.6.10`.
  This iteration is not itself a release or production-adoption claim.
- Dependency order: TC is merged; CC is the next independent official-contract
  iteration and must be merged before another record format begins.
- Working tree was clean at creation.

## Planned contract and evidence

1. Re-derive the CC byte spans, total length, ordered key, current status,
   history, code domains, and 0B14/0B16 delivery behavior from pinned JV-Data
   4.8/4.9 workbooks plus SDK 5 source/manifest before production edits.
2. Extend or add one compact official-contract test module. Every new or
   changed parser/validator/schema gate must first be red on this exact base,
   with paired provider-valid green cases.
3. Cover direct/factory parsing; caller aliases; native `NL_CC`; standard
   `COURSE_CHANGE`; `RT_CC`; both batch importers; single-record import;
   realtime single/batch; SQLite, fresh PostgreSQL, Dual orientation,
   caller-owned transactions, provider-order replacement, and fail-before-
   mutation migration.
4. Update executable metadata, public support/migration documentation, release
   notes/changelog, and this worklog only where required by proven CC facts.
5. Freeze one full candidate SHA, aggregate independent official-oracle and
   critical reviews, apply at most one consolidated repair batch, then run
   focused/workflow/package gates before one PR and merge.

## Coding-agent choice

- This is complex fail-closed parser/schema/migration work, so the planned
  Claude Code model is `--model fable`, session id
  `839154eb-0967-4b4d-87e4-785f2dfdce64`. The same session will be resumed for
  review repairs. If authentication/quota blocks it, record the failure and use
  Codex implementation plus independent critical reviews rather than silently
  weakening the gate.

### Claude execution result

- Claude Code `2.1.233` was invoked after the start-worklog commit with
  `--model fable` and session id
  `839154eb-0967-4b4d-87e4-785f2dfdce64`. It exited before reading or editing
  the repository because the OAuth session was expired and could not be
  refreshed. The CLI also emitted non-fatal warnings about obsolete `Write`
  permission-rule spellings in the parent settings. No Claude implementation
  or review evidence exists for this iteration. Codex will implement the
  bounded contract with independent official-oracle and critical review as the
  recorded fallback.

## Known preliminary risks (not yet official findings)

- `CCParser` declares `RECORD_LENGTH=50` while its docstring says 48 bytes and
  it does not expose the terminal CRLF field.
- Current parser has no CC-specific key/body validator. Native/realtime schemas
  are nullable, while standard `COURSE_CHANGE` is keyless and nullable.
- Existing status-domain work already restricts current CC to status `1`, but
  all parser/caller/schema boundaries and code domains still require an
  independent official audit.

## Official oracle and red-first evidence

- Pinned JV-Data 4.8.0.2 and 4.9.0.1 `フォーマット` rows 1531–1553 and
  SDK 5 `JV_CC_INFO` agree on a 50-byte layout with 16 spans including CRLF,
  current status `1`, and ordered key
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`.
- The current track-code domain is `00`, `10`–`29`, and `51`–`59`; the reason
  domain is initial `0` plus `1`–`4`. Distances retain exactly four ASCII
  digits including `0000`; `HappyoTime` accepts `00000000` or a real
  `MMDDhhmm` value.
- CC was added on 2004-05-25 in Ver.1.1.6. No later physical-layout change was
  found. `0B14` is the date-snapshot source and `0B16` is event-oriented.
- Before production edits, added
  `tests/fixtures/official_layout/cc_contract_4901.json` and one grouped
  `tests/test_cc_official_contract.py` covering the physical oracle, strict
  negatives/initial sentinels, native/standard identity, schema negatives,
  both batch importers, single import, realtime, snapshot replacement, and
  header aliases.
- Red command on unchanged production HEAD
  `da1da38e46ffcda90254108a737820a9b8867015`:
  `python -m pytest -q -o addopts='' tests/test_cc_official_contract.py`.
  Result: `51 failed, 7 passed`. Failures include the missing delimiter span,
  15 malformed raw cases being accepted, nullable/keyless or unsafe schemas,
  standard revision duplication, caller/single/realtime invalid-body
  acceptance, and schema-manager fail-open. Passing controls include official
  initial sentinels, current header aliases, native provider replacement, and
  the existing CC date-snapshot behavior.
- Before production edits, the grouped schema contract was extended with
  generated/required-column and Dual-orientation negatives plus opt-in
  PostgreSQL deferrable/generated/UNIQUE and provider-operation-count cases.
  The unchanged production result became `57 failed, 7 passed, 5 skipped`;
  both Dual unsafe orientations failed to stop before mutation. PostgreSQL
  cases were intentionally skipped in this local red run and are to be run
  against a fresh PostgreSQL instance after implementation.
- Three independent read-only reviewers audited the committed pre-production
  HEAD. Two completed before the intentional red files appeared and one was
  told those files were primary-owned. Their non-duplicated findings match the
  red contract: strict parser/caller/realtime validation, exact three-table
  storage/preflight, and a CC-specific durable 0B14 assertion are required.

## Implementation and local validation

- Implemented one bounded CC repair after the grouped red run:
  - `CCParser` now binds all 16 official spans, including CRLF, and validates
    the six-part identity, real dates and announcement time, exact distance
    widths, official venue/track domains, and reason domain before returning a
    parsed row;
  - native `NL_CC`/`RT_CC` and standard `COURSE_CHANGE` now expose the same
    complete required payload and exact ordered primary key;
  - both batch importers, single-record import, realtime dict entry points,
    SchemaManager, standard preflight, metadata, and provider-operation
    counting share the CC validator and strict schema verifier;
  - the verifier rejects missing/extra/generated/identity columns, wrong
    affinities/capacities/nullability, wrong/deferrable PostgreSQL keys, and
    unapproved UNIQUE/FK/CHECK constraints on every Dual migration target;
  - public support, migration and release documents now state the current-only
    status-1 contract and distinguish 0B14 snapshot replacement from 0B16
    event updates.
- Fresh SQLite compact contract after implementation: `64 passed, 5 skipped`.
- Fresh disposable PostgreSQL 16 compact contract, including native/standard
  same-key provider ordering, unsafe schema rejection, first-invalid realtime
  transaction state, and mixed SQLite/PostgreSQL Dual orientations:
  `77 passed`.
- The adjacent affected aggregate (`CC`, announcement-time, realtime,
  migration, schema/index, importer and prior `TC` contract) passed
  `295 passed, 56 skipped, 9 subtests passed` under Python 3.13.5.
- The first workflow-equivalent broad run on exact committed candidate
  `686f6018f8f83f7e102fb55d1fb2f539514e9a43` finished `3448 passed,
  386 skipped, 14 deselected, 20 subtests passed` with four CC failures.
  All four were the same pre-existing false-positive fixture class: generic
  parser tests supplied an all-blank CC key/body and expected it to be valid.
  The strict parser was not weakened. `CC` was added to the generic envelope's
  domain-payload-required set and the shared parser sample now supplies one
  complete official-valid CC row. The exact affected selection then passed
  `152 passed`; the candidate-wide suite must be rerun after this test-only
  repair.
- `scripts/validate_test_gate.py` reported `TEST GATE PASS`; workflow-fatal
  flake8 (`E9,F63,F7,F82`) reported zero; `uv lock --check`, compileall,
  strict MkDocs, import-order lint for newly touched imports, and
  `git diff --check` passed. Generic project-wide Ruff debt was not formatted
  or mixed into this scoped change.
- The disposable PostgreSQL container remains intentionally running only until
  the exact committed candidate and final bounded reviews are complete. No
  provider, production, GitHub, release-lock, KPS data, or model state was
  changed.

## Frozen-candidate reviews and one repair batch

- The first frozen review candidate was
  `7dffe3b1c6fea6099e0c57715f0f1f86a229f3d1`, with base
  `6e9a9f500f2353d7b423e5f1e12b07c30275f8d1` and a clean worktree.
  Three independent read-only reviews were aggregated before any repair:
  - the database reviewer found that caller-built integer distances were
    accepted but stored to standard `COURSE_CHANGE` as `"0"`/`"12"` rather
    than the lossless official four-character `"0000"`/`"0012"` form;
  - the same reviewer found that failed public `SchemaManager.create_table`
    and `create_all_tables` CC preflights could leave a PostgreSQL catalog-read
    transaction pending because ownership was sampled after the first read;
  - the official-oracle reviewer demonstrated that forged workbook/SDK source
    fields, code domains, history fields, and `JV_CC_INFO` spans were not
    truth-bound by the initial oracle test, and also identified the wrong
    Unicode separator in the recorded timing-sheet locator;
  - the release reviewer found no code or package blocker, but correctly
    rejected the stale worklog as incomplete release provenance. Its parser
    offset, code-domain, schema fail-open, provider-count, stale-snapshot, and
    routing mutants all made the corresponding tests fail.
- Red-first follow-up was committed as
  `a5a47249edde6afbacb643e47c4c0052be07d273`. On the unrepaired production
  candidate, the grouped review regressions produced five failures: one exact
  official-locator/oracle failure, two importer distance-normalization
  failures, and two PostgreSQL SchemaManager transaction-closure failures.
  Provider-valid controls remained green.
- One consolidated repair was committed as
  `6caa56b9d39bbb5c6cb27b634f82fc5000ecb2f3`:
  - standard CC translation formats accepted integer distances to exactly four
    digits after shared validation;
  - strict SchemaManager preflight snapshots ownership before every catalog
    read and closes only a transaction created by the failing call;
  - the compact oracle now binds both workbook sources and hashes, SDK source
    and hash, every `JV_CC_INFO` field span, exact track/reason domains,
    history/provider facts, and the real U+FF65 worksheet separator.
  All five previously red review regressions passed after this repair.

## Final local evidence before publication

- Compact CC contract on SQLite: `66 passed, 15 skipped`.
- Compact CC contract against the fresh disposable PostgreSQL 16 instance:
  `81 passed`.
- Workflow-equivalent suite on exact
  `6caa56b9d39bbb5c6cb27b634f82fc5000ecb2f3`: `3454 passed, 388 skipped,
  14 deselected, 20 subtests passed`.
- Python 3.12 affected suite on the same production/test tree: `715 passed,
  58 skipped, 9 subtests passed`.
- Workflow-fatal flake8 (`E9,F63,F7,F82`) returned `0`; the repository test
  gate reported `TEST GATE PASS`; `uv lock --check`, strict MkDocs, and
  `git diff --check` passed.
- A git-archive-derived wheel and sdist for `2.0.0.dev0` built successfully.
  The official distribution-content gate passed for both artifacts, and the
  isolated wheel initialization smoke passed. No `specs/` worklog is included
  in the distributable artifacts.
- No provider, production, GitHub, release-lock, KPS data, or model state was
  changed by these local validations. The PostgreSQL instance is disposable
  and will be removed after the final carry-forward review.

## Next safe command and STOP conditions

- Next: commit this final evidence update, freeze the resulting clean full SHA,
  run one bounded carry-forward review of the consolidated repair/provenance,
  then push one branch, open one PR, request the single native Copilot review,
  address actionable comments in one batch, require unresolved thread count
  zero, and merge only after the applicable checks and exact-head evidence are
  green.
- STOP on non-worklog drift, a material disagreement among pinned official
  sources, backend divergence that is not explained and tested, or any need
  for destructive/provider action beyond the authorized local test scope.
- Credentials, provider identifiers, and connection strings must not be
  written to this worklog.
