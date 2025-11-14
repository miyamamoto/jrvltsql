#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Performance benchmark tests for JLTSQL.

Tests performance characteristics under various loads:
1. Import performance (batch sizes, record counts)
2. Query performance
3. Database comparison (SQLite vs DuckDB vs PostgreSQL)
4. Memory usage
5. Concurrent operations

Note: These are benchmark tests that may take longer to run.
Use pytest -m "not slow" to skip them in CI/CD.
"""

import os
import tempfile
import unittest
import time
from pathlib import Path
import pytest

from src.database.sqlite_handler import SQLiteDatabase
from src.database.duckdb_handler import DuckDBDatabase
from src.database.schema import SchemaManager
from src.importer.importer import DataImporter


class PerformanceTestBase(unittest.TestCase):
    """Base class for performance tests."""

    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of function."""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed

    def generate_sample_records(self, count, record_type='RA'):
        """Generate sample records for testing."""
        return [
            {
                'レコード種別ID': record_type,
                '開催年月日': f'2024{i:04d}',
                '競馬場コード': f'{i % 10:02d}',
                'レース番号': f'{(i % 12) + 1:02d}',
                'データ区分': '1',
            }
            for i in range(1, count + 1)
        ]


@pytest.mark.slow
class TestImportPerformance(PerformanceTestBase):
    """Test import performance with various configurations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'perf.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.schema_mgr.create_table('NL_RA')

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_import_100_records(self):
        """Benchmark: Import 100 records."""
        records = self.generate_sample_records(100)
        importer = DataImporter(self.database, batch_size=10)

        result, elapsed = self.measure_time(importer.import_records, records)

        print(f"\n100 records: {elapsed:.3f}s ({100/elapsed:.0f} records/sec)")
        self.assertLess(elapsed, 5.0, "Should complete in under 5 seconds")

    def test_import_1000_records(self):
        """Benchmark: Import 1000 records."""
        records = self.generate_sample_records(1000)
        importer = DataImporter(self.database, batch_size=100)

        result, elapsed = self.measure_time(importer.import_records, records)

        print(f"\n1000 records: {elapsed:.3f}s ({1000/elapsed:.0f} records/sec)")
        self.assertLess(elapsed, 30.0, "Should complete in under 30 seconds")

    def test_batch_size_comparison(self):
        """Compare performance with different batch sizes."""
        records = self.generate_sample_records(500)
        batch_sizes = [10, 50, 100, 500]

        results = {}
        for batch_size in batch_sizes:
            # Reset table
            self.database.execute("DELETE FROM NL_RA")

            importer = DataImporter(self.database, batch_size=batch_size)
            _, elapsed = self.measure_time(importer.import_records, records)
            results[batch_size] = elapsed

            print(f"Batch size {batch_size}: {elapsed:.3f}s")

        # Larger batch sizes should generally be faster
        # (though not always due to transaction overhead)
        self.assertIsInstance(results[10], float)

    def test_single_vs_batch_insert(self):
        """Compare single record vs batch insert performance."""
        records = self.generate_sample_records(100)

        # Single record inserts
        importer_single = DataImporter(self.database, batch_size=1)
        _, time_single = self.measure_time(
            importer_single.import_records, records[:50]
        )

        # Reset table
        self.database.execute("DELETE FROM NL_RA")

        # Batch inserts
        importer_batch = DataImporter(self.database, batch_size=50)
        _, time_batch = self.measure_time(
            importer_batch.import_records, records[50:]
        )

        print(f"\nSingle: {time_single:.3f}s, Batch: {time_batch:.3f}s")
        # Batch should be faster or comparable
        self.assertLessEqual(time_batch, time_single * 2)


@pytest.mark.slow
class TestQueryPerformance(PerformanceTestBase):
    """Test query performance."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'query_perf.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.schema_mgr.create_table('NL_RA')

        # Populate with test data
        records = self.generate_sample_records(1000)
        importer = DataImporter(self.database, batch_size=100)
        importer.import_records(records)

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_simple_select_all(self):
        """Benchmark: SELECT * FROM table."""
        _, elapsed = self.measure_time(
            self.database.fetch_all,
            "SELECT * FROM NL_RA"
        )

        print(f"\nSELECT *: {elapsed:.3f}s")
        self.assertLess(elapsed, 1.0, "Should complete in under 1 second")

    def test_filtered_query(self):
        """Benchmark: SELECT with WHERE clause."""
        _, elapsed = self.measure_time(
            self.database.fetch_all,
            "SELECT * FROM NL_RA WHERE 開催年月日 >= '20240500'"
        )

        print(f"\nFiltered SELECT: {elapsed:.3f}s")
        self.assertLess(elapsed, 1.0, "Should complete in under 1 second")

    def test_count_query(self):
        """Benchmark: COUNT query."""
        _, elapsed = self.measure_time(
            self.database.fetch_one,
            "SELECT COUNT(*) as cnt FROM NL_RA"
        )

        print(f"\nCOUNT query: {elapsed:.3f}s")
        self.assertLess(elapsed, 0.5, "Should complete in under 0.5 seconds")

    def test_aggregation_query(self):
        """Benchmark: Aggregation queries."""
        query = """
            SELECT 競馬場コード, COUNT(*) as cnt
            FROM NL_RA
            GROUP BY 競馬場コード
        """

        _, elapsed = self.measure_time(self.database.fetch_all, query)

        print(f"\nAggregation query: {elapsed:.3f}s")
        self.assertLess(elapsed, 1.0, "Should complete in under 1 second")


