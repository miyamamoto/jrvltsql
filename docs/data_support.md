# 対応データ種別一覧

このページでは、jrvltsql が対応している JRA-VAN DataLab / JV-Link の
データ種別、レコード種別、保存先テーブル、運用コマンドをまとめます。

jrvltsql は JRA / 中央競馬専用です。NAR / 地方競馬はこのリポジトリの対象外です。

## このページの読み方

ドキュメントは次の 3 層に分かれています。上から順に読めば、3 分で結論、
必要に応じて参照表、さらに必要なら契約の詳細へ進めます。

| 層 | 内容 | 場所 |
| --- | --- | --- |
| 1. 要約 | 「先に結論」の表。できること・できないことと使うコマンド | このページの「先に結論」（すぐ下） |
| 2. 参照表 | 取得系統 / JVOpen 蓄積系データ / JVRTOpen 速報レース・開催情報 / JVRTOpen オッズ・票数 / パーサー・テーブル対応 / 対象外 | このページの各表 |
| 3. 契約詳細 | レコード種別ごとの公式レイアウト・主キー・`DataKubun`・既存 DB からの移行手順、および共通の検証・transaction 規約 | 要点はこのページの「レコード別の契約・移行手順（要点）」、全文は [レコード別の公式契約と移行手順](record_contracts.md) |

## 先に結論

| 知りたいこと | 結論 | 使うコマンド / 保存先 |
| --- | --- | --- |
| 出馬表、成績、払戻を保存できるか | できます。 | `quickstart.bat` または `quickstart_timeseries.bat`。主に `NL_RA`, `NL_SE`, `NL_HR` に保存します。 |
| 確定オッズを保存できるか | 全賭式でできます。 | `RACE` 取得で `NL_O1`〜`NL_O6` に保存します。ただし投資判断時点のオッズではありません。 |
| 過去1年分の時系列オッズをまとめて取れるか | 単複枠・馬連だけできます。 | `0B41` / `0B42` を `TS_O1` / `TS_O2` に保存します。SQLite でも PostgreSQL でも保存できます。 |
| 三連複・三連単の締切前オッズを長期評価できるか | 開催週から蓄積していればできます。 | `0B30` または `0B35` / `0B36` を `TS_SOKUHO_O5` / `TS_SOKUHO_O6` に保存します。JRA-VAN 側の保持は約1週間です。 |
| `daily_sync.bat` は SQLite / PostgreSQL の両方で使えるか | 使えます。 | `daily_sync.bat --db sqlite` または `daily_sync.bat --db postgresql` で通常データ、公式時系列、開催週速報を更新します。通常データだけにする場合は `--no-timeseries --no-realtime` を指定します。 |
| NAR / 地方競馬も取れるか | このリポジトリでは取れません。 | JRA 専用です。 |

## 表の見方

| 表記 | 意味 |
| --- | --- |
| 対応済み | パーサー、スキーマ、importer / updater の保存経路があります。 |
| 運用導線あり | 保守している CLI コマンドまたは batch ファイルがあります。 |
| パーサー・スキーマのみ | レコードのパーサーとテーブルはありますが、推奨運用フローは未整備です。 |
| 非対応 | 現在の jrvltsql の対象外です。 |

実装上の正本は以下です。

- `src/jvlink/constants.py`
- `src/parser/factory.py`
- `src/database/table_mappings.py`
- `src/database/schema.py`
- `src/cli/main.py`

## 取得系統

