# jrvltsql Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-15

## Active Technologies

- **Python 3.12+** (32-bit or 64-bit) + pywin32 (COM API), click (CLI), rich (UI), structlog (logging), SQLite/PostgreSQL/DuckDB (database)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.12+: Follow standard conventions

## Architecture Constraints

### Database: SQLite / PostgreSQL / DuckDB

- SQLite provides stable, lightweight database solution (default)
- PostgreSQL supported via pg8000 driver (pure Python)
- DuckDB supported (64-bit Python only, high-performance analytics)

### Python Version: 32-bit or 64-bit

- **32-bit Python**: Native COM access to JV-Link/NV-Link
- **64-bit Python**: Requires DLL Surrogate registry settings (see `scripts/check_dll_surrogate.py`)
- **NV-Link Note**: Must remove `RunAs` registry value that conflicts with DllSurrogate
- **Minimum Version**: Python 3.12
- **Compatibility**: Works with both JV-Link (JRA) and UmaConn/NV-Link (NAR)

## Recent Changes

- 64-bit Python support restored via DLL Surrogate (2025-12-26)
- DuckDB support restored for 64-bit Python
- SQLite (default), PostgreSQL, and DuckDB all supported

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
