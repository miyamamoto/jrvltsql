# CS/COURSE official key and complete-storage worklog

## 2026-08-17 — iteration start

- Objective: make the current `CS` course-information record preserve its full
  official identity and body in both native and standard storage, and reject
  legacy or unsafe schemas before any mutation.
- Minimal scope: `CSParser`, native `NL_CS`, standard `COURSE`, their mapping,
  migration/preflight behavior, focused SQLite/PostgreSQL/Dual tests, and the
  directly affected public data-support documentation. `DataKubun=0` erase
  coverage for the remaining record families is a separate later iteration.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree: `/home/keiba/scratch/20260817_jrvltsql_cs_course`.
- Branch: `agent/cs-course-key-20260817`.
- Base and initial HEAD: `17335604e0f951ae1cc39ebb447c6fb1b7b683be`,
  the squash merge of PR #204. `origin/master` was fetched and matched this
  full SHA before the worktree was created; the initial worktree was clean.
- Production/release context: source version `2.0.0.dev0`; latest published
  release remains v1.6.10. This iteration must not publish a release. It is the
  next dependency after the merged UM/UMA repair and before the WE/JC, SE,
  remaining physical-erase, final documentation/provider-E2E, and release
  iterations.
- Known audit hypotheses to verify independently against the pinned official
  4.8.0.2/4.9.0.1 workbook and SDK 5.0 manifest/source:
  1. Current CS key is `(JyoCD, Kyori, TrackCD, KaishuDate)`, while native
     `NL_CS` currently declares only the first three columns as its primary key.
  2. The standard `COURSE` table has no official primary key and omits the
     6,800-byte `CourseEx` payload, so successful imports can discard the body
     and collapse distinct renovation dates.
  3. Existing wrong-key/keyless or harmful-extra-UNIQUE schemas must fail
     before additive migration or DML on SQLite, PostgreSQL, and each Dual
     backend.
- Validation policy: derive red tests from the official key/layout first and
  actually run them against this base. Pair every rejection with current valid
  insert/update/readback behavior. Use exact full SHAs, real PostgreSQL 16, and
  a complete first/middle/last body readback rather than key-only success.
- Review policy: finish one implementation batch, freeze one clean candidate,
  then use two independent Codex critical reviewers because Claude Code remains
  unavailable. Aggregate all findings before any repair. No reviewer is to
  edit the shared candidate.
- Initial KPS status check was read-only. KPS itself is clean/current; the NAR
  repository is separately behind its origin and will not be touched until the
  validated jrvltsql release is complete.
- Next safe action: locate and pin the official CS rows/history/manifest,
  mechanically compare every parser span and both schemas/mappings, then add
  the smallest failing official-contract tests before production changes.
  STOP on official-source ambiguity, worktree drift, or any need to broaden
  into unrelated record families.

## 2026-08-17 — official oracle and red-first evidence

- Official workbook evidence is unambiguous. In both JV-Data 4.8.0.2 and
  4.9.0.1, format rows 1241-1251 define one 6,829-byte CS record. Rows
  1246-1249 mark `(JyoCD, Kyori, TrackCD, KaishuDate)` as the four-part key;
  row 1250 defines `CourseEx` at position 28 with width 6,800 bytes. The SDK
  5.0 manifest independently binds `JV_CS_COURSE` to the same spans and total
  length. The two current workbooks are identical for CS.
- History rows record CS introduction in Ver.3.2.0, an unspecified format typo
  correction in Ver.3.2.0.1, and a later special-note addition. No pinned old
  physical layout exists, so this iteration will not invent a legacy binary
  format. The current special note says status 2 may also require callers to
  refresh separately cached course diagrams; the row itself remains keyed and
  stored by the same contract.
- Community topic 237 records a 2023 provider incident where a CS file returned
  an impossible length instead of 6,829. Official support acknowledged bad
  course/training data, re-provided it, and the reporter then completed setup.
  The existing exact-length parser gate is retained and now has a CS-specific
  oversized regression; malformed provider data is rejected, not normalized.
