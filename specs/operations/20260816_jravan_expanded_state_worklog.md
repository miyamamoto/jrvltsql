# Standard-schema expanded state worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: make the JRA-VAN standard-schema representation of expanded
  H1/H6/O1-O6 records preserve the official physical-record header state,
  including cancellation `DataKubun=9` and erroneous-record erase `0`, without
  weakening normalized native storage.
- Minimum scope: inventory the current split header/child schemas and mappings,
  compare them with current and immediately prior official layouts, define a
  backward-compatible storage and migration contract, prove the present loss
  with a red-first test, implement it in ordinary and optimized importers, and
  complete one reviewed PR/merge.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated worktree for the branch below; its local absolute path is
  intentionally omitted from this tracked public record.
- Branch: `agent/jravan-expanded-state-20260816`.
- Base/initial HEAD/origin master full SHA:
  `71178e29e2715c3056fd39ae265c7dbed80298b2` (PR #188 merge).
- Dependency order: cancellation mutation semantics PR #188 is merged. Parser
  framing, final acquisition/release, NAR, and MCP-server iterations follow.
- Production/release version at start: tag and project version `v1.6.10` /
  `1.6.10`. This iteration does not release.
- Agent/model: Codex only. No Claude session or external coding agent is used.

## Plan and gates

- Re-read the current and immediately prior official H1/H6/O1-O6 physical
  record definitions and identify header fields that apply to all expanded
  children.
- Inventory `JRAVAN_SCHEMAS`, native-to-standard table mappings, migration code,
  ordinary/optimized importer routing, primary keys, and existing databases.
- Prefer an additive compatible representation. STOP if the only design would
  silently reinterpret existing child rows, destroy keys, or require an
  ambiguous backfill.
- Add the smallest failing test before changing production code. Pair the
  missing-state rejection with normal/cancellation storage and explicit erase.
- Run focused SQLite and isolated PostgreSQL tests, workflow-equivalent checks
  warranted by the change, and a bounded acquired-record replay at the exact
  candidate SHA.
- Request one GitHub-native Copilot review, perform Codex review, aggregate
  findings, require CI success, unresolved threads zero, local/remote full SHA
  equality, and a clean worktree before merge.

## Starting observation

- Native NL/RT schemas persist `DataKubun` on every normalized child row.
  The legacy standard-schema mapping routes expanded records to child tables
  whose schemas omit physical-header state, and the importer does not currently
  materialize the corresponding header tables. The exact scope, existing table
  compatibility, and safest repair are not yet assumed.

## Next safe command

- Read the standard schemas, mappings, migration helpers, and expanded importer
  paths without changing code; then compare their field ownership with the
  official H1/H6/O1-O6 layouts.
