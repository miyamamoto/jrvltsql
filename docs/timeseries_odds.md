# 時系列オッズ

jrvltsql では、JRA-VAN のリアルタイムオッズ系データを次の2系統として扱います。
オッズ以外を含む全データ種別の対応状況は
[対応データ種別一覧](data_support.md) を参照してください。

| 用途 | JVRTOpen spec | 保存先テーブル | 保持期間 | 備考 |
| --- | --- | --- | --- | --- |
| 公式長期時系列 | `0B41` | `TS_O1` | 約1年 | 単勝・複勝・枠連の時系列オッズです。 |
| 公式長期時系列 | `0B42` | `TS_O2` | 約1年 | 馬連の時系列オッズです。 |
| 開催週の速報蓄積 | `0B30` | `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` | 約1週間 | 全賭式を1つのストリームから取得します。 |
| 開催週の速報蓄積 | `0B31`〜`0B36` | `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` | 約1週間 | 賭式別の速報オッズストリームです。 |

## 目的別の使い分け

| やりたいこと | 使うコマンド | 取得できる範囲 |
| --- | --- | --- |
| SQLite に単複枠・馬連の過去時系列を入れる | `quickstart_timeseries.bat --db sqlite --from <FROM> --to <TO>`、`quickstart.bat` で時系列オッズ取得を選択、または `jltsql realtime odds-timeseries --db sqlite` | JRA-VAN 側に残っている約1年分の `TS_O1` / `TS_O2` |
| PostgreSQL に単複枠・馬連の過去時系列をまとめて入れる | `quickstart_timeseries.bat --db postgresql --from <FROM> --to <TO>`、`quickstart_postgres_timeseries.bat <FROM> <TO>`、または `jltsql realtime odds-timeseries --db postgresql` | JRA-VAN 側に残っている約1年分の `TS_O1` / `TS_O2` |
| 既存 DB に単複枠・馬連の時系列だけ追加する | `fetch_timeseries_postgres.bat <FROM> <TO>` | `TS_O1` / `TS_O2` のみ |
| 三連複・三連単を含む全賭式の締切前オッズを残す | `jltsql realtime odds-sokuho-timeseries --from <FROM> --to <TO> --db postgresql` | 開催週の `TS_SOKUHO_O1`〜`TS_SOKUHO_O6`。SQLite へ保存する場合は `--db sqlite` を指定します。 |
| 日次運用として通常データと直近オッズを更新する | `daily_sync.bat` | 直近通常データ、公式 `TS_O1` / `TS_O2`、開催週の速報系データ。通常データだけにする場合は `--no-timeseries --no-realtime` |

## コマンド

公式1年保持の時系列オッズ:

```bat
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db postgresql
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db sqlite --db-path data/keiba.db
```

開催週の全賭式速報オッズ蓄積:

```bat
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db sqlite --db-path data/keiba.db
```

PostgreSQL へ通常データと公式 `TS_O1/TS_O2` をまとめて投入:

```bat
quickstart_timeseries.bat --db postgresql --from 20250426 --to 20260412
quickstart_timeseries.bat --db sqlite --from 20250426 --to 20260412
```

`quickstart.bat` は PostgreSQL 専用セットアップを呼びません。SQLite に
公式時系列オッズを入れる場合は対話形式で時系列オッズ取得を選ぶか
`quickstart_timeseries.bat --db sqlite --from <FROM> --to <TO>` を使います。
PostgreSQL も同じ `quickstart_timeseries.bat --db postgresql --from <FROM> --to <TO>` です。
`quickstart_timeseries.bat` で `--from` / `--to` を省略した場合は、通常データも公式時系列オッズも今日から過去365日分を対象にします。
`quickstart.bat --yes --include-timeseries` は、通常データを `19860101` から今日まで、
公式時系列オッズを今日から過去12か月取得します。

`jltsql realtime odds-timeseries` / `odds-sokuho-timeseries` は、既存 DB の
レース情報を使って JVRTOpen のキーを作ります。先に通常データを投入してください。
公式長期時系列は `TS_O1` / `TS_O2`、開催週速報は
`TS_SOKUHO_O1`〜`TS_SOKUHO_O6` に分けて保存します。

当日の公式時系列をライブ判断用に小さく取得する場合は、`odds-timeseries` の発走時刻
ウィンドウを明示します。

```bat
jltsql realtime odds-timeseries --spec 0B41 --from 20260901 --to 20260901 --db postgresql --post-time-within-minutes 30 --post-time-not-past-minutes 2
```

