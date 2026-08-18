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

## Known preliminary risks (not yet official findings)

- `CCParser` declares `RECORD_LENGTH=50` while its docstring says 48 bytes and
  it does not expose the terminal CRLF field.
- Current parser has no CC-specific key/body validator. Native/realtime schemas
  are nullable, while standard `COURSE_CHANGE` is keyless and nullable.
- Existing status-domain work already restricts current CC to status `1`, but
  all parser/caller/schema boundaries and code domains still require an
  independent official audit.

## Next safe command and STOP conditions

- Next: invoke the recorded Fable session, independently extract the official
  CC oracle, then write the smallest red-first contract before production edits.
- STOP on non-worklog drift, a material disagreement among pinned official
  sources, backend divergence that is not explained and tested, or any need
  for destructive/provider action beyond the authorized local test scope.
- Credentials, provider identifiers, and connection strings must not be
  written to this worklog.
