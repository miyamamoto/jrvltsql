# 対応データ種別一覧

このページでは、jrvltsql が対応している JRA-VAN DataLab / JV-Link の
データ種別、レコード種別、保存先テーブル、運用コマンドをまとめます。

jrvltsql は JRA / 中央競馬専用です。NAR / 地方競馬はこのリポジトリの対象外です。

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
| `DIFN` | `DIFF` | 蓄積系マスタ差分 | `UM`, `KS`, `CH`, `BR`, `BN`, `RC` | `NL_UM`, `NL_KS`, `NL_KS_SEISEKI`, `NL_CH`, `NL_CH_SEISEKI`, `NL_BR`, `NL_BN`, `NL_RC` | はい | いいえ | はい | 旧名 `DIFF` は受け付けません（下記参照）。 |
| `BLDN` | `BLOD` | 血統情報 | `HN`, `SK`, `BT` | `NL_HN`, `NL_SK`, `NL_BT` | はい | いいえ | はい | 旧名 `BLOD` は受け付けません（下記参照）。 |
| `MING` | - | データマイニング予想 | `DM`, `TM` | `NL_DM`, `NL_TM` | はい | いいえ | はい | full quickstart に含めています。 |
| `SLOP` | - | 坂路調教関連 | `HC` | `NL_HC` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `WOOD` | - | ウッドチップ調教関連 | `WC` | `NL_WC`（native）、`WOOD`（標準名モード） | はい | いいえ | はい | 現行105バイトを全項目保存します。公式キーはトレセン区分・調教年月日・調教時刻・血統登録番号の4項目で、`0` は同じキーの削除です。standard / full quickstart に含めています。 |
| `YSCH` | - | 開催スケジュール | `YS` | `NL_YS` | はい | いいえ | はい | 開催カレンダー保守に使います。 |
| `HOSN` | `HOSE` | 競走馬市場取引価格 | `HS` | `NL_HS` | はい | いいえ | はい | 旧名 `HOSE` は受け付けません（下記参照）。 |
| `HOYU` | - | 馬名の意味由来 | `HY` | `NL_HY` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `COMM` | - | 各種解説・コース情報 | `CS` | `NL_CS` | はい | いいえ | はい | full quickstart に含めています。 |
| `SNPN` | `SNAP` | 出走時点情報 | `CK` | `NL_CK`、`NL_CK_CHAKU`、`NL_CK_RUIKEI` | はい | はい | はい | 現行6,870バイトをnative名モードで完全格納します。既定 quickstart では使っていません。旧名 `SNAP` は受け付けません（下記参照）。 |
| `TCVN` | `TCOV` | 特別登録馬情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。旧名 `TCOV` は受け付けません（下記参照）。 |
| `RCVN` | `RCOV` | レース情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。旧名 `RCOV` は受け付けません（下記参照）。 |

`O1`〜`O6` は `RACE` や速報系ストリームに含まれるレコード種別IDであり、
単独の `JVOpen` データ種別IDではありません。確定オッズは `RACE` を取得して
`NL_O1`〜`NL_O6` へ保存します。JV-Link APIと `jltsql fetch` は、同じoptionで
有効な4文字のデータ種別IDを `RACEDIFN` のように連結した指定にも対応します。

### jrvltsql で非対応の旧仕様 dataspec

`DIFF` / `BLOD` / `SNAP` / `HOSE` / `TCOV` / `RCOV` は jrvltsql では
受け付けません。`fetch` / `cache build` / `cache rebuild` は取り込みや既存
cache の変更に入る前に、対応する現行種別名を示して停止します。JRA-VAN の
仕様表には旧名も掲載されており、公式API全体で廃止されたという意味ではありません。

**旧名は新名の別名ではありません。** 2023-08 の JV-Data 仕様変更で桁数が変わって
おり（繁殖登録番号 8→10 / 生産者コード 6→8 / 生産者名 70→72）、旧名を要求すると
現行のパーサが解釈できない旧仕様のバイト列が返ります。桁がずれたまま取り込むと、
レコードの途中から後ろが全て壊れます。

`RACE` はこの仕様変更の対象外なので、これまでどおり使えます。

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
| `0B51` | 速報重勝式 WIN5 | `WF` | `RT_WF` | `YYYYMMDD` または WIN5 開催キー | 公式7,215-byte形式（対象5レース・有効票数5件・払戻243件）に対応。速報系のデータ区分は0/1/2/3/9で、蓄積系のみの7は受け付けません |

