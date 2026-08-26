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

Use Python 3.12 with a current allowed Click release (8.5.0 in the reproduced
CI environment; the deprecation was introduced in 8.4) and run
`tests/test_cli.py tests/test_retired_data_specs.py` unchanged. Record the
warning-as-error failure count and exact warning. Do not suppress the warning
and do not pin Click below 8.4.

Captured red on unchanged production/tests at base
`def93638466722e30a12f318baf7da5ec0da9ec2` using Python 3.12.11 and Click
8.5.0:

```text
47 failed, 154 passed
DeprecationWarning: 'isolated_filesystem' is deprecated and will be removed
in Click 8.5. Use 'isolation' instead.
```

Command:

```bash
python -m pytest tests/test_cli.py tests/test_retired_data_specs.py -q --no-cov
```

## Implementation boundary

- Add a small test-only `CliRunner` compatibility subclass whose existing
  isolation method is implemented with `tempfile.TemporaryDirectory()` and a
  guaranteed CWD restore in `finally`.
- Import that runner in only the two affected modules, retaining every existing
  call site and assertion.
- Retain `CliRunner` itself and all existing assertions.
- Add no warning filters.

## Verification and merge gates

- Same Python 3.12 / Click 8.5.0 selection turns green.
- Existing test-gate validator, fatal flake8, compileall, and diff check pass.
- Exact candidate full SHA recorded on the PR; required `test` and `lint`
  checks execute successfully; unresolved review threads are zero; worktree is
  clean before merge.

## Uncommitted implementation verification

The minimal test-only compatibility runner was applied with no production
source, dependency, warning-policy, or assertion changes. Python 3.12.11 with
Click 8.5.0 now reports:

```text
193 passed, 10 subtests passed
```

The repository fail-closed test-gate validator and `compileall` also pass.
The next candidate commit must still pass fatal flake8, `uv lock --check`, the
non-slow full suite, and the required GitHub checks before merge.

## STOP conditions

- Any production source change.
- Any warning suppression or dependency downgrade.
- Any test assertion or CLI behavior change beyond filesystem isolation.
- Any worktree drift outside this dedicated worktree.

## Next safe action

Run the remaining local gates, commit the exact candidate, run the non-slow
full suite against that SHA, then push one PR and complete its required checks
and single native review before merging.
