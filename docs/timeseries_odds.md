# 時系列オッズ

jrvltsql では、JRA-VAN のリアルタイムオッズ系データを次の2系統として扱います。
オッズ以外を含む全データ種別の対応状況は
[対応データ種別一覧](data_support.md) を参照してください。

| 用途 | JVRTOpen spec | 保存先テーブル | 保持期間 | 備考 |
| --- | --- | --- | --- | --- |
| 公式長期時系列 | `0B41` | `TS_O1` | 約1年 | 単勝・複勝・枠連の時系列オッズです。 |
| 公式長期時系列 | `0B42` | `TS_O2` | 約1年 | 馬連の時系列オッズです。 |
| 開催週の速報蓄積 | `0B30` | `TS_O1`〜`TS_O6` | 約1週間 | 全賭式を1つのストリームから取得します。 |
| 開催週の速報蓄積 | `0B31`〜`0B36` | `TS_O1`〜`TS_O6` | 約1週間 | 賭式別の速報オッズストリームです。 |

## 目的別の使い分け

| やりたいこと | 使うコマンド | 取得できる範囲 |
| --- | --- | --- |
| SQLite に単複枠・馬連の過去時系列を入れる | `quickstart_timeseries.bat --db sqlite --from <FROM> --to <TO>`、`quickstart.bat` で時系列オッズ取得を選択、または `jltsql realtime odds-timeseries --db sqlite` | JRA-VAN 側に残っている約1年分の `TS_O1` / `TS_O2` |
| PostgreSQL に単複枠・馬連の過去時系列をまとめて入れる | `quickstart_timeseries.bat --db postgresql --from <FROM> --to <TO>`、`quickstart_postgres_timeseries.bat <FROM> <TO>`、または `jltsql realtime odds-timeseries --db postgresql` | JRA-VAN 側に残っている約1年分の `TS_O1` / `TS_O2` |
| 既存 DB に単複枠・馬連の時系列だけ追加する | `fetch_timeseries_postgres.bat <FROM> <TO>` | `TS_O1` / `TS_O2` のみ |
| 三連複・三連単を含む全賭式の締切前オッズを残す | `jltsql realtime odds-sokuho-timeseries --from <FROM> --to <TO> --db postgresql` | 開催週の `TS_O1`〜`TS_O6`。SQLite へ保存する場合は `--db sqlite` を指定します。 |
| 日次の通常データ更新だけ行う | `daily_sync.bat` | `RACE` などの通常データ。時系列オッズは対象外 |

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

## 重要な制約

- JRA-VAN はすべての賭式について長期保持の時系列オッズを提供しているわけではありません。
- ワイド、馬単、三連複、三連単の投資判断時点オッズは、開催週に
  `0B30` または `0B33`〜`0B36` を継続蓄積する必要があります。
- jrvltsql は raw の時系列オッズを保存します。投資判断時刻は、利用側が
  `HassoTime` から選択してください。
- `HassoTime` は発表時刻であり、必ずしも発走時刻と一致しません。
