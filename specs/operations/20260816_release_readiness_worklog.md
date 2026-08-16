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
  review uses Claude Code 2.1.226 with `--model fable --effort high` in session
  `81f08480-ef14-435c-9a06-1f7592fbfac5` for this worktree and iteration. The
  first read-only attempt hit the subscription session limit before producing
  a review, so it is not evidence; resume this same session after the reported
  20:10 JST reset rather than starting a new one.
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
  Empty, short, oversized, wrong-ID, non-CRLF, and whole-record-invalid CP932
  inputs are rejected before persistence. A later independent review found
  that the H1/H6 repository reconstructions were still incorrectly included as
  accepted lengths; the grouped correction is recorded below.
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
- On clean full SHA `7b6c853cf5eb86aa9c2bad184eb2df2ebda846d6`, the
  independent length/factory parity check plus the focused parser/envelope
  selection passed 483 tests. The complete suite then passed 2,449 tests with
  90 environment-specific skips, 15 subtests, and the same three pre-existing
  warnings. This is pre-repair development evidence and is non-gating because
  that SHA still accepted the repository-only H1/H6 layouts. Fatal flake8
  syntax/undefined-name checks reported zero, and mypy with imports skipped
  reported zero issues in all 38 changed parser files.
- Repository-wide mypy is not green: the direct workflow command reports 79
  pre-existing errors in 20 files. The workflow's `continue-on-error` setting
  makes the job look successful, so neither PR #191 nor this iteration treats
  that status as a zero-error type gate. PR #191 received a public evidence
  correction. This debt remains explicit for the release audit rather than
  being misreported or silently attributed to the fixed-record change.
- A local distribution rebuild was attempted on the exact SHA but the current
  environment lacks the `build` module. That missing optional local tool is
  not waived as release evidence: wheel/sdist generation plus the content gate
  must run in the PR workflow on the final pushed SHA.
- A separate static pass found an obsolete `RT_RC` route that is not part of
  the official current realtime record list. Real jockey changes use the
  current `JC` route; the stale route is incompatible with normal `RC` parser
  dispatch. It will be removed with a dedicated red-first regression after the
  two already-developed iterations are split and merged.

- PR #192 was opened for this iteration. Candidate
  `a8b36412e32116f44c55594178e78694ec7e58b6` passed GitHub Linux tests,
  lint, distribution build/content checks, and the Windows launcher job in run
  `31937860098`; performance was the expected skipped job. Its worktree was
  clean and unresolved review threads were zero, but that candidate was not
  merged because independent review found two data-integrity blockers.
- Existing PR heads #173 (`2cb09402bb1cc71f83543b43dab6b4e84534fea1`)
  and #174 (`100d568f8b9cbf3bccf6dba7e5415da7c7cf544b`) were compared again with
  `master` `a04733e640c67ad5d9c27860a6253c16c9fce850`. Their parser/schema intent
  is fully represented by #175 through #183, and #174's remaining metadata
  intent is represented more safely by #191's executable-schema mapping. The
  focused replacement evidence was 262 passed, 10 skipped, and 3 subtests.
  Courteous evidence-based comments thanked the contributor, identified the
  replacement PRs, and explained why merging either stale head would regress
  the normalized storage work; both PRs were then closed as superseded.
- A fresh mechanical extraction of the official 4.9.0.1 format worksheet found
  exactly 38 current record types. Every parser `RECORD_LENGTH` matches its
  official physical length. Comparing 4.8.0.2 with 4.9.0.1 found exactly seven
  changed physical lengths (BR, BT, CK, HN, HS, SK, and UM), all matching the
  implementation. H1 remains 28,955 bytes and H6 remains 102,890 bytes in both
  official versions; the repository-only 317/78-byte reconstructions are not
  provider layouts.
- The independent Codex review of exact SHA
  `a8b36412e32116f44c55594178e78694ec7e58b6` reproduced both blockers. The
  default factory accepted the two repository-only vote reconstructions, so a
  provider record truncated to either exact synthetic length could be stored.
  Whole-record strict CP932 validation also missed a valid two-byte sequence
  split across adjacent fixed fields; field decoders using replacement mode
  then persisted U+FFFD or an empty value instead of rejecting the row.
- Red-first proof on that implementation: the new focused regression reported
  six failures. Two showed H1/H6 synthetic lengths returning parsed data; four
  showed AV, BaseParser/BT, H1, and H6 accepting a CP932 pair split between the
  final byte of `MakeDate` and the first byte of the following physical field.
  The whole raw record decoded strictly, proving the missing check was the
  field boundary rather than generic invalid encoding.
