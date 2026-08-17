# JC official contract worklog

## Start state

- Started: 2026-08-18 JST
- Objective: audit and, only where primary evidence requires it, repair the
  current JC (jockey-change announcement) parser, native/standard/realtime
  storage, migration, metadata, tests, and public documentation.
- Minimal scope: JC only. The generic PostgreSQL same-key batch statistics
  discrepancy and other remaining JV-Data formats stay in separate later
  iterations.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_jc_official`
- Branch: `agent/jc-official-contract-20260818`
- Base / starting HEAD / current `origin/master`:
  `074425a220f33e63b053751b96ce1e5e7cdd1f7e`
- Dependency evidence: PR #208 was squash-merged as
  `074425a220f33e63b053751b96ce1e5e7cdd1f7e`; this iteration starts from that
  merge, not from its former PR head.
- Production release remains `v1.6.10`; the repository candidate remains the
  unreleased `2.0.0.dev0` compatibility series. No release or capability claim
  is made by starting this audit.
- Dependency order: complete and merge this JRA format iteration before the
  final jrvltsql release audit; only after jrvltsql is released may the planned
  jrvltsql-nar and jvlink-mcp-server propagation/release iterations start.

## Audit contract

- Primary evidence: pinned JV-Data 4.8.0.2 and 4.9.0.1 workbooks plus the
  tracked SDK 5.0 source manifest. Community reports may identify provider
  defects or transition behavior but cannot override the official field/key
  contract without corroboration.
- Check current physical length and every field span; official key and status
  domain; historical same-length or physical changes; parser/caller validation;
  native, standard, realtime, SQLite, PostgreSQL, and Dual storage; schema
  preflight; metadata; deletion/ordering semantics; tests and docs.
- Any new or changed validator/gate must first be exercised by an observed red
  regression on unchanged production and retain a paired valid green case.
- STOP on source ambiguity, candidate drift, failed required test/readback,
  unsafe schema mutation, unresolved review thread, or any release action
  before the complete release gate.
- No 64-bit SDK support statement is permitted without a real 64-bit SDK
  acquisition and storage proof. This iteration does not attempt that proof.

## Initial state and next safe action

- Fresh worktree is clean and exactly matches the merged WE release-series
  head above. No implementation or test change has been made yet.
- Existing code references suggest the native/realtime JC identity omits
  `HappyoTime`, while the central status ledger already defines current status
  `1` and a pre-2003-07-11 historical status-0 window. These are hypotheses,
  not accepted findings, until independently derived from primary sources and
  reproduced against storage entrypoints.
- Next safe action: derive the complete JC physical layout, ordered key, status
  domain, availability rules, and change history from the pinned official
  sources, then compare parser, schemas, importer/realtime paths, metadata,
  current tests, and public docs before designing one compact red-first repair.

## Primary-source derivation and starting-SHA probes

- Pinned artifacts were read directly. SHA-256:
  - JV-Data 4.8.0.2 workbook:
    `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`
  - JV-Data 4.9.0.1 workbook:
    `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`
  - SDK 5.0.0 Python structure source:
    `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`
- Both workbooks define the same 161-byte JC record at format rows 1479-1506.
  SDK `JV_JC_INFO` and nested `JC_INFO` independently reproduce every span:
  11-byte header, 16-byte race ID, 8-byte `MDHM`, two-byte `Umaban`, 36-byte
  `Bamei`, two 43-byte before/after blocks, and CRLF.
- The official ordered key has eight components:
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HappyoTime, Umaban)`.
  Current status is `1`. Change-history row 306 removes historical status `0`
  on 2003-07-11; the existing central status ledger already represents the
  strict-before boundary. Status `0` is therefore an old exact-key command,
  not a current realtime deletion signal.
- Code table 2303 defines apprentice codes `0,1,2,3,4,9`. Current `9` is the
  female-rider two-kilogram allowance; the history records the 2019 addition
  and later description updates without changing the one-byte physical span.
- The official 0B14 note requires a fetched date snapshot to replace the prior
  date snapshot because a previously announced jockey change can disappear.
  Existing `replace_date_snapshot()` already clears all five change tables by
  date before one 0B14 refresh, so this behavior is preserved rather than
  reimplemented as a synthetic current status `0`.
- Community evidence was used only as corroboration:
  - topic 331 confirms JC is updated in realtime when JRA announces a change;
  - topic 339 confirms cancellation and substitute-rider events can overlap;
  - topic 254 confirms 0B14/date retrieval for the complete change snapshot.
  These do not alter the workbook/SDK key or field domains.

