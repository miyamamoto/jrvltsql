# jrvltsql v2.0.0 Release Notes (unreleased draft)

This version is not released yet. The repository reports `2.0.0.dev0` until
the official data-contract repairs, documentation audit, and real acquisition
and database release gates are complete.

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
  malformed CP932 and unsupported historical/synthetic lengths, and preserve
  explicitly supported old/new semantic boundaries instead of guessing them
- native and standard schemas now verify primary keys, types, capacities,
  child-table constraints, and cancellation/delete behavior before mutation;
  several record families gained complete child storage or corrected keys
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
  nullable-key, or otherwise unsafe AV tables require rebuild and reimport
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
- Invalidates legacy cache completeness markers under schema v2, separating
  legacy raw from active raw.
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
