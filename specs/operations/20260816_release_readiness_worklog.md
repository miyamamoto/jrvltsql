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
- PR #194 was opened from the first pushed candidate
  `798d4210e00edeb654417eaeaa5f81d6f399e144`. GitHub Actions run
  `31951212329` executed on that exact SHA and passed the fail-closed CI
  self-check, Linux deterministic tree (2,322 passed, 79 explicit environment
  skips, 14 slow deselections, and 15 passing subtests), distribution content,
  Windows launcher, and fatal lint gates. The optional tokenless coverage
  upload could not publish but its configured non-gating step and job
  completed successfully; it is not counted as test evidence. The performance
  job was a zero-step PR skip by workflow design.
- The first grouped GitHub review identified three actionable fail-open or
  incompleteness classes: inferring a repeat stride from only two evaluations,
  accepting a same-prefix root with an arbitrary field renamed `head`, and
  comparing history sets without constraining duplicate or extra entries.
  Two related review nits identified unbounded per-byte gap diagnostics and
  unreviewed constructor keyword arguments. These findings were aggregated
  before modifying the candidate.
- Before the grouped repair, the new negative matrix produced 10 failures and
  23 passes. Seven failures directly reproduced the review findings; three
  additional failures were expected-value drift after the synthetic positive
  fixture was corrected to contain the real common header contract. A separate
  complete-header semantic negative then produced 1 failure and 33 passes,
  demonstrating that width and name checks alone still admitted a false
  header. These are the required red results for this inspector change.
- The extractor now accepts repeat starts only when they are provably affine in
  the loop variable, rejects loop-dependent widths and constructor keyword
  arguments, and reports a contiguous gap as one bounded range. Manifest
  validation requires the exact 8-byte date and 11-byte common record-header
  field contracts, and every root must begin at byte 1 with that nested header.
  The history tests require exact cardinality in addition to exact identity
  sets, so duplicate or unreviewed entries cannot disappear under set
  comparison. Paired positive and negative coverage is 34 passed in the oracle
  module alone.
- Regeneration with the repaired extractor from the same official source
  produced 38 records, 94 structures, and 46,985 expanded leaves and was
  byte-for-byte identical to the tracked manifest; both files had SHA-256
  `437a21ea582315f807609dbee809c581518b31d6b48bddc96fd57b92c84e366a`.
  The affected CPython 3.12 selection passed 227 tests. The fail-closed CI
  self-check reports `TEST GATE PASS`; Ruff, Black, isolated fatal flake8, and
  `git diff --check` all pass. Pytest emitted best-effort temporary-directory
  cleanup warnings during the gate self-tests, but no test or gate failed and
  no repository artifact was created.
- Claude Code session `365b9699-b517-405f-b567-b6c87fd77266` remains the same
  Fable session for this iteration. Its prior request reached the account
  session limit before communication or inspection; therefore it is still not
  review evidence. Resume that session against the final pushed full SHA after
  the 01:10 JST reset and do not merge PR #194 before its grouped critical
  review is complete.
- A final Codex fail-open pass after the first review repair found that Python
  equality allowed Boolean `manifest_schema_version` to impersonate integer
  version 1, source SHA validation stringified a non-string 64-digit integer,
  and field decoder calls could silently ignore unreviewed keyword arguments.
  The three new tests produced the required red result of 3 failed and 34
  passed on candidate `3f3905666248776565bc8cb7fdbebafadcd009f7` before the
  implementation changed.
- Manifest validation now requires the schema version to be a non-Boolean
  integer and the source SHA-256 to be a lowercase 64-character string. The
  extractor rejects keywords on scalar/nested slice calls and repeat `range`
  calls, including nested slice calls, so a newly introduced argument cannot
  be silently discarded. The paired oracle module is 37 passed. Regeneration
  from the exact official source still expands 38 records, 94 structures, and
  46,985 leaves and remains byte-for-byte identical with SHA-256
  `437a21ea582315f807609dbee809c581518b31d6b48bddc96fd57b92c84e366a`.
- Known findings remain release blockers rather than oracle exceptions: HY
  field/primary-key semantics, CK omitted repeats, six standard-schema storage
  routes, schema metadata integrity, obsolete routes, and strict fresh
  acquisition-to-SQLite/PostgreSQL evidence. No support statement, version,
  tag, or release lock changed in this iteration.
- Next safe action: run fatal lint, the fail-closed CI self-check, and the
  affected parser/fixture contracts; commit a clean candidate; obtain one
  grouped Fable critical review and GitHub review on that exact candidate; then
  fix any independently reproduced findings together before merge.
- On 2026-08-17 the user explicitly authorized a Codex critical agent as the
  substitute review gate when the same Claude Code session remained blocked by
  its account limit. A read-only reviewer ran with `gpt-5.6-sol` at `xhigh`
  reasoning because this iteration changes an inspector whose failure mode is
  false release confidence. It reviewed exact full SHA
  `857533a3c1f29b899d2ce34fb076dc9c44afef09` and returned `NEEDS_CHANGES`.
  The independently reproduced grouped findings were: Boolean AST constants
  accepted as integer layout expressions; unreviewed `SetDataB` method shapes
  and non-`b` slice sources accepted; and official manifest/history fixtures
  structurally validated without binding every official fact and provenance
  field. The reviewer also independently confirmed the three official source
  hashes, all 38 current lengths, all 10 physical history changes, the PR-to-BR
  transition, the UM same-length semantic split, and distribution exclusion of
  `specs/`, the oracle fixtures, and the extraction script.
- Before changing the inspector implementation, the grouped regression matrix
  was run against the implementation at full SHA
  `857533a3c1f29b899d2ce34fb076dc9c44afef09`. It produced the required red
  result of 19 failed and 2 passed: four Boolean arithmetic paths, seven
  method/source-buffer paths, one same-shape manifest drift, and seven history
  content/provenance drifts failed to say no; the two already-covered
  nested/range keyword branches remained green.
- The extractor now excludes Boolean constants from both integer evaluators,
  requires exactly one synchronous direct `@classmethod SetDataB(cls, b)` with
  one unconditional constructor return, and requires every scalar or nested
  slice to read that reviewed byte parameter. The official manifest and history
  ledger are now bound in CI by canonical JSON SHA-256 in addition to the
  readable semantic assertions; strict ledger schema-version typing prevents
  `True` from impersonating version 1. All 21 grouped negative/paired cases are
  green, and the complete oracle plus current-record selection is 166 passed.
  Ruff, Black, and `git diff --check` pass.
- Regeneration after the grouped repair from the pinned official SDK source is
  still byte-for-byte identical to the tracked manifest: 38 records, 94
  structures, 46,985 expanded leaves, raw-file SHA-256
  `437a21ea582315f807609dbee809c581518b31d6b48bddc96fd57b92c84e366a`.
  The broader affected selection on CPython 3.12.11 is 251 passed, the
  repository fail-closed self-check reports `TEST GATE PASS`, and isolated
  fatal flake8 reports zero findings.
  A broader pre-existing packaging condition remains for release audit: the
  sdist ships some tests whose excluded script/fixture dependencies are absent.
  It is not a PR #194-specific oracle defect and was not mixed into this repair.
- Next safe action: run the affected broader selection and CI-equivalent local
  gates, commit and push one clean candidate, then perform the single final
  exact-SHA gate (checks, unresolved threads, review evidence, and clean
  worktree) before merging PR #194.

## Iteration: HY official semantics and storage contract (2026-08-17 JST)

- Objective and minimum scope: correct only the HY record's current official
  field semantics and its native plus standard-schema persistence contract.
  The required official byte layout is `KettoNum` at 12-21, `Bamei` at 22-57,
  and `Origin` at 58-121, with the horse registration number as the durable
  identity. CK expansion, unrelated standard routes, global metadata repair,
  and the strict fresh-acquisition release gate remain separate iterations.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260817_jrvltsql_hy_official`.
- Branch: `agent/hy-official-20260817`.
- Base / initial HEAD / `origin/master` full SHA:
  `3a0b108cfca22d9c2741aed96942178f4d475f90`.
- Dependency and production state: PR #194 merged as
  `3a0b108cfca22d9c2741aed96942178f4d475f90`; the release remains v1.6.10 and
  no version, tag, release lock, or support statement changes in this
  iteration. The dependency order remains HY, CK, remaining standard routes,
  metadata integrity, strict fresh acquisition/storage E2E, documentation and
  open-PR audit, then the jrvltsql release before downstream NAR and MCP work.
- Official evidence remains the pinned SDK 5.0.0 Python structure source with
  SHA-256
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`
  and the merged official manifest generated from it. Proprietary source and
  provider records are not copied into the repository.
- Red-first requirement: before changing parser/schema/import code, add the
  smallest paired contract that fails on the current implementation for all
  three semantic fields, the native primary key, the standard BAMEIORIGIN
  owner/schema, and SQLite/PostgreSQL-equivalent round-trip behavior. A passing
  parser-only test is insufficient. Do not infer a data migration or silently
  preserve the old misnamed columns without an explicit compatibility
  decision supported by schema-migration behavior.
- STOP conditions: do not merge if either storage mode drops HY, if duplicate
  horse identifiers do not deterministically upsert, if the schema migration
  can destroy existing rows, if official byte boundaries are not independently
  bound, or if any required test/review/thread/clean-worktree gate is missing.
- Next safe action: inspect the merged HY parser, native schema, standard
  BAMEIORIGIN schema/routing, importer mappings, migration behavior, and all HY
  tests; then write and execute the grouped red contract before implementation.

### HY implementation and pre-candidate verification (2026-08-17 JST)

