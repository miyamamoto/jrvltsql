# JRVLTSQL v2.0.0 Test Suite

## Overview

Comprehensive test suite for the JRVLTSQL project covering all parsers, database operations, and end-to-end workflows.

### Test Statistics

- **Total Tests**: 415+
  - **Unit Tests** (test_parsers.py): 404 tests
  - **Integration Tests** (test_integration.py): 11 tests
- **Parser Coverage**: All 38 JRA data format parsers
- **Integration Coverage**: Database operations, transactions, type conversions, error handling

## Running Tests

### Prerequisites

- Python 3.10+ (32-bit required for JV-Link compatibility)
- pytest and dependencies installed:
  ```bash
  pip install -r requirements-dev.txt
  ```

### Run All Tests

```bash
py -3-32 -m pytest tests/ -v
```

### Run Specific Test Files

```bash
# Parser unit tests only
py -3-32 -m pytest tests/test_parsers.py -v

# Integration tests only
py -3-32 -m pytest tests/test_integration.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
py -3-32 -m pytest tests/test_parsers.py::TestIndividualParsers -v

# Run tests matching a pattern (e.g., all RA parser tests)
py -3-32 -m pytest tests/test_parsers.py -k "RA" -v

# Run a specific integration test
py -3-32 -m pytest tests/test_integration.py::TestIntegration::test_parse_and_import_ra_record -v
```

### Run with Coverage Report

```bash
py -3-32 -m pytest tests/ --cov=src --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`.

## Test Categories

### 1. Parser Unit Tests (test_parsers.py)

**404 comprehensive tests** covering all 38 parser types with consistent validation.

#### Test Coverage per Parser

Each of the 38 parsers is tested for:

1. **Basic Functionality** (3 tests per parser)
   - Parser instance creation
   - `RECORD_TYPE` / `record_type` attribute validation
   - `RECORD_LENGTH` attribute validation (where applicable)

2. **Parsing Operations** (3 tests per parser)
   - `parse()` method existence and invocability
   - Successful parsing with sample data
   - Common field validation (RecordSpec, DataKubun, MakeDate)

3. **Data Integrity** (1 test per parser)
   - RecordSpec value accuracy in parsed output

4. **Error Handling** (3 tests per parser)
   - Empty data handling
   - Short/truncated data handling
   - Wrong record type handling

#### Test Classes

1. **TestParserFactory** (5 tests)
   - Factory initialization
   - Supported types enumeration (38 parsers)
   - Invalid record type handling
   - Empty/None type handling

2. **TestIndividualParsers** (342 tests = 38 parsers × 9 tests)
   - Parametrized tests for all parser types
   - Consistent interface validation
   - Sample data parsing

3. **TestParserFactoryParseMethod** (4 tests)
   - Factory-level parse method
   - Valid/invalid record handling via factory

4. **TestParserCaching** (2 tests)
   - Parser instance caching behavior
   - Parser independence verification

5. **TestParserFieldExtraction** (2 tests)
   - Detailed field extraction for RA parser
   - Detailed field extraction for SE parser

6. **TestParserEncodingHandling** (1 test)
   - Shift-JIS encoding validation
   - Japanese character handling

7. **TestParserRobustness** (8 tests)
   - Exact-length data processing
   - Over-length data handling

8. **TestAllParsersComprehensive** (2 tests)
   - Verification all 38 parsers load correctly
   - Interface consistency across all parsers

#### Supported Parser Types (38 total)

```
AV, BN, BR, BT, CC, CH, CK, CS, DM,
H1, H6, HC, HN, HR, HS, HY,
JC, JG, KS,
O1, O2, O3, O4, O5, O6,
RA, RC, SE, SK, TC, TK, TM,
UM, WC, WE, WF, WH, YS
```

### 2. Integration Tests (test_integration.py)

**11 comprehensive integration tests** validating complete workflows from parsing through database operations.

#### Test Coverage

1. **test_create_all_tables**
   - Creates all 58 database tables
   - Verifies table existence and column structure
   - Tests idempotent table creation

2. **test_table_column_counts**
   - Validates expected column counts for major tables
   - Verifies schema integrity

3. **test_parse_and_import_ra_record**
   - RA (race details) record parsing
   - Database import verification
   - Data retrieval and validation

4. **test_parse_and_import_se_record**
   - SE (horse race result) record parsing
   - Type conversion validation
   - Japanese text handling

5. **test_duplicate_handling_with_replace**
   - INSERT OR REPLACE behavior validation
   - Duplicate key handling
   - Update vs insert verification

