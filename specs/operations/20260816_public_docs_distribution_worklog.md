# Public documentation and distribution hygiene worklog

## Iteration identity

- Objective: remove the four superseded crawler-audit pages requested by the
  maintainer, remove private implementation provenance from public-facing
  tracked content, and prove that tracked `specs/` evidence remains outside
  release distributions.
- Minimum scope: public/tracked documentation references, MkDocs navigation and
  links, packaging configuration, one fail-closed distribution-content check,
  and release-artifact inspection. No version bump, publication, or provider
  acquisition is included in this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_docs_distribution`
- Branch: `agent/docs-distribution-hygiene-20260816`
- Base/full SHA: `3fbd5272a3375e3422f47335bc4a98f98c9f6e2b`
- Dependency: PR #185 merged as the same base SHA.
- Production/release version at start: tag `v1.6.10`; project version `1.6.10`.
- Agent/model: Codex only. No Claude session is used.

## Plan and gates

- Inventory tracked public references without printing private provenance in
  review evidence. Remove the four explicitly superseded audit pages and repair
  any links or navigation that would break.
- Keep repository `specs/` tracked as the audit/worklog source of truth. Add a
  distribution-content gate that builds both wheel and sdist and fails when
  either contains `specs/` or superseded audit pages. Per the validator policy,
  demonstrate the negative case before accepting the gate.
- Run focused packaging tests, generated wheel/sdist inspection, strict MkDocs,
  full/workflow-equivalent tests only as required by the affected surface,
  fatal lint, and clean-tree checks on an exact candidate SHA.
- Open a separate PR, request one GitHub-native Copilot review, aggregate all
  actionable feedback, require unresolved threads zero, and merge only with
  green gates and a tree-equivalent squash merge.
- STOP on any remaining tracked public disclosure, broken documentation link,
  distribution leakage, base drift, or unresolved actionable review finding.

## Starting state

- `specs/` is intentionally tracked and must remain in the Git repository.
- The package finder is limited to `src`/`src.*`; an empirical build of the
  preceding TK candidate contained zero `specs/` or `docs/` entries in wheel
  and zero `specs/` or `docs/` entries in sdist. This is useful starting
  evidence but not a regression gate for the new exact SHA.
- Four superseded pages still exist under `docs/` and strict MkDocs reports
  them as files outside navigation. Their deletion is explicitly requested.

## Red-first distribution gate evidence

- Added `tests/test_distribution_contents.py` before the checker exists. The
  test pairs a wheel and sdist, requires both artifact kinds, and supplies
  explicit negative fixtures for tracked specifications and superseded audit
  pages in either archive format.
- The pre-implementation command
  `python3 -m pytest -q -o addopts='' --basetemp=/home/keiba/scratch/pytest_distribution_red tests/test_distribution_contents.py`
  failed during collection with
  `ModuleNotFoundError: No module named 'scripts.check_distribution_contents'`.
  This proves the new release gate is absent before implementation; the test
  must not be weakened when the checker is added.

## Implementation and pre-candidate validation

- Deleted the four maintainer-designated crawler-audit pages and removed all
  remaining tracked references to their paths outside the regression test.
- Replaced environment-specific deployment names, implementation provenance,
  machine connection details, and a credential-like example in tracked public
  documentation/worklogs with portable descriptions. A bounded case-insensitive
  scan of the changed Markdown and documentation paths found none of the private
  identifiers, endpoint patterns, usernames, or credential patterns. The scan
  prints only pass/fail status so no sensitive value enters the evidence log.
- Kept `specs/` tracked. Added `scripts/check_distribution_contents.py` and an
  explicit `.gitignore` exception so the checker itself cannot be omitted. It
  inspects, without extracting, both wheel and sdist members and fails on a
  missing artifact kind, unreadable/unsupported archive, unsafe member path,
  any `specs` path component, or any of the four superseded page basenames.
- Added `build>=1.2` to the development extra and synchronized `uv.lock`; CI now
  builds both artifacts after its focused suite and applies the same checker.
- The focused synthetic suite passed: `7 passed`. An empirical pre-candidate
  `uv build --wheel --sdist` produced both artifacts, and the checker reported
  `Distribution content check passed for 2 artifacts`. The sdist contains the
  intended test sources but neither artifact contains `specs/` or `docs/`.
- Strict MkDocs, compileall for changed Python paths, fatal flake8 checks for the
  checker/test, and `git diff --check` passed. These are pre-candidate results;
  exact-SHA workflow-equivalent/full validation remains required after commit.

## Candidate validation

- Candidate full SHA: `fb6c131e3defa6eb44a24282050a1a7c90b96cdd`.
  `git fetch origin master` confirmed `origin/master` and the merge base both
  remained `3fbd5272a3375e3422f47335bc4a98f98c9f6e2b`; there was no base drift.
- A first full-suite attempt was intentionally discarded after a concurrent
  source-tree build rewrote package metadata while CLI tests were running; it
  reported two CLI failures, and both passed immediately when reproduced after
  the build completed. A second attempt in a newly created environment stopped
  at collection because optional PostgreSQL and test helper dependencies were
  absent; this was also discarded as invalid environment evidence.
- The clean serial full run used the supported `>=3.12` interpreter line with
  development and PostgreSQL extras plus the existing dotenv test helper. It
  passed: `2314 passed, 67 skipped, 3 warnings, 6 subtests passed`.
- The exact GitHub Actions focused selection, including the new distribution
  test and coverage, passed: `871 passed, 2 skipped, 3 warnings, 3 subtests
  passed`; source coverage was 53%.
- `python -m build` produced `jltsql-1.6.10-py3-none-any.whl` and
  `jltsql-1.6.10.tar.gz`. The fail-closed checker accepted both; independent
  member enumeration confirmed `specs=0 docs=0` in each artifact.
- `mkdocs build --strict`, compileall for changed Python paths, fatal flake8
  checks over `src`, `tests`, and the checker, and `git diff --check` passed.
  The workflow's non-blocking mypy check was also executed without treating its
  existing advisory result as a merge gate.
- The sanitized public-document scan covered 51 tracked documentation-bearing
  files and reported `public_document_scan=PASS`. Outside the intentional
  regression-test constants, no tracked reference to the deleted page paths
  remains. The worktree was clean at this candidate.

The worklog evidence update changes only this tracked `specs/` file. Because
`specs/` is excluded from both release formats, the final evidence commit will
rerun the changed-surface distribution tests, actual artifact inspection,
strict documentation build, disclosure scan, and clean-tree check. The full
and workflow-equivalent suites above remain the code-tree evidence and are not
repeated for a documentation-only SHA update.

## GitHub review repair

- PR #186 was opened at final candidate
  `04a1860dd10783059600da77646451d87c9fc657`. GitHub Actions test and lint
  completed successfully. CodeRabbit reported a usage-limit skip and therefore
  supplied no review finding; it is not treated as review evidence.
- The single requested GitHub-native Copilot review was submitted against that
  full SHA and produced one concrete performance finding: `TarFile.getmembers()`
  materialized the complete sdist member list even though the checker consumes
  it once. The finding is accepted. The checker now iterates the `TarFile`
  directly, preserving the same fail-closed member checks with bounded memory.
- This does not add or change a validation rule, so the original red-first
  negative tests remain the contract. The review delta must pass the focused
  distribution suite, actual wheel/sdist build and inspection, strict MkDocs,
  fatal lint/compile, disclosure scan, and clean-tree gate before push.

## Next safe command

- Commit this evidence-only worklog update, run the proportional final-SHA
  checks described above, then push and open the documentation/distribution PR.
  Do not edit the release version or publish artifacts in this iteration.
