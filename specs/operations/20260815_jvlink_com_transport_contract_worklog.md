# JV-Link COM transport contract worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: make the native Python JV-Link transport and the public bridge
  helpers conform to the official JV-Link 4.9.0.1 call/return/state contracts,
  without changing parser layouts or database schemas in this iteration.
- Minimum scope:
  - native pywin32 `JVOpen` six-argument invocation and tuple handling;
  - native `JVGets` byte-array/size/filename invocation;
  - distinct JVOpen `-1` no-data and `-2` setup-cancel semantics;
  - recoverable JVRead/JVGets `-3` propagation and bounded caller retry;
  - bridge download completion at `JVStatus == downloadcount`;
  - fail-closed COM-buffer reconstruction when bytes cannot be recovered;
  - focused negative/positive tests, documentation evidence, review, PR, and
    merge for this transport-only iteration.
- Out of scope: BaseParser byte slicing, WH/schema expansion, the remaining 38
  parser layouts, dataspec generation guards, updater DataKubun semantics, and
  fixture provenance. Those remain separate follow-up iterations documented in
  PR #162.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260815_jrvltsql_com_transport`
- Branch: `agent/jvlink-com-transport-contract-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `c1fc891a5d17ff2982901867f4c4b6dc4af98464`
- Dependency: documentation audit PR #162 merged as the base SHA above.
- Related released version: `v1.6.10`; this is a new unreleased code candidate.
- Reviewer policy: Codex performs the implementation review. Gather all
  actionable correctness/data-integrity findings before a consolidated fix;
  do not merge without exact-head tests, CI, unresolved threads zero, and a
  clean worktree.

## Official contracts

- JV-Link interface specification 4.9.0.1:
  `https://jra-van.jp/dlb/sdv/sdk/JV-Link4901.pdf`.
- The official SDK community index was rechecked on 2026-08-15. It still
  identifies interface specification 4.9.0.1 (2024-08-07) as current even
  though the separate development guide link was updated on 2026-08-04:
  `https://developer.jra-van.jp/t/topic/45`.
- `JVOpen(dataspec, fromtime, option, readcount, downloadcount,
  lastfiletimestamp)` has six parameters. The last three are output/ref values.
- `downloadcount` is the subset of `readcount` requiring download, so both
  counts are non-negative and `downloadcount <= readcount`.
- `JVGets(Byte Array buff, size, filename)` has three parameters.
- JVOpen `-1` means no matching data; `-2` means the setup dialog was cancelled.
- JVRead/JVGets `-3` means the file is still downloading and reading must resume
  after a wait.
- `JVStatus` is a downloaded-file count. Completion is equality with the
  `downloadcount` returned by JVOpen, and the completed value remains until
  JVClose.
- Official `JVRTOpen(dataspec, key)` has no read-count out parameter and
  succeeds only with return code `0`; the Python API retains a zero-valued
  second tuple item solely for backward interface compatibility.
- The current official error-code community post confirms the meanings and
  remedies for `-1`, `-3`, `-201/-202/-203`, `-402/-403`, and `-502/-503`:
  `https://developer.jra-van.jp/t/topic/822`.

## Start state and operations

- Verified `gh` 2.76.0 and an authenticated `miyamamoto` GitHub session.
- Fetched `origin/master`; created the clean dedicated worktree and branch from
  full SHA `c1fc891a5d17ff2982901867f4c4b6dc4af98464`.
- At the initial checkpoint, no production source or test had been edited yet.
- Added platform-neutral, fixed-signature COM fakes and public state-machine
  tests in `tests/test_jvlink_transport_contract.py`; these do not inherit the
  Windows-only skip marker in `tests/test_jvlink_wrapper.py`.
- Red-first command on unchanged production source:
  `pytest -q tests/test_jvlink_transport_contract.py` exited `1` with
  `13 failed`. The observed failures included three missing `JVOpen`
  arguments, the missing `JVGets` filename argument, `-2` being accepted as
  no-data/readable, `-3` raising immediately instead of waiting, U+FFFD being
  silently changed to ASCII `0`, CP1252 byte `0x93` becoming CP932 `0x8167`,
  bridge `wait_for_download` not accepting `download_count`, and JVStatus
  overshoot being accepted as completion. These are the intended contract
  failures, not fixture/setup failures.
