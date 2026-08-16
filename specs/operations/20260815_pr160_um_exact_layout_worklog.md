# PR #160 UM exact-layout validation worklog

## Scope and provenance

- Objective: make the new JV-Data Ver.4.9.0.1 UM parser accept only the exact
  1609-byte layout with the exact terminal `CRLF`, so unsupported or truncated
  records cannot be imported as partial horse-master rows.
- Minimal scope: `src/parser/um_parser.py`, focused UM parser tests, and this
  worklog. Existing schema/layout changes in the PR are reviewed but are not
  broadened unless a concrete defect is found.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_pr160_fix`
- Branch: `claude/um-parser-jvdata-4901-layout` (cross-repository PR branch in
  `hayato1980/jrvltsql`)
- PR: https://github.com/miyamamoto/jrvltsql/pull/160
- Base branch: `master`
- Latest base full SHA at iteration start:
  `0001ea2179db28be49938f4b7f178a6bd70c0942`
- Starting PR head full SHA:
  `f9ca84852fc78f4a574ea165b5c0c27a4c8d30d2`
- Base-update merge commit full SHA:
  `3b1748c04659fd3772d772dc28d896041865667d`
- Related release: `v1.6.10`
- Dependency: PR #159 was merged first as
  `0001ea2179db28be49938f4b7f178a6bd70c0942`; PR #160 now contains that latest
  `master`. PR #161 remains downstream of this iteration.

## Claude Code sessions

- Implementation/review-fix session ID:
  `3330d708-31bf-4354-a34b-4463a096ae22`
- Planned independent final-review session ID:
  `24d2b051-a331-462b-8de1-ce6ae22d05bf`
- Model for both: `--model fable`
- Selection reason: this change is a parser validity gate. Accepting an
  unsupported length or delimiter would fail open and can persist structurally
  incomplete master data, so boundary behavior has high rollback cost.
- The implementation session is reused for any review correction in this
  iteration. The final-review session is separate and read-only.

## Status at start

- Observed: original PR Actions test/lint and CodeRabbit status succeeded on
  `f9ca84852fc78f4a574ea165b5c0c27a4c8d30d2`.
- Observed: CodeRabbit's outside-diff Major finding is valid. `UMParser.parse`
  only warns below 200 bytes, validates a delimiter only at lengths at least
  1609, accepts both `CRLF` and `LFCR`, and proceeds to field extraction after
  either warning. A legacy 1577-byte record therefore returns a partial dict.
- Required contract: exact length 1609 and exact terminal bytes `b"\r\n"`.
  Shorter, longer, legacy 1577-byte, and wrong-delimiter records must return
  `None` before field extraction; the valid 1609-byte counterpart must remain
  green.
- Review threads: zero. The actionable finding is in the review body outside
  the diff, so resolution evidence must be recorded in the PR conversation.
- Base update: merged latest `origin/master` into the PR branch without
  conflicts; no implementation edits have been made in this iteration.
- Worktree: clean before creating this worklog.

## Red-first requirement

- Before production edits, add the minimum focused negative test(s) that prove
  unsupported UM records are currently accepted. Run them on unchanged
  production code and record the exact failing assertion/exit status here.
- Keep a valid exact-layout positive counterpart green.
- A warning followed by a parsed dict is not rejection; invalid inputs must
  return `None` without throwing.

## Remaining gates

- Red-first evidence on unchanged production code.
- Minimal implementation and focused/workflow-equivalent local tests on the
  eventual candidate full SHA.
- Source-branch drift reconciliation before push.
- GitHub Actions success on the candidate full SHA.
- Independent Claude Code GREEN review on the candidate full SHA.
- All review threads resolved, PR evidence comment, matching local/remote/PR
  head SHA, CLEAN merge state, and clean worktree.

## Next safe command

Start Claude Code implementation session
`3330d708-31bf-4354-a34b-4463a096ae22` with model `fable`; require red-first
failure before changing `UMParser.parse`.

## Implementation session log (3330d708, 2026-08-15)

### Red-first evidence on unchanged production code

- Test added first: `tests/test_um_parser_layout.py` gained
  `TestUMParserExactLayoutEnforcement` with one parameterized negative test
  `test_unsupported_record_returns_none` (ids: `legacy-1577-crlf`,
  `short-1608`, `long-1610`, `delimiter-lfcr`, `delimiter-spaces`) plus the
  explicit positive counterpart
  `test_exact_1609_byte_crlf_record_is_accepted`.
- Command:
  `python3 -m pytest tests/test_um_parser_layout.py::TestUMParserExactLayoutEnforcement -p no:cacheprovider --no-cov -q`
- Result on unchanged `src/parser/um_parser.py`: exit status `1`,
  `5 failed, 1 passed`. All five negative ids failed at
  `tests/test_um_parser_layout.py:160` with
  `AssertionError: assert {'Bamei': 'テストウマアルファ', ...} is None` —
  i.e. `UMParser.parse` returned a fully populated dict for the legacy
  1577-byte record, a 1608-byte short record, a 1610-byte long record, an
  LFCR-terminated 1609-byte record, and a space-terminated 1609-byte record.
  The positive 1609-byte CRLF case passed, confirming the failure is the
  accept-invalid behavior, not the fixture.

### Implementation

- `src/parser/um_parser.py` (`UMParser.parse`): replaced the two lenient
  checks (warn below 200 bytes; warn on non-CR/LF delimiter only when
  `len(data) >= 1609`, accepting both `b"\r\n"` and `b"\n\r"`) with strict
  pre-extraction guards mirroring the existing `SEParser.parse` contract:
  - `len(data) != RECORD_LENGTH` (1609) → log warning, `return None`.
  - `data[1607:1609] != b"\r\n"` → log warning, `return None`.
  Both guards run before any field extraction, log via `self.logger.warning`,
  and never raise; the surrounding `try/except` → `None` error path is
  unchanged. No schema, factory, or importer changes.
- Caller safety check: records reach `parser.parse` as raw bytes via
  `ParserFactory.parse` (`src/realtime/updater.py:205`,
  `src/fetcher/historical.py:516`, `src/fetcher/base.py:191`) with the
  terminal CRLF intact — the already-strict SE parser (`se_parser.py:52-59`)
  proves the delimiter is not stripped upstream.
- `tests/test_parsers.py`: two fixtures encoded the old lenient contract and
  failed after the fix (4 UM-only failures: `test_parser_parse_sample_data`,
  `test_parser_output_has_common_fields`, `test_parser_output_record_spec_value`,
  `test_parser_handles_exact_length`). Updated them following the SE
  precedent already in the file: `sample_data` UM length 969 → 1609, and the
  CRLF-terminator special case extended from `("SE",)` to `("SE", "UM")` in
  both the fixture and `test_parser_handles_exact_length`.

### Validation on the fixed code

- `python3 -m pytest tests/test_um_parser_layout.py -q` → `99 passed`.
- `python3 -m pytest tests/test_um_parser_layout.py tests/test_parsers.py
  tests/test_parser_compatibility.py tests/test_jvdata490_layouts.py -q` →
  `717 passed`, exit 0. (`test_parser_compatibility.py` needed no edits: its
  minimal-data test only asserts on a non-None result.)
- `python3 -m pytest tests/test_all_schemas.py tests/test_table_mappings.py
  tests/test_e2e_comprehensive.py tests/test_jvd_self_repair.py -q` →
  `45 passed, 3 skipped`, exit 0 (UM references there are schema-name lists
  and mocks, unaffected).
- Blocking lint, same selection as CI:
  `python3 -m flake8 src tests --count --select=E9,F63,F7,F82` → `0`, exit 0.
- Style lint on changed files (CI runs this exit-zero):
  `flake8 --max-complexity=10 --max-line-length=127` reports only 3 F841
  warnings in `tests/test_parsers.py` that also exist on unchanged HEAD
  (verified via `git stash` round-trip); none are in edited lines.
- `git diff --check` → clean, exit 0.
- Changed files: `src/parser/um_parser.py`, `tests/test_parsers.py`,
  `tests/test_um_parser_layout.py`, plus this worklog. Not committed; no
  GitHub state touched, per session constraints.

## Codex candidate verification before commit

- Environment: CPython 3.12.11 from `uv sync --frozen --extra dev --extra
  postgres --python 3.12`.
- Focused parser/layout/compatibility command on the current tree:
  `pytest tests/test_um_parser_layout.py tests/test_parsers.py
  tests/test_parser_compatibility.py tests/test_jvdata490_layouts.py -q
  --no-cov` → `717 passed`, exit 0.
- Schema/UM-reference command initially stopped at collection because the
  locked dev extras do not install `python-dotenv`, which the pre-existing
  `tests/test_all_schemas.py` imports. Installed `python-dotenv` into the local
  virtualenv only (no project/lockfile change), then reran the same command →
  `45 passed, 3 skipped`, exit 0. This was an environment dependency gap, not
  a product assertion failure.
- Exact test list from `.github/workflows/test.yml`, including coverage →
  `656 passed, 2 skipped, 3 subtests passed`, exit 0. The new compact
  exact-layout test file is additionally covered by the focused 717-test run.
- Blocking flake8 gate on the repository → `0` findings, exit 0.
- Informational mypy command → 85 existing errors in 22 files, exit 1; the
  workflow marks this step `continue-on-error`. No error is in
  `src/parser/um_parser.py`.
- `git diff --check` → exit 0.
- Source drift check: contributor source remains
  `f9ca84852fc78f4a574ea165b5c0c27a4c8d30d2`; latest `origin/master` remains
  `0001ea2179db28be49938f4b7f178a6bd70c0942`; local base-update HEAD before the
  candidate commit is `3b1748c04659fd3772d772dc28d896041865667d`.
- Candidate is ready to commit. After commit, rerun the necessary focused and
  workflow-equivalent checks on the resulting full SHA before push.

## STOP conditions

- Stop before push if the contributor source branch moves away from
  `f9ca84852fc78f4a574ea165b5c0c27a4c8d30d2` without reconciliation.
- Stop before merge if an unsupported record can still return a dict, a valid
  1609-byte CRLF record fails, any focused/workflow-equivalent test fails, the
  final Claude review is not GREEN, an unresolved review thread exists, the
  PR head differs from the tested full SHA, or the worktree is dirty.
