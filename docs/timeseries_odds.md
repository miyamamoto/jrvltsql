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

## コマンド

公式1年保持の時系列オッズ:

```bat
jltsql realtime odds-timeseries --from 20250426 --to 20260412 --db postgresql
```

開催週の全賭式速報オッズ蓄積:

```bat
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
```

PostgreSQL へ RACE と公式 `TS_O1/TS_O2` をまとめて投入:

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

`quickstart.bat` からも、通常セットアップ完了後に PostgreSQL 時系列オッズ投入を
続けて実行できます。`quickstart_postgres_timeseries.bat` の最後では、
`daily_sync.bat` を Windows タスクスケジューラへ登録するか確認します。

## 重要な制約

- JRA-VAN はすべての賭式について長期保持の時系列オッズを提供しているわけではありません。
- ワイド、馬単、三連複、三連単の投資判断時点オッズは、開催週に
  `0B30` または `0B33`〜`0B36` を継続蓄積する必要があります。
- jrvltsql は raw の時系列オッズを保存します。投資判断時刻は、利用側が
  `HassoTime` から選択してください。
- `HassoTime` は発表時刻であり、必ずしも発走時刻と一致しません。
