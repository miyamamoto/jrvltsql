# 変更履歴

このプロジェクトの主な変更点をこのファイルに記録します。

形式は [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) を参考にし、
バージョン番号は [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

## [Unreleased]

### Added

- JVOpen/JVRTOpen の対応データ種別、レコード種別、保存先テーブル、運用コマンドをまとめた `docs/data_support.md` を追加

### Changed

- 公開ドキュメントを日本語表記へ統一
- `quickstart.bat` は SQLite 既定の通常セットアップに戻し、PostgreSQL 専用の `quickstart_postgres_timeseries.bat` 呼び出しを削除
- SQLite でも `quickstart.bat --yes --include-timeseries` または `jltsql realtime odds-timeseries --db sqlite` で公式 `TS_O1/TS_O2` を保存できることを明記
- `quickstart.bat` 完了時に SQLite 用 `daily_sync.bat` の Windows タスクスケジューラ登録を確認するよう変更
- `quickstart_postgres_timeseries.bat` 完了時に Windows タスクスケジューラ登録を確認するよう変更
- `install_tasks.ps1` で `daily_sync.bat` の DB 種別・日付窓・PostgreSQL 環境変数永続化を指定可能に変更

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
- H1/H6パーサーのフルストラクト対応（28,955 / 102,900バイト）
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

[Unreleased]: https://github.com/miyamamoto/jrvltsql/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.0.0
