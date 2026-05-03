# スクリプト一覧

現在の運用で使うスクリプトだけを記載します。古い設計や現在使っていない導線の
スクリプト一覧は削除しています。

| スクリプト | 用途 |
| --- | --- |
| `quickstart.bat` | Windows 向けの通常 quickstart です。既定は SQLite です。 |
| `quickstart_postgres_timeseries.bat` | PostgreSQL へ RACE と公式 `TS_O1/TS_O2` 時系列オッズを投入します。 |
| `fetch_timeseries_postgres.bat` | 既存 PostgreSQL 環境へ公式 `TS_O1/TS_O2` 時系列オッズだけを追加します。 |
| `daily_sync.bat` | Windows タスクスケジューラから実行する日次同期です。 |
| `install_tasks.ps1` | `daily_sync.bat` の Windows タスク登録・更新を行います。 |
| `scripts/quickstart.py` | バッチファイルから呼ばれる Python 側のセットアップ・更新処理です。 |
| `scripts/raceday_verify.py` | レース開催日のデータ健全性チェックです。 |
| `tools/export_timeseries_csv.py` | 保存済み時系列オッズを確認用 CSV として出力します。 |

正確な CLI 引数は、実行環境で `--help` が使えるスクリプトでは `--help` を確認し、
それ以外は `jltsql --help` を参照してください。

`quickstart.bat` は通常セットアップ完了後に
`quickstart_postgres_timeseries.bat` を続けて実行するか確認します。
PostgreSQL 時系列オッズ投入が終わると、`daily_sync.bat` を日次 Windows
タスクとして登録するか確認します。
