# Click 8.4 CLI test isolation compatibility — 2026-08-27

## Purpose and minimal scope

The required GitHub Actions `test` job on PostgreSQL statistics PR `#251`
executed after an Actions outage and failed 47 tests/subtests. Every failure is
the same `DeprecationWarning`: Click 8.4 deprecates
`CliRunner.isolated_filesystem()`, while this repository intentionally treats
all warnings as errors. This iteration replaces only that deprecated test
helper usage with an equivalent standard-library temporary working directory.
No CLI production behavior, dependency range, importer, database, collector,
or release metadata changes are in scope.

## Repository and immutable starting state

- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260827_jrvltsql_click84_ci`
- Branch: `fix/click84-test-isolation-20260827`
- Base and initial HEAD: `def93638466722e30a12f318baf7da5ec0da9ec2`
- Base source: freshly fetched `origin/master`
- Dependent repair PR after this iteration: `#251`
- Initial worktree state: clean

## Red-first evidence to capture

Use Python 3.12 with current allowed Click 8.4 and run
`tests/test_cli.py tests/test_retired_data_specs.py` unchanged. Record the
warning-as-error failure count and exact warning. Do not suppress the warning
and do not pin Click below 8.4.

## Implementation boundary

- Add a small test-only context manager based on
  `tempfile.TemporaryDirectory()` and a guaranteed CWD restore in `finally`.
- Replace only calls to Click's deprecated `isolated_filesystem()` in the two
  affected modules.
- Retain `CliRunner` itself and all existing assertions.
- Add no warning filters.

## Verification and merge gates

- Same Python 3.12 / Click 8.4 selection turns green.
- Existing test-gate validator, fatal flake8, compileall, and diff check pass.
- Exact candidate full SHA recorded on the PR; required `test` and `lint`
  checks execute successfully; unresolved review threads are zero; worktree is
  clean before merge.

## STOP conditions

- Any production source change.
- Any warning suppression or dependency downgrade.
- Any test assertion or CLI behavior change beyond filesystem isolation.
- Any worktree drift outside this dedicated worktree.

## Next safe action

Create a disposable Python 3.12 environment with current project dependencies,
run the two unchanged test modules to capture red, then implement the minimal
test-only helper replacement.
