# PostgreSQL provider-operation import statistics — 2026-08-27

## Purpose and minimal scope

The unpublished `2.0.0` final candidate completed a bounded real-provider DIFN
option-4 setup with 253,944 parsed records, zero failed records, and 253,529
reported imports. The durable PostgreSQL master state was correct, but 415
accepted same-primary-key provider revisions were collapsed by the PostgreSQL
multi-row upsert before the importer counted them. SQLite counts the accepted
input operations. This iteration fixes only that statistics/backend-parity
contract; it does not change parsing, validation, keys, final-row semantics,
transactions, collector identity, or release metadata.

## Repository and immutable starting state

- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260827_jrvltsql_import_stats`
- Branch: initially `fix/postgresql-import-statistics-20260827`; replacement
  branch `fix/postgresql-import-statistics-ci-retry-20260827`
- Base and initial HEAD: `def93638466722e30a12f318baf7da5ec0da9ec2`
- Base source: freshly fetched `origin/master`
- Related draft release PR: `#249` (`2.0.0` final; publication held)
- Current published prerelease: `v2.0.0.dev6`
- Target release after this repair is merged and revalidated: `v2.0.0`
- Initial worktree state: clean

The shared checkout `/home/keiba/jrvltsql` contains unrelated changes and is
out of scope. The KIR runtime checkout also contains unrelated local state and
must not be edited by this iteration.

## Observed evidence and cause

- Real provider DIFN option-4 setup accepted 253,944 parsed records and reported
  zero failures, but `records_imported=253529`.
- The discrepancy is concentrated in one successful 10,000-record PostgreSQL
  chunk: it reported 9,585 imports, exactly 415 fewer accepted operations.
- `PostgreSQLDatabase.insert_many()` deliberately keeps the last row for each
  repeated primary key so one `ON CONFLICT DO UPDATE` statement is valid.
- Generic importer statistics use that deduplicated physical-operation count
  except for a selective record-family allowlist. Therefore an unlisted DIFN
  family undercounts accepted provider operations; SQLite does not.
- Final durable data and transaction completion were correct. This is a
  statistics/observability defect, not record loss.

## Red-first contract

Add one compact regression using an existing generic DIFN master family and
two valid same-key provider revisions in one batch. It must prove:

1. both regular and optimized importers report two accepted operations;
2. durable storage contains one row with the last provider revision;
3. `records_failed` remains zero;
4. SQLite and PostgreSQL agree;
5. the test fails against the base behavior before implementation.

Do not create a broad record-family matrix. Reuse an existing official-contract
fixture and its PostgreSQL integration fixture where possible.

## Implementation boundary under review

On a successful generic batch, every converted input row was accepted; batch
failure already enters the existing per-record fallback (or propagates for a
caller-owned transaction) and counts individual successes/failures. The likely
minimal fix is therefore to count `len(converted_batch)` / `len(batch)` after a
successful generic batch rather than maintain a selective allowlist. Before
changing it, verify there is no success path where `insert_many` intentionally
returns fewer accepted input operations for a reason other than same-key
deduplication.

## Verification and merge gates

- Red proof against base, with the observed assertion recorded here and in the
  PR.
- Focused official-contract test on SQLite and disposable PostgreSQL 16.
- Existing importer/database focused tests affected by the shared path.
- Formatting/lint/compile and `git diff --check` proportional to the delta.
- Candidate full SHA recorded after push; unresolved review threads zero;
  clean worktree; PR merged before rebuilding draft release PR `#249`.

## STOP conditions

- Any durable-row or transaction semantic change beyond statistics.
- Any mismatch between the reproduced failure and the real DIFN evidence.
- Any unexpected shared-worktree drift in this dedicated worktree.
- Any PostgreSQL result that indicates actual record failure or loss rather
  than same-key compaction.

## Next safe action

Extend one existing DIFN official-contract test with a two-revision same-key
batch, run it unchanged against this base to capture the red result, then make
the smallest shared statistics correction in both importer implementations.

## Red proof on the base implementation

The compact BN regression was added without changing production code and run
against a fresh disposable PostgreSQL 16 instance plus SQLite:

```text
tests/test_bn_official_contract.py: 2 failed, 48 passed
PostgreSQL DataImporter:          assert 1 == 2
PostgreSQL OptimizedDataImporter: assert 1 == 2
SQLite regular/optimized controls: passed
```

Both PostgreSQL failures stored exactly one final row with the later body and
reported zero failures. This matches the real DIFN setup evidence: data and
provider order are correct, while accepted-operation statistics are
under-counted after same-key batch compaction.

## Implementation and focused green evidence

- Removed the record-family allowlist from the two generic batch writers.
- After a successful generic batch, `DataImporter` now counts
  `len(converted_batch)` and `OptimizedDataImporter` counts `len(batch)`.