### Independently reproduced starting-SHA failures

- Existing JC-focused selections are false-green: `19 passed, 130 deselected`.
  The physical parser accepts impossible `MonthDay`, unknown `JyoCD`, invalid
  `HappyoTime`, `Umaban=19`, nonnumeric weight/rider code, and unsupported
  apprentice code while returning a normal row.
- `NL_JC` and `RT_JC` omit `HappyoTime` from their primary key. Both regular
  and optimized SQLite imports reported two successful records for two
  announcement times but retained only the later row.
- `KISYU_CHANGE` has no primary key. It retained both different times but
  appended an exact duplicate on reimport and cannot support exact erasure.
- A date-proven historical status-0 row is not routed through the official
  erase writer. Native storage replaced the live row with a status-0 tombstone;
  standard storage appended another row. Both importers reported success.
- Native JC weight columns are documented as kilogram values and are `REAL`,
  but `AtoFutan=580` was stored as `580.0`, not `58.0`; standard storage
  correctly preserves the raw three-byte string.
- JC has no caller validator or strict schema verifier. Realtime caller rows
  bypass body validation, and old seven-key/keyless/wrong-type/additional-
  uniqueness layouts are not rejected before mutation.
- `NL_JC`/`RT_JC` metadata is a hand-written Japanese pseudo-schema that omits
  official columns and the announcement-time key, rather than being derived
  from executable DDL.

- Next safe action: await the two independent read-only audits, aggregate any
  additional findings once, then add one compact JC contract fixture/module
  and demonstrate its negative cases red on this exact starting SHA before
  production implementation.

## Independent base review and aggregated repair scope

- Two independent Codex reviewers completed read-only reviews of exact starting
  SHA `074425a220f33e63b053751b96ce1e5e7cdd1f7e`. Both ended on the same SHA;
  tracked production/tests/docs remained unchanged and this worklog was the
  only untracked path.
- Official-oracle review verdict: `NEEDS_CHANGES`, P0=0/P1=4/P2=2. Critical
  database review verdict: `NEEDS_CHANGES`, P0=0/P1=3/P2=1. Duplicate findings
  were consolidated instead of producing one repair/review cycle per item.
- Accepted P1 groups:
  1. The official ordered identity is eight columns including `HappyoTime`, but
     `NL_JC`/`RT_JC` use a seven-column key and `KISYU_CHANGE` is keyless. The
     same defect affects exact historical status-0 erasure and can make Dual
     report in-sync while backend row counts differ.
  2. JC lacks one shared parser/caller validator. Invalid date, venue, time,
     horse number, weight, jockey code, apprentice code, and CP932/width values
     can reach storage; valid native weights are stored ten times too large.
  3. JC lacks strict pre-mutation schema verification for ordered PK, key
     types/nullability, body capacity/type, harmful replacement constraints,
     PostgreSQL PK readiness, and every Dual target. An incompatible JC table
     can therefore survive while unrelated schema migration occurs first.
- Accepted P2 group: the parser claims 159 bytes/20 fields rather than the
  official 161 bytes/21 spans including delimiter, and tests/docs/metadata do
  not pin the corrected key, unit, erase, snapshot, migration, or semantic
  contracts. Runtime metadata is rebound to executable DDL, so this is not a
  separate missing-column defect; it currently exposes the wrong DDL contract.
- Explicit non-findings/boundaries: physical offsets, CRLF and CP932 envelope,
  the canonical standard owner name, header alias conflict handling, and
  caller-owned normal rollback were correct. The generic PostgreSQL same-key
  operation-statistics discrepancy predates JC and remains a separate later
  iteration. Current 0B14 snapshot replacement remains the current cancellation
  mechanism; historical status 0 is supported only before 2003-07-11 and only
  as an eight-key exact erase.

## Implementation delegation

- This change modifies validators, schema gates, provider ordering, and three
  storage variants, so it meets the high-backtracking-cost criteria for Claude
  Code Fable. Planned model: `--model fable`; session ID:
  `db4794e7-4bb6-4370-943f-11d349f99292`.
- The same session must first add the compact fixture/test contract and execute
  it against the unchanged starting SHA, recording the observed red failures,
  then implement one aggregated repair. Any follow-up for this iteration must
  use `--resume db4794e7-4bb6-4370-943f-11d349f99292`, not a fresh session.
