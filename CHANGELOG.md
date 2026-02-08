# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-08

### Added
- **41パーサー** (38 JRA + 3 NAR専用: NC, NU, HA) によるフルデータパース
- **NV-Link (地方競馬) 対応** — ParentHWnd修正、NVOpen修正、-502リトライ、COM再起動 (#25)
- **NAR日付分割ダウンロード** — 1日ずつチャンクで-502エラー回避 (#26)
- **JRA実データテストフィクスチャ** — 27パーサー、114テスト (#28)
- **NCパーサー** (NAR競馬場マスタ) 実装 (#19)
- **HAパーサー** (NAR払戻データ) 実装 (#4)
- NV-Link ダウンロード手順と-502リトライ戦略ドキュメント (#17)
- SQLite + PostgreSQL 対応
- JV-Link によるリアルタイムデータ取得
- Quickstart ウィザード
- CLI コマンド（データ管理・セットアップ）
- 384+ テスト

### Changed
- README.md を最新状態に更新 (#22)
- Getting Started ドキュメント更新 (#23)
- Reference / User Guide / Troubleshooting ドキュメント更新 (#24)
- pyproject.toml メタデータ更新 (#10)
- README再構成 — JRAセットアップ追加、技術詳細を別ファイルに分離 (#9)
- 32-bit Python 必須に変更、64-bit 非推奨 (#14)
- NARでもoption=1を使用（kmy-keiba準拠）(#25)

### Fixed
- NAR認証キー修正、OAマッピング追加 (#16)
- NV-Link -3エラーコード説明修正 (#18)
- クロスプラットフォームテスト互換性 (#7)
- テスト警告解消 (PytestReturnNotNoneWarning) (#12)
- コードクリーンアップ — 未使用変数・f-string・関数再定義の修正 (#8)
- コード品質改善 (#5)
- NV-Link初期化とエラーハンドリング (#3)

### Removed
- 不要ファイル整理・削除 (#30)
- DuckDB サポート (32-bit Python非互換)

## [2.2.0] - 2025-12-21

### Removed
- DuckDB support removed due to incompatibility with 32-bit Python environment

### Changed
- Standardized on SQLite for 32-bit Python compatibility with UmaConn (NAR)

## [2.1.0] - 2025-12-06

### Added
- NL_HR schema: HenkanDoWaku5-8 columns for complete refund slot coverage

### Fixed
- Primary key detection via `PRAGMA table_info()` for proper conflict resolution
- Rollback error handling: Log warnings instead of silent failures

## [2.0.10] - 2025-12-06

### Added
- Time-series odds: Custom period selection for historical odds data

## [2.0.4] - 2025-12-05

### Added
- Initial public release
- SQLite and PostgreSQL database support
- JV-Link integration for real-time data fetching
- Quickstart wizard for easy setup
- CLI commands for data management

[1.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v2.2.0...v1.1.0
[2.2.0]: https://github.com/miyamamoto/jrvltsql/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/miyamamoto/jrvltsql/compare/v2.0.10...v2.1.0
[2.0.10]: https://github.com/miyamamoto/jrvltsql/compare/v2.0.4...v2.0.10
[2.0.4]: https://github.com/miyamamoto/jrvltsql/releases/tag/v2.0.4
