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
- Branch: `fix/postgresql-import-statistics-20260827`
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