### WH テーブルの互換性に関する注意

`WH` は公式 format 101 の847バイト馬体重レコードです。1レコード内の
18頭配列を `NL_WH` / `RT_WH` の馬ごとの行へ展開し、レース識別子と馬番を
主キーにします。`HappyoTime` は訂正発表の時刻として保存しますが、同一レース・
同一馬の新しい発表は最新値として置き換わります。
JRA-VAN標準名モードの `BATAIJYU` は展開せず、18頭分を1行に保持する公式の
横持ち表現です。1つの公式WHレコードにつき、レース主キーの1行を保存します。

旧 jrvltsql が作成した `NL_WH` / `RT_WH` は、誤って天候変更の40バイト相当の
列と主キーを持っていました。この物理テーブルが存在する環境では、起動時の
schema migration は主キー不一致を検出して停止します。JRA-VAN標準名モードの
旧 `BATAIJYU` も主キーが無いため、同様にオペレーター移行が必要です。自動dropや
暗黙変換は行いません。DBをバックアップしたうえで、オペレーターが対象を
`NL_WH` / `RT_WH` / `BATAIJYU` のうち実在する旧テーブルだけに限定して削除し、
`jltsql create-tables --db <sqlite|postgresql>` または標準名テーブルの初期化手順で
再作成してください。`RT_WH` はその後 `jltsql realtime start --specs 0B11` で、
JRA-VANの保持期間内に再取得します。旧 `NL_WH` / `RT_WH` の行は公式WHではない
ため、馬体重履歴として移植しないでください。

### 発表月日時分の保存形式と旧標準名テーブル

`WH`, `WE`, `AV`, `JC`, `TC`, `CC` と `O1`〜`O6` の公式
`HappyoTime` は、年を含まない8バイトの `MMDDhhmm` です。SQLの `TIME` や
`TIMESTAMP` には変換せず、先頭ゼロを含む文字列として保存します。速報開催情報の
JRA-VAN標準名は `TENKO_BABA`, `TORIKESI_JYOGAI`, `KISYU_CHANGE`,
`HASSOU_JIKOKU_CHANGE`, `COURSE_CHANGE` です。旧来の英語別名は読み取り側の
互換性のため残しますが、新しい標準名インポート先には使いません。

旧版が作成したこれらの標準名テーブル、および `ODDS_*_HEAD` テーブルで
`HappyoTime` が `TIMESTAMP` の場合、起動時検証は型不一致として停止します。
月日を欠いた旧値から公式8桁値を復元できないため、自動 `ALTER` や暗黙変換は
行いません。DBをバックアップし、対象テーブルだけを退避または削除して現行の
標準名スキーマ（`VARCHAR(8)`）で再作成した後、JRA-VANの保持期間内のデータを
再取得してください。既存値を時刻部分だけで移植しないでください。

## JVRTOpen オッズ・票数

| データ種別 | 内容 | 想定レコード種別 | 通常速報モードの保存先 | 時系列モードの保存先 | キー形式 | JRA-VAN 側の保持 | 運用コマンド |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `0B20` | 速報票数 | `H1`, `H6` | `RT_H1`, `RT_H6` | 対象外 | `YYYYMMDDJJRR` | 約1週間 | パーサー・スキーマ対応。推奨 batch helper は未整備 |
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
| `YS`, `TK`, `CS` | `NL_YS`、`NL_TK_RACE`＋`NL_TK`、`NL_CS` |
| `WE`, `WH`, `AV`, `JC`, `TC`, `CC` | `NL_WE`, `NL_WH`, `NL_AV`, `NL_JC`, `NL_TC`, `NL_CC` |
| `DM`, `TM`, `JG` | `NL_DM`, `NL_TM`, `NL_JG` |
| `WF` | `NL_WF`（native・1レコード1行）、標準名モードは `JYUSYOSIKI_HEAD`＋`JYUSYOSIKI`（払戻243行） |
| `HC`, `HS`, `HY`, `WC` | `NL_HC`, `NL_HS`, `NL_HY`, `NL_WC` |
| `CK` | `NL_CK`（互換親）、`NL_CK_CHAKU`（着回数278行）、`NL_CK_RUIKEI`（累計8行） |

