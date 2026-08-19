# H1（票数１・全掛式）公式契約 worklog

## 前提

- repository: `github.com/miyamamoto/jrvltsql`
- base: `9aaefe5bb01df5b0e80e5f61f964232e8f0e1df41`（PR #223 merge、UM 契約）
- implementation: `c7a0aef` → `5b30ff2`（branch head、PR #224）
- worktree: `/home/keiba/scratch/20260819_jrvltsql_h1_official`
- branch: `agent/h1-official-contract-20260819`
- 実装: Devin（session `83dda3bd2bb44d7abe83462669c51210`）
- 直列順: HN → SK → UM → **H1** → H6 → O1-O6（真偽・parser）→ O1-O6（無損失
  storage）→ 2.0.0.dev0

## 一次資料

- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.pdf`
  （抽出テキスト `/tmp/jvdata4901.txt`、５．票数１、レコード長 28,955 バイト）
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4802.pdf`
  （抽出テキスト `/tmp/jvdata4802.txt`）
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Link4901.pdf`
- リポジトリ側の公式レイアウト pin: `tests/test_jvdata490_layouts.py`,
  `tests/fixtures/official_layout/*`

公式で確認した H1 の値域:

| 項目 | 公式値 |
| --- | --- |
| データ区分 | `0` 削除 / `2` 前日最終売上 / `4` 最終 / `5` 月曜最終 / `9` レース中止 |
| 発売フラグ 1〜7 | `0` 発売なし / `1` 発売前取消 / `3` 発売後取消 / `7` 発売あり |
| 複勝着払キー | `0` 複勝発売なし / `2` 2着まで / `3` 3着まで |
| 返還馬番/枠番/同枠 | 位置ごとの `0`/`1`、28 / 8 / 8 桁、初期値 `0` |
| 票数 | 11 バイト、単位百円、ALL0 は発売前取消し・発売票数なし |
| 人気順 | 数字（単勝・複勝・枠連 2 桁、馬連・ワイド・馬単・3連複 3 桁）、`--` 発売前取消、`**` 発売後取消、空白 登録なし |
| 票数合計 | 11 バイト × 14 個（返還分票数を含む） |

## 着手前の実測（RED / 現状の欠陥）

`/tmp/probe_h1.py`, `/tmp/probe_h1b.py`, `/tmp/probe_h1c.py`, `/tmp/probe_h1d.py`

1. caller 本文検証が皆無。`MakeDate=notadate` / `JyoCD=X` / `RaceNum=99999` /
   `BetType=Bogus` / `Hyo=-1` / `Ninki=abc` / `HatubaiFlag1=Z` /
   `FukuChakuBaraiKey=9` / `HenkanUma=None` がすべて `imported=1`。
2. strict schema 検証が無い。主キーを 1 列削った `NL_H1` と追加 `UNIQUE` を
   持つ `NL_H1` がどちらも `imported=2` で通る。`OptimizedDataImporter` も
   不正 `JyoCD` を受け付ける（`imported=1`）。
3. 公式の人気順マーカーが失われる。`Ninki="--"` / `"**"` は native `NL_H1`
   （`INTEGER`）で `NULL` になる。標準名も `HYOSU_WAKU` / `HYOSU_UMATAN` /
   `HYOSU_SANREN` が `SMALLINT` のため `**` が `NULL` になる（実測）。
   `HYOSU_TANPUKU` / `HYOSU_UMARENWIDE` だけが `VARCHAR` で保持していた。
4. 消去表 `_OFFICIAL_ERASE_STORAGE_TABLES["H1"]` が
   `{"NL_H1", "RT_H1", "HYO_TANPUKU"}`。`HYO_TANPUKU` は `SCHEMAS` にも
   `JRAVAN_SCHEMAS` にも存在しない別名で、標準名 header/子 table は消去対象に
   入っていなかった。
5. native `NL_H1` / `RT_H1` は 40 列すべて nullable、標準名 6 table も全列
   nullable（key 列を含む）。
6. 赤先行テスト（`tests/test_h1_official_contract.py`）の初回実行は
   `ImportError: cannot import name 'validate_h1_record'` で collection error。

## 実装（GREEN）

- `src/parser/h1_parser.py`: 公式値域の `validate_current_fields` /
  `validate_key_fields` を追加（データ区分、実在日、レースキー、頭数、発売
  フラグ、複勝着払キー、返還フラグ列、賭式ごとの組番幅、票数、人気順、票数合計）。
- `src/importer/importer.py`:
  - `validate_h1_record()`（record type と保存先 table の結合を含む）
  - `verify_h1_storage_schema()`（`verify_table_schema` +
    `_verify_strict_storage_column_contract(allow_extra_columns=False)` +
    CHECK/FK 拒否 + 置換キー検証。owner `HYOSU` の検証は子 table 全部を含む）
  - `_verify_h1_standard_replacement_key()`（標準名は import が作る公式キー
    index だけを許可し、他の UNIQUE/exclusion を拒否）
  - 消去表を実在する 8 table へ修正
  - 空白の人気順を `NULL` にせず空文字で保存
  - batch / 単発 / header の各経路へ検証を配線
- `src/importer/importer_optimized.py`: 同じ検証を optimized 経路へ配線。
- `src/database/schema.py`: `NL_H1` / `RT_H1` の `Ninki` を `TEXT` へ、key 8 列を
  `NOT NULL` へ。`STRICT_H1_STORAGE_TABLES` を schema manager の 4 経路へ配線。
- `src/database/schema_jravan.py`: `HYOSU_WAKU` / `HYOSU_UMATAN` /
  `HYOSU_SANREN` の `Ninki` を `VARCHAR(2)` / `VARCHAR(3)` / `VARCHAR(3)` へ、
  標準名 6 table の公式キー列を `NOT NULL` へ。

### 公式初期値と提供実測の差（明示的な判断）

- 公式仕様の返還エリア初期値は `0`、票数合計は 11 桁数字である。しかし本
  リポジトリには「provider が未設定位置を空白で送る」ことを前提にした無損失
  pin（`tests/test_expanded_record_storage.py::
  test_sqlite_standard_vote_refund_arrays_keep_blank_positions`）が既に存在
  する。テストを緩めず契約を保つため、返還エリアは `0`/`1`/空白のみ、票数合計は
  11 桁数字または空白のみを受け付け、それ以外（`X` 等）と桁落ちは拒否する。
  この判断は `docs/record_contracts.md` に明記した。

## 実測結果

| 対象 | 結果 |
| --- | --- |
| `tests/test_h1_official_contract.py`（SQLite） | 143 passed / 13 skipped |
| 同（PostgreSQL 16 有効） | 152 passed / 4 skipped |
| フルスイート（SQLite） | 3905 passed / 466 skipped / 20 subtests |

PostgreSQL は既存の使い捨てコンテナ `jltsql-sk-pg16-8215`
（`127.0.0.1:32904`）のみを再利用し、新規コンテナは作成していない。テストは
一時 schema を作成して終了時に `DROP SCHEMA ... CASCADE` する。

### mutation probe（各ガードが効いていることの実測）

`/tmp/h1_mutation_probe.py`（対象は H1 契約テストのみ）

| 取り除いたガード | 結果 |
| --- | --- |
| baseline | 139 passed |
| parser の公式値域検証 | 23 failed |
| 各経路の `validate_h1_record` | 0 failed（下記の残余リスク参照） |
| 各経路の `verify_h1_storage_schema` | 47 failed |
| 標準名の置換キー probe | 6 failed |
| 人気順列を数値型へ戻す | 5 failed |
| 空白人気順の保持 | 2 failed |
| 消去表を別名へ戻す | 1 failed |

## 独立レビューと修正（同一イテレーション内）

1. 人気順の取消マーカーが緩かった。`set(text) in ({"-"}, {"*"})` は `-` や `---`
   も通していた。公式表記は 2 文字固定（`'--'` 発売前取消 / `'**'` 発売後取消、
   `/tmp/jvdata4901.txt` の各賭式「スペース:登録なし '--':発売前取消
   '**':発売後取消」）なので `{"--", "**"}` へ厳格化した。
2. `_H1_KEY_COLUMNS` が未使用の死んだ定数だった（UM イテレーションと同じ指摘）。
   削除し、公式キーは `_STANDARD_VOTE_RACE_KEY_COLUMNS` /
   `_STANDARD_VOTE_CONFIG["H1"]["children"]` の単一の出所から取る。
3. 既存 DB への追加 migration preflight（`_preflight_existing_strict_storage`）が
   native 2 table だけを見ていた。標準名 owner `HYOSU`（子 table を含む）を
   `STRICT_H1_STORAGE_TABLES` に加え、
   `test_h1_migration_preflight_covers_the_standard_family` で pin した。
   他レコードの `STRICT_*` は native のみだが、H1 の物理レコードは owner/子に
   跨るため、drift した標準名 table を放置すると消去と置換が壊れる。

## 追加レビュー（CodeRabbit）への対応

| 指摘 | 判定 | 対応 |
| --- | --- | --- |
| PostgreSQL の置換キー判定が式 index / 部分 index を公式キーと誤認 | 有効 | `indexprs` / `indpred` / `indisvalid` / `indisready` を確認して fail closed。赤先行 2 件 FAILED → 修正後 pass |
| SQLite の `PRAGMA index_list.partial` 未検査 | 有効 | 部分 index を拒否。`test_h1_rejects_a_partial_official_key_index` で pin |
| 取消マーカーが `-` / `---` を通す | 有効 | `{"--", "**"}` の完全一致へ |
| 空白の許容が空白文字列も通す | 有効 | parse 後の正規形 `""` のみ許可。`test_h1_accepts_only_the_canonical_blank` で pin |
| 人気順列の列挙漏れ（`HYOSU_TANPUKU`, `HYOSU_UMARENWIDE`） | 有効 | docs / CHANGELOG / RELEASE_NOTES に追記（型変更はなく、以前から文字列列） |
| `docs/data_support.md` の `#h11` が壊れている | 反証 | 生成 HTML に `id="h11"` が存在し、`mkdocs build --strict` は 0 warning。見出し id は mkdocs の slugify に委ねる既存方針 |
| `PostgreSQLDatabase._reconnect()` が `search_path` を復元しない | 範囲外 | H1 で導入した挙動ではなく、`SET search_path` を使う contract test は 14 モジュール以上に既存。H1 fixture の cleanup は `DROP SCHEMA <name> CASCADE` を明示名で実行するため search_path に依存しない。共有 handler の変更は別イテレーションで扱う |

## 残余リスク

- 各 importer 経路の `validate_h1_record(record, table_name)` を外しても
  契約テストは赤にならない。`validate_import_record_header()` が同じ検証を
  先に実行しているためで、per-path hook は他 13 レコードと同じ多層防御として
  残している（record type と保存先 table の結合は
  `test_h1_validation_binds_the_record_type_to_h1_storage` で直接 pin 済み）。
- `HYOSU` 系標準名 table には宣言上の PRIMARY KEY が無く、一意性は import 時に
  作られる公式キー UNIQUE index に依存する。今回はその index 以外の UNIQUE を
  拒否する契約までを固定し、PRIMARY KEY の宣言追加は H6 と共通の変更になるため
  行っていない。
- 速報 `RT_H1` は `RealtimeUpdater.RECORD_TYPE_TABLE` の既存ルーティングを
  維持した（`0B20` 速報票数は公式に提供される）。速報固有のデータ区分差分は
  公式資料に明記が無いため追加していない。
- H6（票数６・３連単）は同じ標準名 owner/子構造を持つが、本イテレーションでは
  値域検証を H1 に限定している。H6 は次イテレーションで同じ型を適用する。

## 停止条件

- H6 は本 PR が CI green・未解決レビュースレッド 0 で merge されるまで着手しない。