- The grouped repair removes the synthetic H1/H6 layouts from the provider
  parsers and deletes their production parsing branches. Every field decoder
  that previously used replacement mode now decodes its fixed byte slice
  strictly. BaseParser re-raises a field UnicodeDecodeError rather than
  converting it into a partial row. The H1/H6 and O1-O6 repository
  reconstructions are no longer labelled or exercised as provider vote
  records; the broader reconstructed fixture suite remains a release-blocking
  follow-up and is not described as repaired here. Post-repair, the six red
  cases pass. Those replaced cases are three H1 flat tests, two H6 flat tests,
  and `test_sqlite_standard_vote_flat_compatibility_layouts`. Extending the
  same boundary contract to every parser whose decoder changed gives 98 passed
  in the complete 38-type envelope matrix. The affected
  parser/fixture/storage selection reports 395 passed with 20
  environment-specific skips. A scan of production parsers finds no remaining
  replacement-mode decoder or synthetic flat-length branch.
- The complete local suite initially stopped during collection because the
  new scratch Python 3.12 environment did not yet contain the optional
  PostgreSQL driver or dotenv test dependency; no test executed in that run.
  After installing the repository's test/optional dependencies into that
  external environment, the same suite completed with 2,443 passed, 90
  environment-specific skips, 15 subtests passed, and the same three existing
  pytest return-value warnings. Workflow-equivalent fatal flake8 checks report
  zero, changed-parser mypy with imported modules skipped reports zero, and
  `git diff --check` is clean. Repo-wide all-rule lint/type debt remains
  distinct from this candidate and is not reported as green.
- GitHub workflow run `31939754174` on exact SHA
  `1efd998b66d416bc4c2763deeadaadfe5ff1e386` ran the workflow's configured
  subset and reported 944 passed. It is distinct from, and does not replace,
  the local full-suite result of 2,443 passed on the same SHA.
