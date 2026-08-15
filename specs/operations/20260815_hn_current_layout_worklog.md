# HN current-layout compatibility worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: reconcile the `HN` breeding-horse master parser and storage
  contract with the official pre-2023 and current JV-Data definitions, fixing
  every byte-offset consequence of the 8-byte to 10-byte registration-number
  change without accepting unsupported mixed layouts.
- Minimum scope: `HN` parser, directly coupled schemas/mappings/import paths,
  a gap-free CP932 byte sentinel, exact-layout rejection, migration guidance,
  and directly affected compatibility documentation.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_hn_layout`
- Branch: `agent/hn-current-layout-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `8b6e803843bf885054c582fc72d4d58dc39efce5`
- Previous iteration: PR #170 merged at the base SHA; its final candidate was
  `fbaf4166ad97fd1a718caf40a012892b4e517f06`.
- Implementer and reviewer: Codex. Claude Code is not used.

## Initial decision boundary

- Re-read current official SDK 5.0.0 and archived 4.8.0.2 definitions before
  changing offsets. Record length alone is not sufficient proof.
- Determine the supported physical-layout policy from the official 2023
  dataspec migration guidance. Do not silently dispatch mixed old/current
  records if current DIFN setup is the supported source contract.
- Because this change corrects a fail-closed parser gate and exact-offset test,
  add the failing current-layout sentinel first and run it against the base
  implementation before changing production code.
- Stop before merge unless every downstream field after each expanded
  registration number, exact length/CRLF rejection, schema compatibility,
  exact-candidate tests, review findings, and PR threads are resolved.

## Official and community evidence

- Current official artifact: JRA-VAN Data Lab SDK 5.0.0 64-bit,
  `https://jra-van.jp/dlb/sdv/sdk/JVDTLABSDK500_64bit.zip`; archive SHA-256
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`.
  Its Python `JVData_Struct.py` SHA-256 is
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`.
- SDK `JV_HN_HANSYOKU.SetDataB` defines the current 251-byte record at positions
  `HansyokuNum=12/10`, `reserved=22/8`, `KettoNum=30/10`, `DelKubun=40/1`,
  `Bamei=41/36`, `BameiKana=77/40`, `BameiEng=117/80`, `BirthYear=197/4`,
  `SexCD=201/1`, `HinsyuCD=202/1`, `KeiroCD=203/2`,
  `HansyokuMochiKubun=205/1`, `ImportYear=206/4`, `SanchiName=210/20`,
  `HansyokuFNum=230/10`, `HansyokuMNum=240/10`, and `crlf=250/2`.
- Official 4.8.0.2 defines a 245-byte physical record: the three breeding
  registration numbers are 8 bytes, the first reserved field starts at 20,
  `KettoNum` at 28, `BameiEng` at 115/80, parents at 228/8 and 236/8, and CRLF
  at 244. The 4.9.0 change history explicitly expands all three numbers from
  8 to 10 bytes.
- Official JRA-VAN developer-community staff guidance in topics 215 and 221
  distinguishes old dataspec records from N-suffixed current records and says
  a fresh current setup returns older history converted to the expanded shape;
  old/new stores should be rebuilt rather than mixed. This iteration therefore
  follows the repository's current-dataspec policy: accept exactly 251-byte HN
  records and fail closed on 245-byte records.

## Base audit and red proof

- Base parser declares 251 bytes but reads `HansyokuNum` as 8 bytes, then uses
  neither the old nor current layout: it reads a one-byte first reserve, starts
  `KettoNum` at 21, truncates `BameiEng` to 40 bytes, reads father/mother at
  181/8 and 189/8, and treats bytes 197-249 as a nonexistent `Reserved_197`.
  It also warns but continues on short input and never validates exact length
  or CRLF. Thus every field from the first registration number through the
  delimiter can be corrupted, including the primary key.
- The native `NL_HN` schema persists the nonexistent `Reserved_197`. The
  optional standard-name `HANSYOKU` schema omits both `HansyokuNum` and
  `HansyokuMNum`, lacks the primary key, and uses SDK names that the native
  parser does not translate, so standard-name HN import cannot preserve the
  official record contract.
