# BaseParser byte-offset compatibility worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: audit and correct the generic parser boundary so official
  byte-position layouts remain correct when earlier CP932 fields contain
  multibyte Japanese text, without changing bespoke byte-first parsers.
- Minimum scope: `src/parser/base.py`, subclasses that actually consume its
  generic field extraction path, the smallest regression fixtures/tests, and
  directly affected parser documentation.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_base_parser_bytes`
- Branch: `agent/base-parser-byte-offset-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `fc5d4fb08533021b5fbc83e39a499e92ef8929b6`
- Previous iteration: PR #165 merged as
  `fc5d4fb08533021b5fbc83e39a499e92ef8929b6` after exact-source bridge runtime
  validation; its worktree and local branch were removed.
- Reviewer: Codex. Claude Code and external coding agents are not used.

## Initial scope and safety

- Treat positions and lengths in official JV-Data layouts as byte offsets.
- Inventory every concrete `BaseParser` consumer before changing the shared
  method; do not assume bespoke parsers use the generic path.
- Add one minimal record with CP932 multibyte content before a later ASCII
  field and prove the later field fails on the current base SHA before repair.
  Retain the paired ASCII/normal case.
- Missing/invalid input must remain an explicit parse failure, not a silent
  pass. Do not broaden decoding error suppression without a proven legacy
  contract.
- No authenticated JV-Link call, database write, collector mutation, or model
  work is needed for this pure parser-contract iteration.

## Official contract and consumer inventory

- The public SDK page was rechecked on 2026-08-15 and still lists SDK
  `4.9.0.2` plus JV-Data specification `4.9.0.1`:
  <https://jra-van.jp/dlb/sdv/sdk.html>. The official 4.9 C# and VB structure
  sources both implement `MidB2S` by passing a byte array, byte start, and byte
  length directly to Shift-JIS `GetString`; they never index a decoded string.
- The official 2026-07-31 64-bit Python structure package captured by the prior
  specification audit defines the same `MidB2S` contract as a byte slice
  followed by Shift-JIS decoding:
  `b[start-1:start-1+length].decode(...)`. Its docstring explicitly calls the
  start and length byte positions. The published 4.9 and later 2026 structure
  generations therefore agree; this is not a format-boundary behavior that
  requires separate old/new parsing modes.
- `BaseParser.parse` currently decodes the entire CP932 record to `str` and
  then applies `FieldDef.start/length`. Every double-byte Japanese character
  before a later field shortens the decoded character index by one relative to
  the byte index, so later fields are read from the wrong bytes. The existing
  comment that replacement decoding preserves field positions is false for
  multibyte text.
- Factory inventory shows 11 concrete parsers use `BaseParser.parse` directly:
  `BT`, `CC`, `CK`, `CS`, `HC`, `JC`, realtime `RC`, `TC`, `WC`, `WE`, and
  `WH`. `CK`, `JC`, and realtime `RC` contain Japanese name fields before later
  fields and are directly exposed to the offset shift. `AV` already documents
  and implements byte-first extraction; the remaining bespoke parsers override
  `parse` and are outside this shared-method change.

## Red-first plan

- Add one tiny concrete BaseParser test with a four-byte middle field and a
  later two-byte ASCII field. Parameterize it with an ASCII four-character
  normal case and the CP932 four-byte/two-character value `日本`. The old code
  must retain the ASCII pass but misread the later field in the multibyte case.

## Red-first observation

- Before production repair,
  `pytest -q tests/test_parser.py::TestBaseParser::test_field_positions_are_byte_offsets
  --no-cov` produced **1 passed, 1 failed**. The ASCII case stayed green; in
  the CP932 multibyte case the later byte-positioned `Tail` field was `None`
  instead of `42`. This directly demonstrates the offset shift rather than a
  general parser failure.

## Implementation and local validation

- `BaseParser` now verifies the record type from the first two bytes and passes
  raw bytes to `_extract_field`. Each field is sliced using `FieldDef.start`
  and `length` before CP932 decoding. The existing replacement-decoding,
  whitespace stripping, conversion, per-field failure, empty-record, and
  record-type mismatch behavior is otherwise unchanged.
- The paired red test passed **2/2** after repair. A single-process focused run
  covering base/parser tests, all parser factory cases, compatibility cases,
  and registered fixtures passed **755 tests**. Targeted mypy, fatal flake8,
  compileall, and `git diff --check` passed.
- The first isolated full-suite run had two transient CLI failures in
  `status` and `version`; both passed immediately when rerun alone. No parser
  assertion failed. With no other pytest process present, the complete isolated
  suite was rerun unchanged and passed **1829 tests**, skipped 38
  environment-specific tests, passed 5 subtests, and emitted only the three
  pre-existing `PytestReturnNotNoneWarning` warnings.

## Codex pre-candidate review

- P0/P1: none after repair. This corrects a data-integrity boundary to match
  official byte offsets; it does not change field definitions, layouts,
  database schemas, record selection, or result/odds handling.
- The regression checks the later field first, so it cannot pass merely because
  the Japanese field itself happens to decode. The paired ASCII case guards
  against an over-strict implementation.
- Bespoke parsers are not routed through the changed method. Parser-specific
  incomplete layouts, including `WH`, remain separate iterations rather than
  being mixed into this shared contract PR.

## PR publication

- Code candidate `247b2e289c19d78ee8726de269687c0881f4b695` was
  pushed and opened as ready-for-review PR #166 against `master`:
  <https://github.com/miyamamoto/jrvltsql/pull/166>.
- The PR contains only the BaseParser byte-order repair, its paired regression,
  and this worklog. Final candidate SHA, repeated exact-SHA checks, review
  verdict, unresolved-thread count, and merge metadata belong in PR metadata
  after this tracked publication update to avoid a self-referential commit
  loop.

## Next safe command

Commit and push this publication update, rerun focused/full tests on the new
exact full SHA, and merge only after exact-SHA CI, final Codex review, and
unresolved-thread count are green.

## STOP conditions

- Stop if field positions are character-based in a concrete documented layout
  rather than byte-based.
- Split a parser-specific layout correction into a later PR if it is not
  required to make the shared byte-extraction contract correct.
- Do not merge with a missing red-first observation, failing focused/full test,
  unresolved review thread, dirty worktree, or SHA mismatch.