- Codex independently expanded the official SDK 5.0.0 Python structures into
  46,985 scalar leaves across 94 structures and 93 repeated templates. All 38
  current record lengths were gap/overlap free and matched both the executable
  parser declarations and JV-Data 4.9.0.1. The 4.8.0.2 to 4.9.0.1 physical
  changes are UM 1577, BR 537, HN 245, SK 178, CK 6864, HS 196, and BT 6887;
  current N-layout dispatch rejects all seven previous lengths. The source
  SHA-256 values used were `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`
  for JV-Data 4.8.0.2, `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`
  for JV-Data 4.9.0.1, and
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`
  for the SDK structure.
- A warning-strict local audit on exact SHA
  `1efd998b66d416bc4c2763deeadaadfe5ff1e386` reported 3 failed, 2,455
  passed, 84 skipped, and 15 subtests. The three failures are pytest functions
  returning non-None values in `test_key_generation`,
  `test_fetch_time_series_method`, and `test_list_methods`; this is explicit
  red evidence for the separate test-truth iteration, not a green result for
  this candidate.
- The official-contract coverage audit found release blockers outside this
  iteration: HY assigns the official KettoNum/Bamei/Origin spans to the wrong
  fields and primary key; CK omits 988 of 1,729 official leaves; standard
  schema routing cannot store BT, CK, HY, JG, WC, or WF; executable metadata
  disagrees with 70 of 78 schemas; and the current real-data E2E harness has
  invalid call signatures, no PostgreSQL path, and no fail-closed fresh
  download/EOF/close evidence. These require separate red-first PRs before a
  release.
- Claude Code 2.1.233 resumed the same Fable session
  `81f08480-ef14-435c-9a06-1f7592fbfac5` after its 20:10 JST reset and
  independently reviewed clean exact SHA
  `1efd998b66d416bc4c2763deeadaadfe5ff1e386` read-only. Fable was retained
  because this fail-closed boundary has high rollback cost. It confirmed the
  official source hashes, all 38 current lengths, removal of H1 317/H6 78,
  strict fixed-field CP932 boundaries, and no official-leaf boundary split.
  It classified two remaining PR-local blockers: the new 38-type gate was not
  in the workflow whitelist, and the existing oversized-record test also had
  an invalid delimiter. The grouped follow-up adds the gate to CI and makes
  the oversized regression retain a valid CRLF delimiter. CK, HY, the six
  standard-schema routes, the broader CI contract gap, and real-data E2E were
  independently classified as downstream release blockers.
- Before the grouped follow-up commit, the current-record and parser selection
  passed 511 tests with coverage disabled, workflow YAML parsed successfully,
  fatal flake8 syntax/undefined-name checks reported zero, and
  `git diff --check` was clean. This is development evidence; the same focused
  selection and the workflow-configured suite must be bound to the pushed full
  SHA before merge.

## Fixed-record envelope outcome

- The grouped PR #192 follow-up was committed and pushed as exact candidate
  `5390272ffade21b350d0466cce429c194f0df98a`. Local focused evidence was 511
  passed; the workflow-equivalent selection was 1,049 passed, 2 skipped, 3
  known warnings, and 12 subtests. GitHub run `31945371164` bound to the same
  SHA completed Linux tests, distribution content verification, the Windows
  launcher job, and lint successfully; the performance job had zero executed
  steps and was the expected non-master skip. All review findings were either
  repaired or independently refuted with evidence, unresolved threads were
  zero, and the worktree was clean. PR #192 was squash-merged as
  `89ef8f68d5d854c0e17d7540a7b8fafc91511714` on 2026-08-16. The merged and
  red-reproduction worktrees were then removed.

## Audit iteration: test-truth gate

- Objective: make the deterministic test suite and GitHub workflow fail closed
  before adding the compact official oracle. The minimum scope is test
  collection, warning/error policy, fatal lint wiring, truthful fixture
  provenance, and removal or isolation of manual live scripts that currently
  masquerade as pytest gates. Production parser/schema/import behavior is out
  of scope for this iteration.
- Repository: `miyamamoto/jrvltsql`. Dedicated worktree:
  `$WORKSPACE/20260816_jrvltsql_test_truth`. Branch:
  `agent/test-truth-gate-20260816`. Base and initial HEAD:
  `89ef8f68d5d854c0e17d7540a7b8fafc91511714`, fetched from current
  `origin/master`. The worktree was clean at start. Production/release remains
  v1.6.10; no version, tag, package publication, or provider acquisition is in
  this iteration.
- Dependency order: merge this test-truth PR first; start the compact official
  38-record oracle from its merge SHA; then repair HY, CK, standard schema
  routing, obsolete routes, metadata, and real-data E2E in independent
  iterations. Do not interpret a green test-truth PR as release readiness.
- Existing red evidence to preserve:
  - warning-strict deterministic-suite audit: 3 failed because pytest test
    functions return booleans instead of using assertions/skips;
  - the workflow executes a hand-selected subset and omits most official
    contract files;
  - fatal flake8 and mypy are both placed behind step-level
    `continue-on-error`, so a real fatal lint failure can be reported as a
    successful job;
  - reconstructed database-row fixtures are described as real provider bytes,
    and several manual Windows/live scripts catch failures or return booleans;
  - the standalone E2E harness is invalid and remains excluded until its own
    fail-closed iteration.
- Claude Code 2.1.233 will use `--model fable --effort high` in session
  `b63e9497-10e4-45d0-bf19-3f369dc6332d`. Fable is selected because changing
  a release gate can create false-green results and because collection,
  environment boundaries, fixtures, and CI ordering interact. The initial
  turn is read-only critical audit; implementation review will resume the same
  session for this worktree and iteration.
- Codex audited the exact clean start commit
  `29b4b464927fc061d52939294af2b6272d5b01b9`: pytest collected 2,555 tests
  from 76 files, while the workflow selected only 16 files and omitted 60.
  A warning-strict deterministic run reported 5 failed, 2,446 passed, 84
  skipped, and 15 subtests. Three failures were the known non-None pytest
  returns. The two CLI failures passed immediately in isolation and with all
  preceding modules, so they are recorded as a concurrent-run/transient
  observation rather than an attributed defect. The exact failing return
  functions and CI collection gap remain reproducible.
- The independent Fable audit inspected actual clean HEAD
  `29b4b464927fc061d52939294af2b6272d5b01b9` and classified the iteration
  `NEEDS_CHANGES`. It independently measured 2,555 collected tests, found the
  workflow selecting about 41% of collected cases, reproduced three
  `PytestReturnNotNoneWarning` failures, verified fatal flake8 has a true
  failing negative case but is currently advisory, and found repo-wide mypy
  remains advisory debt. It also reproduced collection failure without the
  undeclared dotenv package, import-time logging resource warnings, misleading
  PostgreSQL skip reasons, and self-derived database-row fixture provenance.
  The initial prompt contained an incorrect expanded SHA after the valid short
  prefix; Fable explicitly rejected that value, resolved and reported the
  actual full HEAD above, and performed the audit against it.
- The grouped implementation scope after reconciliation is: add one
  fail-closed CI configuration validator with a negative and positive control;
  remove undeclared dotenv collection dependencies and boolean-return live
  pseudo-tests; make warnings fatal without import-time log resources; gate
  live PostgreSQL tests on an explicit environment variable and fail when an
  opted-in server is unavailable; remove duplicate no-assert parser cases;
  label and relocate reconstructed database-row fixtures away from provider or
  official fixture namespaces; and make the workflow collect the whole
  deterministic tree. Production data-contract defects remain out of scope.
- The test-gate validator and paired controls were committed separately as
  exact SHA `6bcce2015e1d04e3679d3444a273203b76f83d26`. Against the then-current
  workflow, `tests/test_ci_test_gate.py` produced the required red result:
  1 failed and 3 passed. The repository case reported eight configuration
  errors, including the fixed pytest allowlist, missing integration/slow and
  warning exclusions, missing self-check, and non-fatal flake8 wiring. The
  synthetic valid workflow remained green, proving the validator was capable
  of both rejection and acceptance.
- The grouped implementation now runs the whole deterministic `tests` tree in
  CI, excludes only explicit authenticated/E2E and slow boundaries, treats
  warnings as errors, validates the CI gate before pytest, makes fatal flake8
  a real job failure, and continues to label repository-wide mypy/style debt
  advisory. The Windows launcher job keeps strict pytest configuration instead
  of clearing all configured safeguards.
- The three boolean-return pseudo-tests were replaced with assertions or moved
  out of pytest collection. Duplicate parser cases that caught exceptions but
  asserted nothing were removed. Manual database/download scripts were moved
  to `scripts/` or `tools/manual/`, and collection no longer requires the
  undeclared dotenv package. Test imports suppress production auto-logging so
  collection does not open repository-local log handlers.
- Reconstructed binary fixtures were moved from `fixtures/jra` to
  `fixtures/reconstructed_db`; the generator, test module, class names, and
  documentation now state that they are synthetic records reconstructed from
  already-parsed database rows and do not prove physical provider layout.
  A missing fixture is now a failure rather than a skip. Deterministic
  parse/import tests use complete current synthetic RA/SE/HR records and assert
  parse, insert counts, readback values, EOF, and close calls instead of
  succeeding through conditional assertions.
- Live PostgreSQL cases now require the explicit
  `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1` opt-in. When opted in, missing drivers,
  failed connections, schema failures, read failures, and cleanup failures are
  test failures rather than being mislabeled as an unavailable-driver skip.
- The first grouped focused run exposed two newly meaningful failures: the
  realtime mock supplied JVRead EOF (`0`) instead of a positive record length,
  and one transaction test referenced a nonexistent fixture attribute. Both
  test defects were corrected; the affected comprehensive/metadata/PostgreSQL
  selection then passed 41 tests with 7 explicit live-environment skips. The
  gate controls passed 4 tests and the current workflow self-check reported
  `TEST GATE PASS`; workflow YAML parsing and `git diff --check` were clean.
- A first whole-tree warning-strict run after the grouped changes reported one
  failure, 2,262 passed, 79 explicit environment skips, 14 slow deselections,
  and 15 subtests. The sole failure was an older transport contract that still
  required its filename to appear in the former workflow allowlist. It was
  updated to require whole-tree collection and to prohibit exclusion of that
  module. This was a test-expectation repair caused by the intentional CI
  selection change, not a production-code failure. A final whole-tree run is
  still required on the committed candidate full SHA.
- On clean exact SHA `9b601e6adb3aa4ecb70bbd57f245b706cd8c61ad`, the
  fail-closed self-check and fatal flake8 passed, followed by the whole
  deterministic tree: 2,263 passed, 79 explicit environment skips, 14 slow
  deselections, and 15 subtests, with zero warning or test failures. The
  wheel/sdist build and distribution-content gate also passed for both
  artifacts. This evidence predates the final validator hardening below and
  remains code-identical except for that gate/test/tool scope follow-up.
- Claude Code 2.1.233 resumed the same Fable session
  `b63e9497-10e4-45d0-bf19-3f369dc6332d` with `--model fable --effort high`
  and independently reviewed clean exact SHA
  `9b601e6adb3aa4ecb70bbd57f245b706cd8c61ad` read-only. It reproduced the
  prior red and current whole-tree green, confirmed collection without dotenv,
  verified that opted-in PostgreSQL failures no longer skip, checked moved and
  deleted test coverage, fixture provenance, docs, and distribution scope, and
  returned `NEEDS_CHANGES` for two iteration-local defects. The validator did
  not reject conditional/advisory pytest jobs or steps, warning-policy
  overrides, selection/status-masking arguments, or unapproved ignores. The
  moved manual database tool also retained one now-undefined `load_dotenv()`
  call outside the fatal lint scope. Known HY/CK/schema/metadata/E2E findings
  were again classified as downstream rather than silently waived.
- Codex independently found the same main-gate conditional/advisory and
  warning-override bypasses before receiving the Fable response. Findings were
  aggregated once. The existing negative gate test was expanded before the
  implementation; against the reviewed implementation it produced the
  required red result of 1 failed and 3 passed, listing every newly expected
  refusal code. The paired valid workflow remained green.
- The grouped hardening now rejects `if` or any non-false
  `continue-on-error` on required test/lint jobs and test/self-check/fatal-lint
  steps, requires the exact global warning-error policy, rejects warning
  suppression, partial selection, collect-only, unapproved ignore/deselect,
  and shell status masking in the pytest command, and requires fatal lint to
  cover `src`, `tests`, `scripts`, and `tools`. The undefined manual-tool call
  was removed. The expanded negative/positive gate test passes 4 tests, the
  repository self-check reports `TEST GATE PASS`, and the enlarged fatal lint
  scope reports zero findings.
- PR #193 was opened and marked ready at candidate
  `86d6e96346b8d00a70894f1aac60e499e3d151bf`. GitHub run `31947867380`
  executed rather than encountering a Billing failure. Lint and the 32-bit
  Windows launcher contract passed, but the Linux test job failed after
  running the suite: 2 failed, 2,261 passed, 79 skipped, 14 deselected, and 15
  subtests. The failures were `version` and `status`, both returning exit 1.
  Distribution steps correctly did not run after the real test failure, so the
  candidate was not considered mergeable.
- The failure was independently reproduced as a clean-install contract rather
  than attributed to coverage. A clean GitHub checkout has no
  `config/config.yaml`, while the local development checkout did. The CLI group
  allowed only `init` before configuration, so read-only `version` and `status`
  were unusable in a fresh installation; the previous workflow allowlist had
  never collected `test_cli.py`. Existing tests were first fixed to force the
  no-config state and produced the required red result of 2 failed. The CLI now
  permits `init`, `version`, and `status` without configuration while retaining
  the configuration gate for data-mutating commands. The focused basic/init
  CLI selection then passed 5 tests with coverage enabled. This is a production
  bootstrap repair exposed by the truthful whole-tree CI, not a test waiver.
- PR #193 review findings were aggregated once against exact HEAD
  `1364980a137132a0cd2d3c598f7f22a4f77ac5bb` and repaired in the same Fable
  session `b63e9497-10e4-45d0-bf19-3f369dc6332d` (`--model fable --effort
  high`). Fable was kept because the change set is a release gate whose
  failure mode is a false green: every added refusal must be proven against
  the pre-repair validator, and the shell/YAML/pytest/psycopg surfaces
  interact. Negative tests were added first. Red evidence on the pre-repair
  code: `tests/test_ci_test_gate.py` gained one table-driven test
  (`test_validator_rejects_single_command_masking`, 19 rows) and reported
  18 failed / 5 passed — the pre-repair validator accepted `true` or `exit 0`
  on a new line after pytest, `set +e` before it, `bash -c` wrapping, `-c
  /dev/null`, missing `--ignore=tests/e2e`, `PYTEST_ADDOPTS`/`PYTHONWARNINGS`
  in workflow/job/step `env`, custom `shell`/`working-directory`, an `echo`
  or extra-argument self-check step, `true` after the self-check, and an
  `echo`, newline `true`, `|| true`, or custom-shell fatal flake8 step; only
  the same-line `; true` row was already refused. `tests/test_postgresql.py`
  gained one parametrized contract test and one bootstrap-script test, which
  failed at collection (`ImportError: cannot import name
  'postgresql_test_config' from 'scripts.setup_pg_test_db'`) because no shared
  live-PostgreSQL contract existed. The CLI no-config guard was extended in
  the existing status test to also require `fetch` to exit 1 with the
  configuration error; a one-off run with `fetch` added to
  `CONFIG_OPTIONAL_COMMANDS` produced 1 failure, and the committed code passes.
- Repairs: `scripts/validate_test_gate.py` now treats the self-check, pytest,
  and fatal flake8 steps as exactly one executed command each — one non-comment
  logical line, no shell operators (`| & ; < > $ ( ) { }` or backticks), no
  `if`, `continue-on-error`, `shell`, or `working-directory`; the self-check
  must be literally `python scripts/validate_test_gate.py`; the pytest command
  must start `pytest tests`, carry `--ignore=tests/integration`,
  `--ignore=tests/e2e`, and `-m "not slow"`, and may only add `-v`, `-q`,
  `-r…`, `--cov=src`, `--cov-report=…`, `--durations=…`; any other option,
  ini/override, plugin toggle, warning flag, selection flag, extra ignore, or
  `PYTEST_ADDOPTS`/`PYTHONWARNINGS` env is refused with a stable code; the
  fatal flake8 step is identified by its `flake8` command token and select
  set rather than substring, and must cover `src tests scripts tools`.
  `scripts/setup_pg_test_db.py` now defines the single
  `postgresql_test_config()` contract (`POSTGRES_*` over `PG*`, default
  `jltsql_test`/`jltsql`/empty password/5 s), passes psycopg3
  `connect_timeout` instead of the invalid `timeout` keyword, and quotes the
  environment-derived database name with `psycopg.sql.Identifier`.
  `tests/test_e2e_comprehensive.py`, `tests/test_metadata_application.py`,
  and `tests/test_postgresql.py` import that contract instead of three
  divergent inline dictionaries. The duplicated `## Next safe action` heading
  from the envelope iteration was renamed to `## Fixed-record envelope
  outcome`.
