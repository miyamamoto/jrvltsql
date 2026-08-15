# JVOpen runtime gap remediation worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: diagnose the authenticated `JVOpen(RACE)` 120-second timeout,
  re-audit the merged public client against current and legacy official JV-Link
  contracts plus the deployed Wine runtime, implement only proven gaps, run
  focused and real-environment tests, obtain strict Codex review, and merge a
  complete PR.
- Minimum scope: JV-Link process launch and JSON transport, `JVInit`, `JVOpen`,
  `JVStatus`, `JVRead`, `JVClose`, compatibility envelopes, timeout cleanup,
  and the smallest directly affected fetcher paths.
- Repository: `miyamamoto/jrvltsql`
- Worktree:
  `/home/keiba/scratch/20260815_jrvltsql_jvopen_runtime_gap`
- Branch: `agent/jvopen-runtime-gap-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `1fbcb09c049b4fa0ad09c350cc74dd2093a855cb`
- Related release: `v1.6.10`; PRs #161-#164 are merged and unreleased.
- Dependency order: official/community contract audit, local contract tests,
  isolated authenticated development-collector smoke, then PR review/merge.
- Reviewer: Codex. Claude Code and external coding agents are not used.

## Initial state

- KPS read-only status was checked with
  `python3 scripts/system_status.py --json --skip-remote --sections git`.
  KPS was clean and current; the unrelated jrvltsql-nar checkout warning is
  outside this public jrvltsql iteration.
- `origin/master` was fetched before worktree creation and matched the base SHA
  above.
- PR #164 proved a real authenticated
  `JVInit -> JVRTOpen(0B30) -> JVRead(962 bytes) -> JVClose` path and the
  `JVOpen(MING)=-1 -> JVClose=0` obligation. Successful-data
  `JVOpen(RACE) -> JVStatus -> JVRead` remained unproven because both the exact
  merge-SHA harness and deployed Wine-aware client timed out at 120 seconds.

## Official and community recheck

- The current official SDK page still publishes JV-Link SDK `4.9.0.2`
  (2024-08-07) and JV-Link/JV-Data specifications `4.9.0.1`:
  <https://jra-van.jp/dlb/sdv/sdk.html>.
- The cached official `JV-Link4901.pdf` was re-read for `JVOpen`, `JVStatus`,
  `JVRead`, and `JVClose`. `JVOpen` validates the request, obtains the server
  file list, compares local files, starts the download thread, and then returns
  to the application. Therefore a 120-second silence before the JSON bridge
  emits an open response is not a successful large-download wait; download
  progress belongs to `JVStatus` after `JVOpen` returns.
- The official 2023 change notice and the July 2026 developer announcement were
  checked again. They confirm the 2023 format boundary and that DIFF after
  2023-08-08 is exposed as `DIFN`; this runtime iteration does not alter those
  parser contracts:
  <https://jra-van.jp/dlb/sdv/ml/20230808a.html>,
  <https://developer.jra-van.jp/t/topic/898>.
- Current community/staff reports were checked for `JVOpen` ordering and
  dialogs. Reports cover invalid FromTime `-112`, RACE retrieval behavior,
  missed records when reading before `JVStatus` completes, and a blocking
  `JRA-VANからのお知らせ` dialog. Staff recommends disabling the notice in
  JV-Link settings:
  <https://developer.jra-van.jp/t/topic/807>,
  <https://developer.jra-van.jp/t/topic/832>,
  <https://developer.jra-van.jp/t/topic/773>,
  <https://developer.jra-van.jp/t/topic/342>.

## Reproduction and root cause

- The public `src/jvlink/bridge.py` launched a Windows `.exe` directly and had
  no Wine command/environment path. The deployed collector client had a
  separate Wine-aware implementation, but its dialog watcher matched only
  `JRA-VANからのお知らせ` and activated the default button with `Return`.
- Under the development collector's non-blocking service lock, the deployed
  bridge reproduced `JVInit=0` followed by no `JVOpen(RACE)` response. During
  the blocked COM invocation, an X11 window owned by `JVLinkBridge.exe` was
  observed with exact title `JRA-VAN DataLab.`, geometry `476x120`, and a
  prompt asking whether to download the new version. Its default focused
  button was affirmative. No secret, record payload, filename, race key, or
  registry value was captured or retained.
- The first bounded diagnostic intentionally timed out after 45 seconds and
  cleaned up. A second call installed a test-only exact-title watcher that
  sent `Escape`, not `Return`. It rejected one prompt, after which the same
  `JVOpen(RACE, 20260808000000, option=1)` returned in about 0.8 seconds with
  `code=0`, `readcount=30`, and `downloadcount=30`. This isolates the root
  cause to a missed blocking update prompt rather than download volume or
  `JVStatus` ordering.

## Red-first contract evidence

- Before changing production code, six focused tests were added and run
  against base SHA `1fbcb09c049b4fa0ad09c350cc74dd2093a855cb`:
  `pytest -q tests/unit/test_jvlink_bridge.py -k 'environment_override or
  builds_a_wine_command or fails_closed_when_wine_is_missing or
  known_update_dialog or wine_preamble or timeout_aborts' --no-cov`.
- Result: **6 failed**. The failures showed that the environment bridge path
  was ignored, no Wine command/fail-closed check existed, no safe dialog
  rejection existed, Wine preamble/BOM output was rejected, and a response
  timeout left the stuck process running.
- A paired normal case was retained or added for every changed boundary: Wine
  present/missing, known dialog/default-disabled watcher, valid JSON after
  runtime preamble, normal response/timeout abort.
