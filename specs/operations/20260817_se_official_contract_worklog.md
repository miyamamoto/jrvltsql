# SE official parser and storage contract worklog

## Iteration identity

- Started: 2026-08-17 JST.
- Objective: bind the SE horse-per-race record to the pinned current and
  historical official layouts and preserve every distinct official identity
  through native and JRA-VAN-standard storage.
- Minimum scope: SE official/history oracle, parser field/byte contract,
  native and standard column/key/readback, cancellation behavior, fail-closed
  migration, focused SQLite/PostgreSQL/Dual tests, and directly affected docs.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260817_jrvltsql_se_official`.
- Branch: `agent/se-official-contract-20260817`.
- Base / initial HEAD / `origin/master` full SHA:
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`.
- Production/release context: repository version `2.0.0.dev0`; no 2.0 release
  exists and this iteration does not authorize a release.
- Dependency: PR #206 merged as
  `5922a9a28d2d5bc300ed4ebdd873898bc52a3424`, closing executable MCP
  metadata coverage without changing the underlying SE schema.
- Implementer/reviewer policy: Codex with two independent critical Codex
  reviews for a frozen high-risk candidate. Claude Code is unavailable and is
  not counted. No model switch or external reviewer session has occurred.

## Initial observed risk

- Current native documentation and DDL use a seven-column SE key ending in
  `Umaban`; the prior official-workbook audit identified `KettoNum` as an
  additional official SE key field. If confirmed against the pinned sources,
  two provider records that differ only by that field can collapse under
  replacement/upsert semantics while import statistics still report success.
- SE has no dedicated current-layout worklog comparable to RA, and earlier
  schema/parser validation reported SE among the remaining mismatches. No
  assumption is made yet about which parser/storage fields are complete.
- The first action is read-only: derive the current and historical contract
  from pinned official artifacts, compare every parser field and both schemas,
  then reproduce concrete loss before writing a repair test or production code.

## Test and review contract

- Any new or changed key/layout/schema validator must first be shown to fail
  on unchanged production, with a paired canonical positive.
- Reviewer hypotheses will be collected and deduplicated before one repair
  batch. No per-finding SHA/review loop.
- Actual SQLite and fresh disposable PostgreSQL are required for key collision,
  update, cancellation, old-schema no-mutation, and readback. Dual must prove
  both target orientations or document a bounded reason when one is not
  applicable.
- Existing 1.x/wrong-key tables are not silently rewritten. If lossless
  migration cannot be proved, import must stop before schema or row mutation
  and operator backup/recreate/reimport guidance must be documented.

## Next safe command

Locate the pinned 4.8.0.2/4.9.0.1 workbook rows and SDK 5.0 manifest/source for
SE, derive length/field/key/status/history facts independently, then inspect
`SEParser`, `NL_SE`/`RT_SE`, the standard owner, importer mappings, validators,
and existing tests. Record observations before adding red tests.

## STOP conditions

- Stop on candidate/worktree drift outside this iteration.
- Do not infer key membership, legacy support, cancellation semantics, or a
  standard owner from naming alone; require pinned official or executable
  evidence.
- Do not mutate a real provider database, publish a provider/x64 claim, push,
  merge, tag, or release during the audit/red-first phase.
