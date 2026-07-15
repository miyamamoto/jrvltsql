"""Tests for batch processor setup-range splitting decisions."""

from unittest.mock import MagicMock, call

import pytest

from src.importer.batch import BatchProcessor
from src.importer.importer import DataImporter, ImporterError
from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase


def test_option_3_setup_range_splits_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 3) is True


def test_option_4_setup_range_does_not_split_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 4) is False


def test_diff_options_do_not_split_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 1) is False
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 2) is False


def test_schema_preparation_failure_stops_before_fetch(monkeypatch):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.importer = MagicMock()

    def fail_schema_preparation(_database):
        raise RuntimeError("unsafe schema")

    monkeypatch.setattr(
        "src.importer.batch.create_all_tables",
        fail_schema_preparation,
    )

    with pytest.raises(RuntimeError, match="unsafe schema"):
        processor.process_date_range("RACE", "20260701", "20260714")

    processor.fetcher.fetch.assert_not_called()
    processor.importer.import_records.assert_not_called()


def test_import_rejection_fails_batch_and_rolls_back(monkeypatch):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter([{"RecordSpec": "SE"}])
    processor.fetcher.get_statistics.return_value = {"records_fetched": 1}
    processor.importer = MagicMock()
    processor.importer.import_records.return_value = {
        "records_imported": 0,
        "records_failed": 1,
    }
    monkeypatch.setattr(
        "src.importer.batch.create_all_tables",
        lambda _database: None,
    )

    with pytest.raises(ImporterError, match="rejected 1 record"):
        processor.process_date_range("RACE", "20260701", "20260714")

    processor.database.rollback.assert_called_once()


def test_fetch_parse_rejection_is_not_overwritten_by_import_stats(monkeypatch):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter([])
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 1,
        "records_parsed": 0,
        "records_failed": 1,
    }
    processor.importer = MagicMock()
    processor.importer.import_records.return_value = {
        "records_imported": 0,
        "records_failed": 0,
    }
    monkeypatch.setattr(
        "src.importer.batch.create_all_tables",
        lambda _database: None,
    )

    with pytest.raises(ImporterError, match="rejected 1 record"):
        processor.process_date_range("RACE", "20260701", "20260714")

    processor.database.rollback.assert_called_once()


def test_caller_managed_import_still_begins_driver_transaction(monkeypatch):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter([])
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 0,
        "records_parsed": 0,
        "records_failed": 0,
    }
    processor.importer = MagicMock()
    processor.importer.import_records.return_value = {
        "records_imported": 0,
        "records_failed": 0,
    }
    monkeypatch.setattr(
        "src.importer.batch.create_all_tables",
        lambda _database: None,
    )

    processor.process_date_range(
        "RACE", "20260701", "20260714", auto_commit=False
    )

    processor.database.begin_transaction.assert_called_once_with()
    processor.database.commit.assert_not_called()


def test_import_rejection_rolls_back_earlier_successful_batch(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "atomic.db")})
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter(
        [
            {
                "RecordSpec": "RA",
                "Year": "2026",
                "MonthDay": "0714",
                "JyoCD": "05",
                "Kaiji": "01",
                "Nichiji": "01",
                "RaceNum": "01",
            },
            {"RecordSpec": "UNKNOWN"},
        ]
    )
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 2,
        "records_parsed": 2,
        "records_failed": 0,
    }

    with database:
        database.execute(SCHEMAS["NL_RA"])
        database.commit()
        processor.importer = DataImporter(database, batch_size=1)

        with pytest.raises(ImporterError, match="rejected 1 record"):
            processor.process_date_range(
                "RACE",
                "20260714",
                "20260714",
                ensure_tables=False,
            )

        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"]

    assert row_count == 0


def test_multiple_specs_passes_auto_commit_without_overwriting_option():
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.process_date_range = MagicMock(return_value={"records_imported": 1})

    results = processor.process_multiple_specs(
        ["RACE"],
        "20260701",
        "20260714",
        auto_commit=False,
    )

    processor.process_date_range.assert_called_once_with(
        data_spec="RACE",
        from_date="20260701",
        to_date="20260714",
        auto_commit=False,
        ensure_tables=False,
    )
    assert results["_summary"]["failed"] == 0


def test_split_setup_commits_once_after_all_chunks_succeed():
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor._iter_year_chunks = MagicMock(
        return_value=iter(
            [("20200101", "20201231"), ("20210101", "20211231")]
        )
    )
    processor.process_date_range = MagicMock(
        side_effect=[
            {"records_imported": 2, "records_failed": 0},
            {"records_imported": 3, "records_failed": 0},
        ]
    )

    stats = processor._process_split_setup_range(
        "RACE", "20200101", "20211231", 3, True, False
    )

    assert stats["records_imported"] == 5
    assert all(
        call.kwargs["auto_commit"] is False
        for call in processor.process_date_range.call_args_list
    )
    processor.database.commit.assert_called_once_with()


@pytest.mark.parametrize("driver", ["pg8000", "psycopg"])
def test_split_setup_rolls_back_postgresql_transaction_on_later_failure(
    monkeypatch, driver
):
    import src.database.postgresql_handler as postgresql_handler

    database = postgresql_handler.PostgreSQLDatabase({})
    database._connection = MagicMock()
    database._cursor = MagicMock()
    monkeypatch.setattr(postgresql_handler, "DRIVER", driver)

    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor._iter_year_chunks = MagicMock(
        return_value=iter(
            [("20200101", "20201231"), ("20210101", "20211231")]
        )
    )
    processor.process_date_range = MagicMock(
        side_effect=[{"records_imported": 1}, RuntimeError("later chunk failed")]
    )

    with pytest.raises(RuntimeError, match="later chunk failed"):
        processor._process_split_setup_range(
            "RACE", "20200101", "20211231", 3, True, False
        )

    if driver == "pg8000":
        assert database._connection.run.call_args_list == [
            call("BEGIN"),
            call("ROLLBACK"),
        ]
    else:
        database._connection.rollback.assert_called_once_with()


def test_split_setup_rolls_back_all_chunks_on_later_failure(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "split-atomic.db")})
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.side_effect = [
        iter(
            [
                {
                    "RecordSpec": "RA",
                    "Year": "2025",
                    "MonthDay": "0714",
                    "JyoCD": "05",
                    "Kaiji": "01",
                    "Nichiji": "01",
                    "RaceNum": "01",
                }
            ]
        ),
        iter([{"RecordSpec": "UNKNOWN"}]),
    ]
    processor.fetcher.get_statistics.side_effect = [
        {"records_fetched": 1, "records_parsed": 1, "records_failed": 0},
        {"records_fetched": 1, "records_parsed": 1, "records_failed": 0},
    ]
    processor._iter_year_chunks = MagicMock(
        return_value=iter(
            [("20250101", "20251231"), ("20260101", "20261231")]
        )
    )

    with database:
        database.execute(SCHEMAS["NL_RA"])
        database.commit()
        processor.importer = DataImporter(database, batch_size=1)

        with pytest.raises(ImporterError, match="rejected 1 record"):
            processor._process_split_setup_range(
                "RACE", "20250101", "20261231", 3, True, False
            )

        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"]

    assert row_count == 0
