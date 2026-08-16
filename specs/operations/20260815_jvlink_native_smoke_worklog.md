# JV-Link native smoke worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: execute a real authenticated JV-Link transport smoke for the code
  merged by PR #163, covering the real-data call chain from `JVInit` through
  `JVOpen`, `JVStatus`, `JVRead`, and `JVClose` rather than mocks.
- Minimum scope: discover an existing authorized JV-Link runtime,
  prove the exact code SHA under test, run a bounded read-only/small-date smoke,
  record sanitized exit status and counts, and publish the evidence in a
  documentation-only PR.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_native_smoke`
- Branch: `agent/jvlink-native-smoke-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `2dad8a5b34e15a06f1e65931b8a1918532c560d1`
- Related release: `v1.6.10`; PR #163 is merged but unreleased.
- Dependency: merged PR #163 and a separately provisioned, authorized
  non-production JV-Link runtime used for the authenticated smoke.
- Reviewer: Codex. No Claude review is used for this iteration.

## Initial state

- `python3 scripts/system_status.py --json --skip-remote --sections git` was
  run from KPS before discovery. It confirmed the KPS status command was
  available and read-only; this test targets the separate jrvltsql repository.
- The host is Linux x86_64 and has no directly usable authenticated bridge
  runtime or `powershell.exe` command.
- Read-only discovery found a healthy authorized development runtime. Its
  machine, container, image, binary, account, and filesystem identities are
  intentionally omitted from this public record. Secret environment values,
  registry contents, and record payloads were not printed.
- Every authenticated test used the runtime's existing non-blocking
  coordination mechanism and unprivileged identity. An active scheduled
  collection was observed during discovery, so the smoke stopped and waited
  rather than overlapping it. The coordination path and identity are omitted.

## Exact-code staging

- The full worktree at merge SHA
  `2dad8a5b34e15a06f1e65931b8a1918532c560d1` was copied to a disposable,
  isolated staging directory. The public source hashes used for the smoke were:
  - `src/jvlink/bridge.py`:
    `ae6a9df9fd7386af9c866194a8f45e2873e4c2068b6afea34fe818e61f63d836`
  - `src/jvlink/wrapper.py`:
    `0b03c16aa3050463a9986ea7ebc344927a6156ef9394dfc5bd43dd3a76b8d917`
  - `src/fetcher/base.py`:
    `bd5dc3a5eca74f6d66e38b34f279536c844e25199d39595f251cd7c08a71eb6c`
  - `src/fetcher/historical.py`:
    `8a1763ebf7fea3ac76ec8d803de74fac4980284475f5e0b180d12c0916152111`
- The public repository bridge launches its configured executable directly.
  The collector requires an environment-specific launcher, so a test-only
  subclass overrode `_start_process` solely to supply that launcher.
  `jv_init`, `jv_open`, `jv_rt_open`,
  `wait_for_download`, `jv_read`, `jv_close`, protocol validation, and state
  tracking remained the exact merge-SHA implementation. This is valid
  evidence for those protocol methods, but not for native Windows process
  startup.

## Authenticated test results

### Real record path: pass

- Command summary: while holding the runtime coordination guard, select one
  existing 2026-08-15 JRA race identity internally, then run
  `JVInit -> JVRTOpen(0B30) -> JVRead -> JVClose` through the exact merge-SHA
  protocol methods. The race key and returned record bytes were not printed.
- Sanitized observation:
  - `JVInit`: `0`
  - `JVRTOpen`: `0`
  - legacy compatibility read count: `0`
  - first `JVRead`: return code `962`, payload length `962`, one read call
  - `JVClose`: `0`
  - notice dialogs closed by the test watcher: `0`
- Result: **PASS**. This proves real authenticated transport, exact byte-count
  validation, one real record, the current JVRTOpen response envelope, and an
  explicit successful close for merge SHA
  `2dad8a5b34e15a06f1e65931b8a1918532c560d1`.

### JVOpen no-data/close obligation: pass

- Command summary: under the same lock and identity, run
  `JVInit -> JVOpen(MING, 20260815000000, option=1) -> JVClose`.
- Sanitized observation:
  - `JVInit`: `0`
  - `JVOpen`: `-1`
  - read count: `0`
  - download count: `0`
  - `JVClose` from the preserved close obligation: `0`
- Result: **PASS** for the official no-data envelope and the PR #163 change
  that retains a close obligation after `JVOpen=-1`.

