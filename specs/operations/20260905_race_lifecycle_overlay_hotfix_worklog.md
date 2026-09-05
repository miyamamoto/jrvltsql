# 2026-09-05 race lifecycle overlay hotfix worklog

## Scope and provenance

- Objective: repair `fetch_time_series_batch_from_db` prospective post-time target
  selection so a same-day `RT_RA` lifecycle row supersedes the matching historical
  `NL_RA` row before fail-closed post-time validation. Preserve rejection of true
  same-source ambiguity and honor a current realtime cancellation without falling
  back to the stale historical row.
- Minimum scope: `src/fetcher/realtime.py`, the smallest regression coverage in
  `tests/test_time_series.py`, version/release metadata for patch `2.1.2`, and this
  tracked worklog. No schema, storage, migration, or provider-write change.
- Repository: `miyamamoto/jrvltsql`.
- Worktree:
  `/home/keiba/worktrees/jrvltsql-hotfix-2.1.2-race-lifecycle-overlay-20260905`.
- Branch: `hotfix/2.1.2-race-lifecycle-overlay`.
- Hotfix base / production release: tag `v2.1.1`, full SHA
  `0f3161d30de65f15795608e2a4bec9fc91e05349`.
- Development branch observed after `git fetch origin master --tags --prune`:
  `origin/master` at `2e58b17f6177eb0e0bc5bd097fa0b181ed2d7ba4`.
- Intended integration order: create `release/2.1.2` from the exact `v2.1.1`
  commit; merge this hotfix there; publish immutable `v2.1.2`; then forward-port
  the same repair to `master` in a separate PR.
- Downstream dependency: `miyamamoto/jrvltsql-wine-runtime` must pin the resulting
  merged `jltsql` source/artifact before KPS JRA prospective capture can be
  considered repaired. The first complete prospective proof must come from a
  future real race day; this hotfix does not backfill 2026-09-05.
- Release classification: emergency correctness hotfix. On 2026-09-05 a stale
  `NL_RA` post time and a revised `RT_RA` post time for the same full race key were
  UNIONed and interpreted as ambiguity before window filtering, aborting later
  due races and leaving JRA race 06-12 without official O1/O2 capture.
- Rollback: reinstall/re-pin immutable `v2.1.1` at
  `0f3161d30de65f15795608e2a4bec9fc91e05349`; no database rollback is required.

## Guardrails

- Add the failing regression first and record its exact failure before modifying
  production code.
- Missing, malformed, or truly ambiguous current lifecycle data remains a hard
  failure. A current `RT_RA` row, including cancellation status, owns the full
  race key; an older `NL_RA` row is used only when that key is absent from
  `RT_RA`.
- All tests run at `nice -n 15`. Do not inspect, open, signal, reprioritize, or
  otherwise interact with the concurrent NAR P8 DuckDB workload.
- No credentials or connection strings are recorded.

## Chronology

- 2026-09-05: read the complete release-readiness skill and its release/host
  references. Read `docs/release_policy.md`; no repository or ancestor
  `AGENTS.md` exists in this checkout. Ran the JRA readiness scan: 58 PASS,
  2 pre-existing KPS WARN, 0 FAIL.
- 2026-09-05: fetched `origin/master` and tags, verified the exact base and
  development SHAs above, created this dedicated worktree from `v2.1.1`, and
  confirmed the worktree was initially clean.
- 2026-09-05: selected Claude Code `--model fable` for the implementation
  (`claude-fable-5`, CLI 2.1.233), because this is a fail-closed lifecycle
  selector whose source precedence and cancellation boundaries directly alter
  collection decisions. Session ID for same-worktree continuation:
  `26f1d160-d2a4-41b4-994a-c95fe270a934`.
- 2026-09-05 RED: added four focused lifecycle tests without changing
  production code. After tightening the incident fixture to the actual Nakayama
  key shape (`20260905-06-08`, stale `NL_RA` 14:00 versus current `RT_RA`
  `DataKubun=6` 14:01, with 06-12 at 16:30), ran:
  `nice -n 15 python3 -m pytest tests/test_time_series.py -k 'rt_lifecycle' -v`.
  Result: **3 failed, 1 passed, 26 deselected**. The primary red was
  `FetcherError: ... 202609050608: ambiguous HassoTime values [1400, 1401]`;
  cancellation red opened both `202609050611` and `202609050612` instead of
  only race 12; PostgreSQL-query parity reproduced the same ambiguity. The
  paired selected-source conflict test remained green, proving the existing
  fail-closed boundary that the repair must preserve.
