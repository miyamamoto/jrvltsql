# JRA-VAN H1/H6 standard-schema state worklog

## Iteration identity

- Started: 2026-08-16 JST
- Objective: make H1/H6 vote-count records conform to the official current
  and supported historical JV-Data layouts in both native and JRA-VAN
  standard schemas, without changing existing public compatibility aliases.
- Minimal scope: H1/H6 parser-to-standard storage routing, physical
  header/child materialization, current-snapshot replacement, zero erase,
  additive schema verification, ordinary/optimized importer parity, focused
  contracts, and documentation needed to describe public behavior.
- Repository: `miyamamoto/jrvltsql`
- Dedicated worktree: scratch worktree `20260816_jrvltsql_hyosu`
- Branch: `agent/jravan-hyosu-20260816`
- Base and initial HEAD:
  `dde898c3394c24c9b781024d959c770ee7add58e`
- Base provenance: squash merge of PR #189, which completed O1-O6
  standard-schema header/child storage.
- Related released version: `v1.6.10`, targeting
  `dbb299a756e01bad4c79efd76d934c64f3d8af69`. This iteration is not yet a
  release candidate.
- Agent/model: Codex only, per user instruction; no Claude Code session is
  used for implementation or review.

## Dependency order and boundaries

1. Confirm current and immediately prior official H1/H6 physical layouts,
   status semantics, table ownership, and documented historical changes.
2. Compare parser rows, native schemas, standard schemas, table mappings, both
   importers, erase behavior, and package/docs surface against those contracts.
3. Add the smallest red-first regressions for the missing fail-closed/state
   contracts, then implement one aggregated repair.
4. Validate the frozen full SHA with affected Python 3.12 tests, fresh
   PostgreSQL, static checks, and an acquired normalized snapshot replay when
   source coverage exists.
5. Open one PR, request the single GitHub-native Copilot review, aggregate all
   findings, repair once if needed, prove unresolved threads are zero, and
   merge before the next logical iteration.

## Initial observations

- PR #189 deliberately left H1/H6 as the next release blocker because their
  standard schemas split one physical record into one header plus several
  vote-count child tables, while the existing public mapping points to legacy
  child aliases.
- The O1-O6 coupled-storage implementation is a useful transaction and
  verification pattern, but H1/H6 require their own official field transforms
  and cannot be treated as odds rows by renaming record types.
- A new provider acquisition remains a mandatory final release gate for the
  repository as a whole. Historical snapshot replay in this iteration is
  supporting storage evidence, not a substitute for that release gate.

## Current state

- Worktree is based on current `origin/master` and clean at iteration start.
- Focused red-first storage contracts have been added locally; production
  source is still unchanged. The worktree is intentionally dirty only for the
  new tests and this worklog until the red evidence is committed.

## Official current/prior contract

- The official JV-Data Ver.4.9.0.1 PDF and SDK 5.0.0 Python/C#/C++ structures
  agree on H1 as 28,955 bytes and H6 as 102,890 bytes. The repository offsets,
  entry sizes, counts, and six-part race key match those primary sources.
  Official current PDF:
  https://jra-van.jp/dlb/sdv/sdk/JV-Data4901.pdf
- The immediately prior Ver.4.8.0.2 contains the same H1/H6 record lengths,
  positions, repeat counts, status values, and key fields. No version switch is
  needed between these two supported official layouts.
- Both define `DataKubun` 2/4/5 as provided states, 9 as race cancellation, and
  0 as physical deletion caused by a provider correction. H1 contains seven
  non-trifecta arrays and 14 total/refund-total fields; H6 contains 4,896
  trifecta rows and two total/refund-total fields.
- Historical availability differs without changing the physical record:
  H1 is provided from 1986; old popularity values can use 99/999 cancellation
  sentinels; refund horse/bracket information and several refund totals are
  populated only from 2002-06-15. H6 is provided only from 2004-08-14. Blank
  pre-introduction fields therefore mean unknown/not supplied and must remain
  nullable rather than fail or be fabricated.
