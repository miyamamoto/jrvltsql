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

### 2026-08-27 — fresh differential acquisition admission

- The existing merged `ingestctl` implementation at KIR checkout SHA
  `c03cc88c6d682c6eb0f48df8cef89e0420e11dfc` was inspected; the checkout is
  three commits behind `origin/main`, but those three commits do not change
  `scripts/ingestctl.py` or its focused test. Its only tracked local change is
  unrelated `scripts/run_jrdb_sync_loop.py`; the admitted command does not use
  that file.
- The candidate scope is `RACE`, option 1, provider start `20260824`, client
  filter end `20260830`, PostgreSQL destination. The five-year recovery window
  and schema evidence remain `2021-08-20..2026-08-19`; the existing schema
  ledger has `jra_schema=completed` for exactly that window.
- New progress path
  `/home/keiba/backups/rebuild-20260820/ingestctl_progress_jra_cache_final_candidate_20260824_30.json`
  is absent. The dry run returned `jra_cache=manual`/`nothing to run in a dry
  run`, as designed for collector-owned acquisition, and made no provider or
  database call. It also states that no optional outer image-equivalence
  service was named; stage-local candidate image/version/identity gates below
  are the binding evidence.
- Exact apply command after this record is pushed:

  ```text
  python3 scripts/ingestctl.py rebuild --years 5 --today 2026-08-20
    --stage jra_cache --apply
    --progress-file /home/keiba/backups/rebuild-20260820/ingestctl_progress_jra_cache_final_candidate_20260824_30.json
    --compose-file /home/keiba/kps-ingestion-dev-runtime/docker-compose.ingestion.yml
    --sources-file /home/keiba/kps-ingestion-dev-runtime/config/collector_sources.json
    --env-file /home/keiba/kps-ingestion-dev-runtime/.env
    --jra-container kps_ingestion_dev_jra_collector
    --jra-schema-completion-file /home/keiba/backups/rebuild-20260820/ingestctl_progress_jra_schema_v2.json
    --jra-spec RACE --jra-from 2026-08-24 --jra-to 2026-08-30
  ```

- Candidate runtime remains exact container
  `7dc00adad73b4b88d3c6f44b8340b2e524237b7c3cbb55b1b6f835f46be8b99b`,
  image `sha256:94ebb91ecc110718fdff5c14c4a8d24d48735fd679f33fe2222f4c018d201a3a`,
  installed/source `2.0.0`, wrapper `2.0.0.dev7`, healthy. Identity guard,
  host recovery lock and measured-owner service-lock probe pass; both kick
  schedulers are exited; no provider process or non-idle PostgreSQL client is
  present.
- Pre-call PostgreSQL totals/maxima remain `NL_RA=32,584/20260823`,
  `NL_SE=391,158/20260823`, `NL_HR=17,535/20260823`; all three have zero rows
  for 2026-08-24..30. Cache baseline is 8,844 files, 6,428,646,328 bytes,
  latest mtime ns `1787407590094613767`; free space is 39,539,838,976 bytes.
  Mounted `jltsql.log` is 13,572,021 bytes at mtime epoch `1787736980`.

STOP on nonzero stage/collector result, missing or wrong progress completion,
provider/transport/parser/import/schema/transaction error, zero cache delta,
no positive future PostgreSQL rows when the provider reports records, lingering
provider process/transaction/lock, candidate identity or image/version drift,
or any non-JRA container lifecycle mutation. Retain the complete non-secret
command output outside the repository and do not retry merely to obtain a
different result.

### 2026-08-27 — real RACE differential read and two-backend reconciliation

- The exact admitted `ingestctl` command ran once and exited zero. Its progress
  binds `jra_cache=completed` to `RACE`, option 1,
  `20260824..20260830`. Retained command output is 4,196 bytes at
  `/home/keiba/backups/rebuild-20260820/ingestctl_jra_cache_final_candidate_20260824_30.log`,
  SHA-256 `ddb901969fae07eff7956b38f1dc16d030be937e516d40a6e34e6eb1172bb1d4`.
- Candidate runtime reported **1,665 physical records fetched, 408,388 parsed,
  408,388 imported, 0 failed, 641 batches**. The log delta contains exactly one
  JVOpen/stream-open, one provider EOF (`Read complete - no more data`), one
  successful stream close, one fetch completion and one import completion;
  error-level entries are zero. Open diagnostics were `read_count=23` and
  `download_count=0`.
