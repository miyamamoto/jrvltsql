# BR current-layout iteration worklog

## Scope and identity

- Started: 2026-08-15 JST
- Objective: reconcile the BR breeder-master parser and native/standard
  storage with the official current JV-Data layout, including every repeated
  result member and the supported pre/post-2023 dataspec boundary.
- Minimum scope: BR parser, directly coupled schemas/mappings/importers,
  fixtures, red-first byte/storage contracts, official-version decision,
  canonical compatibility audit, exact-SHA Codex review, PR, and merge.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_br_layout`
- Branch: `agent/br-current-layout-20260815`
- Base / initial HEAD: `19954206bc8f282f535e505a44b2f81023bbfd96`
  (merged `master`, PR #177).
- Dependency: BN iteration merged as PR #177 at the base SHA above. BR is an
  independent follow-up and does not reuse the BN candidate SHA as evidence.
- Production/release version: no release is created by this iteration. The
  final release remains gated on all official-layout and public-package cleanup
  iterations plus fresh acquisition with the final merged release-candidate.
- Implementer/reviewer policy: Codex only for local implementation and
  independent review. Claude Code is not used per the user's instruction.

## Starting hypotheses to verify

- The compatibility audit records BR as implementation 455 bytes versus
  official current 545 bytes and notes a 2023 physical-generation boundary of
  537 to 545 bytes.
- Determine exact 4.8.0.2, 4.9.0.1, and SDK 5.0.0 offsets and repeated result
  cardinality directly from official materials; do not trust grouped PR #174
  or existing generated comments as evidence.
- Determine whether the supported current `DIFN` setup normalizes historical
  BR periods to the current physical shape. Accept multiple layouts only if
  the current provider contract can actually return both.
- Audit `NL_BR` and standard `SEISAN` keys, all business fields, additive or
  fail-closed migration behavior, full-reimport requirements, and idempotent
  imports through both ordinary and optimized paths.

## Evidence and version decision

- Official JV-Data 4.8.0.2 rows 779-797 define the old 537-byte BR: a six-byte
  breeder code, three 70-byte name fields, the unchanged English/address
  fields, two 60-byte result blocks, and CRLF at bytes 536-537.
- Official JV-Data 4.9.0.1 and both SDK 5.0.0 copies define the current
  545-byte BR: an eight-byte breeder code, three 72-byte name fields, the same
  two complete result blocks, and CRLF at bytes 544-545. SDK
  `JV_BR_BREEDER.SetDataB` independently slices the blocks at
  `424 + 60 * i`, two times, using all six finish counts from
  `SEI_RUIKEI_INFO`.
- The 4.9.0.1 change history records the code/name width expansion. Community
  topic `https://developer.jra-van.jp/t/topic/206` reproduces that retired
  `DIFF` setup returns the old 537-byte BR while `DIFN` returns the new body
  width. More importantly, the official support response at
  `https://developer.jra-van.jp/t/topic/215` confirms that new setup must use
  the new data IDs, normalizes pre-2023 periods to the new sizes, and forbids
  mixing old/new stores.
- Product entry points already reject retired `DIFF`. This iteration therefore
  accepts exactly the supported current 545-byte physical record and rejects
  old 537-byte and repository 455-byte records. Supporting the retired physical
  generation inside the parser would contradict the supported setup contract.
- The standard schema is named `SEISAN`, consistent with the repository's
  JRA-VAN-compatible schema and established DB naming, but the reverse mapping
  incorrectly selected `BREEDER`; this made standard BR imports target a table
  for which no schema exists. `SEISAN` becomes canonical while the public
  `BREEDER -> NL_BR` lookup remains a read-side alias. A database containing
  only the legacy alias table fails closed without row loss and must rebuild as
  `SEISAN`.
- PR #174 correctly noticed the 545-byte tail and result-array cardinality but
  did not add exact length/type/CRLF/strict-CP932 gates, did not repair standard
  storage/mapping, and stored parser metadata as a business column. It remains
  reference material only and is not cherry-picked.

## Red-first proof

- Added `tests/test_br_official_contract.py` before product changes. It defines
  a gap-free 28-field current record with distinct same-width sentinels, every
  exact offset, old/corrupt rejection, canonical/alias mapping, native/standard
  schemas, both importers, native migration/full reimport, keyless `SEISAN`,
  and legacy `BREEDER` row-preserving failure.
