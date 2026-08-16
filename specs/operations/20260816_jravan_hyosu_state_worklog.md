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
- No source or test changes have been made yet.
- Next safe action: inspect repository H1/H6 layouts and standard schemas, then
  verify the current and prior official specifications and relevant public
  community reports before writing regressions.
