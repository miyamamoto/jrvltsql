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
- Reviewers: Codex plus one independent read-only Claude Code critical review
  documented below.

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
  later. An initial local commit preferred the ordinary interpreter and used
  wording that could be read as jrvltsql x64 support. That candidate was not
  pushed or proposed for merge. Maintainer review correctly required an actual
  x64 SDK end-to-end test before such a claim. The public text now separates
  the official SDK announcement from project evidence, and automatic launchers
  keep the already release-validated 32-bit path first. An explicit x64
  interpreter may be used only for the pending bounded validation.
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
- Red-first evidence for the corrected support boundary: three tests failed on
  the unpublished initial commit because launchers preferred the unverified
  architecture and public text claimed support without an SDK E2E result.
- Claude Code `--model fable --effort high` performed an independent read-only
  documentation review in session
  `bd9ea27f-29c0-4d9e-b829-419498a41712`. Fable was selected because a false
  release-support claim has a high rollback cost and the audit crosses docs,
  installers, launchers, packaging metadata, and release gates. Claude was
  denied edit/write tools and created no repository artifact.
- Actionable Claude findings were independently reproduced: two secondary
  launchers bypassed the release-validated interpreter preference; a tracked
  pre-JRA-only backup and an obsolete E2E script remained; the installer banner
  retained a removed product name; one historical H6 length was wrong; the
  package Documentation URL was invalid; and the v1.4.1 link had no matching
  changelog section. All are repaired in PR #191. Stale test
  install/count documentation had already been replaced while the review ran.
- The two missed launchers received their own red-first replay on intermediate
  commit `175cde9691d7d261218cd43440554c45664acdb8`: the retained regression
  failed because `fetch_timeseries_postgres.bat` lacked the validated
  interpreter branch. The same regression is included in the aggregate
  launcher test after the repair.
- Codex additionally found that the current standalone real-data E2E harness
  passes a removed constructor argument, reads dict statistics as attributes,
  and queries a non-existent race-name column. It cannot gate a release in its
  present state. This is a separate validator repair: prove these failures red,
  repair the harness, and run it with fresh provider data before release.
- Post-repair focused docs/installer/metadata/distribution selection:
  115 passed, 4 environment-specific skips. Fatal flake8 syntax/undefined-name
  selection reported zero findings; strict MkDocs completed successfully;
  staged `git diff --check` is clean. Tracked Markdown scans found no prohibited
  runtime disclosure or maintainer-local home path.
- Focused green evidence after implementation: the same five tests pass.
- PR #173 remains open but conflicting; its RC/KS/CH parser/schema changes are
  superseded by merged official-layout PRs. PR #174 now differs from current
  master only in `src/database/schema_metadata.py`; its one residual useful
  change is independently implemented here with the fourteen-slot regression
  test. Neither stale head is safe to merge.
- Split the public-contract/SDK/packaging iteration into branch
  `agent/sdk-docs-audit-20260816` and opened PR #191. Its pre-worklog-update
  candidate `717c09138f5e502c9d9d649e6a66242618f19eb6` was verified from a clean
  exact-SHA worktree: 115 focused tests passed with 4 environment-specific
  skips; strict MkDocs passed; sdist and wheel built; both generated artifacts
  passed the distribution-content checker; fatal flake8 checks reported zero
  findings; `git diff --check` was clean; and generated-archive plus tracked
  Markdown privacy/path scans passed. The final candidate SHA is recorded in
  PR metadata after this worklog update rather than by a self-referential
  follow-up commit.
- PR #191 GitHub review on the implementation predecessor produced eight
  unresolved threads which collapsed into three actionable defect classes:
  an existing virtual environment could be reused with bitness different from
  the selected interpreter; an activated/PATH installation could be bypassed
  by an unrelated global launcher; and explicit `PYTHON` override quoting was
  inconsistent across Windows entry points. All findings were accepted and
  repaired together rather than triggering one review cycle per comment.
- The explicit override contract is now one executable path, Python 3.12 or
  later. Invalid or compound command values fail loudly and never fall through
  to a different interpreter. An activated virtual environment precedes
  repository and global automatic discovery, and the time-series fetch helper
  restores its PATH-installed CLI fallback before global Python launchers.
  Installers recreate an existing virtual environment when its architecture
  differs from the selected interpreter.
- Red-first evidence on pre-repair PR head
  `694832ea05b312a9143854c43196518eacacc7fc`: four focused contract tests all
  failed, respectively exposing missing override validation/active-environment
  selection, missing virtual-environment bitness comparison, silent invalid
  override fallback, and missing PATH CLI selection. A fifth test failed on an
  unquoted PostgreSQL password argument.
- Resumed the same Claude Code Fable session
  `bd9ea27f-29c0-4d9e-b829-419498a41712` for the grouped review fix, preserving
  the original model/reasoning context. Its post-implementation read-only
  review found two additional cmd.exe parsing blockers: early expansion of a
  parenthesized interpreter path inside an IF block, and a password quoting
  form that exposed command metacharacters. Two focused tests failed on the
  intermediate implementation before both paths were changed to delayed
  expansion. The adjacent host/port/database/user arguments were quoted in the
  same already-open command construction.
- Green evidence after the grouped repair: all 15 launcher static contracts
  pass; the broader quickstart plus Windows-runtime selection reports 51
  passed and 3 expected non-Windows skips; workflow YAML parses; and
  `git diff --check` is clean. A dedicated Windows job now exercises an
  interpreter path containing spaces/parentheses, invalid compound override
  rejection, and PATH CLI precedence. That job is a launcher parser check only
  and is not SDK architecture or provider-acquisition evidence.

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

- Complete PR #191 at its final exact SHA with proportional local tests, strict
  docs, disclosure/distribution checks, aggregated review findings, unresolved
  threads zero, green Linux and Windows checks, and a clean worktree. Merge it before
  rebasing the fixed-record envelope iteration onto the resulting
  `origin/master`. Then repair the fail-open real-data E2E harness and remove
  the obsolete realtime route as separate red-first iterations. Stop before
  version changes or authenticated acquisition until all audit iterations are
  merged.