- Application raw cache changed from 8,844 files / 6,428,646,328 bytes to
  8,846 files / 6,446,407,186 bytes. Three paths changed after the baseline:
  two framed binary files and the RACE index. The two binaries contain exactly
  the 1,665 physical records above, aggregated by record ID as
  `H1=72,H6=72,HR=72,O1..O6=72 each,RA=72,SE=943,WF=2`.
- The requested future dates have no RA/SE/HR rows. The new binaries are actual
  race dates 2026-08-22/23 delivered as differential corrections/reprovision;
  this explains why the provider start can be 2026-08-24 while client-filtered
  race identities remain the preceding meeting. No future-card claim is made.
- PostgreSQL retained the exact official-key result for those two days. A fresh
  SQLite database built only from the two new framed binaries through the exact
  candidate parser and importer produced the same per-table cardinalities:
  `NL_RA=72, NL_SE=943, NL_HR=72, NL_H1=53,431, NL_H6=150,726,
  NL_O1=3,095, NL_O2=6,050, NL_O3=6,050, NL_O4=12,100,
  NL_O5=25,121, NL_O6=150,726, NL_WF=2`.
- The SQLite replay independently measured 1,665 raw, 408,388 parsed/imported,
  zero parse/import failures, 641 batches, `PRAGMA integrity_check=ok`, no
  pending transaction before close or after reopen. The retained disposable DB
  is 50,511,872 bytes, SHA-256
  `034550a9b773a279c66d3d2ab5b3532af50c5b1f531c81fcf1d7661334cd2548`,
  at `/home/keiba/scratch/20260827_jrvltsql_final_sqlite/provider_fresh.db`.
- PostgreSQL duplicate groups for executable RA/SE/HR primary keys remain zero;
  no non-idle transaction remains. Candidate identity/version/health, both
  locks, scheduler stop and provider-process absence remain correct.

Classification: this is strong real JV-Link open/read/EOF/close evidence and
byte-identical logical reconciliation across PostgreSQL and fresh SQLite. It is
not an SDK-network-download result because `download_count=0`; the provider's
own JVD cache already held the 23 files. One different, bounded current
dataspec may be admitted to seek `download_count>0`; do not repeat RACE or
delete provider-managed JVD files to manufacture a download.

### 2026-08-27 — bounded DIFN network-download admission

- One different scope is admitted: `DIFN`, option 1, provider/client window
  `20260820..20260827`. `DIFN` is an official option-1 accumulated master
  dataspec covering UM/KS/CH/BR/BN/HN/SK/RC. It was not part of either final
  candidate call above.
- Fresh progress path
  `/home/keiba/backups/rebuild-20260820/ingestctl_progress_jra_cache_final_candidate_difn_20260820_27.json`
  is absent. The same dry-run path returned the expected collector-owned
  `manual` result without provider/database work; the same exact five-year
  `jra_schema=completed` ledger is required by apply.
- Exact apply command is identical to the prior `ingestctl` command except for
  the new progress path and `--jra-spec DIFN --jra-from 2026-08-20
  --jra-to 2026-08-27`. It will run once under the same host recovery lock and
  measured-owner service-lock bootstrap.
- Pre-call cache is 8,846 files / 6,446,407,186 bytes, latest mtime ns
  `1787759010634671073`; `jltsql.log` baseline is 13,582,563 bytes, mtime epoch
  `1787759111`; free space is 39,564,820,480 bytes.
- PostgreSQL representative master baselines are
  `NL_UM=214,048, NL_KS=1,565, NL_CH=1,476, NL_BR=10,764,
  NL_BN=8,740, NL_HN=11,185, NL_SK=39,690, NL_RC=2,145`; non-idle sessions are
  zero. Candidate image/version/identity, health, scheduler stop, both locks and
  provider-process absence must pass immediately before apply.

STOP on all previous provider/storage/identity conditions. In addition, this
scope passes the remaining network-fresh gate only if the exact open diagnostic
reports `download_count>0`, the stream reaches EOF and successful close, no
parse/import failure occurs, and raw-cache/DB readback is coherent. A zero
download remains useful real-provider evidence but does not close this gate;
provider-managed JVD files must not be removed or altered.