- Read-only comparison against the pinned SDK 5.0.0 manifest confirmed the
  complete 123-byte `JV_HY_BAMEIORIGIN` layout: the 11-byte record header,
  `KettoNum` 12-21, `Bamei` 22-57, `Origin` 58-121, and `crlf` 122-123. The
  previous parser incorrectly exposed the registration number as `Bamei` and
  the two following official fields as anonymous `Field5`/`Field6`; the native
  schema consequently used the misnamed value as its primary key, while the
  standard BAMEIORIGIN schema had no durable identity and the reverse mapping
  selected an absent legacy table name.
- Red-first evidence before implementation: the grouped parser, schema,
  routing, migration-safety, SQLite round-trip/upsert, and PostgreSQL-equivalent
  contract produced `12 failed, 4 passed, 1 skipped`. This demonstrated that
  the new checks could reject the old implementation rather than only blessing
  a green path.
- Implemented the official parser names and boundaries; made `KettoNum` the
  native and BAMEIORIGIN primary key; added `Bamei` and `Origin` to the standard
  schema; selected canonical BAMEIORIGIN for HY standard storage while keeping
  MEANING as a lookup-only compatibility alias; and made legacy-only MEANING
  storage fail closed without changing existing rows. Existing obsolete native
  and keyless BAMEIORIGIN schemas are also rejected without destructive
  migration.
- SQLite verification after the implementation: `16 passed, 1 skipped` in
  `tests/test_hy_official_contract.py`, covering both `DataImporter` and
  `OptimizedDataImporter`, native and standard schema, deterministic upsert,
  and all fail-closed row-preservation paths.
- Real PostgreSQL verification used a disposable PostgreSQL 16 container bound
  only to `127.0.0.1:55440`, with a unique test schema. With
  `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1` and the PostgreSQL extra installed, the
  same contract completed `17 passed in 0.47s`; both importers stored and
  updated the official HY row in native NL_HY and standard BAMEIORIGIN. The
  fixture dropped its schema and the disposable container was stopped and
  auto-removed; a subsequent container-name lookup was empty. No shared KPS or
  production database was mutated.
- Broader affected verification on CPython 3.12 covered the HY contract,
  reconstructed binary fixtures, current-record validation, the official
  manifest oracle, mappings, indexes, all schemas, migrations, and both
  importers: `336 passed, 1 skipped in 2.77s`. The skip was the explicitly
  gated PostgreSQL case already executed separately above.
- Local mechanical gates passed: `scripts/validate_test_gate.py` (`TEST GATE
  PASS`), fatal flake8 E9/F63/F7/F82 (`0`), Ruff and Black for the new contract,
  and `git diff --check`.
- Implementation commit full SHA
  `02484d516376ed7469d744ee64c8cab484905612` was created from full base SHA
  `3a0b108cfca22d9c2741aed96942178f4d475f90`. Its exact-SHA verification passed:
  the affected selection produced `336 passed, 1 skipped in 2.70s`; the
  explicitly enabled disposable PostgreSQL path produced `17 passed in 0.53s`;
  the test gate, fatal flake8, new-test Ruff/Black, and committed-diff check all
  passed. The exact-SHA PostgreSQL container and test schema were removed.
- This worklog evidence update is intentionally documentation-only, so its own
  resulting commit cannot self-record its SHA. The final candidate full SHA and
  any GitHub checks/review evidence will be recorded in the PR, as required by
  the no-self-reference rule. Next safe action: commit this evidence-only
  update, push one PR, then run the single final gate on the resulting PR head
  and resolve all review threads before merge. STOP if the implementation diff
  changes, the final exact-SHA gate fails, or the worktree is not clean.

### PR #195 critical-review repair (2026-08-17 JST)

- PR #195 was opened at full candidate SHA
  `76b0c66f14fc3b856c676d8d6eeb6be9f24beb32`. Its initial Actions run
  `31957369681` completed successfully for the Linux full test and distribution
  job, fatal lint, and Windows launcher contract; the performance job was the
  expected zero-step PR skip. CodeRabbit was rate-limited and did not perform a
  review, so its neutral status is not counted as review evidence.
- A read-only independent Codex critical review used `gpt-5.6-sol` at `xhigh`
  on that exact clean candidate. This choice followed the user's authorized
  substitute for an unavailable external reviewer and was appropriate because
  status-dependent deletion and actual-schema verification are fail-open data
  integrity boundaries. The review returned `NEEDS_CHANGES` with two P1s and
  one documentation correction; it made no file or GitHub changes.
- Independent re-reading of both official JV-Data 4.8.0.2 and 4.9.0.1
  workbooks confirmed that HY is unchanged across those versions: its only
  statuses are `1` for the supplied value and `0` for deletion, and
  `KettoNum` is the deletion/storage key. The initial PR accepted arbitrary
  status values and treated `0` as a successful tombstone upsert. Both
  importers reproduced the defect in native NL_HY and standard BAMEIORIGIN.
- The same review constructed a partial legacy native table containing all
  current columns but `PRIMARY KEY (Bamei)`. Both importers reported complete
  success while allowing one horse to occupy multiple rows and one shared name
  to replace a different horse. The prior obsolete-table test exercised only
  `SchemaManager`, so its statement that all fail-closed paths were covered was
  premature. The schema module header also still named the obsolete key.
- Red-first review contract, run before the repair, produced `9 failed, 15
  passed, 1 skipped`. The failures separately proved rejection was absent for
  status `2`, all four SQLite native/standard plus importer deletion paths,
  both obsolete native importer paths, and both current-column/wrong-key native
  paths.
- Implemented strict HY status `0/1` validation; provider-order keyed deletion
  by `KettoNum` for NL_HY and BAMEIORIGIN through the shared erase path; cached
  actual-schema verification before every HY upsert or delete in both
  importers; and corrected the schema header key. Verification rejects missing
  columns or any primary key other than `KettoNum` with
  `SchemaMigrationError`, before mutation.
- Post-repair SQLite contract: `24 passed, 1 skipped in 0.78s`. Explicitly
  enabled disposable PostgreSQL 16 verification, including create, upsert, all
  four keyed-deletion paths, wrong-schema safety contracts, and cleanup:
  `25 passed in 1.11s`. The unique schema and loopback-only container were
  removed after the run.
- Broader affected verification covered the expanded record erase machinery
  and realtime cancellation distinction in addition to the prior parser,
  schema, mapping, migration, importer, reconstructed-fixture, and official
  oracle selection: `457 passed, 21 skipped, 12 subtests passed in 7.18s`.
  The skips are explicit live/PostgreSQL gates; the HY PostgreSQL gate was run
  separately above. The fail-closed CI test gate, fatal flake8, new-contract
  Ruff/Black, and `git diff --check` also passed.
- Current review repair remains uncommitted and therefore is not final evidence.
  Next safe action: commit/push one aggregated review repair, then perform one
  exact-SHA critical verification and GitHub final gate. STOP if any deletion
  leaves a tombstone, any malformed schema changes a row, or the PR head lacks
  clean exact-SHA evidence.

## Iteration: CK complete official layout and native storage (2026-08-17 JST)

- Objective and minimum scope: replace CK's representative/opaque extraction
  with a complete, gap-free current-layout parse and lossless native storage for
  every official leaf. Preserve provider order for `DataKubun=0/1/2`, reject
  the obsolete 6,864-byte layout, and use normalized child tables where one
  PostgreSQL row would exceed the database column limit. Canonical standard
  `CHOKYO_DETAIL` routing remains the immediately following independent
  standard-schema iteration; other record types and release changes are out of
  scope here.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260817_jrvltsql_ck_official`.
- Branch: `agent/ck-official-20260817`.
- Base / initial HEAD / `origin/master` full SHA:
  `9f2e2a8c11bae32a76e850c13aa0e112f75ef67a`.
- Dependency and production state: PR #195 merged as
  `9f2e2a8c11bae32a76e850c13aa0e112f75ef67a`; release remains v1.6.10. No
  version, tag, release lock, distribution, or support statement changes are
  authorized in this iteration.
- Official evidence: pinned SDK 5.0.0 structure source SHA-256
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`,
  official JV-Data 4.9.0.1 workbook SHA-256
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`,
  and official 4.8.0.2 workbook SHA-256
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`.
  The current record is 6,870 bytes and 1,729 expanded scalar leaves; the older
  official record is 6,864 bytes because the breeder code/name area changed.
- Initial observed gap: the current parser reads only the first of six ranks in
  each of 69 horse count blocks, only the first of four running-style counts,
  one opaque 1,220-byte block from each of two 2-block jockey/trainer sections,
  and one opaque 60-byte block from each owner/breeder 2-block section. This
  omits 988 official leaves and cannot be represented losslessly by the current
  single-table schema.
- Design constraint: PostgreSQL cannot hold the complete 1,729-leaf record in
  one row. The parser contract must expose all leaves deterministically, while
  native persistence uses an official-key parent plus bounded normalized child
  rows with explicit block/rank identity. No opaque packed field may be treated
  as equivalent to leaf-level storage.
- Red-first requirement: before implementation, add a compact oracle-driven
  contract that fills first/middle/last sentinels for every repeat family,
  asserts exact expanded leaf cardinality and no unread byte span, proves
  current code fails, and covers create/update/delete plus SQLite/PostgreSQL
  reconnect readback and malformed-schema no-mutation behavior.
- STOP conditions: do not merge if any official CK leaf is neither stored nor
  explicitly validated metadata, if old/current layouts can be confused, if
  child rows can outlive or mismatch their parent, if `DataKubun=0` leaves a
  tombstone, if a PostgreSQL column-limit assumption is untested, or if exact
  candidate SHA/review/thread/clean-worktree gates are incomplete.
