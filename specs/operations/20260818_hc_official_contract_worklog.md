# HC official contract worklog

## Iteration start (2026-08-18)

- Objective: audit and implement the complete current JRA-VAN `HC` hill-training
  contract against the pinned official 4.8.0.2/4.9.0.1 workbooks and SDK 5.0
  source/manifest, then prove parser, native/standard storage, exact identity,
  importer/realtime behavior, migration safety, documentation and distribution
  behavior on SQLite and fresh PostgreSQL.
- Minimum scope: `HC` only. Do not mix the remaining `TC` or `CC` record
  iterations, NAR implementation, MCP changes, release tagging, or any 64-bit
  support claim into this PR.
- Repository: `miyamamoto/jrvltsql`.
- Dedicated worktree:
  `/home/keiba/scratch/20260818_jrvltsql_hc_official`.
- Branch: `agent/hc-official-contract-20260818`.
- Base/HEAD/origin master at start:
  `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a` (HS PR #212 squash merge).
- Published production release remains `v1.6.10`; source version is the
  unreleased `2.0.0.dev0`. This iteration does not publish either artifact.
- Dependency order: complete and merge this HC iteration first; start TC/CC
  only from the resulting latest master; run the final cumulative official-doc,
  real-provider-storage and release-document audit after all record iterations;
  only then release jrvltsql and proceed to jrvltsql-nar and jvlink-mcp-server.

## Initial risk and verification plan

- Existing reconstruction is only a 60-byte layout smoke. The initial audit
  must independently pin every physical span, current/historical status and
  key rule, unit/sentinel semantics, native `NL_HC`, standard `HANRO`, importer
  and realtime ownership, schema constraint/type/nullability behavior, and
  metadata/documentation claims.
- Before changing a parser/validator/schema gate, add one compact official
  negative contract and run it on this unchanged base to prove red; retain the
  paired provider-valid green. Do not add one test function per reviewer
  hypothesis.
- Test real durable rows rather than parser-only success: provider-order
  updates/deletes, two distinct official keys, same-key revision, both batch
  importers, single-record, auto-commit true/false, SQLite, fresh PostgreSQL and
  Dual orientation where relevant.
- Use Claude Code `--model fable` for the complex aggregated implementation if
  the CLI service is available; otherwise record the failure and use Codex with
  two independent critical reviews on one frozen candidate SHA. Reuse one
  Claude session for this worktree/iteration.
- STOP on official-source ambiguity that changes storage meaning, any
  provider-valid over-rejection, partial/silent field loss, wrong-key collapse,
  mutation-before-schema rejection, stats/durability divergence, transaction
  ownership leak, candidate drift during review, failed executed CI step,
  unresolved thread, or unsupported SDK/64-bit/release claim.

## Next safe action

1. Freeze start SHA and clean state, then extract the HC oracle from the pinned
   official sources without editing production.
2. Compare that oracle to parser/schema/mapping/importer/realtime/tests/docs and
   reproduce concrete gaps on SQLite.
3. Add one compact red-first HC contract, then implement one aggregated repair.

## Initial official-source audit (2026-08-18)

- The start identity remained exact: HEAD and `origin/master` were both
  `ed39ac78aa371e7ce4e18a87d8a25c50a07fe78a`; the only worktree change was
  this intentional worklog.
- Pinned primary artifacts were re-read from
  `/home/keiba/scratch/20260815_jvdata_official_materials`:
  - `JV-Data4802.xlsx` SHA-256
    `6a567f10b601115eca350571f36d27d9d28bd2d3835ea72b5bc057711155d4a7`;
  - `JV-Data4901.xlsx` SHA-256
    `23bafd375f704acbdd696b5032ac1619f17d47e882587d6e7954b610527a8234`;
  - `JV-Data4901.pdf` SHA-256
    `b6c21aae4ccbba6a71c5e8065609c4fbb1ccee826c16e7d99ca6ecf7a4101522`.
- Both current workbooks define the same gap-free 60-byte HC record in
  `フォーマット` rows 1142-1167. The SDK 5.0 manifest independently binds
  `HC` to `JV_HC_HANRO`, width 60, with the same 15 logical fields and CRLF at
  bytes 59-60.
- The official ordered identity is
  `(TresenKubun, ChokyoDate, ChokyoTime, KettoNum)`. `DataKubun` is exactly
  `1` (initial value) or `0` (exact record deletion). The body owns seven
  fixed-width numeric timing fields; `0000`/`000` are documented measurement-
  failure values and their units are tenths of a second.
- `特記事項` rows 195-198 state that SLOP provides data from 2003 onward and
  that Miho used 600m measurement through 2004-11-29 and 800m from
  2004-11-30. This changes interpretation/availability, not physical size.
  The change history only records wording/unit additions (rows 170, 174 and
  344); no alternate HC physical layout is documented in the two pinned
  current workbooks or SDK manifest.
- `データ提供タイミング・提供単位` row 26 defines irregular daily delivery,
  one complete day/training-center unit, and one-year retention. HC is
  accumulated through SLOP, not an RT table in the current application.

## Claude availability and fallback

- The selected complex-task model was Claude Code `--model fable` (CLI
  2.1.233), because this iteration combines a validator, exact-delete order,
  cross-backend schema gates and migration safety. The audit-only launch used
  session id `8fd313d0-4bc7-4b46-9cb4-d03e4f4ea659` but failed before a usable
  session was created: the local OAuth session was expired and could not be
  refreshed. No repository mutation came from Claude and there is no usable
  session to resume.
- Per the user-approved fallback, Codex will implement only after red-first
  evidence, and at least two independent Codex reviewers will audit one frozen
  candidate SHA before PR/release action.