- Before production edits, expanded the same red suite with direct negative
  cases for deterministic call-order/download failures, byte-count mismatch,
  and bridge setup-cancel state. A second unchanged-source red run is required
  below before implementation.
- Expanded unchanged-source red command:
  `pytest -q tests/test_jvlink_transport_contract.py` exited `1` with
  `20 failed`. The added cases also observed that `-201/-202/-203/-502/-503`
  were retried or deleted instead of failing once, a short native buffer was
  not rejected by a byte-count contract, and bridge `-2` exposed a readable
  state. Product edits begin only after this second red result.
- Independent source re-check after the first green implementation found an
  actionable pywin32 marshaling error in the candidate: the official interface
  has three JVGets arguments, but a working pywin32 implementation returns
  `(return_code, memoryview, filename)`, not the candidate's assumed four-item
  tuple. The same field report changed JVRead/JVGets out-argument placeholders
  from empty strings to `bytearray()` after intermittent JVLinkAgent crashes.
  Evidence: `https://qiita.com/hraps/items/b7a4ba572ff52f4ff47d` (updated
  2025-07-14), cross-checked against the official JVGets syntax. Tests are
  changed first; a focused red result against the first candidate is required
  before correcting production code.
- Review also found that `.github/workflows/test.yml` enumerates test files and
  did not include the new transport contract suite, so CI could be green while
  every new negative test was absent. A workflow-membership test is added
  before the workflow edit and must fail on the current workflow.

## Red/green implementation evidence

- First implementation corrected the six-argument JVOpen call, JVGets call
  shape, `-1/-2/-3` handling, exact JVStatus completion, corrupt-file error
  classification, and fail-closed buffer recovery. The expanded contract suite
  turned green after those edits.
- A source recheck against the working 64-bit Python/pywin32 field report
  `https://qiita.com/hraps/items/b7a4ba572ff52f4ff47d` found that JVGets
  actually returns three values `(code, memoryview, filename)` and that empty
  string dummy arguments had caused intermittent JVLinkAgent failures. Two new
  tests failed against the first candidate, then passed after both JVRead and
  JVGets used `bytearray()` placeholders and JVGets accepted the three-value
  return shape.
- The CI-membership test failed once before
  `tests/test_jvlink_transport_contract.py` was added to the enumerated workflow
  command, then passed.
- Additional state/protocol negative tests were run before each related fix:
  bridge RT no-data/close exception (`2 failed`), malformed/short base64 payload
  (`2 failed`), missing result codes and close error response (`5 failed`),
  missing open outputs/RT compatibility count (`4 failed`), and undocumented
  positive JVOpen (`1 failed`). Each corresponding focused rerun passed after
  the implementation change.
- The assumed mandatory bridge RT `readcount` was then checked against the
  actual companion runtime. Read-only inspection of
  `miyamamoto/jrvltsql-wine-runtime` `origin/main` full SHA
  `be759ee5bdccd06dccb61f1c63f9799f136c0a39` proved that its valid
  `JVRTOpen=-1` envelope omits `readcount`. A compatibility test for this exact
  response, positive JVRTOpen rejection, and negative expected download count
  produced `3 failed` before correction and `4 passed` after correction. The
  earlier missing-RT-count hypothesis/test was withdrawn rather than encoding
  a bridge-incompatible contract.
- Strict state review found that a successful COM/bridge open followed by a
  malformed output envelope lost the JVClose obligation, and that impossible
  `downloadcount > readcount` plus a nonzero invented JVRTOpen count were still
  accepted. The focused negative run produced `6 failed`; after preserving
  pending-close state before output validation and validating the counts it
  produced `6 passed`.
- A close acknowledgment with a nonzero result was being treated as success
  and clearing state. The new native/bridge negative test produced `1 failed`;
  after exact-zero validation, the close-focused group produced `5 passed`.
