# JRVLTSQL ドキュメント

JRVLTSQL は JRA-VAN DataLab のデータを SQLite / PostgreSQL に取り込む Windows 向けツールです。

この `docs/` は、現在の運用に必要な最小限の情報だけを残しています。詳細な運用手順は `README.md`、CLI の引数確認は `jltsql --help` と [CLI.md](CLI.md) を参照してください。

## 最初に見る表

| 目的 | 実行するもの | 結果 |
| --- | --- | --- |
| まず SQLite で JRA データを作る | `quickstart.bat` | 主要な蓄積系データを SQLite に取り込みます。 |
| SQLite に公式時系列オッズも入れる | `quickstart.bat` で時系列オッズ取得を選択、または `quickstart.bat --yes --include-timeseries` | `TS_O1` / `TS_O2` を SQLite に保存します。 |
| PostgreSQL で運用を始める | `quickstart_postgres_timeseries.bat <FROM> <TO>` | `RACE` 系データと公式1年保持の `TS_O1` / `TS_O2` を PostgreSQL に投入します。 |
| 公式時系列オッズだけ追加する | `fetch_timeseries_postgres.bat <FROM> <TO>` | 既存 PostgreSQL に `TS_O1` / `TS_O2` を追加します。 |
| 三連複・三連単を含む全賭式の締切前オッズを蓄積する | `jltsql realtime odds-sokuho-timeseries --from <FROM> --to <TO> --db postgresql` | 開催週の速報オッズを `TS_O1`〜`TS_O6` に保存します。`--db sqlite` も指定できます。 |
| 日次同期を自動化する | `quickstart.bat` / `quickstart_postgres_timeseries.bat` の最後で登録、または `install_tasks.ps1` | SQLite / PostgreSQL 用の `daily_sync.bat` を Windows タスクスケジューラへ登録します。 |

## どこまでできるか

| データ | 対応状況 | 注意 |
| --- | --- | --- |
| JRA 出馬表・成績・払戻 | 対応済み | `NL_RA`, `NL_SE`, `NL_HR` などに保存します。 |
| 確定オッズ 全賭式 | 対応済み | `NL_O1`〜`NL_O6`。レース後の確定オッズです。 |
| 単複枠・馬連の公式時系列オッズ | 対応済み | `TS_O1` / `TS_O2`。JRA-VAN 側の保持は約1年です。 |
| ワイド・馬単・三連複・三連単の締切前オッズ | 開催週の蓄積で対応 | `TS_O3`〜`TS_O6`。JRA-VAN 側の保持は約1週間です。 |
| NAR / 地方競馬 | 非対応 | 別コレクタ / 別リポジトリの対象です。 |

## 対象

- JRA / 中央競馬のみ
- Windows 10 / 11
- JRA-VAN DataLab + JV-Link
- SQLite / PostgreSQL

対応済みの JVOpen / JVRTOpen データ種別、保存先テーブル、運用コマンドは
[対応データ種別一覧](data_support.md) に集約しています。

## 基本コマンド例

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

## 重要な注意

- JRA-VAN の実データ取得は Windows + JV-Link 環境が必要です。
- `0B41/0B42` は公式1年保持の時系列オッズで、`TS_O1/TS_O2` に保存します。
- 0B30〜0B36 は速報オッズで、公式仕様上の保存期間は 1週間です。
- `quickstart.bat` は通常セットアップ用です。PostgreSQL 専用セットアップは呼びません。
- SQLite に公式時系列オッズを入れる場合は、対話形式で時系列オッズ取得を選ぶか、非対話では `quickstart.bat --yes --include-timeseries` を使います。
- PostgreSQL へ `RACE` と `TS_O1/TS_O2` をまとめて投入する場合は `quickstart_postgres_timeseries.bat` を使います。
- `daily_sync.bat` は `--db sqlite` / `--db postgresql` の両方に対応します。
- `quickstart.bat` の最後では SQLite 用の日次同期タスク登録を確認します。
- `quickstart_postgres_timeseries.bat` の最後で、`daily_sync.bat` を Windows タスクスケジューラに登録するか確認します。
- `daily_sync.bat` は通常データの更新用です。公式時系列オッズや全賭式速報オッズの蓄積は別コマンドで行います。
- ワイド・馬単・三連複・三連単の締切前オッズは、開催週に `odds-sokuho-timeseries` で継続蓄積してください。
- 古い設計メモや未実装機能のドキュメントは削除しています。

## ドキュメント

- [アーキテクチャ](architecture.md)
- [CLI](CLI.md)
- [対応データ種別一覧](data_support.md)
- [PostgreSQL](postgresql.md)
- [時系列オッズ](timeseries_odds.md)
- [スクリプト一覧](scripts.md)
