# AV Official Contract Worklog

- Started: 2026-08-18 (Asia/Tokyo)
- Objective: audit and repair the AV record parser, native/standard/realtime
  storage identity, validation, migration, erasure, units, metadata, tests, and
  public documentation against pinned official JV-Data sources.
- Minimum scope: AV only. Unrelated record types and generic refactors are
  excluded unless an AV correctness or data-integrity repair cannot be made
  safely without them.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_av_official`
- Branch: `agent/av-official-contract-20260818`
- Base / production master at start:
  `a152045c4bf9c6f9c53f483d2f2cfa0baa05dcb7`
- Dependency: JC official-contract PR #209 merged first at the base SHA above.
- Package version at start: `2.0.0.dev0` (`pyproject.toml` and
  `src/__init__.py`).

## Review and implementation model

- This iteration changes validators, database identity, ordering, and
  fail-before-mutation boundaries, so it is classified as complex under
  `AGENTS.md`.
- Claude Code is requested with `--model fable`. The generated session UUID is
  intentionally not retained because a substring tripped the repository's
  public privacy gate. If authentication or quota prevents
  it from reading or acting, that failure is not evidence and implementation
  continues with Codex as explicitly authorized by the user.
- Findings will be collected and deduplicated before one repair batch. The
  immutable candidate will receive one bounded independent Codex critical
  review plus one official-source oracle review.

## Required sequence

1. Re-derive AV length, all physical spans, ordered official key, status domain,
   status history, provider-spec availability, field units, and cancellation
   behavior from pinned 4.8/4.9 workbooks, SDK manifest/source, and relevant
   official/community discussions.
2. Compare parser, native `NL_AV`/`RT_AV`, standard owner, importer paths,
   realtime paths, metadata, migration verification, documentation, and tests.
3. Add the minimum contract regression and run it on the unchanged base to
   record an actual red result before changing validator/gate behavior.
4. Implement only the aggregated AV repair. Validate SQLite, fresh PostgreSQL,
   Dual orientation, provider order, caller-owned transactions, exact erasure,
   unsafe-schema no-mutation, current/prior boundaries, and durable readback.
5. Freeze a clean full SHA, run the required local/workflow/package gates once,
   request the configured GitHub reviews once, resolve actionable threads to
   zero, and merge only when every blocking gate is green.

## Current state

- New worktree was created from a freshly fetched `origin/master`; start status
  was clean.
- No AV code or test has been changed yet.
- A read-only Codex oracle pre-audit is running in parallel. Its findings are
  provisional until independently reproduced in this worktree.
- Claude Code `2.1.233` was invoked once with `--model fable`, but its OAuth
  session was expired and
  could not be refreshed. It did not read, test, or edit the repository, and no
  Claude output is counted as audit or implementation evidence. Per the user's
  fallback authorization, Codex continues the iteration.
- The pinned 4.8.0.2 and 4.9.0.1 workbooks independently agree on the 78-byte,
  fourteen-field AV layout and the seven-part key
  `(Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)`; `HappyoTime` is
  not a key field. SDK 5.0.0 binds the same root length and nineteen expanded
  leaves.
- Current statuses are `1` and `2`. Historical status `0` is accepted only for
  `MakeDate < 2003-07-11` and means exact physical deletion. The 2021-01-25
  reason-field change altered the initial representation from zero to spaces,
  not the physical layout, so blank and `000` through `003` remain accepted
  when provenance is unknown.
- Independent unchanged-base SQLite probes reproduced the actionable gaps:
  keyless standard storage retained two revisions of one official identity;
  historical status zero became a stored tombstone in both importer modes;
  and caller `RaceNum='1X'` was silently coerced to integer 1 and overwrote a
  valid row. No provider or user data was used by these synthetic probes.
- Red-first evidence on unchanged base
  `a152045c4bf9c6f9c53f483d2f2cfa0baa05dcb7`:
  `.venv/bin/python -m pytest tests/test_av_official_contract.py -q
  --basetemp=/tmp/jrvltsql-av-red --no-cov` produced `20 failed, 11 passed`
  before stopping at `--maxfail=20`. Representative failures were
  `DID NOT RAISE ValueError` for all seven malformed raw-field cases, native
  durable count `1` instead of exact erase `0`, and standard durable count `3`
  instead of `0`. The first oracle failure was an independently corrected test
  transcription of SDK `MDHM`'s four scalar leaf names; it was not counted as
  production evidence.
- The aggregated implementation now adds strict AV raw/caller validation,
  seven-column `NOT NULL` identity DDL for native/realtime/standard storage,
  exact historical erase routing, all-target schema preflight, and realtime
  dictionary validation. The first post-repair AV run passed `34` tests; the
  expanded unsafe-schema matrix and public documentation are now being checked
  before the candidate is frozen.
- SQLite focused verification after the repair passed `363 tests`, skipped `9`
  opt-in tests, and passed `10` subtests across AV, current-record framing,
  realtime, schema/index/metadata, importer, and DataKubun entry contracts.
- A fresh disposable PostgreSQL 16 instance was used with no provider or user
  data. The final AV contract passed `65/65`: native/standard, DataImporter/
  OptimizedDataImporter/single-record, owned/caller transactions, status
  `1 -> 2 -> historical 0`, wrong type, short text, extra UNIQUE, deferrable
  primary key, and both SQLite/PostgreSQL Dual orientations. A broader actual-
  PostgreSQL run including the adjacent SE/WE/JC official contracts passed
  `318/318`. The exact container was removed and an exact-name listing was
  empty afterward.
- Workflow-equivalent local verification on the final pre-review tree passed:
  `scripts/validate_test_gate.py` reported `TEST GATE PASS`, followed by
  `3126 passed, 244 skipped, 14 deselected, 21 subtests passed` with `78%`
  line coverage. No production or test semantics changed after that run; a
  broad Black rewrite was deliberately undone, and Python AST equality was
  checked for every restored file before the focused suite was replayed.
- The final post-format focused AV/parser set passed `465/465` with `18`
  PostgreSQL-only skips. Fatal flake8 (`E9,F63,F7,F82`) reported zero errors,
  `uv lock --check` passed, and `mkdocs build --strict` completed successfully.
  Ruff import-order comparison has one pre-existing finding in
  `schema_jravan.py`; the same finding is present in the unchanged base and
  this iteration adds no Ruff import-order debt.
- Fresh PEP 517 wheel and sdist build succeeded as `2.0.0.dev0`.
  `scripts/check_distribution_contents.py` passed both artifacts and
  `scripts/smoke_distribution_init.py` passed the extracted wheel. The tracked
  `specs/`, this worklog, and official-layout fixtures remain excluded from the
  distributable artifacts.

## STOP conditions

- Stop before mutation if official key/status/unit semantics remain ambiguous.
- Stop on worktree drift outside this worklog before implementation starts.
- Stop before merge on failed required test, unsafe schema mutation, durable
  count/stat mismatch in the AV path, unresolved review thread, dirty worktree,
  or absent exact-SHA evidence.
- Do not claim 64-bit support without an installed official x64 SDK runtime test.
- Do not include private implementation provenance or prohibited internal
  environment identifiers in tracked files, PR text, logs, or artifacts.
