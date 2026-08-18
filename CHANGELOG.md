# 変更履歴

このプロジェクトの主な変更点をこのファイルに記録します。

形式は [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) を参考にし、
バージョン番号は [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

## [Unreleased]

次回リリースは互換性を破る変更を含むため `2.0.0` とする。1.xとしては配布しない。

### Removed

- `JVLinkWrapper.jv_set_service_key` / `JVLinkBridge.jv_set_service_key` と、
  レジストリをプログラムから変更する経路を削除。利用登録はDataLabで行う
- O1〜O6を単独JVOpen data specのように見せる重複定数を削除。これらはRACEに
  含まれるrecord typeであり、`RECORD_TYPE_O1`〜`RECORD_TYPE_O6`を使用する

### Changed

- 非Windowsのbridge起動は暗黙の実装選択を廃止し、外部runnerを
  `JVLINK_BRIDGE_RUNNER`で明示する。公開propertyは
  `uses_external_runner`へ変更
- CLIの既定config/log/dataはinstalled package配下ではなく実行時の作業場所と
  user stateを使う。`jltsql init`はカレントディレクトリをSQLite-onlyの安全な
  既定で初期化し、`--config`との併用は曖昧さを避けるため拒否する
- JV-Link SDK 5.0.0 で公式 64-bit 版が追加されたことを文書へ反映。ただし
  jrvltsql の 64-bit 実行経路は未検証であり、x64 SDK の実導入・取得・parse・
  DB保存を完了するまでは対応済みとしない。インストーラとランチャーは、
  リリース検証済みの 32-bit Python / JV-Link 経路を既定として維持
- Python の実行要件を `pyproject.toml` と一致する 3.12 以上へ統一
- 公式 64-bit 版と競合し得る旧レジストリ回避ツールを削除
- 公式 fixed-width parser、DataKubun、primary key、native/standard child
  schema を現行契約へ揃え、SQLite/PostgreSQL の transaction recovery と
  durable statistics を fail closed 化
- 1.x DB は事前 backup のうえ v2 schema で rebuild/reimport し、件数・key・
  取消・readback を確認する。rollback は部分移行DBの再利用ではなく、backup と
  旧releaseの復元で行う。詳細は `docs/data_support.md` と v2 release notes を参照

### Fixed

- `HN`を公式現行251バイト配置と10桁`HansyokuNum` identityへ結び付け、native
  `NL_HN`と標準名`HANSYOKU`でprovider順のstatus 1/2更新、status 0 exact erase、
  caller validation、SQLite/PostgreSQLのstrict schema preflightを一致させた。
  旧245バイト配置とnullable/keyless/wrong-type/extended tableは自動移行せず、
  backup・rebuild・`BLDN` reimportを要求する。HNは蓄積系masterだけであり、
  `RT_HN`を追加しない
- `CC`を公式50バイト配置と6項目race keyへ結び付け、発表`MMDDhhmm`、変更前後の
  4桁距離・track code、事由区分をlosslessに検証・保存する。native `NL_CC`、
  速報`RT_CC`、標準名`COURSE_CHANGE`でprovider順の改訂を1行へ反映し、current
  status 1以外、不正日付/競馬場/track/reason、nullable・keyless・wrong-type・
  追加constraintをmutation前に拒否する。status 0 deleteは作らず、`0B14`の
  正常完了後だけ日単位の完全snapshot置換を行う。旧unsafe tableはbackup・
  rebuild・reimportを要求する
- `TC`を公式45バイト配置と6項目race keyへ結び付け、発表`MMDDhhmm`と変更前後
  `HHmm`をlosslessに検証・保存する。native `NL_TC`、速報`RT_TC`、標準名
  `HASSOU_JIKOKU_CHANGE`でprovider順の改訂を1行へ反映し、current status 1以外、
  不正日付/競馬場/時刻、nullable・keyless・wrong-type・追加constraintをmutation前に
  拒否する。TCにはstatus 0 deleteを作らず、`0B14`の正常完了後だけ日単位の完全
  snapshot置換を行う。旧unsafe tableと旧標準名`COMMENT`はbackup・rebuild・
  reimportを要求する
- `HC`を公式現行60バイト配置と4項目キーへ結び付け、native `NL_HC`と標準名
  `HANRO`で7つの走破・lap time fieldを0.1秒単位で保持し、provider順の更新、
  status 0 exact delete、caller validation、SQLite/PostgreSQLのstrict schema
  preflightを一致させた。
  旧nullable/keyless/wrong-key tableや未承認の追加列・constraintは自動移行せず
  backup・rebuild・`SLOP` reimportを要求し、HCは蓄積系のみであることを明記した
- `HS`を現行HOSNの公式200バイト配置と3項目キーへ結び付け、native `NL_HS`と
  標準名`SALE`でprovider順の更新・exact delete・operation統計を一致させた。
  旧196バイトHOSEは引き続き拒否し、v2以前の既存tableは空でも値長から推測せず
  backup・rebuild・現行sourceからのreimportを要求する（現行互換の空`NL_HS`で
  marker/delimiterだけが欠ける場合を除く）。過去の馬齢は公式setup済み値を再解釈せず、
  市場名は当時表記を保持する。live本文はcoercion前に検証し、
  status 0の非key本文だけはexact eraseを妨げないopaque project policyとした
- `HR`を公式719バイト・6項目キーへ結び付け、3件の予備領域を数値化せず文字列で
  保持する全repeatを
  native/速報/JRA-VAN標準名`HARAI`へ保存。`HARAI`の払戻NULL化・重複行、
  coercion前validation欠落、unsafe schemaの見逃し、PostgreSQL同一キー操作の
  統計過少計上を修正。2004-08-14より前の同長114バイト領域は三連単と誤解釈せず
  hexでlossless保持し、現行三連単列と区別する。公式に本文値の規定がない中止状態9も
  本文を払戻として意味変換せず、raw監査値とキー・状態を保持する
- `AV`を公式78バイト・7項目キーへ結び付け、native/速報/JRA-VAN標準名の
  主キーを`NOT NULL`で統一。旧status 0はexact delete、現行status 1/2と
  2021年前後の事由blank/000〜003を両立し、旧`AVOIDENCE`単独構成、不正key・
  本文・unsafe schemaをSQLite/PostgreSQLのmutation前に拒否
- `SE`の現行555バイト全sliceをSDK 5.0.0 manifestへ結び付け、native/速報/
  JRA-VAN標準名の主キーを公式8項目（末尾`KettoNum`）へ統一。旧7項目・keyless・
  不正型・追加一意制約・deferrable主キーはmutation前に拒否し、個別取消、4予約領域、
  馬体重/増減の整数kg、status Aの本賞金0円をSQLite/PostgreSQLで保持
- MCP向け`TABLE_METADATA`をnative 80表とJRA-VAN標準54表の全134実DDLへ
  結び付け、列名・型・論理NULL可否・主キー・索引対象が実在する物理列と一致する
  よう修正。適用前に各backendの実catalogを照合し、SQLiteは旧版の表示専用疑似列を
  除去、PostgreSQLは物理列へcommentを適用、Dualは各backend固有の構文で処理する。
  MCP exportは破壊的な物理metadata契約を明示するversion 2.0.0へ更新
- JV-Link COM class 未登録時の診断を、公式SDKが提供する同じbit数のJV-Linkと、
  jrvltsqlでリリース検証済みの32-bit経路を区別する案内へ修正
- `NL_SK` の公開メタデータに欠けていた曽祖父母8頭の繁殖登録番号を追加し、
  parser が保持する3代14頭分の血統番号と一致

## [1.6.10] - 2026-08-11

### Fixed

- write-through cache への書き込みを parsed record 単位ではなく `jv_read` buffer
  単位に変更。full-struct parser（H1 は 28,955 byte の buffer から 1,485 行、
  H6 は 102,890 byte から 4,896 行）は 1 つの buffer を多数の行に展開し、各行が
  同一の `_raw` を持つため、同じ blob が行数分だけ追記されていた。実測（RACE/option=4）
  では、約 10 分間で 21.8 GB・99.9% が重複（同一範囲の実データは約 80 MB）。
  書き込みレートは別計測で 4,230 MB/min、修正後に同一範囲を再実行すると
  10.17 MB/min・重複 0% になった（2 つは別々の計測で、一方から他方は導出できない）。
  `_raw` の契約と yield される record の形は変更なし
- `JVRead` の `-402`（0 byte の破損ファイル）を、`JVRead` が返した exact filename
  だけを `JVFiledelete` で削除し、同一の `JVOpen` context を再オープンして自己修復。
  再ダウンロード完了・file count・`last_file_timestamp` の一致を確認し、既に caller へ
  返した prefix を読み飛ばして重複なしで継続する。再試行は最大 2 回で、確認できない
  条件はすべて fail closed。`-403` は同一ファイルの一部 record を既に返している
  可能性があるため、best-effort 削除のうえ fail closed とし、危険な位置再開はしない
- append-only の raw cache を fetch 開始前の byte checkpoint へ rollback するよう変更。
  generator の途中放棄、replay 不完了、index 更新失敗でも半端な cache を残さない。
  複数日 range の complete index は一時ファイルからの atomic replace で一括確定する
- `--from/--to` と cache 完全性の意味を安全側へ統一。option=2 は `JVOpen` が
  `--from` を取得範囲として扱わないため、既存 NL cache を含めて cache をバイパスし、
  `cache build/rebuild --option 2` は誤った完全範囲を作る前に fail loud する
- HC/WC を日付なし master として扱わず、時系列の `ChokyoDate` で `--to` filter と
  cache 日付を判定。対応する event date を持たない master 行を検出した場合は完全
  cache marker を付けず、同一取得の部分 cache append も rollback する
- 旧 cache の完全性 marker を schema v2 で失効させ、legacy raw と active raw を分離

### Changed

- `fetch --option 2` の説明と `--from` の help を公式仕様に合わせて修正。`fromtime`
  は任意の過去週を選択するものではなく、現在の開催サイクル内の継続性を管理する
  ものであること、日曜・月曜は 2 つの開催サイクルにまたがりうることを明記
  （ドキュメントと help のみの変更で、取得と cache の挙動は変更なし）
- `config/config.yaml.example` の `databases.postgresql` に `connect_timeout` と
  `sslmode` を built-in 既定と同じ値（10 / prefer）で追記

### Added

- `tests/test_historical_cache_write_through.py`（新規）: buffer 単位の cache 書き込み
  回帰テスト。5 ケース中 4 ケースは本修正前には失敗する
- `tests/test_jvd_self_repair.py`（新規）: `JVRead` `-402`/`-403` の自己修復と
  fail-closed 条件の網羅テスト

## [1.6.9] - 2026-07-21

### Fixed

- PostgreSQL の `_get_existing_primary_key_columns()` / `_get_primary_key_columns()` /
  `table_exists()` を `to_regclass()` ベースに統一し、search_path 外のスキーマにある
  同名テーブルとの誤結合・`UndefinedTable` 例外を修正
- JV-Link 戻り値 `-100` を JVOpen/JVRTOpen 関連として誤配置していたのを修正
  （公式仕様書では `-100` は JVSetUIProperties/JVSetServiceKey 等の戻り値で、
  JVOpen/JVRTOpen の戻り値ではない）
- `scripts/quickstart.py` が JVInit の戻り値 `-100`〜`-103` を「サービスキー未設定/無効/
  期限切れ」と誤解釈していたのを修正。JVInit は `-101`〜`-103` のみを返し、いずれも
  sid パラメータの形式エラーであり、サービスキー状態（`-301`〜`-303`、JVOpen/JVRTOpen
  の戻り値）とは無関係
- `src/fetcher/base.py`・`src/fetcher/historical.py` の `-201`/`-202`/`-203` に関する
  誤ったコメント（「データベースビジー」「ファイルビジー」「セットアップ未完了」）を、
  公式仕様書に基づく正しい説明に修正（リトライ対象コードの集合自体は変更なし）

### Added

- `tests/test_jvlink_constants.py`（新規）: エラーコード定数とメッセージの網羅テスト
- `tests/test_postgresql.py`: search_path 切り替え時の `table_exists()`/`_get_existing_columns()`/
  `_get_existing_primary_key_columns()` 解決を検証する統合テスト
- `tests/test_quickstart_cli.py::TestAnalyzeErrorJVInitCodes`: JVInit vs JVOpen/JVRTOpen
  のエラーコード判定の回帰テスト

## [1.6.8] - 2026-07-18

### Added

- JRA SE の raw 固定幅値を保持したまま、走破タイム、上がり3F、馬体重、増減、着順、馬番の canonical 数値列を追加
- SQLite/PostgreSQL の additive migration と primary-key 検証、および実レコード例を固定した parser contract test を追加

## [1.6.7] - 2026-07-15

### Fixed

- 速報・蓄積ストリーム中の `JVRead -2` をデータなしとして扱わず、途中まで取得した応答を正常終了として commit しないよう修正

## [1.6.6] - 2026-07-15

### Fixed

- dual mode で secondary PostgreSQL が接続不能な場合は migration/verification 対象から除外し、documented best-effort 動作どおり primary の収集を継続

## [1.6.5] - 2026-07-15

### Fixed

- `JVRead` が正の長さと空バッファを返した不完全な速報取得を失敗として扱い、0B14 の既存 snapshot を空または部分データで置換しないよう修正
- dual SQLite/PostgreSQL の additive schema migration を各 backend へ個別適用し、PostgreSQL の小文字 table identifier を誤って引用して追加列移行が止まる問題を修正

## [1.6.4] - 2026-07-15

### Fixed

- 非対話 `daily_update.py` でも外部 bridge の未購読例外を正常な spec スキップとして扱い、0B14/0B51 など任意購読 feed が未契約でも他 feed の収集を継続するよう修正

## [1.6.3] - 2026-07-15

### Fixed

- 外部 bridge の `JVLinkBridgeError` を未購読・busy の正常なリトライ判定に含め、任意 spec の未購読で同一 polling cycle の正常データを rollback しないよう修正
- JVRead の回復可能エラーも不完全取得として追跡し、欠損した 0B14 応答で既存の開催変更 snapshot を置換しないよう修正
- 外部 bridge 初期化失敗時に realtime monitor の health を停止状態へ更新するよう修正

## [1.6.2] - 2026-07-15

### Fixed

- `DataKubun=9` を RA/SE/WF の中止状態として保持しつつ、オッズ・票数など他レコードでは削除命令として処理するよう修正
- 0B14 のパース失敗を検知した場合、不完全な速報開催情報スナップショットで既存行を置換しないよう fail-closed 化
- 一時的な JV-Link / DB エラー後も background realtime polling を継続するよう修正
- 再利用される historical/realtime fetcher の統計を呼び出しごとに初期化し、前回の失敗が次の spec/key に混入しないよう修正
- realtime polling 中の全スキーマ準備を常駐プロセスにつき一度に制限し、締切前ポーリングの不要な DDL/metadata 負荷を削減

## [1.6.1] - 2026-07-15

### Fixed

- 非対話の JRA daily sync 経路で、坂路調教 `SLOP` / `NL_HC` とウッドチップ調教 `WOOD` / `NL_WC` を通常差分として毎日取得するよう修正
- `daily_sync.bat` の既定 `JRA_DAILY_UPDATE_SPECS` に `SLOP,WOOD` を追加し、Windows タスクスケジューラ実行でも調教データが初回セットアップ後に stale にならないよう修正
- MING、速報開催情報、WIN5 の定期収集と購読エラー処理を修正
- RA/SE の公式拡張レイアウトとマイニング領域の位置を修正し、不正レコードを fail-closed に変更
- WIN5 (`WF`) を公式7,215-byte形式へ更新し、有効票数5件と払戻243件を欠落なく保存
- SQLite/PostgreSQL の速報取り込みをトランザクション単位で原子的にし、途中失敗時は全件 rollback
- 0B16 を `JVWatchEvent` のイベントキー専用として日付指定ポーリングから除外

### Notes

- 公開リリースには外部 collector ランタイム変更を含めていません
- `NL_WF` / `RT_WF` に公式WF形式の列を追加する additive migration を含みます

## [1.6.0] - 2026-06-16

### Fixed

- JV-Data490 の HC / AV / H6 / O1〜O6 レイアウト不整合を修正
- 展開済みオッズ・払戻行を保持できるよう保存キーと不完全な primary-key 行の扱いを修正
- SQLite / PostgreSQL import、PostgreSQL batch insert grouping、migration metadata、realtime expanded-record storage を堅牢化

### Notes

- 既存 DB に旧 O1 / H6 / HC / AV 関連テーブル定義がある場合は、対象レコードの再 import 前に table recreation または migration を確認してください

## [1.5.0] - 2026-06-11

### Added

- HR の主要払戻配列を複数エントリ抽出へ拡張
  （3件の予備領域を含む完全化と標準名保存は2.0.0で実施）
- コーナー通過順位を最大4セットの配列として収集
- `0B12` / `0B15` の daily sync 統合を追加
- JVOpen/JVRTOpen の対応データ種別、レコード種別、保存先テーブル、運用コマンドをまとめた `docs/data_support.md` を追加
- 初回ユーザー向けの実行順序をまとめた `docs/getting_started.md` を追加
- SQLite / PostgreSQL 共通の範囲指定つき時系列 quickstart `quickstart_timeseries.bat` を追加

### Changed

- 運用環境固有のバックアップ除外設定を `.gitignore` に追加
- 公開ドキュメントを日本語表記へ統一
- README と MkDocs ホームを、初回導線・目的別コマンド・重要なデータ区分が一目で分かる構成へ整理
- `quickstart.bat --yes --include-timeseries` の既定取得範囲をドキュメントに明記
- `quickstart.bat` は SQLite 既定の通常セットアップに戻し、PostgreSQL 専用の `quickstart_postgres_timeseries.bat` 呼び出しを削除
- SQLite でも `quickstart.bat --yes --include-timeseries` または `jltsql realtime odds-timeseries --db sqlite` で公式 `TS_O1/TS_O2` を保存できることを明記
- `quickstart.bat` 完了時に SQLite 用 `daily_sync.bat` の Windows タスクスケジューラ登録を確認するよう変更
- `quickstart_postgres_timeseries.bat` 完了時に Windows タスクスケジューラ登録を確認するよう変更
- `install_tasks.ps1` で `daily_sync.bat` の DB 種別・日付窓・PostgreSQL 環境変数永続化を指定可能に変更

## [1.4.1] - 2026-06-08

### Fixed

- Windowsタスクからの日次同期で実行場所を正しく復元し、非対話更新の失敗を
  呼び出し元へ返すように修正

## [1.4.0] - 2026-05-03

### Added

- PostgreSQL 向け JRA-VAN 時系列オッズ取得導線を追加
  - `quickstart_postgres_timeseries.bat`
  - `fetch_timeseries_postgres.bat`
  - `daily_sync.bat`
- 公式1年保持の `0B41/0B42` を `TS_O1/TS_O2` に保存する導線を整理
- 開催週の速報オッズ `0B30` 系から `TS_O1`〜`TS_O6` を蓄積する導線を追加
- 展開済みオッズ行の直接保存と PostgreSQL 複数行 INSERT を追加
- JRA データコレクタ単体のアーキテクチャ / PostgreSQL / 時系列オッズ / スクリプトのドキュメントを追加

### Fixed

- JRA-VAN 時系列オッズキーの生成を修正
- 空欄・未発売系オッズ値を PostgreSQL 保存前に正規化
- O1〜O6 の展開済みパーサー出力をテスト側でも正しく扱うよう修正
- PostgreSQL 複数行 INSERT のプレースホルダ生成を修正

### Changed

- PostgreSQL 時系列オッズのクイックスタート名をデータコレクタ汎用名へ変更
  - 新しい名前: `quickstart_postgres_timeseries.bat`
- 古いスクリプト README を削除し、現行ドキュメントへ集約
- 公開ドキュメントから下流システム固有の表現と内部パス例を削除

## [1.3.0] - 2026-04-22

### Added

- **二重書き込みモード** を追加
  - SQLite を primary としつつ PostgreSQL へ同時書き込み
  - `src/database/dual_handler.py` を新設
- **PostgreSQL 移行支援** を追加
  - 既存 SQLite スキーマの PostgreSQL 側反映と移行経路を整備
- migration / dual-write 向けテストを追加
  - `tests/test_migration.py`

### Fixed

- DDL が dual-write 時に mirror 側へ確実に反映されない問題を修正
- realtime / verify 周辺の false positive とメッセージ不整合を修正
- batch importer / realtime updater の PostgreSQL 併用時の整合性を改善

### Changed

- CLI と database 初期化フローを dual-write / PostgreSQL mirror 前提で整理
- realtime monitor の DB 書き込み経路を見直し
- config example を PostgreSQL 併用前提に更新

## [1.2.0] - 2026-04-17

### ⚠️ Breaking Changes

- **地方競馬（NAR）サポートを廃止** — NAR/NV-Link 関連機能をすべて削除。本ツールは JRA（中央競馬）専用となります。

### Added

- レースデー監視ツール群
  - `scripts/raceday_verify.py` — 17項目の自動検証（スキーマ・RT_・NL_・オッズ・払戻・smoke test）
  - `scripts/raceday_scheduler.py` — 各レース後に自動検証を実行するスケジューラ（12R + 事後チェック）
  - `scripts/raceday_tmux.sh` — tmux 3ウィンドウ構成の一発起動スクリプト
- Claude Code `/loop` との連携 — 検証レポートを読んで問題があれば自動でコード修正・PR作成
- NL_SE / RT_SE インデックス追加（`idx_nl_se_date`, `idx_rt_se_date` など）
- テストカバレッジ大幅拡充（1,256件: 1,256 pass）
  - `test_cache_manager.py` — CacheManager 全API（NL_/RT_ 読み書き、インデックス、スレッドセーフ）
  - `test_utils_config.py` — Config.get、環境変数展開、バリデーション
  - `test_utils_lock_manager.py` — acquire/release、競合検出、stale lock 自動削除

### Fixed

- `quickstart.py`: `BatchProcessor` に削除済み `data_source` 引数を渡していたクラッシュを修正
- `raceday_verify.py`: `--date` 引数の長さ検証を追加
- `updater.py`: INSERT OR REPLACE で UPSERT が正常動作していたにもかかわらず誤解を招くTODOコメントを削除

### Changed

- `quickstart.bat`: `--option` を `--mode` に修正、S3キャッシュ同期ステップを追加
- `pyproject.toml`: pytest `--basetemp=C:/tmp/pytest-jrvl` 追加（Windows AppData 権限エラー対策）

### Documentation

- README.md を全面書き直し（要件・クイックスタート・CLI・レースデーワークフロー・キャッシュ構造）

## [1.1.0] - 2025-02-08

### Added
- ワンコマンドインストーラー (`install.ps1`) — `irm ... | iex` で一発セットアップ
- 自動アップデート機能 (`jltsql update`, `jltsql version --check`)
- H1/H6パーサーのフルストラクト対応（28,955 / 102,890バイト）
- quickstart.bat で JRA-VAN 契約ページの自動オープン
- テストカバレッジ大幅拡充（1,247件: 1,239 pass, 8 skip）
- JRA実データテストフィクスチャ（27パーサー, 81レコード）

### Changed
- 32-bit Python 必須に変更（64-bit非対応を明確化）

### Fixed
- H1/H6パーサーのフルストラクト解析の不具合修正
- テスト3件の失敗修正（wrapper挙動との整合性）

### Documentation
- Windows専用であることを明確化
- ワンコマンドインストーラーをREADMEに追加
- クロスプラットフォーム検証の注記追加
- 入門 / リファレンス / ユーザーガイドを最新仕様に更新

## [1.0.0] - 2025-02-07

### Added
- 初回公開リリース
- JRA-VAN DataLab (JV-Link) 対応 — 38種パーサー
- SQLite / PostgreSQL データベース対応
- リアルタイムオッズ・速報データ監視
- quickstart.py 対話形式セットアップウィザード
- CLI コマンド（fetch, status, monitor, init）

[Unreleased]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.10...HEAD
[1.6.10]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.9...v1.6.10
[1.6.9]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.8...v1.6.9
[1.6.8]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.7...v1.6.8
[1.6.7]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.6...v1.6.7
[1.6.6]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.5...v1.6.6
[1.6.5]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.4...v1.6.5
[1.6.4]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/miyamamoto/jrvltsql/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.6.0
[1.5.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.5.0
[1.4.1]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.4.1
[1.4.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.0.0
