# SK official-contract closure worklog

## Start state (2026-08-19)

- Objective: close the remaining SK progeny-master (産駒マスタ) contract, the
  second item of the serial official-contract order
  `HN -> SK -> UM -> H1 -> H6 -> O1-O6 (truth/parser) -> O1-O6 (lossless storage)`
  recorded in `specs/operations/20260818_official_contract_inventory_worklog.md`.
- Minimal scope (fixed by Codex; not to be loosened): current ten-digit
  `KettoNum`, key/body official domains, header alias conflict/missing
  rejection, native `NL_SK` and standard `SANKU` provider order `1 -> 2 -> 0`
  as physical exact erase with in-order operation statistics, strict exact
  schema preflight for SQLite/PostgreSQL/Dual before any DML without
  mutation-before-rejection, all `DataImporter`/`OptimizedDataImporter`/
  single-record/`auto_commit=True|False` paths, realtime explicitly N/A
  (accumulated `BLDN` master only, no `RT_SK`), and preservation of the merged
  PR #175 official 208-byte current-only layout with all 14 pedigree values.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_sk_official`.
- Branch: `agent/sk-official-contract-20260818`.
- Base and starting HEAD: `802d3d6fb9f0fc3ffbeb707544f8b8bb22565132`
  (`origin/master`, PR #220 squash merge: native `NL_UM` replacement-key
  verification). Devin rebased the branch onto this base before handoff.
- Package version under development: `2.0.0.dev0`; no prerelease published.
- Starting worktree was clean.
- Implementer: Claude Code, `claude --model fable` (`claude-fable-5`),
  session id `532e9724-bff1-4481-8ee3-a37b0d0c6edf`. Fable was chosen because
  the iteration builds a validator/gate (fail-open risk) and a schema
  verifier whose ordering (reject before mutation) changes the outcome, both
  of which AGENTS.md lists as Fable-eligible.
