# JV-Data official-spec and compatibility audit worklog

## Audit identity

- Started: 2026-08-15 JST
- Objective: compare jrvltsql exhaustively against the current official
  JV-Data/JV-Link contracts, their published change history, and relevant
  JRA-VAN developer-community reports; determine whether changed formats are
  handled correctly before and after each boundary.
- Minimum scope: dataspec/option matrix, JV-Link calls and return handling,
  record IDs and lengths, field offsets/types/encodings, parser dispatch,
  SQLite/PostgreSQL schemas, realtime/time-series records, and known versioned
  layout transitions. Community posts are corroboration, never a replacement
  for an official contract.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_official_spec_audit`
- Branch: `codex/jvdata-official-spec-audit-20260815`
- Base / initial HEAD / `origin/master`:
  `d6f8f70e4976e053f636dc1d136a3214fa6996ad`
- Related production/release version: none identified; this is a read-only
  source-contract audit of current `master`.
- Dependencies: none. No production runtime or credential-bearing data source
  is required for the initial static audit.

## Evidence policy

- Official JRA-VAN SDK documents and announcements are primary evidence.
- JRA-VAN Data Lab developer-community staff answers and archived board posts
  are secondary evidence and will be labelled as such.
- Current source behavior, repository history, fixtures, and tests are observed
  independently. A passing test is not treated as proof if it does not reach a
  failure boundary.
- “Supports both versions” means the implementation can identify the applicable
  layout and parse each without silent field shift, truncation, key corruption,
  or schema coercion. Merely keeping an old dataspec constant importable does
  not count as old-layout parsing support.

## Initial sources discovered

- Official SDK index: `https://jra-van.jp/dlb/sdv/sdk.html`
- Current official JV-Data specification 4.9.0.1:
  `https://jra-van.jp/dlb/sdv/sdk/JV-Data4901.pdf`
- Official 2023-08-08 SDK/JV-Link update notice:
  `https://jra-van.jp/dlb/sdv/ml/20230808a.html`
- Official support notice requiring the 2023-08-08 client update:
  `https://support.jra-van.jp/jravan/detail?category=2&id=332&site=SVKNEGBV`
- Official developer community: `https://developer.jra-van.jp/`
- Community topics initially relevant to change history and option behavior:
  `/t/topic/457`, `/t/topic/459`, `/t/topic/622`, `/t/topic/732`.

## Operations and observations

- Fetched `origin/master`, verified full SHA
  `d6f8f70e4976e053f636dc1d136a3214fa6996ad`, and created the clean dedicated
  worktree/branch above.
- Initial official-source search confirms the current published SDK is 4.9.0.2
  while both the JV-Link and JV-Data reference documents are 4.9.0.1 dated
  2024-08-07. The current JV-Data table lists legacy and N-suffixed dataspecs in
  parallel; the exact semantics and date/layout selection still require
  section-level verification and must not be inferred from the table alone.
- Downloaded the current official JV-Data/JV-Link documents and the immediately
  preceding JV-Data 4.8.0.2 PDF/XLSX into
  `$WORKSPACE/20260815_jvdata_official_materials/`. Relevant SHA-256
  values are:
  - `JV-Data4901.xlsx`:
    `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`
  - `JV-Data4901.pdf`:
    `b6c21aae4ccbba6a71c5e8065609c4fbb1ccee826c16e7d99ca6ecf7a4101522`
  - `JV-Link4901.pdf`:
    `dfd1c425a62304bb464f15c25106e030ffccbf99c7c777972d6bb6b6d27ef1d7`
  - `JV-Data4802.xlsx`:
    `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`
- Official JRA-VAN staff answers in developer-community topics 215 and 221
  establish three distinct cases at the 2023-08-08 boundary: old normal data
  through 2023-08-07 is requested with the old dataspec and old structure;
  normal data registered on/after 2023-08-08 uses the N-suffixed dataspec and
  expanded structure; a fresh N-suffixed setup returns older history converted
  to the expanded structure. Staff explicitly advises rebuilding with the new
  setup instead of mixing old and new structures in one store.
- Comparing the official 4.8.0.2 and 4.9.0.1 workbooks found exactly seven
  record-length transitions: `UM 1577->1609`, `BR 537->545`, `HN 245->251`,
  `SK 178->208`, `CK 6864->6870`, `HS 196->200`, and `BT 6887->6889`.
  The changes are breeder code/name and breeding-registration-number width
  expansions, including all consequent byte-offset shifts.
