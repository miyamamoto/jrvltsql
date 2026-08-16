# jrvltsql final release-readiness worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: complete the final specification, public-documentation, privacy,
  distribution, live-acquisition, and release gates after the JV-Data
  compatibility repair series, then publish the next patch release only if all
  gates are green.
- Minimum scope for this first iteration: audit and repair tracked public text,
  specification evidence, packaging exclusions, stale pull requests, and any
  remaining contradiction between the merged implementation and the current
  plus immediately prior public contracts. Version publication and provider
  acquisition are deliberately deferred to a fresh post-merge release branch.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `$WORKSPACE/20260816_jrvltsql_release`.
- Branch: `agent/release-audit-20260816`.
- Base / initial HEAD / `origin/master` full SHA:
  `3a2c892649b8e9ec85113a7b0122e7e4d637443b`.
- Dependency order: merged compatibility PRs through #190; this audit PR if
  changes are needed; fresh release candidate; bounded new provider
  acquisition; version/release PR; tag and release publication; downstream
  NAR and MCP-server compatibility iterations.
- Release at start: `v1.6.10` at
  `dbb299a756e01bad4c79efd76d934c64f3d8af69`; project version `1.6.10`.
- Planned next patch version: `1.6.11`, subject to all gates below.
- Reviewer: Codex. No Claude session is used.

## Required gates

- Reconfirm that all official-layout and state-semantics findings merged after
  v1.6.10 are represented in code, tests, release notes, and compatibility
  language without claiming undocumented layouts as official history.
- Remove every remaining tracked disclosure of maintainer-prohibited private
  runtime provenance. The audit records only sanitized pass/fail counts and
  never copies the prohibited values into this file, PR text, or release text.
- Keep `specs/` tracked as the audit source of truth while proving that wheel
  and sdist exclude it, all deleted audit pages, and other non-release evidence.
- Confirm obsolete PRs #173 and #174 are fully superseded before closing them;
  never merge their stale heads.
- Run the proportional local suite, strict documentation build, distribution
  build/content gate, disclosure scan, and exact-SHA GitHub review/check gate
  for every code/documentation iteration.
- After the audit iteration is merged, create a fresh release branch from the
  new `origin/master`. Use that exact source for a bounded, authenticated, new
  provider acquisition. Require at least one newly obtained real record to be
  parsed and stored by the release candidate, with clean close/cleanup and no
  identity, record payload, key, filename, credential, or environment value in
  public evidence.
- Do not publish the release if the new acquisition is unavailable, stale,
  replay-only, partially parsed, not stored through the repaired code, or not
  bound to the exact release candidate full SHA.

## Starting state

- PR #190 merged H1/H6 standard snapshot storage as merge SHA
  `3a2c892649b8e9ec85113a7b0122e7e4d637443b`. Its source candidate
  `1bc2fa8e3b8d14aebc20528fc316263716577cb1` passed GitHub lint/test,
  focused parser/storage/mapping tests, fresh PostgreSQL integration, and all
  review threads were resolved before merge.
- PR #186 previously removed the four maintainer-designated audit pages and
  added a fail-closed wheel/sdist content checker. This iteration must verify
  the current tree rather than reuse that older candidate evidence.
- Open PRs #173 and #174 target older implementations that appear superseded
  by merged PRs #175 through #183. Exact file/behavior coverage and base drift
  must be checked before they are closed.

## Next safe action

- Inventory tracked public text using sanitized filename/count output, run the
  existing distribution checker against freshly built artifacts, compare open
  PR #173/#174 patches with the merged replacements, and enumerate any final
  implementation/specification contradiction. Stop before version changes or
  authenticated acquisition until this audit is complete and merged.

