"""Unit tests for data importer."""

import tempfile
from pathlib import Path

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS, create_all_tables
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter


class TestDataImporter:
    """Test cases for DataImporter."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create SQLite database instance."""
        config = {"path": str(temp_db_path)}
        return SQLiteDatabase(config)

    @pytest.fixture
    def importer(self, db):
        """Create data importer."""
        return DataImporter(db, batch_size=10)

    def test_initialization(self, importer):
        """Test importer initialization."""
        assert importer.batch_size == 10
        assert importer._records_imported == 0
        assert importer._records_failed == 0

    def test_import_single_record(self, db, importer):
        """Test importing single record."""
        # Setup database
        with db:
            db.execute(SCHEMAS["NL_RA"])

            # Create test record
            record = {
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
                "Hondai": "テストレース",
                "Kyori": 2000,
            }

            # Import record
            success = importer.import_single_record(record, auto_commit=False)
            assert success is True

            db.commit()

            # Verify import
            row = db.fetch_one(
                "SELECT * FROM NL_RA WHERE Year = ? AND RaceNum = ?",
                (2024, 11),
            )

            assert row is not None
            assert row["Hondai"] == "テストレース"

    def test_import_multiple_records(self, db, importer):
        """Test importing multiple records."""
        with db:
            db.execute(SCHEMAS["NL_RA"])

            # Create test records
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
                    "Hondai": f"レース{i}",
                    "Kyori": 2000,
                }
                for i in range(1, 6)
            ]

            # Import records
            stats = importer.import_records(iter(records), auto_commit=False)

            assert stats["records_imported"] == 5
            assert stats["records_failed"] == 0

            db.commit()

            # Verify imports
            rows = db.fetch_all("SELECT * FROM NL_RA ORDER BY RaceNum")
            assert len(rows) == 5

    def test_batch_processing(self, db, importer):
        """Test batch processing."""
        importer.batch_size = 3

        with db:
            db.execute(SCHEMAS["NL_RA"])

            # Create 10 records (will be processed in 4 batches: 3+3+3+1)
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
                    "Hondai": f"レース{i}",
                    "Kyori": 2000,
                }
                for i in range(1, 11)
            ]

            stats = importer.import_records(iter(records), auto_commit=False)

            assert stats["records_imported"] == 10
            assert stats["batches_processed"] == 4

            db.commit()

    def test_import_mixed_record_types(self, db, importer):
        """Test importing different record types."""
        with db:
            create_all_tables(db)

            # Create mixed records
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
                    "RaceNum": 1,
                    "Hondai": "レース1",
                },
                {
                    "headRecordSpec": "SE",
                    "RecordSpec": "SE",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": 1,
                    "Umaban": 1,
                    "KettoNum": "2024012345",
                    "Bamei": "テスト馬",
                },
                {
                    "headRecordSpec": "HR",
                    "RecordSpec": "HR",
                    "DataKubun": "1",
                    "MakeDate": "20240601",
                    "Year": 2024,
                    "MonthDay": 601,
                    "JyoCD": "06",
                    "Kaiji": 3,
                    "Nichiji": 8,
                    "RaceNum": 1,
                    "TorokuTosu": 18,
                    "SyussoTosu": 18,
                },
            ]

            stats = importer.import_records(iter(records), auto_commit=False)

            assert stats["records_imported"] == 3
            assert stats["records_failed"] == 0

            db.commit()

            # Verify each table
            ra_count = db.fetch_one("SELECT COUNT(*) as cnt FROM NL_RA")
            se_count = db.fetch_one("SELECT COUNT(*) as cnt FROM NL_SE")
            hr_count = db.fetch_one("SELECT COUNT(*) as cnt FROM NL_HR")

            assert ra_count["cnt"] == 1
            assert se_count["cnt"] == 1
            assert hr_count["cnt"] == 1

    def test_invalid_record_handling(self, db, importer):
        """A malformed header aborts the batch before any valid row is stored."""
        with db:
            db.execute(SCHEMAS["NL_RA"])

            # Records with missing/invalid data
            records = [
                {  # Missing headRecordSpec
                    "Year": 2024,
                    "RaceNum": 1,
                },
                {  # Unknown record type
                    "headRecordSpec": "XX",
                    "Year": 2024,
                },
                {  # Valid record
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
            ]

            with pytest.raises(SchemaMigrationError, match="record-type"):
                importer.import_records(iter(records), auto_commit=False)

            assert db.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"] == 0

    def test_get_statistics(self, importer):
        """Test getting statistics."""
        stats = importer.get_statistics()

        assert "records_imported" in stats
        assert "records_failed" in stats
        assert "batches_processed" in stats

    def test_reset_statistics(self, importer):
        """Test resetting statistics."""
        importer._records_imported = 100
        importer._records_failed = 10

        importer.reset_statistics()

        assert importer._records_imported == 0
        assert importer._records_failed == 0

    def test_add_table_mapping(self, importer):
        """Test adding custom table mapping."""
        importer.add_table_mapping("XX", "CUSTOM_TABLE")

        assert "XX" in importer._table_map
        assert importer._table_map["XX"] == "CUSTOM_TABLE"

    def test_repr(self, importer):
        """Test string representation."""
        repr_str = repr(importer)

        assert "DataImporter" in repr_str
        assert "imported=" in repr_str
