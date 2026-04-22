# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-04-22

### Added

- **Dual-write mode** を追加
  - SQLite を primary としつつ PostgreSQL へ同時書き込み
  - `src/database/dual_handler.py` を新設
- **PostgreSQL migration support** を追加
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
- Getting Started / Reference / UserGuide を最新仕様に更新

## [1.0.0] - 2025-02-07

### Added
- 初回公開リリース
- JRA-VAN DataLab (JV-Link) 対応 — 38種パーサー
- SQLite / PostgreSQL データベース対応
- リアルタイムオッズ・速報データ監視
- quickstart.py 対話形式セットアップウィザード
- CLI コマンド（fetch, status, monitor, init）

[Unreleased]: https://github.com/miyamamoto/jrvltsql/compare/v1.2.0...HEAD
[1.3.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.0.0
