# jrvltsql v2.1.2 Release Notes

`2.1.2` is an emergency correctness hotfix on top of `2.1.1` for prospective
time-series odds capture; no parser, schema, storage, migration, or
provider-registration contract changes.

What `2.1.2` fixes over `2.1.1`:

- when `--post-time-within-minutes` / `--post-time-not-past-minutes` are
  requested, race targets are selected per full race key (Year, MonthDay,
  JyoCD, Kaiji, Nichiji, RaceNum) with lifecycle-source precedence: a stored
  same-day `RT_RA` row first owns its full key, and `NL_RA` is used only for
  full keys absent from `RT_RA`; when the optional `RT_RA` table is absent,
  `NL_RA` owns every key. A stale `NL_RA` post time coexisting with the current
  `RT_RA` revision is no longer misread as ambiguity — on 2026-09-05 that
  misread aborted the whole batch and left later due races without official
  O1/O2 capture
- the selected current row's DataKubun is validated against the official RA
  domain; missing, blank, or out-of-domain statuses fail closed naming the
  12-digit race key, and nothing is opened. A persisted DataKubun=0 erase
  marker also fails closed instead of becoming an active target. After
  validation, DataKubun=9 cancellations are omitted for whichever source owns
  the key, never falling back to the shadowed row. A 12-digit JVRTOpen key
  carrying both active and canceled selected rows fails closed independent of
  row order; genuine post-time conflicts still fail closed
- window statistics always report `omitted_canceled_keys` (0 when none), and
  `window_kept_keys` equals the keys actually opened
- machine-parsed CLI progress is extended for downstream verification: the
  `Window:` line adds `canceled=`, the `Keys:` lines add `nonempty=` (keys
  that returned at least one record — `ok=` success alone is not evidence of
  nonempty capture), a window run that keeps zero keys still prints exactly
  one terminal `Keys: 0/0 ...` summary, and `nonempty_keys` is always
  present in fetcher progress callbacks and the completion log
- target selection and queries without the post-time window options are
  unchanged; the only no-window output change is that `Keys:` lines gain
  `nonempty=` when a key is processed

Verification limits:

- regression coverage is database-backed: SQLite fixtures mirroring the real
  `NL_RA`/`RT_RA` key shape, with the generated PostgreSQL window query
  executed against an equivalent SQLite model (no live PostgreSQL in the
  focused run). No live JV-Link race day has exercised this build yet: the
  first complete prospective proof must come from a future real race day, and
  this release does not backfill 2026-09-05
- the normal updater physically removes RT DataKubun=0 rows. This read path
  therefore cannot distinguish an already-removed RT erase tombstone from a
  key which never received an RT update; rejecting a tombstone that remains
  stored is covered, but preventing stale-NL fallback after an already-removed
  RT erase is not proven by this release. `2.1.2` does not claim unconditional
  lifecycle resolution for every DataKubun state

Adoption / rollback:

- no schema change; no migration or reimport is required from `2.1.1`
- downstream `jrvltsql-wine-runtime` must explicitly re-pin this release's
  tag/artifact before KPS JRA prospective capture is considered repaired;
  merging or tagging alone adopts nothing
- rollback: re-adopt immutable `v2.1.1`
  (`0f3161d30de65f15795608e2a4bec9fc91e05349`); no database rollback is
  required

# jrvltsql v2.1.1 Release Notes

`2.1.1` is a CLI compatibility hotfix on top of `2.1.0`; no parser, schema,
storage, provider-registration, or migration contract changes.

What `2.1.1` fixes over `2.1.0`:

- `realtime odds-timeseries` now exposes `--post-time-within-minutes` and
  `--post-time-not-past-minutes` and forwards them to the generic `timeseries`
  implementation, so requested filtering cannot silently fall back to
  whole-day collection
- the alias exposes `--spec`, defaulting to `0B41,0B42`, while rejecting
  sokuho (`0B30`-`0B36`) and every other unsupported spec before collection
- omitting the new options preserves the previous official-spec, unfiltered
  behavior exactly

