# RA current-layout compatibility worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: replace the non-official 856-byte RA compatibility contract with
  the complete official 1,272-byte race-detail layout without dropping prize,
  lap-time, corner, or update fields, while strictly validating its framing
  delimiter.
- Minimum scope: `RA` parser, directly coupled native/standard schemas,
  fixtures and generators, importer/storage behavior, exact-length and CRLF
  rejection, compatibility audit reconciliation, focused/full tests, Codex
  review, PR, and merge.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_ra_layout`
- Branch: `agent/ra-current-layout-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `ff62d65c07b1026e7ea7606b1d6329dbd9768199`
- Previous iteration: PR #175 merged at the base SHA; its final PR head was
  `7dc9d6fdb0697d37cd1e89d3a7c2c314b389f94a`.
- Implementer and reviewers: Codex only. Claude Code is not used because the
  user explicitly requested continued Codex review.
- Applied workflow: `kps-jra-nar-release-readiness`, limited to JRA parser and
  storage data integrity, red-first contract tests, exact-SHA review, PR gates,
  and release-readiness evidence.

## Official evidence and initial audit

- Official JV-Data 4.9.0.1 workbook SHA-256:
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`.
- Official SDK 5.0.0 archive SHA-256:
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`.
  Its `JV_RA_RACE.SetDataB` contract ends at byte 1,272 and defines 7 current
  main-prize values, 5 previous main-prize values, 5 current additional-prize
  values, 3 previous additional-prize values, 25 lap times, and 4 corner
  blocks before `RecordUpKubun` and CRLF.
- Official 4.8.0.2 also defines RA as 1,272 bytes. The repository's 856-byte
  shape is therefore not the previous official generation and must not be
  presented as old-layout compatibility.
- Base `RAParser.RECORD_LENGTH` is 856, warns but continues for shorter input,
  accepts longer/truncated data heuristically, stores only four prize values
  and one lap value, and exposes a delimiter inside the official record. It
  partially overlays selected 1,272-byte offsets but still drops most official
  arrays.
- Native `NL_RA` and `RT_RA` cannot store the full prize/lap contract. Standard
  `RACE` has most official columns but parser key mismatches drop lap, haron,
  and first-corner values, and the table has no race identity primary key.
- The canonical audit is stale for already merged transport and byte-first
  repairs. PR #163 fixed the COM signature/state contract, PR #164 recorded an
  authenticated Windows/JV-Link smoke, PR #165 fixed headless open behavior,
  and PR #166 made `BaseParser` byte-first. This iteration will reconcile those
  entries while updating RA.

## Decision and stop conditions

- Accept exactly 1,272 bytes with `RA` at bytes 1-2 and CRLF at bytes
  1,271-1,272. Reject 856-byte, truncated, overlong, wrong-type, and bad-CRLF
  inputs; unknown or unreadable input is not a successful parse.
- Preserve the official three-leading-space marker in each corner-order field;
  it identifies horses that did not pass the corner and is not record padding.
- Preserve documented legacy output aliases only where existing callers need
  them, while emitting every official array field so both native and standard
  storage retain all values.
- Add the smallest exact-layout negative and positive regression contract
  first and run it against the base to prove the current parser can fail open
  and lose data.
- Stop before merge if any official value is missing, either importer drops a
  value, schema migration/upsert cannot preserve race identity, tests fail,
  review findings remain, or PR threads are unresolved.
- Final release has a separate non-waivable gate from the user: run the merged
  release candidate on an actual supported JV-Link environment, acquire fresh
  data from the provider, and verify acquisition, parse, and database storage
  with record counts, keys, and representative values. Mocks, synthetic
  fixtures, and replay of previously saved data do not satisfy this gate. Do
  not publish a release if that acquisition cannot be completed.

## Initial safe commands

1. Extract the exact RA field sequence and byte ranges from both official
   workbooks and SDK 5.0.0, then compare parser and both schemas mechanically.