- Next safe action: independently derive the complete recursive CK leaf and
  repeat model from the pinned manifest/workbooks, choose the smallest
  PostgreSQL-safe normalized schema, and write the grouped red contract before
  changing parser/importer/schema code.
- Red-first contract executed at unchanged base full SHA
  `9f2e2a8c11bae32a76e850c13aa0e112f75ef67a`:
  `uv run pytest -q tests/test_ck_official_contract.py
  --basetemp=/home/keiba/scratch/pytest_ck_red --no-cov` returned
  `9 failed, 1 passed`. The old parser accepted blank/3/9 `DataKubun`, exposed
  none of the required 70 horse, four professional, or four owner/breeder
  normalized rows, and the schema/importers had no child-table contract. Both
  importers therefore inserted the parent when every required child table was
  absent instead of failing before mutation. The previous 6,864-byte shape was
  already rejected. This is the required observed red for the new CK integrity
  check; implementation had not changed when it was captured.
- The independent design cross-check rejected the tentative wide professional
  rows because they would make validation and querying unnecessarily opaque.
  The final native representation preserves keyed `NL_CK` as a compatibility
  parent and adds two bounded children: `NL_CK_CHAKU` has 278 dimensioned rows
  with `Count1..Count6` (only the four-value running-style row has NULL 5/6),
  and `NL_CK_RUIKEI` has eight actor/period summary rows. The children store
  1,666 count leaves plus 32 summary leaves. The remaining 31 leaves are in the
  parent or, for CRLF, strictly validated before parse. This three-table shape
  stays below PostgreSQL's column limit and preserves all 1,729 official leaves.
- `CKStorageVersion` is importer-owned completion metadata. Additive migration
  leaves existing parent rows NULL; only a fully validated parent+278+8 write
  sets it to 1 at the end of the transaction. Existing partial rows cannot be
  reconstructed from the old representative columns because 988 leaves were
  never stored. They require current `SNPN` reimport, and complete consumers
  must verify marker 1 plus the two per-key child cardinalities.
- The current 6,870-byte parser strictly validates record type, physical length,
  CRLF, CP932 boundaries, DataKubun `0/1/2`, the seven official key fields, and
  every numeric payload leaf. A delete validates the envelope and key but does
  not invent a requirement that the official raw body be blank; it emits no
  child rows and deletes the exact parent key. The old 6,864-byte shape remains
  explicitly rejected rather than being guessed by length. Native owner and
  breeder compatibility column names retain their existing offset meanings;
  canonical SDK names belong to the separate standard-schema iteration.
- Both importers now use the same ordered prepare/apply contract. Before any
  mutation they require exact child columns/types/nullability, composite primary
  and parent keys, named CHECK bodies, and `ON DELETE CASCADE`; input rows must
  contain the exact ordered 278/8 dimensions and cannot forge the completion
  marker. Parent upsert with a NULL marker, exact child replacement, and the
  final marker update occur in one transaction. Standard-name CK storage fails
  explicitly until a canonical `CHOKYO_DETAIL` parent/child design is merged.
- A second validator red was observed after the initial implementation:
  `test_ck_child_schema_is_never_additively_repaired` failed because the generic
  `SchemaManager.create_table` silently added a missing `Count6` column and
  reported success while the required CHECK remained absent. The strict child
  tables are now excluded from additive repair. A paired create-all red also
  failed with `assert True is False` when `ck_chaku_domain` was replaced by
  `CHECK(TRUE)`; create-all now runs the dedicated coupled verifier and reports
  both children unavailable. Both red tests pass after the repair.
- The broader parser selection exposed three false-green generic CK tests whose
  positive fixture left every CK domain field blank. The strict parser correctly
  rejected it at `Year must contain only ASCII digits`. The fixture now contains
  a valid current-layout header/key and digits in every official numeric region;
  the three existing tests pass without weakening production validation.
- SQLite CK contract after the repairs: `36 passed, 6 skipped in 1.41s`; the six
  skips are the explicitly gated PostgreSQL cases. A disposable PostgreSQL 16
  container bound only to `127.0.0.1:55439` then ran the entire contract with
  the PostgreSQL extra: `42 passed in 2.41s`. This covered both importers,
  reconnect readback, ordered 1/0/2 replacement, final 278/8 row counts, exact
  deletion, direct database constraint enforcement, and malformed
  CHECK/FK/PK/nullability/column contracts preserving the legacy parent. The
  unique schemas were dropped by fixtures and the auto-remove container was
  stopped; a subsequent container-name lookup was empty.
- Broader affected verification covering the CK contract, current-record gate,
  every schema, migrations, comprehensive E2E schema creation, both importers,
  parser/factory compatibility, expanded storage, and table mappings completed
  `700 passed, 28 skipped in 5.00s`. The skips are explicit environment/live
  gates; CK's PostgreSQL path was executed separately above. `docs/data_support.md`
  now documents the current 6,870-byte three-table native contract, old-layout
  rejection, completion marker/reimport requirement, and explicit lack of CK
  standard-name storage rather than implying a partial table is complete.
- Strict MkDocs built the public documentation successfully. Wheel and sdist
  built from the working candidate, the content gate passed both artifacts,
  `schema_ck.py` was present, and tracked `specs/` plus official oracle inputs
  remained absent from distributions. The repository test-gate self-check,
  compileall, fatal Ruff `E9/F63/F7/F82`, full Ruff and Black for all new Python
  files, and `git diff --check` also pass. Existing all-rule Ruff debt in large
  legacy modules is unchanged and is not substituted for the fatal gate.
- The aggregated implementation was committed as full SHA
  `a0604c99e5379ecc18d5edc1032ce1a9cf9c72f6` on unchanged base
  `9f2e2a8c11bae32a76e850c13aa0e112f75ef67a`. Its clean exact-SHA full local
  suite completed `2428 passed, 92 skipped, 15 subtests passed in 52.97s`;
  exact disposable PostgreSQL CK verification completed `42 passed in 2.24s`.
  The test-gate self-check, fatal/new-file lint and formatting, compileall,
  strict docs, two-artifact distribution-content gate, and clean-tree check all
  passed on that SHA. The exact PostgreSQL schema/container was removed.
- An independent read-only Codex critical review used `gpt-5.6-sol` at `xhigh`
  on clean exact SHA `a0604c99e5379ecc18d5edc1032ce1a9cf9c72f6` and returned
  `NEEDS_CHANGES` with two P1 fail-open findings. It independently confirmed
  all CK offsets/repeats against the pinned manifest and found no other parser,
  storage, history, ordering, marker, or standard-mode blocker.
- P1 one: PostgreSQL constraint verification checked expected names and token
  substrings rather than constraint semantics. Keeping every token inside
  `CHECK (TRUE OR (...))` let both importers accept the malformed schema and
  replace the preserved parent. The added real PostgreSQL regression failed for
  both importers with `DID NOT RAISE SchemaMigrationError`; the review's
  independent fake-catalog probe also accepted a weak count-shape OR check.
  The repair now verifies constraint type and validated state, the exact ordered
  local/remote FK columns, referenced parent, and cascade action. It evaluates
  PostgreSQL's actual `pg_get_expr` CHECK expressions against the full 278 valid
  CK dimensions plus metric boundary, invalid entity/period/family cases, and
  paired count/summary NULL-shape positives and negatives. Tautological domain,
  weak count shape, NOT VALID, RESTRICT, and wrong FK order are all rejected.
- P1 two: the public single-table creation API excluded strict children from
  additive repair but still ran only the generic column/PK verifier. A complete
  SQLite child with `ck_chaku_domain CHECK(TRUE)` therefore returned `True`.
  The new regression failed exactly at `assert True is False`. A dedicated
  single-child verifier now validates the selected child and parent without
  requiring the sibling that may not yet have been created; create-all retains
  the full coupled verifier.
- Post-review repair verification is currently uncommitted: the three SQLite
  schema regressions pass; the complete disposable PostgreSQL 16 CK contract,
  including both importers and all new malformed constraints, completes
  `51 passed in 2.22s`; and the broader affected selection completes
  `701 passed, 36 skipped in 4.67s`. The container and all test schemas were
  removed. The stale E2E introduction was also corrected from 78/45 to the
  already asserted 80 total/47 native tables. Next safe action: finish
  mechanical checks, commit this one aggregated review repair, then run one
  clean exact-SHA final review/gate. STOP on any false-green schema result,
  failed test, container residue, source drift, or dirty final worktree.
- The first aggregated review repair was committed as full SHA
  `812bbd8105496075ff036782527becf5fef9332b`. Its clean exact-SHA full local
  suite completed `2429 passed, 100 skipped, 15 subtests passed in 52.35s`;
  the disposable PostgreSQL contract completed `51 passed in 3.26s`; and all
  exact mechanical/docs/distribution/clean gates passed. The container and
  schemas were removed.
- The continued `gpt-5.6-sol` `xhigh` review of exact SHA `812bbd8105496075ff036782527becf5fef9332b`
  returned `NEEDS_CHANGES` with one remaining P1 and one P2 before root changed
  the tree. The P1 demonstrated that finite truth samples alone were not an
  equivalence proof: canonical `ck_chaku_domain OR EntityKubun='EVIL'` passed
  verification and PostgreSQL stored the invalid child. The new real-PostgreSQL
  `extra-domain-value` regression preserves that red. The P2 showed an otherwise
  canonical `DEFERRABLE INITIALLY DEFERRED` FK was accepted, changing enforcement
  timing inside caller-owned transactions.
