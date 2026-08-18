# HN official-contract closure worklog

## Start state (2026-08-18)

- Objective: close the remaining HN breeding-horse master contract before the
  `2.0.0.dev0` development-test prerelease.
- Minimal scope: HN official key/body validation, status-0 exact physical erase
  and provider ordering/statistics, strict native `NL_HN` and standard
  `HANSYOKU` schema preflight, backend/Dual evidence, and directly affected
  docs/tests. Do not add an `RT_HN` table; HN is an accumulated BLDN master.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_hn_official`.
- Branch: `agent/hn-official-contract-20260818`.
- Base and starting HEAD: `8408bcf7e3580b72f25c027a3a4e0a138343447b`
  (`origin/master`, inventory PR #216 squash merge).
- Production/release version under development: `2.0.0.dev0`; no prerelease
  has been published.
- Starting worktree was clean.
- Implementer: Codex. No Claude Code session has been started for this
  iteration.

## Prior completed boundary

- PR #172 / merge `6dc55078dba33a7f4582d67e816276c25be2700e`
  corrected the official current 251-byte layout, rejects the obsolete
  245-byte physical record, preserves all native and standard fields, and
  establishes `HansyokuNum` as the native/standard key.
- The current parser/layout work is retained. This iteration does not reopen
  already-proved offsets merely because the earlier test module is not named
  `test_hn_official_contract.py`.

## Confirmed gaps at start

- HN is absent from `_OFFICIAL_ERASE_KEY_COLUMNS`, the provider-order set, and
  official-operation statistics. Native and standard `1 -> 2 -> 0` therefore
  leave a status-0 tombstone instead of deleting the keyed record.
- `validate_import_record_header()` performs only shared header/status checks
  for HN. Caller-built key-only rows, missing body, and malformed key values can
  reach storage.
- HN has no dedicated exact native/standard schema verifier. Generic additive
  verification is insufficient for types/nullability, generated or extra
  columns, harmful constraints, and PostgreSQL PK usability.
- HN is accumulated-only (`BLDN`); realtime storage/processing is N/A and must
  remain explicitly rejected/not routed rather than creating a new table.

## Red-first and implementation plan

1. Add one compact HN official-contract module by extending/reusing the existing
   layout builder. First run it against this base and record the actual red
   failures for:
   - valid live caller body and malformed/missing key/body;
   - exact-key `1 -> 2 -> 0` erase/order/statistics across DataImporter,
     OptimizedDataImporter, and single-record entry where supported;
   - unsafe native/standard schemas, including extra required/generated or
     uniqueness/constraint/PK defects, rejected before mutation;
   - SQLite, fresh PostgreSQL, and Dual orientation boundaries.
2. Implement the smallest shared HN validator, physical erase dispatch, strict
   schema verifier, and transaction-safe preflight needed to turn those reds
   green. Status 0 validates only header/key and treats the body as opaque.
3. Run affected focused tests, fresh PostgreSQL and Dual probes, exact full-SHA
   review, GitHub checks, and unresolved-thread-zero gate. Aggregate findings
   before one repair batch.
4. Merge the HN PR, clean this worktree/branch, fetch latest master, then begin
   SK in a new worktree.

## Red-first evidence (2026-08-18)

- Added the compact uncommitted regression module
  `tests/test_hn_official_contract.py` before modifying production code.
- Command (repository-supported Python 3.12 environment):
  `uv run --python 3.12 --extra dev python -m pytest -q tests/test_hn_official_contract.py`.
- Base result at full SHA
  `689531763cae6292dfa1d761fdddd88d6b64314b`: **24 failed, 1 passed**,
  exit code 1.
  - four parser-domain negatives were accepted;
  - four caller-built key/body/alias negatives were accepted;
  - all eight batch native/standard, owned/caller-owned erase paths left a
    stored status-0 tombstone;
  - all four single-record erase paths left the row stored;
  - all four unsafe-extra-column schemas reached normal DML handling instead
    of raising `SchemaMigrationError` during preflight.
- The paired positive was the status-0 exact-key/opaque-body header policy; it
  remained green. This proves the new checks can say no without broadening the
  body requirements for deletion commands.
- An earlier invocation selected an unsupported global Python 3.10 and failed
  collection. It is not counted as red-first evidence; only the corrected
  Python 3.12 run above is authoritative.

- A second bounded base probe added unsupported UNIQUE, CHECK, and FOREIGN KEY
  constraints to otherwise current `NL_HN` schemas. All three cases failed the
  new regression because the base verifier did not raise `SchemaMigrationError`
  before DML (**3 failed**, exit code 1). This red is kept as the evidence for
  the exact constraint census rather than adding one test per reviewer
  hypothesis.

- The first workflow-equivalent full-suite run exposed a real interaction that
  the compact contract had not yet fixed: official blank optional HN text was
  converted to SQL `NULL`, which conflicts with the new distinction between a
  validated blank provider value and a missing caller field. That run ended
  with **9 failed, 3478 passed, 399 skipped**; all nine failures were the same
  incomplete/blank HN fixture class, not unrelated product regressions.
- Before changing the converter, the existing HN contract was minimally
  extended with
  `test_hn_blank_optional_text_remains_an_empty_provider_value`. Against that
  candidate the native and standard cases both failed at storage
  (**2 failed**, exit code 1) because `BameiKana` became `NULL`. Production was
  then changed only for the three officially blankable HN text fields
  (`BameiKana`, `BameiEng`, and `SanchiName`) so a present blank remains `""`;
  missing/`None` remains invalid. The paired test then passed **2/2**.

## Implemented contract and green evidence (2026-08-18)

- `HNParser` now validates the complete current 251-byte body, official
  fixed-width numeric/code domains, CP932 capacities, the exact ten-digit
  `HansyokuNum`, and real `MakeDate`; obsolete 245-byte input remains rejected.
  Status 0 validates the header/key from the original bytes and does not decode
  the nonkey body.
- Both importer classes and the single-record entry validate caller-built HN
  before coercion, resolve standard aliases without accepting conflicts, apply
  status 0 as a physical exact-key erase, and count provider operations in
  order. HN remains accumulated-only and no realtime table was added.
- `NL_HN` and `HANSYOKU` now use the same NOT NULL official identity/body
  contract. The dedicated verifier rejects wrong types/capacities/nullability,
  generated or extra columns, additional UNIQUE/CHECK/FK constraints, and
  unusable PostgreSQL primary keys before mutation. SchemaManager and both
  standard/native preflight paths use the same verifier, including Dual
  targets independently.
- SQLite affected selection:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py
  tests/test_current_record_validation.py tests/test_data_kubun_entry_contract.py
  tests/test_migration.py -m 'not postgresql'` => **239 passed**.