- Instantiated all 38 current parser classes and compared their declared or
  effective terminal offsets to the current official record lengths. Twelve
  have an obviously truncated or wrong public current-format contract:
  `BN 387/477`, `BR 455/545`, `CH 592/3862`, `DM 48/303`, `KS 772/4173`,
  `RA 856/1272`, `RC 241/501`, `SK 78/208`, `TK 727/21657`, `TM 39/141`,
  `WH 40/847`, and `YS 146/382` (`implementation/official`). `CC`, `JC`, and
  `TC` end two bytes before the official length only because their BaseParser
  field lists omit CRLF; that is not itself truncation. RA contains a separate
  1272-byte branch despite its incorrect public length constant, so it is
  classified separately: its current branch reaches late fields but still
  stores only a subset of official repeated arrays.
- `BaseParser.parse()` decodes the entire Shift-JIS byte record before slicing
  fields by official byte offsets. The workbook states positions in bytes and
  full-width characters occupy two bytes. Therefore its claim that
  `errors='replace'` preserves field positions is false: any multibyte text
  before a later field shifts that field's Unicode-string index. AV overrides
  the method with byte slicing; other BaseParser descendants require a
  per-record reachability test.
- The code's JVOpen matrix contradicts the current official matrix by accepting
  record IDs `O1`-`O6` as dataspecs; those are records returned inside `RACE`,
  not valid JVOpen data-specification IDs. `MING` and `COMM` with option 1 are
  accepted by the current JV-Data Excel matrix and its change history, so the
  code is correct on those two entries. The current JV-Link PDF omits both from
  option 1 while listing them for setup, which is an official-document conflict
  rather than a code defect; the Excel data contract and explicit history are
  treated as controlling evidence. Its rejection of all six old dataspecs is a
  deliberate single-generation migration policy, not direct support for both
  official old-normal and new-normal retrieval paths.
- JVOpen officially accepts a concatenation of fixed four-character dataspecs.
  `is_retired_data_spec()` checks only exact whole-string equality, so mixed
  requests such as `DIFFRACE` and `RACEDIFF` bypass the old-layout guard. The
  direct wrapper does not enforce the option matrix, and can therefore pass
  such a stream to COM, mixing legacy and current bytes. This defeats the
  safety boundary introduced by the retired-dataspec gate.
- The native pywin32 wrapper invokes `JVOpen(data_spec, fromtime, option)` with
  three arguments. The official interface has six arguments, and current
  working pywin32 examples pass three placeholder out/ref arguments and receive
  `(rc, readcount, downloadcount, lastfiletimestamp)` as the result tuple. No
  in-repository bridge executable/source is shipped, so the native fallback is
  a production-reachable path. Existing mocks assert the three-argument call
  and therefore hide this real COM contract mismatch.
- `jv_gets()` similarly calls `JVGets("", size)` with two arguments and treats
  the result buffer as a string. The official method takes a byte array, size,
  and filename. This public method is not used by the fetchers, but is not a
  compliant JV-Link implementation.
- Official positions are byte offsets in Shift-JIS. A synthetic current CK
  record with `Bamei=テスト` at byte 38 and prize `123456789` at byte 74
  produced `Bamei='テスト ... 123'`, prize `456789`, and no delimiter. This
  executable counterexample proves BaseParser corrupts fields after multibyte
  text. CK, BT, and JC are directly affected; every BaseParser descendant was
  classified by whether meaningful fields follow multibyte content.
- The realtime `WH` implementation is not a truncated bodyweight parser: its
  40-byte fields are the weather/track-change `WE` layout. Official `WH` is 847
  bytes and contains the race number, announcement time, and 18 repeated
  45-byte bodyweight blocks. `NL_WH`/`RT_WH` mirror the wrong 40-byte schema, so
  0B11 cannot be represented or recovered after import.
- H1/H6/O1-O6/HR use `DataKubun=9` to represent race cancellation. The updater
  preserves this domain state only for RA, SE, and WF; for the other official
  record types it dispatches `9` to physical deletion. This discards the
  cancellation state even though the schemas retain a DataKubun column.
- `H1Parser` and `H6Parser` accept undocumented 317-byte and 78-byte “flat”
  fallback layouts, and `RAParser` accepts an undocumented 856-byte branch.
  Neither the immediately prior 4.8.0.2 specification nor the published change
  history identifies these as old official layouts. Tests and generated fixture
  files label these reconstructed shapes as compatibility/real data, so invalid
  lengths are currently normalized by the test contract.
- The direct wrapper and bridge treat JVOpen return `-2` as no-data success and
  mark the stream open. The official code table defines `-2` exclusively as
  user cancellation of the setup dialog. This loses the cancellation state.
