# jrvltsql 2.0.0.dev5 release worklog — 2026-08-22

## Start state and objective

- Objective: publish the merged H6 provider-cancellation repair as the next
  immutable development-test prerelease required before the registered
  five-year JRA `RACE` setup can be retried. Stop at a `2.0.0.dev`
  prerelease; do not declare or publish production `2.0.0`.
- Minimum scope: version parity, release-facing changelog/notes, lock update,
  exact-SHA tests, fresh wheel/sdist gates, PR review/merge, annotated tag and
  GitHub prerelease with exact artifact digests. Live JV-Link calls, runtime
  pinning, KIR pinning, database/cache mutation and provider retry belong to
  dependent iterations after this release is published.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260822_jrvltsql_dev5_release`.
- Branch: `release/2.0.0.dev5-20260822`.
- Base/start HEAD: `2b5fbcf29b860b4d1ca24d1710fd068834b92de4`, exact
  fetched `origin/master`, the squash merge of H6 repair PR #243.
- Functional release delta: PR #243, squash merge
  `2b5fbcf29b860b4d1ca24d1710fd068834b92de4`. It accepts only the exact
  eleven-space provider vote in a combination-bearing H6 `DataKubun=9`
  physical record, normalizes it to parser `SanrentanHyo=""` and SQL `NULL`,
  keeps statuses `2/4/5` and non-space raw whitespace fail closed, applies the
  same validator to realtime raw/parsed/batch routes, and preserves status-0
  key-only erase even when its non-key body is undecodable or malformed.
- Previous prerelease: tag/release `v2.0.0.dev4` at
  `18ddb16f664750e35b31527ae85ba09e540ca0a5`; published wheel SHA-256
  `2eb53ba8e054d6b453bb4e90e6144998a88bbc5a989b26586e604d491b46278b`
  and sdist SHA-256
  `9748697db59103260a760fe04e290bcf7dcd0bedc4199b49d6bd2304c2dba8d3`.
- Dependent operational evidence remains Draft KIR PR #167. KPS feature-type
  parity remains independent Draft PR #624. Neither may treat this unreleased
  branch as an installed/runtime version.
- Implementation is by the primary Codex agent. No Claude session is used:
  this iteration changes release metadata and documentation only, and does not
  implement a new gate, concurrency boundary or cross-repository behavior.

## Planned release contract

1. Bump `pyproject.toml`, `src.__version__`, `uv.lock` and exact
   current-version tests from `2.0.0.dev4` to `2.0.0.dev5`.
2. Add a named dev5 changelog/release-note section that describes the bounded
   H6 status-9 physical shape, SQL representation, realtime validation and
   status-0 opaque-body erase without changing the unreleased production
   warning.
3. Prove version parity and PEP 440 prerelease behavior, then run the
   repository test gate, Python 3.12 workflow-equivalent suite, fatal lint,
   lock check, and fresh git-archive wheel/sdist content plus isolated
   install/init/schema smoke.
4. Push one release candidate and use one GitHub-native review. Aggregate any
   concrete findings once; merge only with exact-head checks successful,
   unresolved threads zero and tracked/ignored worktree clean.
5. Rebuild artifacts from the squash merge SHA, verify content and installed
   version, create annotated `v2.0.0.dev5`, publish a GitHub prerelease, and
   compare GitHub asset digests with the local immutable artifacts.

## STOP conditions

- Stop on any version mismatch, stale dev4 current-release statement, lock
  drift, failed test/content/install smoke, unresolved finding, non-clean
  worktree, or tag/release name collision.
- Do not reuse candidate artifacts after squash merge. Publication artifacts
  must be rebuilt from the exact merge/tag target.
- Do not call JV-Link, mutate the development runtime/database/cache, update a
  runtime or KIR pin, or claim five-year recovery in this release-code
  iteration.
- Do not publish final `2.0.0`. This is only the development prerelease the
  user asked to reach before the eventual Devin handoff.

Next safe action: commit and push this start record, open one Draft PR, then
make the grouped version/release-note change and run the focused release
surface before freezing the candidate.
