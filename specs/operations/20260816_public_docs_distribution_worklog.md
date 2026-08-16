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

## Next safe command

- Commit the red test/evidence, then implement the smallest archive checker and
  wire one actual wheel+sdist build into CI. Do not edit release version or
  publish artifacts in this iteration.
