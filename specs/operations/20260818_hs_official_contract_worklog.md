# HS Official Contract Worklog (2026-08-18)

## Start state

- Objective: audit and, where required, implement the complete official `HS`
  (horse market transaction) contract, with special attention to the 2023
  physical change from 196 to 200 bytes, current-setup behavior, exact keys,
  cancellation semantics, native/standard/realtime persistence, and migration
  safety.
- Minimum scope: `HS` parser, official layout/history oracle, native and JRA-VAN
  compatible schemas/mappings, both batch importers, single-record import,
  realtime handling where supported, executable metadata, public documentation,
  distribution surface, and focused SQLite/PostgreSQL tests. Unrelated record
  types and release publication remain out of scope for this iteration.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_hs_official`.
- Branch: `agent/hs-official-contract-20260818`.
- Base and initial HEAD: `e1fcb810b69c133a3668fe38b8480e31db5e8b27`
  (`origin/master`).
- Preceding iteration: HR PR #211 was squash-merged as
  `e1fcb810b69c133a3668fe38b8480e31db5e8b27`; its candidate worktree and local
  branch were removed, and the remote head branch had already been deleted.
- Related production/release version: repository metadata remains
  `2.0.0.dev0`; no release or 64-bit SDK-support claim is made by this
  iteration.
- GitHub open pull requests at start: zero.
- Start state: new worktree at the exact current `origin/master`, clean index and
  worktree.

## Plan and evidence rules

1. Re-derive the 4.8.0.2 and 4.9.0.1 physical layouts, the 2023 change history,
   SDK 5.0.0 field spans, key and `DataKubun` semantics, and relevant official
   community clarifications. Distinguish official fact from project policy.
2. Compare every logical field and byte span against parser, native/standard
   schema, mapping, importer, realtime, metadata, tests, docs, and package
   contents. Check both the old 196-byte and current 200-byte boundaries rather
   than inferring compatibility from the current length alone.
3. Aggregate concrete findings. For every validator/gate change, add the minimum
   regression to unchanged production and record the actual red result before
   implementation, with paired official-valid controls.
4. Implement one logically complete HS repair batch. Because field-generation,
   history boundaries, key/erase ordering, cross-backend schema verification,
   and migration safety can interact, use Claude Code `--model fable` if the
   configured CLI is available; otherwise record the availability blocker and
   use Codex implementation plus at least two independent critical reviewers.
5. Verify durable readback in SQLite and a fresh disposable PostgreSQL 16
   instance across both importer implementations and supported entrypoints,
   including provider ordering, cancellation, malformed input, wrong schema,
   caller-owned transactions, and rollback/statistics consistency.
6. Freeze the full candidate SHA, run focused and proportionate workflow/package
   gates, obtain aggregated independent critical review, address all actionable
   findings in one batch, then open and merge one PR only after successful CI,
   zero unresolved review threads, and a clean worktree.

## STOP conditions

- Stop on worktree drift outside this tracked worklog or intentional red-first
  test preparation, on uncertainty about an official old/current boundary that
  changes persisted meaning, on unavailable required database/runtime evidence,
  or on any unresolved correctness, data-integrity, security, or operational
  finding.
- Never interpret a skipped PostgreSQL/provider test as a pass. Do not claim
  support for an untested 64-bit SDK/runtime.

## Next safe command

```text
Inspect src/parser/hs_parser.py, native/standard HS schemas and mappings, the
pinned official layout/history fixtures, and tests/test_jvdata490_layouts.py;
then extract the full official HS oracle before editing production code.
```
