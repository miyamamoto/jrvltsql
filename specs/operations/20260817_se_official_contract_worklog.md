# SE official parser and storage contract worklog

## Iteration identity

- Started: 2026-08-17 JST.
- Objective: bind the SE horse-per-race record to the pinned current and
  historical official layouts and preserve every distinct official identity
  through native and JRA-VAN-standard storage.
- Minimum scope: SE official/history oracle, parser field/byte contract,
  native and standard column/key/readback, cancellation behavior, fail-closed
  migration, focused SQLite/PostgreSQL/Dual tests, and directly affected docs.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260817_jrvltsql_se_official`.
- Branch: `agent/se-official-contract-20260817`.
- Base / initial HEAD / `origin/master` full SHA:
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`.
- Production/release context: repository version `2.0.0.dev0`; no 2.0 release
  exists and this iteration does not authorize a release.
- Dependency: PR #206 merged as
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`, closing executable MCP
  metadata coverage without changing the underlying SE schema.
- Implementer/reviewer policy: Codex with two independent critical Codex
  reviews for a frozen high-risk candidate. Claude Code is unavailable and is
  not counted. No model switch or external reviewer session has occurred.

## Initial observed risk

- Current native documentation and DDL use a seven-column SE key ending in
  `Umaban`; the prior official-workbook audit identified `KettoNum` as an
  additional official SE key field. If confirmed against the pinned sources,
  two provider records that differ only by that field can collapse under
  replacement/upsert semantics while import statistics still report success.
- SE has no dedicated current-layout worklog comparable to RA, and earlier
  schema/parser validation reported SE among the remaining mismatches. No
  assumption is made yet about which parser/storage fields are complete.
- The first action is read-only: derive the current and historical contract
  from pinned official artifacts, compare every parser field and both schemas,
  then reproduce concrete loss before writing a repair test or production code.

## Test and review contract

- Any new or changed key/layout/schema validator must first be shown to fail
  on unchanged production, with a paired canonical positive.
- Reviewer hypotheses will be collected and deduplicated before one repair
  batch. No per-finding SHA/review loop.
- Actual SQLite and fresh disposable PostgreSQL are required for key collision,
  update, cancellation, old-schema no-mutation, and readback. Dual must prove
  both target orientations or document a bounded reason when one is not
  applicable.
- Existing 1.x/wrong-key tables are not silently rewritten. If lossless
  migration cannot be proved, import must stop before schema or row mutation
  and operator backup/recreate/reimport guidance must be documented.

## Next safe command

Locate the pinned 4.8.0.2/4.9.0.1 workbook rows and SDK 5.0 manifest/source for
SE, derive length/field/key/status/history facts independently, then inspect
`SEParser`, `NL_SE`/`RT_SE`, the standard owner, importer mappings, validators,
and existing tests. Record observations before adding red tests.

## Read-only audit result on the unchanged production tree

- Audited HEAD: `1c6226a77dfd9859e218c4878cd7587965ce6f79`.
  Its production tree is identical to base
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`; the only commit delta is this
  worklog.
- Two independent Codex critical reviews completed against that exact clean
  SHA. Claude Code was unavailable and was not counted. Both reviewers
  independently reproduced the official-key and standard-field loss before
  seeing a repair.
- Pinned JV-Data 4.8.0.2 and 4.9.0.1 agree on the current 555-byte physical
  layout. SDK 5.0.0 names the root `JV_SE_RACE_UMA`; all 74 parser slices
  (76 expanded SDK leaves after flattening nested IDs) match byte-for-byte.
- The official ordered key is `(Year, MonthDay, JyoCD, Kaiji, Nichiji,
  RaceNum, Umaban, KettoNum)`. Native `NL_SE`/`RT_SE`, erase routing, and
  realtime routing omit `KettoNum`; standard `UMA_RACE` has no primary key.
- Independent SQLite and fresh PostgreSQL 16 probes proved that two rows with
  the same first seven values and different `KettoNum` collapse to one native
  row while import reports success. Standard storage retains duplicates on a
  repeated full revision and its seven-column erase predicate deletes both
  different horses. Dual can retain different winners on its two backends
  while reporting in-sync when an additional unique constraint is present.
