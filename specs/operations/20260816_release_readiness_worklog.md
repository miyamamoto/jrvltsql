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
- Immediately before release, refresh every still-open pull request and compare
  its exact head diff against the latest `master`. Classify each as fully
  reflected, partially reflected, or still actionable. For a superseded pull
  request, leave a courteous evidence-based message thanking the contribution
  and naming the replacement PR/commit/test coverage before closing it. Do not
  close a pull request with a useful unreflected change; move that change into
  its own tested iteration first.
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
  the original model/reasoning context. Its first post-implementation pass
  raised a parenthesized-path hypothesis and found a password quoting form that
  exposed command metacharacters. The command assignment and PostgreSQL
  arguments were hardened, but the path hypothesis remained unproved until a
  native cmd.exe test could distinguish real Python execution from a shim.
- Green evidence after the grouped repair: all 15 launcher static contracts
  pass; the broader quickstart plus Windows-runtime selection reports 51
  passed and 3 expected non-Windows skips; workflow YAML parses; and
  `git diff --check` is clean. A dedicated Windows job now exercises an
  interpreter path containing spaces/parentheses, invalid compound override
  rejection, and PATH CLI precedence. That job is a launcher parser check only
  and is not SDK architecture or provider-acquisition evidence.
- The first Windows job on candidate
  `fbcbb877bced86fa706295fcd651babbb03ebbcf` failed before collecting any test:
  the minimal job installed pytest without pytest-cov while repository-wide
  addopts requested coverage arguments. This is a real workflow failure, not a
  billing exception and not launcher evidence. The job now clears global
  addopts for its isolated three-test selection; it must execute all three and
  finish green on the replacement exact SHA before merge.
- The second Windows job on candidate
  `0e9361fc8fb5e2a0249f467ec86a8d6cfe0dc546` collected and executed all three
  tests. Invalid compound override rejection and PATH CLI precedence passed.
  The parenthesized-path case failed while using a nested forwarding wrapper.
  That run alone could not distinguish wrapper re-parsing from a launcher
  defect, so it was not accepted as evidence.
- The third Windows job on candidate
  `8cac150318683b145da1d9564292a22374b210b3` replaced that wrapper with an
  argument-independent success stub and still failed at the launcher's version
  check. The stub was still a contract-external `.cmd` rather than a path to
  `python.exe`, so that run proved the gate was red but not why.
- A further read-only review in the same Fable session refuted the percent-path
  explanation from the observed control flow and found the actual shared
  defect: all ten batch Python-version probes pass `^<` inside a quoted Python
  `-c` program. In cmd.exe the caret remains part of that quoted argument, so a
  real Python receives invalid syntax and exits nonzero. Seven probes were
  introduced or made fail-loud in this PR; three existing installer probes
  also made automatic discovery or virtual-environment reuse fail. The runtime
  regression now creates a real Windows virtual environment under a path with
  spaces and parentheses, points `PYTHON` to its `python.exe`, and executes a
  minimal copied quickstart script.
- Red-first Windows run `31935316683` on intermediate full SHA
  `8f9de1ea4a72f3a88b233f3adf010870b483bf9a` created that real 32-bit Python
  3.12 environment successfully, then failed exactly at the launcher version
  gate with `ERROR: PYTHON must point to Python 3.12 or later`; the compound
  override and PATH-precedence runtime tests both passed. This is the required
  pre-implementation red evidence, not an accepted candidate.
- Replaced the quoted `^<` expression with quoted `<` in all ten probes and
  extended the existing static launcher regression to reject a reintroduced
  caret form. Post-repair local evidence is 51 passed with 3 expected
  non-Windows skips, fatal flake8 zero, workflow YAML parse success, no
  remaining caret-form batch probe, and clean `git diff --check`. The final
  exact SHA must execute and pass all three Windows runtime tests before merge.
- The resumed Fable post-repair review found no blocker. Its two optional
  evidence-strengthening suggestions were adopted: `daily_sync.bat` is now
  covered by the caret-form static guard, and the Windows marker includes and
  verifies the exact selected virtual-environment `sys.executable` path.
- Windows run `31935631538` on full SHA
  `e33a02cc0093452679cd7c7bba87dc99e2fe7d6a` proved the corrected version
  probe passed and the exact parenthesized-path venv interpreter executed the
  marker script. It then exposed a separate existing cmd.exe control-flow
  defect: an unescaped parenthesized `Setup Failed (Exit Code: ...)` ECHO line
  prematurely closed the surrounding failure block, so its remaining guidance
  executed even after a zero exit code. The same literal-ECHO class occurred
  in three grouped cache messages in `scripts/quickstart.bat`. All four are
  escaped together and the existing parenthesized-launcher static regression
  now covers their exact forms. A replacement exact-SHA Windows run must still
  pass all three tests.
- A same-session Fable follow-up was attempted for this second cmd.exe finding,
  but the local Claude subscription session limit had been reached. It produced
  no review result and is not counted as evidence. The finding and repair are
  instead grounded in the exact Windows output/control flow plus the focused
  regression; final release review must resume after the stated service reset.
