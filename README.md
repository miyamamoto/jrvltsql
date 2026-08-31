# JRVLTSQL

JRVLTSQL は、JRA-VAN DataLab の JRA データを SQLite または PostgreSQL に保存する
ツールです。NAR / 地方競馬は対象外です。

公開ドキュメント: https://miyamamoto.github.io/jrvltsql/

## 実行環境は2通り

JV-Link は 32-bit の Windows COM コンポーネントなので、公式の実行環境は Windows
です。Linux では同梱の Docker イメージが Wine 上で 32-bit の bridge を動かします。

| 実行環境 | 使うもの | 位置づけ |
| --- | --- | --- |
| Windows 10 / 11 | `quickstart.bat` などの batch と `jltsql` CLI | JV-Link 公式の想定環境 |
| Linux (x86_64) | `Dockerfile` / `docker-compose.yml` + Wine | 同梱の Docker/Wine 実行環境。[Wine/Docker](docs/wine_docker.md) |

ARM（Apple Silicon）では動きません。JV-Link と bridge が 32-bit x86 で、
Rosetta 2 は x86_64 しか扱わないためです。x86_64 のホストを使ってください。

どちらの環境でも、JV-Link のインストール・利用規約への同意・サービスキー登録は
人が行います。このリポジトリは代行しません。未登録なら取得は理由を出して
fail closed で止まります。

## まず準備

| 項目 | 要件 |
| --- | --- |
| OS | Windows 10 / 11、または x86_64 Linux + Docker |
| Python | Python 3.12 以上。Windows のリリース検証済み経路は 32-bit Python + 32-bit JV-Link です。 |
| 契約 | JRA-VAN DataLab + サービスキー |
| PostgreSQL | PostgreSQL 運用時のみ必要 |

公式 JV-Link SDK 5.0.0 では 64-bit 版が追加され、32-bit 版も引き続き提供されています。
ただし、jrvltsql の 64-bit 実行経路は未検証です。x64 SDK の実導入からデータ取得、
parse、DB保存までの検証が完了するまでは、64-bit 対応済みとは扱いません。

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
| 三連複・三連単を含む締切前オッズを残す | `jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql` | 開催週の全賭式速報オッズを `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` に保存します。 |
| 日次同期を手動登録する | `powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30` | `daily_sync.bat` を Windows タスクとして登録します。 |

詳細な判断フローは [はじめに](docs/getting_started.md) を参照してください。

## 重要な区別

| データ | 保存先 | 取得方法 | 注意 |
| --- | --- | --- | --- |
| 通常データ | `NL_*` | `quickstart.bat`, `daily_sync.bat` | 出馬表、結果、払戻、確定オッズなどです。 |
| 確定オッズ | `NL_O1`〜`NL_O6` | `RACE` 取得 | レース後の確定オッズです。投資判断時点のオッズではありません。 |
| 公式時系列オッズ | `TS_O1`, `TS_O2` | `0B41`, `0B42` | 単複枠・馬連のみ。JRA-VAN 側の保持は約1年です。 |
| 開催週の速報オッズ | `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` | `0B30` または `0B31`〜`0B36` | 全賭式対応。ただし JRA-VAN 側の保持は約1週間です。 |
| 日次同期 | `NL_*`, `TS_O1`, `TS_O2`, `TS_SOKUHO_O*` | `daily_sync.bat --db sqlite` / `--db postgresql` | 既定では直近通常データ、公式時系列、開催週速報を更新します。不要なら `--no-timeseries` / `--no-realtime` を指定します。 |

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

`daily_sync.bat` は運用向けに PostgreSQL 既定です。通常データに加え、
公式 `TS_O1` / `TS_O2` と開催週の速報系データも取得します。
通常データだけに絞る場合は `--no-timeseries --no-realtime` を指定してください。

## Linux (Docker + Wine) で動かす

イメージは Wine と 32-bit bridge、noVNC の画面を含みます。JV-Link 本体の
インストールと利用登録は、その画面上で人が一度だけ行います。

```bash
docker compose up -d jltsql
docker compose logs jltsql | tail -20
```

prefix に JV-Link が無ければ、entrypoint がその旨を出して取得は行いません。
ブラウザで noVNC を開き、インストーラを実行して規約に同意し、サービスキーを
入力します（同じ箱で作業している場合。別ホストなら `ssh -L 6080:localhost:6080`）。

```text
http://localhost:6080/vnc.html
```

VNC はパスワード無しなので、compose は `127.0.0.1` にだけ公開します。
手順の全体は [JV-Link 手動登録](docs/jvlink_manual_registration.md) にあります。

登録後は Windows と同じ CLI を使います。

```bash
docker compose exec jltsql jltsql init
docker compose exec jltsql jltsql status
docker compose exec jltsql jltsql fetch --spec RACE --from 20260101 --to 20260417
```

取得中に JV-Link が版更新の確認ダイアログを出すことがあります。既定では
何も押さないので、noVNC 上で人が答えるまで `JVOpen` は戻りません（実測
1,008 秒）。無人で流す場合だけ `JVLINK_AUTO_CLOSE_DIALOGS=1` を明示すると、
既知のダイアログを Escape で拒否します（承諾する入力は送りません）。人の応答待ちや
setup 取得が 120 秒を超える環境では `JVLINK_OPEN_TIMEOUT_SECONDS`（1〜86400 秒）で
`JVOpen` の応答待ちを延ばします。前月までの official setup data は終了時刻で
上限を切れず、複数年取得は数時間かかり得るため、配備側が監視可能な有限値を指定します。

## 詳細ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [はじめに](docs/getting_started.md) | 目的別の実行順序 |
| [Wine/Docker](docs/wine_docker.md) | Linux での実行構成と 32-bit の前提 |
| [JV-Link 手動登録](docs/jvlink_manual_registration.md) | noVNC でのインストールと利用登録 |
| [対応データ種別一覧](docs/data_support.md) | JVOpen / JVRTOpen spec と保存先 |
| [レコード別の公式契約と移行手順](docs/record_contracts.md) | レコード種別ごとの公式レイアウト・主キー・`DataKubun`・既存 DB の移行手順 |
| [時系列オッズ](docs/timeseries_odds.md) | `0B41/0B42` と `0B30` 系の違い |
| [PostgreSQL](docs/postgresql.md) | PostgreSQL 保存と日次同期 |
| [CLI](docs/CLI.md) | CLI リファレンス |
| [スクリプト一覧](docs/scripts.md) | batch / script の役割 |
| [リリース運用方針](docs/release_policy.md) | 通常リリース、緊急 hotfix、運用環境への採用を分離する規則 |
| [アーキテクチャ](docs/architecture.md) | 実装構成 |

## テスト

```bat
pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/
```

イメージには実行時の依存だけを入れているので、テストはリポジトリ側で実行して
ください。Linux でも同じコマンドです。

```bash
pytest tests/ -q --ignore=tests/integration/ --ignore=tests/e2e/
```

## ライセンス

[LICENSE](LICENSE) を参照してください。
