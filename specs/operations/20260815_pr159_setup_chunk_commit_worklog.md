# PR #159 setup chunk commit worklog

## Scope and provenance

- Objective: make option 4 chunk commits fail closed when fetch/parse rejects a record, while preserving already completed chunks.
- Minimal scope: `src/importer/batch.py`, the existing focused batch-processor tests, and this worklog.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_pr159_fix`
- Branch: `upstream-pr-setup-commit-interval` (cross-repository PR branch in `hayato1980/jrvltsql`)
- PR: https://github.com/miyamamoto/jrvltsql/pull/159
- Base branch: `master`
- Base full SHA: `b6429421728b7020489962cfbf59bbc54c1bd3c0`
- Starting head full SHA: `4f4eda761d5361ef08d66b6d0fddd2d0cd11744e`
- Related release: `v1.6.10`
- Dependency order: complete and merge #159 before starting #160, then update #161 after #160.

## Claude Code implementation session

- Session ID: `88faab0e-2905-4b09-927e-5139ccbb1867`
- Model: `--model fable`
- Selection reason: transaction boundaries and ordering determine whether a failed chunk is durably committed, so the change has high rollback cost and fail-open risk.

## Planned independent Claude Code review

- Session ID: `af158531-5546-4010-bd10-fee69ec1c3b6`
- Model: `--model fable`
- Selection reason: the frozen candidate must be challenged independently for transaction-ordering, cumulative-counter, and fail-open edge cases.
- This session is read-only and separate from the implementation session. Its verdict and the reviewed candidate full SHA will be recorded on the PR because a commit cannot contain its own SHA.

## Status at start

- Observed: the PR head is mergeable and its GitHub Actions test/lint jobs passed, but one unresolved CodeRabbit thread reports that fetcher failures are checked only after the chunk commit.
- Independently reproduced before this iteration: a fetcher failure arising while a two-record chunk is consumed raises `ImporterError` only after one commit (`commit_calls=1`).
- Local worktree: clean at the starting head.
- Changes made in this iteration: this worklog only.
- Validation run in this iteration: none yet.

## Iteration: fail-closed per-chunk fetch-failure check (2026-08-15)

### Finding verification (observed, not inferred from the review comment)

- Observed: `HistoricalFetcher.fetch` and `fetch_with_cache` are generator
  functions (verified via `ast` walk), so `_records_failed` increments lazily
  while a chunk is materialized by `_chunks`.
- Observed: the pre-commit check in the option=4 loop was
  `self._raise_if_rejected(import_stats)` — importer statistics only. Fetch
  failures were checked only in `combined_stats` after every chunk commit.
- Conclusion: the CodeRabbit finding is valid; a chunk consumed alongside a
  fetch/parse failure was committed (fail-open) before the post-hoc raise.

### Red test before production change

- Added `test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk`
  with a stateful fake fetcher (`_ParseSkippingFetcher`) whose
  `records_failed` grows while the stream is consumed
  (interval=1, stream: good, PARSE_FAILURE, good).
- Command: `python3 -m pytest tests/test_batch_processor.py::test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk -q --no-cov`
- Observed failure on unchanged production code:
  `AssertionError: assert 2 == 1` on
  `_transaction_calls(processor.database).count("commit") == 1`, with
  recorded calls `['begin_transaction', 'commit', 'begin_transaction',
  'commit', 'rollback']` — the rejected chunk committed. pytest exit status: 1.

### Production change

- `src/importer/batch.py` (option=4 loop only): track cumulative fetcher
  `records_failed` in `fetch_failures_seen`; after each chunk's
  `import_records`, compute the per-chunk delta and raise `ImporterError`
  before `commit` when importer failures + fetch-failure delta > 0. Prior
  committed chunks are preserved; the offending chunk rolls back via the
  existing except handler.
- No double-counting: the per-chunk check only raises; `import_totals` still
  accumulates importer stats alone, and the final `combined_stats` check
  (fetch total + import totals) is unchanged.
- Baseline safety: the first cumulative read happens after the generator has
  started (fetch resets its statistics at first `next()`), and
  `fetch_failures_seen` starts at 0, so stale statistics from a previous data
  spec cannot skew the first chunk's delta.
- Non-option-4 and `auto_commit=False` paths: untouched (`commit_per_chunk`
  guards the whole block).
- Tail edge (observed behavior, by construction): a fetch failure counted
  while materializing a chunk that turns out empty (stream tail) is caught by
  the unchanged `combined_stats` check; only clean chunks were committed.

### Test strengthening

- `test_option_4_rejection_rolls_back_only_its_own_chunk`: now interval=2
  with stream RA01, RA02 | RA03, UNKNOWN — the rejected chunk mixes an
  importable record with the rejected one. Asserts `row_count == 2` (chunk 1
  committed; RA03 rolled back with its chunk).
- A duplicate equivalent fetch-failure test was introduced by an inadvertent
  concurrent resume of the same Claude session. The duplicate process was
  terminated and the redundant test removed before candidate validation; the
  single red-first regression above is the contract test.

### Validation commands and results

- Claude implementation validation before duplicate removal:
  `python3 -m pytest tests/test_batch_processor.py -q --no-cov` → 24 passed,
  exit 0; combined related run → 57 passed, 2 skipped, exit 0.
- `python3 -m ruff check src/importer/batch.py tests/test_batch_processor.py`
  → 8 findings (UP035/UP006/UP038/F401/I001), byte-identical to the findings
  at the unmodified HEAD (verified via `git stash` run). All pre-existing;
  none introduced. CI's lint gate is flake8 `--select=E9,F63,F7,F82`
  (`.github/workflows/test.yml`), which passes on the changed files (exit 0).
- Flake: one earlier combined run of `tests/test_cli.py` +
  `tests/test_comprehensive_integration.py` failed
  `test_status_command`/`test_version_command`; not reproducible in three
  subsequent runs (with and without the change) and both tests pass in
  isolation and per-file. Most likely cause: concurrent external edits to the
  worktree during that run. Inference, not observed root cause.
- Codex candidate validation after duplicate removal, Python 3.12.11:
  - `pytest tests/test_batch_processor.py -q --no-cov` → 23 passed, exit 0.
  - Workflow-equivalent related suite from `.github/workflows/test.yml`
    (`tests/test_parsers.py` through `tests/unit/test_jvlink_bridge.py`, with
    coverage) → 656 passed, 2 skipped, 3 subtests passed, exit 0.
  - Blocking flake8 gate
    `flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics`
    → 0 findings, exit 0.
  - Informational flake8 pass (`--exit-zero`) → 302 pre-existing findings,
    exit 0. `mypy src --ignore-missing-imports --no-strict-optional` → 85
    pre-existing errors, exit 1; the workflow marks mypy `continue-on-error`.
  - `git diff --check` → exit 0.

### Changed files

- `src/importer/batch.py` — per-chunk fail-closed fetch-failure check.
- `tests/test_batch_processor.py` — one new regression test + fake fetcher;
  strengthened multi-record rejected-chunk test.
- `specs/operations/20260815_pr159_setup_chunk_commit_worklog.md` — this update.

### Remaining issues

- Pre-existing ruff findings (typing-modernization, import sorting) left
  untouched: out of the minimal scope and not enforced by CI.
- Source branch drift check: contributor remote and local starting HEAD are
  both `4f4eda761d5361ef08d66b6d0fddd2d0cd11744e`; `origin/master` remains
  `b6429421728b7020489962cfbf59bbc54c1bd3c0`.
- Candidate is ready to commit. Nothing pushed yet; independent Claude review,
  GitHub Actions, review-thread resolution, and final merge gate remain.

## Iteration: review follow-up on frozen candidate 85c4d3e (2026-08-15)

Two new CodeRabbit findings arrived on frozen candidate
`85c4d3edfebf99d6d8a3791d74a8361823ef76e0` after push. Both are addressed in
one minimal local batch (tests + this worklog); no production defect was
found, so `src/importer/batch.py` is untouched in this iteration. Nothing is
committed or pushed, and GitHub state is unchanged.

### Finding 1: exact transaction-order assertion

- `test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk` now
  asserts the exact transaction order via `_transaction_calls`:
  `['begin_transaction', 'commit', 'begin_transaction', 'rollback']` — the
  clean first chunk provably commits and the rejected second chunk provably
  rolls back without a commit, replacing the weaker `commit count == 1` check.
- Green on the fixed code:
  `python3 -m pytest tests/test_batch_processor.py::test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk -q --no-cov`
  → 1 passed, exit 0.
- Red-first re-verified against the parent production code: with
  `git show 4f4eda7:src/importer/batch.py` swapped into the worktree, the same
  command fails with `At index 3 diff: 'commit' != 'rollback'` (the parent
  commits the rejected chunk), pytest exit status 1. `src/importer/batch.py`
  was then restored from HEAD (`git status` shows only the test file
  modified).

### Finding 2: 655 versus 656 workflow-equivalent totals reconciled

- The original PR/pre-fix workflow-equivalent suite at
  `4f4eda761d5361ef08d66b6d0fddd2d0cd11744e` recorded 655 passes (figure as
  recorded on the PR; not re-run in this iteration). The post-fix candidate
  suite at `85c4d3edfebf99d6d8a3791d74a8361823ef76e0` observed 656 passes
  (Codex candidate validation above).
- Causal difference: exactly one net new test — the red-first regression
  `test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk`. The
  other test change of that candidate strengthened
  `test_option_4_rejection_rolls_back_only_its_own_chunk` in place without
  changing the collected count, and the duplicate concurrent-session test was
  removed before the candidate was frozen. 655 + 1 = 656 is expected, not a
  discrepancy.

### Independent review status

- Independent Claude review session `af158531-5546-4010-bd10-fee69ec1c3b6`
  reviewed `85c4d3edfebf99d6d8a3791d74a8361823ef76e0` GREEN.
- That verdict is superseded by this review-follow-up candidate: the
  strengthened test changes the tree, so the next candidate SHA requires a
  fresh independent review before merge.
- Planned fresh review session: `9cce1b2d-9180-449e-8d34-9b733a2ecfa6`,
  model `--model fable`, read-only. Fable is retained because the review must
  independently validate a transaction-ordering and fail-open contract. The
  reviewed full SHA and verdict will be recorded on the PR.

### Validation commands and results

- `python3 -m pytest tests/test_batch_processor.py -q --no-cov` → 23 passed,
  exit 0.
- `git diff --check` → exit 0.

### Changed files

- `tests/test_batch_processor.py` — exact transaction-order assertion.
- `specs/operations/20260815_pr159_setup_chunk_commit_worklog.md` — this update.

## Next safe command

Commit this review-follow-up batch, rerun the focused/workflow-equivalent
checks on the resulting full SHA, push it to the PR source branch, and run a
fresh independent read-only Claude review of that SHA in session
`9cce1b2d-9180-449e-8d34-9b733a2ecfa6`.

## STOP conditions

- Stop before push if the PR head moves away from the recorded source SHA without reconciliation.
- Stop before merge if any focused/workflow-equivalent test fails, a concrete data-integrity finding remains, the final Claude Code review is not GREEN, any review thread remains unresolved, or the worktree is dirty.
- Do not treat the prior successful Actions run as evidence for a new candidate SHA.
