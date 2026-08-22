# JVOpen bounded setup worklog — 2026-08-22

## Objective and minimum scope

Repair the JRA RACE official-setup transport so a requested date range is
bounded at JVOpen rather than fetched as one unbounded tail. The minimum
iteration is:

1. send the official start/end `fromtime` form for end-capable setup specs;
2. preserve the official start-only form for specs that forbid an end point;
3. make long option-4 setup partitioning truly bounded and resumable without
   weakening transaction, cache-complete, parser-rejection, or failure
   semantics; and
4. correct CLI/docs claims so operators do not mistake a client-side filter
   for a provider download bound.

Do not change record parsers, schemas, service-key/registration handling,
provider identity, realtime collection, production release `2.0.0`, or KPS
model/feature work in this iteration. Do not run another live setup until the
code is reviewed, merged, released as a new `2.0.0.dev*` wheel, and pinned by
the development runtime.

## Repository and immutable start state

- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260822_jrvltsql_bounded_setup`
- Branch: `fix/jvopen-bounded-setup-20260822`
- Base / initial HEAD / `origin/master`:
  `3c4650dfceb96df89808291ef29191de506ef85f`
- Related installed/release version: `2.0.0.dev2`
- Upstream runtime image used for the reproducer:
  `kps-jra-collector-dev:e97924fd32049d41f77bafb8634dd32aedc06d17`
- KIR operational evidence PR: #167, current evidence head
  `7495b6eee9fbef965ceb20af90f7a306e29f3884`
- This worktree started clean. The separate checkout `/home/keiba/jrvltsql`
  already contained unrelated uncommitted realtime changes and must not be
  edited or cleaned by this iteration.

## Observed failure and official oracle

- A RACE option-4 setup for 2025-08-20..2026-08-19 completed in about
  32 minutes 37 seconds with `Fetched=135354`, `Parsed=22555875`,
  `Imported=22555874`, `Failed=0`.
- The next RACE option-4 scope, 2024-08-20..2026-08-19, remained live for the
  exact configured 7,200 seconds but returned no JVOpen response. It exited 1
  with `Bridge response timeout (7200.0s)`, counters zero, empty cache
  checkpoints, no cache commit, no success progress ledger, unchanged durable
  DB rows, and unchanged provider-local Data Lab files.
- Pinned official oracle:
  `JV-Linkインターフェース仕様書_4.9.0.1(Win).pdf`, SHA-256
  `3167d5c98d8db78321a983cd2d897e1b5a9f42f141490f9ba817ca0dcf9d2364`.
  Pages 17--20 define `fromtime` as either one start timestamp or start/end
  timestamps joined by `-`. RACE is not in the explicit list that forbids an
  end timestamp. The same section documents options 3/4 and setup
  interruption/resume.
- Exact `2.0.0.dev2` constructs only
  `fromtime = f"{from_date}000000"`; `to_date` is a client-side record filter.
  Its option-3 yearly recursion therefore repeats all later provider data, and
  option 4 is deliberately left as one unbounded open to avoid that O(n^2)
  repetition. The two-hour failure is consequently not evidence that a
  bounded yearly setup was attempted.

## Red-first and implementation contract

Before production changes, add the minimum regression coverage and run it on
this exact base. It must prove at least:

- bounded RACE setup calls JVOpen with
  `YYYYMMDD000000-YYYYMMDD235959` (base must fail because it sends only the
  start timestamp);
- an end-forbidden setup spec such as DIFN remains start-only (paired green);
- option-4 long ranges partition into exact, nonoverlapping bounded chunks and
  do not repeat the open tail;
- a failed later chunk is not recorded complete and cannot silently discard or
  double-count an already durable earlier chunk; and
- invalid/missing dates fail before JV-Link or database mutation.

Record the exact pre-fix failure in this worklog and in the commit/PR evidence.
Do not add one test per reviewer hypothesis; extend the existing historical or
batch-processor contracts with the smallest table/parameterized coverage that
actually turns red.

## Coding-agent session

- Claude Code version: record when started.
- Model: `--model fable`, selected because this changes a fail-closed transport
  gate plus range partition, transaction order, cache completion and resume
  semantics.
- Session ID: `ecb0bbe6-e0b1-4923-b214-07698693c5a7`
- Continue this same session with `--resume` for review fixes in this
  iteration. If context becomes too long, summarize here before starting a new
  session.

## STOP conditions

- Stop on worktree drift not created by this iteration.
- Stop before any live provider operation, runtime image/wheel publication,
  release tag, production deployment, Wine-prefix reset, registration change,
  service-key output, or KIR/KPS mutation.
- A missing official answer, unbounded provider call, cache range falsely
  complete after failure, lost previously committed chunk, or transaction
  ownership ambiguity is a blocker, not a reason to loosen the gate.

Next safe command: commit and push this initial worklog, then start Claude Code
`2.1.233` with `--model fable --session-id
ecb0bbe6-e0b1-4923-b214-07698693c5a7` in this worktree. Require it to inspect
the official evidence and current tests, run the red test against exact base,
implement the smallest coherent repair, run focused tests, update this worklog,
and stop before commit/push/PR so the primary agent can inspect the result.
