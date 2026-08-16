# YS current-layout implementation worklog

## Iteration identity

- Objective: replace the partial YS schedule implementation with the complete
  official current physical layout and keyed update/delete semantics.
- Minimum scope: YS parser, native/standard schemas and metadata, accumulated
  importer behavior, fixtures/tests, and the tracked compatibility audit. No TK
  or release/publication change is included in this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_ys_layout`
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

- Commit this starting worklog, inspect every existing YS mapping/fixture, then
  add and run the official contract red before changing production code.
