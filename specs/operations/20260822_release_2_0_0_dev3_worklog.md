# jrvltsql 2.0.0.dev3 release worklog — 2026-08-22

## Start state and objective

- Objective: publish the merged official start-only JVOpen setup repair as the
  next development-test prerelease so the registered development collector can
  run the five-year recovery from an immutable released artifact.
- Minimum scope: version parity, release-facing changelog/notes, lock update,
  exact-SHA tests, fresh wheel/sdist gates, PR review/merge, signed evidence by
  artifact digest, tag and GitHub prerelease. No live provider call, runtime
  pin, database/cache mutation, Wine registration change, or production
  `2.0.0` claim belongs to this release-code iteration.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260822_jrvltsql_release_dev3`.
- Branch: `release/2.0.0.dev3-20260822`.
- Base/start HEAD: `9d5c6b1aa0b27769134161623e1dcdeada251884`,
  exact fetched `origin/master` and squash merge of PR #238.
- Previous prerelease: tag/release `v2.0.0.dev2` at
  `3c4650dfceb96df89808291ef29191de506ef85f`; published wheel digest
  `7c4e2cec80bddbe34f6fc75874c48480e38e33fdde7a3274903bfa0098282376`.
- Upstream repair evidence: PR #238 final head
  `e7df4dea795a0fc72ab8a14befe33e39850b80aa`, merged at the base SHA above;
  Python 3.12 full `4726 passed, 508 skipped, 22 subtests`, final review with
  no finding, all GitHub checks successful, unresolved threads zero.
- Operator/recovery evidence remains KIR draft PR #167. Its next live setup
  operation is prohibited until this release is merged, published and pinned.
- Implementation is by the primary Codex agent. No Claude session is used:
  this iteration changes release metadata/version parity only and does not
  implement a new gate, concurrency boundary, or multi-repository behavior.

## Planned release contract

1. Bump `pyproject.toml`, `src.__version__`, `uv.lock` and exact version tests
   from `2.0.0.dev2` to `2.0.0.dev3`.
2. Promote the already-merged “next development prerelease” setup/cache notes
   to a named dev3 section without weakening the unreleased `2.0.0` warning.
3. Prove version parity and the updater's PEP 440 prerelease behavior, then run
   lock/test gate, the Python 3.12 workflow-equivalent suite, fatal lint and
   clean git-archive wheel/sdist content plus isolated install/init/schema
   smoke.
4. Push one release candidate, use one GitHub-native review, aggregate any
   concrete findings once, and merge only with exact-head checks successful,
   unresolved threads zero and a clean tracked/ignored worktree.
5. Rebuild artifacts from the merge SHA, validate content and installed version,
   create annotated `v2.0.0.dev3`, publish a GitHub prerelease with both exact
   artifacts, and verify release asset digests against the local build.

## STOP conditions

- Any version mismatch, stale `dev2` current-release statement, lock drift,
  failed test/content/install smoke, unresolved finding, non-clean worktree,
  or tag/release name collision stops publication.
- Do not reuse candidate artifacts after the merge SHA changes; release
  artifacts must be rebuilt from the exact merged tag target.
- Do not call JV-Link, mutate the development runtime/database/cache, update a
  KIR pin, or claim five-year recovery from this metadata-only iteration.
- Do not publish final `2.0.0`; this is only the Devin-handoff development
  prerelease requested by the user.

Next safe action: commit/push this start record, open a Draft PR, then make the
single version/release-note change and write the minimal parity regression
before running the focused gate.
