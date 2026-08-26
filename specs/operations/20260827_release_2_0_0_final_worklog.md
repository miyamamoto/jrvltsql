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

### 2026-08-27 — final-candidate metadata and runtime boundary

- Initial worklog commit `57fe518ff52e496b8802494577a555e2d9205d47` was pushed before implementation so an interruption can resume from tracked evidence.
- GitHub state at implementation start: no open `jrvltsql` PR; public prereleases end at `v2.0.0.dev6`; stable remains `v1.6.10`.
- The current Wine runtime source/release is exact `jrvltsql-wine-runtime` merge/tag `806445a0fad7ac27669f7a0bef7d6cbb4f86d7f8` (`v2.0.0.dev7`). Its runtime repair intentionally pins upstream `jltsql 2.0.0.dev5`.
- The development JRA container is healthy on image `kps-jra-collector-dev:806445a0fad7ac27669f7a0bef7d6cbb4f86d7f8`; direct in-container source and installed metadata both report upstream `2.0.0.dev5`. Mounted Wine prefix and raw cache paths were inspected read-only. No provider/database operation or container change was made.
- Draft KIR PR #167 is the authoritative operational history for the five-year setup and dev7 runtime adoption. It records a complete eleven-spec five-year setup on dev5 and real PostgreSQL sokuho proof on wrapper dev7, but it does not prove merged `dev6` plus PR #248. The final candidate therefore still needs its own bounded real-provider and storage evidence.

#### Red-first version contract

- Existing exact-version assertions were changed first from `2.0.0.dev6` to `2.0.0` while production metadata was left unchanged.
- The first attempted run used system Python 3.10 and stopped at missing `tomllib`; it is an environment failure and is not counted as red evidence.
- The lock-backed worktree environment was then created with `uv` (Python 3.13.5). The two exact tests failed for the intended reason:
  - updater source fallback: `assert '2.0.0.dev6' == '2.0.0'`;
  - public project version: `assert '2.0.0.dev6' == '2.0.0'`.
- Source, project, lock and installed metadata were changed to exact `2.0.0`. The classifier is `Development Status :: 4 - Beta` while this remains an unpublished candidate; a stronger stability classifier must not be asserted before the operational gates.
- CHANGELOG and release notes now describe a final candidate, add the merged PR #248 `SE MakeDate=00000000`/`UMA_RACE VARCHAR(8)` migration boundary, retain the 32-bit-only scope, and explicitly block tag/publication on the remaining gates.
- Post-change exact contract: **3 passed**.
- Release-facing focused selection (`updater`, public setup, distribution contents, CLI): **101 passed, 10 subtests passed**.
- `scripts/validate_test_gate.py`, `uv lock --check`, `compileall`, workflow fatal Flake8 (`E9,F63,F7,F82`) and `git diff --check`: pass. The first Flake8 invocation only reported that Flake8 was not part of the project venv; the workflow-equivalent standalone `uvx flake8` run returned zero.

Next safe action: inspect the diff, commit/push the grouped final-candidate metadata, then build wheel/sdist from that immutable SHA. Do not install it into the development collector until artifact gates and a protected-identity candidate-image plan are recorded.

### 2026-08-27 — immutable candidate artifact and PostgreSQL gate

- Final-candidate metadata commit `1f9f4fc8c77bbe88d398b6263ffa05c64f66eead` was pushed. Its tracked worktree was clean at freeze.
- A fresh source tree was extracted from `git archive` of that exact commit into `/home/keiba/scratch/20260827_jrvltsql_2_0_0_final_artifacts/source`; no editable-worktree files were used for the build.
- The build produced exact metadata `Name: jltsql`, `Version: 2.0.0`, `Requires-Python: >=3.12`:
  - wheel `jltsql-2.0.0-py3-none-any.whl`, SHA-256 `7475450026d731fc338714506c25ea42ddea65d5b52fe12991405273336dee2b`;
  - sdist `jltsql-2.0.0.tar.gz`, SHA-256 `a74fa0a9512890e3fbf895e8c82001f5df781083acfd2dd8861820cbc4336a4d`.