- Code comparison confirmed the hypotheses: `NL_CS` omits `KaishuDate` from its
  primary key; standard `COURSE` has no primary key and no `CourseEx`; MCP
  metadata uses non-physical Japanese column names; neither parser nor caller
  dictionary entry points validate the key fields; and CS does not invoke the
  replacement-constraint catalog verifier.
- Red-first command on base `17335604e0f951ae1cc39ebb447c6fb1b7b683be`:
  `.venv/bin/python -m pytest -q tests/test_cs_official_contract.py --no-cov`
  (with an external basetemp). Result: `27 failed, 2 passed`. Concrete failures
  included native `len(rows)=1` instead of 2 for two renovation dates,
  standard `no such column: CourseEx`, all malformed key cases being accepted,
  all six legacy-schema paths mutating instead of raising, both Dual extra-
  UNIQUE targets being accepted, and a caller-built impossible renovation date
  being stored. This is the required observed red evidence before changing the
  validator or schema.
- A Python 3.13 worktree virtualenv was created with the locked `dev` extra;
  `.venv` is ignored and is not a tracked artifact. Next safe action: implement
  the one-record-family repair without touching remaining erase families, then
  rerun exactly this contract before broadening validation.

## 2026-08-17 — implementation and pre-review validation

- Implemented the bounded CS repair on the still-uncommitted branch based on
  base `17335604e0f951ae1cc39ebb447c6fb1b7b683be`:
  - `CSParser` now validates the real `MakeDate` and `KaishuDate`, the exact
    ASCII widths of `JyoCD` and `Kyori`, and `TrackCD` membership in the pinned
    official 2009 code table before returning a current record.
  - Native `NL_CS` and standard `COURSE` now use the official four-column key
    `(JyoCD, Kyori, TrackCD, KaishuDate)` and persist `CourseEx` with its full
    6,800-byte capacity. Physical metadata now derives from the native schema.
  - Both batch importers and the single-record entry point validate caller-built
    CS keys before schema or row mutation and verify the exact replacement key,
    non-deferrable PostgreSQL key, absence of harmful extra uniqueness, and body
    capacity before DML. Standard storage may add only a missing `CourseEx` when
    the existing key is already exact.
  - Public data-support documentation now states the key/body, rebuild/reimport
    boundary for old schemas, the separate diagram-refresh note for status 2,
    and the official 2023 malformed-provider-file incident without inventing a
    historical binary layout.
- Red-to-green focused result on SQLite: the original `27 failed, 2 passed`
  contract now reports `51 passed, 11 skipped`; the skips are only explicit
  PostgreSQL tests. The directly affected suite reports `236 passed, 15
  skipped`.
- Fresh disposable PostgreSQL 16 was started under the exact temporary name
  `jrvltsql-cs-review-pg16` and removed after the run. With the locked
  PostgreSQL extra, the complete CS contract reported `62 passed`. It covered
  native/standard storage, both batch importers and the single-record path,
  full first/middle/last body readback, two renovation dates plus exact-key
  update, extra unique constraints, deferrable primary keys, and physical
  metadata application. The exact-name container list was empty afterward.
- The first full suite exposed three false-green legacy parser tests: their
  supposed valid CS record left every official key field blank. Before the
  fixture repair the suite reported `3 failed, 2872 passed, 147 skipped, 22
  subtests passed`; each failure was the new parser rejecting blank `JyoCD`.
  The shared positive fixture now supplies the official four key fields. The
  three direct tests then passed, and the complete rerun reported `2875 passed,
  147 skipped, 22 subtests passed`.
- Strict MkDocs completed successfully. Fatal flake8, compilation,
  `uv lock --check`, the fail-closed workflow gate, and `git diff --check`
  pass. Project-wide Black/Ruff still report pre-existing style debt in the
  same generated/large production files; the new CS contract test itself is
  Black- and Ruff-clean.
