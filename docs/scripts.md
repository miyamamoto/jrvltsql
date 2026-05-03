# スクリプト一覧

現在の運用で使うスクリプトだけを記載します。古い設計や現在使っていない導線の
スクリプト一覧は削除しています。

| スクリプト | 最初に使う場面 | できること | できないこと |
| --- | --- | --- | --- |
| `quickstart.bat` | まず手元で SQLite DB を作るとき | 通常セットアップとデータ取得を行います。対話形式で時系列オッズ取得を選ぶか、`--yes --include-timeseries` で SQLite に公式 `TS_O1` / `TS_O2` も保存できます。最後に SQLite 用の日次同期タスク登録を確認します。 | PostgreSQL 専用セットアップは呼びません。`--yes` 実行時は日次同期タスク登録確認もスキップします。 |
| `quickstart_timeseries.bat` | SQLite / PostgreSQL で範囲指定して公式時系列オッズも入れるとき | `--db sqlite` / `--db postgresql` を同じ形で指定し、指定範囲の通常データと公式 `TS_O1` / `TS_O2` を投入します。最後に指定 DB 用の日次タスク登録を確認します。 | 三連複・三連単など `TS_O3`〜`TS_O6` の長期蓄積は行いません。 |
| `quickstart_postgres_timeseries.bat` | PostgreSQL 専用バッチを直接使うとき | 指定範囲の通常データと公式 `TS_O1` / `TS_O2` 時系列オッズを投入します。最後に日次タスク登録を確認します。 | SQLite には使いません。新規手順では `quickstart_timeseries.bat --db postgresql` を推奨します。 |
| `fetch_timeseries_postgres.bat` | 既存 PostgreSQL に公式時系列だけ追加するとき | `0B41` / `0B42` から `TS_O1` / `TS_O2` を追加します。 | `RACE` 系データは追加しません。 |
| `daily_sync.bat` | 日次で通常データを更新するとき | 直近の通常データを更新します。`--db sqlite` / `--db postgresql` に対応します。既定は PostgreSQL、過去7日・未来3日です。 | 公式時系列オッズや全賭式速報オッズの蓄積は行いません。SQLite では `--db sqlite` を指定してください。 |
| `install_tasks.ps1` | 日次同期を Windows タスク化するとき | `daily_sync.bat` の Windows タスク登録・更新を行います。`-DbType sqlite` / `-DbType postgresql` に対応します。 | オッズ取得処理そのものは実行しません。 |
| `scripts/quickstart.py` | バッチの内部処理 | セットアップ・更新処理の本体です。 | 通常は直接実行する必要はありません。 |
| `scripts/raceday_verify.py` | 開催日の健全性確認 | レース前後の DB 状態を検証します。 | データ取得の代替ではありません。 |
| `tools/export_timeseries_csv.py` | 保存済みオッズの確認 | `TS_O*` を確認用 CSV として出力します。 | JRA-VAN からの取得は行いません。 |

正確な CLI 引数は、実行環境で `--help` が使えるスクリプトでは `--help` を確認し、
それ以外は `jltsql --help` を参照してください。

`quickstart.bat` は SQLite 既定の通常セットアップです。最後に SQLite 用の
`daily_sync.bat` を日次 Windows タスクとして登録するか確認します。
範囲指定つきで公式時系列オッズも入れる場合は、SQLite / PostgreSQL とも
`quickstart_timeseries.bat --db <sqlite|postgresql> --from <FROM> --to <TO>` を使ってください。
`--from` / `--to` 省略時は、通常データも公式時系列オッズも今日から過去365日分を対象にします。
この batch も最後に `daily_sync.bat` の日次 Windows タスク登録を確認します。
PostgreSQL だけを対象にした `quickstart_postgres_timeseries.bat` もありますが、新規手順では共通コマンドを使ってください。
PostgreSQL 時系列オッズ投入が終わると、`daily_sync.bat` を日次 Windows
タスクとして登録するか確認します。

三連複・三連単を含む全賭式の締切前オッズを残したい場合は、開催週に
`jltsql realtime odds-sokuho-timeseries` を別途実行してください。SQLite に
保存する場合は `--db sqlite --db-path data/keiba.db` を指定できます。