- Distribution content scanning passed for both artifacts. The extracted-wheel isolated `init`, config/version, and SQLite table-creation smoke passed.
- Fresh disposable PostgreSQL 16 plus SQLite ran the exact candidate's SE MakeDate, official, schema-migration, and canonical selection: **129 passed**. This covers lossless `00000000`, real dates, malformed-date rejection, `UMA_RACE VARCHAR(8)`, and pre-DML rejection of legacy `DATE` storage.
- The dedicated PostgreSQL container `jltsql-final-1f9f4fc-pg16` was removed after the successful run; no volume or persistent database was retained.
- These artifacts are unpublished validation inputs only. They must not become release assets after any later candidate or squash-merge SHA change.

Next safe action: derive a temporary development image from exact runtime dev7 plus this exact wheel, and record an identity-preserving Compose plan before rotating only the JRA collector. Stop before mutation if the runtime build requires any service-key, registration, Wine-prefix, hostname/MAC, database, or non-JRA change.

### 2026-08-27 — candidate runtime image and pre-mutation admission

- An untracked, temporary derivation context was created at `/home/keiba/scratch/20260827_jrvltsql_final_runtime_image`. It uses exact wrapper base image `kps-jra-collector-dev:806445a0fad7ac27669f7a0bef7d6cbb4f86d7f8` (image ID `sha256:68db68a1c669d9e1ac7006dec59d5b95103413dd2f0e3ab0bc6384477b464828`) and force-reinstalls only the candidate wheel whose hash is recorded above.
- Built candidate image `kps-jra-collector-dev:jltsql-1f9f4fc8c77bbe88d398b6263ffa05c64f66eead`, image ID `sha256:94ebb91ecc110718fdff5c14c4a8d24d48735fd679f33fe2222f4c018d201a3a`. OCI labels bind candidate source `1f9f4fc8c77bbe88d398b6263ffa05c64f66eead`, wrapper base `806445a0fad7ac27669f7a0bef7d6cbb4f86d7f8`, and `2.0.0-final-candidate`.
- A network-disabled, read-only container smoke reports installed metadata and `src.__version__` both exactly `2.0.0`.
- A temporary Compose override changes only candidate image, expected upstream version, the three registration-write/reset controls, auto-install, and the already-running 86,400-second timeout. It does not contain credentials or identity values.
- Two plan defects were caught before runtime mutation:
  1. the first override draft inverted the running dialog controls; those keys were removed so the existing setup override continues to provide `AUTO_DISMISS_JVLINK_DIALOGS=1` and `JVLINK_AUTO_CLOSE_DIALOGS=0`;
  2. rendering from `.env` alone produced 7,200 seconds, while the actual admitted container uses 86,400; the candidate now pins the actual 86,400-second value.
- A canonical full-service projection (including one-way representations of environment data, never printed values) is byte-identical between the reconstructed current plan and candidate plan after removing only `build`, `image`, and `JRA_COLLECTOR_EXPECTED_VERSION`: SHA-256 `5b6e8c082abd36a358ac010e294fefacb30e1d0c15c3181caf284f75c5f1cd58` for both.
- Candidate safety values are exact: service-key write/reset/forced reset/auto-install `0`; entrypoint dismissal `1`; client auto-close `0`; timeout `86400`; expected upstream `2.0.0`.
- `scripts/check_nar_identity_guard.sh` passed. The host recovery lock is a regular file and was acquired nonblocking. A direct non-owner service-lock probe correctly failed permission and was not counted; the existing `ingestctl` measured-owner wrapper then validated the Wine-prefix owner and acquired/released `/tmp/jra_collector_service.lock` nonblocking.
- Both scheduler containers remain exited. No provider/fetch/realtime/daily-update process exists. Raw PostgreSQL reports zero non-idle client backends. The current JRA container remains healthy, full ID `1d9ba0f5fefade2d9e280d7172f172415f18dfba3ae13338438f83d0ef7c4832`, on the exact wrapper dev7 image ID above.
- Six non-JRA development services were frozen as a name/ID/image/status/health projection with SHA-256 `b093e2f68f751243e3edffd1ba8c705e79bb38fc7567001f19b085a2bbafdb89`. JRDB collector health is already red; it is a pre-existing external condition and must not be changed or hidden by this JRA-only rotation.

