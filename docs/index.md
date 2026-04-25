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
quickstart_kps_postgres.bat 20250426 20260412
jltsql status
jltsql create-tables
jltsql create-indexes
jltsql fetch --from 20260101 --to 20260417 --spec RACE --option 1
jltsql realtime start --specs 0B12,0B15,0B30
jltsql realtime odds-timeseries --from 20250425 --to 20260425 --db postgresql
```

## 注意

- JRA-VAN の実データ取得は Windows + JV-Link 環境が必要です。
- 時系列オッズは JRA-VAN 公式では過去1年分が提供範囲です。
- KPS の締切オッズ予測では `quickstart_kps_postgres.bat` または `fetch_timeseries_postgres.bat` で PostgreSQL に `TS_O1〜TS_O6` を投入します。
- 古い設計メモや未実装機能のドキュメントは削除しています。