- Green evidence after the repairs on the working tree above HEAD `1364980`:
  gate tests 23 passed; repository self-check `TEST GATE PASS`; the validator
  against the base `89ef8f6` configuration reports 11 refusal codes and
  against `9b601e6` reports only the flake8 scope gap; focused
  gate/PostgreSQL/CLI/transport selection 140 passed with 9 explicit
  environment skips; opted-in PostgreSQL without a server 9 failed and 0
  skipped; fatal flake8 over `src tests scripts tools` reported 0; workflow
  YAML parses and `git diff --check` is clean; the whole deterministic tree
  reported 2,286 passed, 79 explicit environment skips, 14 slow deselections,
  15 subtests, and zero warnings or failures.
- Codex then independently reviewed the repaired validator and found three
  remaining instances of the same false-green class before any review-fix
  commit or push: workflow/job `defaults.run.shell` could replace every
  required command with a successful no-op, fatal flake8 accepted an
  `--exclude` covering all required roots, and the validator did not constrain
  pytest's `addopts` or collection patterns in `pyproject.toml`. Existing
  table-driven gate coverage was extended rather than adding one test function
  per hypothesis. Against the then-current implementation the exact focused
  run reported the required red result of 6 failed and 23 passed: three custom
  run-default scopes, one flake8 exclusion, one `-k never` addopts mutation,
  and one narrowed `python_functions` mutation were all incorrectly accepted.