# jrvltsql v2.1.0 Release Notes

`2.1.0` is a minor release on top of `2.0.0`. It adds prospective capture of the
official one-year time-series odds (`0B41`/`0B42`) and fixes capture provenance;
no schema rebuild or reimport is required relative to `2.0.0`.

What `2.1.0` adds over `2.0.0`:

- generic `realtime timeseries` accepts `--post-time-within-minutes` and
  `--post-time-not-past-minutes`, so a scheduled run can fetch only the races
  whose post time is still ahead instead of the whole day. Post time is resolved
  from `NL_RA`/`RT_RA`; missing, malformed, or ambiguous post times fail closed
  rather than being silently kept or dropped
- time-series odds upserts preserve `CollectedAt` as the first capture time, so a
  later refetch cannot erase the evidence that a price was held before the
  decision time. SQLite and PostgreSQL behave identically
- the sokuho odds primary key is publication identity. Because collapsing
  existing rows deletes data, the migration is no longer run implicitly at
  startup or on the write path; it is an explicit operator command that defaults
  to dry-run and applies only with `--apply`

# jrvltsql v2.0.0 Release Notes

`2.0.0` is the stable major release built from the provider, SQLite,
PostgreSQL, setup/backfill, realtime, artifact, and independent-review gates
recorded in the release worklog. The 64-bit SDK path remains outside the
supported claim; 1.x and older 2.0 prerelease databases require a backup,
rebuild, and reimport.

What `2.0.0` adds over `2.0.0.dev6`:

- accepts the official `SE` cancellation/exclusion initial value
  `MakeDate=00000000`, while continuing to reject malformed dates. Standard
  `UMA_RACE.MakeDate` is `VARCHAR(8)` rather than `DATE`, and a legacy `DATE`
  table fails before DML. Existing databases must be rebuilt and reimported;
  this is not an in-place migration
- consolidates the official record, key, schema, transaction, transport, and
  packaging contracts proven incrementally by `dev0` through `dev6` into one
  major-version release. The prerelease sections below remain as audit history

What `2.0.0.dev6` adds over `2.0.0.dev5`:

- preserves the exact COM buffer bytes when pywin32 projects a binary provider
  buffer as text. The recovery accepts supported Latin-1-like, CP1252 and
  CP932 projections, removes only the trailing COM NUL, and requires all
  exact-length recovery candidates to agree. Ambiguous or oversized-prefix
  payloads fail closed instead of sending corrupted fixed-width bytes to a
  parser
- partitions only the live-evidenced bounded `RACE` option-1 fetch into
  calendar-year `JVOpen` chunks. Every chunk is closed before the next begins;
  a primary processing error remains primary when close also fails, and
  provider `-402` recovery replays only the prefix emitted by the active
  chunk. Option 2, setup options 3/4, and data specs without verified bounded
  range behavior remain start-only

What `2.0.0.dev5` adds over `2.0.0.dev4`:

- accepts the exact H6 race-cancellation shape subsequently observed during
  the registered five-year provider setup: `DataKubun=9` may retain a known
  trifecta combination while its physical vote field is exactly eleven
  spaces. The parser exposes `SanrentanHyo=""` and native numeric vote storage
  uses SQL `NULL`; blank values on live statuses 2/4/5, mixed tab/digit bytes,
  caller `None`, and caller space-only values remain rejected before mutation.
  Realtime raw, parsed-record, and batch inputs use the same validation.
  Existing expanded caller rows with status 9 and `SanrentanHyo=""` remain
  accepted as SQL `NULL`, so this release does not claim raw-record provenance
  for caller-created mappings
- preserves H6 `DataKubun=0` as a key-only physical erase. A noncanonical or
  undecodable non-key body cannot suppress an exact erase when the type,
  status, MakeDate, six-field race key, fixed length, and CRLF remain valid;
  live statuses continue to validate the complete body

What `2.0.0.dev4` adds over `2.0.0.dev3`:

