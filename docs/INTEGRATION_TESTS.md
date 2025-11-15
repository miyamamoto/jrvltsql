# Integration Testing with Real JV-Link Data

This document describes the integration testing framework for JLTSQL, which tests the complete workflow using **real JV-Link API data**.

## Overview

Unlike unit tests that use mocks, integration tests:
- Connect to actual JV-Link API
- Fetch real horse racing data from JRA-VAN
- Parse actual JV-Data fixed-length format
- Import data to real SQLite database
- Verify data integrity end-to-end

## Quick Start

### Option 1: Interactive Helper Script (Recommended)

```bash
python run_integration_tests.py
```

This script will:
1. Prompt you for your JV-Link service key (if not set)
2. Show you a menu of available tests
3. Run your selected test with detailed output

### Option 2: Manual Test Execution

```bash
# Set your service key
export JVLINK_SERVICE_KEY="YOUR_KEY_HERE"

# Run all integration tests
pytest tests/integration/ -v -s

# Run specific test
pytest tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_full_workflow_with_real_data -v -s
```

## Available Tests

### 1. Connection Test
```bash
pytest tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_jvlink_connection -v -s
```
- Verifies JV-Link COM object initialization
- Tests JV-Link API connection
- **Duration**: ~5 seconds

### 2. Small Data Sample Test
```bash
pytest tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_fetch_small_data_sample -v -s
```
- Fetches ~100 records from 7 days ago
- Tests data fetching and parsing
- Shows statistics and sample records
- **Duration**: ~30 seconds

### 3. Full Workflow Test (Most Comprehensive)
```bash
pytest tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_full_workflow_with_real_data -v -s
```
- Complete workflow: Fetch → Parse → Import → Verify
- Creates temporary SQLite database
- Imports real data to database
- Verifies data integrity
- Shows detailed statistics
- **Duration**: ~60 seconds

### 4. Parser Field Coverage Test
```bash
pytest tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_parser_with_real_data_formats -v -s
```
- Analyzes real JV-Data format
- Verifies all expected fields are parsed
- Shows field coverage report
- **Duration**: ~30 seconds

### 5. Error Handling Tests
```bash
pytest tests/integration/test_jvlink_real.py::TestJVLinkErrorHandling -v -s
```
- Tests invalid date ranges
- Tests future date handling
- Verifies error recovery
- **Duration**: ~15 seconds

## What Gets Verified

### Data Fetching
- ✓ JV-Link API connection
- ✓ JVOpen() data stream initialization
- ✓ JVRead() record reading
- ✓ Proper stream cleanup

### Data Parsing
- ✓ Shift_JIS encoding handling
- ✓ Fixed-length format parsing
- ✓ Record type detection (RA, SE, HR)
- ✓ Field extraction accuracy
- ✓ Header field parsing (headRecordSpec, headDataKubun, headMakeDate)

### Data Import
- ✓ Automatic table creation
- ✓ Batch processing (50-1000 records/batch)
- ✓ Record type to table mapping
- ✓ Transaction management
- ✓ Error recovery (batch → individual insert fallback)

### Data Integrity
- ✓ Record counts match (fetched = imported)
- ✓ Primary key constraints
- ✓ Field data types
- ✓ Japanese text encoding (UTF-8 in DB)
- ✓ Sample data verification

## Expected Output Example

When running the full workflow test with a valid service key:

```
=== Full Workflow Integration Test ===
Date range: 20241107 - 20241107

Processing data...

--- Processing Statistics ---
Records fetched:  150
Records parsed:   150
Records imported: 150
Records failed:   0
Batches processed: 3

--- Database Verification ---
NL_RA_RACE records: 15
NL_SE_RACE_UMA records: 120
NL_HR_PAY records: 15

--- Sample Race Record ---
Year: 2024
Race Number: 01
Race Name: 新馬
Distance: 1200
Track Code: 05

Total records in DB: 150

✓ Full workflow test PASSED
```

## Requirements

### System Requirements
- Windows OS (JV-Link is Windows-only)
- JV-Link installed and registered
- Python 3.9+

### JRA-VAN Requirements
- Active JRA-VAN DataLab subscription (月額2,090円)
- Valid service key

### Python Dependencies
All dependencies are already installed if you've set up the project:
- pywin32 (Windows COM interface)
- pytest (testing framework)
- structlog (logging)
- All JLTSQL modules (database, parser, fetcher, importer)

## Troubleshooting

### Service Key Issues

**Problem**: "JVLINK_SERVICE_KEY not set - skipping integration tests"
```bash
# Solution: Set environment variable
export JVLINK_SERVICE_KEY="YOUR_KEY"

# Or use the helper script
python run_integration_tests.py
```

### JV-Link Connection Issues

**Problem**: "JV-Link initialization failed"
```bash
# Verify JV-Link is installed
python -c "import win32com.client; print(win32com.client.Dispatch('JVDTLab.JVLink'))"

# Should output: <COMObject JVDTLab.JVLink>
```

**Problem**: "No records were fetched"
- Check internet connection
- Verify JRA-VAN subscription is active
- Try different date range (data may not be available for all dates)
- Check JV-Link service status

### Import Errors

**Problem**: "ModuleNotFoundError: No module named 'structlog'"
```bash
# Install missing dependencies
pip install structlog click rich tenacity python-dateutil pyyaml
```

## Test Data Source

Integration tests use real data from **7 days ago** by default:
- Ensures data is available (recent races)
- Avoids future dates (no data)
- Avoids very old dates (may require special options)

You can modify the date in the test code if needed:
```python
target_date = datetime.now() - timedelta(days=7)  # Change days value
```

## Performance Notes

- **Small sample test**: Fetches up to 100 records (~30 seconds)
- **Full workflow test**: Fetches all data for 1 day (~60 seconds)
- **Batch size**: 50 records/batch for tests (production uses 1000)
- **Database**: Uses temporary SQLite file (auto-cleaned)

## Safety Features

- Tests use temporary databases (no data loss risk)
- Service key only stored in environment (not in code)
- Tests skip gracefully if service key not available
- No destructive operations on production data
- All database operations are in transactions

## Next Steps

After running integration tests successfully:

1. **Review test output** for any parsing issues
2. **Check database records** to verify data accuracy
3. **Adjust parsers** if field formats differ from specification
4. **Increase batch size** for production use (1000+ records)
5. **Test with different data specifications** (RACE, DIFF, O1-O6)
6. **Test date ranges** (months, years)

## Documentation

- Integration test code: `tests/integration/test_jvlink_real.py`
- Integration test README: `tests/integration/README.md`
- Helper script: `run_integration_tests.py`
- This document: `INTEGRATION_TESTS.md`