- The same Fable session and model were resumed with that red evidence, but
  Claude Code returned its account session limit before making any further
  change. Codex completed the already-scoped repair: workflow, test-job, and
  lint-job custom run defaults now have distinct refusal codes; fatal flake8
  permits only its current non-selection-changing command tokens; and the
  deterministic pytest collection/addopts/warning contract is compared
  exactly with `pyproject.toml`. The paired focused gate run is now 29 passed,
  the repository self-check reports `TEST GATE PASS`, changed-file fatal lint
  and `git diff --check` pass, and the combined gate/PostgreSQL/CLI/transport
  focused selection reports 147 passed with 9 explicit live-environment
  skips. The prior whole-tree result remains evidence for the pre-follow-up
  working tree only; GitHub must rerun it on the final pushed full SHA.
- A final Codex inspection found that flake8 would still read a future
  repository `.flake8`/`setup.cfg` and could therefore inherit an exclusion
  outside the validated workflow command. The existing parameter table gained
  one row; before implementation it produced the required red result of 1
  failed and 29 passed. Fatal lint now requires `--isolated`, the workflow uses
  it, and only non-selection-changing tokens are allowed. The paired gate run
  is 30 passed, the repository self-check is `TEST GATE PASS`, and the exact
  isolated fatal command reports zero findings across `src tests scripts
  tools`.