- 2026-09-05 GREEN: implemented the minimal repair in `src/fetcher/realtime.py`
  only. When a post-time window is requested and `RT_RA`/`rt_ra` exists, the
  SQLite and PostgreSQL target queries tag each row with its lifecycle source
  and `DataKubun` and use `UNION ALL`; the new `_overlay_current_lifecycle_rows`
  helper then selects by the exact full key (Year, MonthDay, JyoCD, Kaiji,
  Nichiji, RaceNum): any `RT_RA` row owns its full key regardless of
  `DataKubun` (including 9), `NL_RA` is used only for full keys absent from
  `RT_RA`, and duplicates within the selected source are preserved. Selected
  rows still pass the unchanged fail-closed `_filter_race_rows_by_post_time`
  validation; only after validation are full keys canceled by RT `DataKubun=9`
  omitted, with no NL fallback. The no-window queries (both engines) and the
  NL-only window path are untouched; no schema, storage, migration, or
  provider-write change.
- 2026-09-05 GREEN evidence: the PATH `pytest` shim runs Python 3.10 and fails
  one unrelated parser-import test (`StrEnum`; project requires >=3.12), so the
  gates ran on the uv-managed venv (CPython 3.13.5) with pinned lock:
  `nice -n 15 uv run --frozen --extra dev pytest tests/test_time_series.py -k
  'rt_lifecycle' -v --no-cov` -> **4 passed, 26 deselected in 0.30s**;
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py --no-cov` -> **30 passed in 0.52s**. Version
  metadata and release docs intentionally not yet touched.
- 2026-09-05 RED (refinement before candidate freeze): critical review of the
  implemented overlay found three fail-closed gaps; added the smallest failing
  coverage without touching production code. (a) A selected lifecycle row with
  missing/blank/officially-invalid RA `DataKubun` (official domain:
  `src/parser/status_domain.py`) is silently treated as active — the new
  parameterized `test_sqlite_race_window_rt_lifecycle_rejects_undecidable_datakubun`
  ((RT, None), (RT, ""), (RT, "8"), (NL, " "), (NL, "９")) expects a
  `FetcherError` naming `202609050610` and got **DID NOT RAISE** in all five
  cases. (b) A canceled row owned by NL (06-10 `DataKubun=9`, absent from
  RT_RA) is opened — the extended cancellation test failed with
  `('0B41', '202609050610')` opened before race 12; RT-9-blocks-NL-fallback
  is asserted in the same test. (c) Window statistics keep omitted
  cancellations — PG-parity red `assert 2 == 1` on `window_kept_keys` (the
  run log even printed `omitted_canceled_keys=1` while stats did not carry
  it), and the exact-progress test is red for the missing
  `omitted_canceled_keys: 0` key in the no-cancellation shape. Command:
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'rt_lifecycle or keeps_near_post' -v --no-cov`
  -> **8 failed, 2 passed, 25 deselected in 0.43s**; the overlay and
  selected-source conflict tests stayed green. No src/, version-metadata, or
  release-doc change in this step.
- 2026-09-05 GREEN (refinement): minimal production changes in
  `src/fetcher/realtime.py` only. Every selected lifecycle row's DataKubun is
  now validated with the official
  `src.parser.status_domain.validate_data_kubun` for record type `RA`
  (REALTIME context for RT rows, ACCUMULATED for NL rows; no ad-hoc accepted
  set); a validation failure is converted to `FetcherError` naming the
  12-digit race key and no key is opened. Cancellation (validated
  `DataKubun=9`) is collected from whichever selected source owns the full
  key, strictly after source selection, so RT 9 still never exposes the
  shadowed NL row; HassoTime validation-before-cancellation and same-source
  post-time conflict fail-closed ordering are unchanged. Window stats are now
  truthful: `omitted_canceled_keys` is always exposed (0 when none) and
  `window_kept_keys` is reduced by the omitted count so it equals
  `total_keys` and the opened targets. The stat is documented on
  `fetch_time_series_batch_from_db` and the overlay helper as counting
  selected cancellations that passed validation and otherwise fell inside
  the requested window. Evidence (uv-managed CPython 3.13.5, frozen lock):
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'rt_lifecycle or keeps_near_post' -v --no-cov`
  -> **10 passed, 25 deselected in 0.35s**;
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py --no-cov` -> **35 passed in 0.60s**. Version
  metadata and release docs still untouched.
