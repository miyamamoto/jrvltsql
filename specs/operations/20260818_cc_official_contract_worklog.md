# CC official contract iteration worklog

## Start state (2026-08-18)

- Objective: bind the JRA `CC` course-change record to the pinned official
  physical layout, current status/key/body domains, native/standard/realtime
  storage, exact schema preflight, provider ordering, and transaction safety.
- Minimal scope: `CC` only. Do not fold unrelated HC/HS/TC cleanup or later
  record formats into this iteration.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_cc_official`.
- Branch: `agent/cc-official-contract-20260818`.
- Base and starting HEAD: `6e9a9f500f2353d7b423e5f1e12b07c30275f8d1`
  (`origin/master`, TC PR #214 squash merge).
- Package version: `2.0.0.dev0`; latest published release remains `v1.6.10`.
  This iteration is not itself a release or production-adoption claim.
- Dependency order: TC is merged; CC is the next independent official-contract
  iteration and must be merged before another record format begins.
- Working tree was clean at creation.

## Planned contract and evidence

1. Re-derive the CC byte spans, total length, ordered key, current status,
   history, code domains, and 0B14/0B16 delivery behavior from pinned JV-Data
   4.8/4.9 workbooks plus SDK 5 source/manifest before production edits.
2. Extend or add one compact official-contract test module. Every new or
   changed parser/validator/schema gate must first be red on this exact base,
   with paired provider-valid green cases.
3. Cover direct/factory parsing; caller aliases; native `NL_CC`; standard
   `COURSE_CHANGE`; `RT_CC`; both batch importers; single-record import;
   realtime single/batch; SQLite, fresh PostgreSQL, Dual orientation,
   caller-owned transactions, provider-order replacement, and fail-before-
   mutation migration.
4. Update executable metadata, public support/migration documentation, release
   notes/changelog, and this worklog only where required by proven CC facts.
5. Freeze one full candidate SHA, aggregate independent official-oracle and
   critical reviews, apply at most one consolidated repair batch, then run
   focused/workflow/package gates before one PR and merge.

## Coding-agent choice

- This is complex fail-closed parser/schema/migration work, so the planned
  Claude Code model is `--model fable`, session id
  `839154eb-0967-4b4d-87e4-785f2dfdce64`. The same session will be resumed for
  review repairs. If authentication/quota blocks it, record the failure and use
  Codex implementation plus independent critical reviews rather than silently
  weakening the gate.

### Claude execution result

- Claude Code `2.1.233` was invoked after the start-worklog commit with
  `--model fable` and session id
  `839154eb-0967-4b4d-87e4-785f2dfdce64`. It exited before reading or editing
  the repository because the OAuth session was expired and could not be
  refreshed. The CLI also emitted non-fatal warnings about obsolete `Write`
  permission-rule spellings in the parent settings. No Claude implementation
  or review evidence exists for this iteration. Codex will implement the
  bounded contract with independent official-oracle and critical review as the
  recorded fallback.

## Known preliminary risks (not yet official findings)

- `CCParser` declares `RECORD_LENGTH=50` while its docstring says 48 bytes and
  it does not expose the terminal CRLF field.
- Current parser has no CC-specific key/body validator. Native/realtime schemas
  are nullable, while standard `COURSE_CHANGE` is keyless and nullable.
- Existing status-domain work already restricts current CC to status `1`, but
  all parser/caller/schema boundaries and code domains still require an
  independent official audit.

## Official oracle and red-first evidence

- Pinned JV-Data 4.8.0.2 and 4.9.0.1 `フォーマット` rows 1531–1553 and
  SDK 5 `JV_CC_INFO` agree on a 50-byte layout with 16 spans including CRLF,
  current status `1`, and ordered key
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum)`.
- The current track-code domain is `00`, `10`–`29`, and `51`–`59`; the reason
  domain is initial `0` plus `1`–`4`. Distances retain exactly four ASCII
  digits including `0000`; `HappyoTime` accepts `00000000` or a real
  `MMDDhhmm` value.
- CC was added on 2004-05-25 in Ver.1.1.6. No later physical-layout change was
  found. `0B14` is the date-snapshot source and `0B16` is event-oriented.
- Before production edits, added
  `tests/fixtures/official_layout/cc_contract_4901.json` and one grouped
  `tests/test_cc_official_contract.py` covering the physical oracle, strict
  negatives/initial sentinels, native/standard identity, schema negatives,
  both batch importers, single import, realtime, snapshot replacement, and
  header aliases.
- Red command on unchanged production HEAD
  `da1da38e46ffcda90254108a737820a9b8867015`:
  `python -m pytest -q -o addopts='' tests/test_cc_official_contract.py`.
  Result: `51 failed, 7 passed`. Failures include the missing delimiter span,
  15 malformed raw cases being accepted, nullable/keyless or unsafe schemas,
  standard revision duplication, caller/single/realtime invalid-body
  acceptance, and schema-manager fail-open. Passing controls include official
  initial sentinels, current header aliases, native provider replacement, and
  the existing CC date-snapshot behavior.
- Three independent read-only reviewers audited the committed pre-production
  HEAD. Two completed before the intentional red files appeared and one was
  told those files were primary-owned. Their non-duplicated findings match the
  red contract: strict parser/caller/realtime validation, exact three-table
  storage/preflight, and a CC-specific durable 0B14 assertion are required.

## Next safe command and STOP conditions

- Next: commit this red-first contract, implement the bounded CC parser/schema/
  importer/realtime repair once, then run focused SQLite and fresh PostgreSQL/
  Dual validation before freezing one review candidate.
- STOP on non-worklog drift, a material disagreement among pinned official
  sources, backend divergence that is not explained and tested, or any need
  for destructive/provider action beyond the authorized local test scope.
- Credentials, provider identifiers, and connection strings must not be
  written to this worklog.