- accepts the exact H1 race-cancellation shape observed during the registered
  five-year provider setup: `DataKubun=9` may retain a known combination while
  the physical vote field is exactly eleven spaces. The parser exposes
  `Hyo=""` and native numeric vote storage uses SQL `NULL`; blank values on
  live statuses 2/4/5 and non-space whitespace remain rejected before
  mutation. Existing expanded caller rows with status 9 and `Hyo=""` are also
  accepted as SQL `NULL`, so this release does not claim raw-record provenance
  for caller-created mappings
- retains the strict H6 boundary. The official format permits an unregistered
  space value, but the audit found no available combination-bearing H6
  status-9 instance in the current RACE cache or development database, so dev4
  does not widen H6 by analogy

What `2.0.0.dev3` adds over `2.0.0.dev2`:

- option 3/4 setup uses one inclusive-start, start-only `JVOpen`. The official
  historical setup tail is all setup data after `fromtime`; an end timestamp
  only limits the current-month normal-data portion, so `--to` remains a
  client-side record filter and calendar-year recursion is not used
- the finite `JVLINK_OPEN_TIMEOUT_SECONDS` ceiling is raised to 86,400 seconds
  for monitored multi-hour setup recovery; the default remains 120 seconds
  and invalid, non-finite, or larger values fail closed
- NL cache schema v3 invalidates completeness markers built with the old
  setup start boundary while retaining their v2 raw bytes separately;
  `cache build/rebuild` also rejects malformed or inverted ranges before
  cache lookup or clearing

What `2.0.0.dev2` adds over `2.0.0.dev1`:

- `JVOpen` no longer imposes a fixed 120s response budget. A deployment sets
  `JVLINK_OPEN_TIMEOUT_SECONDS` (1-7200, default 120) so a setup fetch, or a
  `JVOpen` that is waiting on JV-Link's own dialog (measured 1,008s), is not
  abandoned as a bridge timeout. An unreadable value fails closed

What `2.0.0.dev1` added over `2.0.0.dev0`, all of it measured against a real
registered JV-Link on a Linux/Wine development host:

- a first end-to-end acquisition through storage: `JVInit` `0`,
  `JVOpen(RACE, 20260810, option=1)` `0` with 48 files, then
  4,447 fetched / 864,827 parsed / 864,827 imported / 0 failed into SQLite
  (`NL_H6` 319,548, `NL_O6` 319,548, `NL_H1` 112,257, `NL_RA` 144, `NL_SE` 1,934, …)
- two contract defects that only real provider data exposes, both of which had
  made whole record families unimportable: H1 cancellation markers fill the
  field width, so three-character bet types send `***`, and O1-O6 announcement
  time is set only for interim odds, so final odds carry the official
  zero-filled `00000000`. Both values are now stored verbatim
- a realtime `JVRTOpen` that closes on no-data and error, instead of leaving the
  stream open so the next key fails with `-202`, plus `RT_RA` as a same-day
  target source next to `NL_RA`
- the Wine/Docker runtime layer (native 32-bit bridge, image, entrypoint) and
  the manual noVNC registration runbook. Nothing in it performs an approval:
  installing JV-Link, agreeing to the terms and entering the service key stay
  with a person, and JV-Link's own dialogs are left for that person unless
  `JVLINK_AUTO_CLOSE_DIALOGS=1` is set explicitly

What this prerelease is verified against:

- the complete test gate on the frozen release SHA, with SQLite and a real
  PostgreSQL 16 backend
- a wheel and an sdist built from that same SHA. The wheel (not the sdist) was
  installed into an isolated virtual environment, where `jltsql --version`, `jltsql init`, full schema creation
  (80 tables), and an official fixed-width O2 import (complete-snapshot
  replacement plus `------` / `******` / `000000` markers) were exercised

What it is **not** verified against:

- 64-bit SDK execution, or ARM hosts (JV-Link and the bridge are 32-bit x86)
- migration of an existing 1.x database (rebuild and reimport are required)
- sustained multi-day collection, or realtime `JVRTOpen` against a live race day
  (the measured `JVRTOpen` targets had no data on the days available)

Current migration boundary:

