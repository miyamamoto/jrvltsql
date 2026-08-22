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
  combination `SanrentanHyo` in live statuses `2/4/5/9` to be exactly eleven
  ASCII digits.  Status 0 intentionally returns after key validation because
  delete bodies are opaque, and a totals-only status-9 snapshot is already
  supported.  No code change is justified until an exact combination-bearing
  blank-vote provider shape is established.
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

## Read-only evidence closure

- The pinned current workbook
  `JV-Data仕様書_4.9.0.1.xlsx` has SHA-256
  `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`.
  Its H6 format rows 370 and 382--385 independently confirm status
  `0/2/4/5/9`, 4,896 21-byte trifecta slots, a six-byte combination, an
  eleven-byte vote and a four-byte favourite order.  The vote description
  distinguishes `ALL0` (pre-sale cancellation/no votes) from spaces
  (unregistered).  Special-note rows 255 and 276 say H1/H6 status 9 is
  supplied only after prior vote-count data.  These facts establish that an
  eleven-space vote is an official field value, but they do not establish
  that a combination-bearing H6 status-9 row uses that value.
- The pinned official SDK document
  `JRA-VAN Data Lab.開発ガイド_4.2.2.pdf`, obtained from the official SDK
  distribution page <https://jra-van.jp/dlb/sdv/sdk.html>, has SHA-256
  `1792c6b6d3e06b7f782b402e924d61da0a4c8ef5c10b0cc520be35882bd7db57`.
  Section 1.2.2 states that provider data is compressed and encrypted and
  that software receives decrypted records from JV-Link.  The retained
  retained H6 provider object is consequently recorded only by anonymized
  metadata (2,442,161 bytes, SHA-256
  `14e28d4d366e0630b2d243972095f7c021a37c577e3ab4ac030c11cd123318e4`);
  it is not treated as an offline-decodable record source.  Calling
  `JVOpen`/`JVRead` merely to inspect it would violate this iteration's
  no-provider-acquisition/read-state-mutation boundary.
- A second read-only scan of every current local `RACE` cache member found
  110 v2 files, 135,354 well-formed length-prefixed records, zero malformed
  files, zero H1 status-9 records and zero H6 status-9 records.  No raw body or
  race identity was emitted.
- A read-only query of the active development PostgreSQL tables found zero
  `DataKubun=9` rows in both `public.nl_h6` and `public.rt_h6`.  The older
  tracked registered-data replay remains useful proof that one H6 status-9
  record expanded to 4,896 rows, but because its vote-byte distribution was
  not retained it cannot close the present question.
- Current production still accepts totals-only H6 cancellation snapshots,
  treats status 0 as key-only opaque deletion, and requires an eleven-digit
  vote for every combination-bearing live-status row.  No new provider shape
  contradicts that fail-closed boundary.

## Decision and verification

- This iteration is audit-only.  No parser, importer, schema or test is
  changed.  Permitting blank combination votes would broaden accepted input
  on an official possibility without the required provider instance; that is
  specifically disallowed by the STOP contract.  H6 therefore remains strict.
- This is not evidence that H6 can never emit the H1 shape.  If a future
  provider run returns an H6 status-9 combination with an empty normalized
  vote, that exact failure plus the original raw eleven-byte class is the
  trigger for one paired red-first H6 regression.
- The pre-closure worklog commit was
  `4f1b4c5c632690f02b8a161ee32985648ba74c26`; evidence closure was reviewed at
  `9d184da7e83d93a910aed01390107e7a9790ba17`, both based on
  `1ee2ccb3ee5c104a15177f57281004395e669bb7`.  The exact final PR head is
  intentionally recorded in the PR description and GitHub metadata because a
  tracked file cannot self-reference the commit that contains itself.
- The first local focused command accidentally selected an external Python
  3.10 `pytest` after `uv` had created a different environment and stopped at
  collection because Python 3.10 has no `enum.StrEnum`; it is not counted as a
  candidate test result.  All generated environment/coverage/cache artifacts
  were removed.  Re-running from the existing repository Python 3.13.5
  environment with the current worktree on `PYTHONPATH` passed the bounded H6
  contract: `158 passed, 13 skipped` (PostgreSQL opt-in cases excluded).  No
  ignored artifact remained in this worktree.

Next safe action: commit and push this audit conclusion, update PR #241 to the
exact candidate, make it ready for the repository's one native review, and
merge only after CI, review, unresolved-thread count and clean-worktree gates
are green.  Then release the next `2.0.0.dev` from the resulting master before
retrying the development provider through `ingestctl`.
