"""Integration tests with real JV-Link data.

These tests fetch actual data from JV-Link API and verify the full workflow:
Fetch -> Parse -> Import -> Verify

Requirements:
- JV-Link must be installed on Windows
- Service key must be configured in JRA-VAN DataLab application
- JV-Link service must be running

Usage:
    # Configure service key in JRA-VAN DataLab application first
    # Then run integration tests
    pytest tests/integration/test_jvlink_real.py -v
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.database.schema import SchemaManager
from src.database.sqlite_handler import SQLiteDatabase
from src.fetcher.historical import HistoricalFetcher
from src.importer.batch import BatchProcessor


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "integration_test.db"
        db = SQLiteDatabase({"path": str(db_path)})
        yield db


class TestJVLinkRealDataFetching:
    """Integration tests with real JV-Link data.

    Note: Service key must be configured in JRA-VAN DataLab application.
    """

    def test_jvlink_connection(self):
        """Test JV-Link connection and initialization."""
        fetcher = HistoricalFetcher()

        # Test initialization
        assert fetcher.jvlink is not None
        assert fetcher.parser_factory is not None

        # Test JV-Link initialization
        try:
            fetcher.jvlink.jv_init()
            print("\n✓ JV-Link initialization successful")
        except Exception as e:
            pytest.fail(f"JV-Link initialization failed: {e}")

    def test_fetch_small_data_sample(self):
        """Test fetching a small sample of real data.

        Fetches 1 day of RACE data from recent past.
        """
        fetcher = HistoricalFetcher()

        # Use a recent date (7 days ago to ensure data is available)
        target_date = datetime.now() - timedelta(days=7)
        from_date = target_date.strftime("%Y%m%d")
        to_date = from_date  # Same day

        print(f"\n=== Fetching RACE data for {from_date} ===")

        # Fetch data
        records = []
        record_types = {}

        try:
            for record in fetcher.fetch("RACE", from_date, to_date):
                records.append(record)

                # Track record types
                rec_type = record.get("RecordSpec") or record.get("headRecordSpec", "Unknown")
                record_types[rec_type] = record_types.get(rec_type, 0) + 1

                # Limit to 100 records for quick test
                if len(records) >= 100:
                    break

            # Print statistics
            stats = fetcher.get_statistics()
            print(f"\n--- Fetcher Statistics ---")
            print(f"Records fetched: {stats['records_fetched']}")
            print(f"Records parsed:  {stats['records_parsed']}")
            print(f"Records failed:  {stats['records_failed']}")

            print(f"\n--- Record Types Found ---")
            for rec_type, count in sorted(record_types.items()):
                print(f"{rec_type}: {count} records")

            # Verify we got some data
            assert len(records) > 0, "No records were fetched"
            assert stats["records_parsed"] > 0, "No records were parsed"

            # Show sample record
            if records:
                print(f"\n--- Sample Record (Type: {records[0].get('RecordSpec') or records[0].get('headRecordSpec')}) ---")
                for key, value in list(records[0].items())[:10]:
                    print(f"{key}: {value}")
                print("... (truncated)")

        except Exception as e:
            pytest.fail(f"Failed to fetch data: {e}")

    def test_full_workflow_with_real_data(self, temp_db):
        """Test complete workflow: Fetch -> Parse -> Import -> Verify.

        This is the most comprehensive integration test.
        """
        print("\n=== Full Workflow Integration Test ===")

        # Use recent date
        target_date = datetime.now() - timedelta(days=7)
        from_date = target_date.strftime("%Y%m%d")
        to_date = from_date

        print(f"Date range: {from_date} - {to_date}")

        with temp_db:
            # Create batch processor
            processor = BatchProcessor(
                database=temp_db,
                batch_size=50,  # Smaller batch for testing
            )

            # Process data
            print("\nProcessing data...")
            try:
                stats = processor.process_date_range(
                    data_spec="RACE",
                    from_date=from_date,
                    to_date=to_date,
                    auto_commit=True,
                    ensure_tables=True,
                )

                # Print results
                print("\n--- Processing Statistics ---")
                print(f"Records fetched:  {stats.get('records_fetched', 0)}")
                print(f"Records parsed:   {stats.get('records_parsed', 0)}")
                print(f"Records imported: {stats.get('records_imported', 0)}")
                print(f"Records failed:   {stats.get('records_failed', 0)}")
                print(f"Batches processed: {stats.get('batches_processed', 0)}")

                # Verify data was imported
                assert stats.get("records_imported", 0) > 0, "No records were imported"

                # Verify database content
                print("\n--- Database Verification ---")

                # Check NL_RA table
                ra_count = temp_db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM NL_RA"
                )
                print(f"NL_RA records: {ra_count['cnt']}")

                # Check NL_SE table
                se_count = temp_db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM NL_SE"
                )
                print(f"NL_SE records: {se_count['cnt']}")

                # Check NL_H1 table
                h1_count = temp_db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM NL_H1"
                )
                print(f"NL_H1 records: {h1_count['cnt']}")

                # Get sample race data
                if ra_count['cnt'] > 0:
                    sample_race = temp_db.fetch_one(
                        "SELECT * FROM NL_RA LIMIT 1"
                    )
                    print("\n--- Sample Race Record ---")
                    print(f"Year: {sample_race.get('Year')}")
                    print(f"Race Number: {sample_race.get('RaceNum')}")
                    print(f"Race Name: {sample_race.get('Hondai')}")
                    print(f"Distance: {sample_race.get('Kyori')}")
                    print(f"Track Code: {sample_race.get('JyoCD')}")

                # Verify core race tables have data (NL_H1 may be empty same-day)
                total_db_records = ra_count['cnt'] + se_count['cnt'] + h1_count['cnt']
                print(f"\nTotal records in DB: {total_db_records}")

                assert ra_count['cnt'] > 0, "No NL_RA records in database"
                assert se_count['cnt'] > 0, "No NL_SE records in database"

                print("\n✓ Full workflow test PASSED")

            except Exception as e:
                pytest.fail(f"Full workflow test failed: {e}")

    def test_parser_with_real_data_formats(self):
        """Test that parsers handle real data formats correctly.

        Fetches real data and verifies all expected fields are parsed.
        """
        fetcher = HistoricalFetcher()

        target_date = datetime.now() - timedelta(days=7)
        from_date = target_date.strftime("%Y%m%d")
        to_date = from_date

        print(f"\n=== Testing Parser Field Coverage ===")

        field_coverage = {}

        try:
            record_count = 0
            for record in fetcher.fetch("RACE", from_date, to_date):
                rec_type = record.get("RecordSpec") or record.get("headRecordSpec")

                if rec_type not in field_coverage:
                    field_coverage[rec_type] = {
                        "count": 0,
                        "fields": set(record.keys()),
                        "sample": record,
                    }

                field_coverage[rec_type]["count"] += 1
                field_coverage[rec_type]["fields"].update(record.keys())

                record_count += 1
                if record_count >= 50:
                    break

            # Print coverage report
            print("\n--- Parser Field Coverage Report ---")
            for rec_type, info in sorted(field_coverage.items()):
                print(f"\nRecord Type: {rec_type}")
                print(f"  Records processed: {info['count']}")
                print(f"  Unique fields found: {len(info['fields'])}")
                print(f"  Fields: {', '.join(sorted(list(info['fields']))[:10])}...")

                # Verify required header fields (parsers use RecordSpec/DataKubun/MakeDate)
                required_headers = [
                    ("RecordSpec", "headRecordSpec"),
                    ("DataKubun", "headDataKubun"),
                    ("MakeDate", "headMakeDate"),
                ]
                for primary, fallback in required_headers:
                    assert primary in info["fields"] or fallback in info["fields"], \
                        f"Required field '{primary}' not found in {rec_type} records"

            print("\n✓ Parser field coverage test PASSED")

        except Exception as e:
            pytest.fail(f"Parser field coverage test failed: {e}")


class TestJVLinkErrorHandling:
    """Test error handling with real JV-Link API."""

    def test_invalid_date_range(self):
        """Test handling of invalid date ranges."""
        fetcher = HistoricalFetcher()

        # Try to fetch data with invalid date format
        with pytest.raises(Exception):
            list(fetcher.fetch("RACE", "invalid", "invalid"))

    def test_future_date_handling(self):
        """Test fetching data for future dates."""
        fetcher = HistoricalFetcher()

        # Future date (1 year from now)
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y%m%d")

        # Should return no data (not an error)
        records = list(fetcher.fetch("RACE", future_date, future_date))

        print(f"\nFuture date ({future_date}) returned {len(records)} records (expected 0)")
        assert len(records) == 0, "Future date should return no records"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