Next safe command after this evidence is pushed: recreate exactly `jra-collector` with base Compose + the existing setup-dialog override + the temporary final-candidate override, using `--no-deps --no-build --force-recreate --wait`. Immediately verify exact image/package/runtime versions, health, the same protected-identity projection, the same non-JRA projection, free locks, provider absence, scheduler state and PostgreSQL idle before any provider call.

### 2026-08-27 — exact candidate adopted without provider access

- Pre-mutation admission was committed/pushed as `4360b697fb42c48180923bfa1c837dd1977419a1`. Immediately mutable identity, host/service lock, provider absence, scheduler-stop, PostgreSQL-idle and current-container gates passed again.
- Compose force-recreated only `jra-collector` using base + the existing setup-dialog override + the temporary final-candidate override and `--no-deps --no-build --force-recreate --wait`. It reached healthy. No other service was requested from Compose.
- New JRA container full ID is `7dc00adad73b4b88d3c6f44b8340b2e524237b7c3cbb55b1b6f835f46be8b99b`; exact image ID is `sha256:94ebb91ecc110718fdff5c14c4a8d24d48735fd679f33fe2222f4c018d201a3a`.
- Actual container contract matches the candidate plan: hostname, protected MAC, every planned environment key, and the exact mount source/target/read-write set. A non-secret canonical actual identity digest is `71f2aaf6a12029e959ec34bfd93e22ebaa22249d6caebacc3f31366d744303d2`.
- Direct checks agree: installed distribution `2.0.0`, imported `src.__version__=2.0.0`, wrapper `/app/pyproject.toml=2.0.0.dev7`. `/health` is `{status=ok, kind=jra, runtime.version=2.0.0, runtime.runtime_version=2.0.0.dev7}`.
- The first health assertion looked for the two version values at the JSON top level and stopped on `None`; the actual API nests them under `runtime`. This was an inspection assertion only. The corrected nested-field assertion passed; no provider or database operation occurred between them.
- Recreation removed the ephemeral service lock. The existing measured-owner acquisition wrapper recreated/validated it and acquired/released it nonblocking; the host recovery lock is also available.
- Provider/fetch/realtime/daily-update process count remains zero; raw PostgreSQL has zero non-idle client backends; identity guard passes; startup bad-marker count is zero.
- The six-service non-JRA projection remains exactly `b093e2f68f751243e3edffd1ba8c705e79bb38fc7567001f19b085a2bbafdb89`. The pre-existing unhealthy JRDB collector and every other non-JRA ID/image/status remain untouched.

Next safe action: commit/push this no-provider adoption evidence and open a Draft release PR. Then use the existing bounded acquisition tooling in dry-run/read-only mode to admit one positive RACE/MING/results scope for the exact candidate. Record PostgreSQL baselines, provider/cache/process/lock state and disk first; do not start a provider call until the exact planned payload and stop gates are frozen.

### 2026-08-27 — Draft PR and bounded provider-call admission

- Opened Draft PR #249: <https://github.com/miyamamoto/jrvltsql/pull/249>. It explicitly blocks merge/tag/publication on provider, sustained/realtime, full-suite, artifact and independent-review gates.
- The existing `backfill_jra_durable_race.py` was selected rather than a new ad-hoc provider caller. A proposed 2026-08-24 start was rejected by its finalized-date contract before any HTTP/provider access because expected finalized date 2026-08-23 preceded the requested start.
- Accepted dry-run is one and only one collector payload:
  - mode `results_only`, from `20260822`, database `postgresql`;
  - specs exactly `RACE,MING,0B12,0B14,0B15,0B51`;
  - `skip_if_running=true`, source timeout 7,200 seconds;
  - expected durable date `20260823`;
  - one rung (`--step-days 5`), no second provider request.
