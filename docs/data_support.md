# 対応データ種別一覧

このページでは、jrvltsql が対応している JRA-VAN DataLab / JV-Link の
データ種別、レコード種別、保存先テーブル、運用コマンドをまとめます。

jrvltsql は JRA / 中央競馬専用です。NAR / 地方競馬はこのリポジトリの対象外です。

## 先に結論

| 知りたいこと | 結論 | 使うコマンド / 保存先 |
| --- | --- | --- |
| 出馬表、成績、払戻を保存できるか | できます。 | `quickstart.bat` または `quickstart_postgres_timeseries.bat`。主に `NL_RA`, `NL_SE`, `NL_HR` に保存します。 |
| 確定オッズを保存できるか | 全賭式でできます。 | `RACE` 取得で `NL_O1`〜`NL_O6` に保存します。ただし投資判断時点のオッズではありません。 |
| 過去1年分の時系列オッズをまとめて取れるか | 単複枠・馬連だけできます。 | `0B41` / `0B42` を `TS_O1` / `TS_O2` に保存します。 |
| 三連複・三連単の締切前オッズを長期評価できるか | 開催週から蓄積していればできます。 | `0B30` または `0B35` / `0B36` を `TS_O5` / `TS_O6` に保存します。JRA-VAN 側の保持は約1週間です。 |
| `daily_sync.bat` だけで全オッズが自動蓄積されるか | されません。 | `daily_sync.bat` は通常データ更新用です。時系列オッズは別コマンドで取得します。 |
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
| 今週データ | `JVOpen` | option `2` | `quickstart.bat`, `daily_sync.bat`, `jltsql fetch --option 2` | 今週開催分 | `TOKU`, `RACE`, `TCVN`, `RCVN` に対応 |
| セットアップデータ | `JVOpen` | option `3` / `4` | `quickstart.bat`, `jltsql fetch --option 3/4` | 初期構築用の過去範囲 | 下記の蓄積系 spec に対応 |
| 速報レース・開催情報 | `JVRTOpen` | `0B11`〜`0B17` | `jltsql realtime start --specs <SPEC>` | `YYYYMMDD` | 下記レコードに対応 |
| 速報オッズ・票数 | `JVRTOpen` | `0B20`, `0B30`〜`0B36` | `jltsql realtime timeseries --spec <SPEC>` | `YYYYMMDDJJRR` | 対応済み。JRA-VAN 側の保持は約1週間 |
| 公式時系列オッズ | `JVRTOpen` | `0B41`, `0B42` | `quickstart_postgres_timeseries.bat`, `fetch_timeseries_postgres.bat`, `jltsql realtime odds-timeseries` | `YYYYMMDDJJRR` | 対応済み。JRA-VAN 側の保持は約1年 |

## JVOpen 蓄積系データ