- configure provider registration in DataLab; programmatic registry-writing
  setup APIs have been removed
- non-Windows bridge deployments must explicitly configure the externally
  managed runner with `JVLINK_BRIDGE_RUNNER`
- `jltsql init` creates a safe SQLite-only configuration in the current
  directory; installed package directories are no longer configuration or
  runtime-state targets
- 64-bit SDK execution remains unverified and is not claimed as supported

Public API replacements:

- `JVLinkWrapper.jv_set_service_key` and
  `JVLinkBridge.jv_set_service_key` have no programmatic replacement;
  complete provider registration in DataLab
- removed `DATA_SPEC_O1` through `DATA_SPEC_O6` constants are replaced by
  `RECORD_TYPE_O1` through `RECORD_TYPE_O6`; these are record identifiers
  delivered by a supported data spec, not standalone open specs
- use `uses_external_runner` instead of the removed
  implementation-specific runner-detection property

## Data-contract and reliability changes since v1.6.10

- parser contracts now bind current official fixed-width layouts, reject
  malformed CP932 in interpreted fields and unsupported historical/synthetic
  lengths, and preserve explicitly supported old/new semantic boundaries
  instead of guessing them
- TC start-time changes now use the official 45-byte layout and exact six-part
  race identity in `NL_TC`, `RT_TC`, and `HASSOU_JIKOKU_CHANGE`. Announcement
  and before/after times remain lossless fixed-width text; current status 1 is
  the only accepted TC status. Unsafe legacy/keyless/nullable/extended tables
  require backup, rebuild, and reimport. TC does not invent a status-0 delete:
  stale realtime changes are removed only by a successfully completed 0B14
  full-date snapshot replacement
- CC course changes now use the official 50-byte layout and exact six-part
  race identity in `NL_CC`, `RT_CC`, and `COURSE_CHANGE`. Announcement time,
  four-digit before/after distances, official track codes, and reason codes
  remain lossless, including documented zero-initial values. Existing
  keyless, nullable, wrong-type, extended, or otherwise unsafe CC tables must
  be backed up, rebuilt, and reimported. Current status 1 is the only accepted
  status; stale realtime rows are removed only after a successful 0B14
  full-date snapshot, while 0B16 remains event-oriented.
- O1-O6 odds (オッズ1〜6) now bind the official fixed-width layouts
  (962 / 2,042 / 2,654 / 4,031 / 12,293 / 83,285 bytes) and keep every official
  provider value. The parser previously discarded rows whose odds were all `0`
  or `-`/`*`, so `000000` (no bet), `------` (cancelled before sale) and
  `******` (cancelled after sale) were lost; odds and favourite-order columns
  were `REAL`/`INTEGER` in `NL_O1`-`NL_O6` and `RT_O1`-`RT_O6` and
  `DECIMAL`/`SMALLINT` in the standard `ODDS_*` children, so cancellation
  markers collapsed into `NULL` and could not be told apart from "not
  registered" (blank). Those columns are now text and store the official value
  verbatim.
- one physical O1-O6 record is the complete odds snapshot of one race at one
  point in time, so native, realtime and standard storage now replace the whole
  race snapshot. A later snapshot with fewer combinations no longer leaves the
  combinations it no longer offers, and a totals-only snapshot (no sale or a
  cancelled race) replaces every earlier combination while keeping the official
  vote totals as a single `Kumi=TOTAL` row. `DataKubun=0` erases the race
  physically from every O1-O6 table, leaving no tombstone or totals sentinel.
- O1-O6 race keys and combination numbers are now `NOT NULL`, and the official
  body domain plus a strict schema preflight run on every storage path
  (batch importer, optimized importer, single-record import, realtime, and
  `DualDatabase`) before any DML. Missing official keys, nullable keys,
  additional UNIQUE/partial/expression/exclusion indexes, deferrable primary
  keys, columns too narrow or too numeric for the official markers, missing
  owner/child tables, and unapproved CHECK/FOREIGN KEY constraints are
  rejected. Existing O1-O6 tables are not migrated automatically: back up,
  rebuild with the current schema, and reimport from `RACE`.