- A fresh isolated source copy of the current candidate built both PEP 517
  artifacts successfully. The distribution-content gate passed, `specs/` was
  absent from both archives, and the extracted-wheel init/config/version/
  SQLite table-creation smoke passed for `jltsql-2.0.0.dev0`. Observed archive
  counts were 99 wheel members and 120 sdist members. All temporary source,
  artifact, site, basetemp, and PostgreSQL resources were removed or kept
  outside the repository as appropriate.
- Current state remains intentionally dirty with only this iteration's source,
  test, documentation, and tracked worklog changes. No release, GitHub write,
  provider-acquisition claim, or 64-bit support claim has been made.
- Next safe action: run the distribution-content/build checks from an isolated
  copy, freeze one clean candidate commit, and obtain two independent Codex
  critical reviews of that exact full SHA. Aggregate both verdicts before any
  repair. STOP on worktree drift, a packaging leak, or any correctness/data-
  integrity finding.

## 2026-08-17 — frozen review and one aggregated repair batch

- Froze clean candidate `94a0104440c40f413cba9cceeaa89b5f9dfd42c2`
  (parent `17335604e0f951ae1cc39ebb447c6fb1b7b683be`) and stopped edits while two
  independent Codex reviewers worked in parallel. Claude Code was unavailable,
  so this was the documented local-review fallback. One reviewer emphasized
  official workbook/SDK/history/code-table/docs/test-oracle truth; the other
  independently attacked migration, type, constraint, transaction, Dual, and
  actual-storage boundaries. Both started and ended on the same clean full SHA,
  used separate disposable PostgreSQL 16 resources, made no repository or
  GitHub changes, and returned `NEEDS_CHANGES`.
- Aggregated findings before editing, with duplicates merged:
  1. P1: official code table 2001 was not enforced; undefined or explicitly
     unused venue codes such as the reviewed negative controls were accepted.
  2. P1: caller-built status 1/2 records could omit `CourseEx`, supply a
     non-string or non-CP932 value, or exceed 6,800 CP932 bytes. SQLite stored
     the invalid values, and PostgreSQL `VARCHAR(6800)` checked characters
     rather than official physical bytes.
  3. P1: standard preflight allowed any missing `COURSE` column, and adding
     `CourseEx` to a nonempty table left existing rows permanently incomplete.
  4. P1: generic schema verification did not check integral `Kyori` storage.
     TEXT/BLOB keys could split one official distance into `'0900'` and `900`;
     one Dual probe reported in-sync despite divergent row counts.
  5. P2: the CS test named both workbooks but bound only the SDK plus a local
     hand-written tuple, and did not compare the complete code-table domains.
- Added the smallest grouped red contracts before production repair. On the
  frozen production code they reported `35 failed, 52 passed, 13 skipped`.
  The failures covered the complete venue/code oracle, every public importer
  entry point for an oversized caller body, missing/invalid body forms, both
  Dual targets with an invalid key type, native/standard wrong-key types,
  nonempty bodyless `COURSE`, and arbitrary missing non-body columns. This is
  the actual red-first evidence for the revised validators and gates.
- Implemented one repair batch:
  - added pinned shared code domains for official tables 2001 and 2009 and made
    CS reject undefined/unused venue and track codes;
  - required status 1/2 `CourseEx` to be a string, strict-CP932 encodable, and
    at most 6,800 encoded bytes before any schema/DML path, while preserving
    status 0 body opacity for the later physical-erase iteration;
  - added a dedicated integral `Kyori` verifier across every migration target;
  - restricted standard additive migration to an exact-key, empty `COURSE`
    whose only missing column is `CourseEx`; any other missing column or a
    nonempty bodyless table stops before ALTER/DML;
  - added a reviewed official fixture with exact workbook hashes/rows/layout,
    the shared 2001 venue oracle, and the complete 2009 track-code set; and
  - aligned public documentation with the narrow safe-additive boundary.
