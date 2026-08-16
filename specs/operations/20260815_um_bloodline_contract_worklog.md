# UM three-generation pedigree contract worklog

## Iteration identity

- Started: 2026-08-15 JST
- Objective: resolve the remaining official-spec gap reported in issue #156 by
  proving whether the current `UM` parser reads all 14 three-generation
  pedigree slots and every following field at the official byte offsets, then
  apply the smallest correction if the current contract is still wrong.
- Minimum scope: `UM` parser/layout, directly coupled schema/import paths,
  focused byte-level regression tests, migration/reimport guidance if stored
  rows are affected, and directly affected documentation.
- Repository: `miyamamoto/jrvltsql`
- Worktree: `$WORKSPACE/20260815_jrvltsql_um_bloodline`
- Branch: `agent/um-bloodline-contract-20260815`
- Base / initial HEAD / `origin/master` full SHA:
  `dec167b10426aa74284a4d3a1745638af98c2b96`
- Related issue: #156.
- Dependency: PR #169 is merged at the base SHA; this iteration is independent
  of the `HappyoTime` storage correction.
- Implementer and reviewer: Codex. Claude Code is not used.

## Initial evidence and decision boundary

- Issue #156 reports an observed model of `block start + 2` and 48 bytes per
  slot versus the official 46-byte slot (`HansyokuNum` 10 bytes + `Bamei` 36
  bytes), corrupting all 14 pedigree entries and the fields after the block.
- PR/commit history includes later `UM` 1609-byte layout corrections, so the
  report may already be fixed. The issue will not be closed from code reading
  alone: current and historical official definitions, parser field offsets,
  a synthetic sentinel record, and relevant existing tests must agree.
- If a new or modified validator is required, its negative case must be run
  against the pre-fix implementation first and fail for the intended reason.
- If current production already passes the official byte-level contract, do
  not manufacture a code change. Record the proof on #156 and close it only if
  every reported affected field class is covered.

## Official and community verification

- Current official artifact: JRA-VAN Data Lab SDK 5.0.0 64-bit,
  `https://jra-van.jp/dlb/sdv/sdk/JVDTLABSDK500_64bit.zip`.
- Archive SHA-256:
  `21f4d54706ff050e383f21f3571f59ffe8de38ed46a01be3e5b7756ee957f9d7`.
- Official `JVData_Struct.py` SHA-256:
  `8994f985fce846f1b4fcbc3ddf2a5c6394c586a458478346891222b3b61e4ee3`.
- `JV_UM_UMA.SetDataB` reads the 14 pedigree entries as
  `MidB2B(b, 205 + 46 * i, 46)`. Each `KETTO3_INFO` is a 10-byte
  `HansyokuNum` followed by a 36-byte `Bamei`; the following official
  positions are `TozaiCD=849`, `ChokyosiCode=850`, `BreederCode=883`, and
  `BanusiCode=983`.
- The official 2023 upgrade notice records the 4.8.0.2 to 4.9.0 format change.
  JRA-VAN support further states in the developer community thread
  `https://developer.jra-van.jp/t/topic/215` that a new setup with the new
  dataspec returns pre-2023 data in the new physical shape, and that old and
  new stores must not be mixed. The current parser's exact-1609-byte-only
  policy is therefore deliberate compatibility with the supported DIFN setup
  path, not an omission of a required mixed-layout dispatch.
- The issue's reporter, `hayato1980`, also authored PR #160. Its real DIFN
  validation imported 4,034 `NL_UM` rows, reached pedigree slot 14, and found
  every populated breeding number to be ten digits. PR #160 merged as
  `e55b1f93f4661cf83cc7d890ebe6ee7399f354ab`.
- A follow-up history audit found that the reachable pre-PR-160 parser already
  used the current 46-byte pedigree stride. PR #160 extended the parser through
  the 1,609-byte record tail, made length/CRLF validation strict, and added the
  exhaustive byte-level proof; it did not introduce the stride itself. The
  exact producer/version that created the reporter's previously corrupted
  stored rows is therefore not reproducible from reachable `um_parser.py`
  history and must not be attributed to that PR's parent revision.

## Base-SHA verification