### 2026-08-27 — network-fresh DIFN acquisition

- The admitted DIFN command ran once and exited zero. The immutable progress
  scope is `DIFN`, option 1, `20260820..20260827`, status completed. Retained
  output is 4,209 bytes at
  `/home/keiba/backups/rebuild-20260820/ingestctl_jra_cache_final_candidate_difn_20260820_27.log`,
  SHA-256 `b3d733a437cce5d1a63763f91f04b2ce179011b9f24d00026ab5f439dd8f7616`.
- Exact open diagnostics are **download_count=8, read_count=14**. The log delta
  contains one open/stream-open, provider EOF, successful stream close, fetch
  completion and import completion, with zero error-level entries. The result
  is **3,881 fetched / 3,881 parsed / 3,881 imported / 0 failed / 10 batches**.
- PostgreSQL durable master counts changed exactly from the recorded baseline:
  `NL_UM 214,048 -> 214,140`, `NL_BN 8,740 -> 8,741`,
  `NL_RC 2,145 -> 2,147`; `NL_KS/NL_CH/NL_BR/NL_HN/NL_SK` retained their
  prior cardinalities. This is positive downloaded provider data, not a
  no-data/open-only result. PostgreSQL is idle after completion.
- Application raw-cache file count, bytes and latest mtime did not change.
  This is the documented fail-safe behavior for undated DIFN master records:
  `_extract_record_date` has no Year+MonthDay/ChokyoDate key, so the stream is
  imported but its partial date-keyed app-cache append is not committed or
  marked complete. CHANGELOG and release notes already state that undated
  master rows suppress completeness and roll back partial append. No
  provider-managed JVD file was altered to obtain this result.
- Candidate identity/image/version/health, scheduler stop, provider-process
  cleanup, both locks and non-JRA lifecycle state remain correct.

The network-fresh acquisition gate is now closed: the exact candidate performed
positive JVOpen download/status wait, read, EOF, close and durable PostgreSQL
import. Together with the preceding RACE two-backend replay, this proves real
provider transport plus PostgreSQL/SQLite parser-storage equivalence without
conflating an undated master stream with a replayable date-keyed app cache.

### 2026-08-27 — bounded setup/resume admission

- Candidate-specific setup uses `DIFN`, option 4, `20260820..20260827`. RACE
  is intentionally not selected because its v3 cache is already complete for
  the current span and would bypass JVOpen; DIFN's documented undated-master
  behavior guarantees the option-4 provider path is exercised without
  deleting or invalidating cache.
- Fresh progress path
  `/home/keiba/backups/rebuild-20260820/ingestctl_progress_jra_setup_final_candidate_difn_20260820_27.json`
  is absent. Dry-run returned the expected collector-owned manual result and
  performed no provider/database action.
- Exact apply command uses the same arguments and five-year schema completion
  as the network-fresh call, with `--stage jra_setup`, the fresh setup progress
  path, `--jra-spec DIFN --jra-from 2026-08-20 --jra-to 2026-08-27`. It is
  executed once under the host recovery lock. After completion, the exact same
  apply command is executed once more with the same progress path and must
  return `skipped/already completed` without a new log/cache/DB/provider delta.
- Baselines: cache 8,846 files / 6,446,407,186 bytes / latest mtime ns
  `1787759010634671073`; `jltsql.log` 13,589,951 bytes at epoch `1787759452`;
  free space 39,562,440,704 bytes. Master counts are
  `UM=214,140, KS=1,565, CH=1,476, BR=10,764, BN=8,741,
  HN=11,185, SK=39,690, RC=2,147`; PostgreSQL is idle.
- Candidate container/image/health and both scheduler stop gates remain exact.
  Identity, process and both-lock gates must pass immediately before apply.

STOP on any previous provider/storage/identity condition, unexpected setup
dialog/timeout, setup-source error, missing completion, or a resume call that
re-enters the provider instead of skipping. The earlier dev5 full five-year
eleven-spec setup remains background sustained-volume evidence; this bounded
candidate call proves the exact final code path and does not replace or
overclaim that older full-range run.

### 2026-08-27 — bounded setup completion, resume, and statistics finding

