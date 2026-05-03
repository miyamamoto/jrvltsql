# PostgreSQL

jrvltsql は SQLite だけでなく PostgreSQL へ直接保存できます。複数マシンで
コレクタのデータを共有する場合や、下流の分析基盤へ渡す場合は PostgreSQL
運用を推奨します。

## PostgreSQL で何が入るか

| 操作 | 入るデータ | 入らないデータ |
| --- | --- | --- |
| `quickstart_postgres_timeseries.bat <FROM> <TO>` | `RACE` 系データ、公式1年保持の `TS_O1` / `TS_O2` | `TS_O3`〜`TS_O6` の長期蓄積 |
| `fetch_timeseries_postgres.bat <FROM> <TO>` | 公式1年保持の `TS_O1` / `TS_O2` | `RACE` 系データ、`TS_O3`〜`TS_O6` |
| `daily_sync.bat --db postgresql` | 直近の通常データ | 時系列オッズ |
| `jltsql realtime odds-sokuho-timeseries --db postgresql` | 開催週の `TS_O1`〜`TS_O6` | JRA-VAN 側の保持期間を過ぎた速報オッズ |

## 必要な環境変数

```bat
set POSTGRES_HOST=<host>
set POSTGRES_PORT=5432
set POSTGRES_DATABASE=<database>
set POSTGRES_USER=<user>
set POSTGRES_PASSWORD=<password>
```

一部の script では `POSTGRES_DATABASE` の別名として `POSTGRES_DB` も使えます。

## クイックスタート

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

このコマンドは、RACE データと公式1年保持の `TS_O1/TS_O2` 時系列オッズを
PostgreSQL に投入します。通常の `quickstart.bat` からは呼びません。
SQLite と PostgreSQL の導線を分けるため、PostgreSQL 運用を始める場合は
この batch を直接実行してください。

`quickstart_postgres_timeseries.bat` の最後では、`daily_sync.bat` を
Windows タスクスケジューラへ登録するか確認します。PostgreSQL 接続情報を
現在の CMD セッションだけに設定している場合、タスク実行時には見えません。
登録時の確認で現在の `POSTGRES_*` を Windows ユーザー環境変数へ保存するか、
事前に永続的な環境変数として設定してください。

## 日次同期

```bat
daily_sync.bat --db postgresql --days-back 7 --days-forward 3
```

このコマンドは、直近のレース番組、結果、関連する通常データを更新します。
SQLite で同じ処理をする場合は `daily_sync.bat --db sqlite` を使います。

手動で Windows タスクを登録・更新する場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType postgresql -Time 06:30
```

## SQLite フォールバック

`config/config.yaml.example` の既定は SQLite です。PostgreSQL を使えない
ローカル検証や単一ユーザー運用では SQLite を使えます。