- The H6 release-flag description says “3連複” in both current and prior PDFs,
  but the section title, field name, 4,896 ordered combinations, and every SDK
  structure name it as 3連単. This is a long-standing documentation typo, not a
  second layout.
- The repository also accepts 317-byte H1 and 78-byte H6 flat compatibility
  records. Neither current nor immediately prior official specifications
  define those physical records. They will remain supported as a public
  compatibility input, but will not be described as an official historical
  layout.

## Community and sample-importer change audit

- The JRA-VAN developer-community thread about the official JV-Data import
  class documents a split-table state bug: child insertion was conditional on
  release flags, then header presence incorrectly selected UPDATE when a flag
  changed from 0 to 7. The inverse 7-to-0 transition also made flag-gated
  updates unsafe. Support advised not to use the release flag as the child
  update condition; the reporter selected DELETE-INSERT so newly appearing and
  disappearing combinations are both represented.
  https://developer.jra-van.jp/t/topic/64
- JRA-VAN support states in the same thread that the H1 and H6 C++/VB sample
  importers were corrected on 2024-08-07, including horizontally equivalent
  errors. This behavioral change is newer than the stable physical layout and
  is therefore part of the required compatibility audit.
- Implementation decision: always persist valid H1/H6 child combinations
  independent of the release flag, and replace the complete owned child set
  inside the same transaction as the header. This handles both pre-fix and
  post-fix sample behavior without relying on header presence to choose
  INSERT versus UPDATE.
- A current community answer also confirms that the `RACE` data spec can emit
  H1/H6 and that H1 contains final vote counts, not payouts:
  https://developer.jra-van.jp/t/topic/860
- Read-only registered-data inspection found cancellation-state H1 and H6
  physical records with many expanded combinations, not merely empty headers.
  No race identity was recorded. This supports retaining status 9 as a
  queryable header plus its supplied child set, followed only by physical
  removal on status 0.

## Confirmed implementation gap

- Public reverse mappings currently select legacy names `HYO_TANPUKU` and
  `HYO_SANRENTAN`, which have no physical schema definitions. The actual
  standard owners are `HYOSU` and `HYOSU2`; H1 owns five child tables and H6
  owns `HYOSU_SANRENTAN`.
- Generic row upsert cannot create one standard header, expand concatenated
  refund arrays into numbered header columns, merge Tansyo/Fukusyo and
  Umaren/Wide rows into their shared child tables, or remove combinations that
  disappear in a later complete record.
- Existing standard tables have no declared primary keys. The repair must add
  deterministic official-key unique indexes on clean tables and fail closed
  if duplicate existing official keys prevent safe upsert. It must also run
  additive migration on every owner and child before verification.
- The H6 parser places total fields only on expanded child rows. A valid full
  record with no combinations therefore returns a header without its physical
  totals. Totals must be attached to the base header before expansion so an
  empty replacement can clear children while preserving its own totals.

## Red-first evidence

- Against unchanged production source at HEAD
  `4337ff3aeea20e1f888d98dc9265341675d4f0b3`, the focused H1/H6 contract run
  produced `8 failed, 4 skipped, 45 deselected`.
- Both ordinary and optimized standard importers routed H1/H6 to nonexistent
  legacy alias tables instead of the physical owners. The empty full H6 record
  lost both physical totals. Existing duplicate H1 official keys did not raise
  `SchemaMigrationError`. The rollback tests could not reach their transaction
  assertion because the initial standard import already failed.
- This is the required pre-repair proof that the new owner, state-replacement,
  total-preservation, duplicate-key, and rollback checks can reject the current
  implementation. No production repair has been applied yet.

## Implementation and pre-candidate validation

- Standard-name resolution now sends H1 to physical owner `HYOSU` and H6 to
  `HYOSU2`, while every physical child table is addressable and the existing
  public reverse aliases remain unchanged.
