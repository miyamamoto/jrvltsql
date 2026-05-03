# はじめに

このページは、JRVLTSQL を初めて使うときの実行順序だけをまとめた手順書です。
細かい spec やテーブル定義は、あとで [対応データ種別一覧](data_support.md) を見てください。

## 0. 準備

JRVLTSQL は Windows + JRA-VAN DataLab / JV-Link を前提にした JRA 用ツールです。
地方競馬は対象外です。

Python は 3.10 以上で動作します。JV-Link COM を直接使う環境では 32-bit Python を推奨します。

インストール:

```powershell
irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
```

手動で入れる場合:

```bat
git clone https://github.com/miyamamoto/jrvltsql.git
cd jrvltsql
pip install -e .
```

## 1. まず決めること

決めることは2つだけです。

| 質問 | 迷ったときの選択 |
| --- | --- |
| 保存先は SQLite か PostgreSQL か | まずは SQLite。共有・本番運用なら PostgreSQL。 |
| 必要なオッズはどれか | 通常データだけなら `quickstart.bat`。投資判断時点のオッズ評価をするなら時系列オッズも取得。 |

## 2. ルートA: SQLiteでまず動かす

一番簡単な導線です。

```bat
quickstart.bat
```

実行後にできること:

- `data\keiba.db` が作られます。
- 出馬表、成績、払戻、確定オッズなどの通常データが `NL_*` に入ります。
- 完了時に、SQLite 用の日次同期タスクを登録するか確認されます。

このコマンドだけではできないこと:

- PostgreSQL への保存
- 三連複・三連単を含む締切前オッズの長期蓄積

## 3. ルートB: SQLiteに公式時系列オッズも入れる

単複枠・馬連の過去時系列オッズも保存したい場合です。

対話形式では、`quickstart.bat` の途中で時系列オッズ取得を選びます。

非対話で実行する場合:

```bat
quickstart.bat --yes --include-timeseries
```

実行後に入るデータ:

| データ | 保存先 |
| --- | --- |
| 通常データ | `NL_*` |
| 単複枠の公式時系列オッズ | `TS_O1` |
| 馬連の公式時系列オッズ | `TS_O2` |

注意:

- `--yes` を付けると確認プロンプトを出しません。
- そのため、日次同期タスク登録もスキップします。必要なら後で `install_tasks.ps1` を実行してください。
- `TS_O1` / `TS_O2` は JRA-VAN 側で約1年保持される公式時系列です。

## 4. ルートC: PostgreSQLで運用する

共有DBや本番運用では PostgreSQL を使います。

先に接続情報を設定します。

```bat
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5432
set POSTGRES_DATABASE=keiba_dev
set POSTGRES_USER=ingestion_writer
set POSTGRES_PASSWORD=<password>
```

次に PostgreSQL 用 quickstart を実行します。

```bat
quickstart_postgres_timeseries.bat 20250426 20260412
```

実行後にできること:

- PostgreSQL に指定範囲の通常データが入ります。
- 公式時系列オッズ `TS_O1` / `TS_O2` が入ります。
- 完了時に、PostgreSQL 用の日次同期タスクを登録するか確認されます。

注意:

- `quickstart.bat` から PostgreSQL 用 quickstart は呼びません。
- SQLite と PostgreSQL は導線を分けています。
- タスクから PostgreSQL に接続する場合は、`POSTGRES_*` を Windows ユーザー環境変数として保存する必要があります。

## 5. ルートD: 三連複・三連単を含む締切前オッズを残す

全賭式の投資判断時点オッズを評価したい場合は、開催週に速報オッズを蓄積します。

PostgreSQL に保存する場合:

```bat
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db postgresql
```

SQLite に保存する場合:

```bat
jltsql realtime odds-sokuho-timeseries --from 20260418 --to 20260419 --db sqlite --db-path data/keiba.db
```

入るデータ:

| 賭式 | 保存先 |
| --- | --- |
| 単勝・複勝・枠連 | `TS_O1` |
| 馬連 | `TS_O2` |
| ワイド | `TS_O3` |
| 馬単 | `TS_O4` |
| 三連複 | `TS_O5` |
| 三連単 | `TS_O6` |

注意:

- `0B30` 系の速報オッズは JRA-VAN 側の保持が約1週間です。
- 1か月後にまとめて取りに行く運用はできません。
- 長期評価したい場合は、開催週から継続蓄積してください。
- `jltsql realtime odds-timeseries` / `odds-sokuho-timeseries` は、既存 DB のレース情報を使って取得キーを作ります。先に通常データを入れてください。

## 日次同期

通常データの更新だけを毎日行う場合は `daily_sync.bat` を使います。
直接実行時の既定は PostgreSQL です。SQLite では必ず `--db sqlite` を指定してください。

```bat
daily_sync.bat --db sqlite --days-back 7 --days-forward 3
daily_sync.bat --db postgresql --days-back 7 --days-forward 3
```

Windows タスクスケジューラへ手動登録する場合:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType sqlite -Time 06:30
powershell -NoProfile -ExecutionPolicy Bypass -File install_tasks.ps1 -DbType postgresql -Time 06:30
```

`daily_sync.bat` が更新するのは通常データです。時系列オッズは取得しません。

## よくある混同

| 混同しやすい点 | 正しい理解 |
| --- | --- |
| `quickstart.bat` は PostgreSQL も設定するのか | しません。SQLite 既定の通常 quickstart です。 |
| `quickstart_postgres_timeseries.bat` は SQLite にも使うのか | 使いません。PostgreSQL 専用です。 |
| `daily_sync.bat` は SQLite / PostgreSQL の両方で使えるのか | 使えます。`--db sqlite` または `--db postgresql` を指定します。 |
| `daily_sync.bat` で時系列オッズも入るのか | 入りません。通常データ更新だけです。 |
| 確定オッズ `NL_O*` は投資判断時点のオッズか | 違います。レース後の確定オッズです。 |
| 三連複・三連単の過去時系列を1年分まとめて取れるか | 取れません。開催週の継続蓄積が必要です。 |

## 動作確認

DB の状態確認:

```bat
jltsql status
```

保存済み時系列オッズを CSV で見る場合:

```bat
python tools/export_timeseries_csv.py --help
```

CLI の詳細:

```bat
jltsql --help
jltsql realtime --help
```