- GitHub Actions run `31949422208` executed on exact code/review-fix candidate
  `6afb96ad694f3a54ccf647344ae4f64417bf6eda`: the fail-closed self-check,
  isolated fatal lint, Linux deterministic tree, distribution build/content
  validation, and 32-bit Windows launcher contract all passed. The Linux tree
  reported 2,293 passed, 79 explicit environment skips, 14 slow deselections,
  and 15 passing subtests; both wheel and sdist passed the distribution-content
  gate. The later worklog-heading correction is documentation-only, so its
  successor SHA still requires the automatically triggered final checks rather
  than reusing this run as exact-SHA evidence.

## Next safe action: test-truth gate

- Commit and push the review repairs, run the affected gate/PostgreSQL/CLI
  checks and the whole-tree workflow on the exact pushed SHA, resolve every
  PR #193 thread with that evidence, and merge only if all executed mandatory
  jobs pass. The compact official oracle and known HY, CK, standard-schema,
  metadata, obsolete-route, and strict fresh E2E blockers remain separate
  required iterations after this PR.

## Official 38-record oracle iteration start

- Objective and minimum scope: add a compact, mechanically validated oracle
  derived from the official current JV-Data layout, make the deterministic CI
  collect it, label reconstructed database fixtures truthfully, and add the
  current and historical physical-length regressions needed to expose known
  specification gaps. Storage mapping is deliberately outside this physical
  oracle PR: HY, CK, standard-schema routing, metadata, and fresh live E2E are
  repaired in the following independent iterations rather than being made
  green by encoding the current implementation's assumptions here.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260816_jrvltsql_official_oracle`.
