# PR #161 retired data-spec gate worklog

## Scope and provenance

- Objective: make the pre-2023-08 JV-Data layout names that jrvltsql cannot
  parse fail closed at every supported historical JVOpen entry point, while
  keeping the current-layout names usable and restoring the PR's failing CI
  tests without weakening the CLI configuration contract. This is a local
  support policy, not a claim that JRA-VAN removed the old IDs from its API.
- Minimal scope: shared retired-spec validation, the public Python JV-Link
  wrapper/bridge entry points, the existing historical/CLI guards and focused
  tests, plus this worklog. Operational name replacements already present in
  the PR are reviewed but not broadened without a concrete defect.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_pr161_fix`
- Branch: `claude/reject-legacy-dataspecs-225` (cross-repository PR branch in
  `hayato1980/jrvltsql`)
- PR: https://github.com/miyamamoto/jrvltsql/pull/161
- Base branch: `master`
- Latest base full SHA at iteration start:
  `e55b1f93f4661cf83cc7d890ebe6ee7399f354ab`
- Starting PR head full SHA:
  `b2a79a70145ddb6427fe03a7c711c5c6e3847c32`
- Base-update merge commit full SHA:
  `7e1f583aea6d027528a1eec2cf863bf1559adc7b`
- Related release: `v1.6.10`
- Dependency order: PR #159 merged as
  `0001ea2179db28be49938f4b7f178a6bd70c0942`; PR #160 merged as
  `e55b1f93f4661cf83cc7d890ebe6ee7399f354ab`; this PR now includes both.

## Claude Code sessions

- Implementation/review-fix session ID:
  `e2ec26a4-3b59-499a-b1a7-a98c1a6b27cd`
- Planned independent final-review session ID:
  `ddf27a69-bc9a-4e68-8cb6-fba082d2e181`
- Model for both: `--model fable`
- Selection reason: this is a fail-closed validator with multiple public
  entry paths (CLI, historical fetcher, in-process COM wrapper, out-of-process
  bridge). Incorrect ordering or a missed path changes whether a retired name
  reaches JVOpen and can silently request the wrong/unsupported dataset.
- Review corrections in this iteration must resume the implementation session;
  the final-review session is separate and read-only.

## Unsupported legacy-name contract

- Legacy → current-layout mappings introduced by the PR:
  `DIFF→DIFN`, `BLOD→BLDN`, `SNAP→SNPN`, `HOSE→HOSN`, `TCOV→TCVN`,
  `RCOV→RCVN`.
- Matching is case-insensitive. Replacement/current names remain accepted.
- Rejection must occur before COM invocation or bridge command transmission,
  with an actionable message naming the replacement.

## Status at start

- Observed: original PR lint and CodeRabbit succeeded, but the Actions test job
  ran real test steps and failed: `9 failed, 745 passed, 2 skipped` on
  `b2a79a70145ddb6427fe03a7c711c5c6e3847c32`. This is a real CI failure and
  cannot be waived.
- Observed CI cause: all nine failures invoke root Click commands without a
  config file, so the root callback exits with `Configuration file not found`
  before the subcommand retired-spec guard runs. The tests therefore do not
  reach the behavior they claim to verify.
- Contract decision pending implementation review: preserve configuration as
  the root CLI prerequisite and provide a minimal config to focused CLI tests,
  unless evidence shows retired-name validation intentionally belongs before
  all root setup. Do not move business validation into the root callback just
  to satisfy a test.
- Observed bypass risk: `HistoricalFetcher.fetch`/cache paths guard retired
  names, but direct public `JVLinkWrapper.jv_open` and
  `JVLinkBridge.jv_open` calls do not yet invoke the shared guard. Direct users
  can therefore bypass the PR's intended fail-closed boundary.
- The PR has no known unresolved inline thread; review-body and CI findings
  require explicit PR conversation evidence after correction.
- Latest `origin/master` merged without conflicts; no implementation edit has
  been made in this iteration. Worktree was clean before creating this log.

## Red-first requirement

- Before production edits, add the minimum regression contract proving direct
  wrapper and bridge calls with retired names currently reach their downstream
  COM/send paths. Run on unchanged production code and record the observed red
  assertions/exit status.
- Keep replacement/current names green and prove they still reach the
  downstream path.
- Repair CLI tests so they exercise the command under its real config
  prerequisite; a missing config is not evidence about retired-spec handling.

## Implementation session evidence (e2ec26a4, 2026-08-15)

### Environment

- `uv sync --python 3.12 --extra dev --extra postgres` in the worktree;
  `.venv/bin/python -V` → `Python 3.12.11` (matches the CI job's 3.12).
- All commands below ran from the worktree root with
  `.venv/bin/python -m pytest ... -p no:cacheprovider --no-cov -q`.

### CI 9-failure diagnosis confirmed locally (unchanged code)

- Command: `pytest tests/test_retired_data_specs.py` on
  `7e1f583aea6d027528a1eec2cf863bf1559adc7b` before any edit.
- Result: `9 failed, 98 passed`, exactly the nine
  `TestCLIRejectsRetiredSpecs` tests. Representative assertion:
  `assert '2023-08' in "Error: Configuration file not found. Run 'jltsql
  init' first.\n"`.
