# KS current-layout implementation worklog

## Iteration identity

- Objective: replace the partial KS jockey-master implementation with an
  official-layout, lossless, fail-closed implementation and storage contract.
- Minimum scope: KS parser, native/standard schemas and mappings only where the
  official current record requires them, accumulated importer behavior,
  compatibility fixtures/tests, public support documentation, and this audit
  evidence. No unrelated partial format is changed in this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_ks_layout`
- Branch: `agent/ks-current-layout-20260816`
- Base/full SHA: `888e3cb4d572320512da6da4854c5cc6b66bb37d`
- Previous dependent merge: PR #181, TM official-layout merge
  `888e3cb4d572320512da6da4854c5cc6b66bb37d`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release-lock or publication iteration.
- Agent/model: Codex only, per the user's explicit instruction to continue the
  review with Codex. No Claude session is used.

## Starting observations

- The tracked official compatibility audit marks KS as `partial`: the public
  parser length is 772 bytes while JV-Data 4.9.0.1 documents 4173 bytes.
- The current implementation stops inside the repeated jockey-performance
  region and therefore cannot prove that the complete current record was
  consumed or stored.
- Official JV-Data 4.8.0.2, 4.9.0.1, and SDK 5.0.0 definitions, plus relevant
  official developer-community corrections, must be compared before choosing
  whether any historical/current dual layout is legitimate.

## Plan and gates

- Extract the exact byte layout, repeated groups, data-kind domains, delimiter,
  and version history from official sources; compare every implemented field
  and schema column rather than trusting the current parser names.
- Inspect community reports for KS corrections, delivery order, deletion, or
  historical layout changes and distinguish authoritative facts from
  inferences.
- Add the minimum failing contract to the unchanged production implementation
  and record its actual red result before modifying parser/storage checks.
- Implement one complete current contract, or explicit old/current dispatch
  only if official evidence establishes more than one valid physical layout.
- Validate the immutable candidate with focused/full tests, supported Python,
  disposable PostgreSQL where storage changes require it, exact-head CI, one
  aggregated review, unresolved threads zero, and a clean worktree.
- STOP on conflicting official evidence, a schema migration that can lose
  existing rows, any executable failure, base drift, or unresolved actionable
  finding.

## Next safe command

- Inspect `src/parser/ks_parser.py`, native/standard KS schemas and metadata,
  then extract format 7 from all available official documents/SDK structures.