- Final native-state review found the same close-obligation leak for a
  malformed successful one-item JVRTOpen tuple. Its focused test produced
  `1 failed` before state capture was moved ahead of tuple validation and
  `1 passed` afterward.
- Final bridge-state review found that a protocol-level `status: ok` response
  without a result code raised correctly but lost the remote JVClose
  obligation for both JVOpen and JVRTOpen. The two-case negative test produced
  `2 failed` with `_needs_close == False`; after capturing the obligation
  before result-code validation it produced `2 passed`.
- The complete fetch-loop reread found that `-402/-403` with no recovery
  callback continued without deleting or reopening anything, allowing an
  endless reread of the same corrupt file. The two-code negative test first
  produced `2 failed` because no exception was raised, then `2 passed` after
  the no-recovery branch was made fail-closed.
- Companion-runtime compatibility review found that
  `jrvltsql-wine-runtime@be759ee5bdccd06dccb61f1c63f9799f136c0a39`
  acknowledges close as `{"status":"ok"}` without the official native Long
  result code. A direct compatibility test produced `1 failed` against the
  strict candidate. The bridge now accepts only this successful legacy
  envelope (while still rejecting explicit nonzero codes and error envelopes);
  native COM continues to require exact zero. The close group produced
  `9 passed`, and the combined transport/bridge group produced `76 passed`.
- Post-commit public-call-site review of candidate
  `86a62c4d41b475ed5afbb0e17c8b256edf344901` found that making
  `download_count` the first required `wait_for_download` argument broke the
  released `wait_for_download(timeout, poll_interval)` API. Two tests first
  produced `2 failed` with a missing-argument `TypeError`. The bridge now
  stores the validated JVOpen count, keeps the historical positional order,
  permits an explicit keyword override, and fails closed when neither source
  supplies an expected count. The focused rerun produced `2 passed`; the
  combined transport/bridge group produced `78 passed`. The cited candidate
  SHA is superseded and must not be used as final evidence.
- Positive counterparts cover JVOpen success/no-data/cancel state, JVRTOpen
  success/no-data, exact JVStatus equality, valid byte/memoryview recovery,
  valid bridge base64, and successful exact-zero close.

## Implemented scope

- `src/jvlink/wrapper.py`
  - invokes JVOpen with all six official arguments;
  - invokes JVRead/JVGets with stable `bytearray()` out placeholders;
  - accepts current three-value and compatible four-value marshaled read
    responses without inventing missing fields;
  - distinguishes readable state from the mandatory JVClose obligation;
  - validates official result/count relationships and rejects malformed
    successful envelopes without leaking close state;
  - preserves `-3` for bounded caller retry;
  - reconstructs exact transport bytes and rejects replacement/unencodable or
    short buffers instead of manufacturing `0`/`?` data;
  - clears state only after exact-zero JVClose.
- `src/jvlink/bridge.py`
  - validates result codes and required JVOpen fields fail-closed;
  - remains compatible with the current runtime's count-less RT no-data
    envelope while requiring any provided compatibility count to be zero;
  - validates base64, byte length, declared size, explicit close results, and
    exact download-count completion, while retaining the current companion
    runtime's code-less successful close acknowledgment;
  - preserves the released positional wait signature by retaining the latest
    validated JVOpen download count and refuses to infer completion when no
    expected count is available;
  - preserves pending-close state across malformed envelopes and failed close.
- `src/fetcher/base.py` and `src/fetcher/historical.py`
  - bound `-3` wait/retry with monotonic elapsed time;
  - allow targeted corrupt-file recovery only for official `-402/-403`;
  - fail once without blind deletion for deterministic call-order, download,
    and missing-file statuses;
  - reject setup cancellation as no-data and reject negative/overshot download
    counts immediately.
- `.github/workflows/test.yml` executes the new platform-neutral transport
  contract suite on every test job.

## Verification on the current uncommitted candidate