- Root cause: the root Click callback requires a config file for every
  subcommand except `init`, and its default path is resolved relative to the
  repository source tree (`Path(__file__).parent.parent.parent /
  "config/config.yaml"`), not the CWD. CI has only `config.yaml.example`, so
  the callback exits 1 before the subcommand retired-spec guard runs; the
  tests never reached the behavior they assert. (A checkout that happens to
  have a local `config/config.yaml` would mask this, which is why it slipped
  through the PR author's local run.)
- Contract decision: keep configuration as the root prerequisite. The tests
  were repaired to write a minimal config satisfying `_validate_config`
  (`jvlink`, `database.type`, one enabled database, `auto_update_check:
  false` to avoid the update probe) inside `isolated_filesystem()` and to
  pass it via `--config`, reaching the real subcommand guard. No business
  validation was moved into the root callback.

### Red-first direct-boundary evidence (unchanged production code)

- Added `TestWrapperRejectsBeforeCOM` and `TestBridgeRejectsBeforeTransmission`
  to `tests/test_retired_data_specs.py`. Both build the object via `__new__`
  (same technique as `TestFetcherRejectsBeforeReachingJVLink`) and stub only
  the downstream layer (`_jvlink` COM mock / `_send_command` mock) with a
  successful JVOpen response, so "the guard fired before transmission" is
  observable as "downstream never called".
- Command: `pytest tests/test_retired_data_specs.py::TestWrapperRejectsBeforeCOM
  tests/test_retired_data_specs.py::TestBridgeRejectsBeforeTransmission` on
  unchanged `src/`.
- Result: exit status 1, `14 failed, 2 passed`. Every retired spelling
  (DIFF, BLOD, SNAP, HOSE, TCOV, RCOV, lowercase `diff`) failed with
  `Failed: DID NOT RAISE <class 'ValueError'>`, and the captured logs show
  the retired name reaching the downstream path on both boundaries, e.g.
  `JVOpen successful data_spec=DIFF ...` (wrapper COM mock) and
  `JVOpen via bridge data_spec=RCOV ...` (bridge send). The two replacement
  tests (`DIFN` reaches the mocked downstream) passed, proving the harness
  itself exercises the real methods.
- Full run at this point: `pytest tests/test_retired_data_specs.py` →
  `14 failed, 109 passed` (the nine repaired CLI tests are green because the
  CLI guard from the PR already works once the command is actually reached).

### Implementation (after red evidence)

- `src/jvlink/wrapper.py`: import `is_retired_data_spec` /
  `retired_data_spec_message` from `src.jvlink.constants`; `jv_open` now
  raises `ValueError(retired_data_spec_message(data_spec))` before the `try`
  block, so the rejection happens before `self._jvlink.JVOpen(...)` and is
  not re-wrapped into `JVLinkError` by the method's catch-all. Docstring
  gained the same `Raises: ValueError` line historical.py uses. `jv_rt_open`
  untouched.
- `src/jvlink/bridge.py`: same imports; `jv_open` raises the same
  `ValueError` before `_send_command({"cmd": "open", ...})`, so no bridge
  command is transmitted. `jv_rt_open` untouched (realtime specs are a
  separate namespace).
- Exception type and message reuse the shared constants helpers exactly, so
  wrapper, bridge, and `HistoricalFetcher` all fail with the identical
  actionable `ValueError` naming the replacement and `2023-08`.
- `tests/test_retired_data_specs.py`: the two new boundary classes (16 tests)
  plus the CLI repair (`MINIMAL_CLI_CONFIG` + `_invoke_cli_with_config`
  helper; the nine tests now pass `--config` with a minimal valid config
  written in `isolated_filesystem()`).
- Changed files: `src/jvlink/wrapper.py`, `src/jvlink/bridge.py`,
  `tests/test_retired_data_specs.py`, this worklog. `uv.lock` was touched by
  `uv sync` (stale `jltsql` version number only) and restored with
  `git checkout -- uv.lock`.

### Validation (after implementation)

- `pytest tests/test_retired_data_specs.py` → `123 passed`, exit 0.
- `pytest tests/test_retired_data_specs.py tests/unit/test_jvlink_bridge.py
  tests/test_jvlink_wrapper.py tests/test_jvlink_constants.py` →
  `157 passed, 22 skipped` (skips are the Windows-only wrapper module),
  exit 0.
- Workflow-equivalent selection (the exact CI pytest file list from
  `.github/workflows/test.yml`, minus coverage flags) → `779 passed,
  2 skipped, 3 subtests passed`, exit 0.
- `pytest tests/test_cli.py` → `2 failed, 21 passed`
  (`TestCLIBasic::test_version_command`, `::test_status_command`).
  Pre-existing and unrelated: the same two fail on pristine HEAD
  `7e1f583` in a clean temp worktree, pass when the class runs alone
  (order-dependent), and `test_cli.py` is not in the CI selection. Not
  touched, per minimal scope.
- Blocking lint: `flake8 src tests --count --select=E9,F63,F7,F82
  --show-source --statistics` → `0`, exit 0.
- `git diff --check` → clean.

### Boundary review (unguarded public historical JVOpen paths)

- Raw transmission exists in exactly two places: `wrapper.py`
  (`self._jvlink.JVOpen(...)`) and `bridge.py` (`{"cmd": "open", ...}`),
  both now behind the guarded public `jv_open`.
- `HistoricalFetcher.fetch` / `fetch_with_cache` are guarded by the PR;
  `fetch_with_date_range` delegates to `fetch` (verified in source). CLI
  fetch / cache build (rebuild delegates to build) guarded by the PR and now
  actually exercised by tests.
- `src/fetcher/historical.py.bak_20260210_203545` is a tracked leftover
  backup containing an old `jv_open` call, but its filename is not an
  importable Python module name, so it is not a supported bypass. Pre-dates
  this PR; left alone under minimal scope (candidate for separate cleanup).
- No NAR/second bridge variant exists; all other `JVOpen`/`jv_open` hits in
  `src/` are comments, docstrings, or progress labels.
- Realtime (`jv_rt_open`, realtime fetcher/updater) intentionally untouched.

## Remaining gates

- DONE (this session): red-first direct-boundary evidence, repaired CLI test
  setup, minimal public-boundary implementation, Python 3.12 focused and
  workflow-equivalent tests green locally, blocking flake8 and
  `git diff --check` clean.
- DONE (Codex): source-branch drift reconciliation, commit, push, exact-SHA
  local verification, and GitHub Actions test/lint success for the first
  pushed candidate `341927c0d62de97be3979672e3e813e3f12a2d9b`.
- SUPERSEDED by the user's 2026-08-15 follow-up: Claude Code is no longer the
  final reviewer for this iteration because its account limit remained
  unavailable; independent Codex review is required instead (see below).
- PENDING: review-fix commit and push, GitHub Actions success on the resulting
  full SHA, two independent Codex GREEN reviews, unresolved thread count zero,
  matching local/remote/PR head SHA, CLEAN merge state, final PR evidence
  comment, and clean worktree.

## Next safe command

Review and commit the second consolidated review-fix diff, run the focused and
workflow-equivalent suites for that exact SHA, then obtain two new independent
Codex verdicts and resolve all four GitHub review threads. Stop before merge
unless both reviewers are GREEN for the exact PR head SHA.

## Codex verification and Claude availability note

- Codex re-ran the focused boundary suite under Python 3.12.11:
  `pytest tests/test_retired_data_specs.py tests/unit/test_jvlink_bridge.py
  tests/test_jvlink_wrapper.py tests/test_jvlink_constants.py -q --no-cov` →
  `157 passed, 22 skipped`, exit 0.
- Exact workflow pytest selection including coverage → `779 passed, 2
  skipped, 3 subtests passed`, exit 0.
- Blocking flake8 gate → `0` findings, exit 0; `git diff --check` → clean.
- Informational mypy → 85 existing errors in 22 files, exit 1; the workflow
  marks this step `continue-on-error`. The reported wrapper/bridge items are
  pre-existing `no-any-return` findings, not the new guards.
- Source drift check: contributor source remains
  `b2a79a70145ddb6427fe03a7c711c5c6e3847c32`; `origin/master` remains
  `e55b1f93f4661cf83cc7d890ebe6ee7399f354ab`; local pre-candidate HEAD is
  `7e1f583aea6d027528a1eec2cf863bf1559adc7b`.
- First candidate committed and pushed as
  `341927c0d62de97be3979672e3e813e3f12a2d9b`. Exact-SHA verification repeated:
  focused `157 passed, 22 skipped`; workflow-equivalent coverage run `779
  passed, 2 skipped, 3 subtests passed`; blocking flake8 `0`; `git diff
  --check` clean. GitHub Actions run `31855794537` then completed with both
  `test` and `lint` successful; performance-test was intentionally skipped.
- Claude implementation session
  `e2ec26a4-3b59-499a-b1a7-a98c1a6b27cd` completed the edits, red/green
  evidence, boundary audit, and worklog update, then the CLI reported its
  session usage limit with reset at `13:30 Asia/Tokyo` before emitting a final
  prose summary. No Claude process remains and no edit was left in progress.
- This does not waive the user's required final Claude Code review. Commit,
  push, and Actions may proceed, but merge remains stopped until independent
  review session `ddf27a69-bc9a-4e68-8cb6-fba082d2e181` can review the frozen
  candidate and return GREEN.
- The first independent-review invocation at 2026-08-15 10:11 JST stopped
  before reading the candidate with `You've hit your session limit · resets
  1:30pm (Asia/Tokyo)`. This is an unavailable review, not a verdict, and is
  not counted as merge evidence. No file changed during the attempt.

## Codex review-fix continuation (user instruction, 2026-08-15)

- At 10:47 JST the user explicitly instructed the iteration to continue using
  Codex for review. This supersedes the still-unavailable Claude final-review
  requirement; the earlier Claude implementation/red-first evidence remains
  part of the history but is not presented as a final verdict.
- Resume point was clean and synchronized: local HEAD, contributor remote, and
  PR head all `18ed1081c007c1651fc8e572c3a9beedb71ef79e`; Actions test/lint
  successful; merge state CLEAN.
- CodeRabbit's substantive pass on the preceding code candidate produced four
  unresolved threads, still applicable to the same production diff:
  1. incorrect TCVN/RCVN descriptions;
  2. `scripts/fill_empty_postgresql_tables.py` uses `SNPN` with option 2 while
     the repository validator rejected that pair;
  3. two changed f-strings had no replacement fields;
  4. direct wrapper/bridge positive coverage exercised only `DIFN`.
- Official-source adjudication: JRA-VAN `JV-Data4901.pdf`, section "JVOpen
  メソッドで指定可能な option と dataspec の関係", lists `SNPN` for option 2.
  It also defines TCVN as "特別登録馬情報補てん" and RCVN as
  "レース情報補てん". Therefore the reviewer's proposed `SNPN` option 1 change
  was rejected as harmful; the actual defect was the repository's incomplete
  option-2 allow-list and quickstart's duplicate allow-list.

### Red-first evidence on `18ed1081` production

- Test-only change added `SNPN` to the existing option-2 contract and added one
  quickstart operational-boundary test. Before production edits:
  - central validator test → `1 failed, 2 passed`; observed
    `is_valid_jvopen_combination('SNPN', 2) is False`;
  - quickstart boundary test → `1 failed`; observed status `skipped` with
    `option=2 ... SNPN に対応していません` and no downstream call;
  - expanded six-replacement wrapper/bridge positives → `12 passed`, showing
    the positive harness was valid before production edits.

### Consolidated correction

- Added `SNPN` to `JVOPEN_VALID_COMBINATIONS[2]`; quickstart now reuses that
  central contract instead of maintaining a divergent local option-2 set.
- Corrected TCVN/RCVN source and quickstart labels to the official supplemental
  data names; corrected SNPN documentation to 出走時点情報 / CK and option 2
  support. The nearby fill-script comment now describes CK rather than
  unrelated realtime change records.
- Removed the two review-identified unnecessary f-string prefixes.
- Parameterized the existing direct wrapper and bridge positive tests over all
  six replacements with their supported options; no extra test functions or
  large matrix were added.
- Targeted green after production changes: central/boundary tests `15 passed`;
  quickstart operational-boundary test `1 passed`.
- Review-body-only nitpicks were not used to broaden the patch: the wording
  regression test remains because it protects the PR's explicit no-alias
  documentation contract, and the option 1/3/4 list-deduplication suggestion
  is unrelated refactoring with shared-mutable-list risk. These are
  non-actionable for merge and have no unresolved inline thread.

## Independent Codex review of `681b3802bb1a4ec447f434e0ae3afa77c6e1d9cf`

- Exact-SHA local evidence before review: focused `207 passed, 22 skipped`;
  workflow-equivalent `790 passed, 2 skipped, 3 subtests passed`; blocking
  flake8 `0`; changed-script compilation and `git diff --check` successful.
- Contract reviewer `/root/pr161_contract_review` → `NEEDS_CHANGES`:
  - P1: race-day payout/result recovery incorrectly requested DIFN, which does
    not carry HR/H1/H6; RACE is the relevant data spec.
  - P2: a MagicMock wrapper test treated invalid `DIFN + option 2` as valid.
  - P2: SNPN/HOSN display labels remained inconsistent with the official
    names.
  - P2: user-facing text incorrectly described the old IDs as officially
    abolished rather than as legacy layouts unsupported by jrvltsql.
- Boundary reviewer `/root/pr161_boundary_review` → `NEEDS_CHANGES`:
  - P1: `cache rebuild --spec DIFF` deleted an existing cache file before the
    delegated build command rejected the legacy spec.
  - P2: worklog STOP conditions still named the superseded Claude gate and an
    obsolete contributor SHA.
- Candidate `681b3802...` was rejected and was not pushed. Findings were
  consolidated before beginning this second repair batch.

### Second red-first evidence (production still at `681b3802...`)

- Cache rebuild test created `cache/nl/DIFF/20240101.v2.bin` with a sentinel,
  invoked the real CLI, and expected the bytes to survive. Result: exit 1;
  assertion raised `FileNotFoundError`, proving rejection happened after
  destructive clearing.
- Race-day post-phase test isolated operational checks and captured
  `run_fetch`. Result: exit 1; actual call was
  `('DIFN', '20260815', '20260815', 1, 'data/test.db')` instead of RACE.

### Second consolidated correction

- `cache_rebuild` now invokes the shared legacy-spec rejection before option
  checks, CacheManager construction, or clearing. Sentinel regression test is
  green.
- Post-race recovery now requests RACE once when either NL_H1 or NL_RA is
  missing. Scheduler/verification text identifies RACE as the payout source;
  pre-race setup retains its separate DIFN master update but no longer labels
  it as payouts/odds. Operational regression test is green.
- Wrapper option-parameter test now uses valid `SNPN + option 2`.
- SNPN and HOSN constant/progress labels now use 出走時点情報 and
  競走馬市場取引価格情報.
- User-facing error/docs now say that jrvltsql does not support the legacy
  layout and explicitly avoid claiming that JRA-VAN abolished the old IDs.
  Internal helper names remain stable and do not change public behavior.
- Targeted green after this batch: both new regressions `1 passed` each;
  wrapper/legacy suite `134 passed, 22 skipped`.

## STOP conditions

- Stop before the next push if the contributor source branch moves away from
  the last fetched remote `18ed1081c007c1651fc8e572c3a9beedb71ef79e`
  without reconciliation.
- Stop before merge if any unsupported legacy spelling reaches COM/bridge
  transmission or causes cache deletion,
  any replacement/current name is incorrectly rejected, CLI tests still fail
  before exercising their target, payout recovery requests a spec that cannot
  provide H1, Actions is not successful, either final independent Codex review
  is not GREEN, an unresolved thread exists, tested SHA and PR head differ, or
  the worktree is dirty.

## Second independent Codex review of `aff7f754b23da01c8e2b6ddead7c74770eacee67`

- Boundary/operational reviewer `/root/pr161_boundary_review` → `GREEN`; no
  P0/P1/P2 findings remained after the consolidated cache and recovery fixes.
- Contract reviewer `/root/pr161_contract_review` → `NEEDS_CHANGES` with one
  remaining P1: `check_se_results` still told operators to fetch DIFN when
  central `NL_SE` results were incomplete, although result records are carried
  by RACE. Its other first-pass findings were confirmed fixed; its focused run
  reported `174 passed, 22 skipped`.
- Candidate `aff7f754...` was rejected and was not pushed. A minimal regression
  test was added before the production edit. On `aff7f754...` it failed with
  actual issue text `fetch DIFN` versus expected `fetch RACE`, proving the
  recovery guidance could select the wrong data spec.
- The result-completion comment and actionable issue now consistently direct
  operators to RACE. The paired normal behavior remains covered by the existing
  completion checks; this change does not alter completion thresholds or
  realtime `RT_SE` selection.

## Third independent Codex review of `f5f4f6d3b942f7324a6e55b103afb0b0a56fa64d`

- Boundary/operational reviewer `/root/pr161_boundary_review` → `GREEN` with
  no P0/P1/P2 findings; its related run reported `272 passed, 3 subtests
  passed`, and it confirmed both result-guidance branches were reached.
- Contract reviewer `/root/pr161_contract_review` → `NEEDS_CHANGES` with one
  P2 compatibility finding: four public constants present on base
  (`DATA_SPEC_DIFF`, `DATA_SPEC_BLOD`, `DATA_SPEC_SNAP`, `DATA_SPEC_HOSE`) had
  been deleted, causing existing imports to fail before callers could receive
  the actionable fail-closed rejection. Its previous RACE finding was fixed;
  its focused run reported `175 passed, 22 skipped`.
- Candidate `f5f4f6d3...` was rejected and was not pushed. A test-only import of
  all four compatibility constants failed during collection with
  `ImportError: cannot import name 'DATA_SPEC_BLOD'`, reproducing the break on
  the unchanged production candidate.
- The four public names are restored with their original legacy string values
  and are explicitly documented as deprecated compatibility constants, not
  aliases. Their parameterized test requires that every value remains
  importable while all JVOpen options reject it through the central contract.
