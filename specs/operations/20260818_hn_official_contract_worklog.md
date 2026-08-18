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

## Next safe command and STOP conditions

- Next: transcribe the current official HN key/body domain into the minimal
  regression contract and run the new negatives against base before modifying
  production code.
- STOP on official workbook/SDK disagreement, repository drift, ambiguity about
  legacy 245-byte provenance, a schema migration that would mutate before
  rejection, or any need to access/change real provider state.
- Do not record credentials, connection strings, private provider identifiers,
  or raw secret-bearing logs.
