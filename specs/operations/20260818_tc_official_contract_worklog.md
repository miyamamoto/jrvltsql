# TC official contract iteration worklog

## Start state (2026-08-18)

- Objective: bind the JRA `TC` start-time-change record to the pinned official
  physical layout, status/key/body domains, native/standard/realtime storage,
  exact schema preflight, provider ordering, and durable transaction semantics.
- Minimal scope: `TC` only. The adjacent `CC` record remains a separate later
  iteration even where implementation helpers may ultimately be shared.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_tc_official`.
- Branch: `agent/tc-official-contract-20260818`.
- Base and starting HEAD: `282e03a5cba06fdc42d4d651ee7624b27dadad01`
  (`origin/master`, HC PR #213 squash merge).
- Package version: `2.0.0.dev0`; latest published release remains `v1.6.10`.
  This iteration is not itself a release or production-adoption claim.
- Dependency order: HC is merged; TC is independent of the later CC iteration.
- Working tree was clean at creation.

## Planned contract and evidence

1. Re-derive the TC byte spans, total length, ordered key, status domain,
   history, and delivery context from the pinned JV-Data 4.8/4.9 workbooks and
   SDK 5 source/manifest before changing production code.
2. Extend or add one compact official-contract test module. New/changed
   validators and schema gates must first be shown red on the exact base, with
   paired valid green cases. Avoid a test function per reviewer hypothesis.
3. Cover direct/factory parsing; caller aliases; native `NL_TC`; standard
   `HASSOU_JIKOKU_CHANGE`; `RT_TC`; both batch importers; single-record import;
   SQLite, fresh PostgreSQL, Dual orientation, caller-owned transactions,
   exact-key coexistence/update behavior, and fail-before-mutation migration.
4. Update executable metadata, public support/migration documentation, release
   notes/changelog, and this worklog only to the degree required by the proven
   TC contract.
5. Freeze one full candidate SHA, aggregate independent official-oracle and
   critical reviews, apply at most one consolidated repair batch, then run the
   required focused/workflow/package gates before opening and merging one PR.

## Coding-agent choice

- Complex fail-closed validator/schema/migration work qualifies for Claude
  Fable under `AGENTS.md`. Planned CLI model is `--model fable` with session id
  `eabbe5e2-34f9-4fe1-b4f9-a85d3976f230`; the same session will be resumed for
  review repairs. If Claude authentication/quota prevents useful execution,
  the failure will be recorded and Codex will implement with independent Codex
  reviews rather than silently changing the gate.

### Claude execution result

- Claude Code `2.1.233` was invoked with `--model fable` and session id
  `eabbe5e2-34f9-4fe1-b4f9-a85d3976f230` after the start-worklog commit. It
  exited before reading or editing the repository because the OAuth session was
  expired and could not be refreshed. The CLI also printed non-fatal warnings
  about obsolete `Write(...)` permission-rule spellings in the parent Claude
  settings. No Claude implementation or review evidence exists for this
  iteration. Codex will implement the bounded contract and require independent
  official-oracle and critical Codex review as the recorded fallback.

## Known preliminary risks (not yet official findings)

- Current `TCParser` has no TC-specific key/body validator.
- Native/realtime tables use a six-column race key while standard
  `HASSOU_JIKOKU_CHANGE` currently has no primary key; official key membership
  must be re-derived before deciding whether either layout is correct.
- Key columns and field types are not currently protected by a TC-specific
  strict schema verifier.

## Next safe command and STOP conditions

- Next: extract the TC workbook/SDK oracle and compare it mechanically with
  parser/schema/importer/realtime mappings, then write the smallest red-first
  contract before production edits.
- STOP if HEAD/worktree drifts outside this worklog, pinned official artifacts
  disagree materially, a required real-backend proof cannot be isolated, or a
  destructive/provider operation would be required without new authority.
- No credentials, provider identifiers, or connection strings belong in this
  worklog.