2. Add and run red-first current-shape, malformed-boundary, and storage tests.
3. Implement the parser/schema/import repair in one batch and run focused tests.

## Red-first proof

- Added `tests/test_ra_official_contract.py` before production changes and ran
  `pytest -q tests/test_ra_official_contract.py` against base
  `ff62d65c07b1026e7ea7606b1d6329dbd9768199`.
- Result: exit 1, `11 failed`. The failures proved all intended negative and
  loss cases: the declared length was 856; 856-byte, short, long, wrong-type,
  and bad-CRLF inputs returned dictionaries; native schemas lacked the full
  arrays; standard `RACE` lacked a primary key; native queries could not name
  the missing columns; and standard round-trips stored the missing parser
  values as NULL.
- The strict-decode branch was then exercised against the base parser source
  loaded directly from the base commit. The new invalid-CP932 record produced
  `base_invalid_cp932_result_type=dict`, and the assertion that it be rejected
  failed. The repaired parser returns `None` for the same record.

## Official comparison and implemented candidate

- Read-only extraction of the `フォーマット` sheet in both official
  4.8.0.2 and 4.9.0.1 workbooks found the RA section at the same rows with
  record length 1,272. The 64 field/header rows, names, starts, repeat counts,
  and element widths compared equal. SDK 5.0.0 `JV_RA_RACE.SetDataB` matches
  the same byte ranges.
- `RAParser` now requires exactly 1,272 bytes, `RA` at bytes 1-2, and CRLF at
  bytes 1,271-1,272. It slices each field before strict CP932 decoding and
  returns `None` for unsupported boundaries or unreadable input.
- Standard `RACE.SyogaiMileTime` is numeric, so importer conversion now applies
  the official implied tenth to that exact field (`1572 -> 157.2`). Native
  storage retains its existing raw-text compatibility value. The new
  round-trip assertion failed as `1572` before this conversion repair and
  passes for both importers afterward.
- All official repeated fields are explicit byte slices: main prize 1-7,
  previous main prize 1-5, additional prize 1-5, previous additional prize
  1-3, lap time 1-25, and four corner blocks. Explicit slices also let the
  fixture extractor discover all fields instead of silently omitting loops.
- Official standard names are emitted together with the documented native
  compatibility aliases for the first lap, haron totals, and corner order.
  `NL_RA` and `RT_RA` retain the aliases while also storing every official
  field. `RACE` stores the official names and now has the six-part race
  identity primary key. Both importers round-trip the last member of every
  repeated array through native and standard SQLite schemas.
- Existing standard `RACE` tables created without that primary key cannot be
  repaired by an additive migration. Import now fails closed with
  `SchemaMigrationError`, preserves the existing rows, and requires an
  operator-managed rebuild instead of permitting duplicate race identities.
- The test record factory, compatibility maps, parser tests, realtime update
  tests, and fixture loader now use 1,272-byte current records. The historical
  repository fixture was reconstructed by the former non-official 856-byte
  parser; only its position-compatible first 713 bytes are retained in a
  synthetic current record for core-field regression checks. It is not
  accepted by the production parser or represented as official raw data.
- The canonical audit now records PRs #163/#165 as the resolved transport
  contract and authenticated positive-download smoke, PR #166 as the resolved
  byte-first core, and RA as current-shape. The remaining partial-record count
  is nine. Those older authenticated calls remain insufficient for the
  user-mandated final release-candidate fresh acquisition gate.

## Pre-review candidate validation

- The expanded red-first contract is now green: `13 passed`, including the
  existing keyless-standard-table no-data-loss failure contract.
- The affected RA parser, parser factory, compatibility, registered fixture,
  realtime updater, native/standard importer, and schema suite passed
  `804 tests, 3 subtests passed`.