- Model iteration for the pattern: `specs/operations/20260818_hn_official_contract_worklog.md`
  (PR #217, merge `36800dcbba37d964653b6581cba7eba873fbdef2`).
- Rules: `/home/keiba/keiba/AGENTS.md` (red first, do not mark unmeasured
  things green, answer findings with measurements, record full SHAs, no
  test deletion/weakening/skipping, no fail-open, no self-referencing SHA
  commit). PR creation is left to Devin; this iteration pushes the branch and
  reports the head full SHA.

## Prior completed boundary

- PR #175 / merge `ff62d65c07b1026e7ea7606b1d6329dbd9768199` implemented the
  official current 208-byte SK layout (BreederCode 8 bytes, 14 x 10-byte
  three-generation pedigree numbers), rejects the obsolete 178-byte physical
  record, maps native `NL_SK` and standard `SANKU` with `KettoNum` as the
  single primary key, and refuses a legacy alias-only `HANSYOKU_UMA` database.
  `tests/test_sk_parser_layout.py` is the executable evidence and is retained.
- PR #192 added the shared fixed-length envelope check (`validate_fixed_record`).

## Official source cross-check (2026-08-19, read-only)

Read from the box copies of the official materials
(`/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.xlsx`,
`JV-Data4802.xlsx`, and `/tmp/JVData_Structure.h.utf8` SDK header):

- JV-Data 4.9.0.1 `フォーマット` rows 844-859 (`１９．産駒マスタ`, 208 bytes):
  レコード種別ID 1/2 `"SK"`; データ区分 3/1 初期値 `0` (`1:新規登録 2:更新
  0:該当レコード削除`); データ作成年月日 4/8 `0` yyyymmdd; ○血統登録番号 12/10 `0`
  (生年4桁＋品種1桁＋数字5桁); 生年月日 22/8 `0` yyyymmdd; 性別コード 30/1 `0`
  (code 2202); 品種コード 31/1 `0` (code 2201); 毛色コード 32/2 `0` (code 2203);
  産駒持込区分 34/1 `0` **`0:内国産 1:持込 2:輸入内国産扱い 3:輸入`** (no `9`);
  輸入年 35/4 `0` 西暦4桁; 生産者コード 39/8 `0` (生産者マスタにリンク);
  産地名 47/20 `Ｓ` 全角10文字; 3代血統 繁殖登録番号 67, 14 x 10 = 140, `0`,
  父･母･父父･父母･母父･母母･父父父･父父母･父母父･父母母･母父父･母父母･母母父･母母母;
  レコード区切 207/2 CR/LF.
- The HN sheet (rows 820-841) gives 繁殖馬持込区分 `0:内国産 1:持込
  2:輸入内国産扱い 3:輸入　9:その他`; the `9:その他` cell belongs to HN only.
  The PDF text extraction (`/tmp/jvdata4901.txt`) floats that cell into the
  SK page header, which is why the workbook was consulted directly.
- JV-Data 4.8.0.2 rows 844-859 give the same field order and domains with the
  obsolete widths (178 bytes, 生産者コード 6, pedigree 14 x 8 = 112).
- SDK 5.0.0 `JV_SK_SANKU` matches 4.9.0.1: `KettoNum[10]`, `_YMD BirthDate`,
  `SexCD[1]`, `HinsyuCD[1]`, `KeiroCD[2]`, `SankuMochiKubun[1]`,
  `ImportYear[4]`, `BreederCode[8]`, `SanchiName[20]`, `HansyokuNum[14][10]`,
  `crlf[2]`.
- Code tables 2201 (品種 `0`-`8`...), 2202 (性別 `0`-`3`), 2203 (毛色 `00`-`10`...)
  are digit domains that can grow; as for HN only the fixed 産駒持込区分 list is
  table-enforced, the code fields are enforced as ASCII digits of the official
  width.
- No official disagreement found between 4.8.0.2, 4.9.0.1, and the SDK; no
  STOP condition.

Domain decisions taken from the workbook (recorded so a reviewer can refute
them with evidence rather than re-deriving them):

- `KettoNum`: exactly 10 ASCII digits (as UM/HN). The 生年＋品種＋連番
  composition is not cross-checked against `BirthDate`; that would exceed the
  official caller contract used by the sibling masters.
- `BirthDate`: a real `yyyymmdd` date. The workbook says `yyyymmdd 形式`; the
  standard `SANKU.BirthDate` column is `DATE` (as `UMA.BirthDate`, whereas the
  UM `DelDate` that can be `00000000` was deliberately kept `VARCHAR(8)`), so a
  zero-filled value could not be stored consistently on PostgreSQL anyway. A
  zero-filled `BirthDate` is therefore rejected before DML on every backend
  instead of failing only on PostgreSQL.
- `ImportYear`: exactly 4 ASCII digits; `0000` (initial value for domestic
  horses) is a valid provider value and is kept (`0` in `NL_SK INTEGER`,
  `0000` in `SANKU VARCHAR(4)`).
- `BreederCode`: exactly 8 ASCII digits (初期値 `0`, links to the BR master
  whose key is 8 digits; the reconstructed BR fixture holds `00000100`-style
  values). `00000000` remains valid.
- 14 pedigree numbers: exactly 10 ASCII digits each; `0000000000` remains valid.
- `SexCD`/`HinsyuCD`/`KeiroCD`: ASCII digits of width 1/1/2 (code tables can grow).
- `SankuMochiKubun`: exactly one of `0`,`1`,`2`,`3`.
- `SanchiName`: CP932 text within 20 bytes; officially blankable (初期値 `Ｓ`), so a
  present blank value is stored as `""` (not `NULL`) in both tables, matching
  the HN rule for `BameiKana`/`BameiEng`/`SanchiName`; a missing/`None` value is
  rejected.
- Status `0`: header + exact 10-digit `KettoNum` only; the non-key body is not
  decoded (same erase policy as HN).

## Confirmed gaps at start (base `802d3d6fb9f0fc3ffbeb707544f8b8bb22565132`)

- `SKParser.parse()` decodes fields but validates no domain: non-digit key,
  invalid 産駒持込区分, malformed dates, non-digit pedigree numbers all parse.
- `validate_import_record_header()` has no SK branch: caller-built key-only or
  malformed rows reach storage.
- SK is absent from `_OFFICIAL_ERASE_KEY_COLUMNS`, `_OFFICIAL_ERASE_STORAGE_TABLES`,
  and `_PROVIDER_OPERATION_COUNT_STORAGE_TABLES`; native/standard `1 -> 2 -> 0`
  leaves a `DataKubun='0'` tombstone.
- No `verify_sk_storage_schema`; `NL_SK`/`SANKU` are entirely nullable and only
  the generic additive `verify_table_schema` runs.
- SK is accumulated-only (`BLDN`); no `RT_SK` exists and none must be added.

## Red-first evidence (2026-08-19)

- Added the uncommitted regression module `tests/test_sk_official_contract.py`
  before modifying production code. Its SK dictionaries are derived from
  `tests/test_sk_parser_layout.build_current_record()` (PR #175 layout).
- The module imports `validate_sk_record` / `verify_sk_storage_schema`, which
  do not exist at the base, so the base replay used a two-line import shim
  (`/tmp/skshim/skshim_plugin.py`, `-p skshim_plugin`) that binds both names to
  no-op `False` callables; that reproduces the base behaviour (no SK-specific
  validator/verifier) without changing any production file.
- Command (locked Python 3.12 venv):
  `PYTHONPATH=/tmp/skshim .venv/bin/python -m pytest -q --no-cov -p no:cacheprovider -p skshim_plugin tests/test_sk_official_contract.py`.
- Base result at full SHA `802d3d6fb9f0fc3ffbeb707544f8b8bb22565132`
  (tree = base + this worklog + the new test module): **40 failed, 7 passed,
  11 skipped**, exit code 1.
  - 8 parser-domain negatives were accepted (`assert {...} is None` failed:
    non-digit key, impossible birth date `20240231`, non-digit sex code, the
    HN-only 産駒持込区分 `9`, non-digit import year, non-digit breeder code
    `BR000039`, non-digit pedigree number, blank last pedigree slot);
  - the status-0 raw record with an opaque non-CP932 body was rejected
    (`assert None is not None`), i.e. erase commands were not exact-key only;
  - 5 caller-built body/key negatives were accepted (`DID NOT RAISE
    SchemaMigrationError`: non-digit key, missing `BirthDate`, mochi `9`,
    short pedigree, missing `SanchiName`);
  - `validate_sk_record(erase, "NL_SK")` returned `False` under the shim
    (status-0 header/exact-key validator absent);
  - blank `SanchiName` was stored as `NULL` in both tables
    (`{'SanchiName': None} != {'SanchiName': ''}`);
  - all 8 batch `1 -> 2 -> 0` paths (both importers, owned/caller-owned,
    native/standard) left a stored tombstone
    (`Left contains one more item: {'KettoNum': '2024100001', 'SanchiName': None}`);
  - all 4 single-record erase paths left the row (`{'count': 1} != {'count': 0}`);
  - all 4 unsafe-extra-required-column schemas and the six SQLite verifier
    defects (nullable key, wrong body type, extra UNIQUE/CHECK/FK, generated
    column) plus the SQLite/SQLite Dual case did not raise before DML
    (`DID NOT RAISE SchemaMigrationError`).
- Paired positives that were already green at the base and stay as the
  "not too strict" guard: the official initial/blank-value record parses
  (`0000` import year, `00000000` breeder, 14 x `0000000000` pedigree, blank
  産地名, 持込区分 `0/1/2/3`); the shared header gate already rejects a
  conflicting `headRecordSpec`/`headDataKubun` alias and a missing status;
  same-key `1 -> 2` replacement, other-key survival, and caller-owned rollback;
  SK is not routed to realtime (`RT_SK` absent, no cache write).
- 11 PostgreSQL/mixed-Dual cases skip without the opt-in environment variable
  and are exercised on a disposable PostgreSQL 16 below.

## Implemented contract and green evidence (2026-08-19)

Implementation (mirrors the HN #217 architecture; no new table, no realtime
route):

- `src/parser/sk_parser.py`: `SKParser` now validates its own envelope
  (208 bytes, `SK`, CRLF at 207-208, real `MakeDate`, one central
  `status_domain.validate_data_kubun` call), decodes CP932 strictly for live
  rows only, and validates the complete body domain listed above through
  `validate_key_fields` / `validate_current_fields`. Status 0 decodes and
  validates only the header and the exact ten-digit `KettoNum`; the 14
  pedigree and body spans stay in the regex-discoverable generated form so
  `scripts/reconstruct_fixtures_from_db.extract_parser_info` still finds every
  current field (PR #175 test retained).
- `src/importer/importer.py`: `_SK_STORAGE_TABLES`/`_SK_KEY_COLUMNS`/
  `_SK_BLANK_TEXT_FIELDS`/`_SK_LOSSLESS_TEXT_WIDTHS`; SK added to
  `_PROVIDER_OPERATION_COUNT_STORAGE_TABLES`, `_STRICT_NONADDITIVE_STANDARD_TABLES`
  (`SANKU`), `_OFFICIAL_ERASE_KEY_COLUMNS`, `_OFFICIAL_ERASE_STORAGE_TABLES`;
  new `_verify_sk_no_unapproved_constraints`, `verify_sk_storage_schema`
  (table/PK, exact type/capacity/nullability, no generated/extra columns, no
  extra UNIQUE/CHECK/FK/exclusion, PostgreSQL PK usable by `ON CONFLICT`, Dual
  targets independently, validation-transaction snapshot/rollback), and
  `validate_sk_record`; SK branch in `validate_import_record_header`, standard
  preflight for `SANKU`, blank `SanchiName` kept as `""` in
  `convert_record_types`, and `_verified_sk_tables` + verify/validate calls in
  `DataImporter.import_records` (first record and loop) and
  `import_single_record`.
- `src/importer/importer_optimized.py`: same first-record/loop wiring.
- `src/database/schema.py` / `schema_jravan.py`: `NL_SK` and `SANKU` are
  NOT NULL for every official column (`NL_SK.RecordDelimiter` stays nullable as
  for `NL_HN`); `STRICT_SK_STORAGE_TABLES` hooked into the strict preflight,
  `SchemaManager.create_table`/`create_all_tables`, and module
  `create_all_tables`.
- `src/database/schema_metadata.py`: SK purpose/identity description.
- Sibling test edits (each necessary): `tests/test_sk_parser_layout.py`
  `BreederCode` sentinel `BR000039 -> 00000039` (official domain is digits;
  distinctness assertion still holds); `tests/test_current_record_validation.py`
  adds `SK` to `DOMAIN_PAYLOAD_REQUIRED`; `tests/test_reconstructed_db_fixtures.py`
  fills the 13 blank pedigree slots of the obsolete 78-byte fixture with the
  documented initial value `0` (KS precedent) instead of spaces;
  `tests/fixtures/record_factory.make_sk_record` added and used by
  `tests/test_parsers.py`; the shared PostgreSQL assertion in the new module
  aliases identifiers because PostgreSQL folds unquoted names to lower case.
- Docs: `docs/data_support.md` summary row, `docs/record_contracts.md` new
  `SK（産駒マスタ）` section under the renamed
  `マスタ系（HN / SK / UM / BT / KS / CH / HS）` heading (anchor updated),
  `CHANGELOG.md`, `RELEASE_NOTES.md`.

Green evidence on the pre-review tree (commands run from the worktree with
the locked Python 3.12 venv, `--no-cov -p no:cacheprovider` unless noted):

- `tests/test_sk_official_contract.py tests/test_sk_parser_layout.py` =>
  **93 passed, 11 skipped** (SQLite).
- Affected SQLite selection
  `tests/test_sk_official_contract.py tests/test_sk_parser_layout.py
  tests/test_current_record_validation.py tests/test_reconstructed_db_fixtures.py
  tests/test_parsers.py tests/test_data_kubun_entry_contract.py
  tests/test_migration.py tests/test_metadata_application.py
  tests/test_official_jvdata_oracle.py tests/test_parser_compatibility.py
  tests/test_hn_official_contract.py tests/test_e2e_comprehensive.py` =>
  **918 passed, 31 skipped** after the `make_sk_record` sample fix (the first
  run showed exactly the 3 `test_parsers[SK]` space-filled-sample failures the
  new domain is meant to reject; no other module changed result).
- One disposable PostgreSQL 16 (`postgres:16-alpine`, local image, tmpfs data
  directory, `127.0.0.1` only, `--rm`; started 09:10 JST, removed after the
  final evidence below): `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1`
  `tests/test_sk_official_contract.py` => **58 passed** (47 SQLite + all 11
  PostgreSQL/mixed-Dual cases: both importers x owned/caller-owned x
  native/standard provider order `1 -> 2 -> 0` with exact erase, other-key
  survival and blank `SanchiName` readback as `""`, deferrable-PK rejection,
  mixed SQLite/PostgreSQL Dual rejection in both orientations).
- Expanded PostgreSQL-enabled selection
  `tests/test_sk_official_contract.py tests/test_sk_parser_layout.py
  tests/test_hn_official_contract.py tests/test_migration.py
  tests/test_current_record_validation.py tests/test_metadata_application.py`
  => **337 passed, 3 subtests passed**; `tests/test_postgresql.py
  tests/test_all_schemas.py tests/test_dual_handler_transactions.py` => **26 passed**.
- Manual public `SchemaManager` probe against a legacy all-nullable `NL_SK`
  (current schema minus every `NOT NULL`): SQLite `create_table("NL_SK")` ->
  `False` and `create_all_tables()` -> all `False`, PostgreSQL
  `create_table("NL_SK")` -> `False`; `PRAGMA table_xinfo` /
  `information_schema.columns` identical before and after in every case
  (reject before additive mutation; error text lists each nullability mismatch).
- Workflow-equivalent repository suite (`pytest tests --ignore=tests/integration
  --ignore=tests/e2e -m 'not slow' -q`, coverage on as in CI) =>
  **3560 passed, 435 skipped, 14 deselected, 20 subtests passed** (101 s).
  This run started before the final `dict.fromkeys` lint touch to
  `importer.py`; the suite is rerun on the final candidate below.
- Gates: `uv lock --check` pass; `scripts/validate_test_gate.py` `TEST GATE
  PASS`; fatal flake8 (`E9,F63,F7,F82`, `--isolated`, `src tests scripts tools`)
  `0`; ruff on the touched files: 58 findings after vs 60 before, no new
  finding (one C420 introduced by the first draft was fixed with
  `dict.fromkeys`; three pre-existing `typing.Dict/Optional` findings in the
  old `sk_parser.py` disappeared); `mkdocs build --strict` pass (site built to
  `/tmp` and removed); `git diff --check` clean.

## Independent review (2026-08-19, Devin, direct implementation)

The implementation commit `01b65867285822d3992716c5d2284a2ddb8d4747` was
produced by the delegated Claude Code session, which stopped at its 09:25 JST
session limit before the review batch. On the user's instruction the delegation
was ended and the remaining work was done directly by Devin
(session `83dda3bd2bb44d7abe83462669c51210`). Everything below was measured in
this worktree; the disposable PostgreSQL 16 container `jltsql-sk-pg16-8215`
(`127.0.0.1:32904`, schema-per-test) was reused and is removed at the end of the
iteration.

### Official source cross-check redone against the workbook text

`JV-Data 4.9.0.1` section `１９．産駒マスタ` (extracted text) confirms record
length `208`, `データ区分` `0/1/2`, `血統登録番号` `12/10` with composition
`生年(西暦)4桁＋品種1桁＋数字5桁`, `生年月日` `22/8` `yyyymmdd`, `性別コード`
`30/1`, `品種コード` `31/1`, `毛色コード` `32/2`, `産駒持込区分` `34/1` with the
domain `0:内国産 1:持込 2:輸入内国産扱い 3:輸入` (`9:その他` only appears in the
breeding-horse master), `輸入年` `35/4`, `生産者コード` `39/8`, `産地名` `47/Ｓ`,
and change history item `１９` for the 2023-08 `6→8` / `8→10` widths. The
implemented parser spans and domains match this, including the `初期値 0`
fields that make `0000`, `00000000` and `0000000000` valid provider values.

### Findings

1. **The per-defect schema tests did not pin the importer call sites.**
   Mutation probe: deleting all four `verify_sk_storage_schema` call sites in
   `src/importer/importer.py` left the SK contract module at **2 failed, 45
   passed, 11 skipped** — the six unsafe-schema cases only exercised
   `verify_sk_storage_schema` directly, so a future refactor could remove the
   guard from every importer path without a red test. Deleting the
   `importer_optimized.py` call site left **1 failed**.
   Repair (this commit): `test_sk_importer_paths_reject_each_unsafe_contract_before_dml`
   (both batch importers x six defects, insert and erase) and
   `test_sk_single_record_path_rejects_each_unsafe_contract_before_dml`
   (`auto_commit=True|False` x six defects), each asserting
   `SchemaMigrationError`, an unchanged `PRAGMA table_xinfo`, zero rows, and
   zero counted imports. After the repair the same probes fail **20** and
   **7** cases respectively.
2. **`ImportYear` readback was stronger in the documentation than in storage.**
   Measured: the officially valid domestic value `0000` reads back as `0` from
   `NL_SK` (`ImportYear INTEGER`) and as `"0000"` from `SANKU`
   (`ImportYear VARCHAR(4)`; the SQLite standard schema mirror declares
   `SMALLINT` for the reconstructed variant). The worklog stated this but
   `docs/record_contracts.md` did not.
   Repair: the SK contract section now states the per-table storage type and
   that the value is recoverable by four-digit zero fill, and
   `test_sk_zero_import_year_readback_follows_the_declared_column_type` pins
   both readbacks so documentation and storage cannot drift apart.
3. **`_SK_LOSSLESS_TEXT_WIDTHS["NL_SK"]` has no `ImportYear` entry** while
   `"SANKU"` does. Verified by measurement that this is only because the native
   column is `INTEGER`: `_verify_strict_storage_column_contract` still checks
   its declared type, and `test_sk_sqlite_schema_verifier_rejects_each_unsafe_contract[wrong-body-type]`
   plus the new importer-path variant reject `ImportYear TEXT NOT NULL` before
   any DML. No capacity gap; no code change needed.
4. **Refuted / no change.** Blank `SanchiName` handling is non-vacuous
   (removing the `convert_record_types` branch fails both
   `test_sk_blank_sanchi_name_remains_an_empty_provider_value` cases). Caller
   validation is non-vacuous (removing the five `validate_sk_record` call sites
   fails 6 cases). The SQLite constraint audit intentionally checks only
   FK/CHECK because extra UNIQUE and deferrable primary keys are covered by
   `_verify_replacement_key_constraints`, which is exercised by the
   `extra-unique` and PostgreSQL deferrable-PK cases.

### Residual risk carried forward (not fixed here)

- **The same test-shape weakness exists in the merged HN iteration.** Measured:
  deleting all six `verify_hn_storage_schema` call sites
  (`importer.py` x4, `importer_optimized.py` x2) leaves
  `tests/test_hn_official_contract.py` at **3 failed, 34 passed, 11 skipped`**,
  i.e. HN's per-defect cases also call the verifier directly. This is a missing
  regression pin, not a fail-open in shipped behaviour. It is recorded as the
  first item of the next iteration rather than widening this PR, and the other
  merged families (CS, WF, JG, TC, CC, ...) must be probed the same way.
- `SchemaManager` / `jltsql init` still cannot repair a drifted `NL_SK`; it
  fails closed and requires backup, rebuild and `BLDN` reimport, as documented.
- PostgreSQL evidence is PostgreSQL 16 only.

### Final candidate gates (rerun by Devin on the repaired tree)

- `tests/test_sk_official_contract.py` with `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1`
  => **73 passed, 11 skipped** (the 11 skips are the mixed-Dual/PostgreSQL cases
  that need the fixture's schema-per-test PostgreSQL, which ran in the wider
  selection below).
- PostgreSQL-enabled selection `tests/test_sk_official_contract.py
  tests/test_sk_parser_layout.py tests/test_hn_official_contract.py
  tests/test_migration.py tests/test_current_record_validation.py
  tests/test_metadata_application.py tests/test_postgresql.py
  tests/test_all_schemas.py tests/test_dual_handler_transactions.py`
  => **389 passed, 3 subtests passed**.
- Workflow-equivalent suite (`pytest tests --ignore=tests/integration
  --ignore=tests/e2e -m 'not slow' -q`, coverage on as in CI)
  => **3586 passed, 435 skipped, 14 deselected, 20 subtests passed** (104 s).
- `uv lock --check` pass; `scripts/validate_test_gate.py` `TEST GATE PASS`;
  fatal flake8 (`E9,F63,F7,F82`, `--isolated`, `src tests scripts tools`) `0`;
  `mkdocs build --strict` pass (built to `/tmp` and removed);
  `git diff --check` clean.

### STOP conditions for the next operator

- Do not treat the HN test-shape finding as an SK regression; it is a separate
  bounded PR.
- Do not restart a second PostgreSQL container while the disk is at 99 %.