- 2026-09-05 RED (no-RT_RA boundary before candidate freeze): the refined
  implementation gates lifecycle validation/cancellation on the presence of
  the optional `RT_RA` table, but the selection contract makes NL own every
  key when `RT_RA` is absent, so NL `DataKubun` must still be validated and
  canceled instead of reverting to the unclassified 7-column path. Added two
  minimal SQLite regressions with no `RT_RA` table (the fixture helper can
  now create `NL_RA` alone):
  `test_sqlite_race_window_rt_lifecycle_nl_owns_all_keys_when_rt_table_absent`
  (NL 06-11 `DataKubun=9` in-window plus active 06-12; expects only race 12
  opened with `omitted_canceled_keys=1`, `window_kept_keys=1`,
  `total_keys=1`) is red: `('0B41', '202609050611')` was opened ahead of
  race 12.
  `test_sqlite_race_window_rt_lifecycle_rejects_undecidable_nl_datakubun_when_rt_table_absent`
  (NL 06-10 `DataKubun='8'`) is red with **DID NOT RAISE**; the run log shows
  both `202609050610` and `202609050612` were opened. Command:
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'rt_lifecycle or keeps_near_post' -v --no-cov`
  -> **2 failed, 10 passed, 25 deselected in 0.43s**; all 10 previously
  green lifecycle/stats tests stayed green. GREEN note: the real schema
  already carries `DataKubun`, but the older synthetic NL-only window
  fixtures (`keeps_near_post`, `skips_malformed`, `boundary_date`,
  `candidate_fails_closed`, and the PostgreSQL no-rt fakes returning
  7-column rows) do not; extending the no-RT window query to read NL
  `DataKubun` will require adding that column to those fixtures. No src/,
  version-metadata, or release-doc change in this step.
- 2026-09-05 GREEN (no-RT_RA boundary): both engines' post-time-window target
  queries now always emit source-tagged lifecycle rows with `DataKubun`;
  when `RT_RA`/`rt_ra` is absent the query tags `NL` alone so NL owns every
  full key, and validation/cancellation run through the same
  `_overlay_current_lifecycle_rows` path (the conditional overlay flag was
  removed; the window path is now unconditionally lifecycle-classified).
  No-window queries are untouched on both engines and the exact no-window
  PostgreSQL query contract test still passes. The legacy synthetic window
  fixtures now model the real `NL_RA.DataKubun` column (`keeps_near_post`,
  `skips_malformed`, `boundary_date`, `candidate_fails_closed` SQLite tables,
  plus the PostgreSQL no-rt fake rows, now 9-column 'NL'-tagged) without
  weakening any assertion; the PostgreSQL no-rt window test additionally
  pins `datakubun` in the generated query. Evidence (uv-managed CPython
  3.13.5, frozen lock): `nice -n 15 uv run --frozen --extra dev
  --extra postgres pytest tests/test_time_series.py -k 'race_window' -v
  --no-cov` -> **22 passed, 15 deselected in 0.51s** (every window-path
  test, including both no-RT reds, now green);
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py --no-cov` -> **37 passed in 0.61s**. Version
  metadata and release docs still untouched.
- 2026-09-05 metadata: synchronized patch release metadata to `2.1.2` with
  behavior green. Changed files: `pyproject.toml` and `src/__init__.py`
  (2.1.1 -> 2.1.2); `uv.lock` project entry updated via `uv lock`
  ("Updated jltsql v2.1.1 -> v2.1.2", diff confirmed to touch only that
  version line); exact-version contract tests
  (`tests/test_public_setup_contract.py`: Unreleased compare link now
  `v2.1.2...HEAD` and project version pin; `tests/test_updater.py`:
  pyproject-fallback version); `CHANGELOG.md` (new `[2.1.2] - 2026-09-05`
  lifecycle-overlay/cancellation/fail-closed/stats entry, Unreleased link
  moved to `v2.1.2...HEAD`, `[2.1.2]` compare link added);
  `RELEASE_NOTES.md` (prepended v2.1.2 scope, verification limits — no live
  JV-Link race day yet, PostgreSQL window query verified on an equivalent
  SQLite model — no schema/migration requirement, downstream
  `jrvltsql-wine-runtime` re-pin note, rollback; older notes preserved).
  Focused gate: `nice -n 15 uv run --frozen --extra dev --extra postgres
  pytest tests/test_public_setup_contract.py
  "tests/test_updater.py::TestGetCurrentVersion" -v --no-cov` ->
  **14 passed in 0.17s**, including source/lock/CLI version consistency.
  Full suite, build, and distribution smoke intentionally not yet run; no
  commit/push yet. Planned rollback: re-adopt immutable `v2.1.1` at
  `0f3161d30de65f15795608e2a4bec9fc91e05349`; no database rollback required.
