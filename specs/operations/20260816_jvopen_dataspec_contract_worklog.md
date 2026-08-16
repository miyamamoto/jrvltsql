# JVOpen dataspec contract worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: reconcile every public JVOpen dataspec/option guard with the
  current official JV-Link contract, while preserving explicit rejection of
  pre-change legacy layout selectors.
- Minimum scope: official/current and legacy dataspec inventory, the shared
  combination table, fetcher/wrapper/bridge/CLI entry boundaries, one minimal
  red-first regression contract, focused tests, and a bounded authenticated
  provider smoke if the final change can affect acquisition. Parser layouts,
  cancellation semantics, release versioning, and publication are separate
  iterations.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_jvopen_dataspec`.
- Branch: `agent/jvopen-dataspec-contract-20260816`.
- Base/initial HEAD/origin master full SHA:
  `8fc0d7c3a3e10bfcd3c589cca7ec4707573c5c16`.
- Dependency: public documentation/distribution PR #186 merged as that base
  SHA; candidate and squash-merge trees were identical.
- Production/release version at start: tag and project version `v1.6.10` /
  `1.6.10`. This iteration does not release.
- Agent/model: Codex only. No Claude session or external coding agent is used.

## Plan and gates

- Locate and read the authoritative SDK definitions/version history first;
  distinguish JVOpen dataspec selectors from record type IDs yielded by a
  selected stream and from JVRTOpen selectors.
- Inventory every code and documentation entry point. Do not turn unsupported
  legacy selectors into aliases: selectors that request old physical layouts
  remain fail-closed with their current-layout replacement named.
- Add the smallest regression test that fails against this base, record the
  actual red output, then implement one shared contract consumed at all public
  JVOpen boundaries. Pair rejection with accepted official combinations.
- Run focused transport/CLI/fetcher tests, the necessary broader suite, strict
  docs/lint, and—if acquisition behavior changes—a bounded authenticated smoke
  using the exact candidate without mutating collector identity or production
  state.
- Open one PR, request one GitHub-native Copilot review, aggregate findings,
  require successful CI, unresolved threads zero, clean worktree, and exact
  local/remote candidate equality before merge.
- STOP on ambiguous official evidence, a current selector rejected by the new
  guard, a record-type ID reaching JVOpen as a selector, base drift, failed
  acquisition cleanup, or any unresolved actionable review finding.

## Starting observation

- Read-only inspection at the base shows `JVOPEN_VALID_COMBINATIONS` includes
  the odds record type IDs `O1` through `O6` as if they were JVOpen dataspecs.
  Realtime selectors such as `0B30` yield these record types through JVRTOpen;
  the official source must be checked before this observation is promoted to a
  finding or changed.

## Next safe command

- Locate the official SDK contract and prior tracked audit references, record
  source/version evidence, then write and execute the base-failing combination
  test before editing production code.
