# H6 status-9 vote-shape audit worklog — 2026-08-22

## Start state and objective

- Objective: before repeating the multi-hour five-year JRA `RACE` setup,
  independently determine whether official/provider H6 race-cancellation
  (`DataKubun=9`) records can retain a combination while returning the
  eleven-byte vote field as spaces, analogous to the H1 provider shape fixed
  by PR #240.  Do not relax H6 on analogy alone.
- Minimum scope: pinned current official H6 layout and cancellation note,
  existing registered-data replay evidence, available local raw-cache evidence,
  the current H6 parser/importer contract, and one bounded negative/positive
  reproduction if a real shape is established.  H1, H6 schema/key/storage,
  other record families, runtime dialog behavior, release versioning and the
  development provider retry are out of scope.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260822_jrvltsql_h6_status9_audit`.
- Branch: `audit/h6-status9-vote-20260822`.
- Base/start HEAD: `1ee2ccb3ee5c104a15177f57281004395e669bb7`, exact
  fetched `origin/master`, the squash merge of H1 PR #240.
- Related runtime merge: `miyamamoto/jrvltsql-wine-runtime` PR #30, merge
  `4851ef922bd927b541f8d74d88122181a6b1dcb5`.
- Implementation/audit agent: primary Codex.  No Claude session is used for
  this bounded evidence audit; if a data-contract change becomes necessary,
  its red-first implementation remains in this same iteration/worktree.

## Known evidence at start

- Pinned JV-Data Ver.4.9.0.1 gives H6 the official statuses
  `0/2/4/5/9`, an eleven-byte vote field, and the same cancellation-operation
  note as H1: status 9 is supplied after vote-count data was previously
  provided.
- Existing tracked registered-data inspection recorded at least one status-9
  H6 physical record expanding to all 4,896 ordered trifecta combinations.
  That older replay proved owner/child retention and status-0 removal but did
  not record whether each raw vote span was digits or spaces; it predates the
  present strict H6 caller validator and therefore is not proof that the
  current validator accepts the provider shape.
- Current `H6Parser.validate_current_fields()` requires every non-total
  combination `SanrentanHyo` to be exactly eleven ASCII digits.  A totals-only
  status-9 snapshot is already supported.  No code change is justified until
  an exact combination-bearing blank-vote provider shape is established.
- Read-only scan of the 110 current `RACE` v2 raw-cache files (135,354
  length-prefixed records) found zero H1 or H6 status-9 records.  This is a
  negative availability result, not evidence that the shape cannot occur.

## STOP and evidence contract

1. Never infer H6 semantics solely from the H1 fix.  Require pinned official
   field semantics plus a provider/registered raw or normalized H6 instance.
2. Do not disclose race identity or raw provider bodies.  Record only status,
   field-shape counts, byte-class counts, hashes, and aggregate outcomes.
3. If a valid blank-vote shape is found, extend the existing H6 contract test
   once and prove it red on this exact base before changing production.  Pair
   it with statuses 2/4/5 and non-space whitespace negatives.
4. If no stronger evidence can be recovered, finish this as an audit-only
   worklog and retain the existing fail-closed validator.  A future provider
   failure then supplies the missing exact evidence; do not preemptively widen
   acceptance.
5. Stop on worktree drift, provider/DB mutation, a failed unrelated gate, or
   any need to start a new JV-Link acquisition.  This iteration is read-only
   until an evidence-backed red test exists.

Next safe action: inspect the pinned H6 layout fixture/workbook-derived oracle,
the registered-data replay history, and local immutable provider/cache sources
for an anonymized status-9 vote-byte distribution.  Then decide explicitly
whether production/test changes are justified.