- 2026-09-05 RED (CLI window stdout contract): the downstream
  `jrvltsql-wine-runtime` parses the CLI `Window:` stdout line, but
  `omitted_canceled_keys` exists only in the progress dict. Extended the
  existing focused test
  `tests/test_cli.py::TestRealtimeTimeseriesCommand::test_timeseries_passes_race_window_options_and_reports_selection`
  with `omitted_canceled_keys: 2` in the fake window progress and one exact
  token/order assertion:
  `Window: considered=3 candidates=3 kept=1 canceled=2 future=1 past=1
  date_excluded=0`. Command: `nice -n 15 uv run --frozen --extra dev
  --extra postgres pytest "tests/test_cli.py::TestRealtimeTimeseriesCommand::
  test_timeseries_passes_race_window_options_and_reports_selection" -v
  --no-cov` -> **FAILED**: the token string was `not found in` the captured
  output, whose actual line is `Window: considered=3 candidates=3 kept=1
  future=1 past=1 date_excluded=0` — `canceled=` is absent from the
  unchanged CLI. GREEN note: `console = Console(legacy_windows=True)` wraps
  at width 80 in non-tty captures; the extended line is 85 characters, so
  emitting `canceled=` must also guarantee the line stays unwrapped (e.g.
  `soft_wrap=True`) or the exact-token contract will break in captures. No
  production-code change in this step.
- 2026-09-05 GREEN (CLI window stdout contract): `src/cli/main.py` window
  progress line now emits `canceled={omitted_canceled_keys}` between `kept=`
  and `future=` in the exact tested token order, defaulting to 0, and that
  single machine-parsed `console.print` uses `soft_wrap=True` so the
  85-character line stays unwrapped in captured/non-TTY output; no other
  output changed. Evidence (uv-managed CPython 3.13.5, frozen lock,
  dev+postgres, nice -n 15): the focused test
  `tests/test_cli.py::TestRealtimeTimeseriesCommand::test_timeseries_passes_race_window_options_and_reports_selection`
  -> **1 passed in 0.07s**; class `TestRealtimeTimeseriesCommand` ->
  **4 passed in 1.23s**; full `tests/test_cli.py` -> **47 passed in 2.01s**.
- 2026-09-05 RED (nonempty capture evidence): `success_keys` counts a key as
  ok even when JVRTOpen succeeds but `_fetch_and_parse()` yields zero rows,
  so downstream evidence cannot distinguish nonempty capture. Added the
  smallest failing coverage without touching src. New
  `test_fetch_time_series_batch_from_db_counts_nonempty_keys` (two keys:
  open-success with 0 rows, then open-success with 1 row) is red with
  `KeyError: 'nonempty_keys'` after proving the substitution — the empty key
  passed `status == "success"`, `success_keys == 1`, `records_for_key == 0`.
  Extended `test_fetch_time_series_batch_from_db_closes_no_data_stream`
  (no_data per-key shape) -> red `KeyError: 'nonempty_keys'`. Extended the
  exact window_filter progress dict in
  `test_sqlite_race_window_keeps_near_post_and_reports_drop_reasons` with
  `nonempty_keys: 0` -> red "Right contains 1 more item:
  {'nonempty_keys': 0}". Extended the focused CLI progress test with a fake
  final key progress carrying `nonempty_keys: 1` and the exact Keys token
  order -> red: `'ok=1 nonempty=1 no_data=0' not found`, actual line is
  `Keys: 1/1 ok=1 no_data=0 errors=0 records=3`. The structured completion
  summary is a structlog line (not a callback contract); the CLI final Keys
  line covers the user-facing summary instead. Commands:
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'counts_nonempty or closes_no_data_stream or
  keeps_near_post' -v --no-cov` -> **3 failed, 1 passed, 34 deselected**
  (the passing one is the unaffected range-scan close test);
  same runner on the focused CLI test -> **1 failed**. No src/,
  version-metadata, or release-doc change in this step.
