# 2026-09-05 race lifecycle overlay 2.1.2 forward-port worklog

## Scope and immutable inputs

- Purpose: forward-port only the released v2.1.2 prospective O1/O2 lifecycle
  overlay, fail-closed lifecycle/cancellation handling, machine-readable
  Window/Keys evidence, tests, release record, and release-branch CI trigger
  into current development `master`.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/worktrees/jrvltsql-forward-port-2.1.2-race-lifecycle-overlay-20260905`.
- Branch: `fix/forward-port-2.1.2-race-lifecycle-overlay`.
- Exact base: `origin/master`
  `2e58b17f6177eb0e0bc5bd097fa0b181ed2d7ba4`.
- Released source: immutable tag `v2.1.2` and merge SHA
  `bc7951f59f4e6cc1da30fa614014f1da0fa73757`.
- Release URL: https://github.com/miyamamoto/jrvltsql/releases/tag/v2.1.2.
- Release artifacts: wheel SHA-256
  `ef3e293507f8d9ec66617035d6b42bdc09fcd05c2bfb8dd005501279cb45e874`;
  sdist SHA-256
  `310c6c3a11fcf8c0c3f43260e12495227ae2530bdbf3d5832e91a4a3fc3cc3e2`.
- Production/release rollback remains immutable v2.1.1
  `0f3161d30de65f15795608e2a4bec9fc91e05349`. This forward-port does not
  deploy or alter `stable/2.1`.

## Integration constraints and starting evidence

- Started only after PR 267 merged, v2.1.2 was published, its public artifacts
  were re-downloaded and verified, and `release/2.1.2`, `stable/2.1`, and
  `v2.1.2` all resolved to the release merge SHA.
- A read-only three-way `git merge-tree` preview against the exact tag base
  found overlaps in `src/cli/main.py` and `src/fetcher/realtime.py`.
  Current master includes the newer one-dialog/multi-spec JVInit lifecycle
  from PR 266. The forward-port must preserve that initialization ordering
  while adding the released lifecycle overlay and counters; it must not
  restore the older per-fetcher initialization block.
- The released updater limitation remains binding and must stay documented:
  DataKubun=0 is physically removed, so an absent RT tombstone cannot be
  distinguished from no RT update and stale-NL fallback after erase remains
  unproven.
- No database, schema, migration, provider registration, or runtime deployment
  is in scope. No NAR P8 process or target DuckDB may be touched. All tests use
  `nice -n 15`.

## Safe sequence

1. Apply the released squash commit as a three-way forward-port, resolve only
   the current-master overlaps, and inspect every resulting path.
2. Prove released red/green lifecycle and CLI contracts still pass on master,
   then run scoped Black/Ruff/MyPy, fatal Flake8, full suite, and distribution
   smoke on one frozen candidate SHA.
3. Push with dry-run first, open a separate PR to exact current `master`,
   obtain authoritative CI/review, resolve all threads, and merge only while
   the PR head/base/status remain authoritative.

STOP on any loss of the master JVInit lifecycle, fail-open lifecycle state,
test or build failure, unexpected schema/storage change, unresolved review
finding, master drift that changes the integration decision, or any need to
touch the NAR P8 process or its database.

## Progress

- 2026-09-05 forward-port apply: after the tracked starting record was
  committed, applied released squash SHA
  `bc7951f59f4e6cc1da30fa614014f1da0fa73757` with `git cherry-pick`.
  Git's three-way apply merged every path except one localized conflict at the
  pre-loop statistics block in `src/fetcher/realtime.py`. The released side
  still carried its old explicit `self.jvlink.jv_init()`; current master had
  intentionally removed that block because `BaseFetcher.__init__` owns one
  JVInit for the multi-spec session. Resolved the conflict by retaining the
  master initialization lifecycle and adding only the released
  `nonempty_keys` statistics/comment. A post-resolution search found no
  conflict marker and no reintroduced `jv_init` in realtime/CLI; the owning
  call remains in `src/fetcher/base.py`.
- The apply also carries the released hotfix worklog as immutable historical
  evidence. This forward-port worklog records post-release integration facts
  so the historical file does not need a self-referential metadata-only commit.
- 2026-09-05 focused integration evidence (unfrozen forward-port tree, uv
  CPython 3.13.5, frozen dev+postgres dependencies, `nice -n 15`): all four
  released affected files passed, **122 passed and 22 subtests passed in
  2.85s**. The current-master lifecycle boundary also passed:
  `tests/test_jvinit_once_per_process.py` plus
  `tests/test_fetch_multiple_dataspecs.py` -> **27 passed in 0.91s**,
  including one JVInit for three fetches, no re-init after stream error, one
  shared session across specs, and fail-before-open on init error.
- 2026-09-05 scoped pre-freeze gates: the forward-ported CLI initially exposed
  two pre-existing current-master formatting regions under the locked Black;
  formatting the changed file produced only those mechanical line wraps.
  Black check over every changed Python file is now green. The fail-closed CI
  gate validator reports `TEST GATE PASS`, isolated fatal Flake8 reports 0,
  and diff check is green. Configured scoped Ruff improved from **58** on exact
  master base to **57** on the candidate; scoped MyPy is unchanged at **12**
  diagnostics on both. Exact baseline worktree:
  `/home/keiba/scratch/20260905_jrvltsql_forwardport_lint_baseline`,
  detached at `2e58b17f6177eb0e0bc5bd097fa0b181ed2d7ba4`.
- 2026-09-05 first frozen candidate and PR: commit
  `d460dbfef37c47b263e7ff3fef7b14447b80b49b` passed the combined focused set
  (**149 passed, 22 subtests passed in 3.38s**), workflow-equivalent full suite
  (**4962 passed, 516 skipped, 14 deselected, 33 subtests passed in 121.18s;
  81% coverage**), distribution build/content equality, and isolated wheel
  import. Verification-only artifact SHA-256 values were wheel
  `9d5e3a978b0ae8c0ea20f2b109dc9f398f7835671a7d6b2e7d6fe4189d432aec`
  and sdist
  `cc0f8efba9d16ce123656133726e8ea0803bb02a1d5a11f1bce6a8b8305e7d1d`.
  Pushed after a clean dry-run and opened PR 268:
  https://github.com/miyamamoto/jrvltsql/pull/268. Authoritative Tests run
  `33961457946` passed lint, Linux full test/distribution, and Windows launcher
  jobs on that exact SHA; performance was skipped by its declared PR condition.
- 2026-09-05 aggregated first-head review: CodeRabbit completed with no
  actionable comment (its docstring-coverage suggestion is non-blocking style
  debt, not a configured repository gate). The one-time Codex review raised one
  valid P1 at
  https://github.com/miyamamoto/jrvltsql/pull/268#discussion_r3940340565:
  source-selected rows were lifecycle-validated before the existing whole-date
  pruning, so a malformed legacy DataKubun in the generic/default 365-day SQL
  range could abort today's otherwise valid due race even though that row's
  HassoTime was deliberately never evaluated. Merge was held and both completed
  reviews were collected before one repair batch.
- Task 53 impact determination: its explicit same-day
  `--from-date D --to-date D` SQL predicates exclude all other dates before the
  lifecycle overlay, so the reported old-date defect cannot affect that exact
  production path. Rows on D remain candidates at the date phase and continue
  to fail closed on invalid lifecycle state, including same-day races outside
  the minute window; that is the established conservative card contract. The
  public v2.1.2 tag/assets/branches therefore stay immutable. This repair is an
  unreleased development-master follow-up, not a silent retag or a new Wine pin.
- 2026-09-05 RED for the review repair: without changing production source,
  strengthened the existing out-of-window regression so the 2026-09-02 row has
  both malformed HassoTime and invalid accumulated RA DataKubun `8`, while the
  due 2026-09-01 row remains valid. Command (uv CPython 3.13.5, frozen
  dev+postgres dependencies, `nice -n 15`):
  `pytest tests/test_time_series.py::test_race_window_skips_malformed_post_time_on_out_of_window_date -v --no-cov`
  -> **1 failed** with `FetcherError: Race lifecycle selection rejected
  202609020501: RA DataKubun is not valid for accumulated: '8'`; no JV key was
  opened. This demonstrates the exact fail-too-early path.
- 2026-09-05 GREEN implementation: extracted the existing race grouping and
  whole-date candidate calculation as one shared helper. The overlay still
  selects RT-over-NL ownership for every exact full key first, then validates
  lifecycle only for normalized keys whose dates can intersect this request.
  The post-time filter reuses the same reference instant/helper, retains all
  original considered/candidate/date-excluded counters, and alone validates
  candidate HassoTime. No fail-closed candidate, cancellation, source-conflict,
  schema/storage, no-window, or master one-JVInit contract was weakened. The
  exact red test is now **1 passed in 0.08s**.
- 2026-09-05 pre-freeze repair gates (same uv/frozen/nice environment): full
  `tests/test_time_series.py` plus the current-master JVInit and multi-spec
  boundary files -> **69 passed in 1.51s**. The changelog/release-contract file
  -> **10 passed in 0.13s**, and the exact regression remained green after the
  final type-annotation cleanup -> **1 passed in 0.09s**. Black over all seven
  changed Python files, `git diff --check`, `scripts/validate_test_gate.py`, and
  isolated fatal Flake8 are green. Configured scoped Ruff has no new debt and
  remains better than exact master (**57 candidate versus 58 baseline**);
  direct-module scoped MyPy also has no new debt (**11 candidate versus 12
  baseline**). The exact baseline checkout remains the detached worktree named
  above. These are pre-commit repair results; authoritative post-push CI must
  rerun on the new full SHA before merge.