- DIFN option 4 completed under both locks with no dialog intervention:
  `read_count=78`, `download_count=0`, provider EOF and one successful close,
  zero error-level log entries. CLI totals are **253,944 fetched/parsed,
  253,529 imported, 0 failed, 275 batches**. The retained 4,322-byte log is
  `/home/keiba/backups/rebuild-20260820/ingestctl_jra_setup_final_candidate_difn_20260820_27.log`,
  SHA-256 `6cd89a12ae541fccd65034f2a2fb465547043efc4be5adb86940a9d8ee7a0549`.
- Option-4 setup committed 26 bounded chunks. Import totals were 10,000 for
  each of the first 24 chunks, 9,585 for chunk 25, and 3,944 for the final
  chunk. The parsed/imported difference is therefore exactly 415 accepted
  input operations inside one PostgreSQL chunk, not a parser failure or an
  interrupted final tail.
- Durable master cardinalities are unchanged from the immediately preceding
  DIFN differential result, as expected for a current full replacement
  snapshot. PostgreSQL briefly exposed one non-idle session immediately after
  process exit and returned to zero on the next bounded inspection; there is
  no lingering process or transaction. Cache remains unchanged by the
  documented undated-master rule.
- Re-running the exact apply command with the same progress returned
  `jra_setup=skipped`, detail `already completed`. `jltsql.log` size/mtime
  remained exactly `13,615,214 / 1787759786`, proving no JVOpen re-entry. The
  retained resume output SHA-256 is
  `eb2868f79d9b8d0e549d38a8c06026a82b6e9a0affdf230f81605368d268cb97`.
- Existing importer comments define statistics as accepted provider
  operations, but the generic PostgreSQL `insert_many` deduplicates same-PK
  rows before one upsert and returns only deduplicated physical operations.
  A selective table allowlist compensates only reviewed record families. The
  415-operation setup discrepancy is concrete evidence that an unlisted DIFN
  route still undercounts while reporting zero failures. Final data is correct,
  but the CLI/backend statistics contract is not.

Release status: setup transport/chunking/resume gates pass, but publication is
held on a separate minimal statistics repair. Prove the missing regression red
against current master with a same-key provider revision in one generic DIFN
route, make regular and optimized importers count accepted operations
consistently across SQLite/PostgreSQL without hiding real failures, merge that
logical PR, then rebuild/rebase this final release candidate from latest master.

### 2026-08-27 — release blockers merged

- Click 8.5 exposed 47 warning-as-error failures in the statistics PR's first
  executed GitHub `test` job. The independent test-infrastructure repair PR
  `#252` was proven red-first, received one native Copilot review, passed local
  and GitHub full gates, and squash-merged as
  `beee9df5427de3a07b33d40686322096d097bfca`.
- The PostgreSQL provider-operation statistics repair PR `#251` was then
  rebased onto that merge. Final candidate
  `ec16949e6599227696a58656b934fec80ce48c0e` passed a fresh PostgreSQL 16 plus
  SQLite/Click selection (`370 passed, 10 subtests passed`), the non-slow suite
  (`4799 passed, 507 skipped, 14 deselected, 21 subtests passed`), GitHub
  `test`/`lint`/Windows jobs, unresolved review threads zero, and a clean-tree
  gate. It squash-merged as
  `b722317167c92b893b2753a18b192f9b99569388`.
- This release branch remains clean at its prior candidate
  `88d2e03c9e381651469f271ce82f20ba0015991e`; prior artifact and provider
  evidence is historical evidence for the old code candidate only. Its
  artifacts and image must not be published as the final merge result.

Next safe action: rebase this branch onto exact latest `origin/master`
`b722317167c92b893b2753a18b192f9b99569388`, rebuild wheel/sdist from the new
immutable candidate, and rerun the affected statistics, package/install,
SQLite/PostgreSQL, exact-runtime, and bounded provider/log reconciliation
gates. Do not repeat the already-proven full setup solely for volume, and do
not tag until the release PR merges and the merge SHA passes post-merge smoke.

### 2026-08-27 — blocker-merge carry-forward candidate

- The release branch was rebased without conflict onto exact `origin/master`
  `b722317167c92b893b2753a18b192f9b99569388`. The resulting immutable code and
  release-metadata candidate was
  `b01eaa5d6146cc39f9a567a6aaf24a98b9e2b057`; its worktree was clean.