- Next safe command: start that Fable session in this worktree. STOP if the
  client cannot authenticate, if the worktree drifts outside the expected test,
  fixture, worklog, source, and docs paths, or if primary-source ambiguity is
  encountered.

### Claude Code availability result

- `claude --version` reported `2.1.233`. Fable was started with session ID
  `db4794e7-4bb6-4370-943f-11d349f99292`, but the client returned
  `Login expired` before it could read, edit, or execute the requested work.
- The failed login is not review or implementation evidence. No Claude-origin
  repository change exists. Per the authorized fallback, Codex will implement
  the already aggregated contract and independent Codex reviewers will review
  the resulting frozen candidate. If Claude authentication is restored during
  this same iteration, only `--resume db4794e7-4bb6-4370-943f-11d349f99292`
  may be used.

## Red-first evidence on the unchanged production implementation

- Added the compact official fixture `jc_contract_4901.json`, its fixture-index
  entry, and `tests/test_jc_official_contract.py`. No production file had been
  changed when the new contract was first executed.
- Command (external basetemp, cache and coverage disabled):
  `PYTHONDONTWRITEBYTECODE=1 /home/keiba/work/jrvltsql/.venv/bin/python -m pytest -q -p no:cacheprovider --no-cov --basetemp=/home/keiba/scratch/pytest-jc-red tests/test_jc_official_contract.py`
- Observed result on exact starting SHA production: `24 failed, 2 passed`.
  Representative observed reds were:
  - parser contract lacked `RecordDelimiter` (`20` versus official `21` spans);
  - every malformed key/body case failed with `DID NOT RAISE ValueError`;
  - native state machine retained one status-0 tombstone instead of the other
    announcement, while standard retained four rows instead of one;
  - native weights were `550.0/560.0`, expected `55.0/56.0` kilograms;
  - the legacy seven-key native schema was accepted and mutated;
  - realtime historical erase removed both announcement times instead of one.
- The two paired green controls were the valid header and the historical
  status-boundary/opaque-body shape that the existing status ledger already
  handled. This proves the new contract can reject concrete defects without
  merely making all JC input fail.

## Aggregated implementation and local verification

- Codex implemented the already aggregated repair after Claude Code Fable
  session `db4794e7-4bb6-4370-943f-11d349f99292` could not authenticate. No
  Claude output is counted as implementation or review evidence.
- Production changes are limited to the JC contract and shared entry points:
  the official 161-byte/21-span parser, eight-key native/standard/realtime
  schemas, date-proven historical exact erase, kilogram normalization for
  native `REAL` columns, strict caller validation, schema/constraint preflight,
  metadata, and operational documentation. The current 0B14 date-snapshot
  replacement path is unchanged.
- The compact regression contract covers raw and caller validation, valid
  initial-time/undecided-rider values, historical status/body opacity,
  CP932 byte widths, provider order, exact erase, both batch importers and the
  single-record entry point, owned/caller transactions, native/standard/
  realtime storage, unsafe SQLite/PostgreSQL schemas, Dual target recursion,
  metadata, and the pinned SDK field tree.
- SQLite focused verification after implementation:
  `346 passed, 26 skipped, 10 subtests passed` for the JC contract plus the
  affected parser/status/realtime/schema/migration/metadata suites.
- Fresh disposable PostgreSQL 16 verification, using the repository's actual
  `POSTGRES_*` test contract on port 55441:
  `144 passed, 3 subtests passed`. An earlier attempt used incorrect
  `JLTSQL_POSTGRESQL_*` variable names, fell back to unopened port 5432, and is
  explicitly not counted as code evidence.
- Independent mixed-backend Dual probe used real SQLite and the same fresh
  PostgreSQL 16 instance. With PostgreSQL as primary and as secondary, two
  official announcement times produced exactly two rows on each backend and
  zero import failures.
- The first complete suite exposed three stale common parser positives: the JC
  sample was a blank envelope that the old permissive parser accepted. The
  fixture was corrected to a complete official current JC row; the three
  previously failing assertions then passed (`3 passed, 289 deselected`). The
  validator was not weakened.
- Final complete non-opt-in suite was recorded to JUnit XML and exited 0:
  `tests=3340, failures=0, errors=0, skipped=232` in 68.440 seconds. The exact
  fatal workflow lint command reported `0`, and `git diff --check` passed.
- The full-SHA review has not started yet. Next safe actions are to remove the
  disposable PostgreSQL container, record the final dirty-path set, commit the
  candidate, and submit that immutable full SHA once to both independent Codex
  reviewers. STOP on any production/test drift after the SHA is frozen.
