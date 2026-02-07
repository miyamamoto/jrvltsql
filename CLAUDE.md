# jrvltsql Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-27

## Active Technologies

- **Python 3.12+ (32-bit)** + pywin32 (COM API), click (CLI), rich (UI), structlog (logging), SQLite/PostgreSQL (database)

## Project Structure

```text
src/
tests/
```

## Commands

pytest; ruff check src/

## Code Style

Python 3.12+: Follow standard conventions

## Architecture Constraints

### Python Version: 32-bit (Recommended)

- **32-bit Python を推奨** - JV-Link/NV-Link COM API へのネイティブアクセスに必要
- 64-bit Python は DLL Surrogate が必要で、PC-keiba 等の他アプリに影響を与えるため非推奨
- **Minimum Version**: Python 3.12

### Database: SQLite / PostgreSQL

- **SQLite** (default): 軽量、シングルユーザー向け
- **PostgreSQL**: pg8000 ドライバ経由、マルチユーザー/サーバー向け

### COM API

- **JV-Link** (JRA): ProgID = `JVDTLab.JVLink`
- **NV-Link** (NAR): ProgID = `NVDTLabLib.NVLink` (注: NVDTLab ではなく NVDTLabLib)

## Recent Changes

- 32-bit Python を標準として採用 (2025-12-27)
- 64-bit + DLL Surrogate は他アプリへの影響があるため非推奨に変更
- SQLite/PostgreSQL をサポート

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
