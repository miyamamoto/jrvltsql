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

## Aggregated pre-implementation review (2026-08-18)

- Review target: exact committed production base
  `e1fcb810b69c133a3668fe38b8480e31db5e8b27`; the review-start worklog commit
  is `73d05053d99883db54e765a6a3a228e868a62d04` and contains no production or
  test change.
- Three independent review passes agreed on the actionable boundary:
  - current SDK 5.0.0 `HS` is exactly 200 bytes and the historical 196-byte
    layout must remain rejected by the current-only parser;
  - the parser and caller-owned dictionaries need one shared current-field
    validator, while `DataKubun=0` non-key bytes are opaque by project policy;
  - native `NL_HS` and standard `SALE` need the exact ordered
    `(KettoNum, SaleCode, FromDate)` identity, required nullability and exact
    capacities, with a dedicated cross-backend preflight before any mutation;
  - status-0 must erase in provider order, statistics must count provider
    operations, and unsupported realtime `HS` must not write the local cache;
  - a nonempty existing HS table without current-layout provenance is unsafe
    and requires a rebuild/reimport instruction rather than an additive
    mutation. Stored `HansyokuFNum`/`HansyokuMNum` value length is explicitly
    not generation evidence: the current ten-byte fields can legitimately hold
    an eight-digit registration value followed by provider space padding.
- Official fact and project policy are kept distinct: current length, field
  spans and the three-part identity are fixture-backed official contracts;
  accepting arbitrary non-CP932 bytes in non-key status-0 body ranges is the
  repository's exact-erase/opaque-body policy, not a claim about the provider
  specification.
- Generation detection must use the physical raw length/data-spec provenance or
  a current-parser marker attached only after current 200-byte validation.
  A value-length scan is forbidden because it would reject official current
  parent-registration values after the parser strips their padding.
- Claude Code `--model fable` was selected because the change combines a
  validator, provider ordering and cross-backend migration gates. The local
  Claude runtime cannot authenticate in this environment, so no Claude session
  was started and there is no resumable session id. Per the recorded fallback,
  Codex will implement the aggregated batch and the immutable candidate will
  still require independent critical review before release.
- Red-first rule: add one compact `tests/test_hs_official_contract.py`, run the
  defect-bound cases against unchanged production, and record the actual
  failures before editing `src/`.

## Red-first evidence

- Production remained byte-identical to
  `e1fcb810b69c133a3668fe38b8480e31db5e8b27` when the new compact module was
  first run with the repository `.venv` (Python 3.13.5):
  `13 failed, 1 passed`. The failures independently bind missing parser field
  spans, five caller-validation defects, executable schema identity/nullability
  drift, and native/standard exact-erase failure through DataImporter,
  OptimizedDataImporter and single-record import.
- The first opaque-body control used byte `0xff`, which Python's CP932 codec
  accepts and therefore was not a valid negative. It was corrected before any
  production edit to an incomplete `0x81` lead byte followed by ASCII space;
  the corrected case is rerun separately below.

## Codex implementation and verification (2026-08-18)

- Implemented the aggregated repair without starting a Claude session because
  the selected Fable runtime could not authenticate. Production now accepts
  only the official current 200-byte physical layout, derives all 15 logical
  field spans directly, validates the shared caller/raw contract before any
  mutation, and treats status-0 non-key bytes as opaque under the documented
  project exact-erase policy. The obsolete 196-byte layout remains rejected.
- Native `NL_HS` and standard `SALE` now share the exact ordered
  `(KettoNum, SaleCode, FromDate)` identity, required widths/nullability and a
  trusted `CurrentLayoutVersion = 200` marker. Preflight recursively checks
  SQLite/PostgreSQL/Dual stores for incompatible types, short capacities,
  nullable required columns, extra replacement keys, unusable PostgreSQL
  primary keys and unmarked nonempty old stores before schema or DML mutation.
  No parent-registration value-length heuristic was introduced.