- Branch: `agent/official-oracle-20260816`.
- Base and initial HEAD:
  `8baf34a79783370f17ac8430151cd212a496965e` (latest fetched
  `origin/master`, squash merge of PR #193).
- Dependency order: PR #193's fail-closed whole-tree CI is merged first; this
  oracle iteration is based on that merge and must itself merge before HY/CK
  and storage-routing implementation iterations use its contracts.
- Prior production/release reference remains version `1.6.10`; no release or
  release-lock mutation is authorized by this iteration alone.
- Initial state is clean. Existing independent audit evidence reports 38
  current record lengths matching official SDK 5.0.0, 94 structures, 93
  repeated templates, and 46,985 recursively expanded scalar leaves with no
  official-layout gap or overlap. The implementation must reproduce or encode
  that evidence from repository-tracked inputs rather than relying on a local
  scratch-only report.
- Initial safe action: inventory tracked official-spec inputs and current
  contract tests, then design one compact physical manifest/validator with
  red-first tests for missing spans, overlap, incorrect repeat count, unknown
  nested structures, source provenance, and inspection failure. Leaf-to-storage
  disposition and nonexistent storage targets belong to the following schema
  implementation iteration because they require model/storage decisions beyond
  the official byte layout.
- STOP conditions: do not copy or redistribute proprietary provider samples;
  do not invent offsets from current parser code as the oracle; do not mark a
  known HY/CK/storage mismatch green by reproducing the implementation's own
  assumptions; do not claim 64-bit support; do not merge if the oracle cannot
  identify its official source/version/hash or if any required contract remains
  unresolved.
- Red-first evidence: before adding the oracle implementation or manifest,
  `tests/test_official_jvdata_oracle.py` failed during collection with
  `ModuleNotFoundError: scripts.official_jvdata_oracle`. No oracle assertion
  ran, so this is an explicit missing-inspection red rather than a parser
  failure. The paired validator negatives and official-manifest assertions
  must turn green only after the independent extractor, tracked manifest, and
  provenance are present.
- Implemented `scripts/official_jvdata_oracle.py` as a reviewed-AST extractor
  for the SDK's scalar, nested, and fixed-repeat grammar. It produces only
  derived names, one-based byte spans, widths, repeat counts/strides, source
  identity, and aggregate counts; it does not copy SDK source or provider
  records. The validator fails closed on unreadable input, incomplete source
  identity, bad spans, gaps, overlap, invalid repeat definitions, unknown or
  cyclic structures, nested-width mismatch, count mismatch, and root-length
  mismatch.
- The tracked SDK 5.0.0 manifest identifies source SHA-256
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`
  and independently expands to 38 root records, 94 structures, 93 repeat
  templates, and 46,985 scalar leaves. Regeneration from that exact official
  source is byte-for-byte identical to the tracked JSON, and the validator
  reports `OFFICIAL ORACLE PASS`.
- Added a physical-layout history ledger backed by official workbook SHA-256
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`
  for 4.8.0.2 and
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`
  for 4.9.0.1. It records the 2003 SE, BR, and BN length changes; the 2023 UM,
  BR, HN, SK, CK, HS, and BT changes; the PR-to-BR identifier transition; and
  the 2006 UM same-length semantic split. The latter is explicitly marked as
  requiring generation provenance because record length cannot distinguish
  the old 80-byte English-name interpretation from the current 60+1+19 byte
  fields.
- `test_current_record_validation.py` now derives all 38 current lengths and
  every historical rejection case from these official manifests instead of a
  second hand-maintained matrix. The factory still accepts only the current N
  layout; it rejects every ledgered previous physical length, including both
  pre-2003 and 4.8.0.2 generations where applicable.
- Additional validator negatives were proven red before implementation:
  self-reference produced only aggregate count mismatches rather than a cycle
  error; missing artifact/version provenance passed; and Boolean leaf counts
  were accepted as integers. The red run was 3 failed and 13 passed after the
  earlier cycle/history red run of 2 failed and 11 passed. All are now explicit
  failures with paired complete-manifest green coverage.
- Focused green evidence after implementation is 124 passed across the oracle
  and current-record validation modules. Direct CLI validation passes; source
  regeneration is byte-identical; all three official source hashes were
  independently recomputed. The whole-tree CI command merged in PR #193
  collects `tests/test_official_jvdata_oracle.py` automatically because it
  collects all `tests/test_*.py` outside only the explicit integration/E2E
  directories. The reconstructed database fixtures were already truthfully
  renamed and documented by PR #193, so no second relocation is needed here.
- A broader affected-contract run under isolated CPython 3.12.11 passed 209
  tests covering the oracle, all current/legacy physical record validation, and
  reconstructed database-row fixtures. The fail-closed CI self-check reports
  `TEST GATE PASS`; Ruff reports no findings on the three changed Python files;
  isolated fatal flake8 reports zero; Black is clean; JSON parsing and
  `git diff --check` pass. The host's unqualified `python3` is 3.10 and cannot
  import `tomllib`, so it was not treated as project evidence after that
  precondition failure; all accepted local evidence uses the required 3.12
  runtime.
- The first clean local candidate was
  `9374c8df1f19cd84a638a0a14f3613cb16a65502`. Exact-SHA focused evidence was
  209 passed, `TEST GATE PASS`, fatal flake8 zero, and a clean worktree. It was
  not pushed because the grouped critical review had not yet completed.
- Started a new Claude Code session
  `365b9699-b517-405f-b567-b6c87fd77266` with `--model fable --effort high` for
  a read-only critical review of that candidate. Fable was selected because a
  validator can create false release confidence if it fails open. The request
  stopped at the service session limit before any review content or source
  inspection ran; it is not review evidence and must be resumed in the same
  session after the next 01:10 JST reset before merge.
- While that external review was unavailable, Codex independently challenged
  the generic validator rather than waiting idle. A single grouped negative
  matrix proved 10 fail-open shapes red on the first candidate: empty manifests,
  non-string source identities, non-string field names, missing scalar/repeat
  decoders, missing direct/repeated nested targets, a root without `head`, and
  a root redirected to a non-root structure. The run was 10 failed and 16
  passed. The validator now rejects each shape directly, while the paired
  complete fixture and official manifest remain green; the broader affected
  selection is 219 passed with the CI self-check and fatal lint still green.
- A separate search found a `BameiEng VARCHAR(80)` declaration and tested the
  hypothesis that the 2006 UM change remained unfixed. It belongs to the
  distinct `HANSYOKU`/HN contract, whose current official English-name field is
  80 bytes. The `UMA`/UM standard table is correctly 60 bytes with the 1-byte
  flag and 19-byte reserve, so no UM schema change is warranted from that
  search result.
- Known findings remain release blockers rather than oracle exceptions: HY
  field/primary-key semantics, CK omitted repeats, six standard-schema storage
  routes, schema metadata integrity, obsolete routes, and strict fresh
  acquisition-to-SQLite/PostgreSQL evidence. No support statement, version,
  tag, or release lock changed in this iteration.
- Next safe action: run fatal lint, the fail-closed CI self-check, and the
  affected parser/fixture contracts; commit a clean candidate; obtain one
  grouped Fable critical review and GitHub review on that exact candidate; then
  fix any independently reproduced findings together before merge.