- 2026-09-05 RED (idle-window Keys summary): added the focused CLI test
  `test_timeseries_window_idle_run_emits_zero_keys_summary` (same fixture
  pattern as the window test): the fetcher emits only a `window_filter`
  progress with `total_keys=0` (kept=0, canceled=1, past=1) and yields no
  records. The contract requires exactly one terminal no-`last=` summary
  line per spec containing
  `Keys: 0/0 ok=0 nonempty=0 no_data=0 errors=0 records=0`, with the
  Window line separate. Red as intended: the Window assertion passes but
  the Keys count is **`AssertionError: 0 != 1`** — the final summary is
  guarded by `if key_progress["processed_keys"]:` in the unchanged CLI, so
  an idle window day emits no machine-checkable "nothing was opened"
  evidence. Command: `nice -n 15 uv run --frozen --extra dev
  --extra postgres pytest "tests/test_cli.py::TestRealtimeTimeseriesCommand::
  test_timeseries_window_idle_run_emits_zero_keys_summary" -v --no-cov` ->
  **1 failed in 0.09s**. No src/ change in this step.
- 2026-09-05 GREEN (nonempty + idle batch): `fetch_time_series_batch_from_db`
  now tracks `nonempty_keys` (initialized 0, incremented only after one
  complete buffered key materializes >0 records) and includes it, always
  present including zero, in every progress shape — `window_filter`,
  `invalid_key`, the shared per-key status callback — and in the structured
  "Batch time series fetch completed" log. The CLI initializes
  `nonempty_keys: 0` in `key_progress`, emits `nonempty=` between `ok=` and
  `no_data=` on both the intermediate and terminal `Keys:` lines, marks both
  machine-parsed lines `soft_wrap=True`, and prints the terminal no-`last=`
  summary whenever a post-time window was requested OR keys were processed,
  so an idle 0/0 window day emits the summary exactly once while legacy
  no-window/no-key output stays silent. `CHANGELOG.md`/`RELEASE_NOTES.md`
  now describe the machine-readable canceled/nonempty/idle progress and
  correct the earlier no-window claim: target selection/queries stay
  unchanged without a window, but `Keys:` lines gain `nonempty=` whenever a
  key is processed. Evidence (uv CPython 3.13.5, frozen, dev+postgres,
  nice -n 15): previously red set
  (`counts_nonempty or closes_no_data_stream or keeps_near_post`) ->
  **4 passed, 34 deselected in 0.12s**; the two focused CLI window tests ->
  **2 passed in 0.07s**; full `tests/test_time_series.py` -> **38 passed in
  0.65s**; full `tests/test_cli.py` -> **48 passed in 1.71s**; doc-reading
  `tests/test_public_setup_contract.py` -> **9 passed in 0.12s**. Full
  repository suite and commit intentionally deferred.
- 2026-09-05 release-path CI gate: `docs/release_policy.md` mandates merging
  the hotfix PR into `release/X.Y.Z`, but `.github/workflows/test.yml`
  limited the `pull_request` trigger to `[ master, main, develop ]`, so the
  required release PR could never receive the authoritative Tests gate.
  Decision: fail-closed contract first, then the minimal trigger change.
  Added `test_tests_workflow_gates_release_hotfix_pull_requests` to
  `tests/test_public_setup_contract.py` (parses the workflow YAML, tolerates
  the YAML 1.1 `on`->True key, requires `release/**` in
  `pull_request.branches`). Red against the unchanged workflow:
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  "tests/test_public_setup_contract.py::
  test_tests_workflow_gates_release_hotfix_pull_requests" -v --no-cov` ->
  **FAILED**, `AssertionError: assert 'release/**' in
  ['master', 'main', 'develop']`. Then extended only the `pull_request`
  trigger to `[ master, main, develop, 'release/**' ]` — push triggers
  unchanged (policy publishes from PR-gated release branches; no push gate
  is required for them). Green: the focused test -> **1 passed in 0.03s**;
  full `tests/test_public_setup_contract.py` -> **10 passed in 0.13s**.
  Not committed.
