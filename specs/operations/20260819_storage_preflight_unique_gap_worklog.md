# JG/RC/WC replacement-key gap and single-record preflight pins worklog

## Start state (2026-08-19)

- Repository: `miyamamoto/jrvltsql`. Base: `7d3cad05708ef10ef670dee3679bd345a8108b4d`
  (SK official contract, PR #221).
- Worktree: `/home/keiba/scratch/20260819_jrvltsql_verifier_pins`.
- Branch: `agent/storage-verifier-path-pins-20260819`.
- Operator: Devin, session `83dda3bd2bb44d7abe83462669c51210` (direct
  implementation; the Claude Code delegation was ended by the user).
- Trigger: the SK review recorded a residual risk that the per-family contract
  modules may not pin the importer call sites. Probing that risk across every
  family found a real fail-open in three families, not just a test-shape gap.

## Correction to the SK worklog

`specs/operations/20260818_sk_official_contract_worklog.md` said that deleting
every SK verifier call site "could remove the guard from every importer path
without a red test" while quoting **2 failed** in the same sentence. The two
statements contradict each other: the deletion *was* caught, by 2 of 73 cases.
The accurate finding is that the six unsafe-schema defects and the single-record
path were not covered through the importer entrypoints, so most of the guard's
surface could regress silently. The sentence is corrected in this commit; the
measured numbers were already correct.

## Probe 1: is the guard pinned at all? (per family, all call sites deleted)

Deleting every `self._verified_<f>_tables` guard block from `importer.py` and
`importer_optimized.py`, then running that family's contract module:

```
se  9 failed   hr  7 failed   hs  1 failed   hc  9 failed   hn  3 failed
sk 27 failed   tc 11 failed   cc 12 failed   jc  7 failed   cs 16 failed
wf  4 failed   we  7 failed   wc  4 failed   jg  4 failed   rc  4 failed
av  7 failed   ck/ra/tk: no per-record guard   um: no contract module yet
```

No family is fully unpinned, so the HN residual risk recorded in the SK worklog
is bounded: HN's three failing cases do detect wholesale removal.

## Probe 2: is the `import_single_record` preflight pinned?

Deleting only the guard block inside `DataImporter.import_single_record`:

```
sk 12 failed   cs  4 failed
av hr hs hc hn jc jg rc se tc wc we wf: fully green  <-- unpinned
```

For 14 of 16 families the single-record preflight could be deleted without a red
test. Today's behaviour is still correct there (probe 3 shows the rejection is
symmetric), so this is a missing regression pin rather than shipped fail-open.

## Probe 3: which defect is actually unsafe for every family?

Batch vs single-record outcome on a drifted native schema (SQLite):

- `ExternalRequired TEXT NOT NULL` added: symmetric everywhere, and legitimately
  *allowed* by families whose preflight permits additive columns (AV, CS, HR, JC,
  JG, RC, SE, WC, WE, WF) — the row is then refused by the database itself. Not a
  usable universal defect.
- `UNIQUE (RecordSpec)` added: rejected before DML by 13 families, and
  **accepted** by `NL_JG`, `NL_RC` and `NL_WC`.

## Real fail-open found (JG, RC, WC)

With the extra UNIQUE in place, two records carrying *different* official keys
were imported one after the other:

```
NL_JG: first=1 second=1 rows=1  <== the second import erased the first
NL_RC: first=1 second=1 rows=1
NL_WC: first=1 second=1 rows=1
```

Both imports reported success and only one row survived. `verify_jg_storage_schema`,
`verify_wc_storage_schema` and `verify_rc_storage_schema` called only
`verify_table_schema` and never `_verify_replacement_key_constraints`, which is
the check that the merged HN/SK/CS/UM families use to refuse exactly this shape.
This is the same class as the native `NL_UM` fail-open repaired in PR #220.

## Red-first evidence

- `tests/test_{jg,wc,rc}_official_contract.py::test_*_storage_rejects_an_extra_unique_before_it_can_erase_another_key`
  (native and standard table, both importers, both commit modes, plus a
  positive case proving two distinct official keys coexist on the official
  schema): **6 failed**.
- `tests/test_single_record_preflight_pins.py` (16 families x both commit
  modes): **6 failed, 26 passed** — exactly the JG/RC/WC cases.

## Implementation

```
verify_jg_storage_schema / verify_wc_storage_schema / verify_rc_storage_schema
+   _verify_replacement_key_constraints(database, table_name, "<X> storage")
```

Three lines; no schema, parser or DDL change. Both Dual targets are covered
because the helper recurses over `_migration_targets`.

## Green evidence

- Focused: `tests/test_{jg,wc,rc}_official_contract.py` +
  `tests/test_single_record_preflight_pins.py` => **167 passed** with
  `JLTSQL_RUN_POSTGRESQL_INTEGRATION=1` against the disposable PostgreSQL 16
  container `jltsql-sk-pg16-8215` (reused, removed after the iteration).
- Mutation probe on the repaired tree: deleting the three new lines returns
  **12 failed**, so every new assertion is non-vacuous.
- Workflow-equivalent suite (`pytest tests --ignore=tests/integration
  --ignore=tests/e2e -m 'not slow' -q`) => **3624 passed, 435 skipped,
  14 deselected, 20 subtests passed** (114 s); base was 3586 passed.
- `uv lock --check` pass; `scripts/validate_test_gate.py` `TEST GATE PASS`;
  fatal flake8 (`E9,F63,F7,F82`) `0`; `mkdocs build --strict` pass;
  `git diff --check` clean.

## Residual risk

- The new cross-family pin uses one representative defect per family, not the
  full per-family defect matrix, on the single-record path.
- Standard-name and realtime tables of the three repaired families are covered
  through the parametrised native/standard cases only for the batch path plus
  the shared native single-record pin.
- PostgreSQL evidence is PostgreSQL 16 only.

## Stop conditions

- Do not widen this PR into the pending UM official contract; UM keeps its own
  iteration (`H1 -> H6 -> O1-O6 x2 -> 2.0.0.dev0` unchanged behind it).