| 系統 | JV-Link API | option / データ種別 | 運用コマンド | キー / 範囲 | 対応状況 |
| --- | --- | --- | --- | --- | --- |
| 蓄積系 通常データ | `JVOpen` | option `1` | `jltsql fetch --spec <SPEC> --option 1` | FromTime 形式の日付範囲 | 対応済み |
| 今週データ | `JVOpen` | option `2` | `quickstart.bat`, `daily_sync.bat`, `jltsql fetch --option 2` | 今週開催分 | `TOKU`, `RACE`, `SNPN`, `TCVN`, `RCVN` に対応 |
| セットアップデータ | `JVOpen` | option `3` / `4` | `quickstart.bat`, `jltsql fetch --option 3/4` | 初期構築用の過去範囲 | 下記の蓄積系 spec に対応 |
| 速報レース・開催情報 | `JVRTOpen` | `0B11`〜`0B17` | `jltsql realtime start --specs <SPEC>` | `YYYYMMDD` | 下記レコードに対応 |
| 速報オッズ・票数 | `JVRTOpen` | `0B20`, `0B30`〜`0B36` | `jltsql realtime timeseries --spec <SPEC>` | `YYYYMMDDJJRR` | 対応済み。JRA-VAN 側の保持は約1週間 |
| 公式時系列オッズ | `JVRTOpen` | `0B41`, `0B42` | `quickstart_timeseries.bat`, `quickstart.bat --yes --include-timeseries`, `quickstart_postgres_timeseries.bat`, `fetch_timeseries_postgres.bat`, `jltsql realtime odds-timeseries` | `YYYYMMDDJJRR` | 対応済み。JRA-VAN 側の保持は約1年 |

## JVOpen 蓄積系データ