- native and standard schemas now verify primary keys, types, capacities,
  child-table constraints, and cancellation/delete behavior before mutation;
  several record families gained complete child storage or corrected keys
- H6 vote storage (票数６・3連単) now validates the official 102,890-byte record
  body (official `DataKubun` `0`/`2`/`4`/`5`/`9`, a real `MakeDate` and race day,
  two-digit course/meeting/day/race numbers, registered and starting counts, the
  sale flag `0`/`1`/`3`/`7`, eighteen positional refund flags, six-digit
  combinations, eleven-digit vote counts, four-digit favourite order, and the two
  eleven-digit vote totals) before storage, keeps the official non-numeric
  favourite markers (`----` cancelled before sale, `****` cancelled after sale,
  blank not registered) as text in `NL_H6`/`RT_H6` (`SanrentanNinki` was
  `INTEGER`) and standard `HYOSU_SANRENTAN.Ninki` (was `SMALLINT`), and erases a
  status-0 race physically from every H6 table, including the standard
  `HYOSU2`/`HYOSU_SANRENTAN` pair that the previous mapping missed. A snapshot
  with no sold combination (no-sale flag or a cancelled race) previously failed
  to import into native storage and lost its official vote totals; it is now
  stored as a single `SanrentanKumi=TOTAL` row, matching the H1 totals row.
  Existing H6
  tables with nullable keys, numeric favourite columns, missing columns,
  additional UNIQUE indexes, or other drift are not migrated automatically:
  back up, rebuild with the current schema, and reimport from `RACE`.
- H1 vote storage (票数１・全掛式) now validates the official 28,955-byte record
  body (official `DataKubun` `0`/`2`/`4`/`5`/`9`, a real `MakeDate` and race day,
  two-digit course/meeting/day/race numbers, registered and starting counts, sale
  flags `0`/`1`/`3`/`7`, place-payout key `0`/`2`/`3`, twenty-eight/eight/eight
  positional refund flags, per-bet-type two/four/six-digit combinations,
  eleven-digit vote counts, per-bet-type two/three-digit favourite order, and
  fourteen eleven-digit vote totals) across native `NL_H1`, realtime `RT_H1`, and
  the standard `HYOSU` owner/child family. One record replaces one complete race
  snapshot, and `DataKubun=0` performs a physical exact-key erase of every H1
  table, including the standard owner and children that the previous erase map
  missed because it named the non-existent `HYO_TANPUKU` alias. The official
  favourite order is not numeric: `--` (cancelled before sale), `**` (cancelled
  after sale) and blank (not registered) are provider values, so `NL_H1.Ninki`
  and `RT_H1.Ninki` change from `INTEGER` to `TEXT` and standard
  `HYOSU_WAKU`/`HYOSU_UMATAN`/`HYOSU_SANREN.Ninki` change from `SMALLINT` to
  `VARCHAR`; the already-textual `HYOSU_TANPUKU.TanNinki`/`FukuNinki` and
  `HYOSU_UMARENWIDE.UmarenNinki`/`WideNinki` carry the same contract, and blanks
  are stored as empty strings rather than `NULL`. Key columns
  become `NOT NULL`, and the standard children reject any UNIQUE index other than
  the official key. Operators must back up, rebuild, and reimport retained `RACE`
  data; cancellation markers are not recoverable without a reimport
- UM racehorse master storage now validates the official 1609-byte record body
  (real registration/erase/birth dates, `0/1` erase flag, `0/1`-or-blank stabling
  flag, digit symbol/sex/breed/coat/affiliation codes, five/eight/six-digit
  trainer/breeder/owner codes, six nine-digit accumulated prizes, twenty-seven
  eighteen-digit finish-count groups, twelve-digit running-style counts,
  three-digit registered race count, fourteen ten-digit pedigree numbers) and the
  exact ten-digit `KettoNum` identity. Native `NL_UM` and standard `UMA` apply
  provider-ordered status 1/2/3/4/9 revisions and a physical exact-key status-0
  erase that leaves no tombstone row, and reject nullable, keyless, wrong-type,
  under-capacity, generated, extended, or additionally constrained schemas before
  mutation. Officially blankable text spans are stored as empty strings rather
  than `NULL`; `NL_UM.ZaikyuFlag` changes from `INTEGER` to `TEXT` so the official
  blank survives. Operators must back up, rebuild, and reimport retained `DIFN`
  data; UM remains accumulated-only without an `RT_UM` table
