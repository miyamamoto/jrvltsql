# スクリプト一覧

現在の運用で使うスクリプトだけを記載します。古い設計や現在使っていない導線の
スクリプト一覧は削除しています。

| スクリプト | 最初に使う場面 | できること | できないこと |
| --- | --- | --- | --- |
| `quickstart.bat` | まず手元で SQLite DB を作るとき | 通常セットアップ、データ取得、DB 検証を行います。`--include-timeseries` で SQLite に公式 `TS_O1` / `TS_O2` も保存できます。 | PostgreSQL 専用セットアップは呼びません。 |
| `quickstart_postgres_timeseries.bat` | PostgreSQL 運用を始めるとき | `RACE` 系データと公式 `TS_O1` / `TS_O2` 時系列オッズを投入します。最後に日次タスク登録を確認します。 | 三連複・三連単など `TS_O3`〜`TS_O6` の長期蓄積は行いません。 |
| `fetch_timeseries_postgres.bat` | 既存 PostgreSQL に公式時系列だけ追加するとき | `0B41` / `0B42` から `TS_O1` / `TS_O2` を追加します。 | `RACE` 系データは追加しません。 |
| `daily_sync.bat` | 日次で通常データを更新するとき | 直近の通常データを更新します。既定は過去7日・未来3日です。 | 公式時系列オッズや全賭式速報オッズの蓄積は行いません。 |
| `install_tasks.ps1` | 日次同期を Windows タスク化するとき | `daily_sync.bat` の Windows タスク登録・更新を行います。 | オッズ取得処理そのものは実行しません。 |
| `scripts/quickstart.py` | バッチの内部処理 | セットアップ・更新処理の本体です。 | 通常は直接実行する必要はありません。 |
| `scripts/raceday_verify.py` | 開催日の健全性確認 | レース前後の DB 状態を検証します。 | データ取得の代替ではありません。 |
| `tools/export_timeseries_csv.py` | 保存済みオッズの確認 | `TS_O*` を確認用 CSV として出力します。 | JRA-VAN からの取得は行いません。 |

正確な CLI 引数は、実行環境で `--help` が使えるスクリプトでは `--help` を確認し、
それ以外は `jltsql --help` を参照してください。

`quickstart.bat` は SQLite 既定の通常セットアップです。PostgreSQL 運用を
始める場合は `quickstart_postgres_timeseries.bat` を直接実行してください。
PostgreSQL 時系列オッズ投入が終わると、`daily_sync.bat` を日次 Windows
タスクとして登録するか確認します。

三連複・三連単を含む全賭式の締切前オッズを残したい場合は、開催週に
`jltsql realtime odds-sokuho-timeseries` を別途実行してください。SQLite に
保存する場合は `--db sqlite --db-path data/keiba.db` を指定できます。