- Pre-call PostgreSQL baseline:
  - `nl_ra=32,584`, `nl_se=391,158`, `nl_hr=17,535`; all max race date `20260823`;
  - target 2026-08-22/23 identities: `nl_ra=72/72 unique`, `nl_se=943/943 unique`, `nl_hr=72/72 unique`;
  - duplicate groups under each executable primary key: zero.
- Provider raw-cache baseline: 8,844 files, 6,428,646,328 bytes, latest mtime ns `1787407590094613760`. Root free space is 39,553,953,792 bytes.
- Candidate container log has 25 lines. Mounted `jltsql.log` baseline is 13,572,021 bytes with mtime epoch `1787736980`. PostgreSQL non-idle client count is zero.

Next safe action after this admission is pushed: repeat identity/health/exact-image/locks/provider-absence/schedulers/PostgreSQL-idle/disk gates, then run the exact one-rung command under the nonblocking host recovery lock. Retain a non-secret log outside the repository. Stop on nonzero status/return code, wrong payload, parser/import/schema/transaction error, no positive provider work, incomplete durable dates, lingering process/transaction, or identity/non-JRA drift. Do not rerun merely to recreate logs.

### 2026-08-27 — bounded provider cache replay and post-call audit

- The mutable gates were repeated and the one admitted `results_only` call was
  executed once under the nonblocking host recovery lock. The retained log is
  `/home/keiba/backups/rebuild-20260820/jra_final_candidate_1f9f4fc_20260822_23.log`,
  265 bytes, SHA-256
  `f3f407a5756b7e982c7d4b3c08e3f4004a2325a0cfaf3466b39af6c5dfd89ca5`.
  It reports one successful rung from `20260822` and durable maxima
  `nl_ra=nl_se=nl_hr=20260823`; the command exited zero.
- PostgreSQL remained exactly idempotent across the call: total rows are
  `nl_ra=32,584`, `nl_se=391,158`, `nl_hr=17,535`; the target retains
  `72/72`, `943/943`, and `72/72` rows/distinct official identities,
  respectively. Duplicate-key groups remain zero and post-call non-idle
  sessions are zero.
- The provider cache remained 8,844 files and 6,428,646,328 bytes with the
  same latest mtime. The mounted `jltsql.log` also had no byte or mtime delta.
  This is therefore an exact-candidate, real-provider-cache replay and durable
  PostgreSQL idempotency result; it is **not** evidence of a fresh provider
  download. Fresh acquisition remains an open release gate.
- This range contains no persisted `NL_SE.MakeDate=00000000` rows (the whole
  current PostgreSQL table also has zero). The exact captured-provider fixture
  exercised against fresh PostgreSQL remains the sentinel evidence; this live
  call must not be cited as sentinel coverage.
- Candidate identity, image/package/runtime versions, locks and provider
  process absence remained correct after the call.
- The earlier six-service comparison included mutable Docker health text. Its
  hash changed only because the same JRDB collector
  `0dbdc263a636063a47464c35bac1c3b18451b1739cc7e55530e228e123c120d4`
  naturally moved from `unhealthy` to `healthy`. Docker events in the call
  interval contain health-check `exec_*` events only, with no non-JRA
  create/start/stop/die/destroy event. A corrected projection excludes health
  and binds existing non-JRA container names to full container IDs, image IDs,
  creation/start timestamps, and lifecycle status; its current SHA-256 is
  `8d2ab4a382161f9aa8a03657b6c9e7af2400f1449a8d53b05025d9a68bbbb9d9`.
  The old health-inclusive hash is retained as historical evidence but is not
  an immutable identity gate.

Next safe action: commit/push this audit, then admit one bounded differential
`RACE` acquisition whose requested current/future window is absent from the
local cache. Use the existing `ingestctl` runtime-owner/lock path with a fresh
progress file and the already-completed same-window schema ledger. Freeze the
exact dry-run command, PostgreSQL/cache/disk baseline, identity and STOP gates
before `--apply`; do not count another unchanged-cache replay as fresh-download
evidence.
