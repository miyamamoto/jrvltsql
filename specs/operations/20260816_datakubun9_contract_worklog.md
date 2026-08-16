# DataKubun=9 cancellation contract worklog

## Iteration identity

- Started: 2026-08-16 JST.
- Objective: reconcile cancellation/deletion handling with the current official
  JV-Data `DataKubun=9` contract at every historical and realtime import path.
- Minimum scope: identify which record types define `9` as cancellation,
  distinguish state records that must remain queryable from child/expanded
  records that must be deleted, verify primary-key and rollback behavior, add
  one minimal red-first regression contract, implement the shared policy, run
  focused and necessary broader tests, and complete one reviewed PR/merge.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: dedicated worktree for the branch below; its local absolute path is
  intentionally omitted from this tracked public record.
- Branch: `agent/datakubun9-contract-20260816`.
- Base/initial HEAD/origin master full SHA:
  `d2935dff76a96a1b9e4045f48ea07257663651c0` (PR #187 merge).
- Dependency order: JVOpen dataspec contract PR #187 is merged. Parser framing,
  release versioning/publication, NAR follow-up, and MCP-server follow-up remain
  later iterations.
- Production/release version at start: tag and project version `v1.6.10` /
  `1.6.10`. This iteration does not release.
- Agent/model: Codex only. No Claude session or external coding agent is used.

## Plan and gates

- Re-read the current SDK archive's record-specific DataKubun definitions and
  change history; do not infer one universal meaning from the shared header.
- Recheck current official notices and community/staff discussions for later
  cancellation-semantic changes. Official record definitions remain controlling.
- Inventory parser output, table mappings, primary keys, historical import,
  optimized/native import, realtime upsert/delete, and expanded child-row paths.
- Before changing a check/policy, extend the smallest existing regression test
  and run it against the current production code to prove the fail-open behavior.
  Pair every rejection/deletion case with a retained-state or normal-data case.
- Freeze one candidate, run affected SQLite/PostgreSQL/importer/realtime tests,
  workflow-equivalent checks as warranted, and a bounded actual-acquisition
  proof if this change can alter stored provider data.
- Request one GitHub-native Copilot review, use Codex review, aggregate findings,
  require unresolved threads zero, successful CI, exact local/remote head
  equality, and a clean worktree before merge.
- STOP on conflicting official record definitions, missing keys that make a
  delete ambiguous, partial expanded-row deletion, rollback failure, provider
  cleanup failure, base drift, or any unresolved actionable review finding.

## Starting question

- The repository already has partial realtime tests for `DataKubun=9`, but the
  prior official compatibility audit identified payout/vote/odds families as a
  remaining area requiring record-specific verification. No finding is accepted
  until the current official definitions and every importer path are rechecked.

## Next safe command

- Read the prior audit finding and current import/realtime policies, then extract
  the official `DataKubun` definitions for the implicated record types from the
  cached current SDK materials without changing code.