- Fresh artifacts were built from a `git archive` of that exact SHA, not from
  the worktree:
  - wheel `jltsql-2.0.0-py3-none-any.whl`, SHA-256
    `e90fe9e823924851107825ea7778166106ae978bb90c502f180a1ebc0088564b`;
  - sdist `jltsql-2.0.0.tar.gz`, SHA-256
    `b10ef13b6758075a055e48e2e0e1f3d2105e03c47c11d51de03a52afe47f45f8`.
- Both distribution-content checks passed. The wheel reports exact metadata
  `jltsql 2.0.0`, Python `>=3.12`, and contains neither tests nor `specs/`.
  A fresh isolated Python 3.12 environment and unrelated writable directory
  passed import-origin/version, `init`, `config --show`, and SQLite
  `create-tables`; the resulting database contained 80 tables.
- A fresh disposable PostgreSQL 16 plus SQLite selection covering SE
  `MakeDate=00000000`, schema migration, BN provider-operation statistics,
  importer rollback/recovery, and CC passed **299 tests**. The PostgreSQL
  container was removed after the run.
- The exact candidate's full non-slow suite passed **4,799 tests**, with 507
  environment/optional skips, 14 slow deselections, and 21 subtests. Test-gate,
  fatal Flake8, compile, lock parity, diff and clean-tree checks passed.
- Read-only recheck before the current runtime gate found no feature-generation
  or importer process. Draft PR #249 still points to old pre-blocker SHA
  `88d2e03c9e381651469f271ce82f20ba0015991e` and therefore still displays the
  old Click failure; it must not be treated as evidence for this candidate.
  The healthy development JRA collector likewise still runs old candidate
  `1f9f4fc8c77bbe88d398b6263ffa05c64f66eead`.

This worklog update intentionally creates one final docs-only candidate SHA.
Next safe action: rebuild artifacts and the temporary JRA runtime image from
that exact SHA, repeat artifact/install and affected database gates, then
rotate only `jra-collector` with preserved Wine identity, mounts, credentials
and reset/install controls disabled. Perform one bounded provider/log
reconciliation; do not repeat the already-proven full setup solely for volume.

### 2026-08-27 — carry-forward runtime and bounded PostgreSQL reconciliation

- The exact carry-forward SHA `c0987e9c13890f64c323af73cddd8fc516f3d0bc`
  differed from the already-tested `b01eaa5...` only by the preceding tracked
  worklog update. Production/test/package input outside `specs/` was identical.
- Fresh archive artifacts passed the distribution-content gate. Their hashes
  were wheel
  `23fd42a51d2c1d01c41debe8948eb0c1ac668f17e4e14a0b027b1271ecacad1a`
  and sdist
  `383e8a538314e54b36525ee33bfd60716667f8a46c028fe5db049f3037bf1e1b`.
  The first wheel-init invocation used unsupported system Python 3.10 and
  exited 1 before producing release evidence; the project Python 3.13.5 run
  passed. The runtime image below independently installed and imported the
  wheel under Python 3.12.
- Temporary image
  `kps-jra-collector-dev:jltsql-c0987e9c13890f64c323af73cddd8fc516f3d0bc`
  has image ID
  `sha256:f307bbdf2a6ad86ad4a449c2b9f5bce97fd2c307fa001d1a79b74c70d829f96d`.
  OCI labels bind source `c0987e9c13890f64c323af73cddd8fc516f3d0bc`,
  wrapper base `806445a0fad7ac27669f7a0bef7d6cbb4f86d7f8`, and final-candidate
  version. Network-disabled/read-only smoke reports installed/source 2.0.0
  from `/opt/venv/lib/python3.12/site-packages`.
- Rendered Compose projections before/after candidate substitution were exactly
  equal after removing only image/build/expected-version fields, both SHA-256
  `5b6e8c082abd36a358ac010e294fefacb30e1d0c15c3181caf284f75c5f1cd58`.
  Service-key write/reset/force-reset and auto-install remained 0; dialog and
  86,400-second timeout values remained the admitted existing values.
- Identity guard, host recovery lock, measured-owner service lock, provider
  absence and PostgreSQL-idle gates passed. Compose recreated only
  `jra-collector` using `--no-deps --no-build --force-recreate --wait`.
  It became healthy as container
  `14ed882dc50c5c6034840ec2dba0474e8b8cb264498c496357ed60889a01885b`.
  The protected actual hostname/MAC/environment/mount projection was identical
  before and after, SHA-256
  `ba1a2e7bd613667dfde8024ebb0827bfe493ce2d0e3e46ae50f8778f190df6da`.
  The four non-JRA development container identities remained
  `2a075bf1e29d91ee0f0a7fdce53e72525ef67f26113952d6fb04dbfa168f9a29`;
  Docker lifecycle events contained only the JRA replacement.
