# H1 status-9 empty-vote provider contract worklog — 2026-08-22

## Start state and objective

- Objective: close the real five-year JRA setup blocker in which an official
  `H1` status-9 record has an empty/no-vote body but the importer applies the
  live-row eleven-digit vote validator and stops the full RACE acquisition.
- Minimum scope: independently bind the official H1 status-9 body semantics,
  add one paired red-first regression for the real provider shape and a
  malformed live-row control, repair the shared parser/importer boundary, run
  the affected H1 entrypoint/transaction tests, review the exact candidate,
  and release only the next `2.0.0.dev` prerequisite needed by the development
  recovery. No database DDL, key, other record-family, production `2.0.0`,
  Wine identity, or KPS model/strategy change belongs here.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260822_jrvltsql_h1_status9_empty_vote`.
- Branch: `fix/h1-status9-empty-vote-20260822`.
- Base/start HEAD: `d4830042d326b89f26a761e580e5621452e4b86b`, freshly
  fetched `origin/master`; the repository uses `master`, not `main`.
- Related development release: `jltsql 2.0.0.dev3`, whose merge is the base
  above. Runtime merge/image remains
  `6ff5f861690b84faad25dfaa6c3a753d9bd0afb4` until a reviewed successor is
  released and pinned.
- No open `miyamamoto/jrvltsql` PR existed at start. The older primary checkout
  `/home/keiba/jrvltsql` is on a separate dirty Devin branch with two tracked
  modifications; it is user-owned and was not changed.

## Real fail-closed reproduction

- KIR draft PR #167 and its tracked worklog are the operational source of
  truth. Exactly one `ingestctl jra_setup` RACE option-4 call requested
  2021-08-20..2026-08-19 and ran on the exact dev3 runtime for about 1 hour 56
  minutes before exiting 1.
- The triggering parsed record is `RecordSpec=H1`, `DataKubun=9`,
  `MakeDate=20240826`, race date 2024-08-25, venue `04`, race `12`, bet type
  `Tansyo`, and `Hyo=''`. `validate_h1_record()` called
  `H1Parser.validate_current_fields()` and raised
  `SchemaMigrationError: H1 Hyo must be exactly 11 ASCII digits`.
- The dedicated success ledger stayed absent. The operation left no provider,
  recovery lock or PostgreSQL transaction alive; committed prior batches are
  retryable exact-key upserts. The development collector was restored to its
  normal healthy dev3 two-file posture and both collection schedulers remain
  stopped.
- Do not copy the full Rich traceback or raw cache into Git. It may disclose
  broad record bodies and is unnecessary; the non-secret exact header/body
  fields above are sufficient to reproduce the contract.

## Red-first and STOP contract

1. Read the existing H1 official oracle, parser/importer implementation and
   official-layout tests before deciding whether status 9 is body-opaque or
   has a defined no-vote representation. Do not infer a broad exception only
   from one row.
2. Extend an existing H1 contract test where possible. The pre-fix base must
   fail on the exact status-9 empty-vote positive. Keep a status-2/4/5 live-row
   empty/malformed vote negative green so the fix cannot disable validation
   generally.
3. Apply the smallest shared fix before database mutation. Raw parser,
   DataImporter batch/single and OptimizedDataImporter must agree; status 0
   erase opacity and other status domains must not regress.
4. Stop on an official-oracle contradiction, a test that is already green on
   the base, any transaction/stat/schema mutation before rejection, a broader
   record-family change, unresolved review finding, dirty worktree, or failed
   exact-head gate. Do not retry the development provider from an unmerged
   local candidate.

Next safe action: inspect the existing H1 official worklog/tests and pinned
oracle references, then add only the minimal status-9 positive/live negative
test. Run it on this exact base and record the actual red before implementation.

## Official/provider boundary and red-first evidence

- Pinned JV-Data Ver.4.9.0.1 「５．票数１」 defines H1 status `9` as
  race cancellation. Every per-combination `Hyo` field is 11 bytes with an
  initial value of spaces; the table describes spaces as unregistered and
  `ALL0` as pre-sale cancellation/no votes. The cancellation-operation note
  says H1/H6 status 9 is emitted only after vote data was previously provided.
  This supports a cancellation snapshot retaining a known combination while
  its vote value is the canonical parsed blank; it does not justify making the
  whole body opaque.
- The failed provider run's Rich traceback records the normalized row as H1,
  status 9, race `2024-08-25 04-03-06-12`, `BetType=Tansyo`, `Kumi` present,
  and `Hyo=''`. The encrypted/compressed provider JVD is not copied or decoded
  into Git; this normalized parser output plus the pinned official field
  definition is the bounded reproduction evidence.
- Added one paired regression,
  `test_h1_status_nine_accepts_only_the_provider_blank_vote`: status 9 with a
  physical eleven-space vote field must normalize to `Hyo=''` and pass;
  statuses 2/4/5 with that same row must fail, and `None` or non-canonical
  whitespace must still fail.
- Red run on unchanged production base `d4830042d326b89f26a761e580e5621452e4b86b`
  with Python 3.12.11:
  `pytest -q tests/test_h1_official_contract.py::test_h1_status_nine_accepts_only_the_provider_blank_vote`
  failed exactly at the positive assertion with
  `SchemaMigrationError: H1 Hyo must be exactly 11 ASCII digits` (`1 failed`).

Next safe action: allow only the canonical parsed empty `Hyo` when
`DataKubun=9`, then run the new paired test and the existing H1 focused suite.

## Implementation and local green evidence

- `H1Parser.validate_current_fields()` now exempts only `status == "9"` with
  the parser-canonical `Hyo == ""` from the eleven-digit vote check. It still
  validates the race key, counts, sale/refund fields, combination, popularity,
  and totals. Status 0 remains key-only; statuses 2/4/5 and `None`/whitespace
  remain fail-closed.
- The paired regression exercises the physical eleven-space field through
  `H1Parser`, the shared importer validator, and a real SQLite `DataImporter`
  write/readback. The native numeric column stores this no-vote value as SQL
  `NULL` while preserving `DataKubun=9`, `Kumi=01`, and blank `Ninki`.
- Added the same focused PostgreSQL readback using the existing optional
  fixture. A dedicated disposable `postgres:16-alpine` container was used and
  removed after the run; no development database was mutated.
- Current working-diff verification on Python 3.12.11:
  - paired regression: `1 passed`;
  - H1 SQLite focused suite: `159 passed, 13 skipped`;
  - H1 plus adjacent expanded/realtime/layout selection:
    `164 passed, 15 skipped, 140 deselected`;
  - H1 PostgreSQL 16 focused suite: `169 passed, 4 skipped`;
  - workflow-equivalent fatal flake8 selection on the changed Python files:
    `0` findings;
  - `mkdocs build --strict`: success; the existing unlisted
    `docs/record_contracts.md` informational message remains non-fatal;
  - `git diff --check`: success.
- All test caches, coverage HTML, bytecode, documentation output, and the
  disposable PostgreSQL container created by this iteration were removed.
  The development collector remains the unchanged healthy dev3 runtime;
  schedulers remain stopped and no provider retry has been attempted from the
  unmerged candidate.

Next safe action: commit and push this four-file repair, update PR #240 with
the red/green evidence, then perform one exact-head review/check/thread gate.