- Repair validation so far (the exact frozen `6fdc3d1e6595eb42aefae1db7ec944e3274d1651`
  candidate includes one additional status-0 validator test beyond the first
  recorded run):
  - SQLite CS contract: `88 passed, 20 skipped`;
  - fresh disposable PostgreSQL 16 CS contract: `108 passed`, including the
    caller-body byte-width, nonempty bodyless table, and wrong-key-type paths;
  - directly affected parser/schema/migration/metadata/mapping/importer suite:
    `565 passed, 24 skipped`.
  The repair PostgreSQL container was removed and its exact name no longer
  appears in `docker ps -a`.
- The affected suite exposed one additional false-green generic physical-shape
  test which supplied CS with no valid key/body. CS is now correctly classified
  among record types whose positive domain payload is exercised only by their
  dedicated official-contract test; the generic test still verifies short/long
  framing rejection.
- The final post-repair full suite reports `2912 passed, 156 skipped, 22
  subtests passed`; strict MkDocs also passes. The venue-code domain is now a
  single production constant shared by CS and WF, and the existing WF complete-
  domain contract passed after that mechanical centralization.
- Committed the material repair as exact production candidate
  `dd4eff0af33240a21eb7ce5340ea80923e8e91d1` (parent reviewed candidate
  `94a0104440c40f413cba9cceeaa89b5f9dfd42c2`) and confirmed a clean tree.
  Rebuilt wheel and sdist from `git archive` of that exact SHA. The content gate,
  extracted-wheel init/config/version/SQLite smoke, `specs/` exclusion, and the
  required shared code-domain module all passed. Exact artifact hashes were:
  wheel `a9fcf141cda56179168ef44a539b7dd49c094908ed7176b22d29bca30aa1a677`,
  sdist `0efc71eda21bbe981fec3796db920b3c2aa28379631153b1404b564fabcc4394`;
  member counts were 100 and 121 respectively. Temporary artifacts were removed.
- Next safe action: commit this evidence-only worklog update and request one
  bounded carry-forward pass from both original reviewers against the resulting
  exact clean SHA. The pass must verify closure of the four aggregated P1s and
  the official-oracle P2 without reopening unrelated record-family scope.

## 2026-08-17 — carry-forward status-0 storage boundary repair

- The first carry-forward reviewer found one adjacent P1 on exact clean
  `6fdc3d1e6595eb42aefae1db7ec944e3274d1651`. The parser and shared header
  validator correctly treated a status-0 `CourseEx` body as opaque, but every
  importer still passed that body to the database. A caller-built 6,801-character
  body therefore succeeded on SQLite and failed at PostgreSQL `VARCHAR(6800)`
  DML in all 12 native/standard × data/optimized/single × owned/caller cases.
  This is the observed red-first evidence for the storage-boundary repair; the
  reviewer used a fresh PostgreSQL 16 instance and stopped when the shared
  worktree later changed.
- The smallest repair normalizes `CourseEx` to `NULL` in the common post-header
  cleaning path only for CS status 0. It does not interpret the opaque bytes,
  does not extend the status domain, and does not claim to implement the later
  physical-erase iteration. New end-to-end SQLite and PostgreSQL matrices bind
  all 12 public entry-point/storage/transaction combinations and assert the
  same stored result on both backends.
- Post-repair verification:
  - SQLite CS contract: `100 passed, 32 skipped`;
  - fresh disposable PostgreSQL 16 CS contract: `132 passed`;
  - full local suite: `2924 passed, 168 skipped, 22 subtests passed`.
  The exact temporary PostgreSQL container was removed and the exact-name list
  was empty. The focused test file is Black- and Ruff-clean.
- Workflow-equivalent static checks also pass: `uv lock --check`, the
  fail-closed test-gate validator, fatal Flake8 (`0`), compileall, strict
  MkDocs, Black/Ruff for the changed contract, and `git diff --check`.
- Next safe action: commit this single adjacent repair and worklog correction,
  build and inspect artifacts from that exact immutable SHA, then obtain one
  final bounded carry-forward verdict from both original independent reviewers.
  STOP on worktree drift, any failed gate, a packaging/privacy leak, or a new
  correctness/data-integrity finding.
