# アーキテクチャ

jrvltsql は、JRA-VAN DataLab のデータを SQLite または PostgreSQL に保存する
Windows 向け JRA データコレクタです。共有分析基盤向けに PostgreSQL へ
直接保存できます。

## 対象範囲

- JRA / 中央競馬のみ
- Windows 10 / 11
- JRA-VAN DataLab + JV-Link
- Python 3.12 以上
- リリース検証済み構成: 32-bit Python + 32-bit JV-Link

NAR / 地方競馬はこのリポジトリの対象外です。

SDK 5.0.0 では 64-bit 版 JV-Link が追加されましたが、JV-Data と JV-Link の
データ／インターフェース仕様は変更されていません。これは公式SDKの契約についての
記述であり、jrvltsqlのx64動作実証ではありません。64-bit 実行経路は未検証で、
実SDKの導入・取得・parse・DB保存が完了するまではリリース対応範囲に含めません。

## 開発と配備

このリポジトリの開発正本は GitHub と Git worktree です。Windows の実行・
検証・収集環境で直接作った差分を正本にせず、変更は開発用 worktree で
ブランチ化し、テスト後に GitHub へ push してから対象環境へ配備します。

運用の保存先は PostgreSQL を優先します。`daily_sync.bat` の既定は
`--db postgresql` で、収集した通常データは PostgreSQL に直接保存します。
SQLite は単体検証や PostgreSQL がない環境のフォールバックです。

### 外部 bridge を使う配備

公開 CLI の利用要件は Windows 10 / 11 です。`JVLinkBridge` クライアントを
外部 collector から利用する場合は `JVLINK_BRIDGE_EXE` で実行可能な bridge を
指定します。bridge、JV-Link、GUI セッションの準備とサービスキー登録は配備
環境の責務です。Windows では bridge を直接実行します。非Windows の検証環境で
bridge を起動する場合は、外部 runner の実行ファイルを
`JVLINK_BRIDGE_RUNNER` へ明示し、暗黙の実装選択に依存しないでください。

JV-Link は `JVOpen` / `JVRTOpen` 中にお知らせや DataLab 更新確認を表示し、
非対話実行を停止させる場合があります。既定ではクライアントは何も押しません。
提供元の問いかけを人が見て判断できるようにするためで、応答があるまで
`JVOpen` は戻りません（実測 1,008 秒）。無人運転する場合に限り
`JVLINK_AUTO_CLOSE_DIALOGS=1` を明示すると、既知のダイアログだけを安全側へ
拒否します（承諾する入力は送りません）。監視間隔は
`JVLINK_DIALOG_WATCH_INTERVAL_SECONDS` で変更できます。未知のダイアログ、応答
timeout、読めない bridge 応答は成功扱いせず、timeout 時は状態不明の bridge
process を終了します。

## 主要コンポーネント

| コンポーネント | 役割 |
| --- | --- |
| `src/cli/main.py` | Click ベースの CLI エントリポイントです。コマンド名は `jltsql` です。 |
| `src/jvlink/` | JV-Link COM へのアクセス、データ種別定数、キー生成を担当します。 |
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
