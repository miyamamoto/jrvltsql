# Click 8.5 CLI test isolation compatibility — 2026-08-27

## Purpose and minimal scope

The required GitHub Actions `test` job on PostgreSQL statistics PR `#251`
executed after an Actions outage and failed 47 tests/subtests. Every failure is
the same `DeprecationWarning`: Click 8.5 deprecates
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
CI environment; the deprecation was introduced in 8.5) and run
`tests/test_cli.py tests/test_retired_data_specs.py` unchanged. Record the
warning-as-error failure count and exact warning. Do not suppress the warning
and do not pin Click below 8.5.

Captured red on unchanged production/tests at base
`def93638466722e30a12f318baf7da5ec0da9ec2` using Python 3.12.11 and Click
8.5.0:

```text
47 failed, 154 passed
DeprecationWarning: 'isolated_filesystem' is deprecated and will be removed
in Click 9.0. Use 'tempfile.TemporaryDirectory' or pytest's 'tmp_path' fixture
with absolute paths instead.
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
- Retain `CliRunner` itself and all existing assertions; add one focused
  regression only if review exposes an untested compatibility contract.
- Add no warning filters.

## Verification and merge gates

- Same Python 3.12 / Click 8.5.0 selection turns green.
- Existing test-gate validator, fatal flake8, compileall, and diff check pass.
- Exact candidate full SHA recorded on the PR; required `test` and `lint`
  checks execute successfully; unresolved review threads are zero; worktree is
  clean before merge.

## Implementation verification

The minimal test-only compatibility runner was applied with no production
source, dependency, warning-policy, or assertion changes. Python 3.12.11 with
Click 8.5.0 at implementation commit
`e419fb2e342643df18c7f5c0bfed68bfed95908d` reports:

```text
193 passed, 10 subtests passed
4794 passed, 505 skipped, 14 deselected, 21 subtests passed
```

The second line is the complete non-slow local workflow selection. The
repository fail-closed test-gate validator, fatal flake8, `compileall`,
`uv lock --check`, and `git diff --check` also pass. The tree contained only
the intended test helper, two test-module import changes, and this tracked
worklog.

The final worklog commit itself cannot record its own full SHA. Record that
candidate SHA and its required GitHub-check results on the PR before merge, as
required by the repository handoff policy.

## Initial native review and repair

PR `#252` received one native Copilot review at candidate
`852e85d9f50587ae2b7a05c798809175a7bc41ee`. It correctly found that the
compatibility override dropped Click's optional `temp_dir` parameter and that
the docstring described the deprecation too loosely. The worklog also called
this a Click 8.4 deprecation; direct Click 8.5.0 source and a fresh base-archive
red reproduction established that 8.5.0 introduced it and its warning names
Click 9.0 removal.

A minimal regression was added before the repair. It failed on the reviewed
candidate with:

```text
TypeError: CliRunner.isolated_filesystem() takes 1 positional argument but 2
were given
```

The repair preserves the upstream signature, creates the isolated directory
under the optional parent, retains it on context exit when a parent is
provided, restores CWD in all cases, and still cleans default temporary
directories. The new regression then passed, and the complete focused
selection reported `194 passed, 10 subtests passed`. No second external review
is requested solely for these two already-bounded comments; required CI and
unresolved-thread gates still apply to the final candidate.

## STOP conditions

- Any production source change.
- Any warning suppression or dependency downgrade.
- Any test assertion or CLI behavior change beyond filesystem isolation.
- Any worktree drift outside this dedicated worktree.

## Next safe action

Commit this verification evidence, rerun the focused selection on the resulting
candidate, then push one PR and complete its required checks, single native
review, unresolved-thread check, and clean-tree gate before merging.