- Provider-operation accounting and ordered exact erase are wired through
  DataImporter, OptimizedDataImporter and single-record import. Unsupported
  realtime HS is rejected before cache mutation. Executable metadata, public
  data-support documentation and release notes describe the current-only and
  operator rebuild boundaries; physical `Field15` is named
  `RecordDelimiter`.
- Actual red-first evidence against unchanged production is recorded above.
  The finished compact contract module was then exercised against SQLite and
  a dedicated fresh PostgreSQL 16 container:
  `77 passed in 5.71s`. This covers native/standard, both batch importers and
  single-record import, caller-owned/importer-owned transactions, ordered
  status 1 then 2 then 0 operations, statistics, malformed later records,
  strict schema failures, Dual preflight and unsupported realtime cache
  behavior.
- Adjacent existing regressions remained green:
  `tests/test_current_record_validation.py tests/test_all_schemas.py
  tests/test_realtime.py` => `201 passed, 9 subtests passed in 4.91s`; metadata
  and mapping tests => `28 passed, 7 skipped in 3.36s` (the skips are the
  optional PostgreSQL metadata group, not substitutes for the dedicated live
  PostgreSQL contract run above).
- Static checks on the new parser and compact contract module are green:
  Ruff, Black check, and `git diff --check`. No commit, push, PR or GitHub write
  was performed. The next step is an independent critical review of the
  resulting dirty implementation candidate before any release action.

## Main-agent refinement and pre-candidate gate (2026-08-18)

- Tightened both executable schemas so every interpreted numeric/current-body
  field is `NOT NULL`, while the two provider name fields remain nullable.
  Removed acceptance of Python `date` objects at the shared caller boundary:
  HS date fields remain exact eight-character provider/canonical strings.
- Added an independently tracked compact `hs_contract_4901.json` fixture and
  bound it to the SDK 5.0.0 manifest, the two official physical generations,
  all 15 current logical spans, the three-part identity and the current setup
  policy. The storage readback matrix now asserts every interpreted field, and
  the provider-order matrix uses two rows differing only in `FromDate` to bind
  the third key component.
- Added an exact database `CurrentLayoutVersion = 200` CHECK verifier for
  SQLite/PostgreSQL/Dual. A missing or tautologically absent marker constraint
  is rejected; the only additive exception remains an empty native table that
  lacks the marker column and can receive the exact schema definition safely.
- A final self-audit found that the shared exact-delete function validated HS
  status 0 correctly but still coerced every non-key body value before DELETE.
  A caller body object whose `__str__` raises demonstrated the missing opacity
  on the pre-fix candidate: the focused test failed with
  `RuntimeError: opaque HS body was inspected` and the target row remained.
  The function now projects the already-validated official identity before
  type coercion. The same regression then passed and the target row was erased.
- Final pre-candidate tests after that repair:
  - SQLite HS contract: `60 passed, 28 skipped` (all skips are the explicitly
    opt-in PostgreSQL parameter group).
  - Fresh disposable PostgreSQL 16 HS contract: `88 passed`; this includes both
    schemas, both batch importers, single-record import, both transaction modes,
    exact erase/order/statistics, rollback, unusable PK and marker constraints.
  - Adjacent schema/parser/realtime/metadata/oracle/migration selection:
    `411 passed, 7 skipped, 9 subtests passed`.
  - Adjacent official-contract selection affected by the shared delete-key
    projection: `577 passed, 124 skipped`; skips are optional PostgreSQL groups
    that were not used as the HS live-PostgreSQL evidence above.
- Workflow-equivalent fatal checks are green: `TEST GATE PASS`, fatal Flake8
  reports `0`, `uv lock --check` succeeds, strict MkDocs succeeds, Black/Ruff
  on the changed parser/contract test succeed, and `git diff --check` succeeds.
- The dedicated PostgreSQL container `jrvltsql-hs-main-review` was removed and
  an exact-name `docker ps -a` check returned no match. The worktree remains
  intentionally dirty only with this aggregated implementation batch. Next:
  commit/push one immutable candidate, then obtain two independent critical
  reviews of that exact full SHA before opening or merging a PR.