- The second aggregated repair does not grow the sample list around `EVIL`.
  Instead it parses the PostgreSQL-canonical expression into a complete
  structural signature of allowed equality/ANY/range/NULL atoms and exact
  AND/OR/NOT counts, rejects every unrecognized atom/operator, and then evaluates
  the expression across the complete equivalence classes induced by that fixed
  vocabulary: 2,400 entity/period/metric/bucket combinations, all 16 count-shape
  combinations, and all 384 actor/period/six-nullability summary combinations.
  Structure prevents new literals/predicates; the truth table prevents regrouping
  the same atoms into different semantics. The FK catalog gate now also requires
  non-deferrable, initially immediate, `MATCH SIMPLE`, and `ON UPDATE NO ACTION`
  in addition to the previously exact keys/parent/delete action/validation.
- Current second-review repair remains uncommitted. SQLite CK verification is
  `37 passed, 18 skipped`; disposable PostgreSQL 16 is `55 passed in 3.92s`,
  including the preserved EVIL and deferrable reds for both importers; broader
  affected verification is `701 passed, 40 skipped in 4.84s`. The container was
  removed. Next safe action: finish formatting/mechanical checks, commit the
  aggregated structural repair once, and run one final exact-SHA review/gate.
  STOP if structural signature or exhaustive equivalence validation can be
  bypassed, canonical PostgreSQL is rejected, or final evidence is not clean.
- The second aggregated repair was committed as full SHA
  `e7064e5416ed6a15b8062d4176f8ecf5dee39d9c`. Its clean exact-SHA full local
  suite completed `2429 passed, 104 skipped, 15 subtests passed in 50.01s`;
  disposable PostgreSQL 16 completed `55 passed in 4.02s`; and the test gate,
  fatal/new-file lint, compileall, strict MkDocs, wheel/sdist content gate,
  prohibited-public-document scan, retired-document absence, and clean-tree
  checks passed. The test container was removed.
- The continued independent `gpt-5.6-sol` `xhigh` Codex review returned
  `NEEDS_CHANGES` on clean exact SHA
  `e7064e5416ed6a15b8062d4176f8ecf5dee39d9c`. It confirmed the prior
  extra-domain and deferrability repairs, CK parser/storage/docs, and the
  recorded PostgreSQL/focused suites, then found two remaining enforcement
  gaps. First, the PostgreSQL `ANY(ARRAY[...])` signature lowercased quoted
  values and extracted literals from an otherwise unvalidated array body; the
  behavior cases also sampled only one member of each two-value class. A
  computed second member and a case-changed second member were therefore both
  accepted as equivalent while rejecting a valid official child row. Second,
  canonical FK catalog definitions were accepted when SQLite FK enforcement,
  PostgreSQL internal FK triggers, or PostgreSQL's session trigger mode had
  been disabled.
- Red-first evidence for this final aggregated repair was captured before
  implementation. With SQLite FK enforcement disabled, both importers failed
  the new expectation with `DID NOT RAISE SchemaMigrationError` (`2 failed`).
  In disposable PostgreSQL 16, computed/case-changed array members failed the
  expectation for both importers (`4 failed`), disabled FK triggers failed for
  both (`2 failed`), and non-enforcing session trigger mode failed for both
  (`2 failed`). In every case the old verifier allowed import instead of
  refusing before parent mutation.
- The repair preserves quoted-literal case, requires every PostgreSQL array
  member to match the complete canonical text-or-integer literal grammar, and
  evaluates every member of each official entity/period class including
  case-changed negative representatives. SQLite now requires
  `PRAGMA foreign_keys=1`. PostgreSQL now requires session trigger mode
  `origin` plus the exact four active internal FK triggers, split two on the
  parent and two on the child, in addition to the existing exact constraint
  metadata. The paired regressions now pass for both importers: SQLite
  `2 passed`; PostgreSQL malformed-contract matrix `24 passed`; complete CK
  contract `39 passed, 26 skipped` without PostgreSQL and `65 passed` with
  PostgreSQL 16. Next safe action: commit this single aggregated repair, remove
  the disposable database container, then run one clean exact-SHA full and
  PostgreSQL gate followed by one final independent review. STOP on any
  parser/signature ambiguity, inactive FK path, failed test, dirty tree, or
  review finding.
- The final enforcement repair was committed as full SHA
  `5c0d86c1b4097a5636ef3cd2960ff9891b2868f2`. On that clean exact SHA, the
  complete local suite passed `2431 passed, 112 skipped, 15 subtests passed in
  52.57s`; the complete disposable PostgreSQL 16 CK contract passed `65 passed
  in 5.09s`; and the test gate, fatal/new-file lint, compileall, `git diff
  --check`, strict MkDocs, wheel/sdist build and content gate, public-document
  scan, retired-document absence, container cleanup, and clean-tree checks all
  passed. The final independent `gpt-5.6-sol` `xhigh` Codex review of that exact
  SHA returned `GREEN` with no correctness, data-integrity, or release blocker.
- PR `#196` was opened from the same exact code SHA with the above evidence.
  GitHub Actions `test`, `lint`, and `windows-batch-syntax` passed; the optional
  performance job was intentionally skipped; and CodeRabbit completed. Copilot
  was requested once but explicitly reported that its review quota was
  exhausted, so it supplied no review evidence. This evidence closes the CK
  native-complete-storage iteration only. The repository release remains **not
  ready** until the remaining official-contract/storage iterations, final
  documentation and open-PR audit, actual fresh acquisition, and SQLite plus
  PostgreSQL persistence/readback gates are complete. No 64-bit SDK support
  claim is made without an installed-SDK end-to-end run.

### 2026-08-17 — deterministic SQLite test cleanup iteration

- Objective and minimum scope: repair one independently traced test-only
  SQLite connection leak which makes the complete release suite fail
  nondeterministically under Python 3.13 warning enforcement. Repository:
  `miyamamoto/jrvltsql`; dedicated worktree:
  `$WORKSPACE/20260817_jrvltsql_test_resource`; branch:
  `agent/test-resource-cleanup-20260817`; base and initial HEAD:
  `1b66f45629b9ede51fc2f4415e688784b2f55a2c`.
- The leak is independent of the in-progress BT standard-schema iteration and
  is therefore isolated in this smaller prerequisite PR. Claude Code first
  identified `tests/test_hr_schema_migration.py` as the likely allocation;
  Codex then reproduced it with tracemalloc. Running that test immediately
  before the HY official contract with `-W error::ResourceWarning` failed in
  HY while the allocation traceback pointed exactly to `_SqliteDB.__init__`
  line 21. The complete BT candidate suite likewise failed once after 2,463
  passes when the same connection was garbage-collected.
- The minimal repair gives the test wrapper an explicit `close` method and
  registers it immediately as a pytest finalizer. Next safe action: rerun the
  same red command, the focused migration test, and the complete suite on a
  clean committed full SHA; then open and merge this prerequisite before
  rebasing the BT work. STOP if any resource warning remains, migration behavior
  changes, or the finalizer does not execute after a test assertion failure.
- Clean code candidate `25c02ebcc233ba7e6d515f4d09649c487781d9d4`
  passed the exact red-first HR-to-HY sequence with the ResourceWarning promoted
  to an error (`25 passed, 1 skipped`) and the complete local suite (`2,431
  passed, 112 skipped, 15 subtests passed`). Fatal lint, compileall, the
  fail-closed test-gate validator, strict MkDocs, and `git diff --check` passed.
- An independent Codex read-only review of the same exact candidate returned
  GREEN with no P0/P1/P2 finding. It reproduced the parent leak, confirmed that
  explicit close removes it, and deliberately failed the test body to prove the
  registered finalizer runs exactly once even on failure. It found no warning
  filter, exception suppression, forced collection, production-code change, or
  migration behavior change. The final worklog-only commit will be recorded in
  PR metadata rather than adding a self-referential SHA commit.
### 2026-08-17 — standard-schema BT/HY alias storage iteration

- The preceding CK iteration was squash-merged through PR `#196` as master
  full SHA `1b66f45629b9ede51fc2f4415e688784b2f55a2c`. Its clean dedicated
  worktree and local branch were removed after confirming the merged PR and
  updated `origin/master`.
- Objective and minimum scope: make standard-schema imports for the already
  supported current BT and HY records resolve to their existing canonical
  owner tables (`KEITO` and `BAMEIORIGIN`) instead of resolving to undefined
  names and silently importing zero rows. Preserve the current official parser,
  native storage, cancellation, and migration contracts. CK, JG, WC, and WF
  canonical schema design remain separate iterations because they require new
  normalized owners or header/child layouts.
- Repository: `miyamamoto/jrvltsql`. Dedicated worktree:
  `$WORKSPACE/20260817_jrvltsql_standard_storage`. Branch:
  `agent/standard-storage-20260817`. Base and initial HEAD:
  `1b66f45629b9ede51fc2f4415e688784b2f55a2c`. The dependency order remains
  jrvltsql official-contract fixes and release first, then jrvltsql-nar, then
  jvlink-mcp-server.
- No implementation or test claim has been made yet. Next safe action: inspect
  the current reverse mapping, canonical schema keys/types, BT/HY parser
  outputs, cancellation behavior, and existing standard-storage tests; then add
  one grouped red-first contract proving both undefined-owner paths currently
  fail to store. STOP if either existing canonical table cannot represent the
  full official parent contract, if a semantic/key mismatch would require data
  migration beyond alias routing, or if another open PR already implements the
  same exact change.
- Initial inspection refined the scope before any implementation. HY is already
  complete on this base through PR `#195`: the reverse mapping selects
  `BAMEIORIGIN`, the legacy `MEANING` alias fails closed, both canonical/native
  schemas use `KettoNum`, and both importers have SQLite and PostgreSQL
  create/update/delete coverage. It must not be reimplemented from the older
  audit snapshot.