- Caller-built blank/alphanumeric/over-width `KettoNum` and malformed
  alphanumeric `Year` values pass the current boundary; the latter are silently
  coerced to an unrelated integer. Wrong key types, extra unique constraints, and a PostgreSQL
  deferrable primary key are not rejected as schema incompatibilities.
- Parser/native names `Reserved_229`, `Reserved_296`, `Reserved_382`, and
  `Reserved_385` have no aliases to standard `reserved1` through `reserved4`.
  Both importers report success while all four standard columns become NULL.
- The generic scale table incorrectly divides official integer-kilogram
  `BaTaijyu` and `ZogenSa` by ten in native storage. SQLite stored 508kg/+3kg
  as 50.8/0.3 while canonical columns correctly retained 508/3.
- JV-Data 4.9.0.1 row 196 marks `Honsyokin` as set for status 7 and A, so A
  zero means zero yen. Row 197 marks A `Fukasyokin` as initial, so only the
  existing Honsyokin rule is wrong; the first reviewer reading was challenged
  and corrected against columns 12-21 before implementation.
- The reconstructed 463-byte SE fixture is a repository smoke artifact, not
  an official physical oracle. `make_se_record()` also uses NUL padding and
  therefore creates rows that SQLite accepts but PostgreSQL text rejects.

## Historical and community decision

- Change-history row 331 records that Ver.1.0.1 beta added `DMGosaP` and
  `DMGosaM` (four bytes each) on 2003-04-22, changing 547 to 555 bytes. The
  pinned material does not include the old complete field table or its old
  initial-value rules, so deriving and accepting a 547-byte grammar would be
  inference rather than an official parser contract.
- Current-normalized setup remains the supported ingestion boundary: keep the
  explicit 547-byte rejection and pair it with a 555-byte positive. Do not
  claim that arbitrary pre-normalization raw archives are supported.
- JRA-VAN community topic 61 confirms that actual A/B SE values caused the
  availability table to be corrected on 2024-08-07. Topic 88 records a
  provider SE body-value defect, so availability cells are not promoted into
  an over-strict body validator. Topic 215 confirms, for the 2023 data-spec
  transition, that new setup returns the new layout for older dates and old/new
  datasets must not be mixed; it is supporting context, not direct proof of
  the 2003 layout.

## Aggregated repair and red-first boundary

One repair batch will:

1. define one ordered eight-column SE key and use it in both native schemas,
   `UMA_RACE`, erase, completeness, and realtime paths;
2. add shared record/schema validation before coercion or mutation, including
   exact fixed-width key values, integral key storage, exact ordered PK,
   additional UNIQUE/exclusion rejection, and usable non-deferrable PG PK;
3. reject legacy seven-column/keyless tables with backup/recreate/RACE-reimport
   guidance rather than silently altering them;
4. preserve and conflict-check all four standard reserved aliases;
5. correct native body-weight/change units and status-A Honsyokin zero without
   changing A Fukasyokin semantics;
6. replace the NUL-padded test factory with official space padding and bind
   the current parser spans/history to the pinned oracle.

Before production changes, a compact parameterized regression will be run on
this unchanged production tree. It must fail for key coexistence/targeted
erase, malformed key, wrong schema/constraint, standard reserved readback,
native units, status-A Honsyokin zero, and NUL-free fixture, while retaining
paired current-layout/status-9/current-body positives. The exact failure
summary will be appended before the repair is applied.

### Observed red before implementation

- Command (Python 3.12 locked environment):
  `PYTHONPATH=. .../.venv/bin/python -m pytest
  tests/test_se_official_contract.py -q --disable-warnings --maxfail=30
  --basetemp=/home/keiba/scratch/20260817_jrvltsql_se_red --no-cov`.
- Result on unchanged production code: **18 failed, 1 passed**.
- Representative observed failures, not expected-only assertions:
  - fixture contained NUL bytes;
  - schema key tuple lacked `KettoNum`;
  - both native importers retained one of two official identities;
  - seven-column erase removed both rows from a manually correct eight-key
    table;
  - keyless standard storage retained three rows after one revision;
  - all seven malformed-key cases failed to raise;
  - wrong key type and extra UNIQUE both accepted and inserted;
  - realtime exact erase removed both rows;
  - native `BaTaijyu` was 50.8 instead of 508.
