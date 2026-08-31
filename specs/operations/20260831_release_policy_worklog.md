# jrvltsql release policy worklog

## Scope and identity

- Started: 2026-08-31 (Asia/Tokyo)
- Objective: document and adopt separate normal-release and emergency-hotfix tracks so that merging a pull request never updates an operating installation by itself.
- Repository: `https://github.com/miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260831_jrvltsql_release_policy`
- Branch: `codex/release-policy-20260831`
- Base and initial HEAD: `4d3a89b382bb0a0b788d68093bc16f0f8dd950f5`
- Current public stable release: `v2.0.0`
- Production/release scope: JRA / `jrvltsql` only. No KPS, NAR, collector-runtime, database, or provider mutation is in scope.

## User decision and minimum scope

- The operating installation must not be updated every time a pull request is merged.
- Normal updates and emergency fixes must have separate admission and release paths.
- This iteration documents the policy first. Existing pull requests are triaged only after the policy PR is merged.
- The policy must distinguish merge, release publication, and operational adoption as separate actions.
- The policy must define hotfix eligibility narrowly enough that performance work, features, refactors, and observability changes cannot bypass the normal release train.

## Initial observed state

- `origin/master` and the clean dedicated worktree both started at exact SHA `4d3a89b382bb0a0b788d68093bc16f0f8dd950f5` (`jrvltsql 2.0.0 final`).
- The shared checkout `/home/keiba/jrvltsql` has unrelated pre-existing changes in `src/fetcher/realtime.py` and `tests/test_time_series.py`; this iteration does not modify that checkout.
- Six contributor pull requests are open against the same master base: #253 through #258.
- #253 has an actually executed failing test job and unresolved review threads. #256 and #257 also have unresolved data-preservation findings. None is authorized for merge or release by this documentation iteration.
- Existing public docs have no release-policy page, and `mkdocs.yml` has no release-policy navigation entry.

## Planned tracked changes

1. Add `docs/release_policy.md` as the public source of truth.
2. Link the policy from `docs/index.md` and the MkDocs navigation.
3. Keep current-PR-specific status out of the durable public policy; record it here and apply the policy after merge.
4. Validate the MkDocs build, links, diff, and repository cleanliness before opening a PR.

## Release-policy decisions

- `master` is the normal integration branch. A merge to `master` is not a release and must not deploy or update an operating installation.
- Production consumes immutable release evidence: a signed/annotated version tag where available, the full source SHA, artifact hashes, and pinned runtime/adoption metadata. It never follows `master`, a branch tag, or `latest`.
- Normal changes are batched into a release candidate and soak-tested before a scheduled release.
- An emergency hotfix starts from the exact currently adopted release tag, contains only the minimum repair, produces a patch release, and is forward-ported to `master` after validation.
- Data loss/corruption, collection outage, security exposure, or an operationally blocking correctness defect may qualify as an emergency. Features, performance changes, refactors, and observability changes do not.
- A hotfix candidate still requires a red-first regression, focused tests, risk-proportionate provider/database smoke, rollback notes, clean immutable SHA, and resolved reviews. Urgency does not waive evidence.

## STOP conditions

- Any proposed wording that makes merge imply release or release imply operational adoption.
- Any policy that permits a hotfix to include unrelated performance, feature, schema, or refactor work.
- Documentation commands, branch names, version examples, or links that cannot be reconciled with the repository.
- Dirty dedicated worktree, failed required validation, unresolved actionable review, or base/head ambiguity.
- Any request to tag, publish, deploy, mutate a collector/database, or merge an existing contributor PR before this policy iteration is complete.

## Activity log

### 2026-08-31 — iteration start

- Read the release-readiness skill and its release-gate reference.
- Inspected the shared checkout without changing it, fetched `origin/master`, pruned stale worktree metadata, and created the clean dedicated worktree above.
- Read the current MkDocs navigation, public docs index, GitHub workflows, and the final 2.0.0 release worklog.
- No GitHub write, tag, release, deployment, provider call, or database operation has been performed.
- Next safe action was to write the public policy and navigation changes, then run documentation-focused validation.

### 2026-08-31 — public policy and local validation

- Added `docs/release_policy.md` with separate merge, release, and operational-adoption states; normal and emergency tracks; branch/tag rules; hotfix admission; required gates; immutable artifact identity; and rollback requirements.
- Linked the page from `README.md`, `docs/index.md`, and the MkDocs navigation. No runtime, parser, importer, schema, workflow, or version file changed.
- `uvx --from mkdocs-material mkdocs build --strict --site-dir /tmp/jrvltsql_release_policy_site_20260831`: pass. MkDocs reported the pre-existing informational note that `record_contracts.md` is not in `nav`; there was no link or build failure.
- `git diff --check`: pass.
- Code tests were not expanded because this iteration changes documentation and navigation only. The GitHub workflow will still run the repository test/lint/distribution gates for the exact pushed SHA.
- Next safe action: inspect the complete diff, commit and push one documentation iteration, open a PR, request the repository's normal one-time review, and merge only after exact-head checks and unresolved threads are green.