対応済みの速報系レコードは `RT_*` にも保存できます。公式時系列オッズは
`TS_O1` / `TS_O2`、開催週速報オッズは `TS_SOKUHO_O1`〜`TS_SOKUHO_O6`
に保存します。

`WC`はJV-Data 4.9.0.1とSDK 5.0.0の105バイト配置を使用し、10ハロンから
1ハロンまでの合計・ラップを保存します。4.7.0.1で追記されたのは美浦・栗東の
提供開始時期と計測距離の説明であり、別の物理レイアウトではありません。
`Course`（コース）や馬場周りは公式キーではありません。旧版jrvltsqlが作成した
`Course`入り・トレセン区分なしの主キーは自動修復せず、取込前に拒否します。
`WOOD`はデータ種別名とSDK構造に対応させたjrvltsqlの標準名モード上の
canonical table名であり、提供元がSQL DDLやテーブル名を規定しているという意味ではありません。
4項目キーは[JRA-VANソフトサポートの回答](https://developer.jra-van.jp/t/topic/99)とも一致します。
タイムが全桁9のデータは規定内として配信されるため、欠損へ置換せず数値sentinelとして保存します
（[スタッフ回答](https://developer.jra-van.jp/t/topic/367)）。

`KS`は公式4173バイトを1物理レコードとして扱い、nativeでは`NL_KS`と
`NL_KS_SEISEKI`、JRA-VAN標準名モードでは`KISYU`と`KISYU_SEISEKI`へ
原子的に保存します。旧772バイトの復元データは取得元レコードとして受け付けません。
既存の標準名テーブルが主キー契約を満たさない場合は行を変更せず停止します。
現行schemaで再作成した後、`DIFN`のoption 3/4で全件を再取得してください。

`CH`は公式3862バイトを1物理レコードとして扱い、nativeでは`NL_CH`と
`NL_CH_SEISEKI`、JRA-VAN標準名モードでは`CHOKYO`と`CHOKYO_SEISEKI`へ
原子的に保存します。旧592バイトの復元データは取得元レコードとして受け付けません。
旧標準名テーブルは主キーと文字列日付の契約を満たさないため、自動変換せず停止します。
バックアップ後に両テーブルを現行schemaで再作成し、保持期間内の現行データを
再取得してください。

`BT`は現行公式6,889バイトを扱い、10文字の`HansyokuNum`、`KeitoId`、
`KeitoName`、最大6,800バイトの`KeitoEx`を保存します。native名モードの保存先は
`NL_BT`、JRA-VAN標準名モードの保存先は公式名`KEITO`で、どちらも
`HansyokuNum`を主キーに更新し、`DataKubun=0`では同じキーの行を物理削除します。
旧名`BLOOD`は読み取り側の名前解決互換として残しますが、新規import先には使いません。
標準名モードの開始時は既存の標準名テーブルを変更前に一括検証するため、再構築が必要な
旧`KEITO`またはlegacy-only tableが残るDBでは、BT以外のimportもschema変更前に停止します。

旧6,887バイトBTは8文字の繁殖登録番号を前提とするため、現行layoutとして受け付けません。
主キーのない部分的な`KEITO`、10文字未満のkey列、6,800文字未満の説明列、または
旧名`BLOOD`しか存在しない標準名DBは、欠落値を安全に復元できないため行やschemaを
自動変更せず停止します。DBをバックアップして対象テーブルを現行schemaで再作成し、
`BLDN`のoption 3/4で現行データを再取得してください。

`JG`は現行公式80バイト（Ver.4.1.0で追加、Ver.4.1.1は血統登録番号の初期値を追記した
のみでlayout不変）を扱い、`DataKubun`は公式どおり0/1のみ、出走区分・除外状態区分は
公式コードのみを受け付けます。native名モードの保存先は`NL_JG`（互換名`Num`、
`SyussoKubun`、`JyogaiStateKubun`）、JRA-VAN標準名モードの保存先はSDK構造体
`JV_JG_JOGAIBA`から採ったproject canonical名`JOGAIBA`（`ShutsubaTohyoJun`、
`ShussoKubun`、`JogaiJotaiKubun`）です。どちらも公式8列キー（開催キー6列＋
`KettoNum`＋出馬投票受付順番）で更新するため、同一馬の再投票行は共存し、
`DataKubun=0`では同じ8列キーの行だけを提供順に物理削除します。
旧名`WEIGHT_CHANGE`は読み取り側の名前解決互換として残しますが、新規import先には
使わず、`WEIGHT_CHANGE`しか存在しない標準名DBは行を変更せず停止します。
旧7列キー（受付順番を含まない）の`NL_JG`/`JOGAIBA`や列の欠けた`JOGAIBA`は、
再投票行を安全に復元できないため自動`ALTER`せず停止します。DBをバックアップして
対象テーブルを現行schemaで再作成し、`RACE`で保持期間内の現行データを再取得してください。

`WF`（重勝式・WIN5）は現行公式7,215バイト（JV-Data 4.8.0.2 / 4.9.0.1、SDK 5.0.0
`JV_WF_INFO`）を1物理レコードとして扱い、公式キーは開催年・開催月日の2列です。
データ区分は蓄積系が0/1/2/3/7/9、速報系（`0B51`）が0/1/2/3/9で、それ以外は取り込み前に
拒否します。対象5レースの競馬場・回・日・レース番号、発売票数、有効票数5件、返還・不成立・
的中無フラグ、キャリーオーバー金額初期・残高、払戻情報243枠を全て保存します。
対象レースの競馬場は同版の公式コード表2001に掲載された値から初期値・未使用値を除いたコードを検証し、
廃止済みの競馬場・国を含むため現在使用中の会場一覧とは扱いません。初期値`00`、
使用しないと明記されたコード、未掲載コード、小文字表記は受け付けません。公式コードが追加された
場合は、固定した仕様manifestと検証集合を同じ変更で更新する必要があります。
値の有無は公式の状態別規定に従い、`1`（詳細発表時）は発売票数・有効票数・残高・払戻が初期値、
`2`/`9`はこれらの値が設定される場合とされない場合が混在し、`3`/`7`では必須として検証します。
各フラグは未設定時の公式初期値も`0`なので、非削除レコードでは常に`0`か`1`です。予備領域も
公式初期値`00`/`000000`だけを受け付けます。払戻枠は空欄か
組番・払戻金・的中票数の揃った組だけを受け付けます。キャリーオーバー金額初期はVer.4.2.0
（2012年2月21日）以降に作成されたデータでは全状態で必須です。それ以前は`1`で空欄のみ、
`2`/`9`で空欄または数値を許容します。
払戻が確定する`3`/`7`で的中無フラグが`1`の場合は、組番を保持したうえで払戻金
`000000000`・的中票数`0000000000`の公式表現だけを受け付けます。中止状態`9`は下記の
中止用払戻が優先されるため、この的中無規則を一律には適用しません。
Ver.4.1.1とVer.4.2.0はいずれも項目名・初期値・設定有無の変更であり、別の物理レイアウトでは
ありません。旧jrvltsqlの169バイト復元データは取得元レコードとして受け付けません。

native名モードの保存先は`NL_WF`/`RT_WF`（1レコード1行、払戻243枠は`PayoutsJson`）、
JRA-VAN標準名モードの保存先はproject canonical名`JYUSYOSIKI_HEAD`（ヘッダー、
主キー開催年・開催月日）と子テーブル`JYUSYOSIKI`（払戻243枠を`Num`=1〜243の行として
空欄枠も保存、主キー開催年・開催月日・`Num`、親への複合外部キー`ON DELETE CASCADE`）です。
1物理レコードにつきヘッダー1行と子243行を提供順にtransactionで置き換え、`DataKubun=0`は
同じキーの親子を物理削除し、`9`（中止）は払戻が設定される場合に公式の中止用払戻組
（組番`0000000000`・払戻金`000000100`・的中票数`0000000000`）ごと状態として保持します。
`DataKubun=0`ではheaderと公式キーだけを解釈し、仕様が定義しないbody値やbody aliasの差を
削除拒否の根拠にしません。native・標準名・速報の各WF書込はbatch途中のDB例外で全体を
rollbackし、行単位fallbackによる部分成功や、rollbackされた操作を成功件数へ残すことを許しません。
`inserted`は最終行数ではなく、提供順に正常適用された操作数です。
速報の通常grouped batchも、SQLite/psycopgが暗黙に開始したcaller側transactionを所有済みとして
扱い、成功時に勝手にcommitしません。DB書込が1件でも失敗した場合は同じcallのgrouped mutationを
全てrollbackして`inserted=0`と`transaction_rolled_back=true`を返し、後続rollbackで消える行を
部分成功として数えません。削除を含む提供順処理も同じatomic境界を使います。false結果を受け取った
callerは、validation-only拒否かDB rollback済みかにかかわらず、その取込単位を必ず中断してください。
psycopgではSELECTだけでもtransactionが開始されるため、独立した取込単位へ移るcallerは明示的に
commitまたはrollbackして境界を閉じてください。transaction状態を判定できない場合は書込前に失敗します。
時系列取得CLIは保存先table作成を先にcommitしてbatchごとの境界を分離し、1batchでも拒否された場合は
`[OK]`を出さず非0終了します。
`WIN5`は読み取り側の名前解決互換用のaliasであり、新規import先には使いません。
主キーや`HatubaiHyosu`のない旧`JYUSYOSIKI_HEAD`、`Num`・主キー・外部キーのない旧`JYUSYOSIKI`、
親子の片方だけが存在するDB、`WIN5`しか存在しない標準名DBは自動`ALTER`せず、
行やschemaを変更する前に停止します。DBをバックアップして両テーブルを現行schema
（親を先に作成）で再作成し、`RACE`で保持期間内の現行データを再取得してください。
WF保存先は全列の型・文字容量と主キーを取込前に検証します。PostgreSQLの主キーは
`ON CONFLICT`で使用できるvalid・ready・即時・非deferrableでなければならず、公式キー以外の
追加`UNIQUE`/排他制約も、置換時に別開催を消し得るため拒否します。検索用の非一意indexは
保持できます。

`CK`は現行公式6,870バイトの1,729 scalar leafを扱います。PostgreSQLの
1テーブル列数上限を超えないよう、native名モードでは互換親`NL_CK`と
`NL_CK_CHAKU` 278行、`NL_CK_RUIKEI` 8行を1物理レコード単位のtransactionで
更新します。`DataKubun=0`は7列の公式キーで親子を削除します。旧6,864バイトは
現行offsetと混同せず拒否します。

既存`NL_CK`には完全展開していない行があるため、追加される
`CKStorageVersion`が`NULL`の行を完全格納済みと扱ってはいけません。現行`SNPN`を
再取得して`CKStorageVersion=1`、子行数278/8をキーごとに確認してください。
CKのJRA-VAN標準名モードはまだ実装しておらず、`CHOKYO_DETAIL`へ誤って部分保存せず
明示的に停止します。

`DM`は公式303バイトの18頭配列を扱います。native名モードでは`NL_DM`/`RT_DM`へ
馬ごとの行として保存し、JRA-VAN標準名モードでは`MINING`へ1レース1行のwide形式で
保存します。`DMTime`は公式SDKと同じ5桁文字列（9分99秒99）を保持します。
旧48バイト復元データ、旧標準名`DATA_MASTER`、主キーのない`MINING`、数値型の
`DMTime1`〜`DMTime18`は安全に自動変換できないため、取り込みを停止して再構築を求めます。

`TM`は公式141バイトの18頭配列を扱います。native名モードでは`NL_TM`/`RT_TM`へ
馬ごとの行として保存し、JRA-VAN標準名モードでは`TAISENGATA_MINING`へ
1レース1行のwide形式で保存します。`TMScore`は公式SDKと同じ4桁文字列を保持し、
右端1桁が小数第一位です。旧39バイト復元データ、旧標準名`TIME_MASTER`、主キーのない
`TAISENGATA_MINING`、`TMScore`が整数型の旧nativeテーブルは安全に自動変換できないため、
取り込みを停止して再構築を求めます。
DM/TMのnative速報スナップショット置換は、既存レース行の削除後に書込が失敗した場合、caller所有を
含むactive transaction全体をrollbackします。rollback不能時は接続を無効化し、それも失敗した場合は
batch・optimized・single・速報の全入口から`TransactionRecoveryError`を送出し、通常の失敗結果へ
変換しません。

## 対象外

| 項目 | 状況 | 理由 |
| --- | --- | --- |
| NAR / 地方競馬 | 非対応 | このリポジトリは JRA 専用です。地方競馬は別コレクタ / 別リポジトリの対象です。 |
| ワイド・馬単・三連複・三連単の長期公式時系列 | JRA-VAN の長期公式 spec では取得不可 | 開催週に `0B30` または `0B33`〜`0B36` で蓄積する必要があります。 |
| 投資判断スナップショット | 下流システム側の責務 | jrvltsql は raw / 確定 / 時系列データを保存します。投資判断時刻は保存済みデータから利用側が選びます。 |