- 2026-09-05 candidate hardening (still uncommitted): Black formatted the six
  affected Python files and its scoped `--check` is green; `git diff --check`
  is green. The workflow-equivalent fatal Flake8 gate (`--isolated --select=
  E9,F63,F7,F82` over `src tests scripts tools`) reports **0**. A configured
  scoped Ruff comparison over the six affected Python files reports the same
  **58 pre-existing diagnostics** on the candidate as exact `v2.1.1` after
  correcting one newly introduced local-import order (baseline 58; candidate
  58; no new diagnostic). A direct-module scoped MyPy comparison with
  `--follow-imports=skip --ignore-missing-imports --no-strict-optional` first
  found one new `no-any-return` at `_race_key_label`; wrapping the external
  key generator result in `str()` removed it. Candidate and exact-v2.1.1
  baseline now carry the identical **12 pre-existing diagnostics** (11 in
  existing realtime paths plus missing PyYAML stubs in CLI), with no new
  diagnostic. Baseline worktree:
  `/home/keiba/scratch/20260905_jrvltsql_211_lint_baseline`, detached at
  `0f3161d30de65f15795608e2a4bec9fc91e05349`.
- 2026-09-05 focused post-format gate: `nice -n 15 uv run --frozen --extra
  dev --extra postgres pytest tests/test_time_series.py tests/test_cli.py
  tests/test_public_setup_contract.py tests/test_updater.py -v --no-cov` ->
  **118 passed, 22 subtests passed in 2.61s**.
- 2026-09-05 full local Tests-workflow gate: `nice -n 15 uv run --frozen
  --extra dev --extra postgres pytest tests --ignore=tests/integration
  --ignore=tests/e2e -m "not slow" -v --cov=src --cov-report=xml
  --cov-report=term` -> **4872 passed, 514 skipped, 14 deselected, 33
  subtests passed in 118.20s**, total coverage **80%**. Skips are the suite's
  environment-gated PostgreSQL/provider cases; no failure occurred.
- 2026-09-05 provisional distribution gate (uncommitted tree; must be rebuilt
  from the immutable merge SHA before publication): built `jltsql-2.1.2.tar.gz`
  and `jltsql-2.1.2-py3-none-any.whl` outside the repository at
  `/home/keiba/scratch/20260905_jrvltsql_212_dist.f7tmoa`. Distribution
  contents check passed for both and wheel init smoke passed. Wheel METADATA
  reports version `2.1.2`; embedded `src/fetcher/realtime.py` and
  `src/cli/main.py` SHA-256 values exactly equal the working-tree sources
  (`c3dc2f7caa15793d07e3b0e4a51956d7a409e6d291e0622fb632d92d400c46e5`
  and `60924eeb0df12bbbfca2718deb68cb9f556add46fc1093b4449675876ab717df`).
  Provisional artifact hashes: sdist
  `67649f5de39ebedd7fbf13721962454ef9525cbfb3694434b3b49fe887f60ad7`;
  wheel `fc07d18555742e5e13dd4a76ec9ed84a0cad26614c5ae0357c895cef58a65336`.
  These are local pre-freeze evidence, not the authoritative release hashes.
- 2026-09-05 independent review of frozen candidate
  `589a3c08cf39f2a9065cfea965dfd49cc4df33b8` returned NEEDS_CHANGES on two
  P1 fail-open lifecycle edges. The reviewer reproduced that two selected RT
  full keys with different Kaiji/Nichiji but the same 12-digit JVRTOpen key,
  same HassoTime, and active/canceled states were opened or omitted according
  to row order; cancellation was tracked by full key after the post-time
  filter had collapsed to `rows[0]`. The reviewer also reproduced that the
  official RA `DataKubun=0` erase state passed domain validation and was
  treated as an active target. The original Claude Fable implementer session
  reached its session quota before this review response, so one Codex teammate
  is applying the batched review repair; this does not change the recorded
  Fable implementation provenance above.
- 2026-09-05 RED (batched independent-review repair, before any src change):
  added one two-order regression for the physically possible distinct-full-key
  collision (RT DK6 and RT DK9, identical 12-digit key and HassoTime) and one
  RT/NL ownership parameterization for an unexpectedly persisted RA DK0 erase
  marker. Both require `FetcherError` naming the 12-digit key before JV init.
  Command: `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'mixed_state_fails_closed_before_init or
  persisted_erase_fails_closed_before_init' -v --no-cov` -> **4 failed, 38
  deselected in 0.19s**, all with `DID NOT RAISE`. Active-first opened
  `202609050612` with `omitted_canceled_keys=0`; canceled-first omitted that
  same key with `omitted_canceled_keys=1`, proving row-order dependence. Both
  RT-owned and NL-owned DK0 rows opened `202609050610`. No production source
  was changed in this RED step.