- The paired canonical/status-9/B2-initial header test was the one green test,
  proving the new negative suite did not merely reject every SE row.
- No production implementation had been modified when this red was recorded.

## STOP conditions

- Stop on candidate/worktree drift outside this iteration.
- Do not infer key membership, legacy support, cancellation semantics, or a
  standard owner from naming alone; require pinned official or executable
  evidence.
- Do not mutate a real provider database, publish a provider/x64 claim, push,
  merge, tag, or release during the audit/red-first phase.

## Implemented repair batch

- Native `NL_SE`/`RT_SE` and standard `UMA_RACE` now use the ordered official
  eight-column key ending in `KettoNum`; all key columns are explicitly
  `NOT NULL`. Historical and realtime erase routing uses that same tuple.
- `SEParser` and caller-built import records now require exact-width ASCII key
  fields, real MakeDate/race dates, and a JyoCD from official code table 2001
  before numeric coercion or mutation.
- A shared schema gate now checks exact key/type/nullability, rejects additional
  replacement keys and PostgreSQL deferrable primary keys, and verifies every
  Dual target. Legacy seven-column/keyless tables stop before any additive
  migration.
- Standard storage preserves and conflict-checks `Reserved_229/296/382/385` as
  `reserved1/2/3/4`. Native body weight and signed weight change remain integer
  kilograms, and status-A Honsyokin zero is preserved as zero yen while status-A
  Fukasyokin zero remains NULL.
- The SE fixture now uses provider-shaped space padding rather than NUL bytes.
  The official regression expands the pinned SDK manifest and compares every
  parser slice, in order, while proving every byte 1 through 555 is covered
  exactly once.

### Additional observed red for the pre-mutation gate

- After the first repair implementation but before the standard nullability
  preflight was added, the existing unrelated-migration regression was extended
  with an exact eight-column `UMA_RACE` whose `KettoNum` was nullable.
- Exact observed result: `1 failed, 1 passed`; the nullable case raised no
  `SchemaMigrationError` and the log showed `Adding missing column to RACE:
  YoubiCD`. This proved the initial preflight could still say green after an
  unsafe key and mutate an unrelated table.
- Adding the same key-nullability check to the non-mutating standard preflight
  changed that focused result to `2 passed`. The paired legacy seven-column
  case stayed green.

## Current local evidence before candidate freeze

- SQLite/current official contract: `27 passed, 15 skipped` before the added
  nullable-preflight parameter; the added two-case preflight regression passes.
- Directly affected SQLite suite: `163 passed, 15 skipped, 10 subtests passed`.
- Fresh disposable PostgreSQL 16, with the actual psycopg path: `42 passed`.
  This covers native/standard, DataImporter/OptimizedDataImporter/single,
  importer-owned/caller-owned transactions, coexist/update/exact erase,
  reserved-field and unit readback, plus wrong type/extra unique/deferrable-PK
  negatives.
- Workflow self-check prints `TEST GATE PASS`; fatal flake8 reports `0`;
  `uv lock --check` and `git diff --check` pass.
- The PostgreSQL container and test environment remain disposable and will be
  removed after the final exact-SHA review. No provider/x64/release claim is
  made by this evidence.

## Next safe command after this update

Run the broader official-oracle/current-layout/metadata/schema regressions and
the full non-live test gate. Then build and inspect fresh wheel/sdist, run strict
docs, update this worklog with exact results, commit a clean candidate, and ask
the two independent Codex reviewers for one aggregated exact-SHA review each.

## Pre-freeze comprehensive evidence

- Official oracle/current-layout/all-schema/metadata/migration selection:
  `232 passed, 7 skipped`. One first run exposed a stale generic test that
  treated a space-filled SE key as a valid record; SE is now classified with
  the other formats whose positive payload comes from a dedicated official
  fixture. The dedicated SE oracle remains the positive source of truth.
- The first coverage-enabled non-live full suite exposed ten stale expectations:
  incomplete SE parser samples, numeric/coerced caller keys, the former
  divide-by-ten body-weight expectation, and one prohibited infrastructure
  token embedded inside an example malformed value in this worklog. The tests
  were changed to provider-width SE fixtures and the worklog example was made
  generic; the exact last-failed selection then passed `10 passed`.