- BT hit the recorded STOP condition for alias-only routing. Current official BT
  is 6,889 bytes and contains `HansyokuNum`, `KeitoId`, `KeitoName`, and the
  6,800-byte `KeitoEx`; native `NL_BT` retains all fields and keys by
  `HansyokuNum`. Existing standard `KEITO` omits both `HansyokuNum` and
  `KeitoEx` and declares no primary key. Mapping `NL_BT` directly to that table
  would silently discard official data and cannot provide deterministic
  update/delete behavior. The minimum iteration is therefore one-record scope:
  define the complete current canonical `KEITO` schema and key, reject legacy
  partial tables before mutation, select `KEITO` as the reverse owner while
  retaining `BLOOD` as a legacy lookup alias, and prove both importers on actual
  storage. Next safe action: complete an independent official/history audit and
  add the grouped red contract at the unchanged base SHA. STOP on ambiguous
  deletion semantics, unsafe automatic migration of a populated partial table,
  or a conflicting open PR.
- Independent read-only Codex audit on unchanged production/test SHA
  `1b66f45629b9ede51fc2f4415e688784b2f55a2c` compared the 4.8.0.2 and
  4.9.0.1 workbooks plus SDK 5.0.0 manifest with the parser, native/standard
  schemas, mappings, both importers, and tests. It confirmed that the current
  6,889-byte parser and native `NL_BT` are exact, and that the existing history
  ledger test already rejects the old 6,887-byte layout. No dual-layout parser
  is required. The code changes in this iteration must therefore remain on the
  current layout only.
- The same audit independently reproduced five BT integrity defects: reverse
  mapping selects undefined `BLOOD` instead of official `KEITO`; `KEITO` omits
  `HansyokuNum`, `KeitoEx`, and its key; both importers store `DataKubun=0` as a
  tombstone instead of deleting by `HansyokuNum`; the parser accepts undefined
  status values; and the generic schema verifier accepts old/narrow bounded
  text columns such as `VARCHAR(8)` where current BT requires 10 bytes. In
  SQLite, standard import reported zero imported/one failed, while native
  `1 -> 2 -> 0` reported success but retained the zero-status row.
- Migration must be non-additive for an existing standard `KEITO`: missing
  official values cannot be reconstructed for old rows. Before any record
  mutation, keyless/partial/narrow `KEITO` and legacy-only `BLOOD` must fail
  closed and preserve both rows and schema. `BLOOD -> NL_BT` remains a public
  lookup alias, while the reverse owner becomes `KEITO`. HY was also rechecked:
  its official layout, key, canonical/legacy mapping, deletion, and SQLite
  contracts are already complete (`24 passed, 1 PostgreSQL opt-in skip`) and
  require no code change in this iteration. PostgreSQL evidence remains a
  release requirement rather than being inferred from the SQLite result.
- Next safe action: add one grouped BT official semantic/storage contract and
  run it against the unchanged implementation to capture red evidence for the
  mapping/schema/status/deletion/non-additive/capacity failures. Then implement
  the aggregate repair once. STOP if the capacity check cannot distinguish
  bounded text from unbounded text on both SQLite and PostgreSQL, a failed
  migration alters an existing table, or provider-order deletion is flattened.
- Red-first evidence was captured at the unchanged implementation/base SHA.
  `pytest -q -o addopts='' --basetemp=$WORKSPACE/pytest_bt_red
  tests/test_bt_official_contract.py` completed `19 failed, 6 passed, 1
  skipped`. The failures independently exposed all grouped defect classes:
  three undefined statuses did not raise; `KEITO` mapping/schema were absent;
  both standard importers could not store; both native importers retained a
  tombstone after deletion; incomplete deletes did not fail; partial `KEITO`
  was not rejected; narrow bounded text passed verification; and both
  importers wrote into legacy-only `BLOOD`. The six greens covered official
  status values, native round-trip, and exact/unbounded text acceptance. The
  skip was the intentionally opt-in PostgreSQL contract. This is the required
  pre-implementation negative evidence for the repaired checks.
- The aggregate implementation now selects canonical `KEITO`, preserves the
  `BLOOD` lookup alias while refusing legacy-only storage, completes the seven
  standard business fields and `HansyokuNum` key, enforces BT status 0/1/2,
  applies keyed physical deletion in provider order, and prevents additive
  mutation of an existing partial `KEITO`. The shared verifier now rejects a
  bounded CHAR/VARCHAR column narrower than the expected bounded contract while
  accepting exact, wider, and unbounded text.
- Pre-candidate verification is green: the grouped SQLite contract completed
  `25 passed, 1 PostgreSQL opt-in skip`; the broader parser/history/mapping/
  migration/importer/database selection completed `311 passed, 2 skipped`; and
  strict MkDocs completed. A disposable PostgreSQL 16 container then ran the
  complete BT contract `26 passed`, including both importers, native and
  standard 10-character leading-zero key storage, a 6,800-character
  explanation, physical deletion, and rejection of a populated narrow-key
  table without row loss. The dedicated container and schema were removed.
  Next safe action: commit one review candidate, run one independent Claude
  Fable and Codex critical review on its full SHA, aggregate any actionable
  findings, then execute final exact-SHA gates. STOP on any storage mutation
  before schema rejection, review blocker, or PostgreSQL/SQLite divergence.
- Candidate `af99773de6d5f1e3b7afd7fabf00d3b5b84932a2` was reviewed read-only by
  Claude Code `2.1.233` with `--model fable`, session
  `b1064e56-4d66-41af-9e99-130d59de7bf7`. Fable was selected because this
  iteration modifies a fail-closed schema validator and migration ordering.
  Claude returned GREEN after independently replaying the original 19 reds,
  SQLite/PostgreSQL BT storage and deletion, parser boundaries, all declared
  schemas, and full tests. It reported only the existing SQLite ResourceWarning
  flake and minor coverage/documentation notes.
- A separate fresh Codex critical review returned `NEEDS_CHANGES` on the same
  clean exact SHA with two independently reproduced P1 findings that Claude's
  table did not cover. First, the eager standard migration loop can ALTER and
  commit a safely additive column in one table before discovering an
  incompatible capacity, partial `KEITO`, or legacy-only `BLOOD`. Both
  importers, both auto-commit modes, and `import_single_record` can therefore
  fail while leaving unrelated schema mutated. Second, the capacity parser
  conflates truly unbounded text with bounded spellings it does not recognize;
  `NVARCHAR(8)`, `NCHAR(8)`, `CHAR VARYING(8)`, and `VARCHAR2(8)` all passed a
  `VARCHAR(10)` contract. The Codex findings are accepted despite Claude's
  GREEN because they have concrete false-green and mutation reproductions.
- The existing grouped regression was extended rather than adding one test per
  reviewer hypothesis. Red-first execution on the unchanged candidate completed
  `10 failed, 23 passed, 1 skipped`: four unrecognized bounded spellings did not
  raise; both importers in both auto-commit modes added `RACE.YoubiCD` before
  rejecting an existing narrow `RecordSpec`; and both importers altered that
  unrelated `RACE` before rejecting legacy-only `BLOOD`. Existing positive
  cases, original BT behavior, and exact/unbounded text remained green. The
  aggregate repair must distinguish bounded/unbounded declarations and perform
  a read-only compatibility/legacy preflight across all existing standard
  tables before the first additive ALTER.
- The aggregated repair now parses any declared lossless-text type with a
  numeric capacity (including national/variant spellings), preserves a distinct
  unknown-bounded result instead of treating it as unbounded, and adds an
  `allow_missing_columns` mode used only for read-only preflight. Both importers
  first validate every existing standard table, strict canonical table,
  coupled child, and known legacy/canonical pair; only after that entire
  phase succeeds can the existing additive migration loop execute.
- Post-repair grouped SQLite verification completed `33 passed, 1 PostgreSQL
  opt-in skip`; the affected parser/history/mapping/migration/importer/database
  selection completed `319 passed, 2 skipped`. A fresh disposable PostgreSQL
  16 run completed the expanded contract `34 passed`, now including catalog
  equality before/after mixed missing-column plus incompatible-capacity failure
  for DataImporter auto-commit and OptimizedDataImporter caller-owned
  transaction paths. The PostgreSQL schema and container were removed. Next
  safe action: run mechanical checks, commit this single aggregated review
  repair, then perform one exact-SHA final gate/review. STOP if any existing
  declared schema becomes a false positive or full-suite/resource handling is
  not clean enough for a repeatable release gate.
- After rebasing onto prerequisite PR `#197` merge SHA
  `755cf5a77d54e8a346ca6539b74841272fa5ae0b`, clean candidate
  `4022f82eeddbf1c968e09fc5ba94cd2c17ce5110` passed the complete local suite
  (`2,464 passed, 113 skipped, 15 subtests passed`) and disposable PostgreSQL
  16 BT contract (`34 passed`). Test-gate, fatal lint, compileall, strict
  MkDocs, and public-document checks also passed, but this candidate was not
  accepted because the final independent Codex review found one remaining P1.
- The remaining P1 was an explicit ordered-master preflight exclusion. An
  existing `RECORD` with its official primary key but a narrow `RecordSpec`
  and missing additive `Hondai` bypassed preflight; both importers and both
  commit modes added the missing column, and `import_single_record` could also
  store BT while retaining the incompatible existing type. This contradicted
  the documented all-existing-table preflight contract.
- Red-first evidence on unchanged `4022f82eeddbf1c968e09fc5ba94cd2c17ce5110`
  extended the existing grouped regression rather than adding a new test per
  path. The ordinary-table cases remained green while all six ordered-master
  paths failed their expected rejection (`6 failed, 6 passed, 30 deselected`):
  DataImporter and OptimizedDataImporter with both commit modes, plus both
  DataImporter single-record modes.
