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
- Worktree: dedicated worktree for the branch below; its local absolute path is
  intentionally omitted from this tracked public record.
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

## Implementation and second red boundary

- Test-only red evidence was committed as full SHA
  `09a7b31076f33097c33dbccd8425cb7ff1bf2acb`; the worklog-start commit is
  `23ce078d10eb77045da5dbe13fc59117a40bd4df`.
- Implemented a four-character component splitter and shared validator. The
  option matrix now contains only current JVOpen selectors; every component
  must be valid for the selected option, and a legacy component anywhere in a
  concatenated request is rejected with its current replacement named.
- Applied the validator before JV-Link/bridge transmission, cache lookup,
  batch schema creation, and quickstart database setup. The command entry point
  continues to consume the same shared matrix and component-aware retirement
  predicate before database setup. Public docs now distinguish `O1`-`O6`
  record types from `RACE`, the JVOpen selector that contains them.
- Added one minimal batch-side-effect assertion after inventorying that public
  boundary. With the batch validator temporarily absent, ran only
  `test_invalid_dataspec_stops_before_schema_preparation`; result: **1 failed**
  (`DID NOT RAISE ValueError`), and the captured flow reached schema preparation
  and completed the batch. Restoring the guard made the same test green.
- Strict self-review found a second fail-open class in the new validator:
  an unhashable `option` caused `dict.get()` to raise `TypeError` while forming
  the rejection message. Added one existing-suite test and ran it before the
  repair; result: **1 failed**, with `TypeError: unhashable type: 'list'`.
  The validator now checks the option type/domain first and returns a stable
  `ValueError`, so malformed input is a rejection rather than a crash.
- Removed the obsolete quickstart allowlist that described record IDs and
  non-selectors as setup specs. The retained `--no-odds` compatibility flag is
  now documented honestly: final odds are records inside `RACE` and cannot be
  removed by filtering JVOpen selectors.

## Local verification before candidate freeze

- Central red/green set after both repairs:
  `tests/test_retired_data_specs.py tests/test_quickstart_cli.py
  tests/test_batch_processor.py`: **220 passed**.
- Transport/fetcher/wrapper/bridge/error integration set: **287 passed,
  24 skipped**. Skips are the existing platform-specific cases.
- CLI/cache/batch set run serially: **133 passed**. An earlier attempt ran this
  concurrently with `compileall` over the same files and produced two
  non-repeatable import-time CLI failures; both commands passed immediately in
  isolation and the complete set passed when rerun without concurrent
  `compileall`. A bytecode-write race is a plausible explanation, not an
  observed cause. This concurrent run is not counted as gate evidence.
- `compileall`, fatal-only flake8 (`E9,F63,F7,F82`), and `git diff --check`
  pass on the current working tree.
- Strict MkDocs build passes. A public-doc privacy scan found none of the
  prohibited internal collector/runtime names. Remaining `O1`-`O6` mentions
  were inspected and all describe record types inside `RACE` or JVRTOpen
  streams rather than standalone JVOpen selectors.

## Pre-final candidate evidence

- Implementation commit/full SHA:
  `70e490ce47ab9fa14adb0c4df40883f4c60de8a4`. A fresh fetch confirmed
  `origin/master` remained the iteration base
  `8fc0d7c3a3e10bfcd3c589cca7ec4707573c5c16`.
- Repository-wide isolated suite on that SHA: **2334 passed, 67 skipped,
  6 subtests passed**. The only warnings were three pre-existing
  `PytestReturnNotNoneWarning` instances in `tests/test_time_series.py`.
- The exact GitHub Actions test selection with coverage on that SHA:
  **890 passed, 2 skipped, 3 subtests passed**; no failures.
- Python 3.12 built a real wheel and sdist. The fail-closed distribution
  checker passed both artifacts, confirming tracked `specs/` and removed
  crawler-audit documents are absent. Strict MkDocs, fatal flake8, diff check,
  and clean worktree checks passed. The first build command was excluded
  because the host Python lacked the optional `build` module; rerunning through
  an isolated Python 3.12 build environment succeeded without changing project
  dependencies.
- A bounded authenticated acquisition smoke staged this exact committed source
  and verified its `src/jvlink/constants.py` hash before the call. Under the
  acquisition service's non-blocking lock, standalone `O1` was rejected before
  transmission; `RACE` then opened successfully, yielded a real byte-count-
  consistent record, the exact candidate parser parsed it, and explicit
  `JVClose` succeeded. No credentials, payload, record/race identity, filename,
  machine identity, or environment value was printed or stored.
- The first harness launch was excluded because the disposable source directory
  was not writable and logger setup stopped before provider initialization.
  After correcting only disposable-directory ownership, the bounded smoke
  passed. Disposable source/archive files were removed; the service lock was
  free afterward and the development acquisition environment remained healthy.

## Aggregated review repair

- PR #187 was opened at candidate
  `accc5f9f0b9ca9c2845a3fcf4c1660bfc3dee940`. GitHub Actions test/lint
  passed, and one GitHub-native Codex review plus the configured optional
  CodeRabbit review were allowed to finish before any repair.
- Codex found that the `cache build` and `cache rebuild` commands validated too
  late. A stale `O1` cache created by an older release could make `build`
  return `[CACHED]`, while `rebuild` could delete that cache before the fetcher
  rejected the non-selector. This is actionable because it violates both the
  shared contract and the pre-side-effect guarantee.
- Extended the existing CLI contract test with one parameterized build/rebuild
  case. Before production repair it failed **2 cases**: build returned exit 0,
  and rebuild removed the complete cache. This is the required negative proof
  for the newly repaired cache-command guard.
- Added one CLI rendering helper around the shared validator and called it at
  the start of both cache commands, before cache-manager construction, lookup,
  or deletion. Retired-selector diagnostics remain stable, and valid option-2
  requests still reach the existing cache-specific usage rejection.
- CodeRabbit independently flagged the worklog's local absolute worktree path
  as unnecessary public environment disclosure. Replaced it with the dedicated
  branch identity while preserving the worktree handoff contract.
- Focused review-repair selection (JVOpen contract, CLI, cache, quickstart,
  batch, and historical cache tests): **291 passed**. Compileall, fatal flake8,
  strict MkDocs, and diff check also passed. No Claude session or code was used.

## Next safe command

- Commit and push the aggregated repair once, repeat the focused/local,
  distribution, and acquisition gates on the resulting full SHA, reply to and
  resolve both review threads, then merge only after CI and final state are
  green.
