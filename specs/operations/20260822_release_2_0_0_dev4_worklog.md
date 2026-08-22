# jrvltsql 2.0.0.dev4 release worklog — 2026-08-22

## Start state and objective

- Objective: publish the merged H1 provider-cancellation repair as the next
  immutable development-test prerelease required by the registered development
  collector and five-year recovery.  Stop at a `2.0.0.dev` prerelease; do not
  declare or publish production `2.0.0`.
- Minimum scope: version parity, release-facing changelog/notes, lock update,
  exact-SHA tests, fresh wheel/sdist gates, PR review/merge, annotated tag and
  GitHub prerelease with exact artifact digests.  Live JV-Link calls, runtime
  pinning, KIR pinning, database/cache mutation and the provider retry belong
  to dependent iterations after this release is published.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260822_jrvltsql_release_dev4`.
- Branch: `release/2.0.0.dev4-20260822`.
- Base/start HEAD: `bda6d4facddba52480d5e75558845c7e846fd154`, exact
  fetched `origin/master`, the squash merge of audit PR #241.
- Functional release delta: H1 PR #240, squash merge
  `1ee2ccb3ee5c104a15177f57281004395e669bb7`.  It accepts only the exact
  eleven-space provider vote in a combination-bearing H1 `DataKubun=9`
  physical record, normalizes it to parser `Hyo=""` and SQL `NULL`, and keeps
  statuses 2/4/5 plus non-space whitespace fail closed.
- H6 audit PR #241 made no production/test change.  It retained the current
  strict H6 contract because official space semantics were not accompanied by
  an available combination-bearing status-9 provider instance.
- Previous prerelease: tag/release `v2.0.0.dev3` at
  `d4830042d326b89f26a761e580e5621452e4b86b`; published wheel SHA-256
  `2e1f0f09844e838acf8b50282bac3f1e6ff64d465ed484d7f8e052ab90e120b2`
  and sdist SHA-256
  `8e68800875ab4792a8b93e129458310650396973b0cf31387c68d2859c501a5d`.
- Dependent runtime merge: `miyamamoto/jrvltsql-wine-runtime` PR #30,
  `4851ef922bd927b541f8d74d88122181a6b1dcb5`.  Dependent KIR operational
  evidence remains draft PR #167 and must not retry the provider from this
  unreleased branch.
- Implementation is by the primary Codex agent.  No Claude session is used:
  this iteration changes release metadata and documentation only, and does not
  implement a new gate, concurrency boundary or cross-repository behavior.

## Planned release contract

1. Bump `pyproject.toml`, `src.__version__`, `uv.lock` and exact current-version
   tests from `2.0.0.dev3` to `2.0.0.dev4`.
2. Add a named dev4 changelog/release-note section that describes the bounded
   H1 status-9 provider shape, parser/database representations and retained H6
   fail-closed boundary without changing the unreleased production warning.
3. Prove version parity and PEP 440 prerelease behavior, then run the repository
   test gate, Python 3.12 workflow-equivalent suite, fatal lint, lock check,
   and fresh git-archive wheel/sdist content plus isolated install/init/schema
   smoke.
4. Push one release candidate and use one GitHub-native review.  Aggregate any
   concrete findings once; merge only with exact-head checks successful,
   unresolved threads zero and tracked/ignored worktree clean.
5. Rebuild artifacts from the squash merge SHA, verify content and installed
   version, create annotated `v2.0.0.dev4`, publish a GitHub prerelease, and
   compare GitHub asset digests with the local immutable artifacts.

## STOP conditions

- Stop on any version mismatch, stale dev3 current-release statement, lock
  drift, failed test/content/install smoke, unresolved finding, non-clean
  worktree, or tag/release name collision.
- Do not reuse candidate artifacts after squash merge.  Publication artifacts
  must be rebuilt from the exact merge/tag target.
- Do not call JV-Link, mutate the development runtime/database/cache, update a
  runtime or KIR pin, or claim five-year recovery in this release-code
  iteration.
- Do not publish final `2.0.0`.  This is only the development prerelease the
  user asked to reach before the eventual Devin handoff.

Next safe action: commit and push this start record, open a Draft PR, then make
the single grouped version/release-note change and run the focused release
surface before freezing the candidate.

## Release candidate implementation

- The start record was committed/pushed as
  `1699b7f334c8f84af7d96005c2b4af5cecebc85a`; Draft PR #242 is the
  authoritative review surface.
- Version parity changed from `2.0.0.dev3` to `2.0.0.dev4` in
  `pyproject.toml`, `src/__init__.py`, the editable project entry in `uv.lock`,
  and the two current-version updater assertions.  `uv lock` used CPython
  3.12.11 and reported only
  `Updated jltsql v2.0.0.dev3 -> v2.0.0.dev4`.
- CHANGELOG and release notes now name dev4 and describe only the merged H1
  provider-cancellation contract plus the evidence-based decision not to widen
  H6.  The unreleased production `2.0.0` warning remains unchanged.
- No checker or validator is introduced by this metadata-only iteration, so no
  new red-first test is required.  Existing version parity and PEP 440 tests
  are updated rather than duplicated.
- Pre-commit Python 3.12.11 evidence:
  - updater/public-version/distribution/installer focused selection:
    **95 passed**;
  - source and installed editable metadata both report exactly
    `2.0.0.dev4`;
  - `uv lock --check`: pass;
  - `scripts/validate_test_gate.py`: `TEST GATE PASS`;
  - `git diff --check`: pass.
- The focused run created only ignored virtualenv/pytest/coverage artifacts in
  the dedicated worktree.  They remain local during the validation phase and
  must be removed before the final clean-worktree gate.

Next safe action: commit/push the grouped release metadata, freeze its full
SHA, run the Python 3.12 full/workflow/release-artifact gates, then add only the
resulting evidence to this worklog before the one native review.

## Exact release-candidate validation

- Release candidate commit:
  `67b8ee306ff0df58d794f355f4b9ba1b6b8857a5`, pushed to Draft PR #242.
- Exact candidate Python 3.12.11 workflow-equivalent suite:
  **4713 passed, 503 skipped, 14 deselected, 22 subtests passed** in
  140.16 seconds.
- Existing gates on the same candidate:
  - updater/public-version/distribution/installer focused selection:
    **95 passed**;
  - `uv lock --check`: pass;
  - `scripts/validate_test_gate.py`: `TEST GATE PASS`;
  - workflow fatal flake8 selection over `src tests scripts tools`: **0**;
  - `python -m compileall -q src tests scripts tools`: pass;
  - `git diff --check`: pass.
- A fresh `git archive` of the exact candidate, not the editable worktree, was
  built with Python 3.12.  Distribution content validation and the isolated
  wheel `init`/config/version/SQLite schema smoke passed.  Wheel and sdist
  metadata both report exactly `jltsql 2.0.0.dev4`:
  - candidate wheel SHA-256
    `99cfeeaf5491920510f49c21530e3d366f463aaab508800cb1630c0455e859ff`;
  - candidate sdist SHA-256
    `9705e8336b904d511113ba9f73a87c357a96e084581bd5118d987cdd40c0cbc8`.
- These artifacts are candidate-gate evidence only.  They will be removed and
  must not be uploaded after squash merge; publication artifacts will be
  rebuilt from the exact merge SHA.

Next safe action: commit/push this evidence-only update, rerun the bounded
focused/lock/lint/git-archive gates on that final PR head, clean every ignored
artifact, make PR #242 Ready, and request one GitHub-native review.  Merge only
with exact-head CI success, concrete findings addressed, unresolved threads
zero and tracked/ignored worktree clean.

## Final-head gate and grouped review response

- Evidence-only commit `d7c61de353b50803aede3a59c5bc181a5073c911`
  changed only this tracked worklog relative to the production/package
  candidate.  Its exact-head bounded release surface passed: 95 focused tests,
  lock check, test gate, fatal flake8 selection (0), compileall, diff check,
  fresh git-archive wheel/sdist content gate and installed-wheel smoke.  The
  disposable artifacts were removed and the tracked/ignored worktree was
  clean.
- GitHub Actions on that SHA passed test, lint and Windows batch syntax;
  performance remained the workflow's intentional skip.  Copilot recommended
  approval with no comments.
- The one requested Codex review found one concrete P2 documentation error:
  release notes said caller-created H1 status-9 `Hyo=""` was rejected, while
  `H1Parser.validate_current_fields()` intentionally accepts the existing
  expanded caller representation and native storage writes SQL `NULL`.
- CHANGELOG and release notes now distinguish physical provider provenance
  from expanded caller mappings.  This is a documentation-only correction;
  production behavior and tests are unchanged.  The response will be pushed
  once, the exact thread resolved with evidence, and no broad review rerun will
  be requested for this bounded wording fix.

Next safe action: run the version/document release selection and static gates,
commit/push the grouped review response, update the PR evidence to the new full
SHA, wait for exact-head CI, resolve the single review thread, confirm thread
count zero and clean worktree, then squash-merge.  Publication artifacts still
must be rebuilt from the resulting merge SHA.