- Strict Codex boundary review then identified five additional fail-closed
  requirements before candidate freeze: scope X11 operations to the bridge PID,
  reject non-finite watcher intervals, require the official `JVInit` result
  code, close the temporary stderr stream on abort, and abort after a broken
  stdin pipe. Eight focused cases covering those branches were run before the
  repair and **8 failed** (four interval values plus four distinct contracts).
  After one repair batch the same command selection passed **8/8**.

## Implementation and current validation

- `src/jvlink/bridge.py` now discovers the bridge through the deployed
  environment contract, launches it through Wine on non-Windows platforms,
  passes the existing Wine prefix/architecture contract, drains stderr to a
  temporary file, tolerates non-JSON Wine preamble plus UTF-8 BOM, and aborts a
  process when the response stream is timed out or no longer trustworthy.
- The Wine watcher uses exact known title patterns and sends only `Escape`.
  It does not press the affirmative default button. It is limited to Wine with
  an X display and `xdotool`, and can be disabled with
  `JVLINK_AUTO_CLOSE_DIALOGS=0`.
- Focused unit and official transport-contract validation passed:
  `pytest -q tests/unit/test_jvlink_bridge.py
  tests/test_jvlink_transport_contract.py --no-cov` -> **84 passed**.
- The exact modified public `src/` tree (bridge content SHA-256
  `c8ab955195deacb668a285eca3c810c5907f254771440d80b14b92260ea700a6`)
  was staged in the running development collector and executed as UID/GID
  `1001:1001` under its non-blocking service lock. Sanitized result:
  `JVInit=0`; one known update prompt rejected; `JVOpen=0`, `readcount=30`,
  `downloadcount=29`; `JVStatus=29`; first `JVRead=80` with an 80-byte payload;
  legacy runtime `JVClose` acknowledgement accepted as `0`; total about 2.2
  seconds.
- After the smoke, the lock was available, no bridge/agent process remained,
  the collector was healthy, and disposable staged source plus the diagnostic
  screenshot were deleted.
- A second exact modified-source smoke after PID scoping and strict `JVInit`
  validation used bridge content SHA-256
  `f5f0ca40692eeaf71ce1ed27fcac88945909222c8e3395e3bcee99e41f84c032`.
  It rejected one prompt owned by that bridge PID and completed
  `JVInit=0 -> JVOpen=0/readcount=30/downloadcount=0 -> JVRead=80 bytes ->
  JVClose=0` in about 0.81 seconds. The zero download count was expected after
  the earlier bounded call populated the local JV-Link cache; it was not used
  as substitute evidence for the earlier positive-count `JVStatus=29` pass.
- Final pre-commit focused validation:
  `pytest -q tests/unit/test_jvlink_bridge.py
  tests/test_jvlink_transport_contract.py --no-cov` -> **91 passed**;
  `mypy src/jvlink/bridge.py --follow-imports=skip --ignore-missing-imports
  --no-strict-optional` -> **success**; flake8 syntax/undefined-name selection,
  compileall, and `git diff --check` -> **success**.
- The README-prescribed local suite was run alone after an initially invalid
  parallel run exposed the repository's shared `.pytest-tmp` collision. The
  valid isolated command
  `pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/` passed
  **1824 tests**, skipped 38 environment-specific tests, passed 5 subtests, and
  emitted only three pre-existing `PytestReturnNotNoneWarning` warnings.

## Codex review verdict before candidate freeze

- P0: none. This change does not alter race data contents, parser offsets,
  labels, odds timing, or model inputs.
- P1 findings found and fixed in one batch: unsafe default-button activation;
  title-only X11 scope; non-finite watcher interval; timeout/broken-pipe process
  leakage; missing `JVInit` result-code acceptance.
- P2: public Windows support remains the primary documented user contract;
  the separately required Wine provisioning boundary and opt-out setting are
  now documented without exposing deployment secrets.
- Residual compatibility note: the deployed native bridge still acknowledges
  `JVClose` without its official Long result field. The already-merged client
  compatibility envelope accepts that exact legacy acknowledgement with a
  warning. This PR neither broadens nor reports that legacy envelope as an
  official response.
- Verdict: **GREEN for candidate freeze**, subject to tests, authenticated smoke,
  GitHub checks, Copilot review, and unresolved-thread count on the exact
  committed full SHA.

## Safety and evidence rules

- Never expose service keys, database URLs, registry contents, machine
  identity, race keys, filenames, or record payloads.
- Use the development collector's own non-blocking service lock for every
  authenticated call; do not overlap a scheduled collection.
- Do not restart the collector, mutate Wine/JV-Link identity, perform setup
  downloads, or request an unbounded historical interval merely to obtain a
  passing result.
- Distinguish exact public-repository code, a test-only Wine launcher adapter,
  the separately deployed runtime client, and the native bridge binary.
- A timeout, missing response, unreadable value, or cleanup failure is not a
  pass. Any new or changed validator must first be shown failing on the
  pre-fix code and must retain a paired passing case.

## Next safe command

Commit the reviewed diff, run focused and full tests plus the authenticated
smoke on that exact full SHA without changing tracked files, publish the PR,
record SHA-bound evidence in PR metadata, resolve every actionable review
thread, and merge only after the final gate is green.

## STOP conditions

- Stop authenticated calls if the service lock is busy, the target is not the
  development collector, or another bridge/agent owns the stream.
- Stop implementation if the suspected gap is not supported by official
  documentation, current runtime behavior, a reproducible test, or a narrowly
  justified compatibility contract.
- Do not merge with a failing required test, unresolved actionable thread,
  dirty worktree, moved base, or an unrecorded final full SHA.
