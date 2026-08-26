# jrvltsql 2.0.0 final release worklog

## Scope and identity

- Started: 2026-08-27 (Asia/Tokyo)
- Objective: release `jrvltsql 2.0.0` only after the exact final candidate is proven in the development collector with the real provider, SQLite, PostgreSQL, sustained setup/backfill, and race-day realtime paths.
- Repository: `https://github.com/miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260827_jrvltsql_2_0_0_final`
- Branch: `release/2.0.0-final-20260827`
- Base and initial HEAD: `def93638466722e30a12f318baf7da5ec0da9ec2`
- Previous public release: `v2.0.0.dev6`
- Intended release: `v2.0.0` (no public `dev7` release is planned)
- Related completed repair: PR #248, merged as `def93638466722e30a12f318baf7da5ec0da9ec2`.

## Initial observed state

- The shared checkout `/home/keiba/jrvltsql` has unrelated, pre-existing changes in `src/fetcher/realtime.py` and `tests/test_time_series.py`; this iteration does not touch that checkout.
- The dedicated worktree started clean at the exact base SHA above.
- The running development JRA collector is healthy, but its installed `jltsql` package was observed as `2.0.0.dev5`; it therefore does not yet prove the merged `dev6` plus PR #248 code.
- The running wrapper checkout/image identifies itself separately as `2.0.0.dev7`; wrapper version and installed `jltsql` package version must not be conflated.
- Existing `v2.0.0.dev6` release notes explicitly leave sustained collection and live race-day realtime behavior unverified. Those claims remain open for the final release.
- 64-bit JRA-VAN SDK support remains outside the supported release claim unless separately proven. The final release may document the verified 32-bit path only.

## Minimum release gates

1. Exact version parity across source, lockfile, built wheel/sdist, installed metadata, and CLI.
2. Fresh wheel/sdist build, distribution-content gate, isolated install/init, and SQLite smoke.
3. Fresh PostgreSQL validation for schema creation, imports, rollback, and the PR #248 `MakeDate=00000000` migration boundary.
4. Exact candidate installed in the development collector without resetting the Wine prefix, hostname/MAC identity, registration, or service key.
5. Real JV-Link acquisition with auditable open/read/download/EOF/close evidence and durable SQLite/PostgreSQL reconciliation.
6. Sustained setup/backfill completion with checkpoint/restart evidence and no unreviewed parse/import failures.
7. Live race-day realtime validation for expected RT/TS tables, close obligations, stale-snapshot behavior, and transaction cleanliness.
8. Release notes, migration/rebuild guidance, rollback procedure, public API/version checks, and clean distribution contents.
9. One immutable candidate full SHA reviewed critically with Claude Code. Findings must be fixed or explicitly classified before merge.
10. PR checks, required local workflow-equivalent tests, unresolved review threads = 0, clean worktree, merge, then rebuild/tag/release/post-release smoke from the merge SHA.

## Cross-repository boundary

- `jrvltsql` source/release changes belong in this iteration and PR.
- Temporary candidate-image construction and read-only runtime inspection may be used for validation.
- Any tracked change to `jrvltsql-wine-runtime` or `kps-ingestion-runtime` requires a separate worktree, worklog, PR, and dependency ordering. No such change is assumed authorized merely by this release work.

## STOP conditions

- Provider acquisition, parse, import, transaction, or durability error that is not fully explained and repaired.
- Candidate/runtime version or full-SHA ambiguity.
- Destructive database operation without an exact target, verified backup/restore path, and an isolated destination where possible.
- Any action that would reset or mutate Wine machine identity, service registration, or credentials.
- Competition with an active collector/backfill job or loss of the provider lock.
- Live realtime evidence unavailable: the release must remain unreleased rather than converting “not measured” into a pass.
- Failed required test/check, unresolved review thread, dirty candidate worktree, or stale artifact built from a different SHA.

## Activity log

### 2026-08-27 — iteration start

- Read the release-readiness skill and release gate.
- Refreshed `origin/master` and tags; exact base remained `def93638466722e30a12f318baf7da5ec0da9ec2`.
- Created the dedicated clean worktree and branch above.
- Next safe action: inspect existing release/setup worklogs, repository version contracts, runtime build wiring, and the currently open GitHub/runtime state. No database or runtime mutation has been authorized at this point.

