# O1-O6（オッズ1〜6）無損失 storage 契約 worklog（2026-08-19）

## 対象

- repository: `miyamamoto/jrvltsql`
- worktree: `/home/keiba/scratch/20260819_jrvltsql_o1o6_storage`
- branch: `agent/o1-o6-lossless-storage-20260819`
- base: `7bdaa06cd3cc49a9493f15eb1020fc28de704484`（O1-O6 真偽・parser 契約
  PR #226 の merge commit、短縮 `7bdaa06`）

直列順の位置づけ: HN → SK → UM → H1 → H6 → O1-O6（真偽・parser）→
**O1-O6（無損失 storage）** → 2.0.0.dev0。前段は merge 済み・CI green である。

この段の範囲は、parser が公式どおり復元した値を storage で 1 文字も失わない
ことと、1 物理レコード＝1 レース 1 時点の完全 snapshot という公式の意味を
storage 側で守ることである。

## STOP 条件

次のいずれかに当たったら、この段の作業を止めて報告する。

- 公式仕様書（JV-Data 4.8.0.2 / 4.9.0.1）で裏を取れない仕様判断が必要になったとき
- 既存テストの期待値を、公式仕様の裏付け無しに変更する必要が出たとき
- 実 provider（JV-Link）取得、本番 DB、frozen 研究 DB への書き込みが必要になったとき
- 1.x 既存 DB の移行が rebuild/reimport では救えないと判明したとき
- CI が green にならない状態が3回の修正で解消しないとき

次段（2.0.0.dev0）は、この段が merge され CI green になってから着手する。

## 参照した公式資料

- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.pdf`
  「フォーマット」７．オッズ1（単複枠）〜１２．オッズ6（3連複／3連単）
  - オッズの非数値表記: `000000`=無投票 / `------`=発売前取消 /
    `******`=発売後取消 / 空白=登録なし
  - 人気順の非数値表記: 空白=登録なし / `--`=発売前取消 / `**`=発売後取消
    （桁数は O1 2 桁、O2〜O5 3 桁、O6 4 桁）
  - 発売フラグ `0`/`1`/`3`/`7`、O1 複勝着払キー `0`/`2`/`3`
  - DataKubun `0`/`1`/`2`/`3`/`4`/`5`/`9`
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4802.pdf`
  オッズ部の説明と最高値変更の追記履歴

## 着手前に実測した欠陥（前段のレビュー中に記録したもの）

1. 記号値が保存できない列型
   - native `NL_O1`〜`NL_O6`・速報 `RT_O1`〜`RT_O6` のオッズ列は `REAL`、
     人気順列は `INTEGER`。標準名 `ODDS_*` 子 table は `DECIMAL` / `SMALLINT`。
   - 実測: `------` / `******` は `NULL` として保存され、公式の「登録なし」
     （空白）と区別できない。`000000`（無投票）は数値 `0` になる。
2. レース単位 snapshot 置換の不在
   - 実測: `filled=3` の snapshot（`0102`/`0103`/`0104`）を取り込んだあとに
     `filled=2` の snapshot（`0102`/`0103`）を取り込むと `0104` が残存する。
   - 合計のみ snapshot（発売なし・レース中止）でも、`Kumi="TOTAL"` の行が
     追加されるだけで前の組合せが残る。
3. 公式キーが nullable
   - `Year`/`MonthDay`/`JyoCD`/`Kaiji`/`Nichiji`/`RaceNum`/`Umaban`/`Kumi` が
     nullable のため、1 レースの置換が別レースへ当たり得る schema を許していた。
4. storage 経路に本文検証と strict schema preflight が接続されていない
   - parser 側の `validate_current_fields` は前段で実装済みだが、importer
     経路からは呼ばれていなかった。

## 実装（最小差分）

- `src/database/schema.py`, `src/database/schema_jravan.py`
  - オッズ列・人気順列を文字列（native `TEXT` / 標準名 `VARCHAR(n)`）へ変更。
    桁は公式どおり（例: O2 オッズ 6・人気順 3、O6 オッズ 7・人気順 4）。
  - レースキー・馬番・組番を `NOT NULL` に変更。
  - `STRICT_ODDS_STORAGE_TABLES` を追加し、既存表の migration 前 preflight と
    `SchemaManager.create_table` / `create_all_tables` から検査する。
- `src/parser/odds_domain.py`
  - `attach_snapshot_metadata` を追加し、展開した各行へ snapshot 全体
    （`_odds_snapshot_rows`）と位置（`_odds_snapshot_index`）を持たせる。
    DM/TM で確立済みの方式をそのまま使う。