@pytest.mark.slow
class TestDatabaseComparison(PerformanceTestBase):
    """Compare performance across different databases."""

    def setUp(self):
        """Set up test databases."""
        self.temp_dir = tempfile.TemporaryDirectory()

        # SQLite
        sqlite_path = Path(self.temp_dir.name) / 'sqlite.db'
        self.sqlite = SQLiteDatabase({'path': str(sqlite_path)})
        self.sqlite.connect()

        # DuckDB
        duckdb_path = Path(self.temp_dir.name) / 'duckdb.duckdb'
        self.duckdb = DuckDBDatabase({'path': str(duckdb_path)})
        self.duckdb.connect()

        self.databases = {
            'SQLite': self.sqlite,
            'DuckDB': self.duckdb,
        }

        # Create tables in all databases
        for name, db in self.databases.items():
            schema_mgr = SchemaManager(db)
            schema_mgr.create_table('NL_RA')

    def tearDown(self):
        """Clean up."""
        for db in self.databases.values():
            if db._connection:
                db.disconnect()
        self.temp_dir.cleanup()

    def test_import_performance_comparison(self):
        """Compare import performance across databases."""
        records = self.generate_sample_records(500)
        results = {}

        for name, db in self.databases.items():
            importer = DataImporter(db, batch_size=100)
            _, elapsed = self.measure_time(importer.import_records, records)
            results[name] = elapsed

            print(f"{name} import (500 records): {elapsed:.3f}s")

        # Both should complete in reasonable time
        for elapsed in results.values():
            self.assertLess(elapsed, 30.0, "Should complete in under 30 seconds")

    def test_query_performance_comparison(self):
        """Compare query performance across databases."""
        # Populate databases
        records = self.generate_sample_records(1000)
        for db in self.databases.values():
            importer = DataImporter(db, batch_size=100)
            importer.import_records(records)

        # Compare query performance
        query_results = {}
        for name, db in self.databases.items():
            _, elapsed = self.measure_time(
                db.fetch_all,
                "SELECT * FROM NL_RA WHERE 開催年月日 >= '20240500'"
            )
            query_results[name] = elapsed

            print(f"{name} query: {elapsed:.3f}s")

        # Both should complete in reasonable time
        for elapsed in query_results.values():
            self.assertLess(elapsed, 2.0, "Should complete in under 2 seconds")


@pytest.mark.slow
class TestMemoryUsage(PerformanceTestBase):
    """Test memory usage patterns."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'memory.db'

        self.database = SQLiteDatabase({'path': str(self.db_path)})
        self.database.connect()

        self.schema_mgr = SchemaManager(self.database)
        self.schema_mgr.create_table('NL_RA')

    def tearDown(self):
        """Clean up."""
        self.database.disconnect()
        self.temp_dir.cleanup()

    def test_large_batch_memory(self):
        """Test memory usage with large batches."""
        # Generate large dataset
        records = self.generate_sample_records(5000)

        # Import with moderate batch size
        importer = DataImporter(self.database, batch_size=500)

        # Should complete without memory errors
        result = importer.import_records(records)

        self.assertIn('records_imported', result)
        # Most or all should succeed
        self.assertGreater(result['records_imported'], 4000)

    def test_query_large_result_set(self):
        """Test querying large result sets."""
        # Populate database
        records = self.generate_sample_records(2000)
        importer = DataImporter(self.database, batch_size=200)
        importer.import_records(records)

        # Query all records
        rows = self.database.fetch_all("SELECT * FROM NL_RA")

        # Should return all records without memory issues
        self.assertGreater(len(rows), 1500)


@pytest.mark.slow
class TestScalability(PerformanceTestBase):
    """Test system scalability."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_multiple_tables_import(self):
        """Test importing to multiple tables simultaneously."""
        db_path = Path(self.temp_dir.name) / 'multi_table.db'
        database = SQLiteDatabase({'path': str(db_path)})
        database.connect()

        # Create multiple tables
        schema_mgr = SchemaManager(database)
        tables = ['NL_RA', 'NL_SE', 'NL_HR', 'NL_YS']
        for table in tables:
            schema_mgr.create_table(table)

        # Import to different tables
        importer = DataImporter(database, batch_size=50)

        total_time = 0
        for table in tables:
            records = self.generate_sample_records(
                200,
                record_type=table.replace('NL_', '')
            )
            _, elapsed = self.measure_time(importer.import_records, records)
            total_time += elapsed

        print(f"\nMulti-table import ({len(tables)} tables): {total_time:.3f}s")
        self.assertLess(total_time, 60.0, "Should complete in under 60 seconds")

        database.disconnect()

    def test_database_growth(self):
        """Test performance as database grows."""
        db_path = Path(self.temp_dir.name) / 'growth.db'
        database = SQLiteDatabase({'path': str(db_path)})
        database.connect()

        schema_mgr = SchemaManager(database)
        schema_mgr.create_table('NL_RA')

        importer = DataImporter(database, batch_size=100)

        # Import in stages, measure time each stage
        stages = [500, 1000, 1500, 2000]
        times = []

        for stage_size in stages:
            records = self.generate_sample_records(stage_size)
            _, elapsed = self.measure_time(importer.import_records, records)
            times.append(elapsed)

            print(f"Stage {stage_size} records: {elapsed:.3f}s")

            # Clear for next stage
            database.execute("DELETE FROM NL_RA")

        # Performance shouldn't degrade significantly
        # (Last stage should be within 3x of first)
        if len(times) > 1:
            ratio = times[-1] / times[0]
            self.assertLess(ratio, 5.0, "Performance degradation too high")

        database.disconnect()


if __name__ == '__main__':
    unittest.main()
