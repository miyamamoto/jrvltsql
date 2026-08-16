# YS current-layout implementation worklog

## Iteration identity

- Objective: replace the partial YS schedule implementation with the complete
  official current physical layout and keyed update/delete semantics.
- Minimum scope: YS parser, native/standard schemas and metadata, accumulated
  importer behavior, fixtures/tests, and the tracked compatibility audit. No TK
  or release/publication change is included in this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260816_jrvltsql_ys_layout`
- Branch: `agent/ys-current-layout-20260816`
- Base/full SHA: `609f9c4ee3571857367781f4cc8d7e3630a0e9e0`
- Previous dependent merge: PR #183, RC official-layout merge
  `609f9c4ee3571857367781f4cc8d7e3630a0e9e0`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release/publication iteration.
- Agent/model: Codex only. No Claude session is used.

## Official and community evidence

- Official JV-Data 4.8.0.2 and 4.9.0.1 both define YS as exactly 382 bytes:
  bytes 1-26 are the header/race identity/weekday, bytes 27-380 are three
  118-byte graded-race guidance blocks, and bytes 381-382 are CR/LF.
- SDK 5.0.0 independently allocates a 382-byte buffer and loops three times at
  `27 + 118 * i`. Each block has twelve fields at relative positions 1, 5, 65,
  85, 97, 103, 106, 107, 109, 112, 113, and 117.
- The five official key fields are `Year`, `MonthDay`, `JyoCD`, `Kaiji`, and
  `Nichiji`. The three guidance slots belong to one schedule row and are not
  independent database identities.
- Current `DataKubun` meanings are `1` year-end plan, `2` immediately-before
  plan, `3` completed/finalized meeting, `9` cancelled meeting, and `0` deletion
  of an erroneous identified row. Values `1/2/3/9` must therefore upsert the
  complete row; only `0` is a physical exact-key deletion.
- Official developer-community topic 323 reports an apparent loss of July to
  December YSCH rows. Support reproduced complete annual delivery and the user
  found that incorrect `JVGets` separator handling doubled apparent records,
  causing the reader to stop halfway. This is acquisition-loop evidence, not an
  alternative YS physical layout: parser/storage tests must keep exactly one
  CR/LF terminator and the eventual live release gate must check annual coverage.
- The repository's 146-byte shape ends after the first 118-byte guidance block
  and treats bytes 145-146 as CR/LF. No official source supports that truncation.
  A separate generic test expectation of 424 bytes is also contradicted by both
  specifications and SDK 5.0.0.

## Decisions before implementation

- Accept only exact 382-byte `YS` records with strict CP932 and CR/LF framing;
  reject 146, 424, short, long, wrong-type, and malformed-delimiter inputs.
- Flatten all three official guidance blocks into one native/standard row,
  matching the existing standard field naming pattern.
- Preserve the official five-column key in native `NL_YS` and add it to standard
  `SCHEDULE`. Existing keyless/partial storage must fail closed before mutation;
  no automatic primary-key reconstruction is safe without collision review.
- Validate every row before beginning mutation, apply schedule records in
  provider order, and batch only consecutive upserts around exact-key deletes.

## Plan and gates

- Add one minimal official contract and run it red against the unchanged
  implementation, including malformed framing, missing blocks/schema/key,
  unsupported status, incomplete key, delete order, and old-table fail-closed
  behavior.
- Implement parser/schema/importer changes once, then run focused, full,
  workflow-equivalent, and disposable PostgreSQL validation on the exact SHA.
- Request one GitHub-native Copilot review, aggregate all findings, require
  unresolved threads zero, green CI, clean worktree, and tree-equivalent merge.
- STOP on conflicting official evidence, unsafe migration, executable failure,
  base drift, or an unresolved actionable review finding.

## Next safe command

- Run the complete local suite on Python 3.12 after installing the locked
  development dependencies in this worktree. STOP if any existing parser,
  importer, schema, or migration contract regresses.

## Implementation and validation history

- The starting worklog was committed as
  `f3315a17d4b56ab71befc7c77f6c020d51970c9f` before production changes.
- Added one consolidated YS official-contract module covering the exact 46-field
  physical layout, malformed framing/encoding, both schemas and importers,
  statuses 1/2/3/9, exact-key status 0 deletion, pre-mutation validation,
  provider-order batching, obsolete storage, and optional PostgreSQL behavior.
- Red-first command against the pre-implementation production code:
  `python3 -m pytest -q --no-cov --basetemp=$WORKSPACE/20260816_jrvltsql_ys_red tests/test_ys_official_contract.py`.
  Result: `29 failed, 2 skipped`; representative failures were `146 != 382`,
  accepted invalid boundaries, missing guidance 2/3 schema fields, missing
  standard primary key, unsupported status not rejected, valid rows committed
  before malformed rows, deletion treated as an upsert, and obsolete storage not
  failing closed. This demonstrates that the new validator could say no before
  implementing it.
- Implemented an exact 382-byte strict parser, complete native/standard schemas,
  schema-backed schedule metadata, and dedicated YS schema verification/writer
  paths in both importers. Every logical batch is validated before mutation;
  statuses 1/2/3/9 are consecutive upserts and status 0 is an ordered exact-key
  delete. Obsolete ordered-master tables no longer block unrelated standard
  imports, but fail closed when their own rows are written.
- Historical 146-byte fixture handling is explicitly synthetic: only its
  position-compatible 144-byte prefix is padded into a 382-byte current record.
  Production parsing accepts no legacy length.
- Focused green command after implementation:
  `python3 -m pytest -q --no-cov --basetemp=$WORKSPACE/20260816_jrvltsql_ys_green2 tests/test_ys_official_contract.py`.
  Result: `29 passed, 2 skipped`.
- Broader affected-surface command across parser, fixture, schema, and importer
  suites: `809 passed, 3 skipped` using system Python 3.10.12. Formal candidate
  evidence remains pending on the repository-supported Python 3.12 environment.
- Created a worktree-local Python 3.12.11 environment with `.[dev,postgres]`.
  The repository dev extra does not declare `python-dotenv` or `flake8`, so both
  were added to this local environment only for full-suite collection and the
  workflow-equivalent fatal lint check.
- A first Python 3.12 full run reached `2276 passed, 65 skipped` but reported two
  CLI exit-code failures. Both CLI tests immediately passed alone and in their
  preceding file-order surface without a code or environment change. A complete
  rerun then passed `2278 passed, 65 skipped, 3 warnings, 6 subtests`; the three
  warnings are the pre-existing `test_time_series.py` return-value warnings.
  This transient run is not used as candidate evidence; the exact committed SHA
  must pass again.
- Disposable PostgreSQL 16 validation passed all `31` YS tests, including both
  native/standard storage modes and both importers. The workflow-selected local
  suite passed `864 passed, 2 skipped, 3 warnings, 3 subtests`, and fatal flake8
  (`E9,F63,F7,F82`) reported `0`.
- Current worktree is intentionally dirty with the uncommitted candidate. No PR,
  merge, release, or provider acquisition has been claimed for this iteration.
