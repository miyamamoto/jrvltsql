# JVOpen bounded setup worklog — 2026-08-22

## Objective and minimum scope

Repair the JRA RACE official-setup transport so a requested date range is
bounded at JVOpen rather than fetched as one unbounded tail. The minimum
iteration is:

1. send the official start/end `fromtime` form for end-capable setup specs;
2. preserve the official start-only form for specs that forbid an end point;
3. make long option-4 setup partitioning truly bounded and resumable without
   weakening transaction, cache-complete, parser-rejection, or failure
   semantics; and
4. correct CLI/docs claims so operators do not mistake a client-side filter
   for a provider download bound.

Do not change record parsers, schemas, service-key/registration handling,
provider identity, realtime collection, production release `2.0.0`, or KPS
model/feature work in this iteration. Do not run another live setup until the
code is reviewed, merged, released as a new `2.0.0.dev*` wheel, and pinned by
the development runtime.

## Repository and immutable start state

- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260822_jrvltsql_bounded_setup`
- Branch: `fix/jvopen-bounded-setup-20260822`
- Base / initial HEAD / `origin/master`:
  `3c4650dfceb96df89808291ef29191de506ef85f`
- Related installed/release version: `2.0.0.dev2`
- Upstream runtime image used for the reproducer:
  `kps-jra-collector-dev:e97924fd32049d41f77bafb8634dd32aedc06d17`
- KIR operational evidence PR: #167, current evidence head
  `7495b6eee9fbef965ceb20af90f7a306e29f3884`
- This worktree started clean. The separate checkout `/home/keiba/jrvltsql`
  already contained unrelated uncommitted realtime changes and must not be
  edited or cleaned by this iteration.

## Observed failure and official oracle

- A RACE option-4 setup for 2025-08-20..2026-08-19 completed in about
  32 minutes 37 seconds with `Fetched=135354`, `Parsed=22555875`,
  `Imported=22555874`, `Failed=0`.
- The next RACE option-4 scope, 2024-08-20..2026-08-19, remained live for the
  exact configured 7,200 seconds but returned no JVOpen response. It exited 1
  with `Bridge response timeout (7200.0s)`, counters zero, empty cache
  checkpoints, no cache commit, no success progress ledger, unchanged durable
  DB rows, and unchanged provider-local Data Lab files.
- Pinned official oracle:
  `JV-Linkインターフェース仕様書_4.9.0.1(Win).pdf`, SHA-256
  `3167d5c98d8db78321a983cd2d897e1b5a9f42f141490f9ba817ca0dcf9d2364`.
  Pages 17--20 define `fromtime` as either one start timestamp or start/end
  timestamps joined by `-`. RACE is not in the explicit list that forbids an
  end timestamp. The same section documents options 3/4 and setup
  interruption/resume.
- Exact `2.0.0.dev2` constructs only
  `fromtime = f"{from_date}000000"`; `to_date` is a client-side record filter.
  Its option-3 yearly recursion therefore repeats all later provider data, and
  option 4 is deliberately left as one unbounded open to avoid that O(n^2)
  repetition. The two-hour failure is consequently not evidence that a
  bounded yearly setup was attempted.

## Red-first and implementation contract

Before production changes, add the minimum regression coverage and run it on
this exact base. It must prove at least:

- bounded RACE setup calls JVOpen with the inclusive-date encoding
  `(from_date - 1 second at midnight)-to_date 23:59:59`, for example
  `20250819235959-20260819235959` for 2025-08-20..2026-08-19 (base must fail
  because it sends only `20250820000000`);
- an end-forbidden setup spec such as DIFN remains start-only (paired green);
- option-4 long ranges partition into exact, nonoverlapping bounded chunks and
  do not repeat the open tail;
- a failed later chunk is not recorded complete and cannot silently discard or
  double-count an already durable earlier chunk; and
- invalid/missing dates fail before JV-Link or database mutation.

Record the exact pre-fix failure in this worklog and in the commit/PR evidence.
Do not add one test per reviewer hypothesis; extend the existing historical or
batch-processor contracts with the smallest table/parameterized coverage that
actually turns red.

## Coding-agent session

- Claude Code version: `2.1.233` (verified in-session via `claude --version`).
- Model: `--model fable`, selected because this changes a fail-closed transport
  gate plus range partition, transaction order, cache completion and resume
  semantics.
- Session ID: `ecb0bbe6-e0b1-4923-b214-07698693c5a7`
- Continue this same session with `--resume` for review fixes in this
  iteration. If context becomes too long, summarize here before starting a new
  session.

## STOP conditions

- Stop on worktree drift not created by this iteration.
- Stop before any live provider operation, runtime image/wheel publication,
  release tag, production deployment, Wine-prefix reset, registration change,
  service-key output, or KIR/KPS mutation.
- A missing official answer, unbounded provider call, cache range falsely
  complete after failure, lost previously committed chunk, or transaction
  ownership ambiguity is a blocker, not a reason to loosen the gate.

Next safe command (superseded — see "Next safe action" at the end): commit and
push this initial worklog, then start Claude Code `2.1.233` with `--model
fable --session-id ecb0bbe6-e0b1-4923-b214-07698693c5a7` in this worktree.
Require it to inspect the official evidence and current tests, run the red
test against exact base, implement the smallest coherent repair, run focused
tests, update this worklog, and stop before commit/push/PR so the primary
agent can inspect the result.

## Implementation record — 2026-08-22, session `ecb0bbe6-e0b1-4923-b214-07698693c5a7`

Model `claude-fable-5` (Fable 5) on Claude Code `2.1.233`, working only in
this worktree on top of the immutable base (`d7a1523` = worklog only, code
identical to `3c4650d`). No commit/push/PR/release/provider/database action
was performed; the diff is left uncommitted for primary-agent review.

### Official oracle verification

- `/home/keibadb/work/keibadb/jra-van/docs/JV-Link4901.pdf` has SHA-256
  `3167d5c98d8db78321a983cd2d897e1b5a9f42f141490f9ba817ca0dcf9d2364`, byte
  identical to the pinned
  `JV-Linkインターフェース仕様書_4.9.0.1(Win).pdf` inside the SDK directory.
- Pages 17-20, read in-session: `fromtime` has exactly two forms — one start
  point, or start-end joined by a half-width hyphen; eligibility is
  "strictly greater than the start point, up to and including the end
  point". The end point is forbidden for TOKU, DIFF, DIFN, HOSE, HOSN,
  HOYU, COMM ("全データを取得するため"; specifying one returns -1, which is
  indistinguishable from a legitimate no-data response). RACE is not in the
  list. p.19 documents setup interruption/resume as "reopen with identical
  parameters, then JVSkip to the saved file"; the existing -402 self-repair
  already reopens with the identical stored fromtime, so the bounded form
  composes with it. p.20's option table lists MING/COMM under options 3/4
  only, while the local `JVOPEN_VALID_COMBINATIONS` also allows them under
  option 1 — observed deviation, deliberately not touched this iteration.

### Red-first evidence (all runs on base production code)

Environment note: system Python is 3.10 (`StrEnum` import fails), so every
run used `uv run --extra dev --extra postgres pytest ... --no-cov` inside
this worktree, serially. `.venv/`, `.pytest-tmp/` are gitignored artifacts.

1. Round 1 (three extended test files, first bounded-form expectations):
   `uv run --extra dev --extra postgres pytest
   tests/test_jvlink_transport_contract.py tests/test_batch_processor.py
   tests/test_historical_cache_write_through.py --no-cov -q`
   → **20 failed, 79 passed**. Representative exact failures:
   - `AssertionError: expected call not found.` with
     `Expected: jv_open('RACE', '20250820000000-20260819235959', 4)` vs
     `Actual: jv_open('RACE', '20250820000000', 4)` (same for option 3) —
     base sends only the start timestamp;
   - `TypeError: BatchProcessor._should_split_setup_range() takes 3
     positional arguments but 4 were given` — no dataspec dimension in the
     split decision;
   - option-4 long-range partition/durability and per-chunk cache-routing
     tests failed (single unbounded open instead of chunks);
   - all invalid/inverted-date cases failed (`DID NOT RAISE`), i.e. bad
     dates reached JVOpen/schema on base.
   The two long-range batch tests were then re-scoped to the actually
   failed production range 20240820..20260819 (the first draft used a
   364-day range below the 370-day split threshold) and re-proven red on
   stashed base: `Failed: DID NOT RAISE SchemaMigrationError` and a
   full-window single call `('RACE', '20240820', '20260819', 4)` where the
   first bounded chunk `('RACE', '20240820', '20241231', 4)` was expected.
2. Independent primary-agent verification on base production (transport
   contract additions, pre-correction expectations): **8 failed, 2
   passed** — bounded RACE expected but actual jv_open used start-only, and
   invalid dates reached JV-Link; the two greens were the paired DIFN
   start-only and option-1 cases.
3. Post-correction expectations (see next section) re-proven on stashed
   base with the same command restricted to the three transport tests:
   **10 failed, 1 passed** (only `RACE option=1 → 20250820000000` green).
   The captured base log also shows the inverted-range case reaching the
   provider call path as `fromtime=20260819000000`.

### Correction adopted before green: inclusive-from encoding

The official eligibility rule is strictly greater than the start point and
up to and including the end point. Therefore `"{from_date}000000"` silently
drops a provider file stamped exactly at `from_date 00:00:00`, and adjacent
year chunks (previous ends Dec31 23:59:59 inclusive, next starts Jan1
00:00:00 exclusive) would drop a boundary-midnight file from both windows.
For a five-year rebuild this is a completeness defect, not an acceptable
residual, and it must not be deferred to option=1 differentials. Fix: for
setup options 3/4 the requested inclusive `from_date` is encoded as the
exclusive start point one second earlier (normally previous day 23:59:59):

- RACE setup 20250820..20260819 sends
  `20250819235959-20260819235959`;
- DIFN setup (end-forbidden) sends start-only `20250819235959`;
- option 1/2 keep the legacy `{from_date}000000` unchanged this iteration.

Adjacent date chunks are then exact by construction: each next chunk's
exclusive start point equals the previous chunk's inclusive bounded end
(`…-20241231235959` then `20241231235959-…`), pinned by
`test_adjacent_setup_chunk_opens_tile_exactly_at_the_boundary_second`.

### Implementation summary (uncommitted)

- `src/jvlink/constants.py`: `JVOPEN_END_TIME_FORBIDDEN_SPECS` transcribed
  verbatim from p.18 (all seven IDs; DIFF/HOSE additionally remain blocked
  by the retired-spec gate) and `jvopen_supports_end_timestamp()` (True iff
  every four-character component is outside the list; malformed input is
  False and is rejected earlier by `validate_jvopen_combination`).
- `src/fetcher/historical.py`: `validate_date_range()` (8-digit, real
  calendar date, from <= to) called in `fetch()` and `fetch_with_cache()`
  before any JV-Link, cache, or schema side effect (also closes a silent
  empty-success path for inverted ranges in `has_nl_range`);
  `_jvopen_fromtime()` implements the setup forms above; docstrings and
  stream logs updated to the actual contract.
- `src/importer/batch.py`: `validate_date_range` before `create_all_tables`;
  `_should_split_setup_range(data_spec, from_date, to_date, option)` now
  splits >370-day ranges for options 3 and 4 but only for end-capable
  specs (end-forbidden specs never split — splitting them would repeat the
  open tail per chunk, the O(n^2) behaviour; they stay a single open);
  `_process_split_setup_range` gained an option-4 branch in which each
  chunk's inner `process_date_range` owns its transaction boundaries
  (per-`SETUP_COMMIT_INTERVAL` commits when `auto_commit`, no outer
  transaction, committed earlier chunks survive a later chunk's failure;
  with `auto_commit=False` the caller stays the only commit boundary).
  Option 3 keeps the existing single transaction across chunks unchanged.
  `SINGLE_OPEN_SETUP_OPTION` renamed to `SPLIT_SETUP_OPTION` (internal).
- `src/cli/main.py` + `src/jvlink/wrapper.py`: `--from`/`--to` help,
  fetch guardrail notes (now option- and spec-dependent via
  `_print_fetch_guardrail_notes(jv_option, data_spec)`), and the `jv_open`
  fromtime docstring now state the real transport contract, including the
  exclusive-start encoding and the end-forbidden list.
- Tests: `tests/test_jvlink_transport_contract.py` (fromtime form table
  RACE-3/4 bounded + DIFN start-only + option-1 unchanged; adjacent-chunk
  boundary identity; invalid dates before any jvlink call),
  `tests/test_batch_processor.py` (split-decision table over
  spec x option; option-4 bounded partition + committed-chunk durability
  on the real failed scope 20240820..20260819; per-chunk cache routing —
  the resume mechanism; invalid dates before schema/transaction/fetch),
  `tests/test_historical_cache_write_through.py` (failed stream restores
  cache appends and never marks complete — STOP-condition pin),
  `tests/test_cli.py` (new help claims). Existing option-4
  commit-interval tests were re-dated 19860101→20220101 to stay on the
  single-open path their intent pins; all option-3 split-transaction tests
  are untouched and still pass.

### Verification (after implementation)

- Focused: `uv run --extra dev --extra postgres pytest
  tests/test_jvlink_transport_contract.py tests/test_batch_processor.py
  tests/test_historical_cache_write_through.py
  tests/test_historical_cache_failures.py tests/test_jvd_self_repair.py
  tests/test_date_filtering.py tests/test_jvlink_constants.py
  tests/test_cli.py tests/test_public_setup_contract.py --no-cov -q`
  → **188 passed, 8 subtests passed**.
- Second ring: `tests/test_quickstart_cli.py tests/test_updater.py
  tests/test_daily_update.py tests/test_cache_manager.py
  tests/test_importer.py tests/test_retired_data_specs.py
  tests/test_jvlink_wrapper.py` → **309 passed, 22 skipped** (Windows-only
  skips).
- `git diff --check` → clean.

### Primary-agent independent audit

- Draft PR #238 was created against `master` while the remote head still
  contained only the initial worklog commit `d7a1523`; no implementation was
  represented as complete before the red/green gate.
- The primary agent independently stashed only the five production changes,
  leaving the new tests on the base code, and ran the transport regression.
  Result: **8 failed, 2 passed**. The exact bounded failure was
  `Expected: jv_open('RACE', '20250820000000-20260819235959', 4)` versus
  `Actual: jv_open('RACE', '20250820000000', 4)`; malformed, missing and
  inverted dates reached the JV-Link path instead of raising. The production
  stash was then restored without conflict.
- Review against the pinned PDF found that the initial test expectation still
  excluded a provider file stamped at the requested date's midnight. The same
  Fable session was resumed and changed setup start encoding to the previous
  second, added the exact adjacent-boundary equality test, and removed the
  proposed midnight-gap residual. This is why the final RACE expectation is
  `20250819235959-20260819235959`, not the first red draft above.
- The primary agent corrected one CLI-help ambiguity: options 1/2 retain their
  exclusive cursor contract and must not be described as having an inclusive
  start date. The full seven-ID official end-forbidden list is now shown in
  the public help/docstring. Cache rollback now asserts the exact
  `FetcherError` type, and the transport table includes a mixed `RACEDIFN`
  dataspec so one forbidden component keeps the whole open start-only.
- A cache-bypass negative was added to the existing transport contract:
  inverted dates raise before `has_nl_range`, cache reads, JVInit or JVOpen.
- Independent focused rerun after those adjustments:
  `.venv/bin/python -m pytest tests/test_jvlink_transport_contract.py
  tests/test_batch_processor.py tests/test_historical_cache_write_through.py
  tests/test_historical_cache_failures.py tests/test_jvd_self_repair.py
  tests/test_date_filtering.py tests/test_jvlink_constants.py tests/test_cli.py
  tests/test_public_setup_contract.py --no-cov -q`
  → **190 passed, 8 subtests passed**.
- Independent second ring remained **309 passed, 22 skipped**. Workflow fatal
  lint (`flake8 ... --isolated --select=E9,F63,F7,F82`) returned **0**;
  `compileall` and `git diff --check` passed. Repository-wide Ruff/Black were
  not treated as gates because the current baseline has unrelated advisory
  style debt and the actual workflow runs fatal Flake8 only.

### Remaining risks and explicitly blocked items

- Live-provider behaviour of the bounded setup fromtime is UNVERIFIED here
  (live operations are a STOP condition). The first supervised run must
  watch for -112/-113 (fromtime rejections) and confirm the provider
  honours the end point for the setup-data portion; p.20 attaches the end
  clause wording to the current-month normal-data part of the option-3/4
  sentence, so the effective server-side bound for archived setup files is
  an empirical question this iteration cannot answer.
- Resume contract, stated honestly: with the cache enabled, a completed
  chunk marks its exact window complete, so re-running the identical
  command re-derives the identical partition and replays completed chunks
  from local cache without provider calls; the first incomplete chunk
  refetches bounded. Without the cache, a retry re-downloads each bounded
  chunk and re-imports idempotently (upsert) — durable, not download-free.
  A chunk whose stream contained a buffer without a supported event date
  never marks complete and is refetched on retry. A durable chunk ledger
  independent of the NL cache (true download-free resume without cache)
  remains out of scope and is NOT claimed.
- option 1/2 keep `{from_date}000000`: an option-1 backfill still excludes
  a file stamped exactly at from_date midnight (pre-existing contract;
  cursor-based syncs pass `lastfiletimestamp` and are unaffected).
  Deferred explicitly, not silently.
- Registry deviation observed, untouched: local option-1 list allows
  MING/COMM although p.20 lists them only under options 3/4.

### Next safe action

Primary agent: review this uncommitted diff (10 files), then commit/push and
update draft PR #238 for this branch per the iteration protocol. Only after review,
merge, a new `2.0.0.dev*` wheel, and runtime pinning may a supervised
bounded RACE option-4 setup for 20240820..20260819 be attempted, watching
for -112/-113 and the JVOpen response budget.
