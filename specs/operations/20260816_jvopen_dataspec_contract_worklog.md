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

## Official and community evidence

- Current official artifact: JRA-VAN Data Lab SDK 5.0.0 64-bit archive,
  SHA-256
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`.
  Its embedded `JV-Link` 4.9.0.1 PDF, `JV-Data` 4.9.0.1 PDF, and `JV-Data`
  4.9.0.1 workbook independently match the prior official downloads at
  SHA-256 `dfd1c425a62304bb464f15c25106e030ffccbf99c7c777972d6bb6b6d27ef1d7`,
  `b6c21aae4ccbba6a71c5e8065609c4fbb1ccee826c16e7d99ca6ecf7a4101522`,
  and `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`.
- The controlling JV-Data option matrix lists, after applying this repository's
  current-layout-only policy, twelve current IDs for options 1/3/4:
  `TOKU,RACE,SLOP,WOOD,YSCH,HOYU,COMM,MING,DIFN,BLDN,SNPN,HOSN`; and five
  for option 2: `TOKU,RACE,TCVN,RCVN,SNPN`. `O1` through `O6` appear under
  the records contained in `RACE` and JVRTOpen streams, not as JVOpen IDs.
- The JV-Link interface contract states that each dataspec ID is exactly four
  characters and permits one or more IDs concatenated into a string whose
  length is a multiple of four. This makes whole-string retirement checks
  insufficient: every component must be validated independently.
- Official web and community recheck on 2026-08-16 found no superseding matrix.
  The 2023-08-08 official update notice says the option/dataspec matrix changed
  for the new layouts. A 2026 JRA-VAN staff announcement again directs post-
  boundary DIFF consumers to `DIFN`. The community software-registration
  guidance uses concatenated four-character IDs in JVOpen examples. These
  community observations corroborate but do not replace the SDK contracts.

## Confirmed base gaps and red-test design

- `JVOPEN_VALID_COMBINATIONS` contains six record IDs (`O1`-`O6`) in options
  1/3/4. `is_valid_jvopen_combination()` compares only the complete string, so
  it rejects valid concatenated current requests. Conversely,
  `is_retired_data_spec()` compares only the complete string, so a retired
  component can be hidden before or after a current ID.
- The direct fetcher, native wrapper, and bridge apply only the incomplete
  retirement predicate; record IDs and option mismatches can reach JV-Link.
  Quickstart has an additional stale option-4 allowlist containing record IDs
  and unrelated non-dataspec labels, and checks the shared matrix only for
  option 2.
- Extended the existing central and public-boundary tests rather than creating
  a parallel matrix suite. The negative cases require `O1` and `RACEDIFF` to
  stop before JV-Link/database side effects; the paired positives require
  official concatenated current IDs to remain accepted. These test-only changes
  must be run against the base before any production edit.

## Red-first evidence

- With only the tests/worklog changed, ran
  `python3 -m pytest -q -o addopts='' --basetemp=<scratch>
  tests/test_retired_data_specs.py tests/test_quickstart_cli.py` against the
  base production code. Result: **14 failed, 181 passed** (exit 1).
- The failures partition exactly by the intended contract:
  - two mixed legacy requests (`DIFFRACE`, `RACEDIFF`) were not recognized;
  - the allowlist disagreed with the official current matrix;
  - four valid concatenated current requests were rejected centrally;
  - fetcher, native wrapper, and bridge each allowed both a record ID and a
    mixed legacy request to reach the JV-Link boundary (six failures);
  - quickstart entered database setup for `O1` instead of returning an invalid
    dataspec result.
- Existing paired positives remained green within the same run. This proves
  the changed check can say no and the positive harness still reaches the
  current valid path before production implementation.

## Next safe command

- Commit the test-only red evidence, then implement a four-character component
  parser and one shared fail-closed JVOpen validator. Reuse it before JV-Link,
  cache/database, and quickstart side effects; remove record IDs from the
  option matrix and correct the public dataspec documentation.