- The final aggregate repair now gives ordered masters a read-only existing
  type/capacity preflight with missing columns allowed. Legacy key mismatches
  remain non-blocking for unrelated records: additive migration already treats
  them as a no-op, while the dedicated writer owns the complete field/key and
  row-order checks when a matching record arrives.
  Next safe action: rerun the grouped, affected, PostgreSQL, full, packaging,
  and exact-SHA independent-review gates once. STOP on any ordered-master false
  positive, schema mutation before rejection, failed gate, or review finding.
- A first strict-key implementation was rejected before commit because four
  existing RC/TK contracts correctly require a legacy ordered-master key to
  remain non-blocking for unrelated imports. The retained preflight therefore
  allows only that key mismatch while still rejecting incompatible existing
  types and capacities; the additive migrator independently makes mismatched
  keys a no-op. This preserves lazy dedicated-writer rejection without startup
  mutation. The affected RC/YS/TK/migration/BT selection then passed `199
  passed, 10 skipped`; the complete SQLite BT contract passed `41 passed, 1
  skipped`; and disposable PostgreSQL 16 passed all `42` BT tests, including
  ordinary and ordered-master catalog equality after rejection for both
  importer paths. The disposable database was removed.
- Final clean code candidate `ffd5f3acbe4df171a01c64d6b1ed787c8abb4907`
  passed the complete local suite (`2,472 passed, 113 skipped, 15 subtests
  passed`) and a fresh disposable PostgreSQL 16 BT contract (`42 passed`).
  Test-gate validation, fatal/new-test lint, compileall, strict MkDocs,
  wheel/sdist build, distribution-content exclusion, public-document scan,
  retired-document absence, `git diff --check`, generated-artifact cleanup,
  container cleanup, and clean-tree checks all passed.
- The final independent Codex follow-up review of that exact SHA returned GREEN
  with no P0/P1/P2 finding. It independently confirmed the ordered-master
  rejection across both importers, both commit modes, single-record import,
  legacy-key-only no-op behavior, dedicated-writer rejection, and the combined
  legacy-key plus narrow-type case without schema or BT-row mutation. The final
  worklog-only descendant is recorded in PR metadata instead of creating a
  self-referential commit loop. Next safe action: push that clean descendant,
  open the BT PR, request the one-time GitHub auxiliary review, and merge only
  after all exact-head checks succeed and unresolved threads are zero.

### 2026-08-17 — remaining standard-storage audit and JG iteration

- PR `#198` squash-merged the BT canonical-storage iteration as master full SHA
  `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2`. Its GitHub test, lint,
  Windows launcher, and distribution jobs passed; the optional performance job
  was skipped. Copilot and CodeRabbit both reported quota limits and supplied no
  findings, while the exact code SHA retained the independent Claude and final
  Codex GREEN evidence recorded above. The dedicated worktree and branch were
  removed after the merge was confirmed.
- Objective and minimum scope: re-audit the three remaining undefined or
  suspicious standard owners for JG, WC, and WF against the current and
  immediately prior official contracts, then implement only the smallest
  independent record iteration that can preserve every official field, key,
  status, and delete/update semantic. Repository: `miyamamoto/jrvltsql`;
  dedicated worktree: `$WORKSPACE/20260817_jrvltsql_jg_standard`; branch:
  `agent/jg-standard-storage-20260817`; base and initial HEAD:
  `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2`.
- No implementation claim has been made. A fresh independent Codex audit is
  comparing JG/WC/WF official layouts, parser fields, native/canonical schemas,
  mapping ownership, importer behavior, cancellation semantics, tests, and
  docs. Next safe action: select one record only after the owner and complete
  storage contract are proven, then capture grouped red-first evidence on this
  unchanged base. STOP if the apparent standard table is semantically
  unrelated, cannot store all official payload, lacks a deterministic key, or
  another current PR already implements the same contract.
- The independent exact-base Codex audit returned `NEEDS_CHANGES` with no P0
  and selected JG as the smallest safe iteration. Official 4.8.0.2 and 4.9.0.1
  rows 1338-1354 and SDK 5.0.0 `JV_JG_JOGAIBA` agree on the unchanged 80-byte,
  17-leaf layout, `DataKubun=0/1`, and eight-part key: six race identifiers,
  `KettoNum`, and `ShutsubaTohyoJun`. The current native key omits the final
  component, causing two provider rows with reception order `001/002` to
  report two imports while retaining only `002`. Current deletion replaces
  the collapsed row with a `DataKubun=0` tombstone, undefined status `8` is
  accepted, and standard mode resolves to semantically incorrect
  `WEIGHT_CHANGE` although no matching standard schema exists. `JOGAIBA` is a
  project canonical owner inferred from the official SDK structure name; the
  provider specification does not publish SQL DDL or prescribe this table
  name. The legacy native parser field names remain a compatibility surface and
  must translate only at the standard boundary.