- Existing base tests passed despite the defect: HN fixture smoke was 4 passed
  and parser compatibility was 209 passed. The historical binary fixture only
  checks shape/non-emptiness and was reconstructed through the obsolete hybrid
  parser; it is not exact-offset evidence.
- Added a gap-free current-layout sentinel and storage/schema contract before
  changing production code. On base, the three focused negative cases all
  failed as intended, exit 1: `HansyokuNum` produced `12345678` instead of
  `1234567890`; a 245-byte CRLF record returned a corrupt dictionary instead of
  `None`; and the standard schema lacked `HansyokuNum` and `HansyokuMNum`.

## Implementation and local validation

- Corrected all HN slices to the official 251-byte current layout, including
  the 80-byte English name and both 10-byte parent registration numbers.
  Parsing now accepts only exactly 251 bytes ending in CRLF. The 245-byte old
  physical record, short/long input, and malformed delimiters return `None`.
- Preserved the native parser field names for API compatibility, removed the
  nonexistent `Reserved_197`, and added explicit standard-schema aliases for
  `HansyokuMochiKubun`, `HansyokuFNum`, and `HansyokuMNum`.
- Corrected both storage schemas. `NL_HN` keeps its existing native primary-key
  contract; standard `HANSYOKU` now contains `HansyokuNum`, both parent keys,
  official widths/types, and `PRIMARY KEY (HansyokuNum)`.
- Added a gap-free sentinel that makes every decoded field value distinct,
  checks every offset and emitted field, exercises negative exact-layout
  cases, and round-trips through both native/standard schemas with both normal
  and optimized importers. A reproduced obsolete keyless standard table is
  rejected before import; it is not additively mutated into a falsely safe
  shape.
- During the expanded importer test, both optimized imports wrote the correct
  HN values, but the test initially failed because that importer also reports
  `success_rate`. The assertion was narrowed to the three shared statistics;
  this was a test-contract correction, not a production failure.
- Current pre-commit focused validation:
  `pytest -q tests/test_hn_parser_layout.py tests/test_jra_fixtures.py
  tests/test_parser_compatibility.py tests/test_importer.py
  tests/test_importer_clean_record.py tests/test_all_schemas.py
  tests/test_migration.py` -> 406 passed, 1 skipped, exit 0.
- The first repository-wide `pytest -q` exposed three HN failures in the
  shared parser sample because it still ended HN with spaces. Updated that
  generic sample to use current-spec CRLF; `tests/test_parsers.py` then passed
  404/404. The same first run also showed two CLI order-dependent failures
  that passed in isolation. A clean detached worktree at the unchanged base
  SHA reproduced those same two failures (1874 passed, 47 skipped, 2 failed),
  proving they were not caused by HN. The final current-worktree full rerun was
  fully green: 1912 passed, 47 skipped, 5 subtests passed, exit 0.
- New test file passes Black and Ruff. Workflow-equivalent critical Flake8
  (`E9,F63,F7,F82`) reports 0. `git diff --check` passes. Repository-wide
  non-blocking style warnings predate this iteration and are not a CI gate.
- Existing `NL_HN` rows cannot be repaired from their stored values because
  the old parser corrupted the primary key and downstream fields. After this
  code is deployed, rebuild/reimport HN from a current `DIFN` / `BLDN` source.
  An obsolete standard `HANSYOKU` table also requires operator rebuild because
  adding a primary key is intentionally not an automatic migration.

## Candidate validation

- Code candidate full SHA:
  `55071495af6646ead9326ae8341d198ce268ce30`.
- Exact-SHA focused parser/importer/schema/migration run: 406 passed, 1
  skipped, exit 0.
- Exact-SHA local GitHub Actions test-job equivalent: 862 passed, 2 skipped,
  3 subtests passed, exit 0.
- Critical Flake8 (`E9,F63,F7,F82`) and `git diff --check` passed before the
  candidate commit; the repository-wide full suite on the identical candidate
  content passed 1912 tests with 47 skipped.

## Current state and next safe commands

1. Commit this validation record, then run the required focused checks against
   that final documentation-only descendant SHA.
2. Run one aggregated Codex review of the final full SHA and batch any
   actionable corrections before publishing.
3. Push, create the PR, request the one native Copilot review, resolve all
   actionable threads, and merge only after the final-SHA gates are green.
