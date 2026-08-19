# H6（票数６・3連単）公式契約 worklog（2026-08-19）

## 対象

- repository: `miyamamoto/jrvltsql`
- worktree: `/home/keiba/scratch/20260819_jrvltsql_h6_official`
- branch: `agent/h6-official-contract-20260819`
- base: `cddf51b`（H1 公式契約 PR #224 の merge commit）

直列順の位置づけ: HN → SK → UM → H1 → **H6** → O1-O6（真偽・parser）→ O1-O6
（無損失 storage）→ 2.0.0.dev0。H1 は merge 済み・CI green のため H6 に着手した。

## 参照した公式資料

- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.pdf`
  （抽出テキスト `/tmp/jvdata4901.txt`）
  - 「フォーマット」６．票数6（3連単）
  - 「データ提供内容」票数6（3連単）: 発売のないレースについてはレコードを
    提供しない／2004年8月14日以降提供
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4802.pdf`
  （抽出テキスト `/tmp/jvdata4802.txt`）: 3連単関連仕様の追加履歴
- `tests/fixtures/official_layout/jvdata_status_domain.json`
  （出典 `JV-Data4901.xlsx`）: `H6` の DataKubun = `0`/`2`/`4`/`5`/`9`

公式レイアウトの実測値:

| 項番 | 項目 | 位置(1-based) | バイト | 備考 |
| --- | --- | --- | --- | --- |
| 12 | 発売フラグ | 32 | 1 | `0`:発売なし `1`:発売前取消 `3`:発売後取消 `7`:発売あり |
| 13 | 返還馬番情報（馬番01～18） | 33 | 18 | 位置ごとに `0`:返還なし `1`:返還あり |
| 14 | <3連単票数> | 51 | 21 × 4,896 | 組番6＋票数11＋人気順4 |
| 15 | 3連単票数合計 | 102867 | 11 | 単位百円・返還分を含む |
| 16 | 3連単返還票数合計 | 102878 | 11 | 単位百円 |
| 17 | レコード区切 | 102889 | 2 | 合計 102,890 バイト |

人気順の公式表記は「スペース:登録なし '----':発売前取消 '****':発売後取消」で、
H1 の 2 文字表記（`--`/`**`）とは異なり **4 文字固定**である。

## 着手前に実測した欠陥

1. `NL_H6`/`RT_H6` の `SanrentanNinki` が `INTEGER`、標準名
   `HYOSU_SANRENTAN.Ninki` が `SMALLINT` で、公式の取消マーカーが `NULL` に
   落ちていた。
2. H6 の本文検証が存在しなかった（非公式 `DataKubun`、実在しない日付、発売
   フラグ以外の値、桁落ちした組番・票数・人気順がすべて通っていた）。
3. `_OFFICIAL_ERASE_STORAGE_TABLES["H6"]` が実在しない表名 `HYO_SANRENTAN` を
   指しており、標準名 `HYOSU2`/`HYOSU_SANRENTAN` が exact erase の対象から
   漏れていた。
4. native/標準名の key 列が nullable で、置換キーが 1 レース分の snapshot を
   一意に特定できない DB を受け付けていた。
5. 標準名の子 table では公式キー以外の `UNIQUE` index が検査されず、strict
   preflight にも H6 が含まれていなかった。

## 赤先行

`tests/test_h6_official_contract.py`（149 test）を実装前に追加した。実装前の実測:

```
ImportError: cannot import name 'validate_h6_record' from 'src.importer.importer'
1 error in 0.26s（collection error）
```

## 実装（最小差分）

- `src/parser/h6_parser.py`: 公式 domain（`DATA_KUBUN_VALUES`、
  `HATUBAI_FLAG_VALUES`、18 桁返還フラグ、6 桁組番、11 桁票数、4 桁人気順と
  4 文字取消マーカー、11 桁票数合計）と `validate_key_fields` /
  `validate_current_fields` を追加。`DataKubun=0` は key と header だけを検証。
- `src/importer/importer.py`: `_H6_*` storage identity、`validate_h6_record`、
  `verify_h6_storage_schema`、`_verify_h6_no_unapproved_constraints`、
  `_verify_h6_standard_replacement_key`、空白人気順の空文字保持、
  erase mapping の実表名化、共通 header 検証への接続。
- `src/importer/importer_optimized.py`: 同じ検証を optimized 経路へ接続。
- `src/database/schema.py`: `NL_H6`/`RT_H6` の key/本文 key 列を `NOT NULL`、
  `SanrentanNinki` を `TEXT` へ、`STRICT_H6_STORAGE_TABLES` と preflight/
  SchemaManager への接続。
- `src/database/schema_jravan.py`: `HYOSU2`/`HYOSU_SANRENTAN` の key 列を
  `NOT NULL`、`HYOSU_SANRENTAN.Ninki` を `VARCHAR(4)` へ。

## 既存テストの扱い

- `tests/test_expanded_record_storage.py` の
  `test_*_standard_h6_replaces_complete_snapshot`: `ninki` の期待値を数値 `8`
  から公式値 `"0008"` へ更新した（型変更に伴う無損失化の帰結）。
- 同ファイルの `test_*_standard_h6_migrates_existing_child_columns`:
  人気順列を失った drift 済み子 table への列自動追加を期待していた。H1 と同じ
  fail-closed 契約に合わせ、`test_*_standard_h6_rejects_a_drifted_child_table`
  として「DML 前に停止し、行を書かない」ことを検証する形へ書き換えた。挙動変更は
  CHANGELOG / RELEASE_NOTES / `docs/record_contracts.md` に移行手順として明記。

## 緑の証跡

```
H6 focused (SQLite):        149 passed, 13 skipped
H6 focused (PostgreSQL 16): 158 passed, 4 skipped
full suite:                 4054 passed, 479 skipped, 20 subtests passed
mkdocs build --strict:      0 warnings
```

PostgreSQL は既存の使い捨て container `jltsql-sk-pg16-8215`
（`127.0.0.1:32904`）のみを再利用し、test ごとに専用 schema を作成して
`DROP SCHEMA ... CASCADE` で削除している。新しい container は作成していない。

## mutation probe（各 guard が load-bearing であることの実測）

| probe | 内容 | 結果 |
| --- | --- | --- |
| baseline | 変更なし | 149 passed |
| 1 | `validate_h6_record` から本文検証を外す | 26 failed |
| 2 | 両 importer 経路から schema 検証を外す | 47 failed |
| 3 | erase mapping を `HYO_SANRENTAN` に戻す | 1 failed |
| 4 | 人気順列を数値型に戻す | 5 failed |
| 5 | 空白人気順の保持を外す | 2 failed |
| 6 | strict preflight から H6 を外す | 1 failed |

## 残余リスク

1. 共有 `PostgreSQLDatabase._reconnect()` は `search_path` を復元しない（H1 で
   記録した既存課題。H6 の範囲では test 側で schema を明示 drop している）。
2. 標準名 `HYOSU2`/`HYOSU_SANRENTAN` は宣言的 primary key を持たず、公式置換の
   一意性は importer が維持する UNIQUE index に依存する（H1 と同じ構造）。
3. 実 provider データでの H6 取込は本 iteration では実行していない（provider /
   JV-Link へのアクセスは保留指示のため）。合成 102,890 バイト record と実機 DB
   での検証にとどまる。

## 停止条件

O1-O6 は、H6 が test green・CI green・未解決 review thread 0・merge 済みに
なるまで着手しない。
