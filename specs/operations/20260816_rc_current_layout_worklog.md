# RC current-layout implementation worklog

## Iteration identity

- Objective: replace the partial RC course-record implementation with the
  complete official current physical layout and a lossless keyed storage
  contract.
- Minimum scope: RC parser, native/standard schemas and mappings only where the
  official record requires them, accumulated importer behavior, fixtures/tests,
  support documentation, and audit evidence. No TK/YS or release change is in
  this iteration.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `/home/keiba/scratch/20260816_jrvltsql_rc_layout`
- Branch: `agent/rc-current-layout-20260816`
- Base/full SHA: `79833980f8a7f0cc09c2a308a50a512091e5565b`
- Previous dependent merge: PR #182, KS official-layout merge
  `79833980f8a7f0cc09c2a308a50a512091e5565b`.
- Project version at start: `1.6.10`; this is a specification iteration, not a
  release/publication iteration.
- Agent/model: Codex only. No Claude session is used.

## Starting observations

- The tracked audit marks RC as partial: the parser accepts 241 bytes while
  JV-Data 4.9.0.1 documents 501 bytes.
- The current parser stores one complete holder block, two bytes of the second
  horse identifier, then treats bytes 240-241 as CR/LF. It therefore cannot
  represent all three official record-holder blocks or prove record framing.
- Official JV-Data 4.8.0.2, 4.9.0.1, SDK 5.0.0 structures, and relevant official
  developer-community corrections must be compared before deciding whether any
  historical/current dual-layout support is legitimate.

## Plan and gates

- Extract every RC offset, repeated-holder field, key, initial value, and
  version-history transition from primary sources and compare all existing
  schema/parser names.
- Inspect official developer-community reports for RC corrections, record
  holder cardinality, deletion/replacement order, and historical layout
  variants.
- Add a minimal official contract against unchanged production code and run it
  red before modifying parser/storage checks.
- Implement one current contract, or explicit old/current dispatch only when
  official evidence establishes multiple physical layouts.
- Validate the exact full SHA with supported Python, full/focused tests,
  disposable PostgreSQL where schema/storage changes require it, one native
  Copilot review, unresolved threads zero, green CI, and a clean worktree.
- STOP on conflicting official evidence, unsafe migration, executable failure,
  base drift, or an unresolved actionable review finding.

## Next safe command

- Extract the RC table and SDK structure from the local official 4.9.0.1/5.0.0
  evidence, then compare the native and standard `RECORD` schemas field by
  field before writing the red contract.