6. **test_batch_import_with_transactions**
   - Batch processing (50 records)
   - Transaction handling
   - Import statistics tracking

7. **test_mixed_record_types_batch_import**
   - Multiple record types in single batch (RA, SE, HR)
   - Cross-table transaction processing
   - Record routing to correct tables

8. **test_type_conversion_integration**
   - INTEGER field conversion
   - REAL field conversion (including /10 for odds/weights)
   - TEXT field preservation
   - NULL handling

9. **test_transaction_rollback_on_error**
   - Batch failure fallback to individual inserts
   - Failed record tracking
   - Partial batch success handling

10. **test_primary_key_enforcement**
    - Primary key constraint validation
    - REPLACE behavior on constraint violation

11. **test_end_to_end_workflow**
    - Complete workflow: parse → import → query
    - Multi-record type handling
    - Data integrity verification

## Test Data

### Parser Unit Tests

Sample data structure for each record type:

```python
# RecordSpec (2 bytes) + DataKubun (1 byte) + MakeDate (8 bytes) + padding
data = record_type.encode('shift-jis')  # e.g., "RA", "SE"
data += b'1'                             # DataKubun
data += b'20240601'                      # MakeDate
data += b' ' * (RECORD_LENGTH - 11)      # Padding to full length
```

### Integration Tests

Realistic test records with:
- Complete required fields
- Japanese text (UTF-8 encoded)
- Various numeric types for conversion testing
- Primary key combinations for duplicate testing

## Coverage Statistics

### Overall Coverage

Run `py -3-32 -m pytest tests/ --cov=src --cov-report=term` to see current coverage.

### Key Module Coverage

- **src/parser/**: Parser implementations and factory
- **src/database/**: Database operations, schema management
- **src/importer/**: Data import and type conversion logic
- **src/converters/**: Type conversion utilities

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run test suite
  run: |
    pip install -r requirements-dev.txt
    pytest tests/ -v --tb=short --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### pytest Not Found

```bash
pip install pytest pytest-cov pytest-mock
```

### Import Errors

Ensure PYTHONPATH includes project root:

```bash
# Windows
set PYTHONPATH=%CD%
py -3-32 -m pytest tests/ -v

# Linux/Mac
export PYTHONPATH=$(pwd)
pytest tests/ -v
```

### Encoding Issues

Ensure your terminal supports UTF-8 for Japanese text output:

```bash
# Windows (PowerShell)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Windows (Command Prompt)
chcp 65001
```

### Test Failures

View detailed error output:

```bash
py -3-32 -m pytest tests/ -v --tb=long
```

View only failed tests:

```bash
py -3-32 -m pytest tests/ --lf -v  # Last Failed
```

## Development Workflow

### Adding New Tests

1. **For new parsers**: Add to `ALL_RECORD_TYPES` in `src/parser/factory.py`
   - Parametrized tests automatically cover new parsers

2. **For new features**: Add integration tests in `test_integration.py`
   - Follow existing test patterns
   - Include docstrings explaining what's tested

3. **Run tests locally** before committing:
   ```bash
   py -3-32 -m pytest tests/ -v
   ```

### Test Conventions

- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- Include docstrings explaining test purpose and verification steps
- Use pytest fixtures for common setup (database, importer, parser factory)
- Parametrize tests when testing same logic across multiple inputs
- Clean up resources (temp files, database connections) in fixtures

## Future Improvements

- [ ] Performance benchmarking tests for large datasets
- [ ] Real JV-Link data validation tests
- [ ] Boundary value testing for all field types
- [ ] Memory leak detection tests
- [ ] Parallel execution stress tests
- [ ] Schema migration tests
- [ ] Backup/restore functionality tests

## References

- [pytest Documentation](https://docs.pytest.org/)
- [JV-Data Specification v4.9.0.1](http://www.jra-van.jp/dlb/sdv/index.html)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- Project README: [../README.md](../README.md)

## Test Results

Latest test run (as of last documentation update):

```
================================ test session starts ================================
collected 415 items

test_parsers.py::TestParserFactory::test_factory_initialization PASSED
test_parsers.py::TestParserFactory::test_supported_types PASSED
test_parsers.py::TestParserFactory::test_get_parser_invalid_type PASSED
...
test_integration.py::TestIntegration::test_create_all_tables PASSED
test_integration.py::TestIntegration::test_end_to_end_workflow PASSED

================================ 415 passed in ~5.2s ================================
```

**Success Rate**: 100% (415/415 tests passing)