- Both importers now materialize each physical H1/H6 record as one owner plus
  its complete owned child set. Valid combinations are persisted independently
  of release flags, Tansyo/Fukusyo and Umaren/Wide partial rows are merged by
  their official keys, and a later complete record clears combinations that
  disappeared. DataKubun 9 remains queryable and DataKubun 0 removes children
  before the owner in the same transaction.
- Owner and child schemas are migrated and verified together. Deterministic
  official-key unique indexes fail closed on existing duplicates. Successful
  verification is cached only after an importer-owned commit; a failed child
  write rolls back the owner and complete child replacement.
- Packed H1/H6 refund arrays and physical totals are translated to numbered
  standard columns. H6 now attaches its two totals to the base parsed header,
  so a complete record with no child combination retains its own totals.
- The repository's 317-byte H1 and 78-byte H6 compatibility inputs remain
  supported as complete one-row physical snapshots. They are tested but are
  not described as an official historical layout.
- The repaired focused contract first passed `15 passed, 6 skipped`; the
  expanded storage, mapping, and parser compatibility set then passed
  `255 passed, 20 skipped` on SQLite/local paths. Fatal-error Ruff selection,
  bytecode compilation, diff whitespace checks, and parser/importer syntax
  checks passed.
- A disposable fresh PostgreSQL 16 instance ran the complete expanded-record
  storage file with integration enabled: `65 passed`. It covered both
  importers, H1/H6 current snapshot replacement, cancellation/erase, duplicate
  rejection, additive child migration, rollback preservation, and the existing
  O1-O6 contracts. The instance was removed after the run.
- A read-only registered-data replay selected one cancellation-state physical
  snapshot for each record type without recording race identity. H1 expanded
  to 1,501 normalized source rows and the expected 18 horse, 36 bracket, 153
  quinella/wide, 306 exacta, and 816 trio child keys; H6 expanded to all 4,896
  ordered trifecta child keys. Both importers stored one status-9 owner plus the
  complete child sets, then removed every owner and child row on a status-0
  replay. This is stored-data evidence only; a new provider acquisition remains
  a mandatory repository release gate.

## Pre-PR Codex review repair

- The first frozen implementation SHA was
  `941c783fb90dcc36b6cbed314e1158895475dfa2`. Exact-SHA Python 3.12 affected
  tests passed `796 passed, 22 skipped, 12 subtests`; the workflow test list
  passed `893 passed, 2 skipped, 12 subtests`; fresh PostgreSQL 16 passed all
  65 expanded-storage cases; distribution contents passed. The blocking
  flake8 selection reported zero findings. The broader warning-only flake8 run
  retained repository-wide legacy warnings and was non-blocking, matching the
  workflow policy.
- A subsequent Codex boundary review found one historical positional bug before
  PR creation: full H1/H6 refund arrays used the generic trimmed decoder. If an
  early one-byte flag was blank while a later flag was populated, trimming
  shifted the later value into the wrong horse/bracket slot. A new pre-repair
  regression failed twice with `assert 1 == 28` for the ordinary and optimized
  standard paths.
- H1 now preserves all 28 horse, eight bracket, and eight same-bracket bytes;
  H6 preserves all 18 horse bytes. Standard conversion maps positional blanks
  to nullable numbered columns, including pre-introduction refund totals,
  without changing the flat compatibility layout. The focused repaired set
  passed `16 passed, 6 skipped`, and expanded storage/mapping/parser
  compatibility passed `257 passed, 20 skipped`. Because this repair changes
  source after the first freeze, SHA `941c783...` is not the PR candidate.

## Next safe action

- Commit the positional-array review repair and this evidence, freeze the new
  full candidate SHA, and rerun the focused Python 3.12 and PostgreSQL gates
  required by the source change. Then push once, open the PR, collect the
  single GitHub-native Copilot review plus configured automated reviewers,
  aggregate findings, and repair once if necessary.