- 2026-09-05 batched repair (Codex teammate; still uncommitted): lifecycle
  source ownership remains exact-full-key-first, then every selected row is
  validated against the official RA domain. A selected persisted DK0 erase
  marker now raises `FetcherError` naming its normalized 12-digit key before
  JV init. Selected rows are grouped by that 12-digit JVRTOpen key; any
  active/canceled mixture now fails closed independent of input order. An
  all-DK9 group remains in post-time validation and is removed/counts as one
  normalized key only afterwards, preserving genuine HassoTime-conflict
  failure and the established window statistics. The existing cancellation
  test now covers two distinct canceled full keys collapsing to one 12-digit
  key. Changed paths are `src/fetcher/realtime.py`,
  `tests/test_time_series.py`, `CHANGELOG.md`, `RELEASE_NOTES.md`, and this
  worklog.
- 2026-09-05 documentation scope correction: the normal updater physically
  removes RT DK0. Therefore, this read path cannot distinguish an already
  removed tombstone from no RT update, and preventing stale-NL resurrection
  after an erase is **not proven**. CHANGELOG and release notes now say so and
  no longer claim unconditional lifecycle correctness regardless of
  DataKubun. A persisted DK0 is rejected; an absent tombstone remains a
  pre-existing storage-semantics limitation requiring separate work.
- 2026-09-05 GREEN after the production repair and Black:
  `nice -n 15 uv run --frozen --extra dev --extra postgres pytest
  tests/test_time_series.py -k 'mixed_state_fails_closed_before_init or
  persisted_erase_fails_closed_before_init' -v --no-cov` -> **4 passed, 38
  deselected in 0.12s**. Full affected file with the existing active,
  cancellation, invalid-domain, RT-table-absent, genuine HassoTime-conflict,
  PostgreSQL parity, and no-window coverage: `nice -n 15 uv run --frozen
  --extra dev --extra postgres pytest tests/test_time_series.py -v --no-cov`
  -> **42 passed in 0.70s**. Release-document contract: `nice -n 15 uv run
  --frozen --extra dev --extra postgres pytest
  tests/test_public_setup_contract.py -v --no-cov` -> **10 passed in 0.13s**.
- 2026-09-05 formatting/static/diff gates for this repair: `nice -n 15 uv run
  --frozen --extra dev --extra postgres black src/fetcher/realtime.py
  tests/test_time_series.py` and the matching `black --check` both reported
  **2 files unchanged**; isolated fatal lint (`flake8 ... --select=E9,F63,F7,F82`)
  reported **0**; `git diff --check` passed. The five intended files remain
  dirty by explicit handoff instruction; no commit or push was made. Because
  the independent reviewer implemented the repair, a newly frozen full SHA
  still requires a different independent reviewer before release.
- 2026-09-05 remote release-track setup (state-changing, verified): read-only
  `git ls-remote` first proved `release/2.1.2`, `stable/2.1`, `v2.1.2`, and the
  hotfix branch absent. `git push --dry-run origin 0f3161d...:refs/heads/
  release/2.1.2` showed only one new branch; the matching apply succeeded.
  Post-fetch verification proved remote `release/2.1.2` equals exact v2.1.1
  `0f3161d30de65f15795608e2a4bec9fc91e05349` with zero commits beyond it.
  The hotfix push also ran dry first, then applied, and remote verification
  proved candidate `589a3c08cf39f2a9065cfea965dfd49cc4df33b8` exactly. Rollback handles before
  merge are deletion of those two newly-created remote branches; immutable
  v2.1.1 remains the code rollback. No tag or stable branch was created.
- 2026-09-05 PR state (state-changing, verified): opened hotfix PR
  `https://github.com/miyamamoto/jrvltsql/pull/267` from the hotfix branch into
  exact-base `release/2.1.2`. The newly added release-branch trigger worked:
  authoritative Tests run `33959351499` started for candidate `589a3c08...`.
  As soon as independent review reported the first P1, the measured open/ready
  PR was converted to draft and labeled `release:blocker`,
  `release:hotfix-candidate`, `risk:data-integrity`, and `risk:provider`;
  re-read verification confirmed draft=true and the exact labels. Candidate
  `589a3c08...` must not be merged, tagged, released, or adopted.
