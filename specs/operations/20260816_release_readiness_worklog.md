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

## Audit iteration: public contract and SDK 5.0.0

- Re-fetched `origin/master`; the audit base remains
  `3a2c892649b8e9ec85113a7b0122e7e4d637443b`.
- Rechecked the official SDK index, the SDK 5.0.0 announcement, and developer
  community reports concerning installation coexistence. SDK 5.0.0 adds an
  x64 JV-Link while retaining x86. The published JV-Data/JV-Link reference
  documents remain version 4.9.0.1, and the official announcement states that
  their data and interface contracts did not change in SDK 5.0.0.
- Updated installation and quickstart entry points to require Python 3.12 or
  later and to select an interpreter whose bitness matches the installed
  JV-Link. The ordinary Python 3.12 launcher is preferred for a new setup; the
  explicit 32-bit launcher and an existing legacy virtual environment remain
  supported for upgrades.
- Removed two obsolete registry/launcher workaround files. Updated the
  class-not-registered diagnosis to recommend the matching JV-Link
  architecture rather than declaring one Python architecture unsupported.
- Sanitized tracked historical worklogs so public audit evidence uses
  `$WORKSPACE` and generic runtime roles instead of maintainer-local paths or
  private runtime provenance. A filename/count-only disclosure scan found no
  remaining prohibited value in tracked Markdown.
- Added the eight missing great-grandparent entries to `NL_SK` metadata, so
  all fourteen official lineage slots described by the parser/schema are also
  described to metadata consumers.
- Red-first evidence before implementation:
  - the matching-bitness diagnostic plus lineage metadata selection failed
    three tests;
  - the installer/launcher architecture selection failed two tests.
- Focused green evidence after implementation: the same five tests pass.
- PR #173 remains open but conflicting; its RC/KS/CH parser/schema changes are
  superseded by merged official-layout PRs. PR #174 now differs from current
  master only in `src/database/schema_metadata.py`; its one residual useful
  change is independently implemented here with the fourteen-slot regression
  test. Neither stale head is safe to merge.

## Audit iteration: fixed-record envelope

- Audited all 38 current record IDs against their current physical lengths,
  record identifiers, CP932 decoding, and CRLF terminators. Several custom
  parsers and inherited fixed-field parsers accepted adjacent or truncated
  input and could return a partial row.
- Red-first evidence before the shared gate: all 46 malformed cases selected
  across 23 initially weak record types passed through far enough to fail the
  new expectations. Expanding the matrix to every current type exposed four
  additional genuine wrong-type acceptances; five apparent failures were
  correctly classified as invalid blank domain payloads rather than envelope
  defects.
- Added a shared fixed-record validator and applied it to every current parser.
  H1/H6 accept only their exact full official physical record and their exact
  repository compatibility-row shape; no intermediate, empty, short, or
  oversized shape is accepted.
- Green evidence on the uncommitted aggregate candidate:
  - official record/parser/storage/metadata selection: 1,167 passed,
    47 skipped;
  - current/retired data-spec matrix and cancellation-state storage:
    278 passed, 20 skipped;
  - CI syntax/undefined-name selection: zero findings;
  - `git diff --check`: clean.
- A separate static pass found an obsolete `RT_RC` route that is not part of
  the official current realtime record list. Real jockey changes use the
  current `JC` route; the stale route is incompatible with normal `RC` parser
  dispatch. It will be removed with a dedicated red-first regression after the
  two already-developed iterations are split and merged.

## Next safe action

- Split the aggregate worktree into two logical commits/PRs: public
  SDK/documentation/metadata first, then fixed-record envelope validation.
  Run proportional tests, strict docs, disclosure and distribution checks on
  each exact candidate SHA. Merge each only with green checks, aggregated
  review findings, unresolved threads zero, and a clean worktree. Then remove
  the obsolete realtime route in a third focused iteration. Stop before version
  changes or authenticated acquisition until all audit iterations are merged.