| データ種別 | jrvltsqlで非対応の旧仕様名 | 内容 | 主なレコード種別 | 保存先テーブル | option 1 | option 2 | option 3/4 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TOKU` | - | 特別登録馬 | `TK` | `NL_TK_RACE`（レース）、`NL_TK`（登録馬） | はい | はい | はい | 21,657バイトの300頭枠を全て扱います。standard / full quickstart に含めています。 |
| `RACE` | - | レース、出走馬、払戻、確定オッズ、票数、WIN5、除外情報 | `RA`, `SE`, `HR`, `H1`, `H6`, `O1`〜`O6`, `WF`, `JG` | `NL_RA`, `NL_SE`, `NL_HR`, `NL_H1`, `NL_H6`, `NL_O1`〜`NL_O6`, `NL_WF`, `NL_JG` | はい | はい | はい | 中核データです。`NL_O*` は確定オッズで、投資判断時点のオッズではありません。 |
| `DIFN` | `DIFF` | 蓄積系マスタ差分 | `UM`, `KS`, `CH`, `BR`, `BN`, `RC` | `NL_UM`, `NL_KS`, `NL_KS_SEISEKI`, `NL_CH`, `NL_CH_SEISEKI`, `NL_BR`, `NL_BN`, `NL_RC` | はい | いいえ | はい | 旧名 `DIFF` は受け付けません（[旧仕様 dataspec 名](record_contracts.md#dataspec-diff-blod-snap-hose-tcov-rcov) 参照）。 |
| `BLDN` | `BLOD` | 血統情報 | `HN`, `SK`, `BT` | `NL_HN`, `NL_SK`, `NL_BT` | はい | いいえ | はい | 旧名 `BLOD` は受け付けません（同上）。 |
| `MING` | - | データマイニング予想 | `DM`, `TM` | `NL_DM`, `NL_TM` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `SLOP` | - | 坂路調教関連 | `HC` | `NL_HC`（native）、`HANRO`（標準名モード） | はい | いいえ | はい | 現行`DataKubun=1`は60バイトの全項目を保存します。`DataKubun=0`は本文を保存せず、公式4項目キーでexact eraseします。standard / full quickstart に含めています。 |
| `WOOD` | - | ウッドチップ調教関連 | `WC` | `NL_WC`（native）、`WOOD`（標準名モード） | はい | いいえ | はい | 現行105バイトを全項目保存します。公式キーはトレセン区分・調教年月日・調教時刻・血統登録番号の4項目で、`0` は同じキーの削除です。standard / full quickstart に含めています。 |
| `YSCH` | - | 開催スケジュール | `YS` | `NL_YS` | はい | いいえ | はい | 開催カレンダー保守に使います。 |
| `HOSN` | `HOSE` | 競走馬市場取引価格 | `HS` | `NL_HS` | はい | いいえ | はい | 旧名 `HOSE` は受け付けません（同上）。 |
| `HOYU` | - | 馬名の意味由来 | `HY` | `NL_HY` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `COMM` | - | 各種解説・コース情報 | `CS` | `NL_CS`（native）、`COURSE`（標準名モード） | はい | いいえ | はい | 現行6,829バイトと6,800バイトのコース説明を完全保存します。standard / full quickstart に含めています。 |
| `SNPN` | `SNAP` | 出走時点情報 | `CK` | `NL_CK`、`NL_CK_CHAKU`、`NL_CK_RUIKEI` | はい | はい | はい | 現行6,870バイトをnative名モードで完全格納します。既定 quickstart では使っていません。旧名 `SNAP` は受け付けません（同上）。 |
| `TCVN` | `TCOV` | 特別登録馬情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。旧名 `TCOV` は受け付けません（同上）。 |
| `RCVN` | `RCOV` | レース情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。旧名 `RCOV` は受け付けません（同上）。 |

`quickstart` の `standard` モードと `full` モードは、取得するデータ種別の一覧が
同一です（`scripts/quickstart.py` の `STANDARD_SPECS` と `FULL_SPECS`）。
確定オッズ（`O1`〜`O6`）は `RACE` に含まれるため、`full` でも追加のデータ種別は
増えません。

`O1`〜`O6` は `RACE` や速報系ストリームに含まれるレコード種別IDであり、
単独の `JVOpen` データ種別IDではありません。確定オッズは `RACE` を取得して
`NL_O1`〜`NL_O6` へ保存します。JV-Link APIと `jltsql fetch` は、同じoptionで
有効な4文字のデータ種別IDを `RACEDIFN` のように連結した指定にも対応します。

旧仕様名（`DIFF` / `BLOD` / `SNAP` / `HOSE` / `TCOV` / `RCOV`）を受け付けない
理由と、`RACE` がその影響を受けないことは
[旧仕様 dataspec 名](record_contracts.md#dataspec-diff-blod-snap-hose-tcov-rcov)
にまとめています。

## JVRTOpen 速報レース・開催情報

| データ種別 | 内容 | 想定レコード種別 | 保存先テーブル | キー形式 | 対応状況 |
| --- | --- | --- | --- | --- | --- |
| `0B11` | 速報馬体重 | `WH` | `RT_WH` | `YYYYMMDD` | 対応済み |
| `0B12` | 成績確定後の速報レース・払戻 | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | 対応済み |
| `0B13` | 速報タイム型データマイニング予想 | `DM` | `RT_DM` | `YYYYMMDD` | 対応済み |
| `0B14` | 速報開催情報一括 | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `YYYYMMDD` | 対応済み |
| `0B15` | 出走馬名表以降の速報レース情報 | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | 対応済み |
| `0B16` | 速報開催情報指定 | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `JVWatchEvent` が返すイベントキー | パーサー・保存対応。日付指定の日次同期には含めない |
| `0B17` | 速報対戦型データマイニング予想 | `TM` | `RT_TM` | `YYYYMMDD` | 対応済み |
| `0B51` | 速報重勝式 WIN5 | `WF` | `RT_WF` | `YYYYMMDD` | 公式7,215-byte形式（対象5レース・有効票数5件・払戻243件）に対応。速報系のデータ区分は0/1/2/3/9で、蓄積系のみの7は受け付けません |

この表に関わる共通規則は [レコード別の公式契約と移行手順](record_contracts.md)
にあります。

- 速報保存を含む各入口が行う公式 `DataKubun` の検証（全 38 形式の base domain
  表と速報での差分）: [公式 DataKubun の検証](record_contracts.md#datakubun)
- `0B14` の日単位 snapshot 置換と `0B16` の関係:
  [0B14 の日単位 snapshot 置換と 0B16](record_contracts.md#0b14-snapshot-0b16)
- `HappyoTime`（`MMDDhhmm`）の保存形式:
  [HappyoTime の保存形式](record_contracts.md#happyotimemmddhhmm)

## JVRTOpen オッズ・票数

| データ種別 | 内容 | 想定レコード種別 | 通常速報モードの保存先 | 時系列モードの保存先 | キー形式 | JRA-VAN 側の保持 | 運用コマンド |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `0B20` | 速報票数 | `H1`, `H6` | `RT_H1`, `RT_H6` | 対象外 | `YYYYMMDDJJRR` | 約1週間 | パーサー・スキーマのみ。推奨 batch helper は未整備。`H1`（公式 28,955-byte、[レコード別契約](record_contracts.md#h11)）と `H6`（公式 102,890-byte、[レコード別契約](record_contracts.md#h663)）は人気順の取消マーカー保持・`DataKubun=0` の物理 exact erase まで固定済み|
| `0B30` | 全賭式の速報オッズ | `O1`〜`O6` | `RT_O1`〜`RT_O6` | `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime odds-sokuho-timeseries` |
| `0B31` | 単勝・複勝・枠連の速報オッズ | `O1` | `RT_O1` | `TS_SOKUHO_O1` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B31` |
| `0B32` | 馬連の速報オッズ | `O2` | `RT_O2` | `TS_SOKUHO_O2` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B32` |
| `0B33` | ワイドの速報オッズ | `O3` | `RT_O3` | `TS_SOKUHO_O3` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B33` |
| `0B34` | 馬単の速報オッズ | `O4` | `RT_O4` | `TS_SOKUHO_O4` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B34` |
| `0B35` | 三連複の速報オッズ | `O5` | `RT_O5` | `TS_SOKUHO_O5` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B35` |
| `0B36` | 三連単の速報オッズ | `O6` | `RT_O6` | `TS_SOKUHO_O6` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B36` |
| `0B41` | 単勝・複勝・枠連の公式時系列オッズ | `O1` | 非推奨 | `TS_O1` | `YYYYMMDDJJRR` | 約1年 | `jltsql realtime odds-timeseries` |
| `0B42` | 馬連の公式時系列オッズ | `O2` | 非推奨 | `TS_O2` | `YYYYMMDDJJRR` | 約1年 | `jltsql realtime odds-timeseries` |

運用上の重要事項:

- 公式に長期保持される時系列オッズは `0B41` と `0B42` です。
- ワイド、馬単、三連複、三連単の投資判断時点オッズは、開催週に
  `0B30` または `0B33`〜`0B36` を継続蓄積する必要があります。
- 公式長期時系列は `TS_O1` / `TS_O2`、開催週速報は
  `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` に保存し、`HassoTime` を保持します。
- `NL_O*` は確定オッズです。過去参照には使えますが、投資判断時点の
  オッズとして扱ってはいけません。

## パーサー・テーブル対応

jrvltsql は現在、以下 38 種類の JRA レコード種別に対してパーサーと
スキーマを持っています。

| レコード種別 | 保存先テーブル |
| --- | --- |
| `RA`, `SE`, `HR` | `NL_RA`, `NL_SE`, `NL_HR` |
| `UM`, `BR`, `BN` | `NL_UM`, `NL_BR`, `NL_BN` |
| `KS` | `NL_KS`（基本情報・初騎乗/初勝利・最近重賞3件）、`NL_KS_SEISEKI`（本年・前年・累計の3行） |
| `CH` | `NL_CH`（header・最近重賞3件）、`NL_CH_SEISEKI`（本年・前年・累計の3行） |
| `HN`, `SK`, `BT`, `RC` | `NL_HN`, `NL_SK`, `NL_BT`, `NL_RC` |
| `O1`, `O2`, `O3`, `O4`, `O5`, `O6` | `NL_O1`, `NL_O2`, `NL_O3`, `NL_O4`, `NL_O5`, `NL_O6` |
| `H1`, `H6` | `NL_H1`, `NL_H6` |
| `YS`, `TK`, `CS` | `NL_YS`、`NL_TK_RACE`＋`NL_TK`、`NL_CS`（CS標準名モードは`COURSE`） |
| `WE`, `WH`, `AV`, `JC`, `TC`, `CC` | `NL_WE`, `NL_WH`, `NL_AV`, `NL_JC`, `NL_TC`, `NL_CC` |
| `DM`, `TM`, `JG` | `NL_DM`, `NL_TM`, `NL_JG` |
| `WF` | `NL_WF`（native・1レコード1行）、標準名モードは `JYUSYOSIKI_HEAD`＋`JYUSYOSIKI`（払戻243行） |
| `HC`, `HS`, `HY`, `WC` | `NL_HC`, `NL_HS`, `NL_HY`, `NL_WC` |
| `CK` | `NL_CK`（互換親）、`NL_CK_CHAKU`（着回数278行）、`NL_CK_RUIKEI`（累計8行） |

対応済みの速報系レコードは `RT_*` にも保存できます。公式時系列オッズは
`TS_O1` / `TS_O2`、開催週速報オッズは `TS_SOKUHO_O1`〜`TS_SOKUHO_O6`
に保存します。

## レコード別の契約・移行手順（要点）

レコード種別ごとの公式レイアウト、identity（主キー）、保存先、`DataKubun`、
既存 DB からの移行手順の全文は
[レコード別の公式契約と移行手順](record_contracts.md) にあります。
ここでは要点だけを 1 行にまとめます。

共通規則（同ページ）:

| 項目 | 要点 | 詳細 |
| --- | --- | --- |
| 公式 `DataKubun` の検証 | 全 38 形式の base domain 表。値が無い・空欄・1文字でない・別名が食い違う・表に無いレコードは table routing、cache 書き込み、DB 更新より前に拒否。未指定値を `1` で補わない | [公式 DataKubun の検証](record_contracts.md#datakubun) |
| 通常インポートの transaction / rollback | streaming 処理。`auto_commit=True` は batch ごとに commit、`auto_commit=False` は呼び出し全体を all-or-nothing。transaction 状態を取得できない場合は接続を無効化して `TransactionRecoveryError` | [通常インポートの transaction / rollback 規約](record_contracts.md#transaction-rollback) |
| 速報 grouped batch と時系列 CLI | 成功時に caller 側 transaction を勝手に commit しない。DB 書込が 1 件でも失敗すれば grouped mutation 全体を rollback して `inserted=0`, `transaction_rolled_back=true` | [速報 grouped batch と時系列 CLI の transaction 境界](record_contracts.md#grouped-batch-cli-transaction) |
| `HappyoTime`（`MMDDhhmm`） | 年を含まない 8 バイト文字列として保存し、`TIME` / `TIMESTAMP` に変換しない。旧版の速報開催情報標準名テーブル・`ODDS_*_HEAD` の `HappyoTime` が `TIMESTAMP` なら起動時検証で停止 | [HappyoTime の保存形式](record_contracts.md#happyotimemmddhhmm) |
| `0B14` / `0B16` | `0B14` は指定日の完全 snapshot として、正常終了を確認した同一 transaction 内で `RT_WE`/`RT_AV`/`RT_JC`/`RT_TC`/`RT_CC` を置換。`0B16` はイベント指定更新で日単位置換とは別 | [0B14 の日単位 snapshot 置換と 0B16](record_contracts.md#0b14-snapshot-0b16) |
| 既存 DB からの移行 | バックアップ → 対象テーブルを現行 schema で再作成 → 各節の source から再取込 / 再取得。停止条件に当たる既存テーブルは自動修復せず停止 | [既存 DB からの移行の共通手順](record_contracts.md#db) |
| 旧仕様 dataspec 名 | `DIFF` / `BLOD` / `SNAP` / `HOSE` / `TCOV` / `RCOV` は受け付けず、`fetch` / `cache build` / `cache rebuild` は現行種別名を示して停止 | [旧仕様 dataspec 名](record_contracts.md#dataspec-diff-blod-snap-hose-tcov-rcov) |

レコード別（グループ分けは詳細ページと同じ）:

**[速報馬体重・開催情報系（WH / WE / AV / JC / TC / CC）](record_contracts.md#wh-we-av-jc-tc-cc)**

| レコード種別 | 要点 | 詳細 |
| --- | --- | --- |
| `WH` | 公式 format 101 の 847 バイト。`NL_WH` / `RT_WH` は 18 頭配列を馬ごとの行へ展開（主キー: レース識別子＋馬番）、標準名 `BATAIJYU` は 18 頭横持ちの 1 行。旧 `NL_WH` / `RT_WH`（主キー不一致で起動時に停止）と旧 `BATAIJYU` はオペレーター移行が必要 | [WH](record_contracts.md#wh) |
| `WE` | 42 バイト。`HappyoTime`, `HenkoID` を含む 7 項目キーで複数発表を別行保持。現行 `1`、旧 `0` は 2003-07-11 より前の `MakeDate` だけ | [WE](record_contracts.md#we) |
| `AV` | 78 バイト。7 項目キー（`HappyoTime` はキーでない）。現行 `1`=出走取消、`2`=競走除外。旧標準名 `AVOIDENCE` だけの構成は停止 | [AV](record_contracts.md#av) |
| `JC` | 161 バイト。`HappyoTime` を含む 8 項目キー。負担重量は native / 速報の `REAL` 列で `550` を `55.0`kg へ正規化 | [JC](record_contracts.md#jc) |
| `TC` | 45 バイト。6 項目キー。現行 `1` だけで、`0` を TC 単体の削除指示として扱わない。旧標準名 `COMMENT` しかない構成を `HASSOU_JIKOKU_CHANGE` へ自動転用しない | [TC](record_contracts.md#tc) |
| `CC` | 50 バイト。6 項目キーと必須 15 列。現行 `1` だけで、CC 単体の status 0 delete はない | [CC](record_contracts.md#cc) |

**[レース系（HR / SE / JG / WF）](record_contracts.md#hr-se-jg-wf)**

| レコード種別 | 要点 | 詳細 |
| --- | --- | --- |
| `HR` | 719 バイト。6 項目キー。`0` だけが物理削除、`9` は中止状態として保持。2004-08-14 より前の通常 record は位置 604〜717 を hex 保持 | [HR](record_contracts.md#hr) |
| `SE` | 現行 555 バイト（547 バイトは拒否）。8 項目キー。`0` は 8 項目一致の 1 頭だけ削除 | [SE](record_contracts.md#se) |
| `JG` | 80 バイト。受付順番を含む 8 列キーで再投票行を共存。`DataKubun` は 0/1 のみ | [JG](record_contracts.md#jg) |
| `WF` | 7,215 バイト。キーは開催年・開催月日。native は 1 行（`PayoutsJson`）、標準名は `JYUSYOSIKI_HEAD`＋子 `JYUSYOSIKI` 243 行。蓄積系 0/1/2/3/7/9、速報 0/1/2/3/9 | [WF](record_contracts.md#wf-win5) |

**[マスタ系（HN / SK / UM / BT / KS / CH / HS）](record_contracts.md#hn-sk-um-bt-ks-ch-hs)**

| レコード種別 | 要点 | 詳細 |
| --- | --- | --- |
| `HN` | 251 バイト（245 は拒否）。キー `HansyokuNum`。`0` は key だけの exact erase。`RT_HN` なし | [HN](record_contracts.md#hn) |
| `SK` | 208 バイト（178 は拒否）。キー `KettoNum`（10 桁）。14 個の 3 代血統番号を保持。`0` は key だけの exact erase。`RT_SK` なし | [SK](record_contracts.md#sk) |
| `UM` | 1609 バイト。キー `KettoNum`（10 桁）。旧標準名 `UMA`（`KettoNum` 列と主キーなし）は停止 | [UM](record_contracts.md#um) |
| `BT` | 6,889 バイト（6,887 は拒否）。キー `HansyokuNum`。標準名 `KEITO`、旧名 `BLOOD` は読み取り互換のみ | [BT](record_contracts.md#bt) |
| `KS` | 4173 バイト（旧 772 バイト復元データは受け付けない）。`NL_KS`＋`NL_KS_SEISEKI` / `KISYU`＋`KISYU_SEISEKI` へ原子的に保存 | [KS](record_contracts.md#ks) |
| `CH` | 3862 バイト（旧 592 バイト復元データは受け付けない）。`NL_CH`＋`NL_CH_SEISEKI` / `CHOKYO`＋`CHOKYO_SEISEKI` へ原子的に保存 | [CH](record_contracts.md#ch) |
| `HS` | 200 バイト（196 は拒否）。3 項目キー。`CurrentLayoutVersion=200`。`RT_HS` なし | [HS](record_contracts.md#hs) |

**[調教・コース系（HC / WC / CS）](record_contracts.md#hc-wc-cs)**

| レコード種別 | 要点 | 詳細 |
| --- | --- | --- |
| `HC` | 60 バイト。4 項目キー。`0` は key だけの exact erase。`RT_HC` なし | [HC](record_contracts.md#hc) |
| `WC` | 105 バイト。4 項目キー（`Course` はキーでない）。標準名 `WOOD` | [WC](record_contracts.md#wc) |
| `CS` | 6,829 バイト（`CourseEx` 6,800）。4 項目キー。6,829 バイト以外は拒否 | [CS](record_contracts.md#cs) |

**[出走時点情報・マイニング系（CK / DM / TM）](record_contracts.md#ck-dm-tm)**

| レコード種別 | 要点 | 詳細 |
| --- | --- | --- |
| `CK` | 6,870 バイト（6,864 は拒否）。親 `NL_CK`＋`NL_CK_CHAKU` 278 行＋`NL_CK_RUIKEI` 8 行。標準名モードは未実装で停止 | [CK](record_contracts.md#ck) |
| `DM` | 303 バイト・18 頭配列。native は馬ごとの行、標準名 `MINING` は 1 レース 1 行 | [DM](record_contracts.md#dm) |
| `TM` | 141 バイト・18 頭配列。native は馬ごとの行、標準名 `TAISENGATA_MINING` は 1 レース 1 行 | [TM](record_contracts.md#tm) |

## 対象外

| 項目 | 状況 | 理由 |
| --- | --- | --- |
| NAR / 地方競馬 | 非対応 | このリポジトリは JRA 専用です。地方競馬は別コレクタ / 別リポジトリの対象です。 |
| ワイド・馬単・三連複・三連単の長期公式時系列 | JRA-VAN の長期公式 spec では取得不可 | 開催週に `0B30` または `0B33`〜`0B36` で蓄積する必要があります。 |
| 投資判断スナップショット | 下流システム側の責務 | jrvltsql は raw / 確定 / 時系列データを保存します。投資判断時刻は保存済みデータから利用側が選びます。 |
| 旧仕様 dataspec 名 `DIFF` / `BLOD` / `SNAP` / `HOSE` / `TCOV` / `RCOV` | jrvltsql では受け付けません | 旧名は新名の別名ではなく、現行のパーサが解釈できない旧仕様のバイト列が返るためです。[旧仕様 dataspec 名](record_contracts.md#dataspec-diff-blod-snap-hose-tcov-rcov) を参照してください。 |
