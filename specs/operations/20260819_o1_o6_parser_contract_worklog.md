# O1-O6（オッズ1〜6）公式 真偽・parser 契約 worklog（2026-08-19）

## 対象

- repository: `miyamamoto/jrvltsql`
- worktree: `/home/keiba/scratch/20260819_jrvltsql_o1o6_official`
- branch: `agent/o1-o6-official-contract-20260819`
- base: `77bb919d7f756a57bc3af12faae23908e1d7e3c7`（H6 公式契約 PR #225 の merge
  commit、短縮 `77bb919`）

直列順の位置づけ: HN → SK → UM → H1 → H6 → **O1-O6（真偽・parser）** → O1-O6
（無損失 storage）→ 2.0.0.dev0。H6 は merge 済み・CI green のため着手した。

この段の範囲は parser の真偽（公式レイアウトどおりの展開と公式ドメイン検証）と、
その結果として storage から失われていた公式値の回復までである。native/標準名の
列型を無損失にする作業（オッズ・人気順の記号値保存）と、importer 経路への本文
検証接続・strict schema preflight・`DataKubun=0` の物理 exact erase は次段
「O1-O6（無損失 storage）」で扱う。

## 参照した公式資料

- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.pdf`
  （抽出テキスト `/tmp/jvdata4901.txt`）
  - 「フォーマット」７．オッズ1（単複枠）／８．オッズ2（馬連）／
    ９．オッズ3（ワイド）／１０．オッズ4（馬単）／１１．オッズ5（3連複）／
    １２．オッズ6（3連単）
  - 「データ提供内容」各オッズ: 発売のないレースについてはレコードを提供しない
    （提供開始は O1 1993年6月、O3 1999年10月、O4/O5 2002年6月、
    O6 2004年8月14日以降）
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4802.pdf`
  （抽出テキスト `/tmp/jvdata4802.txt`）: オッズ部の説明・最高値変更時期の追記履歴
- `tests/fixtures/official_layout/jvdata_status_domain.json`
  （出典 `JV-Data4901.xlsx`）: `O1`〜`O6` の DataKubun =
  `0`/`1`/`2`/`3`/`4`/`5`/`9`

公式レイアウトの実測値（位置は 1-based）:

| record | レコード長 | 発売フラグ | オッズ部 | 1件の内訳 | 票数合計 |
| --- | --- | --- | --- | --- | --- |
| O1 | 962 | 40/41/42（単勝・複勝・枠連）＋43 複勝着払キー | 単勝 44 から 8×28、複勝 268 から 12×28、枠連 604 から 9×36 | 単勝: 馬番2＋オッズ4＋人気順2 / 複勝: 馬番2＋最低4＋最高4＋人気順2 / 枠連: 組番2＋オッズ5＋人気順2 | 928・939・950（各11） |
| O2 | 2042 | 40 | 41 から 13×153 | 組番4＋オッズ6＋人気順3 | 2030（11） |
| O3 | 2654 | 40 | 41 から 17×153 | 組番4＋最低5＋最高5＋人気順3 | 2642（11） |
| O4 | 4031 | 40 | 41 から 13×306 | 組番4＋オッズ6＋人気順3 | 4019（11） |
| O5 | 12293 | 40 | 41 から 15×816 | 組番6＋オッズ6＋人気順3 | 12281（11） |
| O6 | 83285 | 40 | 41 から 17×4,896 | 組番6＋オッズ7＋人気順4 | 83273（11） |

公式の非数値表記（桁数は項目ごとに異なる）:

- オッズ: 「"000000":無投票 "------":発売前取消 "******":発売後取消
  "&nbsp;":登録なし(sp)」（O1 単勝/複勝は 4 桁、O1 枠連は 5 桁、O3 は 5 桁、
  O6 は 7 桁）
- 人気順: 「スペース:登録なし '--':発売前取消 '**':発売後取消」（O1 は 2 桁、
  O2〜O5 は 3 桁、O6 は 4 桁）
- 発売フラグ: 「0:発売なし 1:発売前取消 3:発売後取消 7:発売あり」
- 複勝着払キー（O1 のみ）: 「0:複勝発売なし 2:2着まで払い 3:3着まで払い」
- 項番10 は「発表月日時分」（月日時分各2桁、中間オッズのみ設定）であり、発走
  時刻ではない。

## 着手前に実測した欠陥

1. parser が公式の提供値を捨てていた。`if not kumi.strip("0 ") or not
   odds.strip("0 "): continue` により、組番を持つのに**オッズが無投票
   （`000000` などの `0` の並び）である組合せが 1 件も保存されない**。O1 では
   枠連の無投票が同様に捨てられていた。
2. 公式ドメイン検証が皆無だった。非公式な `DataKubun`、実在しない日付、発売
   フラグ以外の値、桁落ちした組番・オッズ・人気順、11 桁でない票数合計が
   すべて通っていた。
3. 組合せを 1 件も持たない snapshot（レース中止・削除など）は header だけの
   1 行になり、native の置換キー（…＋`Kumi`）を満たせず取り込みに失敗して
   公式の票数合計ごと失われていた（既存テスト
   `test_sqlite_importer_skips_empty_expanded_o2_header_row` が
   `records_failed == 1` を期待していた）。
4. 時系列オッズ table のメタデータが `HassoTime` を「発走時刻」（例 `1540`）と
   記述していた。公式は「発表月日時分」の 8 桁（`MMDDhhmm`）である。

