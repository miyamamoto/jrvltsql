# アーキテクチャ

jrvltsql は、JRA-VAN DataLab のデータを SQLite または PostgreSQL に保存する
JRA データコレクタです。Windows では JV-Link COM を直接使い、Linux では
Docker/Wine 上の JVLinkBridge 経由で動かせます。共有分析基盤向けに
PostgreSQL へ直接保存できます。

## 対象範囲

- JRA / 中央競馬のみ
- Windows 10 / 11、または Docker が使える Linux
- JRA-VAN DataLab + JV-Link
- JV-Link COM コンポーネントが 32-bit のため、直接 COM では 32-bit Python を推奨
- Linux/Docker では Wine 32-bit prefix と `tools/jvlink-bridge/bin/native/JVLinkBridge.exe` を使用

NAR / 地方競馬はこのリポジトリの対象外です。

## 開発と配備

このリポジトリの開発正本は Linux 開発環境の Git worktree です。a6 は
Windows 実行・検証・収集用の配備先として扱い、a6 上で直接開発した差分を
正本にしません。変更は開発環境でブランチ化し、テスト後に GitHub へ push
し、a6 はそのブランチまたは main を取り込んで動作確認します。

運用の保存先は PostgreSQL を優先します。`daily_sync.bat` の既定は
`--db postgresql` で、収集した通常データは PostgreSQL に直接保存します。
SQLite は単体検証や PostgreSQL がない環境のフォールバックです。

## 主要コンポーネント

| コンポーネント | 役割 |
| --- | --- |
| `src/cli/main.py` | Click ベースの CLI エントリポイントです。コマンド名は `jltsql` です。 |
| `src/jvlink/` | JV-Link COM へのアクセス、データ種別定数、キー生成を担当します。 |
| `tools/jvlink-bridge/` | Windows native / Wine 用の JV-Link COM ブリッジです。Python とは stdin/stdout JSON で通信します。 |
| `Dockerfile` / `docker-compose.yml` | Linux で Wine、Xvfb、noVNC、PostgreSQL をまとめて起動する実行環境です。 |
| `src/parser/` | JRA-VAN レコードのパーサー群です。 |
| `src/database/` | SQLite / PostgreSQL ハンドラ、スキーマ、テーブル対応を管理します。 |
| `src/realtime/` | JVRTOpen 速報・時系列データの保存処理を担当します。 |
| `scripts/quickstart.py` | 対話・非対話の初期セットアップと更新処理をまとめます。 |
| `quickstart.bat` | Windows 向けの通常 quickstart です。既定は SQLite で、対話形式または `--yes --include-timeseries` により SQLite に公式時系列オッズも保存できます。最後に SQLite 用の日次同期タスク登録を確認します。 |
| `quickstart_timeseries.bat` | SQLite / PostgreSQL 共通の範囲指定つき時系列 quickstart です。指定範囲の通常データと公式時系列オッズを投入し、最後にタスク登録を確認します。 |
| `quickstart_postgres_timeseries.bat` | PostgreSQL 専用 quickstart です。 |
| `daily_sync.bat` | Windows タスクスケジューラから実行する日次同期です。 |
| `install_tasks.ps1` | `daily_sync.bat` の Windows タスク登録・更新を行います。 |

対応している `JVOpen` / `JVRTOpen` spec、保存先テーブル、運用コマンドは
[対応データ種別一覧](data_support.md) にまとめています。

## データ保存先

| 保存先 | 用途 |
| --- | --- |
| SQLite | 単一ユーザー・ローカル検証・PostgreSQL がない環境でのフォールバック |
| PostgreSQL | 複数ホストで共有するコレクタ / 分析基盤 |
| バイナリキャッシュ | JV-Link 読み出しの再実行を減らすためのローカルキャッシュ |

`config/config.yaml.example` の既定は SQLite です。PostgreSQL を使う場合は
CLI 引数またはローカル設定で切り替えます。

## 時系列オッズ

JRA-VAN の公式長期保持時系列オッズは以下です。

| JVRTOpen spec | 保存先テーブル | 対象 |
| --- | --- | --- |
| `0B41` | `TS_O1` | 単勝・複勝・枠連。保持は約1年です。 |
| `0B42` | `TS_O2` | 馬連。保持は約1年です。 |

全賭式の速報オッズは `0B30`〜`0B36` です。こちらは開催週の約1週間保持です。
保存先は公式時系列とは分けて `TS_SOKUHO_O1`〜`TS_SOKUHO_O6` です。
ワイド、馬単、三連複、三連単を投資判断時点オッズで評価するには、
開催週に継続蓄積してください。

## スケジューリング

通常データの同期は、Windows タスクスケジューラで `daily_sync.bat` を
日次実行します。`daily_sync.bat` は `--db sqlite` / `--db postgresql` の
両方に対応します。`quickstart.bat` は SQLite 用、`quickstart_timeseries.bat`
は指定した DB 用としてこのタスク登録を確認します。

PostgreSQL 接続をタスクから行う場合、`POSTGRES_*` 環境変数は Windows
ユーザー環境変数など永続的に参照できる場所へ設定してください。

開催週の `0B30`〜`0B36` 継続蓄積は、通常の日次同期とは別に race-day 用の
リアルタイムタスクまたはサービスとして運用します。
