# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-02-08

### Added
- NV-Link（地方競馬DATA）対応 — NAR 3パーサー（HA, NU, NC）
- ワンコマンドインストーラー (`install.ps1`) — `irm ... | iex` で一発セットアップ
- 自動アップデート機能 (`jltsql update`, `jltsql version --check`)
- H1/H6パーサーのフルストラクト対応（28,955 / 102,900バイト）
- NAR -502エラーの自動リトライ（日付分割ダウンロード）
- quickstart.bat で JRA-VAN / 地方競馬DATA 契約ページの自動オープン
- テストカバレッジ大幅拡充（1,247件: 1,239 pass, 8 skip）
- JRA実データテストフィクスチャ（27パーサー, 81レコード）

### Changed
- 32-bit Python 必須に変更（64-bit非対応を明確化）
- NV-Link ダウンロード option=3 に変更
- NAR 認証キーを `"UNKNOWN"` に修正

### Fixed
- H1/H6パーサーのフルストラクト解析の不具合修正
- NV-Link -3 エラー説明の修正
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

[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/miyamamoto/jrvltsql/releases/tag/v1.0.0