- No error, fallback, commit, rollback, conversion, validation, or physical
  upsert branch changed. A failed auto-commit batch still retries and counts
  each individual result; a failed caller-owned batch still propagates.
- The regression uses two independently parsed, official-length 477-byte BN
  records with one key and distinct owner names. It verifies the later body is
  durable as one row while both accepted provider operations are counted.

Fresh disposable PostgreSQL 16 plus SQLite:

```text
tests/test_bn_official_contract.py: 50 passed
tests/test_importer.py
tests/test_importer_clean_record.py
tests/test_dual_handler_transactions.py
tests/test_postgresql.py
tests/test_cc_official_contract.py: 124 passed
```

The second selection retains the previously reviewed same-key CC PostgreSQL
contract and the generic batch-error/transaction coverage. No record failure,
row divergence, or pending transaction was observed.

Local workflow-equivalent static gates also pass: `uv lock --check`,
`scripts/validate_test_gate.py`, fatal flake8 (`E9,F63,F7,F82`, count 0),
Python 3.13 compileall, and `git diff --check`. The repository's advisory
Black/Ruff debt predates this delta and is not a workflow merge gate; no
unrelated formatting rewrite is included.

## Handoff / next safe action

Commit and push this bounded four-file delta, run the non-slow local suite on
that exact candidate SHA, open one PR, and record the candidate full SHA plus
the final test result in the PR evidence (avoiding a worklog self-reference
commit loop). Resolve all actionable review threads before merge. After merge,
refresh the draft `2.0.0` final branch from the new `master` and repeat only the
provider/import statistics and package/runtime gates affected by this fix.

## Aggregated review corrections

The first candidate was `108ee0e2267f81dc5faa16845503f9fddc1804a0`.
The non-slow local suite on that immutable candidate completed with:

```text
4796 passed, 507 skipped, 14 deselected, 21 subtests passed
```

Native review then identified one real adjacent failure boundary: the generic
batch counters were updated before an auto-commit. If that commit failed, the
existing per-record fallback retried the same provider operations and counted
the fallback outcome on top of the failed batch. A minimal regression injects
two commit failures so the batch commit fails, the first individual retry
fails, and the second retry succeeds durably. Before the correction it produced
the required red evidence:

```text
DataImporter:          records_imported=3, expected 1
OptimizedDataImporter: records_imported=4, expected 1
```

The correction moves successful batch counters, and the optimized individual
counter, after the applicable commit succeeds. The same regression is now
green for both importers (`2 passed`), with one durable later revision,
`records_imported=1`, `records_failed=1`, and `batches_processed=0`. This does
not change caller-owned transaction behavior because those paths do not commit
inside the importer.

The PostgreSQL fixture cleanup was also made unconditional with `finally` so a
schema cleanup failure cannot leak the test connection. A request to write the
eventual candidate SHA into its own tracked commit is intentionally not
followed: repository policy forbids self-reference commit loops. Exact final
SHA and immutable test evidence are instead recorded on the PR and in GitHub
check metadata.

## Next safe action after review correction

The complete BN contract and the bounded shared-path selection were run on
SQLite plus a fresh disposable PostgreSQL 16 instance after the correction:

```text
tests/test_bn_official_contract.py
tests/test_importer.py
tests/test_importer_clean_record.py
tests/test_dual_handler_transactions.py
tests/test_postgresql.py
tests/test_cc_official_contract.py: 176 passed
```

The disposable container was removed. `uv lock --check`, the repository test
gate, fatal flake8 (`E9,F63,F7,F82`, count 0), compileall, and `git diff
--check` also pass. Commit and push this one aggregated correction, run the
non-slow suite on its immutable SHA, record that evidence on the PR, and
resolve the review threads. Do not merge until required `lint` and `test`
checks have executed successfully and the worktree is clean.

## GitHub Actions delivery incident and replacement PR

PR `#250` received the initial Copilot and CodeRabbit reviews, and all three
review threads were answered and resolved. However, GitHub did not create a
single `Tests` workflow run for that PR after its initial open, a normal
synchronize push, close/reopen, or a content-identical empty trigger commit.
The branch-protection-required `test` and `lint` contexts therefore remained
missing rather than failed. Required checks are not bypassed.

The exact content-identical trigger candidate
`0f42556321f3a0ed13b5dd0001d12c551ee55005` was independently rerun and again
completed with `4798 passed, 513 skipped, 14 deselected, 21 subtests passed`.
To obtain a real opened-event check suite while retaining `#250` as the review
record, the iteration moves to the replacement branch above and a linked
replacement PR. `#250` must be closed with that reason, not merged. The
replacement PR must still execute the required `test` and `lint` checks before
merge.