- Direct runtime checks agree: installed/source `2.0.0`, wrapper
  `2.0.0.dev7`, and `/health` on the actual port 8081 reports `status=ok` with
  both versions. An initial probe used port 8080 and got connection refused;
  this was a read-only probe-address error, while the configured 8081 listener,
  healthcheck and logs remained healthy.
- One bounded DIFN option-1 call (`20260820..20260827`) then exercised the exact
  candidate through JV-Link and PostgreSQL without repeating the 253,944-row
  setup. It completed **3,881 fetched / 3,881 parsed / 3,881 imported / 0
  failed / 10 batches**, with one open, provider EOF, successful close, fetch
  completion and import completion. `read_count=14`; `download_count=0`, so
  this is a positive provider-cache read rather than a new SDK download.
- The retained command log is
  `/home/keiba/backups/rebuild-20260820/ingestctl_jra_cache_final_c0987e9_difn_20260820_27.log`,
  SHA-256
  `5fa7018518c10cccd5fe6b9dfa005327b7cf9f5e0022e0a59dce925fd7e73fb8`.
  The mounted log delta has zero error-level records; all textual `failed` and
  `error` markers are zero-valued statistics fields.
- PostgreSQL master counts remained exactly
  `UM=214140,KS=1565,CH=1476,BR=10764,BN=8741,HN=11185,SK=39690,RC=2147`.
  There were zero non-idle client backends and zero open client transactions
  after completion. The undated-master app cache remained unchanged, matching
  its documented completeness rule. Candidate health, process cleanup and
  locks remained correct.

This entry is the final tracked operational update before the release PR. Its
commit necessarily becomes the final candidate SHA. Rebuild artifacts and the
temporary runtime image from that exact SHA, prove that the only delta from
`c0987e9...` is this excluded `specs/` record, and perform post-rotation
version/health/identity checks. Record the resulting full SHA and checks in PR
metadata rather than creating a self-referential worklog commit.

### 2026-08-27 — independent final review and release-wording repair

- Claude Code `2.1.233` reviewed exact candidate
  `6a91fbc009f946932dad65dab569873dfc3b0662` read-only with
  `--model fable --effort high`. Fable was selected because this final gate
  combines package/version, migration, provider-evidence and publication
  boundaries. Session ID is `5f41f7d2-5c4a-4b8a-9b25-8f3d9c6a21e0`.
- The review found no P0/P1 and classified code, security and packaging as
  green. It found one concrete P2: `RELEASE_NOTES.md` still said the release
  was unpublished and CHANGELOG kept the final changes under `Unreleased`, so
  the published tag would contradict its own bundled documentation.
- The existing public release-contract test was extended first. Against the
  unmodified candidate it failed exactly because
  `## [2.0.0] - 2026-08-27` was absent. This is the required red evidence.
- Release notes now describe the stable release without candidate/unpublished
  wording. CHANGELOG leaves `Unreleased` empty and moves the accumulated final
  content under dated `## [2.0.0] - 2026-08-27`. The same exact regression
  then passed.
- A bounded post-review audit found the CHANGELOG comparison footer still
  pointed `Unreleased` at `v1.6.10...HEAD`. The same public contract test was
  extended first and failed on the missing `v2.0.0...HEAD` link. The footer now
  defines `Unreleased` as `v2.0.0...HEAD` and `2.0.0` as
  `v1.6.10...v2.0.0`; the paired regression passes.
- Claude's focused test created ignored `.coverage`/`htmlcov` output; it did
  not change tracked files. Those disposable ignored artifacts are removed
  before the final clean-tree gate.

The commit containing this repair and this worklog entry is the final release
candidate. Its full SHA, final artifact hashes, exact-head CI and post-rotation
runtime evidence are recorded in PR #249 metadata to avoid a self-referential
worklog-only commit loop. Do not request another broad external review merely
because this documented review finding was fixed; native review and the exact
release contract/CI must cover the final SHA.