- SK progeny master storage now validates the current official 208-byte
  record body (real `BirthDate`, digit sex/breed/coat codes, 産駒持込区分
  `0/1/2/3`, four-digit import year, eight-digit breeder code, fourteen
  ten-digit pedigree numbers) and the exact ten-digit `KettoNum` identity.
  Native `NL_SK` and standard `SANKU` apply provider-ordered status 1/2
  revisions and a physical exact-key status-0 erase, and reject nullable,
  keyless, wrong-type, generated, extended, or additionally constrained schemas
  before mutation. Officially blankable `SanchiName` is stored as an empty
  string rather than `NULL`. Operators must back up, rebuild, and reimport
  retained `BLDN` data; the obsolete 178-byte layout is not migrated, and SK
  remains accumulated-only without an `RT_SK` table
- HN breeding-horse master storage now accepts only the current official
  251-byte record and exact ten-digit `HansyokuNum` identity. Native `NL_HN`
  and standard `HANSYOKU` apply provider-ordered status 1/2 revisions and a
  physical exact-key status-0 erase, and reject nullable, keyless, wrong-type,
  generated, extended, or additionally constrained schemas before mutation.
  Officially blankable `BameiKana`, `BameiEng`, and `SanchiName` are stored as
  empty strings rather than `NULL`.
  Operators must back up, rebuild, and reimport retained `BLDN` data; the
  obsolete 245-byte layout is not migrated, and HN remains accumulated-only
  without an `RT_HN` table
- HC hill-training storage now binds the current official 60-byte layout and
  four-part identity in both `NL_HC` and standard `HANRO`, preserves every
  tenths-of-a-second timing field as seconds, applies provider-order update and
  exact status-0 erase, and rejects legacy nullable/keyless/unsafe or extended
  tables before mutation. Operators must back up, rebuild, and reimport `SLOP`;
  HC remains an accumulated-only format and does not imply realtime support
- SE horse-per-race storage now uses the complete eight-part official identity
  ending in `KettoNum` across native, realtime, and `UMA_RACE`; legacy
  seven-key/keyless tables require backup, rebuild, and `RACE` reimport rather
  than an automatic key rewrite. The current 555-byte layout, all four reserved
  fields, integer-kilogram body weight/change, exact targeted erase, and status-A
  prize-zero semantics are preserved on SQLite and PostgreSQL
- AV scratch/exclusion storage now uses the official seven-part identity in
  native, realtime, and `TORIKESI_JYOGAI` tables. Historical status 0 is an
  exact erase only before 2003-07-11; current status 1/2 and both pre/post-2021
  reason-field initial representations remain supported. Existing keyless,
  nullable-key, legacy `AVOIDENCE`-only, or otherwise unsafe AV tables require
  rebuild and reimport
- HR payout/refund storage now preserves every official repeat in the 719-byte
  record, including all three reserved entries as text rather than invented
  numeric values, and uses the exact six-part
  race key in `NL_HR`, `RT_HR`, and standard `HARAI`. Existing keyless,
  nullable-key, incomplete-repeat, or otherwise unsafe HR tables require
  backup, rebuild, and RACE reimport. Records before trifecta sales began on
  2004-08-14 preserve bytes 604-717 as an opaque hexadecimal compatibility
  value instead of labeling undocumented old reserved bytes as trifecta
  payouts. Status 0 remains an exact-key erase. Status 9 remains stored as a
  cancellation state, while its unspecified body is retained only as an opaque
  raw audit value instead of being interpreted as ordinary payout fields.
  HR header/key bytes and all interpreted body ranges remain strict CP932;
  only the declared status-0/status-9 body and pre-2004-08-14 legacy tail are
  preserved byte-for-byte without text decoding
