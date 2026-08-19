# UM（競走馬マスタ）公式契約 worklog — 2026-08-19

## 位置づけ

公式直列順の 3 番目（HN #217 → SK #221 → **UM** → H1 → H6 → O1-O6 ×2 →
`2.0.0.dev0`）。JG/RC/WC の fail-open 修復 #222 が merge 済みであることを前提と
する。

- base SHA: `67df164c6bfdd979db6700c868faf5240537805e`（#222 merge）
- worktree: `/home/keiba/scratch/20260819_jrvltsql_um_official`
- branch: `agent/um-official-contract-20260819`
- 実施者: Devin（`claude code` への委任は利用者指示で中止。実装・検証・レビュー
  は Devin が直接実施）
- session: https://app.devin.ai/sessions/83dda3bd2bb44d7abe83462669c51210

## 一次資料

- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4901.pdf`
  （抽出テキスト `/tmp/jvdata4901.txt`）「フォーマット」１３．競走馬マスタ
- `/home/keiba/scratch/20260815_jvdata_official_materials/JV-Data4802.pdf`
  （抽出テキスト `/tmp/jvdata4802.txt`）変更履歴（2023-08-08 の桁数変更）
- 既存 fixture `tests/fixtures/official_layout/*_contract_4901.json`

確認した公式事実（要点）:

- レコード長 1609 バイト、末尾 1607-1608 が CR/LF。
- `DataKubun` は `0`（該当レコード削除）/`1`/`2`/`3`/`4`/`9`（抹消）。
- `KettoNum` 10 バイト、`MakeDate`/`RegDate`/`DelDate`/`BirthDate` は 8 バイト
  `YYYYMMDD`（初期値 0 埋め）。
- 競走馬抹消区分 1 バイト（`0`/`1`）、JRA 施設在きゅうフラグ 1 バイト
  （`0`/`1`、平成 18 年 6 月 6 日以降設定＝それより前は空白）。
- 馬記号 2、性別 1、品種 1、毛色 2、東西所属 1、調教師コード 5、生産者コード 8、
  馬主コード 6、累積賞金 6 項目×9、着回数 27 組×18、脚質傾向 12、登録レース数 3。
- 3 代血統は 14 組（繁殖登録番号 10 + 馬名 36）。

初期値欄の `Ｓ`／`sp` は公式ワークブックの記法どおり「空白」を意味するため、
リテラル文字ではなく空白として解釈した（HN/SK と同じ扱い）。

## RED（実装前の実測）

### 1. 事前 probe（`/home/ubuntu/probe_um.py`、未コミット）

```
=== provider order 1 -> 2 -> 0
NL_UM rows after 1 -> 2 -> 0: 1
surviving: {'DataKubun': '0', 'KettoNum': '2019900001', 'Bamei': 'テストウマアルファ'}
UMA  rows after 1 -> 2 -> 0: 1
surviving: {'DataKubun': '0', 'KettoNum': '2019900001', 'Bamei': 'テストウマアルファ'}
```

本文値域はすべて受理されていた（`DataImporter`/`OptimizedDataImporter` 両方）:

```
BirthDate='20190230' / '2019031' / RegDate='notadate' / SexCD='X' /
HinsyuCD='' / KeiroCD='1' / DelKubun='9' / ZaikyuFlag='Z' / Bamei=None /
Bamei='   ' / Ketto3InfoHansyokuNum1='12345' / TorokuRaceSu='abc' /
SogoChaku='12'  → いずれも ACCEPTED rows=1
```

`/home/ubuntu/probe_um2.py` では、公式に空欄となり得る項目が `NULL` として
読み戻ることを実測した:

```
NL_UM {'ZaikyuFlag': None, 'Reserved': None, ...}
UMA   {'ZaikyuFlag': None, 'Reserved': None, ...}
RT_UM present in importer source: False
RT_UM in SCHEMAS: False
```

原因（コード側）:

- `_OFFICIAL_ERASE_KEY_COLUMNS` と `_OFFICIAL_ERASE_STORAGE_TABLES` に `UM` が
  無く、status 0 が upsert として扱われていた。
- `validate_import_record_header` の UM 分岐は `KettoNum` 10 桁だけを検査。
- `verify_um_storage_schema` は置換キー検証のみで、型・容量・`NOT NULL`・追加列・
  generated 列・有害 `CHECK`/`FK` を見ていなかった（標準名 `UMA` は per-record
  検証の対象外だった）。

### 2. 契約テスト追加直後

`tests/test_um_official_contract.py` を追加して実行:

```
ImportError: cannot import name 'validate_um_record' from 'src.importer.importer'
```

`validate_um_record` を実装した時点で:

```
18 failed, 99 passed, 12 skipped
```

失敗の内訳は、native の物理 erase・provider 順・空欄保持（`Reserved_1608` の
`NOT NULL` を含む）と、標準名 `UMA` の nullable/型欠陥が検出されないこと。

schema manager 経路の RED（後から追加した 1 ケース）:

```
2 failed  test_um_schema_manager_refuses_to_migrate_an_unsafe_existing_table
          （create_table / create_all_tables が不安全な既存 NL_UM を通していた）
```

## 実装（最小差分）

- `src/parser/um_parser.py`: 公式 1609 バイト本文 domain（実在日付、抹消区分
  `0/1`、在きゅうフラグ `0/1`/空欄、桁数固定の各コード、9 桁×6 の累積賞金、
  18 桁×27 の着回数、12 桁の脚質傾向、3 桁の登録レース数、14 個の 10 桁繁殖
  登録番号、CP932 テキストの公式バイト幅）を検証する
  `validate_key_fields` / `validate_current_fields` を追加。`DataKubun=0` は
  ヘッダと `KettoNum` だけを検証し、本文は不透明のまま扱う。
- `src/importer/importer.py`:
  - `validate_um_record` を追加し、共通ヘッダ gate（従来の `KettoNum` 専用検査を
    置換）と全 importer 経路（batch・単発・optimized）から呼ぶ。
  - `UM` を `_OFFICIAL_ERASE_KEY_COLUMNS` / `_OFFICIAL_ERASE_STORAGE_TABLES` /
    provider 操作カウント集合へ追加（native と標準名の両方）。
  - `verify_um_storage_schema` を `NL_UM` と `UMA` 両方に拡張し、
    `_verify_strict_storage_column_contract`（型・容量・`NOT NULL`・追加列・
    generated/identity 列）と `_verify_um_no_unapproved_constraints`
    （`CHECK`/`FK`）を DML 前に実行。
  - 公式に空欄となり得る項目を空文字で保持。
- `src/database/schema.py` / `schema_jravan.py`: `NL_UM` 90 列と `UMA` 227 列を
  `NOT NULL` に、`NL_UM.ZaikyuFlag` を `INTEGER` → `TEXT`（公式の空欄・先頭ゼロを
  表現できないため）。`STRICT_UM_STORAGE_TABLES` を追加して
  `_preflight_existing_strict_storage` / `SchemaManager.create_table` /
  `create_all_tables` / モジュール関数 `create_all_tables` の 4 経路へ結線。
- `tests/test_um_parser_layout.py`: 既存 fixture の sentinel のうち公式 domain 外
  だった 2 件のみ修正（`DelKubun` `3`→`1`、`ZaikyuFlag` `4`→`0`。1 バイト span の
  値の一意性は維持）。旧 seed INSERT は全列を与える形に変更し、標準名 `UMA` が
  per-record 検証の対象になった事実を反映。

## GREEN

```
tests/test_um_official_contract.py                     119 passed, 12 skipped
tests/test_um_official_contract.py + layout（PG 有効）  309 passed
SQLite 全スイート                                      3755 passed, 453 skipped
PostgreSQL 16 有効の全スイート                          4175 passed, 33 skipped
```

使い捨て PostgreSQL は既存コンテナ `jltsql-sk-pg16-8215`（`127.0.0.1:32904`）
1 個のみを再利用。ディスク圧迫のため新規コンテナは起動していない。

ゲート:

```
uv lock --check                                        Resolved 50 packages
python scripts/validate_test_gate.py                   TEST GATE PASS
uvx flake8 --isolated --select=E9,F63,F7,F82 ...       exit 0
mkdocs build --strict                                  built
git diff --check                                       clean
```

## mutation probe（テストが実際に守っているかの実測）

`/home/ubuntu/um_mutations.sh` で各 guard を 1 つずつ削除して測定:

```
erase mappings removed            12 failed, 105 passed
caller body validation removed    22 failed,  95 passed
strict schema contract removed    48 failed,  69 passed
blank-span preservation removed   10 failed, 107 passed
unmutated                        117 passed
```

（`schema manager` 経路の 2 ケースを追加した後は 119 passed）

## 独立レビュー（1 バッチ、Devin 実施）

観点別の確認と処置:

1. 公式 parser/domain — コード表 2201-2204/2301 の値そのものは照合せず桁数のみを
   検査する方針を維持（コード値は将来追加され得るため。SK と同じ判断）。
   `RegDate`/`DelDate`/`BirthDate` は公式初期値 `00000000` を有効値として許可。
2. DB/schema/transaction — `Reserved_1608`（CR/LF span）は parser が空文字を返す
   ため、空欄保持対象へ加えないと `NOT NULL` で INSERT が落ちることを実測し、
   空欄保持と無損失幅 2 の対象に加えた。
3. release/test/docs — 累積賞金が native `REAL` / 標準名 `VARCHAR(9)` で読み戻り
   が異なる点はドキュメントに明記（SK の `ImportYear` と同じ扱い）。

## PR #223 のレビュー対応

外部レビュー（Copilot / CodeRabbit）で 5 件、うち実在の欠陥 4 件を赤先行で修正:

1. PostgreSQL の CHECK/FK probe が  placeholder を使っていた。 を driver
   別へ変換する契約なので pg8000 fallback で壊れる（。placeholder pin を
   追加し、 に戻すと RED になることを実測）。
2. 同 probe が SQLite/PostgreSQL 以外の db_type で無言 return し、検証を飛ばして
   いた（。SK の同型 probe は raise していた）。
3.  が importer/schema では公式 2 バイト span 扱いなのに
    に無く、caller 行では任意文字列が通っていた
   （）。
4. 未使用になった  と、 の
   「標準名 UMA は再検証しない」という古い docstring/コメント（）。
5.  の  fragment（markdownlint MD051）は
   反証。mkdocs strict build 後の HTML に  が存在し、当該 7 箇所は
   すべて解決する。MD051 は GitHub の slug 規則を仮定しており明示 anchor を見ない。

レビュー後の実測: 全スイート（PostgreSQL 16 有効）4182 passed / 33 skipped。

## 残余リスク

- 累積賞金 6 項目の native 型は `REAL` のままで、9 桁 zero fill の文字列表現は
  復元が必要（値としては 9 桁整数の範囲で正確）。native を `TEXT` へ変えるのは
  UM 単独ではなく無損失 storage の段でまとめて判断する。
- コード表の値域は桁数検査のみ。存在しないコード値（例 `SexCD='9'`）は通る。
- 既存 DB は自動移行されない。`NOT NULL` 化と `ZaikyuFlag` 型変更のため、
  backup → rebuild → `DIFN` 再取込が必要（ドキュメントに記載）。
- provider/JV-Link 実接続の検証はしていない（本 iteration の範囲外）。

## 停止条件

- CI green かつ未解決レビュースレッド 0 になるまで merge しない。
- H1 契約は UM が merge されるまで着手しない。
