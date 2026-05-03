# アーキテクチャ

jrvltsql は、JRA-VAN DataLab のデータを SQLite または PostgreSQL に保存する
Windows 向け JRA データコレクタです。共有分析基盤向けに PostgreSQL へ
直接保存できます。

## 対象範囲

- JRA / 中央競馬のみ
- Windows 10 / 11
- JRA-VAN DataLab + JV-Link
- JV-Link COM コンポーネントが 32-bit のため、32-bit Python を推奨

NAR / 地方競馬はこのリポジトリの対象外です。

## 主要コンポーネント

| コンポーネント | 役割 |
| --- | --- |
| `src/cli/main.py` | Click ベースの CLI エントリポイントです。コマンド名は `jltsql` です。 |
| `src/jvlink/` | JV-Link COM へのアクセス、データ種別定数、キー生成を担当します。 |
| `src/parser/` | JRA-VAN レコードのパーサー群です。 |
| `src/database/` | SQLite / PostgreSQL ハンドラ、スキーマ、テーブル対応を管理します。 |
| `src/realtime/` | JVRTOpen 速報・時系列データの保存処理を担当します。 |
| `scripts/quickstart.py` | 対話・非対話の初期セットアップと更新処理をまとめます。 |
| `quickstart.bat` | Windows 向けの通常 quickstart です。既定は SQLite で、`--include-timeseries` により SQLite に公式時系列オッズも保存できます。 |
| `quickstart_postgres_timeseries.bat` | PostgreSQL へ RACE と公式時系列オッズを投入し、最後にタスク登録を確認します。 |
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
ワイド、馬単、三連複、三連単を投資判断時点オッズで評価するには、
開催週に継続蓄積してください。

## スケジューリング

通常データの同期は、Windows タスクスケジューラで `daily_sync.bat` を
日次実行します。`quickstart_postgres_timeseries.bat` は、PostgreSQL
時系列オッズ投入完了後にこのタスク登録を確認します。

PostgreSQL 接続をタスクから行う場合、`POSTGRES_*` 環境変数は Windows
ユーザー環境変数など永続的に参照できる場所へ設定してください。

開催週の `0B30`〜`0B36` 継続蓄積は、通常の日次同期とは別に race-day 用の
リアルタイムタスクまたはサービスとして運用します。