| データ種別 | 別名 | 内容 | 主なレコード種別 | 保存先テーブル | option 1 | option 2 | option 3/4 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `TOKU` | - | 特別登録馬 | `TK` | `NL_TK` | はい | はい | はい | standard / full quickstart に含めています。 |
| `RACE` | - | レース、出走馬、払戻、確定オッズ、票数、WIN5、除外情報 | `RA`, `SE`, `HR`, `H1`, `H6`, `O1`〜`O6`, `WF`, `JG` | `NL_RA`, `NL_SE`, `NL_HR`, `NL_H1`, `NL_H6`, `NL_O1`〜`NL_O6`, `NL_WF`, `NL_JG` | はい | はい | はい | 中核データです。`NL_O*` は確定オッズで、投資判断時点のオッズではありません。 |
| `DIFF` | `DIFN` | 蓄積系マスタ差分 | `UM`, `KS`, `CH`, `BR`, `BN`, `RC` | `NL_UM`, `NL_KS`, `NL_CH`, `NL_BR`, `NL_BN`, `NL_RC` | はい | いいえ | はい | 現在は `DIFN` も受け付けます。 |
| `BLOD` | `BLDN` | 血統情報 | `HN`, `SK`, `BT` | `NL_HN`, `NL_SK`, `NL_BT` | はい | いいえ | はい | 現在は `BLDN` も受け付けます。 |
| `MING` | - | データマイニング予想 | `DM`, `TM` | `NL_DM`, `NL_TM` | はい | いいえ | はい | full quickstart に含めています。 |
| `SLOP` | - | 坂路調教関連 | `HC` | `NL_HC` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `WOOD` | - | ウッドチップ調教関連 | `WC` | `NL_WC` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `YSCH` | - | 開催スケジュール | `YS` | `NL_YS` | はい | いいえ | はい | 開催カレンダー保守に使います。 |
| `HOSE` | `HOSN` | 競走馬市場取引価格 | `HS` | `NL_HS` | はい | いいえ | はい | 現在は `HOSN` も受け付けます。 |
| `HOYU` | - | 馬名の意味由来 | `HY` | `NL_HY` | はい | いいえ | はい | standard / full quickstart に含めています。 |
| `COMM` | - | 各種解説・コース情報 | `CS` | `NL_CS` | はい | いいえ | はい | full quickstart に含めています。 |
| `SNAP` | - | 出馬表スナップショット | 返却レコードは状況依存 | レコード種別に応じた既存 `NL_*` テーブル | はい | いいえ | はい | validation 上は対応。既定 quickstart では使っていません。 |
| `O1`〜`O6` | - | 賭式別の確定オッズ | `O1`〜`O6` | `NL_O1`〜`NL_O6` | はい | いいえ | はい | 通常は `RACE` 経由で取得します。投資判断時点のオッズは時系列コマンドを使います。 |
| `TCVN` | - | 特別登録馬情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。 |
| `RCVN` | - | レース情報補填 | 複数のマスタ・レース系レコード | レコード種別に応じた既存 `NL_*` テーブル | いいえ | はい | いいえ | 今週データ更新で使います。 |

## JVRTOpen 速報レース・開催情報

| データ種別 | 内容 | 想定レコード種別 | 保存先テーブル | キー形式 | 対応状況 |
| --- | --- | --- | --- | --- | --- |
| `0B11` | 速報馬体重 | `WH` | `RT_WH` | `YYYYMMDD` | 対応済み |
| `0B12` | 成績確定後の速報レース・払戻 | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | 対応済み |
| `0B13` | 速報タイム型データマイニング予想 | `DM` | `RT_DM` | `YYYYMMDD` | 対応済み |
| `0B14` | 速報開催情報一括 | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `YYYYMMDD` | 対応済み |
| `0B15` | 出走馬名表以降の速報レース情報 | `RA`, `SE`, `HR` | `RT_RA`, `RT_SE`, `RT_HR` | `YYYYMMDD` | 対応済み |
| `0B16` | 速報開催情報変更 | `WE`, `AV`, `JC`, `TC`, `CC` | `RT_WE`, `RT_AV`, `RT_JC`, `RT_TC`, `RT_CC` | `YYYYMMDD` | JV-Link から提供される場合に対応 |
| `0B17` | 速報対戦型データマイニング予想 | `TM` | `RT_TM` | `YYYYMMDD` | 対応済み |
| `0B51` | 速報重勝式 WIN5 | `WF` | `NL_WF` のパーサー・スキーマは存在。`RT_WF` 運用テーブルは未整備 | `YYYYMMDD` または WIN5 開催キー | パーサー・スキーマのみ |

## JVRTOpen オッズ・票数