`--post-time-within-minutes` は現在時刻（JST）から指定分以内に発走するキーを残し、
`--post-time-not-past-minutes` は発走後の許容分を超えたキーを除外します。未指定時は
従来どおり日付範囲の全キーが対象です。フィルターが有効なときは `NL_RA` / `RT_RA`
の日付だけで有効な bound の完全な範囲外と確定できるキーを先に除外します。残る候補
だけレース発走時刻を検証し、欠損、strict な4桁 `HHMM` として解釈不能、または同じ
JVRTOpen キー内で不一致なら、該当キーを表示して取得前に停止します。日付で除外済み
のキーの発走時刻は解釈しません。window summary は全キー、候補、保持数、未来・過去の
理由別除外数、日付だけで除外した数を個別に表示します。

公式時系列 `TS_O1` / `TS_O2`（0B41/0B42）は発表単位の主キーです。同じ発表行を再取得
した場合、価格などは最新の訂正値へ更新しますが、`CollectedAt` はその発表行を最初に
保有した時刻（最も早い非 NULL 値）を維持します。UTC オフセットが異なる ISO-8601 表現も
同一の時刻軸へ正規化して比較します。

開催週速報 `TS_SOKUHO_O1`〜`TS_SOKUHO_O6`（0B30〜0B36）は poll 単位の主キー
`(…, HassoTime, SourceSpec, CollectedAt)` で、取得ごとに 1 行を残します。0B30〜0B36 の
`HassoTime` は発表時刻として更新されず、朝の値のまま 1 日変わらないことがあるため
（オッズが 10 分ごとに動いていた日も、1 レース 1 値だった）、発表単位の主キーでは
本物の更新まで最初の取得に潰れます。判断時点のオッズは `CollectedAt <= 判断時刻` の
最新の行を使ってください。同じ poll を再取込した場合はその poll の行だけを更新します。

2.0〜2.3 は `TS_SOKUHO_O*` を発表単位の主キー（`CollectedAt` 無し）で作っていました。
その表は PostgreSQL・SQLite とも通常の起動・schema 準備・書き込みで fail closed します。
PostgreSQL は次の読み取り専用 dry-run command を表示します。runtime message の command
に `--apply` は含まれず、データを変更しません。SQLite は in-place 移行をサポートしないため
command を案内せず、backup と現行 schema での table 再構築を指示します。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --table TS_SOKUHO_O2
```

既定は dry run で、状態、現在の主キー、総行数、`CollectedAt` が NULL の行数を表示します。
dry run は読み取り専用 transaction であり、`ACCESS EXCLUSIVE` lock は取得しません。
全テーブルの検査は `--table` を省略し、複数 table の限定は `--table` を繰り返します。
search path 外の PostgreSQL schema は `--schema <SCHEMA>` を付けます。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --schema archive --table TS_SOKUHO_O2
```

適用時は先にすべての poll / writer を停止し、dry run の結果を確認して同じ command に
`--apply` を付けます。データを変更するのは `--apply` を付けた実行だけです。

```bat
jltsql db migrate-sokuho-capture-identity --db postgresql --schema archive --table TS_SOKUHO_O2 --apply
```

apply は指定 table 全体を1 transaction とし、全対象の lock を先に取得してから主キーに
`CollectedAt` を足します。行の削除・書き換えはしません。`CollectedAt` が NULL の行が
あれば何も変更せず拒否します。失敗すれば全変更を rollback します。2.0〜2.3 で潰れた
過去の poll は戻りません。1.x で作った表（主キー末尾が `CollectedAt`）は既に現行の主キー
で、移行は不要です。`TS_O1` / `TS_O2` はこの移行の対象外です。

## 重要な制約

- JRA-VAN はすべての賭式について長期保持の時系列オッズを提供しているわけではありません。
- ワイド、馬単、三連複、三連単の投資判断時点オッズは、開催週に
  `0B30` または `0B33`〜`0B36` を継続蓄積する必要があります。
- jrvltsql は raw の時系列オッズを保存します。投資判断時刻は、利用側が
  `TS_O1` / `TS_O2` では `HassoTime`、`TS_SOKUHO_O*` では `CollectedAt` から選択してください。
- 時系列オッズ行の `HassoTime` は発表時刻であり、発走時刻ではありません。発走時刻
  ウィンドウはレースレコード (`NL_RA` / `RT_RA`) 側の `HassoTime` を使います。
- 過去バージョンで `0B30`〜`0B36` を取得した DB では、速報行が `TS_O*` に
  残っている可能性があります。新規評価では `TS_SOKUHO_O*` を使い、必要に応じて
  公式 `TS_O1` / `TS_O2` を再取得してください。