- On base `19954206bc8f282f535e505a44b2f81023bbfd96`, the contract failed as
  intended: `39 failed, 10 passed`. The failures directly exposed omitted
  result members, `455 != 545`, acceptance of every invalid physical record,
  the `BREEDER` routing break, schema divergence, incomplete round trips, and
  missing migration guards.

## Implementation and pre-commit validation

- `BRParser` now requires exactly 545 bytes, `BR` at bytes 1-2, CRLF at
  544-545, and strictly decodable CP932 fields. It emits all 28 flattened
  physical fields, including both setting years, both prize totals, and twelve
  finish-count values.
- `NL_BR` and canonical `SEISAN` expose the same 27 business fields with
  `BreederCode` as primary key and explicit numeric storage for all result
  values. Ordinary and optimized importers round-trip every field through both
  schemas.
- Existing native `NL_BR` can add the 18 result columns without losing its row
  or key, but those values cannot be inferred and remain NULL until every
  breeder is reimported. Operators must run a complete current `DIFN` option
  3/4 setup after deployment; option-1 differences are insufficient. Reimport
  fills the current fields and is idempotent for the eight-byte breeder key.
- Existing keyless `SEISAN` cannot safely gain its primary key, and a database
  containing only the legacy `BREEDER` alias cannot be silently retargeted.
  Both cases raise `SchemaMigrationError` before mutation and preserve rows;
  operators must rebuild canonical `SEISAN` and reimport current setup data.
- The repository BR fixture is a reconstructed 455-byte shape. Tests retain
  only its position-compatible first 423 bytes in a synthetic current record;
  the dedicated official contract covers the complete 545-byte record.
- Focused contract changed from red to green: `49 passed`. The affected parser,
  fixture, mapping, importer, schema, and migration bundle passed
  `826 passed, 1 skipped`.
- The first full-suite run reached `2066 passed, 47 skipped, 6 subtests` and
  failed only the repository's known order-dependent CLI status/version pair;
  neither CLI implementation nor those tests changed. Both passed alone
  (`2 passed`), and the uncontended rerun passed `2068 passed, 47 skipped,
  6 subtests`.
- The workflow-equivalent test selection with coverage passed `863 passed,
  2 skipped, 3 subtests`. Critical flake8, scoped Ruff/Black for the new parser
  and contract, compileall, and `git diff --check` passed.
- A temporary isolated PostgreSQL 16 instance verified ordinary/optimized x
  native/standard imports. All four fresh paths stored all 27 non-NULL business
  fields with the `BreederCode` primary key and remained one row after a second
  upsert. Both importers also preserved the old native row/key through additive
  migration, observed the new columns as NULL before reimport, filled them from
  the current record, and refused keyless `SEISAN` without row loss. The
  temporary schemas and container were removed after validation.

## PR and aggregated review

- PR #178 was opened from candidate
  `3714fec833da6c7ace8379378b103ca9b484e46f`. GitHub Actions `test` and
  `lint` passed for that full SHA. CodeRabbit could not run because its
  service-side review limit was reached; it is auxiliary and produced no code
  finding.
- The one requested GitHub Copilot review covered all 11 changed files and
  raised one actionable documentation finding: the shared parser test called
  every sample-generation length official even though legacy permissive
  parsers still use shortened samples. The comment now distinguishes sample
  lengths from the supported current physical length required by strict
  parsers. Product behavior and the BR contract are unchanged.

## Stop conditions

- Stop before merge if the official offsets, old/current boundary, key or
  migration contract is unresolved; a required exact-SHA test/check fails;
  any actionable P0/P1/P2 finding or PR thread remains; or the worktree is
  dirty.
- Do not release from this iteration and do not treat fixture/mock/replay data
  as the final fresh-provider release gate.

## Next safe commands

1. Run full and workflow-equivalent validation, static checks, and temporary
   PostgreSQL migration/import verification.
2. Commit one candidate and perform exact-SHA official-layout and storage
   reviews without modifying it during review.
3. Push, open the PR, collect review findings once, and merge only after all
   final gates are green.