- HS horse-sale storage now accepts only the current official 200-byte layout,
  keeps the exact `(KettoNum, SaleCode, FromDate)` identity in native `NL_HS`
  and standard `SALE`, and applies status 0 as an ordered exact-key erase.
  Pre-v2 stores require backup, rebuild, and reimport even when empty; the sole
  additive exception is an empty, otherwise current-compatible native `NL_HS`
  missing only the layout marker/delimiter. Eight-digit parent-registration
  values are valid in the current ten-byte fields and are not generation
  evidence. Historical age values are already unified by provider setup and
  are not reinterpreted, while historical sale-name notation is preserved.
  HS is accumulated-only, so unsupported realtime input changes neither a DB
  table nor the local realtime cache
- imports and realtime updates preserve provider order and use fail-closed
  transaction recovery so returned statistics agree with durable rows across
  SQLite and PostgreSQL
- acquisition/cache handling now requires complete read/EOF/close evidence,
  avoids false complete markers, and repairs only provider-identified corrupt
  files under bounded rules
- distribution and bootstrap gates now inspect built artifacts, isolate wheel
  imports, and verify a base-dependency SQLite installation without writing
  runtime state into the package tree
- MCP schema metadata now covers all 134 executable storage tables: 80 native
  tables and 54 JRA-VAN-standard tables. Application first verifies each live
  backend's exact column set, normalized type family, logical nullability, and
  ordered primary key; SQLite then replaces stale display-only rows,
  PostgreSQL comments physical identifiers, and Dual applies backend-specific
  operations independently. The MCP metadata export is version 2.0.0:
  `nullable` describes the portable logical schema (not SQLite's raw PRAGMA
  enforcement bit), while `indexes` lists distinct physical columns used by
  configured secondary indexes rather than complete index definitions

The record-by-record support and storage details are maintained in
[`docs/data_support.md`](docs/data_support.md).

## Required database migration

Treat v2 as a schema rebuild boundary; do not point the new importer at an
unreviewed 1.x database and assume additive migration is sufficient.

1. Stop collectors and take a verified backup of every SQLite/PostgreSQL
   database plus the prior application release.
2. Validate the backup can be opened/restored, then rebuild affected native or
   standard tables with the v2 schema. A fail-closed preflight error means stop;
   do not weaken keys or constraints to continue.
3. Reimport retained provider data with the v2 parser and verify per-table
   counts, official keys, cancellation behavior, and representative readback.
4. Resume collection only after the real acquisition-to-database gate passes
   for the exact release SHA.

Rollback means stopping v2, restoring the backup, and running the previous
release against that restored database. Do not reuse a partially migrated v2
database with a 1.x binary.

# jrvltsql v1.6.10 Release Notes

Everything merged since v1.6.9: PR #149, #150, #151, #152, and #153.

## Highlights

- Writes the raw write-through cache once per `jv_read` buffer instead of once
  per parsed record. Full-struct parsers expand a single buffer into thousands
  of rows (H1: 1,485 rows from 28,955 bytes; H6: 4,896 rows from 102,890
  bytes), and every one of those rows carries the same `_raw`, so the identical
  blob was appended once per row. A real RACE/option=4 run produced 21.8 GB of
  cache in about ten minutes with 99.9% duplicate content, where the actual data
  for the range is roughly 80 MB. Separately, the observed write rate was
  4,230 MB/min before the fix and 10.17 MB/min with 0% duplicates when the same
  range was re-run after it. The volume and the rate are two independent
  measurements; neither is derived from the other. The `_raw` contract and the
  shape of yielded records are unchanged, so cache replay is unaffected.
- Self-repairs `JVRead` `-402` (a zero-byte corrupt file) at the official error
  boundary rather than by guessing physical bridge-cache paths. Only the exact
  filename returned by `JVRead` is deleted through `JVFiledelete`; the same
  `JVOpen` context is reopened, re-download completion, file count, and
  `last_file_timestamp` are all required to match, and the already-emitted
  prefix is drained without re-parsing, re-yielding, or re-caching it. Retries
  are bounded at two and every unprovable condition fails closed. `-403` may
  have already emitted part of the same file, so it deletes the file
  best-effort for the next run and fails closed instead of resuming at an
  unsafe position.
