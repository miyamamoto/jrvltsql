# JRVLTSQL Docs

JRVLTSQL は JRA-VAN DataLab のデータを SQLite / PostgreSQL に取り込む Windows 向けツールです。

この `docs/` は、現在の運用に必要な最小限の情報だけを残しています。詳細な運用手順は `README.md`、CLI の引数確認は `jltsql --help` と [CLI.md](CLI.md) を参照してください。

## 対象

- JRA / 中央競馬のみ
- Windows 10 / 11
- JRA-VAN DataLab + JV-Link
- SQLite / PostgreSQL

## 基本コマンド

```bat
quickstart.bat
quickstart_postgres_timeseries.bat 20250426 20260412
jltsql status
jltsql create-tables
jltsql create-indexes
jltsql fetch --from 20260101 --to 20260417 --spec RACE --option 1
jltsql realtime start --specs 0B12,0B15,0B30
jltsql realtime odds-timeseries --from 20250425 --to 20260425 --db postgresql
```

## 注意

- JRA-VAN の実データ取得は Windows + JV-Link 環境が必要です。
- `0B41/0B42` は公式1年保持の時系列オッズで、`TS_O1/TS_O2` に保存します。
- 0B30〜0B36 は速報オッズで、公式仕様上の保存期間は 1週間です。
- `quickstart.bat` は通常セットアップ完了後に PostgreSQL + 時系列オッズ投入を続けるか確認します。
- PostgreSQL へ `RACE` と `TS_O1/TS_O2` をまとめて投入する場合は `quickstart_postgres_timeseries.bat` を使います。
- `quickstart_postgres_timeseries.bat` の最後で、`daily_sync.bat` を Windows Task Scheduler に登録するか確認します。
- ワイド・馬単・三連複・三連単の締切前オッズは、開催週に `odds-sokuho-timeseries` で継続蓄積してください。
- 古い設計メモや未実装機能のドキュメントは削除しています。

## Documents

- [Architecture](architecture.md)
- [CLI](CLI.md)
- [PostgreSQL](postgresql.md)
- [Time-series odds](timeseries_odds.md)
- [Scripts](scripts.md)
