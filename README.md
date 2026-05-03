# JRVLTSQL

JRVLTSQL は、JRA-VAN DataLab の JRA データを SQLite または PostgreSQL に保存する
Windows 向けツールです。NAR / 地方競馬は対象外です。

公開ドキュメント: https://miyamamoto.github.io/jrvltsql/

## まず準備

| 項目 | 要件 |
| --- | --- |
| OS | Windows 10 / 11 |
| Python | Python 3.10 以上。JV-Link COM を直接使う環境では 32-bit Python を推奨します。 |
| 契約 | JRA-VAN DataLab + サービスキー |
| PostgreSQL | PostgreSQL 運用時のみ必要 |

PowerShell でインストールします。

```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

手動で入れる場合:

```bat
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
pip install -e .
```

## 最短手順

迷ったら、まず SQLite で動かしてください。

```bat
quickstart.bat
```

これで JRA の出馬表、成績、払戻、確定オッズなどの通常データが
`data\keiba.db` に入ります。完了時に、通常データの日次同期タスクを
Windows タスクスケジューラへ登録するか確認されます。

## 目的別コマンド

| 目的 | 実行するコマンド | 結果 |
| --- | --- | --- |
| SQLite に通常データを入れる | `quickstart.bat` | `NL_RA`, `NL_SE`, `NL_HR`, `NL_O1`〜`NL_O6` などが `data\keiba.db` に入ります。 |
| SQLite に公式時系列オッズも入れる | `quickstart.bat` で時系列オッズ取得を選ぶ | `TS_O1` / `TS_O2` に単複枠・馬連の公式時系列オッズが入ります。 |
| SQLite で範囲指定して公式時系列オッズも入れる | `quickstart_timeseries.bat --db sqlite --from 20250426 --to 20260412` | 指定範囲の通常データ + `TS_O1` / `TS_O2` を取得し、日次同期タスク登録を確認します。 |
| PostgreSQL で範囲指定して公式時系列オッズも入れる | `quickstart_timeseries.bat --db postgresql --from 20250426 --to 20260412` | 指定範囲の通常データ + `TS_O1` / `TS_O2` を取得し、日次同期タスク登録を確認します。 |
| SQLite で非対話実行する | `quickstart.bat --yes --include-timeseries` | 通常データは `19860101`〜今日、公式時系列オッズは今日から過去12か月を取得します。タスク登録確認は出しません。 |
| 既存 PostgreSQL に公式時系列だけ足す | `fetch_timeseries_postgres.bat 20250426 20260412` | `TS_O1` / `TS_O2` だけを追加します。 |
| 三連複・三連単を含む締切前オッズを残す | `jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql` | 開催週の全賭式速報オッズを `TS_O1`〜`TS_O6` に保存します。 |
| 日次同期を手動登録する | `powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30` | `daily_sync.bat` を Windows タスクとして登録します。 |

詳細な判断フローは [はじめに](docs/getting_started.md) を参照してください。

## 重要な区別

| データ | 保存先 | 取得方法 | 注意 |
| --- | --- | --- | --- |
| 通常データ | `NL_*` | `quickstart.bat`, `daily_sync.bat` | 出馬表、結果、払戻、確定オッズなどです。 |
| 確定オッズ | `NL_O1`〜`NL_O6` | `RACE` 取得 | レース後の確定オッズです。投資判断時点のオッズではありません。 |
| 公式時系列オッズ | `TS_O1`, `TS_O2` | `0B41`, `0B42` | 単複枠・馬連のみ。JRA-VAN 側の保持は約1年です。 |
| 開催週の速報オッズ | `TS_O1`〜`TS_O6` | `0B30` または `0B31`〜`0B36` | 全賭式対応。ただし JRA-VAN 側の保持は約1週間です。 |
| 日次同期 | `NL_*` | `daily_sync.bat --db sqlite` / `--db postgresql` | 時系列オッズは取得しません。 |

## PostgreSQL を使う場合

先に接続情報を設定します。

```bat
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5432
set POSTGRES_DATABASE=keiba_dev
set POSTGRES_USER=ingestion_writer
set POSTGRES_PASSWORD=<password>
```

その後、PostgreSQL 用 quickstart を実行します。

```bat
quickstart_timeseries.bat --db postgresql --from 20250426 --to 20260412
```

SQLite と PostgreSQL の範囲指定は `quickstart_timeseries.bat --db <sqlite|postgresql> --from <FROM> --to <TO>` に統一しています。
`quickstart_timeseries.bat` で `--from` / `--to` を省略した場合は、通常データも公式時系列オッズも今日から過去365日分を対象にします。
PostgreSQL 専用バッチ `quickstart_postgres_timeseries.bat <FROM> <TO>` もありますが、新規利用では上の共通コマンドを使ってください。

## 日次同期

`daily_sync.bat` は SQLite / PostgreSQL の両方に対応します。

```bat
daily_sync.bat --db sqlite --days-back 7 --days-forward 3
daily_sync.bat --db postgresql --days-back 7 --days-forward 3
```

手動で Windows タスクへ登録する場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType postgresql -Time 06:30
```

`daily_sync.bat` は通常データ更新用です。公式時系列オッズや全賭式速報オッズを継続蓄積する場合は、別途オッズ取得コマンドを実行してください。

## 詳細ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [はじめに](docs/getting_started.md) | 目的別の実行順序 |
| [対応データ種別一覧](docs/data_support.md) | JVOpen / JVRTOpen spec と保存先 |
| [時系列オッズ](docs/timeseries_odds.md) | `0B41/0B42` と `0B30` 系の違い |
| [PostgreSQL](docs/postgresql.md) | PostgreSQL 保存と日次同期 |
| [CLI](docs/CLI.md) | CLI リファレンス |
| [スクリプト一覧](docs/scripts.md) | batch / script の役割 |
| [アーキテクチャ](docs/architecture.md) | 実装構成 |

## テスト

```bat
pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/
```

## ライセンス

[LICENSE](LICENSE) を参照してください。