- Rolls the append-only raw cache back to a byte checkpoint taken before the
  fetch. Abandoning the generator mid-stream, an incomplete replay, or a failed
  index update no longer leaves a partial cache behind, and multi-day
  completeness markers are committed together by atomic replace from a
  temporary file.
- Makes `--from/--to` and cache completeness fail-safe. Option 2 bypasses the
  cache entirely — including existing NL cache — because `JVOpen` does not
  treat `--from` as a fetch range under that option, and
  `cache build/rebuild --option 2` now fails loudly before it can record a
  bogus complete range.
- Treats HC/WC as time-series rather than undated master data, using
  `ChokyoDate` for the `--to` filter and the cache date key. A master row with
  no corresponding event date suppresses the complete-cache marker and rolls
  back the partial cache appended by the same fetch.
- Invalidates pre-fix cache completeness markers under schema v3, separating
  schema-v2 raw records from the active cache generation. A v2 marker cannot
  prove that the corrected inclusive setup start retained a record stamped
  exactly at midnight.
- Corrects the `fetch --option 2` note and `--from` help to match the official
  JV-Link specification: `fromtime` manages continuity within the current race
  cycle rather than selecting an arbitrary retained week, and Sunday/Monday can
  span two race cycles. Documentation and help only; fetch and cache behavior
  are unchanged.
- Documents `connect_timeout` and `sslmode` in the `databases.postgresql` block
  of `config/config.yaml.example` at the same values as the built-in defaults
  (10 / prefer). The handler already read both keys.

# jrvltsql v1.6.9 Release Notes

## Highlights

- Fixes PostgreSQL table/column/primary-key resolution to consistently use
  `to_regclass()`, so a same-named table in a schema outside `search_path` no
  longer causes false-positive "table exists" results or `UndefinedTable`
  crashes on primary-key lookups.
- Corrects several JV-Link return-code mislabelings independently duplicated
  across the codebase after the PR #144 return-code table fix: `-100` was
  misplaced as a JVOpen/JVRTOpen code (it belongs to JVSetUIProperties/
  JVSetServiceKey), and `quickstart.py`'s JVInit diagnostics conflated
  `-101`/`-102`/`-103` (sid parameter format errors) with service-key state
  (which is actually `-301`/`-302`/`-303` from JVOpen/JVRTOpen).
- Corrects stale comments in the JVRead/JVStatus retryable-error handling
  (`-201`/`-202`/`-203`) to match the official spec; the set of codes treated
  as retryable is unchanged.

# jrvltsql v1.6.8 Release Notes

## Highlights

- Adds canonical numeric JRA SE columns for race time, final 3F, body weight,
  body-weight change, finish position, and horse number while preserving the
  official raw fixed-width fields unchanged.
- Applies the new columns through additive SQLite/PostgreSQL migrations and
  verifies both schema keys and representative official record conversions.

- Treats `JVRead -2` as a read failure rather than no data, preventing partial
  realtime and historical responses from being committed.
- Rejects every realtime stream that exits before the official completion
  code, including positive-length reads with an empty buffer, so an incomplete
  0B14 response cannot replace a valid stored snapshot.
- Migrates dual SQLite/PostgreSQL schemas against each concrete backend, using
  backend-specific table identifiers and verifying both copies before import.
- Preserves best-effort dual-mode availability by excluding an unavailable
  secondary mirror from migration while still validating connected mirrors.

- Treats external bridge subscription responses as normal optional-spec skips in
  the non-interactive daily collector path.
- Prevents an unsubscribed 0B14 or 0B51 feed from aborting collection of other
  configured feeds.

## Upgrade Notes

- This is a compatible reliability patch for v1.6.3 data layouts.
- External collector runtime changes are not part of this repository release.