参考（この段では直さない、次段の対象）: 公式の取消マーカーは native
`NL_O1`〜`NL_O6`（オッズ `REAL`・人気順 `INTEGER`）と標準名 `ODDS_*`
（`DECIMAL`・`SMALLINT`）に保存できず `NULL` へ落ちる。実測:

```text
convert_record_types({... "Odds": "------", "Ninki": "---"}, "NL_O2")
  -> {'Odds': None, 'Ninki': None}
SELECT Kumi, Odds, Ninki FROM NL_O2 -> [{'Kumi': '0102', 'Odds': None, 'Ninki': None}]
```

## 実施内容

1. 赤先行で `tests/test_o1_o6_official_contract.py` を追加（レコード長、
   オッズ部の幾何、公式 DataKubun、公式発売フラグ、無投票の保持、取消マーカーの
   保持、登録なしスロットの除外、合計行 sentinel、票数合計の保持、組番昇順、
   桁落ち・非公式値の拒否、O1 の単勝・複勝・枠連の展開と複勝着払キー）。
2. `src/parser/odds_domain.py` を追加し、O1-O6 が共有する公式ドメイン
   （DataKubun・発売フラグ・複勝着払キー・レースキー・実在日付・発表月日時分・
   桁数付きの記号値・11 桁票数合計・合計行 sentinel）を 1 箇所に定義した。
3. `src/parser/o1_parser.py`〜`o6_parser.py` に公式ドメイン定数と
   `validate_current_fields` / `validate_key_fields` を追加し、行を捨てる条件を
   「組番（O1 単複は馬番）が空白のスロットだけ除外」へ修正した。
4. 組合せを持たない snapshot では、H1/H6 と同じ合計行（`Kumi=TOTAL`）を 1 行
   返すようにした。O1 の合計行は枠連行と同じく `Umaban="0"` を置く。
5. `src/importer/importer.py` の標準名オッズ分割で、合計行に対応する子 table の
   行を作らないようにした（合計は header table の `TotalHyosu*` 列に入る）。
6. `src/database/schema_metadata.py` の時系列オッズ 6 table の `HassoTime` 記述を
   公式の「発表月日時分（MMDDhhmm）」へ修正した。
7. 独立レビューで確認した点として、`DataKubun=0` の物理 exact erase は
   `_OFFICIAL_ERASE_STORAGE_TABLES` に O1-O6 が登録済みで、合計行 sentinel が
   tombstone として残らないことを実測した（native・標準名 header/子 table の
   いずれも 0 行）。回帰しないようテストで固定した。
8. 既存テスト `test_sqlite_importer_skips_empty_expanded_o2_header_row` を公式
   契約どおりの
   `test_sqlite_importer_keeps_the_official_total_of_an_empty_o2_snapshot` へ
   置き換えた（合計行 1 件が保存されることを固定）。

## 証跡

赤先行（実装前の parser に対して新テストを実行）:

```text
105 failed, 91 passed
```

実装後:

```text
tests/test_o1_o6_official_contract.py: 261 passed, 12 skipped   （SQLite のみ）
tests/test_o1_o6_official_contract.py
  + tests/test_expanded_record_storage.py: 337 passed           （PostgreSQL 16 込み）
```

PostgreSQL 16 は既存の使い捨てコンテナ `jltsql-sk-pg16-8215`
（`127.0.0.1:32904`）のみを使用し、テストごとに一時 schema を作成・削除した。

フルスイート:

```text
4319 passed, 491 skipped, 20 subtests passed
```

必須ゲート:

```text
uv lock --check: pass
scripts/validate_test_gate.py: TEST GATE PASS
uvx flake8 --isolated --select=E9,F63,F7,F82 src tests scripts tools: pass
mkdocs build --strict: pass
git diff --check: pass
```

## 独立レビューで見つけた次段の欠陥（この段では直さない）

O1-O6 には H1/H6 のようなレース単位 snapshot 置換が無く、**組合せ数が減った
snapshot を取り込むと古い組合せの行が残る**。実測（native `NL_O2`、SQLite）:

```text
filled=3 を取込 -> COUNT(*) = 3
filled=2 を取込 -> [{'Kumi': '0102'}, {'Kumi': '0103'}, {'Kumi': '0104'}]
                   （0104 は最新 snapshot に無いのに残る）
```

速報経路（`RT_O2`）も同様で、組合せを持たない snapshot を受けると合計行 sentinel
が追加される一方、以前の組合せ行はそのまま残る。`DataKubun=0` の物理 exact erase
だけは公式どおり動く（実測で 0 行）。この置換契約は次段「O1-O6（無損失
storage）」で H1/H6 と同じ形に揃える。

## 実施していないこと

- provider / JV-Link への接続は禁止されているため、実データの O1-O6 取り込みは
  行っていない。検証はすべて公式仕様どおりに構成した合成レコードで行った。
- native/標準名のオッズ・人気順列を無損失（記号値保存）にする変更、importer
  経路への本文検証接続、strict schema preflight は次段「O1-O6（無損失
  storage）」で扱う（`DataKubun=0` の物理 exact erase は既存実装が公式どおりに
  動くことを実測し、この段でテストに固定した）。この worklog の時点では、
  公式の取消マーカーは保存時に `NULL` へ落ちる。
