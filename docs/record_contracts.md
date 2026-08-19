# レコード別の公式契約と移行手順

このページは [対応データ種別一覧](data_support.md) の詳細ページです。
jrvltsql が各レコード種別をどの公式レイアウトで受け付け、どのキーで
保存し、既存 DB をどう移行するかを、レコード種別ごとに同じ構成でまとめます。

## このページの読み方

- 「共通規則」には、複数のレコード種別に共通する検証・transaction・
  保存形式・移行手順を 1 回だけ書きます。
- 「レコード別の契約」は、レコード種別ごとに次の小見出しで揃えます。
    - 公式レイアウト
    - identity（主キー）
    - 保存先
    - DataKubun
    - 既存 DB からの移行手順
- レコード固有の項目がある場合は「値の扱い」「transaction」を追加します。
  記載事項のない小見出しは省略します。
- 移行手順の共通の流れは「既存 DB からの移行の共通手順」に書きます。各節には、
  そのレコードの停止条件、対象テーブル、再取込元（記載がある場合）、固有の
  注意を書きます。
- 用語: 本ページで「native」は `NL_*` / `RT_*` テーブル、「標準名」は
  JRA-VAN 標準名モードのテーブル（`HANSYOKU`, `HARAI` など。一部は
  project canonical 名。各節参照）を指します。

実装上の正本は以下です。

- `src/jvlink/constants.py`
- `src/parser/factory.py`
- `src/database/table_mappings.py`
- `src/database/schema.py`
- `src/cli/main.py`

## 共通規則

### 公式 DataKubun の検証

パーサー、通常インポート、1件インポート、速報保存は、レコード種別ごとの
公式 `DataKubun` を共通契約で検証します。次のいずれかに当たるレコードは、
そのレコードを使った table routing、cache 書き込み、DB 更新より前に
拒否します。

- 値が無い
- 空欄
- 1文字でない
- 別名の値が食い違う
- 下表に無い

未指定値を新規登録 `1` として補うことはありません。

下表は全38形式について、通常 import / parser で使う current base domain を
示します。provider がその形式を蓄積系・速報系のどちらで提供するかを表す
availability 表ではありません。速報では、この base domain から明示的な差分
（後述）を適用します。

| current base domain のレコード種別 | 現行の公式値 |
| --- | --- |
| `WH`, `WE`, `JC`, `TC`, `CC` | `1` |
| `AV` | `1`, `2` |
| `RC`, `HC`, `HS`, `HY`, `JG`, `WC` | `0`, `1` |
| `TK`, `KS`, `CH`, `BR`, `BN`, `HN`, `SK`, `CK`, `BT`, `CS` | `0`, `1`, `2` |
| `HR` | `0`, `1`, `2`, `9` |
| `DM`, `TM` | `0`, `1`, `2`, `3`, `7` |
| `YS` | `0`, `1`, `2`, `3`, `9` |
| `H1`, `H6` | `0`, `2`, `4`, `5`, `9` |
| `UM` | `0`, `1`, `2`, `3`, `4`, `9` |
| `WF` | `0`, `1`, `2`, `3`, `7`, `9` |
| `O1`〜`O6` | `0`, `1`, `2`, `3`, `4`, `5`, `9` |
| `RA`, `SE` | `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `9`, `A`, `B` |

**速報での差分:**

- 速報では、公式に蓄積系限定とされる `7` を `DM`, `TM`, `WF` で
  受け付けません。したがって速報の `DM`/`TM` は `0`, `1`, `2`, `3`、
  `WF` は `0`, `1`, `2`, `3`, `9` です。
- それ以外の形式では、公式資料に明記されない速報独自の制限を推測で
  追加していません。

**旧データ（`MakeDate` 境界）:**

- 同じ物理長の旧データも、公式変更日の前であることを `MakeDate` から
  確認できる場合に限り扱います。
- 日付が無い、読めない、または境界日以後なら現行仕様として検証します。

| レコード / 区分 | `MakeDate` 境界 | 扱い |
| --- | --- | --- |
| `RC=2` | 2005-09-29 | より前だけ扱います |
| `WH`/`WE`/`AV`/`JC=0` | 2003-07-11 | より前だけ扱います |
| `UM=9` | 2003-04-22 | より前のデータでは拒否します |

### 通常インポートの transaction / rollback 規約

- 通常インポートは streaming 処理です。
- `auto_commit=True` では完了した batch を順次 commit するため、後続
  レコードの検証失敗より前に確定済みの正常 batch と、開始時の standard
  schema preflight による変更は保持されます。
- 呼び出し全体を all-or-nothing にする場合は `auto_commit=False` を
  使います。この場合、後続検証失敗は同じ呼び出しまたは同じ caller-owned
  transaction で先に書いた行と統計を rollback します。
- この rollback 要否を判定する transaction 状態を取得できない場合は、
  未確定行を commit 可能な接続として残さず接続を無効化し、
  `TransactionRecoveryError` で停止します。
- 統計の rollback は同じ transaction generation に属する未確定分だけに
  限定します。caller が前の transaction を commit 済みの場合、その確定行と
  累積統計を後続 transaction の状態判定失敗で巻き戻しません。
- 状態判定と接続無効化の両方が失敗した場合は、接続上の未確定分を安全に
  分類できないため `TransactionRecoveryError` を送出し、既存の統計も
  成功・失敗のどちらへも推測更新しません。

レコード別の補足は各節に書きます（[HS](#hs) の `auto_commit` 別の
扱い、[WF](#wf-win5) の batch 全体 rollback、[DM / TM](#dm-tm-snapshot-transaction) の
速報 snapshot 置換と `TransactionRecoveryError`）。

### 速報 grouped batch と時系列 CLI の transaction 境界

- 速報の通常 grouped batch は、SQLite / psycopg が暗黙に開始した caller 側
  transaction を所有済みとして扱い、成功時に勝手に commit しません。
- DB 書込が 1 件でも失敗した場合は同じ call の grouped mutation を全て
  rollback して `inserted=0` と `transaction_rolled_back=true` を返し、
  後続 rollback で消える行を部分成功として数えません。削除を含む提供順
  処理も同じ atomic 境界を使います。
- false 結果を受け取った caller は、validation-only 拒否か DB rollback 済み
  かにかかわらず、その取込単位を必ず中断してください。
- psycopg では SELECT だけでも transaction が開始されるため、独立した
  取込単位へ移る caller は明示的に commit または rollback して境界を
  閉じてください。transaction 状態を判定できない場合は書込前に失敗します。
- batch 開始時に caller 側 transaction が無かった場合、schema / catalog
  検証の SELECT が暗黙に開始した transaction は validation-only 拒否時にも
  rollback して閉じます。開始時から caller 側 transaction が存在した場合は、
  validation-only 拒否だけではその transaction を commit / rollback しません。
- 時系列取得 CLI は保存先 table 作成を先に commit して batch ごとの境界を
  分離し、1 batch でも拒否された場合は `[OK]` を出さず非 0 終了します。

### HappyoTime（MMDDhhmm）の保存形式と旧標準名テーブル

- `WH`, `WE`, `AV`, `JC`, `TC`, `CC` と `O1`〜`O6` の公式 `HappyoTime` は、
  年を含まない 8 バイトの `MMDDhhmm` です。SQL の `TIME` や `TIMESTAMP` には
  変換せず、先頭ゼロを含む文字列として保存します。
- 速報開催情報の JRA-VAN 標準名は `TENKO_BABA`, `TORIKESI_JYOGAI`,
  `KISYU_CHANGE`, `HASSOU_JIKOKU_CHANGE`, `COURSE_CHANGE` です。旧来の英語
  別名は読み取り側の互換性のため残しますが、新しい標準名インポート先には
  使いません。
- 旧版が作成したこれらの標準名テーブル、および `ODDS_*_HEAD` テーブルで
  `HappyoTime` が `TIMESTAMP` の場合、起動時検証は型不一致として停止します。
  月日を欠いた旧値から公式 8 桁値を復元できないため、自動 `ALTER` や暗黙
  変換は行いません。
- 移行手順: DB をバックアップし、対象テーブルだけを退避または削除して
  現行の標準名スキーマ（`VARCHAR(8)`）で再作成した後、JRA-VAN の保持期間内の
  データを再取得してください。既存値を時刻部分だけで移植しないでください。
  （流れは [既存 DB からの移行の共通手順](#db) と同じです。）

### 0B14 の日単位 snapshot 置換と 0B16

- `0B14` は指定日の完全な開催変更 snapshot なので、正常終了を確認した
  同一 transaction 内で当該日の `RT_WE` / `RT_AV` / `RT_JC` / `RT_TC` /
  `RT_CC` を置換し、後続 snapshot から消えた変更を除去します。
- `0B16` は指定イベントの更新であり、この日単位置換とは別です。
- レコード別の補足は [WE](#we)、[AV](#av)、[JC](#jc)、[CC](#cc) の
  各節に書きます。

### 既存 DB からの移行の共通手順

各レコードの節に挙げた停止条件に当たる既存テーブルは、自動修復せず停止（拒否）
します（各節の記載を参照）。停止のタイミング（mutation 前 / 取込前 / 起動時 /
他表の additive migration 前など）と停止条件はレコードごとに異なるため、各節に
書きます。

移行の共通の流れは次のとおりです。

1. DB をバックアップします。
2. 対象テーブルを現行 schema（DDL）で再作成します。
3. 各節に書かれた source と範囲で、データを再取込 / 再取得します。

各節には、対象テーブル、再取込元（記載がある場合）、そのレコード固有の注意
（旧行を移植しない、親を先に作成する、など）を書きます。

### 旧仕様 dataspec 名（DIFF / BLOD / SNAP / HOSE / TCOV / RCOV）

`DIFF` / `BLOD` / `SNAP` / `HOSE` / `TCOV` / `RCOV` は jrvltsql では
受け付けません。`fetch` / `cache build` / `cache rebuild` は取り込みや既存
cache の変更に入る前に、対応する現行種別名を示して停止します。JRA-VAN の
仕様表には旧名も掲載されており、公式API全体で廃止されたという意味ではありません。

**旧名は新名の別名ではありません。** 2023-08 の JV-Data 仕様変更で桁数が変わって
おり（繁殖登録番号 8→10 / 生産者コード 6→8 / 生産者名 70→72）、旧名を要求すると
現行のパーサが解釈できない旧仕様のバイト列が返ります。桁がずれたまま取り込むと、
レコードの途中から後ろが全て壊れます。

`RACE` はこの仕様変更の対象外なので、これまでどおり使えます。

| 旧名 | 現行名 |
| --- | --- |
| `DIFF` | `DIFN` |
| `BLOD` | `BLDN` |
| `SNAP` | `SNPN` |
| `HOSE` | `HOSN` |
| `TCOV` | `TCVN` |
| `RCOV` | `RCVN` |

## レコード別の契約

### 速報馬体重・開催情報系（WH / WE / AV / JC / TC / CC）

#### WH（速報馬体重）

**公式レイアウト:**

- 公式 format 101 の 847 バイト馬体重レコードです。1 レコード内に 18 頭の
  配列を持ちます。

**identity（主キー）:**

- native `NL_WH` / `RT_WH` は 18 頭配列を馬ごとの行へ展開し、レース識別子と
  馬番を主キーにします。
- `HappyoTime` は訂正発表の時刻として保存しますが、同一レース・同一馬の
  新しい発表は最新値として置き換わります。

**保存先:**

- native `NL_WH` / 速報 `RT_WH`（馬ごとの行）。
- JRA-VAN 標準名モードの `BATAIJYU` は展開せず、18 頭分を 1 行に保持する
  公式の横持ち表現です。1 つの公式 WH レコードにつき、レース主キーの 1 行を
  保存します。

**DataKubun:**

- 現行 `1`（[公式 DataKubun の検証](#datakubun) の表を参照）。旧区分 `0` の
  `MakeDate` 境界も同節を参照してください。

**既存 DB からの移行手順:**

- 旧 jrvltsql が作成した `NL_WH` / `RT_WH` は、誤って天候変更の 40 バイト
  相当の列と主キーを持っていました。この物理テーブルが存在する環境では、
  起動時の schema migration は主キー不一致を検出して停止します。
- JRA-VAN 標準名モードの旧 `BATAIJYU` も主キーが無いため、同様に
  オペレーター移行が必要です。自動 drop や暗黙変換は行いません。
- DB をバックアップしたうえで、オペレーターが対象を `NL_WH` / `RT_WH` /
  `BATAIJYU` のうち実在する旧テーブルだけに限定して削除し、
  `jltsql create-tables --db <sqlite|postgresql>` または標準名テーブルの
  初期化手順で再作成してください。
- `RT_WH` はその後 `jltsql realtime start --specs 0B11` で、JRA-VAN の
  保持期間内に再取得します。
- 旧 `NL_WH` / `RT_WH` の行は公式 WH ではないため、馬体重履歴として
  移植しないでください。

#### WE（天候・馬場状態変更）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 で同一の 42 バイト配置です。

**identity（主キー）:**

- 公式キーは `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `HappyoTime`,
  `HenkoID` の 7 項目です。
