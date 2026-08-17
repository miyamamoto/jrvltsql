# WE official contract worklog

## Start state

- Started: 2026-08-18 JST
- Objective: audit and, only where primary evidence requires it, repair the
  current WE (weather/track-condition announcement) parser, native/standard/
  realtime storage, migration, metadata, tests, and public documentation.
- Minimal scope: WE only. JC and other remaining JV-Data formats stay in later
  independent iterations.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_we_official`
- Branch: `agent/we-official-contract-20260818`
- Base / starting HEAD / current `origin/master`:
  `2e7aa556ecb5cf6aa1ba190b2f22a2ed67c00a2a`
- Production release remains `v1.6.10`; the repository candidate remains the
  unreleased `2.0.0.dev0` compatibility series. No release or capability claim
  is made by starting this audit.
- Dependency order: complete and merge this JRA format iteration before the
  final jrvltsql release audit; only after jrvltsql is released may the planned
  jrvltsql-nar and jvlink-mcp-server propagation/release iterations start.

## Audit contract

- Primary evidence: pinned JV-Data 4.8.0.2 and 4.9.0.1 workbooks plus the
  tracked SDK 5.0 source manifest. Community reports may identify provider
  defects or transition behavior but cannot override the official field/key
  contract without corroboration.
- Check current physical length and every field span; official key and status
  domain; historical same-length or physical changes; parser/caller validation;
  native, standard, realtime, SQLite, PostgreSQL, and Dual storage; schema
  preflight; metadata; cancellation/ordering semantics; tests and docs.
- Any new or changed validator/gate must first be exercised by an observed red
  regression on unchanged production and retain a paired valid green case.
- STOP on source ambiguity, candidate drift, failed required test/readback,
  unsafe schema mutation, unresolved review thread, or any release action
  before the complete release gate.
- No 64-bit SDK support statement is permitted without a real 64-bit SDK
  acquisition and storage proof. This iteration does not attempt that proof.

## Initial state and next safe action

- Fresh worktree is clean and exactly matches the merged SE release-series
  head above. No implementation or test change has been made yet.
- Next safe action: independently derive the WE physical layout, key, statuses,
  and change history from the pinned official sources, then compare parser,
  schemas, importer/realtime paths, metadata, current tests, and public docs
  before designing one compact red-first repair.

## Read-only audit on the starting SHA

- Two independent Codex reviewers and the primary agent audited the unchanged
  starting SHA. Both reviewers ended on the same SHA with no production/test
  drift; the only worktree change remained this intentional worklog.
- JV-Data 4.8.0.2 and 4.9.0.1 `フォーマット` rows 1435-1458 and SDK
  5.0.0 `JV_WE_WEATHER` agree on one 42-byte physical record and the ordered
  key `(Year, MonthDay, JyoCD, Kaiji, Nichiji, HappyoTime, HenkoID)`.
- The current status is `1`. Historical status `0` is accepted only when
  `MakeDate < 20030711`; it is an exact-key delete command. The physical layout
  did not change at that boundary.
- Official code domains are `HenkoID in 1..3`, weather in `0..6`, and turf/dirt
  state in `0..4`. `HenkoID=2` requires the four track-state fields to be the
  initial value; `HenkoID=3` requires both weather fields to be the initial
  value. `HappyoTime=00000000` is a real initial-state sentinel.
- Official history also records format-number/description changes in 2004,
  2009, 2010, and 2011 without a physical span change. The 2006 snapshot note
  requires each new 0B14 response to replace the previous date snapshot; that
  transactional behavior is already implemented and is not a new finding.
- Community corroboration was used only for operational behavior, not as the
  format oracle. Developer-community topics 331, 164, and 141 show that the
  latest weather state is selected by `HappyoTime` and that one venue/date has
  an initial `00000000` row plus multiple later announcement times.

### Confirmed starting-SHA failures

- `NL_WE` and `RT_WE` omit `HappyoTime` from their primary key. Two otherwise
  identical announcements at different times report success but collapse to
  one durable row on SQLite and fresh PostgreSQL 16. `TENKO_BABA` has no key,
  so an exact reimport appends a duplicate instead.
- The same identity defect is present in realtime key resolution. Historical
  status `0` is not an official erase in either batch importer and becomes a
  tombstone/extra row; realtime erases every time sharing the incomplete
  six-part key.
- WE has no semantic validator. Invalid dates, venue codes, announcement times,
  `HenkoID`, and weather/track codes pass the parser and caller-dictionary
  entrypoints. Standard native/canonical body aliases can conflict silently.
- WE has no exact storage preflight. Wrong key types/nullability, additional
  UNIQUE constraints, keyless standard storage, and a deferrable PostgreSQL
  primary key are accepted until data is lost or DML fails. DualDatabase
  faithfully reproduces the same wrong outcome on both targets.
- Existing focused tests were green (`220 passed, 2 skipped, 10 subtests`) but
  one test explicitly fixed the incorrect six-part realtime key, the common
  announcement fixture used non-official track codes `5` and `6`, and no test
  checked coexistence, idempotency, exact erase, or unsafe schema rejection.

### Aggregated repair boundary

1. Bind one compact WE fixture/test module to both pinned workbook hashes, the
   SDK manifest, all 17 logical spans, the seven-part key, status/history, and
   code domains. Observe its negative cases failing on this exact starting SHA
   before implementation.
2. Add one shared WE key/body validator to parser, regular/optimized batch,
   single-record, and realtime boundaries. Historical status `0` validates
   only header and seven key fields; its body remains opaque.
3. Make native, standard, and realtime DDL use the same seven-part NOT NULL
   key. Add exact type/nullability/key/UNIQUE/PK-usability verification for
   SQLite, PostgreSQL, and every Dual target before mutation. Legacy six-key or
   keyless tables require operator backup/rebuild/reimport; they are not
   altered automatically.
4. Apply historical status `0` as a seven-key exact delete in provider order,
   update executable metadata and public migration guidance, and correct the
   old six-key/invalid-code tests.

- Next safe action: add the official fixture and compact regression module,
  run it against `2e7aa556ecb5cf6aa1ba190b2f22a2ed67c00a2a`, and record the
  observed red output before touching production implementation.

## Red-first contract evidence on the unchanged starting SHA

- Added one compact `tests/test_we_official_contract.py` contract rather than
  one test per reviewer hypothesis. It binds the pinned workbook hashes, SDK
  manifest, all 17 parser fields, ordered seven-part key, paired valid shapes,
  malformed raw/caller rows, identity/idempotency, historical exact erase,
  realtime erase, and one unsafe-schema negative.
- Command (locked Python 3.12 environment, external basetemp):
  `/home/keiba/work/jrvltsql/.venv/bin/python -m pytest
  tests/test_we_official_contract.py -q --no-cov
  --basetemp=/tmp/jrvltsql-we-red`
- Result on exact production SHA
  `2e7aa556ecb5cf6aa1ba190b2f22a2ed67c00a2a`: **33 failed, 9 passed**.
  Representative observed reds were the official-key assertion
  (`HenkoID` appeared where `HappyoTime` was required), every malformed key/body
  negative returning normally, caller alias conflicts not raising, native
  identities collapsing, standard identities duplicating, status-0 rows not
  being erased, realtime targeted erase retaining/wrongly targeting rows, and
  an extra UNIQUE constraint being accepted. The three paired official valid
  shapes stayed green.
- Before implementation, the test data was corrected so the leap-day positive
  uses year 2024, the alias negative is a real unequal conflict, and historical
  erase keeps the official `HenkoID` key while making only the six non-key body
  codes opaque. These corrections do not change the observed defect classes.
- Next safe action: implement the aggregated four-part repair once, then rerun
  this module plus the existing WE/happyo/status/schema focused suites.

## Implementation delegation

- Claude Code CLI version: `2.1.233`.
- Session ID: `d42d849e-102e-4b18-ac3e-c99794b4b6ce`; later corrections in
  this same WE iteration must use `--resume` rather than a fresh session.
- Model: `--model fable` (`claude-fable-5`). Fable was selected because the
  change is a fail-closed validator/schema gate whose correctness depends on
  ordering across parser, migrations, two batch importers, single-record and
  realtime mutation paths, SQLite/PostgreSQL/Dual behavior, and historical
  status-0 semantics. The cost of a partial repair is irreversible data loss.
- The implementation prompt supplies the observed red result, exact official
  contract, bounded file scope, status-0 opacity boundary, required existing
  focused tests, and prohibition on release/64-bit claims. Primary will inspect
  all resulting changes and owns the final test/review/merge decision.
- The first Fable invocation stopped before reading/editing production because
  Claude Code reported an expired OAuth session that it could not refresh.
  Exit code was 1; no implementation file changed. Per the release-readiness
  fallback and the user's prior instruction, primary Codex continues the same
  repair batch. The session ID above is retained for a possible authenticated
  `--resume`, but Claude is not counted as review or implementation evidence.

## Codex implementation batch

- Primary Codex implemented the aggregated repair without broadening the
  production scope beyond WE. The production changes are:
  - strict parser/caller validation for the complete seven-part key, current
    and date-bounded historical statuses, announcement time, venue and body
    domains, with status-0 body opacity;
  - seven-part `NOT NULL` primary keys for `NL_WE`, `RT_WE`, and `TENKO_BABA`;
  - exact column/type/nullability/key/extra-UNIQUE/primary-key-usability
    preflight for SQLite, PostgreSQL, and every Dual target;
  - historical status-0 exact erase in provider order for both batch
    importers, single-record import, and realtime;
  - executable metadata and public migration/rebuild guidance bound to the
    corrected DDL.
- Modified production/public files: `src/parser/we_parser.py`,
  `src/database/schema.py`, `src/database/schema_jravan.py`,
  `src/database/schema_metadata.py`, `src/importer/importer.py`,
  `src/importer/importer_optimized.py`, `src/realtime/updater.py`, and
  `docs/data_support.md`.
- The official fixture/test batch is
  `tests/fixtures/official_layout/we_contract_4901.json`, the fixture README,
  and `tests/test_we_official_contract.py`. Existing generic fixtures/tests
  were corrected only where they encoded a non-official WE shape/key.

## Green verification before candidate commit

- SQLite/Dual/affected focused suite:
  `199 passed, 18 skipped, 10 subtests passed`.
- Fresh disposable PostgreSQL 16 was used through the optional `psycopg`
  driver. The WE module passed `71 passed`; WE plus the announcement-time
  contract passed `94 passed`. The matrix covers native/standard, regular/
  optimized/single, owned/caller transactions, identity coexistence,
  idempotent revision, historical exact erase, realtime, wrong key type,
  extra UNIQUE, deferrable PK, and no-mutation failures.
- The broader status/layout/schema/metadata/distribution/public-contract set
  initially exposed one stale generic fixture: WE was incorrectly classified
  as accepting a blank body and generated `HappyoTime='01'`. After adding WE
  to the domain-payload-required set, the paired official WE fixture remains
  the positive oracle and the broader set passed `296 passed, 7 skipped`.
- The first full suite exposed three more uses of the same blank WE sample and
  one pre-existing SE performance sample with an incomplete/non-official key.
  Those test-only samples were changed to official-shape values; their focused
  reruns passed `292 passed` and `1 passed`, respectively. Installing the
  declared optional PostgreSQL test dependency removed two environment-only
  collection failures.
- Final full locked-environment suite:
  **`3037 passed, 212 skipped, 21 subtests passed`** in 64.18 seconds.
- `mkdocs build --strict` passed. The generated `site/` directory was moved to
  trash immediately and is not part of the worktree. Fatal workflow-equivalent
  flake8 reported `0`; `scripts/validate_test_gate.py` reported
  `TEST GATE PASS`; `git diff --check` passed. The new WE parser and contract
  test also pass their configured Ruff and Black checks. Existing advisory
  project-wide Ruff/Black debt was not mechanically rewritten into this PR.
- No release, deploy, SDK bitness, or provider capability claim is made by
  these tests. Actual fresh provider acquisition/storage remains a final
  release gate after all format iterations and documentation audit complete.

## Next safe action

- The disposable `jrvltsql-we-pg16` container used above was stopped; it had
  auto-remove enabled, and the exact-name `docker ps -a` filter is empty.
- Inspect the complete diff and worktree for generated/private content, then commit one
  immutable candidate SHA. Push/open one WE PR, request two complementary
  independent Codex critical reviews on that exact SHA, aggregate findings
  once, and do not merge until required checks, comments, thread count, and
  clean-worktree gates are green.