- The isolated repository suite passed `1966 passed, 41 skipped, 6 subtests
  passed` after updating the intentional `NL_RA` column-count contract from
  71 to 122. The first run correctly failed only on that stale count.
- The exact test list in `.github/workflows/test.yml` passed `862 passed,
  2 skipped, 3 subtests passed`. Direct migration/schema/importer coverage
  passed `196 passed, 3 skipped`.
- `scripts/extract_fixtures_from_db.py` discovered 111 literal RA fields at
  length 1,272 and omitted none of the official repeated fields.
- `scripts/validate_schema_parser.py --all` reports both `RA -> NL_RA` and
  `RT_RA -> RT_RA` as exact 122-field matches. The script still exits 1 for
  unrelated pre-existing HR/SE/WF and dynamic-parser findings; those remain
  input to later iterations rather than being claimed green.
- Critical flake8 (`E9,F63,F7,F82`), compileall, targeted Ruff, targeted Black,
  and `git diff --check` pass. `tests/INTEGRATION_TESTS.md` was reconciled to
  the new 122-column native contract.
- Worktree remains dirty only with the intended iteration changes. No release
  or external data operation has been performed in this iteration.

## Independent review and repair batch

- Two independent Codex reviewers inspected immutable candidate
  `6c83b429639609787b07b13171fa76977b7075d4`. Both returned `NEEDS_CHANGES`:
  the shared field decoder and TEXT conversion removed the official three-space
  non-passage marker from `Jyuni1..4` and `TsukaJyuni*`, and the tests did not
  independently populate all 111 official fields.
- Red-first additions were run before the product repair. The focused command
  failed `7 failed, 12 passed`: parser, both importers, native/standard storage,
  and realtime storage all returned ordinary order text instead of the
  expected three-space marker.
- The repair uses right-trim-only decoding/conversion for the eight affected
  official/compatibility names. Both optimized and ordinary importers and the
  realtime updater share that conversion path.
- The new independent layout contract expands all 111 official fields, proves
  byte ranges are contiguous through byte 1,272, gives every field a nonblank
  type-valid sentinel, verifies exact parser values, and checks every business
  column remains non-NULL through both importers and native/standard schemas.
- CRLF is classified as a framing delimiter: exact validation is mandatory,
  but storing control bytes as a database business value is not required.
- The stale public layout note was scheduled for deletion in the separate
  maintainer-requested public documentation cleanup iteration.

## Review-repair validation

- After the repair, the parser/importer/realtime focused contract passed
  `19 passed`; the affected RA bundle passed `844 passed, 3 subtests`.
- The isolated full repository suite passed `1972 passed, 41 skipped,
  6 subtests`, and the exact `.github/workflows/test.yml` list passed
  `862 passed, 2 skipped, 3 subtests`.
- Critical flake8, targeted Black/Ruff, compileall, and `git diff --check`
  remained green.
- An independent PostgreSQL 16 check exercised both ordinary and optimized
  importers with native and standard schemas, confirmed idempotent `RT_RA`
  upsert, and confirmed keyless standard `RACE` fails closed without losing
  its existing row.
- Final candidate review of
  `024da61b2525a6bf675eadf9e5084c493df39d3c` found one P2 test-strength gap:
  four same-width numeric/text field pairs reused a sentinel, so swapping
  those offsets could evade the all-field comparison. A uniqueness assertion
  was added first and failed `1 failed` (`110 != 106`); text sentinels were
  then moved to a letter-first alphabet and the assertion passed with zero
  duplicate `(size, value)` pairs. The implementation itself had no new
  P0/P1/P2 storage finding.

## Next safe commands

1. Commit the review-repaired immutable candidate and record its full SHA in
   PR/review evidence.
2. Run exact-SHA focused/full/workflow/style validation and two complementary
   independent Codex reviews; batch actionable findings once.
3. Open a PR and merge only after checks are green, review threads are zero,
   the worktree is clean, and the PR head matches the validated full SHA.
