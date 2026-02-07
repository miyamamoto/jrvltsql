# Implementation Plan: 地方競馬データ対応（UmaConn連携）

**Branch**: `001-local-racing-support` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-local-racing-support/spec.md`

## Summary

地方競馬DATA（UmaConn）に対応し、既存のJRA-VAN向け実装を最大限再利用しながら、NVLinkWrapperクラスの追加とCLIオプション（`--source nar`）の拡張を行う。JV-Link APIとUmaConn APIは「JV」→「NV」の置換で対応可能であり、既存の38種パーサーもそのまま再利用できる。

## Technical Context

**Language/Version**: Python 3.12 (32-bit) (REQUIRED for UmaConn/NAR support)
**Primary Dependencies**: pywin32 (COM API), click (CLI), rich (UI), structlog (logging), pandas
**Storage**: SQLite (32-bit compatible, default and recommended)
**Testing**: pytest with pytest-cov
**Target Platform**: Windows 10/11 (COM API requirement)
**Project Type**: Single project (CLI tool)
**Performance Goals**: 5,000 records/sec (database insert), 10,000 records/sec (parsing)
**Constraints**: <500MB memory, 4Hz UI refresh, batch operations (1000+ records/transaction)
**Scale/Scope**: 64 tables (JRA), 64 tables (NAR - new), millions of records

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality ✅

| Gate | Status | Notes |
|------|--------|-------|
| Type hints for all functions | ✅ PASS | Existing pattern in wrapper.py will be followed |
| Error handling for external API calls | ✅ PASS | NVLinkWrapper will follow JVLinkWrapper pattern |
| DRY principle | ✅ PASS | Base class/protocol for JV/NV wrappers |
| Single responsibility | ✅ PASS | Separate nvlink/ module |
| Naming conventions | ✅ PASS | NV prefix for NAR, consistent with JV |
| Documentation | ✅ PASS | Docstrings per JVLinkWrapper pattern |

### II. Testing Standards ✅

| Gate | Status | Notes |
|------|--------|-------|
| Database operations tests | ✅ PASS | NAR tables follow same pattern |
| Parser tests | ✅ PASS | Reuse existing parser tests |
| CLI integration tests | ✅ PASS | Add `--source` option tests |
| Error path tests | ✅ PASS | UmaConn unavailable case |
| Test isolation | ✅ PASS | Mock NVLink COM API |

### III. User Experience Consistency ✅

| Gate | Status | Notes |
|------|--------|-------|
| Progress indication | ✅ PASS | Reuse existing progress system |
| Error messages | ✅ PASS | Clear UmaConn-specific messages |
| Confirmation prompts | ✅ PASS | Same pattern as JRA |
| Output formats | ✅ PASS | Human + JSON output |
| Help text in Japanese | ✅ PASS | `--source` option help |
| Exit codes | ✅ PASS | Standard codes |

### IV. Performance Requirements ✅

| Gate | Status | Notes |
|------|--------|-------|
| Batch processing | ✅ PASS | Same batch importer |
| Memory efficiency | ✅ PASS | Same streaming approach |
| Progress updates 4Hz | ✅ PASS | Existing implementation |
| Index strategy | ✅ PASS | Same indexes for NAR tables |

## Project Structure

### Documentation (this feature)

```text
specs/001-local-racing-support/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── main.py              # Add --source option to commands
│   └── commands/
├── database/
│   ├── schema.py            # Add NAR table schemas
│   ├── schema_nar.py        # NEW: NAR-specific schema definitions
│   └── table_mappings.py    # Add NAR table mappings
├── fetcher/
│   ├── base.py              # Abstract base for JV/NV fetchers
│   ├── historical.py        # Modify to support DataSource
│   └── realtime.py          # Modify to support DataSource
├── importer/
│   └── importer.py          # Add NAR table name generation
├── jvlink/
│   ├── wrapper.py           # Existing JV-Link wrapper
│   └── constants.py         # JRA track codes
├── nvlink/                   # NEW: UmaConn module
│   ├── __init__.py
│   ├── wrapper.py           # NVLinkWrapper (mirrors JVLinkWrapper)
│   └── constants.py         # NAR track codes (30-51)
├── parser/                   # REUSE: All 38 parsers unchanged
└── utils/
    └── data_source.py       # NEW: DataSource enum (JRA, NAR, ALL)

tests/
├── unit/
│   └── test_nvlink_wrapper.py  # NEW
├── integration/
│   └── test_nar_import.py      # NEW
└── contract/
```

**Structure Decision**: Single project structure. Add `nvlink/` module parallel to `jvlink/`, and `utils/data_source.py` for DataSource enum. Minimal changes to existing code; mostly additive.

## Complexity Tracking

> No violations. Design follows existing patterns with minimal additions.

| Aspect | Approach | Justification |
|--------|----------|---------------|
| API Wrapper | Separate NVLinkWrapper | Mirrors JVLinkWrapper; same interface |
| Schema | NAR tables with _NAR suffix | Clear separation; same schema |
| CLI | --source option | Backward compatible; JRA default |