- CodeRabbit then added seven inline threads plus one outside-diff finding from
  its intermediate-SHA review. The two delayed-expansion path claims are
  refuted by final run `31935845018`, which executed the exact selected real
  interpreter under a parenthesized path. The remaining findings were grouped
  before changes: workflow least privilege, fail-loud active-environment and
  fallback version validation, secret-safe PostgreSQL password transport,
  executable NL_SK metadata parity, public-evidence wording, quoted worklog
  commands, and redundant test f-strings are actionable.
- Red-first local evidence before that grouped repair: the revised password
  transport and NL_SK executable-metadata contracts fail `2 failed` because
  delayed expansion remains enabled around the secret argument and metadata
  still uses display names absent from the physical schema. A Windows runtime
  regression also supplies an invalid active environment and requires a clear
  fail-loud result without fallback; its intermediate exact-SHA run must be red
  before implementing the validator.
- Windows Actions run `31936387348` supplied that missing red evidence on full
  SHA `e2630c6dc26338f3ee94533401c33d79961afd1f`: the three earlier launcher
  runtime checks stayed green, while the new invalid-active-environment check
  failed its clear-message assertion after the malformed executable reached a
  generic exit-code path. The Linux job independently failed the two new local
  password/metadata contracts, and lint stayed green.
- The grouped repair now gives every active-environment, repository-local, and
  generic launcher fallback an actual Python 3.12-or-later probe; an invalid
  active environment fails loudly instead of falling through. Exact-version
  3.12 launcher selectors remain ahead of generic fallbacks. The PostgreSQL
  password is copied with delayed expansion disabled, inherited as
  `PGPASSWORD`, and omitted from process arguments. A Windows runtime test uses
  a synthetic password containing cmd metacharacters and verifies preservation
  without printing it. `NL_SK` metadata is now generated from the executable
  schema, so all physical columns, types, and the primary key match. The same
  repair also restricts workflow permissions, disables checkout credential
  persistence, corrects public-evidence wording and quoted worklog commands,
  and removes two redundant test f-string prefixes.
- Post-repair local focused evidence is 120 passed with 9 expected skips for
  the SK parser/storage, metadata, quickstart, and Windows launcher suites.
  The five Windows runtime checks, full Linux workflow suite, distribution
  build, and lint/type jobs remain mandatory on the final pushed SHA.

## Audit iteration: fixed-record envelope

- Continuation started after PR #191 merged as
  `a04733e640c67ad5d9c27860a6253c16c9fce850`. The current dedicated worktree
  is `$WORKSPACE/20260816_jrvltsql_fixed_record`, branch
  `agent/fixed-record-envelope-20260816`, based on that exact `origin/master`.
  Only the fixed-record implementation/test diff was transferred from the old
  audit worktree; its first current-base commit is
  `3c958876e9761b9650948f5811c9aca009ef5e07`.
- This is a fail-closed validator change, so the planned independent coding
  review uses Claude Code `--model fable` in a new session for this worktree
  and iteration. The session ID will be recorded when that review starts.
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
- Historical green evidence on the pre-rebase aggregate candidate, retained
  only as development evidence and not as a gate for the current SHA:
  - official record/parser/storage/metadata selection: 1,167 passed,
    47 skipped;
  - current/retired data-spec matrix and cancellation-state storage:
    278 passed, 20 skipped;
  - CI syntax/undefined-name selection: zero findings;
  - `git diff --check`: clean.
- The first full current-base suite on implementation commit
  `3c958876e9761b9650948f5811c9aca009ef5e07` was deliberately treated as a
  gate and failed: 73 failed, 2,375 passed, 90 skipped. Most failures exposed
  an older broad parser fixture that supplied approximate lengths or omitted
  CRLF while still expecting success; one old robustness assertion explicitly
  expected oversized HR input to parse. Those expectations contradicted the
  new physical-envelope contract. The two CLI failures did not reproduce in
  isolation or with their preceding module and were not attributed to this
  change without evidence.
- Updated that existing fixture to derive each positive sample from the
  parser's current declared physical length, terminate every fixed record with
  CRLF, and keep only the already-required domain payload population. The
  oversized HR expectation now rejects trailing bytes like RA and SE. The
  focused parser/envelope selection passed 482 tests, then the complete suite
  passed 2,448 tests with 90 environment-specific skips, 15 subtests, and only
  three pre-existing pytest return-value warnings. The previously observed CLI
  failures were green in the complete rerun.
- A separate static pass found an obsolete `RT_RC` route that is not part of
  the official current realtime record list. Real jockey changes use the
  current `JC` route; the stale route is incompatible with normal `RC` parser
  dispatch. It will be removed with a dedicated red-first regression after the
  two already-developed iterations are split and merged.

## Next safe action

- Run the fixed-record focused and compatibility suites on the current-base
  candidate, reconcile every declared length with current parser constants,
  then perform the independent Fable review. Create and merge a dedicated PR
  only after exact-SHA checks, all actionable findings, unresolved threads
  zero, and clean worktree are complete. Then repair the fail-open real-data
  E2E harness and remove the obsolete realtime route as separate red-first
  iterations. Stop before version changes or authenticated acquisition until
  all audit iterations are merged.