| データ種別 | 内容 | 想定レコード種別 | 通常速報モードの保存先 | 時系列モードの保存先 | キー形式 | JRA-VAN 側の保持 | 運用コマンド |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `0B20` | 速報票数 | `H1`, `H6` | `RT_H1`, `RT_H6` | 対象外 | `YYYYMMDDJJRR` | 約1週間 | パーサー・スキーマ対応。推奨 batch helper は未整備 |
| `0B30` | 全賭式の速報オッズ | `O1`〜`O6` | `RT_O1`〜`RT_O6` | `TS_O1`〜`TS_O6` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime odds-sokuho-timeseries` |
| `0B31` | 単勝・複勝・枠連の速報オッズ | `O1` | `RT_O1` | `TS_O1` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B31` |
| `0B32` | 馬連の速報オッズ | `O2` | `RT_O2` | `TS_O2` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B32` |
| `0B33` | ワイドの速報オッズ | `O3` | `RT_O3` | `TS_O3` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B33` |
| `0B34` | 馬単の速報オッズ | `O4` | `RT_O4` | `TS_O4` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B34` |
| `0B35` | 三連複の速報オッズ | `O5` | `RT_O5` | `TS_O5` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B35` |
| `0B36` | 三連単の速報オッズ | `O6` | `RT_O6` | `TS_O6` | `YYYYMMDDJJRR` | 約1週間 | `jltsql realtime timeseries --spec 0B36` |
| `0B41` | 単勝・複勝・枠連の公式時系列オッズ | `O1` | 非推奨 | `TS_O1` | `YYYYMMDDJJRR` | 約1年 | `jltsql realtime odds-timeseries` |
| `0B42` | 馬連の公式時系列オッズ | `O2` | 非推奨 | `TS_O2` | `YYYYMMDDJJRR` | 約1年 | `jltsql realtime odds-timeseries` |

運用上の重要事項:

- 公式に長期保持される時系列オッズは `0B41` と `0B42` です。
- ワイド、馬単、三連複、三連単の投資判断時点オッズは、開催週に
  `0B30` または `0B33`〜`0B36` を継続蓄積する必要があります。
- 時系列オッズコマンドは、組み合わせ単位に展開した行を `TS_O*` に保存し、
  `HassoTime` を保持します。
- `NL_O*` は確定オッズです。過去参照には使えますが、投資判断時点の
  オッズとして扱ってはいけません。

## パーサー・テーブル対応

jrvltsql は現在、以下 38 種類の JRA レコード種別に対してパーサーと
スキーマを持っています。

| レコード種別 | 保存先テーブル |
| --- | --- |
| `RA`, `SE`, `HR` | `NL_RA`, `NL_SE`, `NL_HR` |
| `UM`, `KS`, `CH`, `BR`, `BN` | `NL_UM`, `NL_KS`, `NL_CH`, `NL_BR`, `NL_BN` |
| `HN`, `SK`, `BT`, `RC` | `NL_HN`, `NL_SK`, `NL_BT`, `NL_RC` |
| `O1`, `O2`, `O3`, `O4`, `O5`, `O6` | `NL_O1`, `NL_O2`, `NL_O3`, `NL_O4`, `NL_O5`, `NL_O6` |
| `H1`, `H6` | `NL_H1`, `NL_H6` |
| `YS`, `TK`, `CS` | `NL_YS`, `NL_TK`, `NL_CS` |
| `WE`, `WH`, `AV`, `JC`, `TC`, `CC` | `NL_WE`, `NL_WH`, `NL_AV`, `NL_JC`, `NL_TC`, `NL_CC` |
| `DM`, `TM`, `WF`, `JG` | `NL_DM`, `NL_TM`, `NL_WF`, `NL_JG` |
| `HC`, `HS`, `HY`, `WC`, `CK` | `NL_HC`, `NL_HS`, `NL_HY`, `NL_WC`, `NL_CK` |

対応済みの速報系レコードは `RT_*` にも保存できます。オッズ時系列は
`TS_O1`〜`TS_O6` に保存します。

## 対象外

| 項目 | 状況 | 理由 |
| --- | --- | --- |
| NAR / 地方競馬 | 非対応 | このリポジトリは JRA 専用です。地方競馬は別コレクタ / 別リポジトリの対象です。 |
| ワイド・馬単・三連複・三連単の長期公式時系列 | JRA-VAN の長期公式 spec では取得不可 | 開催週に `0B30` または `0B33`〜`0B36` で蓄積する必要があります。 |
| 投資判断スナップショット | 下流システム側の責務 | jrvltsql は raw / 確定 / 時系列データを保存します。投資判断時刻は保存済みデータから利用側が選びます。 |
