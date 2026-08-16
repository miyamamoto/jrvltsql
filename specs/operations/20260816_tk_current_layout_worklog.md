# TK current-layout implementation worklog

## Iteration identity

- Objective: replace the one-entry TK implementation with the complete official
  current physical layout and lossless storage contract.
- Minimum scope: TK parser, native/standard schemas and metadata, importer/storage
  behavior, historical fixtures/tests, and the tracked compatibility audit. No
  version bump, release, or live provider acquisition is included in this
  implementation iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_tk_layout`
- Branch: `agent/tk-current-layout-20260816`
- Base/full SHA: `b62ba13be49c07e034acab1b5a5b483e10eb365a`
- Previous dependent merge: PR #184, YS official-layout merge
  `b62ba13be49c07e034acab1b5a5b483e10eb365a`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release/publication iteration.
- Agent/model: Codex only. No Claude session is used.

## Known starting evidence

- The tracked official-spec audit records current TK as 21,657 bytes while the
  repository publishes and parses only 727 bytes.
- The known truncation keeps one repeated horse/training entry from an official
  array of up to 300 entries and places a delimiter inside the provider record.
- Exact offsets, repeated-entry cardinality, official key/update semantics, and
  historical-version behavior must be re-derived from the local official
  specifications and SDK before production code is changed.

## Plan and gates

- Reconcile JV-Data 4.8.0.2, 4.9.0.1, SDK 5.0.0, the current code/schema, and
  relevant official developer-community discussions. Record any physical-layout
  change rather than assuming current-only compatibility.
- Add one consolidated TK contract and run it red against unchanged production
  code. Include strict framing/encoding, every repeated entry, schema/key and
  update semantics, obsolete storage, both importers, and PostgreSQL where the
  official contract supports them.
- Implement once after aggregating findings. Run affected, full,
  workflow-equivalent, fatal lint, compile, and disposable PostgreSQL validation
  on an exact full SHA.
- Request one GitHub-native Copilot review, require green CI, unresolved threads
  zero, a clean worktree, and tree-equivalent merge.
- STOP on conflicting official evidence, unsafe migration, executable failure,
  base drift, or an unresolved actionable review finding.

## Next safe command

- Commit this starting worklog, then inventory all TK parser/schema/mapping/test
  references and locate the exact official specification and SDK structures.