- `pytest -q --no-cov tests/test_jvlink_transport_contract.py
  tests/unit/test_jvlink_bridge.py --tb=short`: `78 passed`.
- `pytest -q --no-cov tests/test_jvd_self_repair.py
  tests/test_retired_data_specs.py --tb=short`: `170 passed`.
- `pytest -q --no-cov tests/test_realtime.py --tb=short`:
  `63 passed, 3 subtests passed`.
- `pytest -q --no-cov tests/test_error_scenarios.py --tb=short`:
  `21 passed`.
- `flake8 src tests --count --select=E9,F63,F7,F82 --show-source
  --statistics`: exit `0`, count `0`.
- `python3 -m compileall -q` on all changed source and the new test: exit `0`.
- `black --check tests/test_jvlink_transport_contract.py`: pass. Existing
  source files are not bulk-reformatted because repository formatting drift is
  outside this iteration.
- `git diff --check`: pass.
- An earlier workflow-equivalent run passed `820 passed, 2 skipped, 3 warnings,
  3 subtests passed`; it predates the final strict-state corrections and is
  chronological evidence only, not the final candidate gate. The full workflow
  command must be rerun after committing the final candidate SHA.
- The first committed candidate
  `86a62c4d41b475ed5afbb0e17c8b256edf344901` passed the updated
  workflow-equivalent command with `842 passed, 2 skipped, 3 warnings, 3
  subtests passed`, but public API review subsequently superseded it with the
  wait-signature correction above. Those results are chronological evidence,
  not the final candidate gate.
- A parallel pytest attempt caused only a shared `.coverage.*` SQLite collision
  after the realtime tests themselves reported `63 passed, 3 subtests passed`.
  It is not counted as a product pass; all affected suites above were rerun
  sequentially with `--no-cov` and exited zero.

## Windows/JV-Link smoke status

- Read-only host inspection on 2026-08-15 found Linux x86_64, no `wine`, no
  `wine32`, no `powershell.exe`, no JV/JRA/WINE integration environment marker,
  and no real JVLinkBridge executable. Located `.exe` files were zero-purpose
  pytest fixtures under `.pytest-tmp`.
- `tests/integration/test_jvlink_real.py` is opt-in through
  `JLTSQL_RUN_REAL_INTEGRATION=1` and explicitly requires an authenticated
  Windows JV-Link host. This host cannot meet that precondition.
- GitHub `.github/workflows/test.yml` runs only on `ubuntu-latest`; it cannot
  supply the missing native COM smoke.
- Linux fixed-signature fakes prove argument/state logic but are not treated as
  equivalent to real pywin32/COM marshaling. Per the iteration STOP condition,
  this remains a merge blocker unless a direct authenticated Windows result is
  supplied for the exact candidate SHA.

## Red-first requirement

- Add the minimum signature-enforcing fakes and state-boundary tests before
  production edits.
- Run them on the unchanged production code and record the exact failing
  assertions/exit status here.
- Positive counterparts must show official success/no-data paths still work.
- A thrown exception is not a successful `-3` decision. Tests must observe a
  recoverable status and a bounded retry/timeout decision at the caller.
- Buffer reconstruction must have a negative test proving U+FFFD or an
  unencodable character cannot become plausible `0`/`?` data.

## Next safe command

Review the complete diff once more, update this worklog if a finding changes
the candidate, commit the candidate, and rerun the exact workflow-equivalent
test/lint commands on that full SHA. Push a draft PR with the exact SHA and
evidence. Do not merge until the real Windows/JV-Link smoke is attached to the
same candidate or an explicitly accepted equally direct replacement exists.

## STOP conditions

- Stop before product edits until the focused new tests fail on unchanged
  production code for the intended reason.
- Stop before merge if the real Windows/JV-Link smoke required by the native
  path cannot be executed or replaced by sufficiently direct evidence; mark it
  as an explicit blocker rather than treating Linux mocks as equivalent.
- Stop before merge on any focused/workflow-equivalent failure, actionable
  review finding, unresolved thread, head/test SHA mismatch, or dirty worktree.