- 2026-09-05 parent independently confirmed the STOP state: keep PR 267 draft,
  batch both P1 repairs red-first, disclose the tombstone limitation, and mark
  ready only after new exact-head affected plus required workflow-equivalent
  gates and final review. The repaired focused aggregate was independently
  rerun in this agent: four affected files -> **122 passed, 22 subtests passed
  in 2.61s**; Black check, diff check, and fatal Flake8 remain green. Scoped
  Ruff has no new debt (57 candidate diagnostics versus 58 on exact v2.1.1),
  and scoped MyPy has no new diagnostic (11 candidate versus 12 baseline).
- 2026-09-05 repaired candidate freeze and remote verification: committed the
  two P1 repairs as `ea187ee586d16a65826b104bf00756bb87229918`
  (`fix(realtime): reject ambiguous lifecycle states`), pushed only after a
  successful dry-run, and verified the remote hotfix branch and PR 267 head
  equal that full SHA. The obsolete `589a3c08...` candidate remains explicitly
  non-releasable. PR 267 remained draft with `release:blocker` throughout.
- 2026-09-05 repaired-candidate exact-head gates: the workflow-equivalent full
  suite on `ea187ee586d16a65826b104bf00756bb87229918` completed with **4876
  passed, 514 skipped, 14 deselected, 33 subtests passed in 119.90s**, total
  coverage **80%**. `scripts/validate_test_gate.py` returned `TEST GATE PASS`;
  isolated fatal Flake8 returned 0; Black check over every changed Python file
  and `git diff --check` passed. Scoped comparisons remain no-new-debt: Ruff
  57 candidate versus 58 exact-v2.1.1 baseline, MyPy 11 versus 12.
- 2026-09-05 repaired-candidate provisional distribution gate: built outside
  the repository at
  `/home/keiba/scratch/20260905_jrvltsql_212_repaired_dist.Q4M5jl`.
  Distribution-content and wheel-init smoke checks passed; METADATA is exactly
  version `2.1.2`. Wheel copies of `src/fetcher/realtime.py` and
  `src/cli/main.py` equal the candidate sources by SHA-256
  (`fff3582543c7d15abf83bc47d6d655c6c93ce947f84ad94c745426aa67111127`
  and `60924eeb0df12bbbfca2718deb68cb9f556add46fc1093b4449675876ab717df`).
  Provisional artifact hashes are sdist
  `8ba6081ba6bfde324908371cc30523db32540d86a904ed773ed8b6199512fe19`
  and wheel
  `a9a58f6963c2674f8198520ae0d2f8d13f234e6d83100476b06f514a9e0e27b6`.
  They are not release artifacts and must not be published or pinned.
- 2026-09-05 authoritative GitHub Actions for the repaired code candidate:
  Tests run `33959854432` is `success` for exact head
  `ea187ee586d16a65826b104bf00756bb87229918`; jobs `test`, `lint`, and
  `windows-batch-syntax` all succeeded, while the PR-inapplicable performance
  job was skipped by its declared condition. The test job executed the
  fail-closed gate, full suite, distribution-content check, and wheel-init
  smoke. The PR remains draft/blocking until the different independent
  reviewer finishes and this final tracked handoff update receives exact-head
  CI.

## Pending safe sequence and STOP conditions

1. Commit and push this documentation-only handoff update, then repeat the
   required exact-head gates and obtain final confirmation from the different
   independent reviewer. Keep PR 267 draft/blocking until all actionable
   findings are closed.
2. Verify authoritative CI and unresolved-thread count on the final head,
   remove `release:blocker`, mark ready, and merge only from authoritative state.
3. Rebuild and hash the authoritative release artifacts from the immutable merge
   SHA, publish `v2.1.2`, advance `stable/2.1` to the same commit, and provide the
   merged tag/source/wheel pins to downstream `jrvltsql-wine-runtime`.
4. Forward-port the repair from the published hotfix into current `master` by a
   separate PR, preserving dependency order and recording its merge SHA.

STOP on any fail-open path, unexpected database/schema change, failing test,
non-authoritative merge state, unresolved review thread, artifact/source mismatch,
or a need to touch the NAR P8 process or its target database.