### JVOpen successful-data/JVStatus path: not proven

- `JVOpen(RACE, 20260815000000, option=2)` and a bounded fallback
  `JVOpen(RACE, 20260808000000, option=1)` each initialized successfully but
  ended in `JVLinkBridgeError` before an open response was received.
- The same option-2 call was repeated with the separately deployed bridge
  client rather than merge-SHA Python. It also returned a
  classified `Bridge response timeout (120s)` after `JVInit=0`.
- Result: **NOT PROVEN**, not a merge-SHA regression finding. The reproduced
  timeout in the separately deployed client shows that this environment
  cannot currently distinguish an external JV-Link/Data Lab response issue
  from a client issue for that call. No source change is justified from this
  evidence. A successful `JVOpen` with a positive `download_count`, exact
  `JVStatus == download_count`, and a real historical `JVRead` remains a
  follow-up gate.

## Cleanup and final state

- After the calls, no bridge or agent process remained, the coordination guard
  was available, and the development runtime remained healthy.
- The disposable staged copy was removed after validating its resolved path.
  No runtime restart, bridge
  identity change, registry edit, database write by the test harness, or
  production mutation was performed.
- Repository source files are unchanged. This iteration changes only this
  tracked evidence file.
- Overall verdict: **partial native smoke pass**. The real-time real-record
  path and the historical no-data/close path passed; successful-data JVOpen
  plus JVStatus is deliberately not reported green.

## PR publication and review

- Documentation-only PR #164 was opened against `master`:
  <https://github.com/miyamamoto/jrvltsql/pull/164>.
- Initial documentation candidate
  `016cfb96e86c14b750a687a7581dcbdd58ef0ae2` had successful GitHub Actions
  `test` and `lint` jobs in run `31867796776`; the documentation-only
  `performance-test` job was skipped by workflow policy.
- Codex reviewed the one-file evidence diff against the sanitized command
  observations and found no actionable contradiction or unsupported green
  claim. GraphQL review-thread inspection reported zero threads.
- CodeRabbit was automatically invoked when the PR left draft, but reported
  `Review rate limited` and produced no review. It is not counted as review
  evidence or as a required gate.
- Candidate `ca8539434c48e2fd9d4e6b5b0e2f7d75ab382c4c` received one Copilot
  documentation comment: two inline code spans crossed Markdown source-line
  boundaries. The finding was accepted, both occurrences were changed to
  short per-token code spans in one revision, and no runtime claim changed.
- This tracked PR-state update necessarily creates a later final candidate.
  Its full SHA, checks, and final thread count are recorded in PR metadata to
  avoid a self-referential commit loop; the initial candidate's checks are not
  reused for that later SHA.

## Safety and evidence rules

- Do not print credentials, service keys, registry contents, connection
  strings, secret environment values, or private runtime identity. Environment
  inspection is limited to variable names and sanitized availability flags.
- Do not stop/restart or mutate the running collector merely to make the test
  possible. Prefer a supported health/API/test entry point or an isolated
  disposable execution path that reuses identity safely.
- Do not count Linux fixed-signature mocks as the real smoke.
- The exact full SHA of the Python code and the exact image/container identity
  must be recorded with the result. A result from an older checkout is not
  evidence for PR #163.
- Bound the requested data interval and record count. Always attempt JVClose;
  abort on an existing open/writer operation, identity conflict, or any sign
  that the smoke would interfere with collection.

## Next safe command

Push this final worklog update to PR #164, record the new candidate full SHA in
the PR, and verify its focused checks, Codex review, unresolved thread count
zero, and clean worktree before merging the documentation-only iteration. A
later follow-up may retry the remaining successful-data historical gate
(`JVOpen`, `JVStatus`, `JVRead`, and `JVClose`) on an authorized native
Windows/JV-Link host, or first diagnose the reproducible deployed-client
`JVOpen(RACE)` timeout without changing the runtime identity. Do not reuse the
real-time pass as proof of the unverified historical-download path.

## STOP conditions

- Stop before an authenticated call if the target is production, is actively
  collecting, owns a writer lock/open JV-Link stream, or cannot isolate the
  smoke safely.
- Stop if the executable/image/code SHA cannot be identified exactly.
- Stop on any request for a secret value or license/runtime identity mutation,
  collector restart, or unbounded historical download.
- Stop before claiming success unless at least one real record is read and
  JVClose is observed without error.