- Verified production base:
  `dec167b10426aa74284a4d3a1745638af98c2b96`.
- The current parser uses zero-based `ketto_pos=204`, increments by exactly
  46 bytes, and reads ten plus 36 bytes for every slot. Its following offsets
  are the official one-based positions minus one.
- `tests/test_um_parser_layout.py` builds a gap-free 1,609-byte CP932 sentinel
  record with unique values for all 14 slots and all subsequent trainer,
  breeder, birthplace, owner, earnings, result-count, running-style, race-count,
  and terminal-CRLF fields. It also rejects legacy 1,577-byte, short, long, and
  malformed-delimiter inputs before field extraction.
- Command: `python3 -m pytest -q tests/test_um_parser_layout.py
  tests/test_parser_compatibility.py
  --basetemp=/tmp/jrvltsql-um156-base-dec167b`.
- Result: **308 passed**, exit 0.
- Conclusion: the corruption described in issue #156 is not present in the
  current base, and the current supported DIFN import path is covered by an
  exact official-layout sentinel. Its historical producer is not reproducible
  from reachable parser history. No production or test change is justified;
  any rows known to have been produced by the corrupt path still require
  reimport with a current parser and current-format Data Lab setup.

## GitHub resolution

- Added an evidence comment to issue #156 identifying PR #160, current and
  official offsets, the 308-test result, the DIFN setup contract, and the need
  to reimport any already-corrupted stored rows.
- Closed issue #156 as `completed` at 2026-08-15T09:59:49Z. This was a GitHub
  metadata change only; no repository code was changed by the closure.
- Codex review of candidate
  `5d8cdf051e52ad691de470f14535fea05d3f8312` found no runtime or test issue,
  while its history investigation exposed the attribution nuance above. A
  transparent correction to #156 was therefore required before publishing
  this audit, so the closed issue distinguishes the proven current contract
  from the unknown historical producer.
- Added that correction at
  `https://github.com/miyamamoto/jrvltsql/issues/156#issuecomment-5301737803`
  at 2026-08-15T10:05:39Z. Issue #156 remains closed as completed; the comment
  explicitly limits the resolution to the proven current contract and does not
  claim a reproducible historical producer.
- GitHub Codex then identified a P2 proof weakness: several one-byte fields,
  three earnings fields, and blank text fields shared decoded values, so a
  swapped parser slice could pass the claimed exact-offset test. Strengthened
  the fixture so every parsed field has a distinct decoded sentinel and added
  an invariant that rejects future duplicate sentinels.
- Red proof before committing the test fix: temporarily changed
  `RuikeiHonsyoSyogai` to read the `RuikeiFukaSyogai` slice, then ran its one
  parametrized case. It failed as intended with
  `assert '000123404' == '000123402'`, exit 1. Restored the production parser
  without change; the strengthened layout suite then passed 100 tests, exit 0.

## Current state and next safe commands

1. Published candidate `b9e42cfec5dba90ce1304dc4421752d381ee1a43`
   on branch `agent/um-bloodline-contract-20260815` and opened ready PR #170:
   `https://github.com/miyamamoto/jrvltsql/pull/170`. Requested the GitHub
   native Copilot reviewer once at PR creation. The exact candidate proof was
   308 passed plus critical flake8 and `git diff --check`, all exit 0.
2. Commit the review-driven sentinel-test correction, push the resulting final
   candidate, and verify its focused tests, Actions, accumulated reviews,
   unresolved-thread count, and clean worktree once as the final gate. Record
   the final full SHA and gate evidence on PR #170 because a commit cannot
   self-record its SHA.
3. After merge, start a separate worktree from the new `origin/master` for the
   next genuine compatibility gap. The audit matrix identifies `HN` current
   10-byte registration-number offsets as the smallest remaining byte-level
   corruption item; re-verify it against SDK 5.0.0 before implementation.

## STOP conditions

- Do not infer character positions from decoded Unicode; JV-Data offsets are
  byte-based CP932 offsets.
- Do not close #156 solely because a later commit mentions `UM`; prove the 14
  slot stride and at least the first fields after the block.
- Do not merge if any current/historical supported layout, storage path, exact
  candidate test, review finding, or PR thread remains unresolved.
