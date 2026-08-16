# TK current-layout implementation worklog

## Iteration identity

- Objective: replace the one-entry TK implementation with the complete official
  current physical layout and lossless storage contract.
- Minimum scope: TK parser, native/standard schemas and metadata, importer/storage
  behavior, historical fixtures/tests, and the tracked compatibility audit. No
  version bump, release, or live provider acquisition is included in this
  implementation iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_tk_layout`
- Branch: `agent/tk-current-layout-20260816`
- Base/full SHA: `b62ba13be49c07e034acab1b5a5b483e10eb365a`
- Previous dependent merge: PR #184, YS official-layout merge
  `b62ba13be49c07e034acab1b5a5b483e10eb365a`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release/publication iteration.
- Agent/model: Codex only. No Claude session is used.

## Known starting evidence

- The tracked official-spec audit records current TK as 21,657 bytes while the
  repository publishes and parses only 727 bytes.
- The known truncation keeps one repeated registered-horse entry from an official
  array of up to 300 entries and places a delimiter inside the provider record.
- Exact offsets, repeated-entry cardinality, official key/update semantics, and
  historical-version behavior must be re-derived from the local official
  specifications and SDK before production code is changed.

## Plan and gates

- Reconcile JV-Data 4.8.0.2, 4.9.0.1, SDK 5.0.0, the current code/schema, and
  relevant official developer-community discussions. Record any physical-layout
  change rather than assuming current-only compatibility.
- Add one consolidated TK contract and run it red against unchanged production
  code. Include strict framing/encoding, every repeated entry, schema/key and
  update semantics, obsolete storage, both importers, and PostgreSQL where the
  official contract supports them.
- Implement once after aggregating findings. Run affected, full,
  workflow-equivalent, fatal lint, compile, and disposable PostgreSQL validation
  on an exact full SHA.
- Request one GitHub-native Copilot review, require green CI, unresolved threads
  zero, a clean worktree, and tree-equivalent merge.
- STOP on conflicting official evidence, unsafe migration, executable failure,
  base drift, or an unresolved actionable review finding.

## Official reconciliation completed before implementation

- Official inputs were re-read from the locally preserved JRA-VAN artifacts:
  `JV-Data4802.xlsx` SHA-256
  `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`,
  `JV-Data4901.xlsx` SHA-256
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`,
  and SDK 5.0.0 Python structure SHA-256
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`.
- The normalized TK format sections in JV-Data 4.8.0.2 and 4.9.0.1 differ only
  by an empty rendered line. Both define one exact 21,657-byte record: bytes
  1-655 are the race/header area, bytes 656-21,655 are 300 fixed 70-byte
  registered-horse slots, and bytes 21,656-21,657 are CR/LF. There is no old
  727-byte official branch to preserve.
- SDK 5.0.0 independently uses `byte[21657]`, parses all 300 slots from
  `656 + 70 * i`, and reads CR/LF at byte 21,656. The per-slot fields are
  `Num`, `KettoNum`, `Bamei`, `UmaKigoCD`, `SexCD`, `TozaiCD`,
  `ChokyosiCode`, `ChokyosiRyakusyo`, `Futan`, and `Koryu`.
- The official race key is `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`.
  `DataKubun=1` is the pre-handicap snapshot, `2` the post-handicap snapshot,
  and `0` exact-record deletion. Each non-delete record is therefore a full
  race snapshot and storage must remove stale child rows when 1 is replaced by
  2; deletion must remove both header and every registered-horse row.
- Official developer-community discussions were used only for semantics, not
  to invent a physical layout: topic 290 states setup mode exposes the latest
  special-registration data; topic 328 documents that an NAR horse may retain
  its former JRA trainer at TK publication and be corrected later by SE; topic
  165 records the transition-period acquisition caveat; topic 147 identifies
  `UmaKigoCD` as the horse-symbol field. The parser must preserve provider
  values and must not rewrite trainer identity.
- Current code is not lossless: `TKParser.RECORD_LENGTH` is 727, only the first
  slot is parsed, bytes 726-727 are mislabelled as the delimiter, native
  `NL_TK` keys children by `KettoNum`, the standard mapping resolves to the
  nonexistent `TOKUBETSU`, and the official standard `TOKU`/`TOKU_RACE`
  tables are keyless.

## Storage decision

- Use two normalized tables in both naming modes. Native `NL_TK_RACE` stores
  one official race header and native `NL_TK` stores one row per populated
  registered-horse slot. Standard mode uses the existing official names
  `TOKU_RACE` and `TOKU`.
- Key headers by the six-field official race key and children by that key plus
  official `Num`. Preserve the slot payload exactly after ordinary field
  padding removal; do not infer or repair trainer values.
- Parse one physical record into one public header dictionary with private
  `_tk_registered_horse_rows` metadata. Validate framing, key/status, numeric
  registration count, unique sequential `Num` values, and count/payload
  agreement before any mutation. Apply every physical snapshot in provider
  order inside one transaction.
- An existing obsolete/keyless TK table is not safe to migrate automatically.
  Dedicated schema verification must fail closed before mutation and retain
  existing rows for explicit rebuild/reimport. Unrelated standard-table imports
  must remain usable when an obsolete TK table is present but unused.

## Red-first evidence

- Added `tests/test_tk_official_contract.py` before production changes. The
  pre-implementation command
  `python3 -m pytest -q -o addopts='' --basetemp=/home/keiba/scratch/pytest_tk_red tests/test_tk_official_contract.py`
  completed with `25 failed, 2 passed, 2 skipped`. Representative red evidence
  was `assert TKParser.RECORD_LENGTH == 21657` (`727 == 21657`); the remaining
  failures covered strict rejection, normalized schemas/mapping, coupled
  replacement/deletion, importer revalidation, single-record atomicity, and
  obsolete-schema fail-closed behavior. The two green cases were unrelated
  standard-import isolation and the two skips were credential-gated PostgreSQL
  variants.
- Implement the parser/schema/coupled-writer batch once, then rerun this same
  contract. Do not weaken the red assertions to fit the old layout.

## Implementation and pre-candidate validation

- Replaced the permissive 727-byte parser with an exact 21,657-byte CP932
  parser. It validates record type, CR/LF, official status/key/count fields,
  every physical slot number, contiguous 001..N sequencing, empty-slot
  initialization, and `TorokuTosu` agreement. It exposes one header plus the
  private `_tk_registered_horse_rows` list and does not store the delimiter.
- Added native `NL_TK_RACE` and normalized `NL_TK`; corrected standard routing
  to `TOKU_RACE` and `TOKU`; added official compound keys and field aliases;
  regenerated schema-backed metadata and indexes. Historical 727-byte test
  fixtures are explicitly synthesized into a current record with one horse and
  are not accepted by production parsing.
- Added one dedicated coupled writer shared by both importers. It verifies both
  schemas before mutation, revalidates parser-private rows, applies status 1/2
  as complete snapshot replacement and status 0 as coupled deletion, preserves
  provider order, and rolls back header insertion plus stale-child deletion if
  a child write fails. Existing incomplete/keyless TK storage fails closed;
  unused obsolete standard TK storage does not block unrelated imports.
- Updated the executable schema counts, index inventory, raceday schema/check
  labels, public data-support table, and the tracked compatibility matrix.
- Focused SQLite regression after implementation:
  `842 passed, 10 skipped`; the expanded TK contract alone is now
  `29 passed, 2 skipped`.
- Disposable PostgreSQL 16 (`postgres:16-alpine`, local ephemeral port) ran the
  complete TK contract with integration enabled: `31 passed`. This covered
  native/standard names and both importers. The disposable container was
  stopped and removed after the run.
- Pre-candidate full suite produced `2305 passed, 67 skipped, 3 warnings,
  6 subtests passed` plus two unchanged CLI tests that exited 1 only in that
  full-suite process. Both exact failing tests passed immediately in isolation
  (`2 passed`) without a code change, matching the previously observed
  order-dependent CLI flake. A clean full rerun remains required on the frozen
  candidate SHA; it is not waived.
- `compileall`, `git diff --check`, and fatal flake8
  (`E9,F63,F7,F82`) pass.

## Next safe command

- Frozen implementation candidate:
  `ef8218f7304a311b00c2d9acd574dc0b4841b43d`; base remained
  `b62ba13be49c07e034acab1b5a5b483e10eb365a` after `git fetch origin master`.
- Exact-candidate full suite: `2307 passed, 67 skipped, 3 warnings,
  6 subtests passed`. The prior CLI order-dependent failures did not recur.
- Exact-candidate workflow-equivalent selection: `864 passed, 2 skipped,
  3 warnings, 3 subtests passed`.
- Exact-candidate focused parser/schema/importer/raceday/index selection:
  `64 passed, 4 skipped`; exact-candidate disposable PostgreSQL 16 contract:
  `31 passed`. The PostgreSQL container was stopped and removed.
- Exact-candidate strict MkDocs build passed. It only reported the four existing
  crawler-audit pages outside `nav`; their separately requested deletion remains
  outside this implementation iteration.
- Exact-candidate `compileall`, fatal flake8 (`E9,F63,F7,F82`),
  `git diff --check`, clean worktree, and absence of disposable TK PostgreSQL
  containers all passed.
- Commit this evidence-only worklog update, rerun the final SHA gates required
  for a documentation-only delta, then push/open the TK PR. Request one native
  Copilot review, resolve every actionable thread, require green CI and a clean
  tree, and merge only if the final tree is unchanged from the reviewed tree.