- `HappyoTime=00000000` の初期発表と、その後の複数発表時刻を別行として
  保持します。最新状態を読む場合は `HenkoID` の大小ではなく最新の
  `HappyoTime` を選びます。この運用は公式スタッフの
  [説明](https://developer.jra-van.jp/t/topic/331)および複数時刻が共存する
  [事例](https://developer.jra-van.jp/t/topic/164)・
  [事例](https://developer.jra-van.jp/t/topic/141)とも一致します。

**保存先:**

- native `NL_WE` / `RT_WE` と標準名モードの `TENKO_BABA` は同じ順序の
  `NOT NULL` 主キーを使います。
- 公式幅を保てる非 padding の文字列型と、公式幅ちょうどの `CHAR` は
  lossless storage として許容します。通常行で必須の 6 つの本文コードは、
  既存表側の `NOT NULL` も安全です。

**DataKubun:**

- 現行のデータ区分は `1` です。
- 2003-07-11 より前の `MakeDate` でだけ旧区分 `0` を受け付け、7 項目が完全
  一致する 1 発表を物理削除します。削除レコードの 6 つの天候・芝・ダート
  本文値は解釈しませんが、キーに含まれる `HenkoID` は必須です。

**値の扱い:**

- 通常行は変更識別 `1`〜`3`、天候 `0`〜`6`、芝・ダート `0`〜`4` を検証し、
  変更識別 `2` では馬場 4 項目、`3` では天候 2 項目が公式初期値 `0` である
  ことを確認します。これを超える状態間の推測規則は適用しません。
- `0B14` の新しい応答が前回の日付 snapshot を置換する既存の一括更新契約は
  維持し、1 応答内では上記 7 項目キーで各発表を保持します。

**既存 DB からの移行手順:**

- 旧 6 項目キー、主キーなし、容量不足・数値化など lossless でないキー型、
  キーの NULL 許容、追加の `UNIQUE`/exclusion、PostgreSQL の遅延主キーがある
  既存表は、取込や他表の additive migration より前に停止します。
- 時刻別履歴や重複行から正しいキーを自動復元できないため、自動 ALTER は
  行いません。
- DB をバックアップし、対象表を現行 DDL で再作成して、保持範囲に合う公式
  42 バイト WE source を再取込してください。

#### AV（出走取消・競走除外）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 で同一の 78 バイト配置です。

**identity（主キー）:**

- 公式キーは `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum`,
  `Umaban` の 7 項目です。`HappyoTime` は発表情報として保存しますがキーでは
  ありません。同一馬の後続発表は同じ行を更新します。

**保存先:**

- native `NL_AV` / `RT_AV` と標準名モードの `TORIKESI_JYOGAI` は同じ順序の
  `NOT NULL` 主キーを使います。

**DataKubun:**

- 現行のデータ区分は `1=出走取消` と `2=競走除外` です。
- 2003-07-11 より前の `MakeDate` でだけ旧区分 `0` を受け付け、7 項目が完全に
  一致する行を物理削除します。旧削除レコードでは発表時刻・馬名・事由の
  本文を解釈しません。

**値の扱い:**

- 事由区分は blank と `000`〜`003` を受け付けます。2021-01-25 の仕様変更は
  初期値表記を `000` から space へ変えた同長変更であり、履歴データの
  provenance が不明な場合にどちらかを過剰拒否しません。
- `0B14` は開催日単位の完全な現行 snapshot です。現行の取消が撤回された
  場合は status `0` が届くのではなく、次の snapshot から AV 行が消えるため、
  同一 transaction でその日の `RT_AV` を置換します。個別イベントは
  `0B16`/`JVWatchEvent` で受けられるという公式サポートの
  [説明](https://developer.jra-van.jp/t/topic/195)があります。

**既存 DB からの移行手順:**

- 旧 nullable key、主キーなし・誤順序、lossless でない型や容量、追加の
  `UNIQUE`/exclusion、PostgreSQL の遅延主キーを持つ既存表は mutation 前に
  停止します。
- 自動的な PK 変更は行わないため、DB をバックアップし、対象表だけを現行 DDL で
  再作成して保持範囲内を再取込してください。
- NULL または不完全な identity を持つ旧行は正しい 7 項目キーへ安全に
  backfill できないため、バックアップには残しても現行表へ再利用せず、
  公式 provider から再取得してください。
- 旧標準名 `AVOIDENCE` だけが存在する構成も、自動移行や別表への誤保存を
  行わず、すべての DB target を変更前に停止します。標準名は
  `TORIKESI_JYOGAI` へ再作成してください。

#### JC（騎手変更）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 で同一の 161 バイト配置です。

**identity（主キー）:**

- 公式キーは `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum`,
  `HappyoTime`, `Umaban` の 8 項目です。
- 同一馬について「未定」の発表と確定後の発表など複数時刻が存在し得るため、
  発表月日時分を省いた最新 1 行への上書きは行いません。

**保存先:**

- native `NL_JC` / `RT_JC` と標準名モードの `KISYU_CHANGE` は、同じ順序の
  `NOT NULL` 主キーで再取込を冪等にします。

**DataKubun:**

- 現行のデータ区分は `1` です。
- 2003-07-11 より前の `MakeDate` に限って旧区分 `0` を受け付け、8 項目が
  完全一致する 1 発表だけを物理削除します。削除本文は解釈しません。
- 現在の取消・訂正を旧区分 `0` で合成せず、`0B14` の日付単位完全 snapshot が
  前回応答を置換する既存契約を使用します。速報更新は
  [公式スタッフの説明](https://developer.jra-van.jp/t/topic/331)で確認でき、
  複数発表時刻は
  [コミュニティで報告された実例](https://developer.jra-van.jp/t/topic/164)でも
  確認できます。

**値の扱い:**

- 負担重量は提供値が 0.1kg 単位なので、native / 速報の `REAL` 列では `550` を
  `55.0`kg へ正規化します。標準名モードの `VARCHAR(3)` は公式 3 バイト表現
  `550` をそのまま保持します。

**既存 DB からの移行手順:**

- 旧 7 項目キー、主キーなし、キーの NULL 許容、容量不足や誤型、追加の
  `UNIQUE`/exclusion、PostgreSQL の遅延主キーを持つ既存表は、取込または
  他表の schema 変更より前に拒否します。
- 発表履歴や重複行から正しい 8 項目 identity を自動復元できないため、DB を
  バックアップし、該当する `NL_JC` / `RT_JC` / `KISYU_CHANGE` だけを現行 DDL で
  再作成して保持期間内の `0B14`/`0B16` または対応する蓄積データから
  再取込してください。

#### TC（発走時刻変更）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 45 バイト配置だけを受け付けます。

**identity（主キー）:**

- `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum` の 6 項目です。

**保存先:**

- native `NL_TC`、速報 `RT_TC`、JRA-VAN 標準名 `HASSOU_JIKOKU_CHANGE` は同じ
  ordered primary key、必須 header/key/body、公式 field capacity を使います。

**DataKubun:**

- 現行の公式 `DataKubun` は `1` だけです。`0` を TC 単体の削除指示として
  扱いません。
- `0B14` / `0B16` の扱いは [0B14 の日単位 snapshot 置換と 0B16](#0b14-snapshot-0b16)
  を参照してください。

**値の扱い:**

- `HappyoTime` は `MMDDhhmm`、変更後・変更前の時刻は各 `HHmm` として先頭ゼロを
  保ったまま保存します。公式の初期値 `00000000` / `0000` も欠損へ変換しません。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、容量不足、generated /
  identity 列、追加列または追加 UNIQUE/FK/CHECK を持つ TC table は自動修復
  せず、mutation 前に停止します。
- DB をバックアップして該当 TC table を現行 schema で再作成し、保持期間内の
  `0B14`/`0B16` または対応する蓄積 source から再取込してください。
- 旧標準名 `COMMENT` しかない構成を `HASSOU_JIKOKU_CHANGE` へ自動転用しません。

#### CC（コース変更）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 50 バイト配置だけを受け付けます。

**identity（主キー）:**

- `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum` の 6 項目です。

**保存先:**

- native `NL_CC`、速報 `RT_CC`、JRA-VAN 標準名 `COURSE_CHANGE` は同じ ordered
  primary key と必須 15 列を使います。

**DataKubun:**

- 現行の公式 `DataKubun` は `1` だけで、CC 単体の status 0 delete はありません。
- `0B14` の正常完了後だけ[日単位 snapshot 置換](#0b14-snapshot-0b16)を行い、
  後続 snapshot から消えた CC を削除します。`0B16` はイベント指定更新なので
  日単位置換を行いません。
- 開催中止決定前に発表済みの CC は、公式仕様どおり中止後も提供対象です。

**値の扱い:**

- `HappyoTime` は `MMDDhhmm`、変更前後の距離は 4 桁、track code は公式コード表
  2009 の `00`, `10`〜`29`, `51`〜`59`、事由区分は初期値 `0` または `1`〜`4`
  です。
- `00000000`、距離 `0000`、track `00`、事由 `0` は欠損へ変換しません。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、容量不足、generated /
  identity 列、追加列または追加 UNIQUE/FK/CHECK を持つ CC table は、失われた
  identity や値を安全に復元できないため自動修復しません。
- DB をバックアップし、該当 3 表を現行 schema で再作成して、保持期間内の
  `0B14`/`0B16` または対応する蓄積 source から再取込してください。

### レース系（HR / SE / JG / WF）

#### HR（払戻）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 の 719 バイト配置へ結び付けています。
- 単勝 3、複勝 5、枠連 3、馬連 3、ワイド 7、予備 3、馬単 6、三連複 3、
  三連単 6 の全 repeat を保存します。

**identity（主キー）:**

- 公式キーは `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum` の
  6 項目です。

**保存先:**

- native 名は `NL_HR` / `RT_HR`、標準名モードは `HARAI` で、いずれも同じ順序の
  `NOT NULL` 主キーを使います。標準名モードでも払戻・人気・予備を NULL へ
  落としません。

**DataKubun:**

- 現行データ区分は `0`, `1`, `2`, `9` です。
- `9` は中止状態として保持し、削除には使いません。公式仕様は `9` の本文値を
  確定していないため、raw 由来の位置 28〜717 は `OpaqueStatus9Body28_717Hex`
  へ hex で保持し、通常の払戻列へは意味変換しません。caller-built の `9` は
  キーと状態だけを保存します。
- `0` だけが 6 項目の完全一致による物理削除で、本文は解釈しません。
- lossless 保持という project policy に従い、raw の `0`/`9` は位置 28〜717 を
  text decode せず、2004-08-14 より前の通常 record は位置 604〜717 を decode
  せずに扱います。header、6 項目キー、およびそれ以外の解釈対象範囲は
  引き続き strict CP932 検査を通します。

**値の扱い:**

- 予備 3 件は数値として意味付けせず、4/9/3 バイトの各区画を文字列で保持します。
- 不成立・特払・返還の 3 つの券種 flag 配列は、6 件目が公式予備のため `0`
  だけを受け付けます。返還馬番 28 件、返還枠番 8 件、返還同枠 8 件は全要素が
  通常の返還対象 flag であり、6 件目も `0` または `1` を受け付けます。
- 速報では着順確定前の人気が空欄になり得るため、空欄を正常値として扱います。
  この挙動は公式スタッフの[説明](https://developer.jra-van.jp/t/topic/304)と
  一致します。provider flag を理由に本文を間引かず、公式固定配置の各値を
  独立して保存します。
- 公式変更履歴の 2004-03-02 の記録はレコード長を変えず、位置 604〜717 の
  予備領域を三連単関連へ転用しています。
- 別の公式特記事項が示す三連単発売開始日 2004-08-14 より前の race では、この
  114 バイトを三連単として解釈せず `LegacyReserved604_717Hex` へ hex で
  lossless 保持し、canonical 三連単列は NULL にします。
- 境界は訂正・再提供日になり得る `MakeDate` ではなく `Year`+`MonthDay` の
  race date で判定します。これにより旧予備値を推測せず、変更前と変更後を同じ
  719 バイト envelope で区別します。

**既存 DB からの移行手順:**

- 旧 nullable key、主キーなし、予備 2・3 件目の列欠落、予備列の数値型、
  型・容量不一致、追加の `UNIQUE`/exclusion、PostgreSQL の deferrable 主キーが
  ある表は、取込や他表の additive migration より前に停止します。
- 欠けた旧払戻を既存行から復元できないため、自動 ALTER で完全扱いにせず、
  DB をバックアップして `NL_HR` / `RT_HR` / `HARAI` を現行 DDL で再作成し、
  保持範囲に合う `RACE` source を再取込してください。

#### SE（馬毎レース情報）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 の現行 555 バイト配置だけを
  受け付けます。
- 2003-04-22 より前の 547 バイト配置は、変更履歴から追加された 8 バイトは
  分かっても旧レイアウト全体を復元できないため、推測で解釈せず明示的に
  拒否します。

**identity（主キー）:**

- 現行の公式キーは `Year`, `MonthDay`, `JyoCD`, `Kaiji`, `Nichiji`, `RaceNum`,
  `Umaban`, `KettoNum` の 8 項目です。

**保存先:**

- native の `NL_SE` / `RT_SE` と標準名モードの `UMA_RACE` はこの順序の
  `NOT NULL` 主キーを使います。
- 標準名モードでは 4 つの予約領域も `reserved1`〜`reserved4` へ保持します。

**DataKubun:**

- `DataKubun=0` は 8 項目が完全に一致する 1 頭だけを削除します。
- base domain は [公式 DataKubun の検証](#datakubun) の表を参照してください。

**値の扱い:**

- 馬体重と増減は kg の整数であり、native でも 508kg/+3kg を 508/3 として
  保存します。
- status A では公式 availability に従い、本賞金 0 円は実値 0、付加賞金の
  初期値 0 は NULL として区別します。この賞金の根拠は公式フォーマット表の
  本賞金・付加賞金行です。騎手見習や着差など、別の A/B 項目で実データに
  合わせて availability 表が訂正された背景は、公式スタッフの
  [回答](https://developer.jra-van.jp/t/topic/61)を参照してください。

**既存 DB からの移行手順:**

- 旧 7 項目キーまたは主キーなしの表、キー型の不一致、追加の `UNIQUE`/
  exclusion、PostgreSQL の deferrable 主キーは取込や他表の additive migration
  より前に拒否します。
- 自動で主キーを作り替えず、DB をバックアップして対象表を現行 schema で
  再作成し、`RACE` から再取込してください。
- 正しい 8 項目キーを持つ表への非キー列の安全な additive migration は
  維持します。

#### JG（競走馬除外情報）

**公式レイアウト:**

- 現行公式 80 バイト（Ver.4.1.0 で追加、Ver.4.1.1 は血統登録番号の初期値を
  追記したのみで layout 不変）を扱います。

**identity（主キー）:**

- 公式 8 列キー（開催キー 6 列＋`KettoNum`＋出馬投票受付順番）で更新するため、
  同一馬の再投票行は共存します。

**保存先:**

- native 名モードの保存先は `NL_JG`（互換名 `Num`、`SyussoKubun`、
  `JyogaiStateKubun`）です。
- JRA-VAN 標準名モードの保存先は SDK 構造体 `JV_JG_JOGAIBA` から採った
  project canonical 名 `JOGAIBA`（`ShutsubaTohyoJun`、`ShussoKubun`、
  `JogaiJotaiKubun`）です。
- 旧名 `WEIGHT_CHANGE` は読み取り側の名前解決互換として残しますが、新規
  import 先には使いません。

**DataKubun:**

- `DataKubun` は公式どおり 0/1 のみ、出走区分・除外状態区分は公式コードのみを
  受け付けます。
- `DataKubun=0` では同じ 8 列キーの行だけを提供順に物理削除します。

**既存 DB からの移行手順:**

- 公式主キー以外の追加 `UNIQUE`/exclusion 制約や、PostgreSQL で `ON CONFLICT`
  に使えない遅延主キーを持つ既存テーブルは、置換が別キーの行を消してしまう
  ため mutation 前に拒否します。
- `WEIGHT_CHANGE` しか存在しない標準名 DB は行を変更せず停止します。
- 旧 7 列キー（受付順番を含まない）の `NL_JG` / `JOGAIBA` や列の欠けた
  `JOGAIBA` は、再投票行を安全に復元できないため自動 `ALTER` せず停止します。
- DB をバックアップして対象テーブルを現行 schema で再作成し、`RACE` で
  保持期間内の現行データを再取得してください。

#### WF（重勝式 WIN5）

**公式レイアウト:**

- 現行公式 7,215 バイト（JV-Data 4.8.0.2 / 4.9.0.1、SDK 5.0.0 `JV_WF_INFO`）を
  1 物理レコードとして扱います。
- 対象 5 レースの競馬場・回・日・レース番号、発売票数、有効票数 5 件、返還・
  不成立・的中無フラグ、キャリーオーバー金額初期・残高、払戻情報 243 枠を
  全て保存します。
- Ver.4.1.1 と Ver.4.2.0 はいずれも項目名・初期値・設定有無の変更であり、別の
  物理レイアウトではありません。旧 jrvltsql の 169 バイト復元データは取得元
  レコードとして受け付けません。

**identity（主キー）:**

- 公式キーは開催年・開催月日の 2 列です。

**保存先:**

- native 名モードの保存先は `NL_WF` / `RT_WF`（1 レコード 1 行、払戻 243 枠は
  `PayoutsJson`）です。
- JRA-VAN 標準名モードの保存先は project canonical 名 `JYUSYOSIKI_HEAD`
  （ヘッダー、主キー開催年・開催月日）と子テーブル `JYUSYOSIKI`（払戻 243 枠を
  `Num`=1〜243 の行として空欄枠も保存、主キー開催年・開催月日・`Num`、親への
  複合外部キー `ON DELETE CASCADE`）です。
- 1 物理レコードにつきヘッダー 1 行と子 243 行を提供順に transaction で
  置き換えます。
- `WIN5` は読み取り側の名前解決互換用の alias であり、新規 import 先には
  使いません。

**DataKubun:**

- データ区分は蓄積系が 0/1/2/3/7/9、速報系（`0B51`）が 0/1/2/3/9 で、それ以外は
  取り込み前に拒否します。
- `DataKubun=0` は同じキーの親子を物理削除します。`DataKubun=0` では header と
  公式キーだけを解釈し、仕様が定義しない body 値や body alias の差を削除拒否の
  根拠にしません。
- `9`（中止）は払戻が設定される場合に公式の中止用払戻組（組番 `0000000000`・
  払戻金 `000000100`・的中票数 `0000000000`）ごと状態として保持します。
- 値の有無は公式の状態別規定に従い、`1`（詳細発表時）は発売票数・有効票数・
  残高・払戻が初期値、`2`/`9` はこれらの値が設定される場合とされない場合が
  混在し、`3`/`7` では必須として検証します。

**値の扱い:**

- 対象レースの競馬場は同版の公式コード表 2001 に掲載された値から初期値・
  未使用値を除いたコードを検証し、廃止済みの競馬場・国を含むため現在使用中の
  会場一覧とは扱いません。
- 初期値 `00`、使用しないと明記されたコード、未掲載コード、小文字表記は
  受け付けません。
- 公式コードが追加された場合は、固定した仕様 manifest と検証集合を同じ変更で
  更新する必要があります。
- 各フラグは未設定時の公式初期値も `0` なので、非削除レコードでは常に `0` か
  `1` です。予備領域も公式初期値 `00`/`000000` だけを受け付けます。
- 払戻枠は空欄か組番・払戻金・的中票数の揃った組だけを受け付けます。
- キャリーオーバー金額初期は Ver.4.2.0（2012年2月21日）以降に作成された
  データでは全状態で必須です。それ以前は `1` で空欄のみ、`2`/`9` で空欄または
  数値を許容します。
- 払戻が確定する `3`/`7` で的中無フラグが `1` の場合は、組番を保持したうえで
  払戻金 `000000000`・的中票数 `0000000000` の公式表現だけを受け付けます。
  中止状態 `9` は上記の中止用払戻が優先されるため、この的中無規則を一律には
  適用しません。

**transaction:**

- native・標準名・速報の各 WF 書込は batch 途中の DB 例外で全体を rollback し、
  行単位 fallback による部分成功や、rollback された操作を成功件数へ残すことを
  許しません。
- `inserted` は最終行数ではなく、提供順に正常適用された操作数です。
- 速報 grouped batch と時系列 CLI の境界は
  [共通規則](#grouped-batch-cli-transaction) を参照してください。

**既存 DB からの移行手順:**

- 主キーや `HatubaiHyosu` のない旧 `JYUSYOSIKI_HEAD`、`Num`・主キー・外部キーの
  ない旧 `JYUSYOSIKI`、親子の片方だけが存在する DB、`WIN5` しか存在しない
  標準名 DB は自動 `ALTER` せず、行や schema を変更する前に停止します。
- DB をバックアップして両テーブルを現行 schema（親を先に作成）で再作成し、
  `RACE` で保持期間内の現行データを再取得してください。
- WF 保存先は全列の型・文字容量と主キーを取込前に検証します。
- PostgreSQL の主キーは `ON CONFLICT` で使用できる valid・ready・即時・非
  deferrable でなければならず、公式キー以外の追加 `UNIQUE`/排他制約も、置換時に
  別開催を消し得るため拒否します。
- 検索用の非一意 index は保持できます。

### 票数系（H1 / H6）

#### H1（票数１・全掛式）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 の 28,955 バイト配置（単勝・複勝・枠連・馬連・ワイド・
  馬単・3連複の 7 賭式と、11 バイト × 14 個の票数合計）だけを受け付けます。
- 1 レコードは 1 レースの完全な snapshot です。parser は 1 組合せを 1 行へ
  展開し、合計だけを持つ `BetType=Total` 行（`Kumi=TOTAL`）を最後に返します。

**identity（主キー）:**

- 公式 identity はレースキー（`Year`・`MonthDay`・`JyoCD`・`Kaiji`・`Nichiji`・
  `RaceNum`）で、native では賭式（`BetType`）と組番（`Kumi`）を加えた 8 列です。
- 標準名では header table `HYOSU` がレースキー、子 table は
  レースキー＋`Umaban`（`HYOSU_TANPUKU`）またはレースキー＋`Kumi`
  （`HYOSU_WAKU`・`HYOSU_UMARENWIDE`・`HYOSU_UMATAN`・`HYOSU_SANREN`）です。

**保存先:**

- native `NL_H1`、速報 `RT_H1`、標準名 `HYOSU` 系はいずれも公式 field
  capacity と NOT NULL の key 列を使い、1 レース分の snapshot を丸ごと
  置換します。
- H1 は蓄積系（`RACE`）と速報系（`0B20`）の両方で提供されるため、
  速報経路は `RT_H1` へルーティングします。

**DataKubun:**

- 公式値は `0`（削除）・`2`（前日最終売上）・`4`（最終）・`5`（月曜最終）・
  `9`（レース中止）だけです。`1` や `3` は受け付けません。
- `DataKubun=0` はレースキーだけを使う物理 exact erase で、native・速報・
  標準名 header/子 table のすべてから対象レースの行を削除します。tombstone は
  残しません。削除指示は本文を持たないため、key と header だけを検証します。

**値の扱い:**

- 人気順は数値ではありません。公式に `--`（発売前取消）・`**`（発売後取消）・
  空白（登録なし）も取り得るため、人気順列はすべて文字列として保持します。
  対象は native `NL_H1`/`RT_H1` の `Ninki`、標準名 `HYOSU_TANPUKU` の
  `TanNinki`・`FukuNinki`、`HYOSU_UMARENWIDE` の `UmarenNinki`・`WideNinki`、
  `HYOSU_WAKU`・`HYOSU_UMATAN`・`HYOSU_SANREN` の `Ninki` です。このうち
  数値列だったのは `NL_H1`/`RT_H1` の `Ninki`（`INTEGER`）と
  `HYOSU_WAKU`/`HYOSU_UMATAN`/`HYOSU_SANREN` の `Ninki`（`SMALLINT`）で、
  旧 schema は取消マーカーを `NULL` に落とします。`HYOSU_TANPUKU` と
  `HYOSU_UMARENWIDE` の人気順列は以前から文字列です。
- 空白の人気順は `NULL` ではなく空文字で保持します（他の table の
  「空欄→`NULL`」規則の例外）。
- 返還馬番・返還枠番・返還同枠は位置ごとの `0`/`1` フラグ列で、公式初期値は
  `0` です。provider が未設定位置を空白で送る実測があるため空白も提供値として
  保持しますが、それ以外の文字と桁落ちは拒否します。
- 票数・票数合計は 11 バイト ASCII 数字（単位百円、ALL0 は発売前取消し・発売
  票数なし）です。provider が合計エリアを空白で送る場合だけ空値を許容します。
- 発売フラグは `0`・`1`・`3`・`7`、複勝着払キーは `0`・`2`・`3` だけを
  受け付けます。

**既存 DB からの移行手順:**

- 既存の nullable key、主キーの欠落・短縮、型違い、容量不足、generated /
  identity 列、追加列、追加 UNIQUE/FK/CHECK を持つ `NL_H1` / `RT_H1` /
  `HYOSU` 系は自動修復せず、mutation 前に停止します。
- 標準名の子 table では、公式キー以外の UNIQUE index も拒否します（別レースの
  行を置換や衝突で失うため）。import が作成する公式キー index だけを許可します。
- 既存 DB に対する追加 migration も、`NL_H1` / `RT_H1` / `HYOSU`（子 table を
  含む）が現行契約を満たすまで停止します。
- DB をバックアップして対象 table を現行 schema で再作成し、保持中の `RACE`
  source から再取込してください。人気順列が数値型だった DB では、再取込しない
  限り取消マーカーは復元されません。

### マスタ系（HN / SK / UM / BT / KS / CH / HS）

#### HN（繁殖馬マスタ）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 251 バイト配置だけを受け付け、旧 245
  バイト配置は拒否します。

**identity（主キー）:**

- 公式 identity は 10 桁の `HansyokuNum` です。

**保存先:**

- native `NL_HN` と標準名 `HANSYOKU` は同じ ordered primary key、必須
  header/key/body、公式 field capacity を使い、status 1/2 を provider 順に
  同じ行へ反映します。
- HN は蓄積系 master だけであり、`RT_HN` は作成しません。

**DataKubun:**

- `DataKubun=0` はこの key だけを使う物理 exact erase です。削除指示の非 key
  本文を decode しない扱いは erase を失わせないための project policy で、
  provider 仕様が任意 binary 本文を規定するという意味ではありません。

**値の扱い:**

- 公式に空欄になり得る `BameiKana`・`BameiEng`・`SanchiName` は、両 table とも
  `NULL` ではなく空文字で保持します（他の table の「空欄→`NULL`」規則の例外）。
- 欠落した項目や `None` は検証で拒否され、`NULL` として保存されません。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、容量不足、generated /
  identity 列、追加列または追加 UNIQUE/FK/CHECK を持つ `NL_HN` / `HANSYOKU`
  は自動修復せず、mutation 前に停止します。
- DB をバックアップして両 table を現行 schema で再作成し、保持中の `BLDN`
  source から再取込してください。

#### SK（産駒マスタ）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 208 バイト配置（生産者コード 8 桁、
  3 代血統 14 × 10 桁）だけを受け付け、旧 178 バイト配置は拒否します。

**identity（主キー）:**

- 公式 identity は 10 桁の `KettoNum`（血統登録番号）です。正確な 10 桁 ASCII
  数字だけを受け付けます。

**保存先:**

- native `NL_SK` と標準名 `SANKU` は同じ列名・同じ `KettoNum` 主キー・必須
  header/key/body・公式 field capacity を使い、status 1/2 を provider 順に
  同じ行へ反映します。父・母・父父・父母・母父・母母・父父父・父父母・父母父・
  父母母・母父父・母父母・母母父・母母母の 14 個の繁殖登録番号（`FNum` 〜
  `MMMNum`）はすべて個別列で保持します。
- SK は蓄積系（`BLDN`）master だけであり、`RT_SK` は作成せず、速報経路にも
  ルーティングしません。

**DataKubun:**

- `DataKubun=0` はこの key だけを使う物理 exact erase です。削除指示の非 key
  本文を decode しない扱いは HN と同じ project policy です。

**値の扱い（公式 4.9.0.1 の domain）:**

- `BirthDate` は実在する `yyyymmdd`、`SexCD`/`HinsyuCD`/`KeiroCD` は 1/1/2 桁の
  数字（コード表 2202/2201/2203 の値は将来増え得るため表照合はしません）、
  産駒持込区分 `SankuMochiKubun` は `0/1/2/3` のみ（`9:その他` は繁殖馬マスタ
  HN だけの値）、`ImportYear` は 4 桁（内国産の `0000` も有効）、`BreederCode`
  は 8 桁数字、14 個の繁殖登録番号は 10 桁数字（未設定の `0000000000` も有効）
  です。
- 公式に空欄になり得る `SanchiName` は、両 table とも `NULL` ではなく空文字で
  保持します。欠落した項目や `None` は検証で拒否され、`NULL` として保存されません。
- `ImportYear` の保存型は table で異なります。`NL_SK.ImportYear` は `INTEGER`、
  `SANKU.ImportYear` は `VARCHAR(4)` なので、公式に有効な `0000` は native では
  `0`、標準名では `0000` として読み戻ります（値は 4 桁 zero fill で復元できます）。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、容量不足、generated /
  identity 列、追加列または追加 UNIQUE/FK/CHECK を持つ `NL_SK` / `SANKU`
  は自動修復せず、mutation 前に停止します。旧標準名 `HANSYOKU_UMA` だけがある
  DB も引き続き拒否します。
- DB をバックアップして両 table を現行 schema で再作成し、保持中の `BLDN`
  source から再取込してください。

#### UM（競走馬マスタ）

**公式レイアウト:**

- 公式 1609 バイトを扱い、血統登録番号 `KettoNum` を 10 文字のまま保存します。

**identity（主キー）:**

- native 名モードの `NL_UM` と JRA-VAN 標準名モードの `UMA` は、どちらも
  `KettoNum` の 1 列だけを主キーとして同じ登録馬の更新を置き換え、異なる
  登録馬を共存させます。
- `KettoNum` は正確な 10 桁 ASCII 数字だけを受け付けます。

**保存先:**

- native `NL_UM`、標準名 `UMA`。どちらも同じ `KettoNum` 主キー・必須
  header/key/body・公式 field capacity を使い、status 1/2/3/4/9 を provider 順に
  同じ行へ反映します。
- 現行の標準名 `UMA` では、公式レコード内の 27 組×6 着回数、4 脚質、登録
  レース数も個別列へ欠落なく展開し、抹消年月日の `00000000` は 8 文字のまま
  保持します。
- UM は蓄積系（`DIFN`/`BLDN`）master だけであり、`RT_UM` は作成せず、速報経路
  にもルーティングしません。

**DataKubun:**

- base domain は [公式 DataKubun の検証](#datakubun) の表と `UM=9` の
  `MakeDate` 境界を参照してください。
- `DataKubun=0` はこの key だけを使う物理 exact erase で、両 table から行を
  削除します（tombstone 行は残しません）。削除指示の非 key 本文を decode しない
  扱いは HN / SK と同じ project policy です。
- `9:抹消` は削除ではなく生存中の更新です。抹消区分・抹消年月日を含む本文を
  同じ行へ反映します。

**値の扱い（公式 4.9.0.1 の domain）:**

- `RegDate`/`DelDate`/`BirthDate` は実在する `yyyymmdd`（公式初期値の
  `00000000` も有効）、競走馬抹消区分 `DelKubun` は `0/1`、JRA 施設在きゅう
  フラグ `ZaikyuFlag` は `0/1` または空欄（平成 18 年 6 月 6 日より前は未設定）
  です。
- `UmaKigoCD`/`SexCD`/`HinsyuCD`/`KeiroCD`/`TozaiCD` は 2/1/1/2/1 桁の数字、
  `ChokyosiCode` は 5 桁、`BreederCode` は 8 桁、`BanusiCode` は 6 桁、累積
  賞金 6 項目は各 9 桁、27 組の着回数は各 18 桁、脚質傾向は 12 桁、登録レース数
  は 3 桁の数字です（コード表 2201-2203/2204/2301 の値は将来増え得るため表照合
  はしません）。
- 3 代血統の 14 個の繁殖登録番号は 10 桁数字（未設定の `0000000000` も有効）、
  14 個の馬名は公式 36 バイト以内です。
- 公式に空欄になり得るテキスト項目（`BameiEng`・`Reserved`・`ZaikyuFlag`・
  `ChokyosiRyakusyo`・`Syotai`・`BreederName`・`SanchiName`・`BanusiName`・
  3 代血統の馬名）は、両 table とも `NULL` ではなく空文字で保持します。欠落した
  項目や `None` は検証で拒否され、`NULL` として保存されません。
- 累積賞金 6 項目の保存型は table で異なります。`NL_UM` は `REAL`、`UMA` は
  `VARCHAR(9)` なので、公式の 9 桁 zero fill は native では数値として、標準名では
  9 文字のまま読み戻ります。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、容量不足、generated /
  identity 列、追加列または追加 UNIQUE/FK/CHECK を持つ `NL_UM` / `UMA` は
  自動修復せず、mutation 前に停止します。v2 で `NL_UM.ZaikyuFlag` は
  `INTEGER` から `TEXT` になり（公式の空欄を保持できないため）、両 table の
  全列が `NOT NULL` になりました。
- 公式主キー以外の `UNIQUE`/exclusion 制約や、PostgreSQL で `ON CONFLICT` に
  使えない遅延主キーがある既存テーブルも、行を置換して消失させるおそれが
  あるため変更前に拒否します。
- 旧版が作成した標準名 `UMA` は `KettoNum` 列と主キーを欠いていたため、安全に
  既存行の識別子を復元できません。この旧テーブルまたは別の主キーを持つ
  テーブルが存在する場合は、列追加や行更新より前に停止します。
- DB をバックアップし、対象 `UMA` を現行 schema で再作成してから `DIFN` で
  競走馬マスタを再取得してください。

#### BT（系統情報）

**公式レイアウト:**

- 現行公式 6,889 バイトを扱い、10 文字の `HansyokuNum`、`KeitoId`、
  `KeitoName`、最大 6,800 バイトの `KeitoEx` を保存します。
- 旧 6,887 バイト BT は 8 文字の繁殖登録番号を前提とするため、現行 layout
  として受け付けません。

**identity（主キー）:**

- `HansyokuNum` を主キーに更新します。

**保存先:**

- native 名モードの保存先は `NL_BT`、JRA-VAN 標準名モードの保存先は公式名
  `KEITO` です。
- 旧名 `BLOOD` は読み取り側の名前解決互換として残しますが、新規 import 先には
  使いません。

**DataKubun:**

- `DataKubun=0` では同じキーの行を物理削除します。

**既存 DB からの移行手順:**

- 標準名モードの開始時は既存の標準名テーブルを変更前に一括検証するため、
  再構築が必要な旧 `KEITO` または legacy-only table が残る DB では、BT 以外の
  import も schema 変更前に停止します。
- 主キーのない部分的な `KEITO`、10 文字未満の key 列、6,800 文字未満の説明列、
  または旧名 `BLOOD` しか存在しない標準名 DB は、欠落値を安全に復元できない
  ため行や schema を自動変更せず停止します。
- DB をバックアップして対象テーブルを現行 schema で再作成し、`BLDN` の
  option 3/4 で現行データを再取得してください。

#### KS（騎手マスタ）

**公式レイアウト:**

- 公式 4173 バイトを 1 物理レコードとして扱います。旧 772 バイトの復元データは
  取得元レコードとして受け付けません。

**保存先:**

- native では `NL_KS` と `NL_KS_SEISEKI`、JRA-VAN 標準名モードでは `KISYU` と
  `KISYU_SEISEKI` へ原子的に保存します。
- `NL_KS` は基本情報・初騎乗/初勝利・最近重賞 3 件、`NL_KS_SEISEKI` は
  本年・前年・累計の 3 行を保持します。

**DataKubun:**

- base domain は [公式 DataKubun の検証](#datakubun) の表を参照してください。

**既存 DB からの移行手順:**

- 既存の標準名テーブルが主キー契約を満たさない場合は行を変更せず停止します。
- 現行 schema で再作成した後、`DIFN` の option 3/4 で全件を再取得してください。

#### CH（調教師マスタ）

**公式レイアウト:**

- 公式 3862 バイトを 1 物理レコードとして扱います。旧 592 バイトの復元データは
  取得元レコードとして受け付けません。

**保存先:**

- native では `NL_CH` と `NL_CH_SEISEKI`、JRA-VAN 標準名モードでは `CHOKYO` と
  `CHOKYO_SEISEKI` へ原子的に保存します。
- `NL_CH` は header・最近重賞 3 件、`NL_CH_SEISEKI` は本年・前年・累計の 3 行を
  保持します。

**DataKubun:**

- base domain は [公式 DataKubun の検証](#datakubun) の表を参照してください。

**既存 DB からの移行手順:**

- 旧標準名テーブルは主キーと文字列日付の契約を満たさないため、自動変換せず
  停止します。
- バックアップ後に両テーブルを現行 schema で再作成し、保持期間内の現行データを
  再取得してください。

#### HS（競走馬市場取引価格）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 200 バイト配置だけを受け付け、旧 196
  バイト配置は常に拒否します。

**identity（主キー）:**

- 公式の保存 identity は `KettoNum`, `SaleCode`, `FromDate` の 3 項目です。

**保存先:**

- native `NL_HS` と標準名 `SALE` は同じ ordered primary key、必須 header/key、
  公式 field capacity を使います。
- HS は蓄積系のみで、`RT_HS` は作成せず、realtime 入口へ渡された HS は DB と
  local realtime cache の両方を変更せず拒否します。
- 現行 parser または同等の caller validation を通った行には
  `CurrentLayoutVersion=200` を保存します。

**DataKubun:**

- `DataKubun=0` はこの key だけを使う exact erase です。非 key 本文を decode
  しない扱いは exact erase を失わせないための project policy であり、
  provider 仕様が任意 binary 本文を規定しているという意味ではありません。

**値の扱い:**

- 現行 10 バイトの `HansyokuFNum` / `HansyokuMNum` 欄には 8 桁値＋space
  padding も正当に存在するため、strip 後の 8 文字は旧世代判定の根拠に
  なりません。
- 過去 record の `Barei` は公式 setup で 2001 年以降の算出方法へ統一済みであり、
  `MakeDate` から再解釈しません。一方、`SaleName` は provider が保持する当時
  表記をそのまま保存します。

**transaction:**

- `auto_commit=False` の同一呼出しで後続 HS が検証失敗した場合は、先行する
  未確定行とその統計を rollback します。
- `auto_commit=True` では既に確定した provider operation を残す incremental
  semantics であり、失敗した後続 record を成功件数へ加えません。
- 共通規則は [通常インポートの transaction / rollback 規約](#transaction-rollback)
  を参照してください。

**既存 DB からの移行手順:**

- v2 以前の `NL_HS` / `SALE` は、空 table も含めて父母繁殖登録番号の値長などから
  世代を推測して自動移行しません。バックアップ後に table を再作成し、現行 200
  バイト source から再取込してください。
- 唯一の加算移行対象は、現行 schema と既存列が完全に互換で、行が空であり、
  native `NL_HS` の `CurrentLayoutVersion` / `RecordDelimiter` だけが欠ける
  場合です。

### 調教・コース系（HC / WC / CS）

#### HC（坂路調教）

**公式レイアウト:**

- 現行 JV-Data 4.9.0.1 / SDK 5.0.0 の 60 バイト配置だけを受け付けます。
- 美浦の測定距離は 2004-11-30 に 600m から 800m へ変わりましたが、物理 record
  長と 4 項目 identity は変わりません。

**identity（主キー）:**

- `TresenKubun`, `ChokyoDate`, `ChokyoTime`, `KettoNum` の 4 項目です。

**保存先:**

- native `NL_HC` と標準名 `HANRO` は同じ ordered primary key、必須
  header/key/body、公式 field capacity を使用します。
- HC は蓄積系のみで `RT_HC` は作成しません。

**DataKubun:**

- `DataKubun=0` は 4 項目 key だけを使う exact erase です。非 key 本文を decode
  しないのは削除指示を失わせないための project policy であり、provider 仕様が
  任意 binary 本文を規定するという意味ではありません。

**値の扱い:**

- 7 つの走破・lap time を 0.1 秒単位の provider 整数から秒へ正規化します。
  公式の測定不能値 `0000`/`000` は 0.0 秒として欠損と混同せず保持します。

**既存 DB からの移行手順:**

- 既存の nullable、keyless、wrong-key、wrong-type、追加列または追加
  UNIQUE/FK/CHECK を持つ `NL_HC` / `HANRO` は自動修復せず、mutation 前に
  停止します。
- バックアップ後に現行 schema で再作成し、`SLOP` を再取込してください。

#### WC（ウッドチップ調教）

**公式レイアウト:**

- JV-Data 4.9.0.1 と SDK 5.0.0 の 105 バイト配置を使用し、10 ハロンから
  1 ハロンまでの合計・ラップを保存します。
- 4.7.0.1 で追記されたのは美浦・栗東の提供開始時期と計測距離の説明であり、
  別の物理レイアウトではありません。

**identity（主キー）:**

- 公式キーはトレセン区分・調教年月日・調教時刻・血統登録番号の 4 項目です。
  `Course`（コース）や馬場周りは公式キーではありません。4 項目キーは
  [JRA-VAN ソフトサポートの回答](https://developer.jra-van.jp/t/topic/99)とも
  一致します。

**保存先:**

- native `NL_WC`、標準名モード `WOOD`。`WOOD` はデータ種別名と SDK 構造に
  対応させた jrvltsql の標準名モード上の canonical table 名であり、提供元が
  SQL DDL やテーブル名を規定しているという意味ではありません。

**DataKubun:**

- `0` は同じキーの削除です。

**値の扱い:**

- タイムが全桁 9 のデータは規定内として配信されるため、欠損へ置換せず数値
  sentinel として保存します
  （[スタッフ回答](https://developer.jra-van.jp/t/topic/367)）。

**既存 DB からの移行手順:**

- 旧版 jrvltsql が作成した `Course` 入り・トレセン区分なしの主キーは自動修復
  せず、取込前に拒否します。
- 公式主キー以外の追加 `UNIQUE`/exclusion 制約や、PostgreSQL で `ON CONFLICT`
  に使えない遅延主キーを持つ既存テーブルは、置換が別キーの行を消してしまう
  ため mutation 前に拒否します。

#### CS（コース情報）

**公式レイアウト:**

- JV-Data 4.8.0.2 / 4.9.0.1 と SDK 5.0.0 で同一の 6,829 バイト配置です。
  6,800 バイトの `CourseEx` を native `NL_CS` と標準名モード `COURSE` の両方へ
  保存します。
- 2009 年の導入直後に仕様書の誤記訂正履歴はありますが、根拠のない旧 binary
  layout は受け付けません。また、2023 年には異常長の CS データが配信され、
  [公式サポートが不備を認めて再提供した事例](https://developer.jra-van.jp/t/topic/237)が
  あるため、6,829 バイト以外を推測補正せず拒否します。

**identity（主キー）:**

- 公式キーは競馬場コード・距離・トラックコード・コース改修年月日（改修後に
  最初に開催された日）の 4 項目です。

**保存先:**

- native `NL_CS`、標準名モード `COURSE`。

**DataKubun:**

- `DataKubun=2` は行だけでなく別途取得したコース図も更新される場合があるため、
  `JVCourseFile`/`JVCourseFile2` の結果を独自保存する利用者は図も更新して
  ください。

**値の扱い:**

- 競馬場コードとトラックコードは公式コード表 2001/2009 の有効値に限定し、
  未定義・未使用コードや物理幅を超える本文は取込前に拒否します。

**既存 DB からの移行手順:**

- 旧 jrvltsql の 3 項目主キー `NL_CS`、主キーなしの `COURSE`、本文列がないまま
  既存行を持つ `COURSE`、追加の一意制約を持つ表は、別改修日の履歴消失・本文
  欠損・再取込重複を避けるため取込前に拒否します。
- 正しい 4 項目主キーを持つ空の `COURSE` だけは、欠けている列が `CourseEx`
  だけなら安全に追加します。
- それ以外は既存表をバックアップし、現行 DDL で再作成して `COMM` を
  再取込してください。

### 出走時点情報・マイニング系（CK / DM / TM）

#### CK（出走時点情報）

**公式レイアウト:**

- 現行公式 6,870 バイトの 1,729 scalar leaf を扱います。旧 6,864 バイトは
  現行 offset と混同せず拒否します。

**identity（主キー）:**

- 7 列の公式キーです。

**保存先:**

- PostgreSQL の 1 テーブル列数上限を超えないよう、native 名モードでは互換親
  `NL_CK` と `NL_CK_CHAKU` 278 行、`NL_CK_RUIKEI` 8 行を 1 物理レコード単位の
  transaction で更新します。
- CK の JRA-VAN 標準名モードはまだ実装しておらず、`CHOKYO_DETAIL` へ誤って
  部分保存せず明示的に停止します。

**DataKubun:**

- `DataKubun=0` は 7 列の公式キーで親子を削除します。
- base domain は [公式 DataKubun の検証](#datakubun) の表を参照してください。

**既存 DB からの移行手順:**

- 既存 `NL_CK` には完全展開していない行があるため、追加される
  `CKStorageVersion` が `NULL` の行を完全格納済みと扱ってはいけません。
- 現行 `SNPN` を再取得して `CKStorageVersion=1`、子行数 278/8 をキーごとに
  確認してください。

#### DM（タイム型データマイニング予想）

**公式レイアウト:**

- 公式 303 バイトの 18 頭配列を扱います。

**保存先:**

- native 名モードでは `NL_DM` / `RT_DM` へ馬ごとの行として保存し、JRA-VAN
  標準名モードでは `MINING` へ 1 レース 1 行の wide 形式で保存します。

**値の扱い:**

- `DMTime` は公式 SDK と同じ 5 桁文字列（9分99秒99）を保持します。

**既存 DB からの移行手順:**

- 旧 48 バイト復元データ、旧標準名 `DATA_MASTER`、主キーのない `MINING`、
  数値型の `DMTime1`〜`DMTime18` は安全に自動変換できないため、取り込みを
  停止して再構築を求めます。

DataKubun と速報 snapshot・transaction の扱いは [DM / TM 共通](#dm-tm-snapshot-transaction) を参照してください。

#### TM（対戦型データマイニング予想）

**公式レイアウト:**

- 公式 141 バイトの 18 頭配列を扱います。

**保存先:**

- native 名モードでは `NL_TM` / `RT_TM` へ馬ごとの行として保存し、JRA-VAN
  標準名モードでは `TAISENGATA_MINING` へ 1 レース 1 行の wide 形式で
  保存します。

**値の扱い:**

- `TMScore` は公式 SDK と同じ 4 桁文字列を保持し、右端 1 桁が小数第一位です。

**既存 DB からの移行手順:**

- 旧 39 バイト復元データ、旧標準名 `TIME_MASTER`、主キーのない
  `TAISENGATA_MINING`、`TMScore` が整数型の旧 native テーブルは安全に自動
  変換できないため、取り込みを停止して再構築を求めます。

DataKubun と速報 snapshot・transaction の扱いは [DM / TM 共通](#dm-tm-snapshot-transaction) を参照してください。

#### DM / TM 共通（速報 snapshot と transaction）

**DataKubun:**

- base domain（`0`, `1`, `2`, `3`, `7`）と速報での `7` 拒否は
  [公式 DataKubun の検証](#datakubun) を参照してください。

**速報 snapshot の受け付け:**

- 速報の非削除 DM/TM は、1 物理レコードから展開された同一種別・同一
  `DataKubun` の 1〜18 頭を完全な list として渡す必要があります。
- 共通 metadata、展開 index、馬番（`01`〜`18`、重複なし）、metadata 内と展開後の
  正規化済み各行内容が完全一致しない list、または 19 頭以上は DB へ到達する
  前に拒否します。
- `process_parsed_record` へ渡す list は 1 物理スナップショットだけを表し、
  他種別との混在を拒否します。非削除の 1 行 dict を完全 snapshot とは
  扱いません。
- `DataKubun=0` だけは metadata を持たない単一の削除レコードとして
  受け付けます。
- `process_parsed_records_batch` は、先頭行の展開 index と metadata 件数で
  複数の DM/TM 物理スナップショットを分割し、間にある削除や他種別レコードも
  提供順の 1 transaction で処理します。

**transaction:**

- 途中の不完全な展開、metadata の無い非削除行、または 1 操作でも DB 書込に
  失敗した batch は、先行操作も含めて全て rollback し、`inserted=0` を
  返します。
- 成功時の `inserted` は最終行数ではなく、提供順に正常適用した展開行と隣接
  レコードの操作数です。
- DM/TM の native 速報スナップショット置換は、既存レース行の削除後に書込が
  失敗した場合、caller 所有を含む active transaction 全体を rollback します。
- rollback 不能時は接続を無効化し、それも失敗した場合は batch・optimized・
  single・速報の全入口から `TransactionRecoveryError` を送出し、通常の失敗
  結果へ変換しません。