- After those corrections, the complete Actions-equivalent non-live suite on
  Python 3.12.11 passed:
  `2948 passed, 184 skipped, 14 deselected, 21 subtests passed`; total coverage
  was 77 percent. No warning was suppressed.
- Fresh PEP 517 wheel and sdist built successfully. The distribution content
  gate passed for both artifacts, installed-wheel init smoke passed, `specs/`
  remained excluded, and strict MkDocs completed successfully.
- A missing negative for standard reserved aliases was found during manual
  coverage review. The exact regression was replayed in a temporary detached
  worktree at production parent
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`: it failed with
  `DID NOT RAISE SchemaMigrationError` and stored one conflicting row. The
  repaired tree passed the same test and retained the existing standard
  readback positive. The temporary worktree was removed.
- A PostgreSQL realtime proof was added after the full-suite run. Latest fresh
  PostgreSQL 16 SE contract result is `44 passed`: two rows sharing the first
  seven key parts coexist, and status-0 removes only the selected `KettoNum`.

## Candidate-freeze boundary

No additional implementation change is planned before freeze. Re-run the
fatal syntax/undefined-name lint, test-gate self-check, lock/diff gates, commit
the complete iteration, then execute the focused and full gates against that
exact clean SHA. Only after those pass should the two independent critical
reviews start; reviewer edits are prohibited until both findings are
aggregated.

## Exact-candidate critical review and one repair batch

- Frozen reviewed candidate:
  `6f4a6a31567c574c78b08cdde0a3125670454d9d`; both independent Codex
  reviewers started and ended on that exact clean SHA. Both returned
  `NEEDS_CHANGES`; no reviewer edited the worktree and no Claude result was
  counted.
- The findings were deduplicated before implementation. The actionable repair
  groups were: preflight every single-table native migration against existing
  SE storage; validate every present SE column type/capacity/nullability;
  validate caller-built CP932 body widths and standard alias conflicts before
  schema migration; allow Dual to create a missing SE table only after each
  existing target is verified; make row-fallback statistics match committed
  rows; and separate the official workbook prize evidence from the narrower
  community A/B background citation.
- The body validator remains deliberately narrow: non-delete caller values
  must be strict CP932 and no wider than their official physical spans, but it
  does not invent availability/value-domain rules from provider defects.
  Status 0 remains an exact-key command with an opaque body.

### Observed red before the review repair

- With only the compact existing test extended and production code unchanged,
  the SQLite SE contract produced **18 failed, 28 passed, 20 skipped**.
  Concrete failures included accepted wrong body type/extra `NOT NULL`, an
  alias conflict after `RACE.YoubiCD` had already been added, all six malformed
  CP932/width cases passing, unrelated `NL_RA` migration despite unsafe
  `NL_SE`, four Dual missing-target false negatives, and
  `records_imported=1` with zero durable rows after row fallback.
- Fresh PostgreSQL 16 on the same unchanged implementation produced **4
  failed** for the added boundary selection: DataImporter batch,
  OptimizedDataImporter batch, and single-record Dual imports all treated an
  over-width standard reservation as success while only SQLite retained it;
  the normal DataImporter again reported one success while PostgreSQL retained
  zero rows after a later trigger rejection.
- These are observed failures, not expected-only assertions. Existing
  canonical current-layout and status-0 positives remained green in the same
  run.

### Implemented review repair

- `SEParser.validate_current_fields()` now validates every present non-delete
  physical body value as strict CP932 within its official byte span. The
  standard aliases are conflict-checked and projected back to their provider
  names before the same validator runs.
- Both batch importers validate the first fully resolved SE target before
  standard schema preflight; single-record import does the same before opening
  or joining a transaction. This prevents the first invalid SE body/alias from
  causing unrelated additive DDL.
- SE schema verification now checks every present column's logical type,
  lossless capacity, and exact nullability. Safe widening is limited to
  unbounded text, sufficient text/numeric capacity, and wider integral types;
  unrelated type families and extra `NOT NULL` constraints fail closed.
- `SchemaManager.create_table()` performs existing-SE preflight before every
  known native table migration. On Dual, only targets where the SE table
  already exists are verified; a missing counterpart can then be created by
  the normal mirrored `CREATE TABLE IF NOT EXISTS` path.
- Normal DataImporter row fallback commits each successful retry before
  incrementing its success count. A later rejected row can no longer roll back
  a row already counted as imported.
- The public documentation now attributes status-A prize-zero behavior to the
  workbook rows that define it and limits the community link to the separate
  A/B availability-correction background it actually supports.

### Repair checks completed so far

- SQLite SE contract: **46 passed, 20 skipped**.
- Fresh PostgreSQL 16 SE contract: **66 passed**.
- A first broader affected run exposed one old simulated SE row with a
  two-character one-byte `Wakuban` and three migration tests using safe widened
  SQLite key affinities. The simulated row was corrected to provider width;
  the schema verifier was narrowed from exact spelling to lossless logical
  compatibility while still rejecting the new wrong-type/capacity/nullability
  negatives. The exact last-failed plus SE selection then passed **50 passed,
  20 skipped**.
- No new release, provider architecture, or 64-bit support claim is made by
  this repair evidence. Final focused/full/build/docs gates and a clean exact
  candidate commit remain required before carry-forward review.

### Pre-commit aggregate gates

- Affected parser/importer/realtime/migration selection: **685 passed, 20
  skipped, 10 subtests passed**.
- Fresh PostgreSQL 16 final SE selection after lossless type-compatibility
  refinement: **66 passed**.
- Complete Actions-equivalent non-live suite on Python 3.12.11: **2967 passed,
  189 skipped, 14 deselected, 21 subtests passed**, total coverage 77 percent.
- Test-gate self-validation, fatal syntax/undefined-name flake8, `uv lock
  --check`, and `git diff --check` passed.
- Strict MkDocs passed. Fresh PEP 517 wheel and sdist built; the distribution
  content gate and installed-wheel init smoke both passed, with `specs/`
  excluded from the artifacts.
- The runtime CP932 width map is directly bound to every non-header/non-key
  parser slice from the pinned SDK manifest in the existing SE oracle test;
  the added assertion passed.
- These results precede the final commit only to catch integration issues. The
  same required gates must be rerun against the resulting clean full SHA before
  it can be reviewed or pushed.

## Exact-candidate carry-forward review and final repair batch

- Two independent Codex reviewers examined exact clean candidate
  `5a3dca5ff0027b08eb590e850eb52d05db870dde` after the preceding aggregate
  gates. Both stayed read-only and both returned `NEEDS_CHANGES` before any
  repair was started.
- The reviewers independently reproduced one shared P1: a standard
  `DataKubun=0` row with conflicting native/standard reservation aliases was
  rejected before the opaque-body branch, so the correct eight-key row was not
  deleted. The database/orchestration reviewer also reproduced a second P1 on
  PostgreSQL: a `CHAR(36)` replacement for expected `VARCHAR(36)` passed the SE
  verifier but read back a one-character name with 35 padding spaces.
- The two findings were deduplicated into this one final repair batch. No
  unrelated review hypothesis or additional broad test matrix was added.

### Observed red before the final repair

- The new standard status-0 storage regression failed on the unchanged
  candidate with `SchemaMigrationError: conflicting SE alias values`; the
  existing row remained present.
- The new fresh-PostgreSQL schema regression failed with
  `DID NOT RAISE SchemaMigrationError`; the fixed-width `Bamei CHAR(36)` table
  was accepted and written.
- These exact failures were observed before changing production code. The
  paired current-layout/status-0 and canonical-schema positives remained green.

### Final repair and focused evidence

- `validate_se_record()` now validates the official key first and returns for
  status 0 before inspecting any body alias. Non-delete rows retain the strict
  conflict, CP932, and physical-width validation.
- The SE type verifier no longer treats fixed and variable text declarations as
  one widening family. Expected `VARCHAR(n)` accepts only sufficient
  `VARCHAR` or unbounded `TEXT`; expected `CHAR(n)` accepts only the exact
  declaration. This prevents backend padding or accepted-domain changes.
- Both formerly red tests pass after the repair. The complete SQLite SE file is
  **47 passed, 21 skipped** and the fresh PostgreSQL 16 SE file is **68
  passed**. Final commit, exact-SHA full gates, and bounded carry-forward review
  remain required before push.
