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
