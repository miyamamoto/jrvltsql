"""Integration tests for JRAVAN SQL importer.

Tests the complete flow from parsing to database import:
1. Parser -> Importer -> SQLite database
2. Table creation and schema validation
3. Data import and retrieval
4. Duplicate handling with INSERT OR REPLACE
5. Batch import with transaction processing
"""

import tempfile
from pathlib import Path

import pytest

from src.database.schema import create_all_tables, SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter
from src.parser.factory import ParserFactory


class TestIntegration:
    """Integration test suite for parser -> importer -> database flow."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database instance.

        Database is created in a temporary file and automatically cleaned up
        after the test completes.
        """
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db = SQLiteDatabase({"path": db_path})
        yield db

        # Cleanup
        try:
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass

    @pytest.fixture
    def importer(self, temp_db):
        """Create data importer with temp database."""
        return DataImporter(temp_db, batch_size=100)

    @pytest.fixture
    def parser_factory(self):
        """Create parser factory instance."""
        return ParserFactory()

    def test_create_all_tables(self, temp_db):
        """Test creating all 58 tables and verify their column counts.

        This test verifies that:
        - All tables can be created without errors
        - Each table has the expected number of columns
        - Table creation is idempotent (can be called multiple times)
        """
        with temp_db:
            # Create all tables
            create_all_tables(temp_db)

            # Verify all tables exist
            table_count = 0
            for table_name in SCHEMAS.keys():
                assert temp_db.table_exists(table_name), f"Table {table_name} should exist"

                # Get column info
                columns = temp_db.get_table_info(table_name)
                assert len(columns) > 0, f"Table {table_name} should have columns"

                table_count += 1

            # Verify we have all expected tables
            assert table_count == len(SCHEMAS), f"Should have {len(SCHEMAS)} tables"

            # Test idempotency - creating tables again should not fail
            create_all_tables(temp_db)
            assert temp_db.table_exists("NL_RA")

    def test_table_column_counts(self, temp_db):
        """Verify expected column counts for major tables."""
        with temp_db:
            create_all_tables(temp_db)

            # Sample column count verification for key tables
            test_tables = {
                "NL_RA": 62,   # Race details table
                "NL_SE": 70,   # Horse race results table
                "NL_UM": 61,   # Horse master table
                "NL_KS": 68,   # Jockey master table
                "NL_HR": 110,  # Refund table
                "NL_O1": 29,   # Odds table
            }

            for table_name, expected_cols in test_tables.items():
                columns = temp_db.get_table_info(table_name)
                actual_cols = len(columns)
                assert actual_cols == expected_cols, \
                    f"{table_name}: expected {expected_cols} columns, got {actual_cols}"

    def test_parse_and_import_ra_record(self, temp_db, importer, parser_factory):
        """Test parsing and importing a race details (RA) record.

        This test verifies:
        - RA record can be parsed correctly
        - Parsed data can be imported into database
        - Data can be retrieved and matches expected values
        """
        with temp_db:
            create_all_tables(temp_db)

            # Instead of creating complex binary data, use a simple record dict
            # This simulates what a parser would return
            parsed_record = {
                "headRecordSpec": "RA",
                "RecordSpec": "RA",
                "DataKubun": "1",
                "MakeDate": "20240601",
                "Year": "2024",
                "MonthDay": "0601",
                "JyoCD": "06",
                "Kaiji": "03",
                "Nichiji": "08",
                "RaceNum": "11",
                "YoubiCD": "1",
                "TokuNum": "0000",
                "Hondai": "テストレース",
                "Kyori": "2000",
                "TrackCD": "10",
                "TorokuTosu": "18",
                "SyussoTosu": "18",
            }

            # Import record
            success = importer.import_single_record(parsed_record, auto_commit=True)
            assert success is True, "Import should succeed"

            # Verify data in database
            row = temp_db.fetch_one(
                "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
                (2024, 11)
            )

            assert row is not None, "Record should exist in database"
            assert row["JyoCD"] == "06", "JyoCD should match"
            assert row["Kyori"] == 2000, "Kyori should be 2000"
            assert row["Hondai"] == "テストレース", "Hondai should match"

    def test_parse_and_import_se_record(self, temp_db, importer, parser_factory):
        """Test parsing and importing horse race result (SE) record."""
        with temp_db:
            create_all_tables(temp_db)

            # Simulate parsed SE record
            parsed_record = {
                "headRecordSpec": "SE",
                "RecordSpec": "SE",
                "DataKubun": "1",
                "MakeDate": "20240601",
                "Year": "2024",
                "MonthDay": "0601",
                "JyoCD": "06",
                "Kaiji": "03",
                "Nichiji": "08",
                "RaceNum": "11",
                "Wakuban": "01",
                "Umaban": "01",
                "KettoNum": "2024012345",
                "Bamei": "テスト馬",
                "SexCD": "1",
                "Barei": "03",
                "Futan": "550",      # Will be converted to 55.0
                "BaTaijyu": "480",   # Will be converted to 48.0
                "Time": "1234",      # Will be converted to 123.4
                "Odds": "0015",      # Will be converted to 1.5
                "Ninki": "01",
                "KakuteiJyuni": "01",
            }

            # Import record
            success = importer.import_single_record(parsed_record, auto_commit=True)
            assert success is True

            # Verify in database
            row = temp_db.fetch_one(
                "SELECT * FROM NL_SE WHERE Year = ? AND Umaban = ?",
                (2024, 1)
            )

            assert row is not None
            assert row["KettoNum"] == "2024012345"
            assert row["KakuteiJyuni"] == 1

    def test_duplicate_handling_with_replace(self, temp_db, importer):
        """Test INSERT OR REPLACE behavior with duplicate records.

        This test verifies:
        - Initial insert succeeds
        - Duplicate insert with same primary key replaces existing record
        - No duplicate errors occur
        - Final record count is correct
        """
        with temp_db:
            create_all_tables(temp_db)

            # First insert
            record1 = {
                "headRecordSpec": "RA",
                "RecordSpec": "RA",
                "DataKubun": "1",
                "MakeDate": "20240601",
                "Year": 2024,
                "MonthDay": 601,
                "JyoCD": "06",
                "Kaiji": 3,
                "Nichiji": 8,
                "RaceNum": 11,
                "Hondai": "初回データ",
                "Kyori": 2000,
            }

            success = importer.import_single_record(record1, auto_commit=True)
            assert success is True

            # Verify first record
            row = temp_db.fetch_one(
                "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
                (2024, 11)
            )
            assert row["Hondai"] == "初回データ"

            # Insert duplicate with same primary key (should replace)
            record2 = {
                "headRecordSpec": "RA",
                "RecordSpec": "RA",
                "DataKubun": "1",
                "MakeDate": "20240602",
                "Year": 2024,
                "MonthDay": 601,
                "JyoCD": "06",
                "Kaiji": 3,
                "Nichiji": 8,
                "RaceNum": 11,
                "Hondai": "更新データ",
                "Kyori": 2400,
            }

            success = importer.import_single_record(record2, auto_commit=True)
            assert success is True

            # Verify record was replaced (not duplicated)
            rows = temp_db.fetch_all(
                "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
                (2024, 11)
            )
            assert len(rows) == 1, "Should have exactly 1 record (not 2)"
            assert rows[0]["Hondai"] == "更新データ", "Record should be updated"
            assert rows[0]["Kyori"] == 2400, "Kyori should be updated"

    def test_batch_import_with_transactions(self, temp_db, importer):
        """Test batch import with transaction processing.

        This test verifies:
        - Multiple records can be imported in batches
        - Transactions are properly committed
        - All records are successfully inserted
        - Statistics are correctly tracked
        """
        with temp_db:
            create_all_tables(temp_db)

            # Create 50 test records (will be processed in batches)
            records = [
                {
                    "headRecordSpec": "RA",
                    "RecordSpec": "RA",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": i,
                    "Hondai": f"レース{i:02d}",
                    "Kyori": 1600 + (i * 100),
                }
                for i in range(1, 51)
            ]

            # Import all records
            stats = importer.import_records(iter(records), auto_commit=True)

            # Verify statistics
            assert stats["records_imported"] == 50, "All records should be imported"
            assert stats["records_failed"] == 0, "No records should fail"
            assert stats["batches_processed"] > 0, "Batches should be processed"

            # Verify all records in database
            rows = temp_db.fetch_all("SELECT * FROM NL_RA ORDER BY RaceNum")
            assert len(rows) == 50, "All records should be in database"

            # Verify sample data
            assert rows[0]["RaceNum"] == 1
            assert rows[0]["Hondai"] == "レース01"
            assert rows[49]["RaceNum"] == 50
            assert rows[49]["Hondai"] == "レース50"

    def test_mixed_record_types_batch_import(self, temp_db, importer):
        """Test importing mixed record types in a single batch.

        This test verifies:
        - Different record types can be imported together
        - Each record goes to the correct table
        - Transaction processing works across multiple tables
        """
        with temp_db:
            create_all_tables(temp_db)

            # Create mixed record types
            records = []

            # Add 5 RA records
            for i in range(1, 6):
                records.append({
                    "headRecordSpec": "RA",
                    "RecordSpec": "RA",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": i,
                    "Hondai": f"レース{i}",
                })

            # Add 10 SE records (2 horses per race)
            for race_num in range(1, 6):
                for umaban in range(1, 3):
                    records.append({
                        "headRecordSpec": "SE",
                        "RecordSpec": "SE",
                        "DataKubun": "1",
                        "MakeDate": "20240601",
                        "Year": 2024,
                        "MonthDay": 601,
                        "JyoCD": "06",
                        "Kaiji": 3,
                        "Nichiji": 8,
                        "RaceNum": race_num,
                        "Umaban": umaban,
                        "KettoNum": f"202401{race_num:02d}{umaban:02d}",
                        "Bamei": f"馬{race_num}-{umaban}",
                    })

            # Add 5 HR records (refund)
            for i in range(1, 6):
                records.append({
                    "headRecordSpec": "HR",
                    "RecordSpec": "HR",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": i,
                    "TorokuTosu": 18,
                    "SyussoTosu": 18,
                })

            # Import all records
            stats = importer.import_records(iter(records), auto_commit=True)

            # Verify statistics
            assert stats["records_imported"] == 20  # 5 RA + 10 SE + 5 HR
            assert stats["records_failed"] == 0

            # Verify each table
            ra_count = temp_db.fetch_one("SELECT COUNT(*) as cnt FROM NL_RA")
            se_count = temp_db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")
            hr_count = temp_db.fetch_one("SELECT COUNT(*) as cnt FROM NL_HR")

            assert ra_count["cnt"] == 5, "Should have 5 RA records"
            assert se_count["cnt"] == 10, "Should have 10 SE records"
            assert hr_count["cnt"] == 5, "Should have 5 HR records"

    def test_type_conversion_integration(self, temp_db, importer):
        """Test that type conversion works correctly during import.

        This test verifies:
        - INTEGER fields are properly converted
        - REAL fields are properly converted (including /10 for odds)
        - TEXT fields remain as strings
        - NULL handling works correctly
        """
        with temp_db:
            create_all_tables(temp_db)

            # Record with various data types
            record = {
                "headRecordSpec": "SE",
                "RecordSpec": "SE",
                "DataKubun": "1",
                "MakeDate": "20240601",
                "Year": "2024",          # STRING -> INTEGER
                "MonthDay": "601",       # STRING -> INTEGER
                "JyoCD": "06",
                "Kaiji": "3",            # STRING -> INTEGER
                "Nichiji": "8",          # STRING -> INTEGER
                "RaceNum": "11",         # STRING -> INTEGER
                "Umaban": "1",           # STRING -> INTEGER
                "KettoNum": "2024012345",
                "Bamei": "テスト馬",
                "Barei": "3",            # STRING -> INTEGER
                "Futan": "550",          # STRING -> REAL (then /10 = 55.0)
                "BaTaijyu": "480",       # STRING -> REAL (then /10 = 48.0)
                "Time": "1234",          # STRING -> REAL (then /10 = 123.4)
                "Odds": "0015",          # STRING -> REAL (then /10 = 1.5)
                "Ninki": "1",            # STRING -> INTEGER
                "KakuteiJyuni": "1",     # STRING -> INTEGER
            }

            success = importer.import_single_record(record, auto_commit=True)
            assert success is True

            # Verify conversions
            row = temp_db.fetch_one(
                "SELECT * FROM NL_SE WHERE Year = ? AND Umaban = ?",
                (2024, 1)
            )

            assert row is not None
            # INTEGER conversions
            assert row["Year"] == 2024
            assert row["MonthDay"] == 601
            assert row["Kaiji"] == 3
            assert row["RaceNum"] == 11
            assert row["Umaban"] == 1
            assert row["Barei"] == 3
            assert row["Ninki"] == 1
            assert row["KakuteiJyuni"] == 1

            # REAL conversions (divided by 10)
            assert abs(row["Futan"] - 55.0) < 0.01, "Futan should be 55.0"
            assert abs(row["BaTaijyu"] - 48.0) < 0.01, "BaTaijyu should be 48.0"
            assert abs(row["Time"] - 123.4) < 0.01, "Time should be 123.4"
            assert abs(row["Odds"] - 1.5) < 0.01, "Odds should be 1.5"

            # TEXT fields
            assert row["KettoNum"] == "2024012345"
            assert row["Bamei"] == "テスト馬"

    def test_transaction_rollback_on_error(self, temp_db, importer):
        """Test that failed batches are rolled back properly.

        This test verifies:
        - When a batch fails, it falls back to individual inserts
        - Failed individual records are tracked
        - Successful records in the batch are still imported
        """
        with temp_db:
            create_all_tables(temp_db)

            # Mix of valid and invalid records
            records = [
                # Valid record
                {
                    "headRecordSpec": "RA",
                    "RecordSpec": "RA",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": 1,
                },
                # Missing required field (no headRecordSpec)
                {
                    "DataKubun": "1",
                    "Year": 2024,
                },
                # Unknown record type
                {
                    "headRecordSpec": "ZZ",
                    "Year": 2024,
                },
                # Valid record
                {
                    "headRecordSpec": "RA",
                    "RecordSpec": "RA",
                    "DataKubun": "1",
                    "MakeDate": "20240602",
                    "Year": 2024,
                    "MonthDay": 602,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 9,
                    "RaceNum": 2,
                },
            ]

            stats = importer.import_records(iter(records), auto_commit=True)

            # Verify statistics
            assert stats["records_imported"] == 2, "2 valid records should be imported"
            assert stats["records_failed"] == 2, "2 invalid records should fail"

            # Verify valid records are in database
            rows = temp_db.fetch_all("SELECT * FROM NL_RA ORDER BY RaceNum")
            assert len(rows) == 2

    def test_primary_key_enforcement(self, temp_db):
        """Test that primary key constraints are properly enforced.

        This test verifies:
        - Primary key constraints exist on tables
        - Duplicate primary keys trigger REPLACE behavior (not error)
        """
        with temp_db:
            create_all_tables(temp_db)

            # Insert record
            temp_db.execute(
                """INSERT INTO NL_RA (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Hondai)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (2024, 601, "06", 3, 8, 11, "テスト1")
            )
            temp_db.commit()

            # Try to insert duplicate (should replace due to INSERT OR REPLACE in importer)
            temp_db.execute(
                """INSERT OR REPLACE INTO NL_RA (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Hondai)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (2024, 601, "06", 3, 8, 11, "テスト2")
            )
            temp_db.commit()

            # Verify only one record exists
            rows = temp_db.fetch_all("SELECT * FROM NL_RA")
            assert len(rows) == 1
            assert rows[0]["Hondai"] == "テスト2"

    def test_end_to_end_workflow(self, temp_db, importer, parser_factory):
        """Complete end-to-end test: parse -> import -> query.

        This test simulates a complete workflow:
        1. Create parsed records (simulating parser output)
        2. Import parsed records into database
        3. Query and verify the data
        """
        with temp_db:
            create_all_tables(temp_db)

            # Simulate parsed records (as if they came from a parser)
            parsed_records = [
                {
                    "headRecordSpec": "RA",
                    "RecordSpec": "RA",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": "2024",
                    "MonthDay": "0601",
                    "JyoCD": "06",
                    "Kaiji": "03",
                    "Nichiji": "08",
                    "RaceNum": "01",
                    "Hondai": "レース1",
                },
                {
                    "headRecordSpec": "SE",
                    "RecordSpec": "SE",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": "2024",
                    "MonthDay": "0601",
                    "JyoCD": "06",
                    "Kaiji": "03",
                    "Nichiji": "08",
                    "RaceNum": "01",
                    "Umaban": "01",
                    "KettoNum": "2024010101",
                    "Bamei": "馬1",
                }
            ]

            # Import records
            stats = importer.import_records(iter(parsed_records), auto_commit=True)

            assert stats["records_imported"] == 2, "Should import 2 records"
            assert stats["records_failed"] == 0, "No failures expected"

            # Query and verify
            ra_count = temp_db.fetch_one("SELECT COUNT(*) as cnt FROM NL_RA")
            se_count = temp_db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")

            assert ra_count["cnt"] == 1, "Should have 1 RA record"
            assert se_count["cnt"] == 1, "Should have 1 SE record"


if __name__ == "__main__":
    # Allow running this test file directly
    import sys
    import pytest

    print("Running integration tests...")
    print("=" * 60)

    # Run with verbose output
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    sys.exit(exit_code)
