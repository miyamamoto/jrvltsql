# data_support.md readability restructure worklog

## Start state (2026-08-18)

- Objective: make `docs/data_support.md` easier to read without changing
  the set of facts it states (user request: 「わかりやすい形にしてほしい。
  ただし嘘は絶対に入れないで」).
- Scope: docs only. Split the 655-line page into a reader entry page
  (`docs/data_support.md`) and a per-record contract page
  (`docs/record_contracts.md`); add the new page to `mkdocs.yml` nav,
  `docs/index.md`, and the README docs table. No parser/schema/CLI change.
- Repository: `miyamamoto/jrvltsql`.
- Worktree: `/home/keiba/scratch/20260818_jrvltsql_docs_readability`.
- Branch: `docs/data-support-readability-20260818`.
- Base and starting HEAD: `36800dcbba37d964653b6581cba7eba873fbdef2`
  (`origin/master`, HN PR #217 squash merge). Worktree was clean.
- Implementer: Claude Code, `claude --model fable` (`claude-fable-5`),
  session id `b3c80966-f901-4d2e-8907-25c80ab2f654`.
- Hard constraints followed: no fact added, dropped, weakened, or
  strengthened; suspected doc/code disagreements are NOT edited in the doc
  and are listed below as 要確認事項; every table / record type / spec ID /
  CLI command / byte count / DataKubun value / primary-key column kept in
  the doc was checked against `src/` and `tests/`.

## Method

1. Read `git show origin/master:docs/data_support.md` and enumerated its
   claims as a numbered checklist (C001–C110, one row per sentence group,
   keyed by old line numbers). Kept in the worktree-local
   `.tmp/claims_checklist.md` (git-ignored); the same mapping is summarised
   in the PR body.
2. Ran four parallel read-only verification passes against the
   implementation and tests, by category:
   - dataspec IDs / options / retired names / realtime specs / CLI
     subcommands and flags / batch files / retention comments
     (`src/jvlink/constants.py`, `src/cli/main.py`, `scripts/*.py`, `*.bat`);
   - table names (native `NL_*`, realtime `RT_*`, timeseries `TS_*`,
     standard-name tables and read-side legacy aliases), column names,
     primary keys, and fail-closed verifier functions
     (`src/database/schema*.py`, `table_mappings.py`, `migration.py`,
     `src/importer/importer.py`);
   - record byte lengths, DataKubun base domains (38 types), historical
     `MakeDate` gates, date boundaries and value rules
     (`src/parser/*_parser.py`, `status_domain.py`, `code_domains.py`,
     `tests/fixtures/official_layout/*`, `tests/test_*_official_contract.py`);
   - transaction / rollback / `TransactionRecoveryError` / realtime grouped
     batch / 0B14 snapshot / WF, CK, KS, CH coupling semantics
     (`src/importer/`, `src/realtime/updater.py`,
     `src/services/realtime_monitor.py`, `src/cli/main.py`).
   Result: every identifier named in the doc exists; all 38 DataKubun rows,
   all byte lengths, all primary-key lists, all CLI subcommands/flags, and
   all realtime spec → record-type mappings match code. Items that could
   not be confirmed or where wording differs from code are listed under
   要確認事項 and were left unchanged in the doc.
3. Restructured:
   - `docs/data_support.md` (entry): 「このページの読み方」(3-layer guide +
     表の見方 + 実装上の正本) → 先に結論 → 取得系統 → JVOpen 蓄積系データ →
     JVRTOpen 速報レース・開催情報 → JVRTOpen オッズ・票数 →
     パーサー・テーブル対応 → レコード別の契約・移行手順（要点、1 行 + link）
     → 対象外. Tables kept verbatim; long contract prose moved out.
   - `docs/record_contracts.md` (detail): 共通規則（公式 DataKubun の検証 /
     通常インポートの transaction・rollback 規約 / 速報 grouped batch と時系列
     CLI の transaction 境界 / HappyoTime（MMDDhhmm）/ 0B14 と 0B16 /
     既存 DB からの移行の共通手順 / 旧仕様 dataspec 名）, then 22 record
     sections (WH, WE, AV, JC, TC, CC / HR, SE, JG, WF / HN, UM, BT, KS, CH,
     HS / HC, WC, CS / CK, DM, TM + DM/TM 共通) each with the same
     sub-headings: 公式レイアウト / identity（主キー）/ 保存先 / DataKubun /
     値の扱い（if any）/ 既存 DB からの移行手順.
   - The task listed WH, TC, CC, HN, HC, HS, JG, WF, CK, DM, TM as the
     detail-page targets; the remaining contract paragraphs (HR, SE, WE, AV,
     JC, CS, WC, KS, CH, UM, BT) were moved as well, because leaving them in
     the entry page would contradict the goal of a short entry page. Reason
     is stated in the PR body.
   - Scoping judgment: the old WF paragraph (old lines 586–597) contained
     sentences whose subject is 「速報の通常 grouped batch」, psycopg SELECT
     transactions, validation-only rejection, and 「時系列取得 CLI」. Their
     wording is general and code confirms they are the general realtime
     updater / CLI paths (`src/realtime/updater.py:641-654, 698-728,
     822-849`; `src/importer/importer.py:1689-1732`;
     `src/cli/main.py:1761-1792, 1871-1887`), so they were placed under
     共通規則 with the WF section linking to them. WF-specific sentences
     (batch-wide rollback of WF writes, `inserted` semantics) stayed in WF.
4. Gates on the candidate commit: `mkdocs build --strict` pass (0 anchor
   warnings; every `record_contracts.md#...` target verified in built HTML),
   `python scripts/validate_test_gate.py` → `TEST GATE PASS`, fatal flake8
   (`E9,F63,F7,F82`) → 0, `uv lock --check` pass, `git diff --check` clean.
   Docs-adjacent tests (`tests/test_public_setup_contract.py`,
   `tests/test_quickstart_cli.py -k docs/documentation/notes/contract`) →
   11 passed under the repository-supported Python 3.12 environment.

## Fact-set equality check (how it was done)

- Old → new: each checklist row C001–C110 records the old line range and
  the new file/heading where the statement now lives, and whether it is
  同一 (same wording), 再構成 (bulletised/tabulated only), or 移動 (moved to
  the detail page). All 110 rows have a target; none is dropped.
- New → old: additions were limited to navigation text (「このページの読み方」
  tables, group headings, sub-heading labels), a terminology note (native =
  `NL_*`/`RT_*`; 標準名 = JRA-VAN 標準名モードのテーブル), a
  旧名→現行名 table that repeats the JVOpen table's 旧仕様名 column, a
  「既存 DB からの移行の共通手順」 paragraph that only generalises the
  backup → rebuild → reimport flow every record section already states
  (stop conditions stay per record), and the one-line digests, each a
  strict subset of its record section.
- A clause-by-clause old vs new comparison by an independent reviewer was
  outstanding when this section was first written (see the handoff note
  below; the earlier wording was corrected after review comment
  3804634673). It has since been performed and is recorded in
  「Independent review and repair batch」 below.

## 要確認事項 (doc kept as-is; documented for a later decision)

1. quickstart standard / full: the doc says `MING` and `COMM` are 「full
   quickstart に含めています」 and `TOKU`/`SLOP`/`WOOD`/`HOYU` 「standard /
   full quickstart に含めています」. `scripts/quickstart.py:1858-1888`
   defines `STANDARD_SPECS` and `FULL_SPECS` as identical lists (both include
   `MING` and `COMM`). Not edited.
2. `0B51` key format 「`YYYYMMDD` または WIN5 開催キー」: only the date-keyed
   form is evidenced (`src/jvlink/constants.py:129,137,163-168`,
   `scripts/daily_update.py:48`). Not edited.
3. `JVCourseFile` / `JVCourseFile2` (CS section) and `JVWatchEvent` (0B16 /
   AV) are JV-Link API names; no implementation in `src/` (`JVWatchEvent`
   appears only in comments, e.g. `src/jvlink/constants.py:135`). Kept as
   provider-API references.
4. 2023-08 JV-Data change widths 「繁殖登録番号 8→10 / 生産者コード 6→8 /
   生産者名 70→72」: the repo records whole-record length changes effective
   2023-08-08 (`tests/fixtures/official_layout/jvdata_layout_history.json`)
   and 10-char `HansyokuNum` constants; the 6→8 and 70→72 field widths are
   not stated anywhere in `src/`/`tests/`. Kept.
5. CK 「1物理レコード単位のtransactionで更新」 and WF 「提供順にtransactionで
   置き換え」: happy path uses one transaction per batch with per-record
   parent+children grouping inside (`src/importer/importer.py:6344-6350`,
   `:3341-3363`); per-record transactions only in the `DatabaseError`
   retry (`:6360-6375`). Atomicity holds; granularity wording differs. Kept.
6. `0B14` 「正常終了を確認した同一transaction内で…置換」:
   `src/services/realtime_monitor.py:321-328` issues `replace_date_snapshot`
   right after `JVRTOpen` returns ≥ 0, before the record stream is drained;
   the whole cycle rolls back on any failure (`:280-281`). End state matches;
   timing wording differs. Kept.
7. KS/CH 「本年・前年・累計の3行」: exactly three rows are enforced
   (`src/importer/importer.py:5422-5424`, `:5246-5248`); the labels are not
   in code. Kept.
8. UM UNIQUE/exclusion and deferrable-PK rejection is implemented for the
   standard-name `UMA` via `_verify_replacement_key_constraints`
   (`src/importer/importer.py:2945`, `:3425-3430`); no dedicated native
   `NL_UM` verifier. Kept.
9. DM 「`DMTime`は…5桁文字列」: bare `DMTime` exists in native
   `NL_DM`/`RT_DM` (`src/database/schema.py:373,1663`); `MINING` has
   `DMTime1`..`DMTime18` `VARCHAR(5)` (`schema_jravan.py:835-903`). Kept.
10. `inserted` = provider-order operations: confirmed for realtime
    WF/DM/TM (`src/realtime/updater.py:781,925,999`); importer statistics
    count provider operations only for `_PROVIDER_OPERATION_COUNT_STORAGE_TABLES`
    (`importer.py:692-700`). Kept (doc scopes it to realtime `inserted`).
11. WH 「起動時の schema migration は主キー不一致を検出して停止」: no
    dedicated WH verifier; the generic `verify_table_schema`
    (`src/database/migration.py:421,507-522`) raises, while
    `migrate_table_if_needed` logs and returns `False` without altering
    (`:352-359`). Behaviour matches the doc. Kept.
- Observations, no doc change: `RT_RC` (`src/database/schema.py:2375`) and
  `TS_O3`–`TS_O6` (`schema.py:2548-2640`, retained for compatibility per
  `table_mappings.py:186-187`) exist but are not listed; not added because
  that would be a new fact.

## Independent review and repair batch (Claude Code, 2026-08-19)

Continued in the same Claude Code session (`claude --model fable`,
`claude-fable-5`, session id `b3c80966-f901-4d2e-8907-25c80ab2f654`) after
the 03:00 JST limit reset. Reviewed head: `c33229dccd94b793f985700369ad2c17b9a9b8ed`
(PR #218). Three read-only reviewers ran in parallel, one batch:

- (a) fact-set diff — clause-by-clause old (`origin/master:docs/data_support.md`)
  vs new (`docs/data_support.md`, `docs/record_contracts.md`), concentrating
  on same-words-different-meaning, strength, and scope; plus a check of the
  author's C001–C110 mapping. Result: **0 blocking, 0 omitted, 0 added
  facts, 0 number/identifier changes**; the 9 external topic URLs match by
  count. Findings: 2 should-fix (low), several nits — all "restore the old
  wording" fixes.
- (b) technical accuracy vs `src/` and `tests/` — checked the statements
  moved into shared sections, every identifier in the digest tables, the
  terminology note, and all anchors. Result: **0 blocking**; the shared
  「速報 grouped batch と時系列 CLI の transaction 境界」 and 「0B14 の日単位
  snapshot 置換と 0B16」 sections hold on the general realtime updater / CLI
  paths (`src/realtime/updater.py:641-654, 694-720, 748-797, 820-849`,
  `src/importer/importer.py:1689-1732`, `src/cli/main.py:1761-1790, 1871,
  1884-1887`, `src/realtime/updater.py:129-152`,
  `src/services/realtime_monitor.py:326-328`), not only for WF/TC. Findings:
  1 should-fix (terminology note over-generalised 「速報」), nits.
- (c) readability / structure / rendering — `mkdocs build --strict` pass,
  all 40 fragments resolve in the built HTML, tables and nested lists render.
  Findings: 6 should-fix (structure only), nits.

Deduplicated repair batch (one commit, no fact added, dropped, or reworded
in strength):

1. Restored old wording where a digest or shared sentence had drifted:
   - digest rows: 「成功時に caller 側 transaction を勝手に commit しない」;
     HappyoTime row scoped to 旧版の速報開催情報標準名テーブル・`ODDS_*_HEAD`
     の `HappyoTime` が `TIMESTAMP`; TC row 「`COMMENT` しかない構成を
     `HASSOU_JIKOKU_CHANGE` へ自動転用しない」; HR row 「2004-08-14 より前の
     通常 record」; KS/CH rows 「旧 772 / 592 バイト復元データは受け付けない」;
   - shared migration flow: dropped the uniformly added 「保持期間内」 and
     「対象テーブルだけ」 (old text says these only for some records), listed
     「起動時」 among the stop timings, 「停止（拒否）」, 「再取込元（記載が
     ある場合）」; digest row updated the same way;
   - AV migration bullet restored the causal 「自動的な PK 変更は行わないため、
     DB をバックアップし…」;
   - removed the new terminology sentence 「蓄積系 = JVOpen / 速報 = JVRTOpen」
     (over-general; the reviewer's proposed replacement would have added a
     claim about 0B41/0B42 routing, so it was deleted instead of edited);
   - 「レコード別の差分」→「レコード別の補足」; TC removed from the 0B14
     補足 list (TC only links back).
2. Structure / navigation (no text meaning changed): entry page order is now
   読み方 → 先に結論 → 表の見方（凡例＋実装上の正本）→ 取得系統; the 3-layer
   table names the actual sections and points to the digest; the sentence
   under the JVRTOpen 速報 table became three link bullets; the digest is
   split into the same five groups as the detail page with linked group
   labels; detail-page sub-heading labels are bold; group heading renamed
   「速報馬体重・開催情報系」; `MakeDate` boundaries are a 3-row table;
   four long bullets split at sentence boundaries (HR, WF ×2, DM/TM); KS/CH
   gained a `DataKubun` pointer to the shared base-domain table; DM/TM tail
   lines point to DM/TM 共通 for DataKubun as well; HS transaction bullet
   links back to the shared rule; HappyoTime migration bullet links to the
   shared flow; CC links 日単位 snapshot 置換 to the shared section.
3. Terminology: 「exact delete」→「exact erase」 (SLOP row; same page and HC
   section already use erase); 0B20 row 「パーサー・スキーマのみ」 to match
   the legend.
4. `mkdocs.yml`: `validation: links: anchors: warn` so that `--strict` now
   fails on a broken fragment (proved: a deliberately broken
   `record_contracts.md#wh-broken` aborted the strict build with 1 warning;
   restored). Reviewer (b) noted the previous pass was real but weak.

Refuted or not applied (with reason):

- CodeRabbit thread 3805258712 asked to add KS/CH key columns
  (`KisyuCode`, `ChokyosiCode`), CK's seven key names, and native vs standard
  DM/TM keys. Not applied: those facts are not in the old page and this PR
  is a fact-preserving restructure; adding them needs its own evidence PR.
  The DataKubun part is already covered by the shared table; pointers added.
- (b) proposed wording for the terminology note added a routing claim →
  sentence removed instead (see above).
- (c) suggested merging the three near-identical 「project policy」 sentences
  (HN/HS/HC) and compressing CC's 0B14 bullet → not merged (HN says 「物理」,
  merging could strengthen HS/HC); CC kept, link added.
- (c) suggested a gloss for 「mutation」 → not added (new definition).
- (c) suggested nesting the nav and updating `RELEASE_NOTES.md` /
  `CHANGELOG.md` pointers → not done (history files; entry page links to the
  detail page). Mentioned in the PR body.
- (a) noted `.tmp/claims_checklist.md` legend/line-range nits → fixed in the
  local (git-ignored) checklist.

Maintainer decisions received (Devin, 2026-08-18 23:50 JST) on 要確認事項,
applied as "do not touch in this PR": item 4 confirmed correct by the
official JV-Data change history (no edit needed); item 1 (quickstart
standard/full) and item 2 (`0B51` key wording) are doc errors to be fixed in
a separate PR; item 8 (UM replacement-key check missing on native `NL_UM`)
is an implementation gap for a separate red-first iteration.

Gates after the repair batch: `mkdocs build --strict` pass (with anchor
validation, 0 warnings; 0 unresolved fragments by HTML-id check),
`python scripts/validate_test_gate.py` → `TEST GATE PASS`, fatal flake8
(`E9,F63,F7,F82`) → 0, `uv lock --check` pass, `git diff --check` clean,
docs-adjacent tests 11 passed (Python 3.12).

## PR

- PR #218 `docs: split data_support into a reader entry page and per-record
  contracts` (base `master`). Head after the repair batch is recorded in
  the PR comment; merge is left to Devin.

## Handoff note (Devin, 2026-08-18 22:39 JST)

- The implementer session stopped at 22:31 JST on the Claude Code session
  limit (resets 03:00 JST) **after** the restructure commit
  `f558ec6409db7edb1f34ed03da2c00f21f640b38` and its gates, but **before the
  single batched independent review was recorded**. The 「Independent review
  and repair batch」 section above is therefore still empty; treat this PR as
  not yet independently reviewed.
- Devin re-ran the docs gates on that commit: `mkdocs build --strict` pass,
  `python scripts/validate_test_gate.py` => `TEST GATE PASS`,
  `uv lock --check` pass, `git diff --check` clean. Fatal flake8
  (`E9,F63,F7,F82`) reported only vendored `.venv` files, which CI excludes.
- Devin also ran an independent token-level fact check between
  `origin/master:docs/data_support.md` and the new pair
  (`docs/data_support.md` plus `docs/record_contracts.md`): every identifier,
  table name, spec ID, byte count, DataKubun value and numeric literal present
  in the old page is still present in the new pages. The only old tokens absent
  are the English words `backup` and `reimport`, which were unified into the
  Japanese wording. The only new tokens are anchor slugs, the two file names,
  and list numbering, i.e. no new factual token was introduced. This is a
  necessary condition, not a sufficient one: it cannot detect a changed claim
  that reuses the same tokens, which is why the batched independent review is
  still required.
- Next: run the batched independent review at or after 03:00 JST, record it
  here, then merge.
- Update (Claude Code, 2026-08-19): done — see 「Independent review and
  repair batch」 above; the PR is now independently reviewed.

## Next safe command and STOP conditions

- Next: keep PR #218 threads at zero unresolved with evidence; leave merge
  to Devin. Separate follow-ups (not this PR): doc fixes for 要確認事項 1 and
  2 (Devin), red-first fix for 要確認事項 8 (native `NL_UM` replacement-key
  check).
- STOP if a reviewer shows a fact was dropped/added/re-scoped and the fix
  would require choosing between doc and code wording that cannot be
  decided from the repository alone; in that case keep the old wording and
  extend 要確認事項.
- No production DB (192.168.0.220), no provider fetch, no `kps_*`
  container was touched. No credentials recorded.
