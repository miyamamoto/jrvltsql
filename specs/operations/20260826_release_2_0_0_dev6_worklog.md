# jrvltsql 2.0.0.dev6 release worklog — 2026-08-26

## Start state and objective

- Objective: publish the already merged COM-buffer recovery and bounded
  `RACE` option-1 range-fetch repair as the next immutable development-test
  prerelease. Stop at `2.0.0.dev6`; do not declare or publish final
  production `2.0.0`.
- Minimum scope: version parity, release-facing changelog/notes, lock update,
  exact-SHA tests, fresh wheel/sdist gates, PR review/merge, annotated tag and
  GitHub prerelease with exact artifact digests. Live JV-Link calls, runtime
  pinning, database/cache mutation, feature generation and deployment are out
  of scope for this metadata-only release iteration.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260826_jrvltsql_dev6_release`.
- Branch: `release/2.0.0-dev6-20260826`.
- Base/start HEAD: `2179530bc90193f4ff1a8159483166d1e05fc194`, exact
  fetched `origin/master`, the squash merge of PR #246.
- Previous prerelease: tag/release `v2.0.0.dev5` at
  `34a3297a376b56646ff166f9d1de903d92b010c9`; published wheel SHA-256
  `6c56352d8a8a994e0dac4b38428634c47a1768b140db5e1e00aa43207ac8d0e6`
  and sdist SHA-256
  `3bfea96479c482d435c76d2c26c862ebb035a1f377528e58f85f36407f6e6b09`.
- Functional release delta:
  - PR #245, squash merge
    `2ed75a8e4873dbde786f3b0f773249ac639f2730`, preserves exact COM
    buffer bytes across supported pywin32 text projections, strips only the
    trailing COM NUL, requires exact-length candidate agreement and rejects
    ambiguous oversized prefixes.
  - PR #246, squash merge
    `2179530bc90193f4ff1a8159483166d1e05fc194`, partitions only the
    live-evidenced `RACE` option-1 bounded range into calendar-year opens,
    closes every chunk before continuing, preserves the primary error when
    close also fails, and replays only the active chunk's emitted prefix on
    provider `-402` recovery. Option 2 and setup options 3/4 remain
    start-only; non-allowlisted data specs remain start-only.
- Implementation is by the primary Codex agent. No Claude session is used:
  this iteration changes release metadata and documentation only and does not
  implement a new checker, concurrency boundary or cross-repository behavior.

## Planned release contract

1. Bump `pyproject.toml`, `src.__version__`, `uv.lock` and exact
   current-version tests from `2.0.0.dev5` to `2.0.0.dev6`.
2. Add named dev6 changelog/release-note sections describing only the two
   merged repairs above while retaining the unreleased production warning and
   the unverified 64-bit/migration/long-run boundaries.
3. Prove version parity and PEP 440 prerelease behavior, then run the
   repository test gate, Python 3.12 workflow-equivalent suite, fatal lint,
   lock check, and fresh git-archive wheel/sdist content plus isolated
   install/init/schema smoke.
4. Push one release candidate and use the repository's native review policy.
   Aggregate any concrete findings once; merge only with exact-head evidence,
   unresolved threads zero and tracked/ignored worktree clean.
5. Rebuild publication artifacts from the squash merge SHA, verify content
   and installed version, create annotated `v2.0.0.dev6`, publish a GitHub
   prerelease and compare GitHub asset digests with the local immutable
   artifacts.

## STOP conditions

- Stop on any version mismatch, stale dev5 current-release statement, lock
  drift, failed test/content/install smoke, unresolved finding, non-clean
  worktree, or tag/release name collision.
- Do not reuse candidate artifacts after squash merge. Publication artifacts
  must be rebuilt from the exact merge/tag target.
- Do not call JV-Link, mutate the development runtime/database/cache, update a
  runtime pin, or claim a completed long-run collection in this release-code
  iteration.
- Do not publish final `2.0.0`. This iteration ends at the development
  prerelease requested for handoff.

Next safe action: apply the grouped version/release-note change, update the
lock, run the focused release surface and freeze one release candidate.

## Release candidate implementation

- Version parity changed from `2.0.0.dev5` to `2.0.0.dev6` in
  `pyproject.toml`, `src/__init__.py`, the editable project entry in `uv.lock`
  and the two current-version updater assertions.
- CHANGELOG and release notes describe only merged PRs #245 and #246 and keep
  the unreleased-production warning. In particular, they do not generalize
  the measured `RACE` option-1 calendar-year behavior to option 2, setup
  options 3/4 or other data specs.
- No checker or validator is introduced by this metadata-only iteration, so
  no new red-first test is required. The merged repairs carry their own paired
  red/green evidence in
  `specs/operations/20260826_pr245_com_buffer_recovery_worklog.md` and
  `specs/operations/20260826_pr246_yearly_jvopen_repair_worklog.md`; this
  release updates existing version assertions instead of duplicating them.
- Pre-freeze Python 3.12.11 evidence:
  - source, installed editable metadata and updater current version all report
    exactly `2.0.0.dev6`; final `2.0.0` compares newer;
  - updater/public setup/distribution/CLI focused selection:
    **101 passed, 10 subtests passed**;
  - `scripts/validate_test_gate.py`, `uv lock --check` and
    `git diff --check`: pass.

Next safe action: commit and push one grouped release candidate, run the full
Python 3.12 workflow and fresh git-archive artifact gates on its exact SHA,
then obtain the repository-native review before merge.

## Exact release-candidate validation

- Release candidate commit:
  `e6b190d966345fc77ca382aa7d2defb455efa0e5`, pushed to PR #247.
- Exact-candidate Python 3.12.11 workflow-equivalent suite:
  **4,780 passed, 503 skipped, 14 deselected, 21 subtests passed** in
  123.73 seconds; no failures. PostgreSQL/live-provider tests retain their
  normal opt-in skip boundary.
- The same exact candidate passed:
  - updater/public setup/distribution/CLI focused selection:
    **101 passed, 10 subtests passed**;
  - `scripts/validate_test_gate.py`, `uv lock --check`, fatal-only Flake8 over
    `src tests scripts tools`, `python -m compileall -q`, strict MkDocs build
    and `git diff --check`;
  - source/editable metadata/updater parity at exact `2.0.0.dev6`, with final
    `2.0.0` comparing newer.
- A fresh `git archive` of exact candidate `e6b190d...`, not the editable
  worktree, built a wheel and sdist. Distribution content validation and the
  isolated wheel init/config/version/SQLite schema smoke passed; both artifact
  metadata records report `jltsql 2.0.0.dev6`:
  - candidate wheel SHA-256
    `1dd99dc4cc41be5a594233785f1f9cc5bcb1f6101c53db0935851dec96eab712`;
  - candidate sdist SHA-256
    `e678e935d57a39233a9d33e48c4e62425a0803a73856b94ae48eba3d0e66d86a`.
- Candidate artifacts and temporary documentation/build trees were removed.
  These hashes are validation evidence only and must not be uploaded after a
  squash merge; publication artifacts will be rebuilt from the exact merge
  and tag target.

Next safe action: commit/push this evidence-only worklog update, run the
bounded version/lock/content gates on the final PR head, request one native
review and merge only after exact-head checks and unresolved-thread count are
acceptable under repository policy.
