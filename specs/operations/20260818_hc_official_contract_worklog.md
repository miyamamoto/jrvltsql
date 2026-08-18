# HC official contract worklog

## Iteration start (2026-08-18)

- Objective: audit and implement the complete current JRA-VAN `HC` hill-training
  contract against the pinned official 4.8.0.2/4.9.0.1 workbooks and SDK 5.0
  source/manifest, then prove parser, native/standard storage, exact identity,
  importer/realtime behavior, migration safety, documentation and distribution
  behavior on SQLite and fresh PostgreSQL.
- Minimum scope: `HC` only. Do not mix the remaining `TC` or `CC` record
  iterations, NAR implementation, MCP changes, release tagging, or any 64-bit
  support claim into this PR.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260818_jrvltsql_hc_official`.
- Branch: `agent/hc-official-contract-20260818`.
- Base/HEAD/origin master at start:
  `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a` (HS PR #212 squash merge).
- Published production release remains `v1.6.10`; source version is the
  unreleased `2.0.0.dev0`. This iteration does not publish either artifact.
- Dependency order: complete and merge this HC iteration first; start TC/CC
  only from the resulting latest master; run the final cumulative official-doc,
  real-provider-storage and release-document audit after all record iterations;
  only then release jrvltsql and proceed to jrvltsql-nar and jvlink-mcp-server.

## Initial risk and verification plan

- Existing reconstruction is only a 60-byte layout smoke. The initial audit
  must independently pin every physical span, current/historical status and
  key rule, unit/sentinel semantics, native `NL_HC`, standard `HANRO`, importer
  and realtime ownership, schema constraint/type/nullability behavior, and
  metadata/documentation claims.
- Before changing a parser/validator/schema gate, add one compact official
  negative contract and run it on this unchanged base to prove red; retain the
  paired provider-valid green. Do not add one test function per reviewer
  hypothesis.
- Test real durable rows rather than parser-only success: provider-order
  updates/deletes, two distinct official keys, same-key revision, both batch
  importers, single-record, auto-commit true/false, SQLite, fresh PostgreSQL and
  Dual orientation where relevant.
- Use Claude Code `--model fable` for the complex aggregated implementation if
  the CLI service is available; otherwise record the failure and use Codex with
  two independent critical reviews on one frozen candidate SHA. Reuse one
  Claude session for this worktree/iteration.
- STOP on official-source ambiguity that changes storage meaning, any
  provider-valid over-rejection, partial/silent field loss, wrong-key collapse,
  mutation-before-schema rejection, stats/durability divergence, transaction
  ownership leak, candidate drift during review, failed executed CI step,
  unresolved thread, or unsupported SDK/64-bit/release claim.

## Next safe action

1. Freeze start SHA and clean state, then extract the HC oracle from the pinned
   official sources without editing production.
2. Compare that oracle to parser/schema/mapping/importer/realtime/tests/docs and
   reproduce concrete gaps on SQLite.
3. Add one compact red-first HC contract, then implement one aggregated repair.

## Initial official-source audit (2026-08-18)

- The start identity remained exact: HEAD and `origin/master` were both
  `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a`; the only worktree change was
  this intentional worklog.
- Pinned primary artifacts were re-read from
  `/home/keiba/scratch/20260815_jvdata_official_materials`:
  - `JV-Data4802.xlsx` SHA-256
    `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`;
  - `JV-Data4901.xlsx` SHA-256
    `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`;
  - `JV-Data4901.pdf` SHA-256
    `b6c21aae4ccbba6a71c5e8065609c4fbb1ccee826c16e7d99ca6ecf7a4101522`.
- Both current workbooks define the same gap-free 60-byte HC record in
  `フォーマット` rows 1142-1167. The SDK 5.0 manifest independently binds
  `HC` to `JV_HC_HANRO`, width 60, with the same 15 logical fields and CRLF at
  bytes 59-60.
- The official ordered identity is
  `(TresenKubun, ChokyoDate, ChokyoTime, KettoNum)`. `DataKubun` is exactly
  `1` (initial value) or `0` (exact record deletion). The body owns seven
  fixed-width numeric timing fields; `0000`/`000` are documented measurement-
  failure values and their units are tenths of a second.
- `特記事項` rows 195-198 state that SLOP provides data from 2003 onward and
  that Miho used 600m measurement through 2004-11-29 and 800m from
  2004-11-30. This changes interpretation/availability, not physical size.
  The change history only records wording/unit additions (rows 170, 174 and
  344); no alternate HC physical layout is documented in the two pinned
  current workbooks or SDK manifest.
- `データ提供タイミング・提供単位` row 26 defines irregular daily delivery,
  one complete day/training-center unit, and one-year retention. HC is
  accumulated through SLOP, not an RT table in the current application.

## Claude availability and fallback

- The selected complex-task model was Claude Code `--model fable` (CLI
  2.1.233), because this iteration combines a validator, exact-delete order,
  cross-backend schema gates and migration safety. The audit-only launch used
  session id `8fd313d0-4bc7-4b46-9cb4-d03e4f4ea659` but failed before a usable
  session was created: the local OAuth session was expired and could not be
  refreshed. No repository mutation came from Claude and there is no usable
  session to resume.
- Per the user-approved fallback, Codex will implement only after red-first
  evidence, and at least two independent Codex reviewers will audit one frozen
  candidate SHA before PR/release action.

## Red-first contract evidence

- Added the compact reviewed fixture
  `tests/fixtures/official_layout/hc_contract_4901.json` and one grouped
  `tests/test_hc_official_contract.py` contract. It binds both pinned workbook
  hashes, every physical byte span, SDK 5.0 manifest structure, current status
  set, exact four-column identity, parser/caller validation, native/standard
  storage, provider order, exact delete, schema fail-closed behavior and the
  optional actual-PostgreSQL route.
- On unchanged production base
  `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a`, the paired provider-valid
  layout/parser oracle passed while the gate failed as intended:
  `31 failed, 1 passed, 1 skipped`. The failures independently cover invalid
  dates/time/key/timing acceptance, status-0 whole-body decoding, keyless
  standard storage, nullable/unsafe schemas, tombstone rather than exact
  deletion, caller coercion before validation, and all batch/single entry
  points. This is the required evidence that the new contract can say no;
  production implementation had not been changed when it was recorded.

## Next safe action

1. Apply one aggregated HC repair to parser, both executable schemas, metadata,
   both batch importers, single-record import, exact-delete routing and strict
   schema preflight.
2. Run the compact SQLite contract, adjacent parser/importer/schema suites and
   a fresh disposable PostgreSQL contract on the resulting candidate.
3. Freeze one full SHA, then collect independent official-oracle,
   data-integrity and release/package reviews before any PR or merge action.

## Aggregated implementation and local evidence

- Implemented the repair as one batch rather than iterating per finding:
  - `HCParser` now binds all official spans, validates real dates/HHMM,
    training-center/key domains and every fixed numeric timing field. Status 0
    decodes only its exact key and keeps the non-key body opaque by documented
    project policy.
  - `NL_HC` and standard `HANRO` now have complete required columns, exact
    four-part primary keys and lossless numeric capacities. Metadata is derived
    from the executable native schema.
  - both batch importers and `DataImporter.import_single_record` share the HC
    validator, strict schema verifier and exact-delete route. Standard `HANRO`
    is non-additive; nullable/keyless/wrong-key/wrong-type and unapproved
    UNIQUE/CHECK/FK constraints stop before mutation on every migration target.
  - provider-operation statistics preserve same-key update/delete order on
    SQLite and PostgreSQL; HC remains accumulated-only with no `RT_HC` claim.
  - public support/release documents now state the official identity, units,
    migration/reimport boundary and unverified realtime/non-applicable scope.
- A later extension of the same strict-schema gate was independently replayed
  on unchanged base `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a` before it
  was accepted: both native/standard extra-CHECK cases failed because the base
  reached DML instead of raising `SchemaMigrationError`, and the Dual unsafe-
  primary case failed because the base accepted and wrote it. The candidate
  rejects all three before mutation. This supplements the initial grouped
  `31 failed` red evidence and proves the new constraint/target census can fail.
- Current candidate validation so far:
  - compact SQLite HC contract: `35 passed, 1 PostgreSQL opt-in skipped`;
  - adjacent parser/status/importer/schema set: `404 passed, 1 skipped`;
  - metadata/schema/index set: `96 passed, 8 skipped`;
  - fresh PostgreSQL 16 compact contract with native/standard, both importers,
    auto-commit true/false, provider-order readback and schema negatives:
    `36 passed`;
  - test-gate validator: `TEST GATE PASS`; fatal flake8 selection: `0`;
    compileall and `uv lock --check`: pass.
- The required one-time broad regression run initially exposed three generic
  parser positives that still supplied a blank HC body. Those tests were based
  on the old permissive parser rather than the official format, so their HC
  sample was corrected to include the four-part identity and all seven fixed
  timing spans. The targeted three cases then passed, and the complete local
  workflow-equivalent suite finished `3314 passed, 333 skipped, 14 deselected,
  20 subtests passed`.
- Final post-format focused aggregate finished `602 passed, 8 skipped`; fatal
  flake8 remained `0`, `TEST GATE PASS`, `uv lock --check` passed, and
  `git diff --check` was clean.
- A fresh PEP 517 wheel and sdist built as unreleased `2.0.0.dev0`; the actual
  distribution content gate passed both artifacts and the installed-wheel init
  smoke passed. The artifacts and local build metadata were removed afterward.
- The disposable PostgreSQL container was removed after the run. No provider,
  production, GitHub, NAR, MCP or release state was changed.

## Next safe action

1. Run the one justified broad local suite because central importer/schema
   dispatch changed, then strict documentation and distribution build gates.
2. Commit/push one clean candidate SHA and freeze it.
3. Run the three independent read-only Codex reviews in parallel against that
   exact SHA, aggregate all concrete findings once, and only then decide the
   repair/PR boundary.
