# BN current-layout iteration worklog

## Scope and identity

- Started: 2026-08-15 JST
- Objective: reconcile the BN owner-master parser and native/standard storage
  with the official current 477-byte JV-Data layout, including both current-year
  and cumulative result arrays, without silently accepting reconstructed or
  obsolete physical shapes.
- Minimum scope: BN parser, directly coupled schemas/mappings/importers,
  fixtures, red-first contracts, official-version boundary, compatibility audit,
  exact-SHA Codex review, PR, and merge.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_bn_layout`
- Branch: `agent/bn-current-layout-20260815`
- Base / initial HEAD: `05bc415713d8995559debbccc2cb5d520d99b4a9`
  (merged `master`, PR #176)
- Production/release version: no release is created by this iteration. The
  user-mandated fresh-acquisition release gate remains pending until all code
  and public-document cleanup iterations are merged.
- Implementer and reviewers: Codex only. Claude Code is not used because the
  user explicitly requested continued Codex review.

## Starting observations

- The canonical audit classifies BN as partial: implementation length 387
  versus the current official 477 bytes.
- `BNParser` accepts overlong input and decodes with replacement, parses only
  one six-byte finish-count value, and treats bytes 386-387 as a delimiter.
- The current official shape has two 60-byte performance blocks (current year
  and cumulative), each containing setting year, main/additional prize totals,
  and six finish-count members; CRLF is at bytes 476-477.
- Native `NL_BN` still reflects the truncated fields. Standard `BANUSI`
  contains most expanded names but currently omits `BanusiCode`,
  `R_ChakuKaisu6`, and a primary key, so an existing legacy-only table may need
  a fail-closed rebuild contract rather than an unsafe additive migration.
- PR #174 is an unmerged, conflicting grouped proposal. Its BN parser/schema
  diff is reference material only; it is not trusted as official evidence and
  will not be merged or cherry-picked as a unit.

## Evidence sources

- Official JV-Data 4.8.0.2 and 4.9.0.1 workbooks/PDFs preserved under
  `/home/keiba/scratch/20260815_jvdata_official_materials/`.
- Official SDK 5.0.0 32/64-bit documentation preserved under
  `/home/keiba/scratch/20260808_jravan_official_audit/`.
- Current `master`, repository tests/fixtures, compatibility audit, and PR #174
  are compared independently; repository or PR claims are not treated as the
  official source.

## Official/version decision

- Workbook rows 800-818 are identical in official 4.8.0.2, 4.9.0.1, and the
  SDK 5.0.0 copy: BN is 477 bytes, the two 60-byte result blocks begin at byte
  356, six six-byte finish counts occur in each block, and CRLF is bytes
  476-477. SDK `JV_BN_BANUSI.SetDataB` independently uses the same slices.
- The official 2003-06-03 change history says BN changed from 413 to 477 bytes
  when the 64-byte no-corporate-suffix owner name was added. The repository's
  387-byte shape is therefore neither the old nor current official format.
- Current provider setup is a current-dataspec contract. The official support
  answer at `https://developer.jra-van.jp/t/topic/215` confirms that older
  history returned through a new setup uses the reviewed current size and that
  mixing old and new physical dataspec records is unsupported; users must
  rebuild through the current data IDs. This iteration accepts current 477-byte
  records only and explicitly rejects old physical 413-byte and repository
  387-byte records. Historical race periods remain available through current
  setup; unsupported physical generations do not receive heuristic parsing.

## Red-first proof

- Added `tests/test_bn_official_contract.py` before product changes. It defines
  a gap-free 28-field record with distinct same-width sentinels, exact parser
  offsets/output, old/corrupt rejection, both storage schemas, both importers,
  and keyless-standard fail-closed row preservation.
- On base `05bc415713d8995559debbccc2cb5d520d99b4a9`, the focused run failed as
  intended: `34 failed, 10 passed`. Missing result-array fields, `387 != 477`,
  acceptance of 413/387/short/long/wrong-type/bad-CRLF/invalid-CP932 records,
  schema divergence, standard import failure, and the absent keyless-table
  guard were all independently observed.

## Implementation and pre-commit validation

- `BNParser` now accepts exactly 477 bytes with `BN` at bytes 1-2 and CRLF at
  bytes 476-477, decodes CP932 strictly, and emits all 28 flattened official
  fields. Both current-year and cumulative result blocks expose setting year,
  both prize totals, and all six finish-count members.
- `NL_BN` now stores the 27 business fields with `BanusiCode` as its primary
  key. Standard `BANUSI` now includes the previously omitted `BanusiCode` and
  `R_ChakuKaisu6`, uses official widths/numeric types, and declares the same
  primary key. Both ordinary and optimized importers round-trip every business
  field through both schemas.
- An existing keyless standard `BANUSI` cannot receive a primary key through a
  safe additive migration. Both importers raise `SchemaMigrationError` before
  mutation and preserve its existing row; operators must rebuild and reimport
  current-shape BN source records. Existing native `NL_BN` already has the
  correct key, so its missing result columns are additively migratable without
  dropping legacy rows. Migration cannot infer those 18 result values,
  however: every pre-existing row has NULL in the new columns until it is
  replaced from current-shape source data. After deploying this change,
  operators must therefore run a complete current `DIFN` setup import
  (`jltsql fetch --from <start> --to <end> --spec DIFN --option 3`, or the
  supported split-setup option 4) rather than relying on option-1 differences.
  The regression contract proves that migration preserves the legacy row and
  primary key, leaves unknown new values NULL, and that full current-record
  reimport fills the new fields idempotently without duplicating the owner.
- The historical three-record BN binary fixture was reconstructed through the
  non-official 387-byte parser. Only its position-compatible first 355 bytes
  are retained in a synthetic current record for core-value regression; it is
  not accepted by the product parser or presented as official raw data.
- Focused contract changed from red to green: `44 passed`. The affected parser,
  fixtures, compatibility, importer, schema, and migration bundle passed
  `819 passed, 1 skipped`.
- The first full-suite run reached `2014 passed, 47 skipped, 6 subtests` but
  failed only the repository's known order-dependent CLI status/version pair;
  neither CLI code nor its tests changed. Both passed in isolation (`2 passed`),
  and the clean-basetemp full rerun passed `2016 passed, 47 skipped,
  6 subtests`.
- During test-style cleanup, replacing adjacent-pair iteration with strict
  unequal-length `zip` caused the new layout assertion itself to raise. It was
  corrected to `itertools.pairwise`; this was confined to the new test and the
  full contract returned to green.

## Stop conditions

- Do not merge if official offsets/types/version boundaries are unresolved,
  any required local/GitHub check fails, candidate-SHA review has unresolved
  P0/P1/P2 findings, PR threads are unresolved, or the worktree is dirty.
- Do not release from this iteration. Fresh provider acquisition with the final
  merged release-candidate SHA remains mandatory before any release.

## Candidate review and response

- Candidate `0c866612b543c6d820ff95f303bf3ec168c847f0` passed the exact official
  layout review with no P0/P1/P2 finding. Independent storage review found one
  P2 operational-contract gap: native additive migration alone leaves the 18
  new result columns NULL for existing owners.
- The response is batched into one follow-up candidate: document the mandatory
  complete current `DIFN` setup reimport and add one migration/reimport contract
  covering both importers. No parser or schema offset changed in response.

## Next safe commands

1. Run the focused migration/importer contract, exact full suite, and
   workflow-equivalent checks on the follow-up candidate.
2. Obtain one final exact-SHA Codex review of the aggregated P2 response.
3. Push the candidate, open the PR, resolve all actionable review threads, and
   merge only with required checks green and the worktree clean.