- `src/parser/o1_parser.py`〜`o6_parser.py`
  - 展開結果（合計のみ行を含む）に snapshot metadata を付ける。
- `src/importer/importer.py`
  - `validate_odds_record`: 宛先 table と record type の整合を検査し、公式
    ドメイン検証を parser へ委譲する。
  - `verify_odds_storage_schema`: native / 標準名 owner・子 table の存在、列型・
    桁・NULL 可否、公式主キー以外の追加 `UNIQUE`（部分・式・exclusion 含む）、
    遅延主キー、未承認の `CHECK` / `FOREIGN KEY` を DML 前に拒否する。標準名の
    子 table は不足列を従来どおり追加移行で補うため、既存列のみ厳格に検査する。
  - `replace_odds_native_snapshot`: 1 レースの全行を検証したうえで削除→再投入。
    失敗時は rollback して `OddsSnapshotMutationError` を投げる。
- `src/importer/importer_optimized.py`: 最適化経路でも同じ置換・検証を通す。
- `src/realtime/updater.py`: 速報の単発・batch 経路で snapshot 置換を行い、
  追従行を二重に書かない。

## 証跡

- 焦点テスト（新規 `tests/test_o1_o6_storage_contract.py`、201 件）
  - 実装前は 24 failed（記号値の欠落・置換されない古い組合せ・nullable key の
    受理・危険 schema が DML へ到達）。
  - 実装後は SQLite 176 passed / PostgreSQL 16 実機込みで全件 passed。
- mutation probe: `attach_snapshot_metadata` を無効化すると 25 failed
  （通常・最適化・単発・速報の置換テストが赤）。
- フルスイート: SQLite 4500 passed / PostgreSQL 16 実機込み 4987 passed、
  503 → 41 skipped（PG 実機で skip が解消）。
- 既存 `tests/test_expanded_record_storage.py` の期待値は、公式提供値
  （文字列）と公式桁数（O6 オッズ 7 桁）へ合わせて修正した。数値へ丸める
  期待値は公式仕様に反するため維持しない。

## 独立レビューで見つけた欠陥（同一 PR 内で赤先行修正）

1. 公式の空白（登録なし）を空文字で保存する分岐が**定義だけで未接続**だった。
   `_ODDS_BLANK_TEXT_FIELDS` は宣言済みなのに `convert_record_types` から
   参照されておらず、空白は `NULL`（未提供）へ落ちていた。接続し、
   `test_blank_official_values_stay_blank_instead_of_null` で固定した。
   O1 は単勝・複勝・枠連の配列が独立なので、その行に存在しない項目は `NULL`
   （未提供）のままである。
2. 単発経路が snapshot の**追従行だけ**を渡されたとき、何も書かずに `True` を
   返していた（silent fail-open）。追従行も snapshot 全体を保持しているため、
   単独で渡されても完全な snapshot を適用し、件数は先頭行のみで数える形に修正した。
   `test_single_record_follower_row_alone_still_stores_the_whole_snapshot` で固定。
3. 速報経路（`RealtimeUpdater.process_parsed_record` / `process_parsed_records_batch`）
   が置換 DML の前に公式ドメイン検証（`validate_odds_record`）を通していなかった。
   caller 由来の dict が検証なしで削除＋再投入へ到達し得たため、importer と同じ検査を
   先に行う形へ修正し、`test_realtime_rejects_a_non_official_snapshot_before_mutation`
   で固定した（検証を外すと 5 件 RED）。
4. PostgreSQL のレース単位置換テストが無かったため追加した
   （`test_postgresql_snapshot_replacement_removes_withdrawn_combinations`）。
5. 合計のみ snapshot の sentinel 行（`Kumi=TOTAL`）は、parser が公式に組合せの
   無いことを空文字で表すため、無損失化後は `NULL` ではなく空文字で保存される。
   既存 `tests/test_expanded_record_storage.py` の期待値をこれに合わせた。

追加後の証跡: 焦点テスト SQLite 217 passed / PostgreSQL 16 実機込み 234 passed、
フルスイート PostgreSQL 16 実機込み **5008 passed**。

## この段で扱っていないこと

- 実 provider（JV-Link）からの取得は行っていない。検証は公式仕様書に基づく
  固定長 fixture と使い捨て PostgreSQL 16（`jltsql-sk-pg16-8215`）で行った。
- 1.x からの既存 DB は、オッズ列の型が変わるため rebuild/reimport が必要である
  （`docs/data_support.md` の移行手順に従う）。この worklog では移行実機検証を
  していない。