- `HistoricalFetcher._wait_for_download()` correctly waits until `JVStatus`
  reaches JVOpen's `downloadcount`. The bridge's public `wait_for_download()`
  instead waits for progress to become positive and then return to zero; the
  official contract says the completed count remains equal to `downloadcount`
  until JVClose, so that bridge helper times out after a real download.
- The wrapper raises immediately for JVRead/JVGets `-3` even though the official
  contract identifies it as “file still downloading; wait and resume”. The
  bridge preserves `-3`. The two public implementations therefore expose
  incompatible behavior for an official recoverable state.
- `JVLinkWrapper.jv_read()` replaces U+FFFD with ASCII `0` and otherwise
  unencodable text with `?`. A transport-decoding failure can therefore mutate
  a field into plausible numeric data rather than failing closed.
- A focused regression run against the candidate full SHA
  `d6f8f70e4976e053f636dc1d136a3214fa6996ad` passed:
  `python3 -m pytest -q tests/test_jvdata490_layouts.py
  tests/test_parser_compatibility.py tests/test_ra_parser_jravan.py
  tests/test_jvlink_constants.py tests/test_jvlink_wrapper.py
  tests/unit/test_jvlink_bridge.py tests/test_error_scenarios.py` (22 skipped).
  The green result is negative evidence for test adequacy because signature
  mocks, reconstructed short fixtures, and flat-layout assertions encode the
  mismatched implementation contract. `python3 scripts/validate_schema_parser.py`
  exited 1 with 7 reported mismatches and 16 errors; several are false positives
  for dynamically expanded parsers, so only independently confirmed findings
  are used in the audit conclusion.
- A second synthetic current HN record independently confirmed the 2023
  transition defect. With official current positions populated, the parser
  returned the ten-byte breeding number as only its first eight bytes, shifted
  the following fields (`DelKubun='J'`, horse name prefixed by `2`), lost both
  parent breeding numbers, and returned an empty delimiter.
- Wrote the tracked all-38 audit report at
  `specs/operations/20260815_jvdata_official_spec_compatibility_audit.md`.
  It separates current-layout coverage, historical/undocumented fallback
  shapes, the 2023 three-path retrieval contract, state-machine/API findings,
  community corroboration, and evidence gaps. No product code, schema, test,
  or fixture was edited.
- Re-fetched `origin/master` after the report draft. Local HEAD and
  `origin/master` remain
  `d6f8f70e4976e053f636dc1d136a3214fa6996ad`; GitHub has no open pull request
  for `miyamamoto/jrvltsql` at this observation point.
- Re-ran the focused audit test selection against the unchanged target SHA;
  exit 0 with 22 Windows-only skips. `git diff --check` also exits 0. These
  tests are recorded as repository-regression evidence, not official-format
  proof, for the fixture/mock reasons stated above.
- Committed the documentation-only audit as
  `2a25c85e27c236de00b7d5a03b2d88962580fed2`, pushed branch
  `codex/jvdata-official-spec-audit-20260815`, and opened PR #162:
  `https://github.com/miyamamoto/jrvltsql/pull/162`. The PR body records that
  merging this documentation does not approve the audited product code and
  that the product verdict remains RED / DO NOT RELEASE.
- Re-ran the focused audit selection on full SHA
  `2a25c85e27c236de00b7d5a03b2d88962580fed2`; exit 0 with the same 22
  Windows-only skips. `git diff HEAD^ --check` exits 0 and the worktree was
  clean before this required post-PR worklog update.

## Remaining evidence gaps

- A real 32-bit Windows/JV-Link smoke test is still required to convert the
  native pywin32 signature finding from primary-contract plus independent
  working examples into an end-to-end observation on this package.
- The official materials define current and published historical layouts, but
  the repository's short fixture records were reconstructed from database rows
  and are not preserved raw JV-Link records. Their provenance cannot establish
  an undocumented official compatibility format.
- Overseas/foreign-sale realtime-key coverage cannot be classified safely from
  the available key examples alone and is left as an explicit coverage gap,
  not reported as a defect.

## Next safe commands

- Commit and push this post-PR evidence update, then record the final candidate
  full SHA in the PR conversation (not in a self-referential commit).
- Verify PR #162 head/checks/threads once against that SHA, then merge only the
  documentation audit iteration. Do not describe that merge as approval of the
  product code; the report verdict remains RED.

## STOP conditions

- Stop before changing production code: this iteration is an audit unless the
  user separately authorizes fixes after findings are presented.
- Stop before treating a community claim as fact unless corroborated by an
  official document, staff answer, executable behavior, or a clearly labelled
  uncertainty.
- Stop and report an evidence gap where an old official specification or
  representative record cannot be obtained; do not infer dual-version support
  from current-format tests.
