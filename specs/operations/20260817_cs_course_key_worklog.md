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