- The official online 4.9.0.1 document independently confirms JG under the
  `RACE` dataspec, and the provider-operated developer community confirms that
  blank or shared blood-registration numbers are not normal valid JG keys and
  describes the Thursday/Friday-Saturday publication stages ([topic 322](https://developer.jra-van.jp/t/topic/322)).
  A separate recent community report where only JG appeared under `RACE` was
  resolved by the caller using `JVSkip` ([topic 732](https://developer.jra-van.jp/t/topic/732)),
  so it does not justify changing JG dispatch.
- Red-first evidence was captured before any implementation change at code base
  `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2` (worklog-only descendant
  `78056df7c6584e4cc9b8a4d3ba88f35b03d77300`). The grouped JG contract
  completed `35 failed, 7 passed, 1 PostgreSQL opt-in skip`. The failures cover
  undefined status and malformed numeric fields, the missing eighth native
  key, absent `JOGAIBA` mapping/schema, silent revote collapse, tombstone
  deletion in both commit modes, absent writer revalidation, obsolete-key
  mutation, legacy-only owner handling, and single-record divergence. The
  seven greens cover exact offsets/CRLF/CP932 boundary rejection and the
  official delete key remaining readable. This is the required pre-change
  proof that the new parser/storage checks can say no.
- Implementation is delegated to Claude Code `2.1.233` with `--model fable`,
  session `cdcfb194-aec1-4045-8827-8d5753a45d71`. Fable is selected because
  this iteration changes a fail-closed schema validator and provider-order
  deletion across two importer implementations; a half-fixed branch could
  silently collapse or erase the wrong official key. The session receives the
  exact official contract and red evidence above and must remain resumable for
  any review repair in this same worktree.
- Claude Fable implemented the initial aggregate parser/schema/mapping/importer/
  documentation/history patch but reached its session limit before executing
  tests (`resets 08:40 Asia/Tokyo`). The result was therefore not accepted as
  verified. Codex inspected every changed path and extended the same grouped
  writer-negative test to direct invalid numeric and semantic code dictionaries.
  On the unmodified partial writer this produced the expected `4 failed` for
  DataImporter/OptimizedDataImporter across `NL_JG`/`JOGAIBA`: an invalid
  `SyussoKubun=8` was stored instead of rejected. The writer now validates the
  exact ASCII widths of the header/key plus both official code domains before
  any mutation, while allowing blank non-key body fields only for deletion.
- Current pre-candidate verification is green. The complete focused JG/oracle/
  dispatch selection completed `215 passed, 1 PostgreSQL opt-in skip`. A fresh
  disposable PostgreSQL 16 database then completed the whole JG contract `46
  passed`: both importers stored two same-race/same-horse reception orders as
  two rows in native and canonical schemas, exact deletion left the other row,
  and native/canonical seven-column legacy primary keys were rejected with
  catalog and sentinel rows unchanged for owned and caller transactions. The
  disposable database was removed. Next safe action: run the broader affected
  and complete suite, commit one candidate, then perform one exact-SHA Codex
  critical review and GitHub gate. STOP on any schema mutation before rejection,
  provider-order loss, official-history hash drift, or review blocker.
- The broader affected selection initially completed `749 passed, 5 skipped,
  3 failed`. All three failures were the same pre-existing generic positive
  fixture in `tests/test_parsers.py`: it constructed JG with blank official key
  fields even though current and historical JG require the fixed-width eight-
  part key. The test fixture, not the parser, was corrected to a valid official
  80-byte JG record; the identical selection then completed `752 passed, 5
  skipped`.
- A final Codex diff audit found one additional fail-open path before candidate
  freeze: a caller-built standard row could provide both native `Num` and
  canonical `ShutsubaTohyoJun` with different values. Validation read the native
  value while translation stored the canonical value. The existing grouped
  writer-negative test was extended first; both standard importers failed red
  (`2 failed, 2 passed`) because no exception was raised. The shared JG writer
  validator now rejects every conflicting native/canonical alias pair before
  mutation. The grouped focused/oracle/parser selection is green (`507 passed,
  1 PostgreSQL opt-in skip`) under Python 3.12.11, and the fail-closed workflow
  self-check prints `TEST GATE PASS`.
- Pre-candidate local gates are complete on the current worktree content. The
  CI-equivalent non-integration/non-E2E suite completed `2507 passed, 108
  skipped, 14 deselected, 15 subtests passed` under Python 3.12.11. The tracked
  SDK 5.0.0 oracle validates (`OFFICIAL ORACLE PASS`), `compileall` is clean,
  strict MkDocs builds, fatal `flake8` returns zero findings, and `git diff
  --check` is clean. Fresh wheel and sdist build successfully; the distribution
  content gate passes both artifacts and confirms repository `specs/` and the
  retired crawler audit pages remain outside the release archives. Setuptools
  emits only the existing future license-metadata deprecation warning. Next
  safe action: commit one clean candidate and run one independent exact-SHA
  Codex critical review plus an exact-SHA PostgreSQL replay. STOP if either
  finds a correctness/data-integrity blocker.
- Candidate `f16463cf7c076721e142bae7abdd5c68104c960b` was clean. Its
  code/test base was `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2`; its direct Git
  parent was the worklog-only `78056df7c6584e4cc9b8a4d3ba88f35b03d77300`. Its exact-SHA
  PostgreSQL 16 replay completed `46 passed`, and the disposable container was
  removed. Independent Codex review returned `NEEDS_CHANGES` (P0=0, P1=3,
  P2=2) after `526 passed, 1 skipped` focused tests, an independent PostgreSQL
  replay, and a Python 3.12 full suite of `2521 passed, 114 skipped, 15
  subtests passed`. The JG physical layout, official key, schema, deletion,
  history and documentation were confirmed; the blockers were all at the
  caller-built header boundary: missing/blank status defaulted through
  validation and stored NULL, conflicting record-type aliases could route JG
  while persisting another type, and accepted legacy-only record aliases were
  removed before storage. Coverage also proved that the newly added JyoCD
  rejectors had no tracked negative case. Canonical-only standard aliases were
  independently green but lacked a tracked positive regression.
- Review repair tests were added before production changes. On exact candidate
  `f16463cf7c076721e142bae7abdd5c68104c960b`, the grouped header/single/cleaner
  selection produced the expected `9 failed, 12 passed`: four batch paths did
  not reject conflicting record-type aliases, four single-record paths did not
  reject missing status, and the cleaner discarded a legacy-only record type.
  A temporary detached worktree at exact base
  `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2` separately failed both assertions
  for `JyoCD=@5`: the parser returned a row and the native writer stored it.
  That worktree was removed. The aggregate repair rejects record-type alias
  conflicts before dispatch, canonicalizes an accepted legacy record type,
  requires an explicit JG status, converts status-alias conflicts to the shared
  schema error, and adds parser/writer JyoCD negatives plus canonical-only
  standard-name greens. The immediate repaired selection is green (`21
  passed`). Next safe action: run affected/full/PostgreSQL gates once, amend the
  candidate, and request one exact-delta confirmation rather than restarting
  the complete review pipeline. STOP on any row mutation after a rejected
  header or any regression outside JG.
- The aggregated review repair is green. The affected importer/parser/oracle/
  realtime selection completed `928 passed, 28 skipped, 12 subtests passed`.
  Because record-type conflict resolution is shared by all importer entry
  points, the CI-equivalent full selection was rerun once and completed `2508
  passed, 108 skipped, 14 deselected, 15 subtests passed` under Python 3.12.11.
  A fresh PostgreSQL 16 container then completed the expanded JG contract `47
  passed`, including the reviewed header negatives and existing revote/delete/
  obsolete-schema paths; the container was removed. Next safe action: rerun the
  small static/oracle/document gate, amend the candidate, confirm exact SHA and
  clean state, then obtain one review-delta verdict. STOP on any failed gate or
  non-worklog drift.
- Independent repair-delta review is GREEN for exact code candidate
  `ab30322abc6532cb194feb9fcedfa0c722241b36` (P0=0, P1=0). Independent
  probes covered both importers, native/canonical schemas, single-record and
  both commit modes, all record-type alias precedence directions, status
  aliases, JyoCD rejection, and canonical-only standard fields; the focused
  repair selection completed `29 passed`. The reviewer confirmed the two topic
  links and ended on the same clean SHA. Its two non-blocking P2 observations
  are closed in a test/worklog-only follow-up: the canonical-only regression
  now queries and asserts all three physical alias columns, and this worklog
  distinguishes the logical code base from the worklog-only Git parent.
  Production code is unchanged by this final delta. The exact code candidate
  also passed `TEST GATE PASS`, `OFFICIAL ORACLE PASS`, fatal flake8, fresh
  wheel/sdist build, and the two-artifact distribution-content gate. Next safe
  action: commit this test/worklog-only child, obtain a carry-forward exact-SHA
  confirmation, then push and open the iteration PR. STOP if the delta contains
  anything outside these two files or the worktree is not clean.
- Final local/test head `fe44afdfccf3d6178b8957f1e66f95a1258079e6`
  received Codex GREEN carry-forward (P0/P1/P2=0): its parent is the reviewed
  GREEN code SHA `ab30322abc6532cb194feb9fcedfa0c722241b36`, and its only
  delta is the canonical-only physical-column assertion plus worklog accuracy.
  Exact-head focused tests completed `54 passed, 1 skipped`; fresh wheel/sdist
  and the two-artifact content gate also passed. The branch was pushed and PR
  [#199](https://github.com/miyamamoto/jrvltsql/pull/199) opened against exact
  base `a53eed6c24cbb4cbb8ebc0edc845ae67849b76b2` with the full red-first,
  PostgreSQL, full-suite, oracle, document and distribution evidence.
- GitHub Actions run `31973574748` executed successfully on that head: `test`,
  `windows-batch-syntax` (32-bit Python launcher contract), and `lint` all
  completed `success`; the branch-only performance job was intentionally
  skipped. Fatal lint passed; the workflow's pre-existing advisory type/style
  debt remains advisory. Copilot was requested exactly once and reported review
  quota exhaustion, so it was not re-requested. CodeRabbit completed with
  Minimal merge risk and no actionable blocker or inline review thread. Its two
  trivial suggestions were assessed without a SHA churn: the writer retains an
  independently pinned fixed-width table instead of trusting the parser's
  validation constant, and adding raw prefixes to regex strings containing no
  escapes would not change behavior or the configured lint gate. Thread-aware
  GraphQL reports zero unresolved threads; PR head matches local head and the
  worktree is clean. Next safe action: commit and push this worklog-only GitHub
  evidence, carry the reviewed production verdict forward, confirm the final
  Actions/head/thread gate once, then squash-merge PR #199. STOP on any
  non-worklog delta, failed executed job, actionable review, or head mismatch.
- PR [#199](https://github.com/miyamamoto/jrvltsql/pull/199) passed its final
  gate on exact head `9ab32b05a34a47c258e8b2c5bc18a0449897ab7d`.
  GitHub Actions run `31973856450` completed `test`, `lint`, and
  `windows-batch-syntax` successfully, with only the intentionally conditional
  `performance-test` skipped. Thread-aware GraphQL returned zero unresolved
  threads, the PR was `MERGEABLE` / `CLEAN`, and independent Codex
  carry-forward review returned P0/P1/P2=0. The iteration was squash-merged as
  `b4369f74d2ba236c8b33dbb1e45882ffa7c9aa0f`; the merged worktree and local
  branch were removed. This is an iteration merge, not a repository release.
- WC official-storage iteration started from current `origin/master` full SHA
  `b4369f74d2ba236c8b33dbb1e45882ffa7c9aa0f`. Repository:
  `miyamamoto/jrvltsql`; dedicated worktree:
  `/home/keiba/scratch/20260817_jrvltsql_wc_standard`; branch:
  `agent/wc-standard-storage-20260817`. Minimal scope is WC only: reconcile the
  current 105-byte official/SDK layout, the documentation-only 4.7.0.1
  availability/measured-distance clarification,
  native `NL_WC` and canonical `WOOD` ownership, status/delete semantics,
  migration fail-closed behavior, tests, public support documentation, and the
  official-history oracle. JG is already merged; WF remains a separate later
  iteration. Dependency order remains jrvltsql specification/storage fixes,
  final repository audit plus fresh provider acquisition/storage and release,
  then jrvltsql-nar alignment/release, then jvlink-mcp-server alignment/release.
  STOP if official sources do not establish the WC key/history, if the
  canonical owner cannot losslessly store all fields, if a legacy mismatch is
  mutated before rejection, or if a current PR already owns the same scope.
- Implementation is assigned to Claude Code `2.1.233` with `--model fable`,
  session `08bd10b4-8b1b-4e04-97df-2a55addde642`. Fable is selected because WC
  changes an official-key/schema validator and ordered delete behavior in both
  importers, where a partial repair can silently overwrite or erase the wrong
  training record. The session must first preserve grouped red-first evidence
  on this exact base, and any repair review in this worktree must resume the
  same session. Codex remains responsible for official-source reconciliation,
  test execution, independent critical review, GitHub gates, and merge.
- Claude Code session `08bd10b4-8b1b-4e04-97df-2a55addde642` stopped before
  reading or editing the candidate because its account session limit had been
  reached (`resets 08:40 Asia/Tokyo`). The CLI also printed local permission-
  rule syntax warnings, but no tool action or repository change occurred.
  Per the operator-approved fallback, Codex will implement the same aggregate
  red-first contract rather than waiting idle; Claude output is not counted as
  review or implementation evidence for this iteration. Current dirty state is
  still this worklog entry only. Next safe action: add the grouped WC contract,
  run it on unchanged production code, and record the red result before any
  source/schema change. STOP if the red probe does not expose the known key,
  deletion, standard-owner, or validator gaps.
- The grouped WC regression contract was added before any production/schema
  change and executed on exact code base
  `b4369f74d2ba236c8b33dbb1e45882ffa7c9aa0f` with
  `python3 -m pytest -q tests/test_wc_official_contract.py --no-cov
  --basetemp=/home/keiba/scratch/20260817_wc_red_pytest`. It produced the
  required red evidence: `42 failed, 1 passed, 1 PostgreSQL opt-in skip`.
  Failures independently exposed the generic parser raising or accepting
  corrupt fields, DATE/delimiter representation drift, the wrong native key,
  missing canonical `WOOD` schema, missing 4.7.0.1 documentation-history
  entry, collapse across training centres, Course-driven duplication, status-0
  tombstones, absent caller-dictionary validation, obsolete-schema mutation,
  and single-record divergence. The sole green was the official delete body
  remaining readable with its complete four-part key, proving the test fixture
  itself can express the provider contract. Next safe action: implement the
  bounded WC parser/storage/importer/history repair, then rerun this same
  contract. STOP if a new rejector makes the official all-nine sentinel or a
  nonblank status-0 body fail.
- The bounded WC repair is implemented without touching another record type's
  storage contract. `WCParser` now validates the exact 105-byte/type/CP932/CRLF
  envelope, explicit status 0/1, four fixed-width key values, current code
  domains, and all 19 status-1 timing fields while accepting documented
  zero-valued measurement fields and all-nine timing sentinels. Native `NL_WC`
  now uses the official four-part key;
  canonical `WOOD` stores the SDK field names losslessly. Both importers and
  the single-record path share a schema verifier and caller-dictionary
  validator, reject native/canonical alias conflicts, and apply status 0 as an
  exact provider-ordered delete. Existing wrong-key tables are rejected rather
  than migrated. The 4.7.0.1 ledger entry is explicitly documentation-only,
  and public support docs distinguish the project canonical table name from a
  provider-prescribed SQL DDL.
- Community evidence was rechecked rather than inferred from current data.
  JRA-VAN software support explicitly confirms the four recommended WC key
  fields and reports no observed same-key BabaAround variant in [topic
  99](https://developer.jra-van.jp/t/topic/99). Staff also confirms that all-nine
  lap/total values are provider-valid overflow measurement sentinels, not a
  parse error, in [topic 367](https://developer.jra-van.jp/t/topic/367). A 2023
  report of malformed course/hill/WC data was acknowledged and re-provided by
  support in [topic 237](https://developer.jra-van.jp/t/topic/237); this is the
  basis for adding semantic date/time rejection and reacquisition rather than
  accepting malformed values or changing the documented key. These links and
  the official workbook rows are independent sources for the test contract.
- The original grouped contract is now green: `43 passed, 1 PostgreSQL opt-in
  skip`. Its first affected selection exposed four old generic fixture
  failures: the shared length test and parser sample used blank WC keys and
  payload despite the current official domain. Those fixtures were corrected
  (or delegated to the dedicated official-contract positive) rather than
  weakening the parser; the affected parser/schema/importer/oracle selection
  then completed `763 passed, 1 skip`. A disposable PostgreSQL 16 container
  completed the expanded contract `44 passed`, covering both importers,
  native/canonical create/update/delete, the two-centre collision direction,
  Course non-key updates, and wrong-key schema rejection with catalog and rows
  unchanged. One initial PostgreSQL assertion failed only because unquoted
  identifiers are returned lowercase; the query now uses an explicit lowercase
  alias and the production path was unchanged. The disposable container was
  stopped and removed. Next safe action: inspect the aggregate diff, run the
  official/static/document gates and CI-equivalent full suite, then freeze one
  candidate for independent exact-SHA review. STOP on any non-WC behavior
  regression, ledger hash drift, PostgreSQL schema mutation, or stale container.
- Pre-candidate gates are complete under Python 3.12.11. The CI-equivalent
  suite completed `2553 passed, 109 skipped, 14 deselected, 15 subtests passed`
  with coverage. The same interpreter and a fresh PostgreSQL 16 container
  repeated the WC contract `44 passed`; the container was stopped and removed.
  `TEST GATE PASS`, `OFFICIAL ORACLE PASS`, full fatal flake8, Black/Ruff for
  the new WC parser/contract, compileall, `git diff --check`, and strict MkDocs
  all pass. Fresh
  sdist and wheel for package version 1.6.10 built successfully and the two-
  artifact distribution-content gate passed, including exclusion of tracked
  `specs/` from release artifacts. Setuptools emitted only its pre-existing
  future license-metadata deprecation. The pinned official workbook hashes were
  rechecked as `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`
  (4.9.0.1) and
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`
  (4.8.0.2). Changed scope is the WC parser, native/canonical schemas, shared
  importer plus optimized wiring, WC tests and corrected generic fixtures,
  official-history fixture/oracle, data-support docs, and this worklog. Next
  safe action: commit one candidate, confirm exact SHA/clean state, then request
  one independent Codex critical review of that immutable SHA. STOP on any
  worktree drift, failed exact-SHA replay, or data-integrity finding.
- Exact candidate `4be96d1f3ad1f88c47894c7337ee7dcd28f094d8` was clean and
  completed an exact-SHA no-coverage full replay (`2553 passed, 109 skipped,
  14 deselected, 15 subtests passed`) plus a fresh disposable PostgreSQL 16 WC
  contract (`44 passed`). Independent Codex critical review then returned
  `P0=0 / P1=2 / P2=2` and NEEDS_CHANGES. The two P1 findings were semantic
  fail-open acceptance of impossible Gregorian dates, invalid HHMM values such
  as the provider-confirmed bad `1160`, and over-width caller `reserved`
  values; and stale Japanese-name `NL_WC` metadata whose physical-column
  intersection was zero. The P2 findings were lack of a tracked-manifest bind
  for all WC fields/aliases and the earlier worklog's incorrect description of
  4.7.0.1 as a key change. No release or fresh-provider claim was made, and the
  review did not use a 64-bit SDK runtime. The Claude Fable session remains
  quota-blocked, so this aggregated repair continues under the operator-
  approved Codex fallback.
- Before changing production code, the grouped WC contract was extended on
  exact candidate `4be96d1f3ad1f88c47894c7337ee7dcd28f094d8` and produced the
  required red result: `14 failed, 36 passed, 1 PostgreSQL opt-in skip`.
  Failures covered parser calendar/HHMM semantics, both batch importers and
  native/canonical caller dictionaries, `DataImporter.import_single_record`,
  over-width/CP932-multibyte `reserved`, and exact metadata column/key drift.
  The paired valid leap-day/midnight case, all-nine timing payload, blank
  reserved field, and nonblank status-0 body remained green. The test now also
  binds all 30 logical parser fields and every WOOD alias to the pinned SDK
  5.0.0 manifest. The bounded repair shares Gregorian/HHMM/CP932-width helpers
  between parser and importer validation, keeps status-0 body opaque, and
  derives `NL_WC` metadata from the executable schema. The same contract is
  now green (`50 passed, 1 PostgreSQL opt-in skip`). Next safe action: run the
  affected SQLite/metadata/oracle selection, repeat the real PostgreSQL WC and
  metadata application paths, then freeze a repaired exact SHA for one
  aggregated delta review. STOP if any valid official zero/all-nine payload is
  rejected, metadata application fails, a wrong schema or row mutates, or a
  non-WC regression appears.
- The repaired affected selection completed `556 passed, 5 skipped`. A fresh
  disposable PostgreSQL 16 instance then completed the expanded WC contract
  `51 passed`, including both importers/native/canonical storage and actual
  `COMMENT ON COLUMN` metadata application; the container was stopped and
  removed. `TEST GATE PASS`, `OFFICIAL ORACLE PASS`, compileall, fatal flake8,
  focused Black/Ruff, strict MkDocs, and `git diff --check` also pass. Full-file
  Black/Ruff still report the repository's pre-existing formatting/typing debt
  in `importer.py` and `schema_metadata.py`; no unrelated mechanical rewrite
  was made. Next safe action: commit the repaired candidate, run one exact-SHA
  CI-equivalent full suite, and resume the same Codex reviewer for one
  aggregated delta review. STOP on a failed full test, post-commit drift, or a
  remaining correctness/data-integrity finding.
- Repaired candidate `56a86301a89cfe5382c1d5d4f167d0e744c79bb2` was clean and
  completed the exact Python 3.12 CI-equivalent full suite: `2560 passed, 109
  skipped, 14 deselected, 15 subtests passed` with coverage. Fresh wheel and
  sdist 1.6.10 built successfully and the two-artifact distribution-content
  gate passed, retaining the required exclusion of tracked `specs/` and oracle
  materials. The only build output was the existing future setuptools license-
  metadata deprecation. Open PR inspection still returned zero PRs.
- The resumed Codex delta review of exact `56a86301...` closed both prior P1s
  and the worklog correction, and found no new production correctness blocker,
  but returned `P0=0 / P1=0 / P2=2` NEEDS_CHANGES for test-oracle gaps. It
  independently demonstrated that swapping two equal-width production parser
  offsets escaped the manifest test, and noted that all tracked status-0 bodies
  were also valid status-1 bodies while official measurement-failure zero
  values lacked storage readback. Before repairing the oracle, a minimal
  monkeypatch regression on unchanged production produced the required red
  result: `1 failed, 50 passed, 1 PostgreSQL opt-in skip`. The repaired test now
  compares all 30 tuples from `WCParser()._fields`, after applying the
  production WOOD alias map, directly with the compact pinned SDK structure;
  the same injected offset drift must raise. Existing parameterized paths now
  use a physically decodable but status-1-invalid status-0 body, include a
  caller-built over-width body for exact delete, and read back first/middle/last
  official zero measurements as `0.0`. Focused SQLite is `51 passed, 1 skip`
  (`74 passed, 5 skipped` with metadata tests), and a fresh disposable
  PostgreSQL 16 run is `52 passed`; the container was removed. Test gate,
  official oracle, focused Black/Ruff, and `diff --check` pass. Next safe
  action: commit this test/worklog-only delta, confirm the production parent is
  unchanged, and request one final carry-forward review rather than restarting
  the full review loop. STOP on a non-test/non-worklog delta, false-green
  mutation probe, failed PostgreSQL path, or unresolved reviewer finding.
