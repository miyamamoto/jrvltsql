# RC current-layout implementation worklog

## Iteration identity

- Objective: replace the partial RC course-record implementation with the
  complete official current physical layout and a lossless keyed storage
  contract.
- Minimum scope: RC parser, native/standard schemas and mappings only where the
  official record requires them, accumulated importer behavior, fixtures/tests,
  support documentation, and audit evidence. No TK/YS or release change is in
  this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_rc_layout`
- Branch: `agent/rc-current-layout-20260816`
- Base/full SHA: `79833980f8a7f0cc09c2a308a50a512091e5565b`
- Previous dependent merge: PR #182, KS official-layout merge
  `79833980f8a7f0cc09c2a308a50a512091e5565b`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release/publication iteration.
- Agent/model: Codex only. No Claude session is used.

## Starting observations

- The tracked audit marks RC as partial: the parser accepts 241 bytes while
  JV-Data 4.9.0.1 documents 501 bytes.
- The current parser stores one complete holder block, two bytes of the second
  horse identifier, then treats bytes 240-241 as CR/LF. It therefore cannot
  represent all three official record-holder blocks or prove record framing.
- Official JV-Data 4.8.0.2, 4.9.0.1, SDK 5.0.0 structures, and relevant official
  developer-community corrections must be compared before deciding whether any
  historical/current dual-layout support is legitimate.

## Official and community evidence

- Primary official JV-Data 4.8.0.2 (2023-02-15) and 4.9.0.1 (2024-08-07)
  both define RC as exactly 501 bytes. In both, bytes 1-109 are the header and
  record attributes, bytes 110-499 are three 130-byte record-holder blocks, and
  bytes 500-501 are CR/LF. The 4.9 changes do not list an RC physical-layout
  transition, so the repository's 241-byte shape is not an official old layout.
- SDK 5.0.0 independently agrees: `JV_RC_RECORD.SetDataB` allocates 501 bytes,
  extracts `SyubetuCD` at 94/2, `Kyori` at 96/4, `TrackCD` at 100/2, and loops
  three times over `RECUMA_INFO` at `110 + 130 * i` before CR/LF at 500/2.
- The official table marks eleven key fields: `RecInfoKubun`, the six race-ID
  fields, `TokuNum`, `SyubetuCD`, `Kyori`, and `TrackCD`. `TokuNum` is the G1
  discriminator; course-record rows retain its documented numeric initial value.
- The official developer-community archive topic 39 reports a concrete database
  construction error where G1 (`RecInfoKubun=2`) rows appeared missing. After
  correcting the code/key handling, both record-identification classes were
  present (the archived 2022 example reports 1,906 course and 117 G1 rows).
  This reinforces that a permissive or incomplete database key is data loss, not
  a harmless schema preference.
- The format documents `DataKubun=0` as deletion of the identified record. The
  importer must therefore apply upserts and deletions in provider order and must
  verify the full primary key before any mutation.
- The 2005-09-29 Ver.2.1.3 history explicitly says RC's former `DataKubun=1/2`
  variants were unified to current `1`. Because this was a semantic transition,
  not a 501-byte physical-layout change, legacy `2` must remain a non-delete
  upsert while current `1` and deletion `0` retain their documented behavior.

## Decisions before implementation

- Support only the evidenced 501-byte RC physical layout and reject 241-byte,
  short, long, wrong-type, non-CR/LF, and invalid-CP932 records.
- Dispatch `DataKubun=0` to keyed deletion and both current `1` and legacy `2`
  to keyed upsert, preserving compatibility across the documented 2005 change.
- Flatten all three official holder blocks into the existing one-row RC model;
  a child table adds no cardinality because the provider caps tied holders at
  three inside one physical master record.
- Replace `SyubetuCD_TrackCD` with the separate official fields and require the
  full eleven-column primary key for both `NL_RC` and standard `RECORD`.
- Existing tables with the obsolete/keyless primary key are unsafe to migrate
  additively. Import must fail closed without changing their rows; an operator
  can perform an explicit data-preserving key migration after collision audit.

## Red-first evidence

- Before changing production code, added `tests/test_rc_official_contract.py`
  and ran it with Python 3.12:
  `.venv/bin/python -m pytest -q --no-cov --basetemp=/home/keiba/scratch/20260816_jrvltsql_rc_layout_pytest_red tests/test_rc_official_contract.py`.
- Result: **20 failed**. Representative failures were
  `assert RCParser.RECORD_LENGTH == 501` (`241 == 501`), all malformed-boundary
  cases being accepted, missing `SyubetuCD`/holder-3 schema columns, and
  `Failed: DID NOT RAISE SchemaMigrationError` for obsolete primary keys.
  This proves both the new boundary check and the storage-key validator can say
  “no” on the unchanged implementation.

## Implementation and pre-candidate validation

- Replaced the permissive 241-byte parser with a strict 501-byte parser. It
  separates `SyubetuCD` and `TrackCD`, reads all three 130-byte holder blocks,
  and rejects wrong length/type/CRLF and undecodable CP932.
- Expanded native `NL_RC` and standard `RECORD` to all 49/48 stored parser
  fields respectively, retained raw four-byte time and three-byte holder weight
  text, and declared the official eleven-column primary key in both schemas.
- Added a schema verifier before either importer can mutate RC storage. Additive
  startup migration cannot safely change primary keys or existing numeric time /
  weight columns, so old or keyless tables fail closed with their rows intact.
- Added an ordered RC writer shared by `DataImporter` and
  `OptimizedDataImporter`: `0` deletes exactly one full official key; current
  `1` and pre-Ver.2.1.3 legacy `2` upsert. Every row/key is validated before the
  transaction starts.
- Updated reconstructed-fixture handling, parser-length compatibility checks,
  schema metadata/index descriptions, and the tracked compatibility audit. The
  old 241-byte binary fixture is used only to synthesize a current-shape test
  record from its compatible 93-byte prefix; it is never accepted by production.
- Focused SQLite tests after implementation: 392 passed, 1 skipped. A broader
  metadata/index selection initially found that five newly documented RC key
  names lacked metadata column definitions; these were added, after which that
  selection passed 38 with 4 optional PostgreSQL skips.
- Disposable PostgreSQL 16 validation, both importers and both table-name modes:
  `tests/test_rc_official_contract.py` passed 22/22, including legacy-2 upsert,
  exact-key delete, distinct-key coexistence, and third-holder round trip.
- The first full-suite run exposed three obsolete `tests/test_parsers.py` RC
  sample assumptions (1,926 bytes and no CR/LF); they were corrected to 501 and
  strict CR/LF. Two CLI tests also failed only in that full-run process but
  passed 429/429 when rerun with their parser suite. The complete rerun then
  passed: **2,241 passed, 63 skipped, 6 subtests passed** (three pre-existing
  pytest return-value warnings).
- `scripts/validate_schema_parser.py --all` is not used as RC evidence: its
  static AST collector cannot expand dynamic f-string fields and reports the
  same false mismatch class for RC as for existing CH/KS repeated blocks. The
  executable 49-field gap-free contract and storage round trips are authoritative.
- Workflow-fatal flake8 selection passed with zero findings; `git diff --check`
  passed.

## PR review correction

- Opened PR #183 from implementation SHA
  `1af0bea142deaaf71576e399bd5728a353a1ce19`. A local final-diff review found
  the module-level schema documentation still named the obsolete seven-column
  RC key; the executable schema was already correct. The documentation-only
  candidate `7333d5017104a336efa49338356cb3901d244b77` passed the full 2,241-test
  suite, the 864-test workflow selection, 22 PostgreSQL RC tests, compileall,
  fatal flake8, and clean-worktree checks before push.
- One GitHub-native Copilot review was requested at PR creation. Codex,
  Copilot, and CodeRabbit findings were collected before changing the candidate.
  Actionable findings were: an obsolete unused standard `RECORD` table blocked
  unrelated standard imports during global startup verification; generic key
  filtering removed malformed RC rows before the fail-closed validator; the
  legacy-2 same-key replacement contract was not directly tested; consecutive
  upserts were written one statement at a time; and MCP metadata advertised the
  wrong `Kyori` type and a formatted rather than raw `RecTime` example.
- Before the review fixes, the new focused regression selection ran against the
  unchanged candidate and failed **6 cases**: both importers committed the one
  valid row instead of raising on an incomplete deletion key, both emitted
  upsert batch sizes `[1, 1, 1]` rather than `[2, 1]` around a delete, and both
  stopped an unrelated HN standard import because the unused `RECORD` key was
  obsolete. This is the required red evidence for the revised checks.
- The aggregated correction routes every RC row to the RC validator, verifies
  standard `RECORD` only when RC is actually written, batches only consecutive
  upserts and flushes at every delete boundary, adds a same-key legacy-2
  replacement assertion, and aligns exported metadata. The first focused green
  run passed **70 tests with 2 optional PostgreSQL skips**.
- The unsupported-`DataKubun` validator branch also lacked a direct negative
  contract. A minimal test for value `9` was added; with that rejection branch
  temporarily disabled, both importer cases failed with `DID NOT RAISE` and
  persisted the row. Restoring the allowed set to `0/1/2` produced a final
  focused result of **72 passed with 2 optional PostgreSQL skips**.

## Plan and gates

- Extract every RC offset, repeated-holder field, key, initial value, and
  version-history transition from primary sources and compare all existing
  schema/parser names.
- Inspect official developer-community reports for RC corrections, record
  holder cardinality, deletion/replacement order, and historical layout
  variants.
- Add a minimal official contract against unchanged production code and run it
  red before modifying parser/storage checks.
- Implement one current contract, or explicit old/current dispatch only when
  official evidence establishes multiple physical layouts.
- Validate the exact full SHA with supported Python, full/focused tests,
  disposable PostgreSQL where schema/storage changes require it, one native
  Copilot review, unresolved threads zero, green CI, and a clean worktree.
- STOP on conflicting official evidence, unsafe migration, executable failure,
  base drift, or an unresolved actionable review finding.

## Next safe command

- Review and commit the aggregated PR feedback once, then rerun focused/full,
  workflow-equivalent, and disposable PostgreSQL validation against the new
  exact full SHA. Push once, resolve all review threads with evidence, and merge
  only with green CI, zero unresolved threads, and a clean worktree.