- Expanded HN SQLite contract after backend/Dual negatives:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py` =>
  **69 passed, 9 skipped**.
- Fresh disposable PostgreSQL 16, with opt-in integration enabled:
  `tests/test_hn_official_contract.py` => **44 passed**. This includes both
  importers, native/standard, `auto_commit=True/False`, provider order/exact
  erase, deferrable-PK rejection, and mixed SQLite/PostgreSQL Dual orientation.
- Final directly affected SQLite selection after fixture and blank-value
  closure:
  `tests/test_hn_official_contract.py tests/test_hn_parser_layout.py
  tests/test_parsers.py tests/test_rc_official_contract.py
  tests/test_tk_official_contract.py tests/test_ys_official_contract.py
  -m 'not postgresql'` => **449 passed, 17 skipped**.
- Final expanded fresh PostgreSQL 16 selection (HN, layout/current-status,
  migration, metadata, and directly adjacent contracts) => **294 passed,
  3 subtests passed**. A separate real PostgreSQL readback probe confirmed
  native and standard blank provider values remained empty strings rather than
  `NULL`.
- A manual public `SchemaManager` probe against an unsafe existing HN schema
  returned failure and preserved the exact before/after schema, confirming the
  strict verifier rejects before additive mutation.
- Final workflow-equivalent repository suite under locked Python 3.12:
  `uv run --python 3.12 --extra dev --extra postgres python -m pytest tests
  --ignore=tests/integration --ignore=tests/e2e -m 'not slow' -q` =>
  **3489 passed, 399 skipped, 14 deselected, 20 subtests passed**.
- `uv lock --check`, `scripts/validate_test_gate.py`, fatal flake8
  (`E9,F63,F7,F82`), and `mkdocs build --strict` all passed after the affected
  docs/code changes. These lightweight gates will be repeated after the final
  worklog edit and before freezing the candidate commit.
- The disposable PostgreSQL container is not production/provider state and
  will be removed before the candidate commit. No provider acquisition or real
  database was changed in this iteration.

## Handoff to Claude Code and terminal closure (2026-08-18)

- Codex stopped at its usage cap after committing candidate
  `03b67208954114069a7312c0675879e98664f53e` (worktree clean, 2 commits ahead
  of `origin/master` `8408bcf7e3580b72f25c027a3a4e0a138343447b`; no drift at
  handoff). Continued by Claude Code, `claude --model fable`
  (`claude-fable-5`), session id `0d3dab84-62e8-4fea-92b2-4fa762267d12`.
  Fable was chosen because the remaining work repairs a validator/gate
  (fail-open risk) and aggregates a batched review, which AGENTS.md lists as
  Fable-eligible.
- Lightweight gates repeated at `03b6720…` before review: `uv lock --check`
  pass, `scripts/validate_test_gate.py` `TEST GATE PASS`, fatal flake8
  (`E9,F63,F7,F82`) `0`, `mkdocs build --strict` pass (site built to `/tmp`
  and removed).
- Disposable review artifacts removed: containers
  `jltsql-cc-critical-pg16-7dff` (with its anonymous volume) and
  `jltsql-cc-review-pg16-7dff`; the worktree's iteration-generated
  `.coverage`, `htmlcov/`, `.pytest-tmp/`, `.pytest_cache/`, `.ruff_cache/`,
  `logs/`, `jltsql.egg-info/`, `__pycache__/`. `.venv` was kept only while
  tests were still needed and is removed after the PR is opened. No `kps_*` /
  `jrdb-*` container, volume, or scheduler was touched.
- Official domain cross-check before review: the JV-Data 4.9.0.1 workbook text
  (`１８．繁殖馬マスタ`, 251 bytes) gives 初期値 `0` for 予備(22/8), 予備(40/1,
  "0"を設定), 血統登録番号, 生年, 性別/品種/毛色コード, 輸入年, and both parent
  numbers, `sp`/`Ｓ` for 馬名/馬名半角ｶﾅ/馬名欧字/産地名, and 繁殖馬持込区分
  `0/1/2/3/9`. The committed domains match; no official disagreement, so no
  STOP.

### Single batched independent review of `03b67208954114069a7312c0675879e98664f53e`

Three parallel read-only reviewers (official parser/domain; DB/schema/
transaction; release/test/docs). Result: **0 blocking**, 4 should-fix, nits.

Accepted and repaired in one batch:

1. Parser (should-fix): `_require_cp932_text` treated only `""` as blank, so a
   caller-built live row with whitespace-only `Bamei` passed
   `validate_import_record_header` and then failed at INSERT (`NOT NULL`,
   `records_failed=1`) instead of being rejected before coercion. Fixed with
   `not value.strip()`.
2. Importer (should-fix): `validate_hn_record` resolved standard aliases
   (`HansyokuMochiKubun`/`HansyokuFNum`/`HansyokuMNum`) for every target, but
   the native `NL_HN` write path never translates them back, so an alias-only
   row passed validation and failed at DML (`NOT NULL constraint failed:
   NL_HN.MochiKubun`; `ImporterError` under caller-owned transactions). Fixed by
   resolving aliases only when the target is unknown or `HANSYOKU` (the
   existing WE/`TENKO_BABA` precedent), so `NL_HN` now rejects before DML with
   `SchemaMigrationError`.
3. Layout test (should-fix): the narrowed distinctness sentinel excluded four
   fields although the only collision was `DataKubun == MochiKubun == "1"`; a
   MochiKubun read from byte 3 would have passed. `MochiKubun` sentinel is now
   the official `9`, `HansyokuNum` sentinel `1234567891` (no trailing `0`
   adjacent to the zero-filled reserved span), and the original
   `test_every_field_uses_a_distinct_decoded_sentinel` is restored.
4. Docs (should-fix): the blank-optional-text-as-empty-string storage rule was
   documented only in this worklog; one sentence added to `docs/data_support.md`,
   `CHANGELOG.md`, and `RELEASE_NOTES.md`.
5. Nits: restored the four blank lines the diff had removed (E302/E305 in
   `importer.py`, `importer_optimized.py`, `schema_metadata.py`,
   `record_factory.py`); `expected=(251,)` message typo in
   `HNParser._validate_envelope`.

Recorded as non-blocking / not repaired (reason):

- Unreachable length/CRLF checks remain in `HNParser.parse()` after
  `_validate_envelope`; harmless, left to keep the diff minimal.
- `SexCD`/`HinsyuCD`/`KeiroCD` are digit-domain only (code tables 2201-2203 can
  grow); only `MochiKubun` is table-enforced. The earlier "code domains" wording
  above should be read that way.
- A present-but-empty standard alias key next to a populated native value
  (`{MochiKubun:"1", HansyokuMochiKubun:""}`) still reaches DML for `HANSYOKU`
  and fails loudly; same pre-existing pattern as HR, out of this scope.
- `_HN_LOSSLESS_TEXT_WIDTHS["NL_HN"]["RecordDelimiter"]` is dead (column always
  NULL); `HANSYOKU.MakeDate DATE` SQLite affinity is pre-existing; every HN
  record is validated twice (header + table) like HC/HS.
- The batch erase test observes only the final `1 -> 2 -> 0` count; the
  DB reviewer probed the intermediate status-2 revision directly (both
  importers, both tables hold one row `DataKubun='2'`), and interleaved keys /
  double erase / erase-of-missing-key behave and count as for siblings.
- `-m 'not postgresql'` in the commands above is a no-op (no such marker is
  registered); the PostgreSQL cases skip via the fixture unless
  `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1`, so CI without PostgreSQL skips them
  cleanly (verified: collected and skipped, not errored).
- Red-first reconciliation measured by the review: the committed module
  replayed against base `8408bcf…` fails to import
  `verify_hn_storage_schema`; with an import shim it is **34 failed, 1 passed,
  11 skipped**, i.e. the 24+1 above plus the six schema-defect params, the two
  blank-text cases, the raw-body-opaque case, and the Dual case that were added
  later. Sibling test edits (`test_rc/tk/ys_official_contract`, `test_parsers`,
  `test_current_record_validation`, `test_hn_parser_layout`) were each
  necessary: their base versions fail 37 cases against the new HN domain.

### Repair batch red-first and green evidence

- Reds against the unrepaired candidate `03b6720…`
  (`.venv/bin/python -m pytest -q --no-cov tests/test_hn_official_contract.py`
  selected cases): `test_hn_caller_values_are_rejected_before_coercion
  [whitespace-only-required-body]` and
  `test_hn_standard_only_aliases_are_rejected_for_native_storage_before_dml`
  both `Failed: DID NOT RAISE SchemaMigrationError` (**2 failed**); the second
  also logged the underlying `NOT NULL constraint failed: NL_HN.MochiKubun`.
  Paired positives (`validate_hn_record(alias_only, "HANSYOKU") is True`,
  status-0 header-only) stayed green.
- After the repair batch, affected SQLite selection
  (`tests/test_hn_official_contract.py tests/test_hn_parser_layout.py
  tests/test_parsers.py tests/test_current_record_validation.py
  tests/test_rc_official_contract.py tests/test_tk_official_contract.py
  tests/test_ys_official_contract.py tests/test_data_kubun_entry_contract.py
  tests/test_migration.py`) => **629 passed, 17 skipped**.
- One fresh disposable PostgreSQL 16 container (`postgres:16-alpine`, tmpfs
  data dir, `127.0.0.1` only, removed immediately after; no volume left):
  `tests/test_hn_official_contract.py` with the opt-in enabled => **48
  passed** (all 11 PostgreSQL/mixed-Dual cases included);
  `tests/test_hn_parser_layout.py tests/test_migration.py
  tests/test_current_record_validation.py -k 'HN or hn or migration'` => **65
  passed**. The repair touched only backend-agnostic validation; schema
  verifier and erase paths are unchanged from the `03b6720…` evidence above.
- Workflow-equivalent repository suite on the repaired tree
  (`pytest tests --ignore=tests/integration --ignore=tests/e2e -m 'not slow'`,
  Python 3.12 venv) => **3491 passed, 399 skipped, 14 deselected, 20 subtests
  passed** (two more passes than before = the two new regression cases).
- Gates on the repaired tree: `uv lock --check` pass; `validate_test_gate.py`
  `TEST GATE PASS`; fatal flake8 `0`; blank-line lint on the touched files `0`;
  ruff on the touched files unchanged (16 pre-existing, 0 new);
  `mkdocs build --strict` pass; `git diff --check` clean.
- Final candidate full SHA is the commit that carries this worklog delta and
  the repair batch; it is recorded in the PR body and PR comment, not
  self-referenced here.

## Next safe command and STOP conditions

- Next: open the PR against `master` from
  `agent/hn-official-contract-20260818`, record the exact head full SHA in the
  PR body, wait for the required `lint`/`test` checks and the single Copilot
  review, answer every thread with evidence, and leave merge to Devin.
- STOP on official workbook/SDK disagreement, repository drift, ambiguity about
  legacy 245-byte provenance, a schema migration that would mutate before
  rejection, or any need to access/change real provider state.
- Do not record credentials, connection strings, private provider identifiers,
  or raw secret-bearing logs.
