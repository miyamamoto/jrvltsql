"""Tests for batch processor setup-range and transaction decisions."""

from unittest.mock import MagicMock

import pytest

from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.fetcher.historical import HistoricalFetcher
from src.importer.batch import BatchProcessor
from src.importer.importer import DataImporter, ImporterError


def test_historical_no_data_resets_statistics_from_previous_spec():
    fetcher = HistoricalFetcher.__new__(HistoricalFetcher)
    fetcher.show_progress = False
    fetcher.progress_display = None
    fetcher.cache_manager = None
    fetcher._records_fetched = 9
    fetcher._records_parsed = 8
    fetcher._records_failed = 1
    fetcher.jvlink = MagicMock()
    fetcher.jvlink.uses_external_runner = False
    fetcher.jvlink.jv_open.return_value = (-1, 0, 0, "")

    assert list(fetcher.fetch("RACE", "20260701", "20260714")) == []
    assert fetcher.get_statistics() == {
        "records_fetched": 0,
        "records_parsed": 0,
        "records_failed": 0,
        "recoverable_read_errors": 0,
        "repaired_read_errors": 0,
    }


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


def test_invalid_dataspec_stops_before_schema_preparation(monkeypatch):
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
    prepare_schema = MagicMock()
    monkeypatch.setattr("src.importer.batch.create_all_tables", prepare_schema)

    with pytest.raises(ValueError, match="four-character"):
        processor.process_date_range("O1", "20260701", "20260714")

    prepare_schema.assert_not_called()
    processor.fetcher.fetch.assert_not_called()


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
                "DataKubun": "1",
                "MakeDate": "20260714",
                "Year": "2026",
                "MonthDay": "0714",
                "JyoCD": "05",
                "Kaiji": "01",
                "Nichiji": "01",
                "RaceNum": "01",
            },
            {"RecordSpec": "RA", "DataKubun": "Z"},
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

        with pytest.raises(SchemaMigrationError, match="DataKubun"):
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


def test_option_3_long_range_uses_one_open_and_remains_atomic(tmp_path):
    """option=3は年次tailを反復せず、後段拒否時は単一transactionを戻す。"""
    database = SQLiteDatabase({"path": str(tmp_path / "option3-single-open.db")})
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter(
        [
            {
                "RecordSpec": "RA",
                "DataKubun": "1",
                "MakeDate": "20250714",
                "Year": "2025",
                "MonthDay": "0714",
                "JyoCD": "05",
                "Kaiji": "01",
                "Nichiji": "01",
                "RaceNum": "01",
            },
            {"RecordSpec": "RA", "DataKubun": "Z"},
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

        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            processor.process_date_range(
                "RACE", "20200101", "20260819", option=3, ensure_tables=False
            )

        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"]

    processor.fetcher.fetch.assert_called_once_with(
        "RACE", "20200101", "20260819", 3
    )
    assert row_count == 0


class _RecordingImporter:
    """Fake importer that consumes each stream and records what it received."""

    def __init__(self):
        self.calls = []

    def import_records(self, records, auto_commit=True):
        batch = list(records)
        self.calls.append(batch)
        return {
            "records_imported": len(batch),
            "records_failed": 0,
            "batches_processed": 1,
        }


def _record(index):
    return {"RecordSpec": "RA", "index": index}


_PARSE_FAILURE = object()


class _ParseSkippingFetcher:
    """Fake fetcher whose stream drops records mid-run, like a parse failure.

    ``records_failed`` grows lazily while the stream is consumed, matching
    how HistoricalFetcher counts parse failures inside its generator.
    """

    def __init__(self, plan):
        self._plan = plan
        self._fetched = 0
        self._parsed = 0
        self._failed = 0

    def fetch(self, *_args, **_kwargs):
        self._fetched = self._parsed = self._failed = 0
        for item in self._plan:
            self._fetched += 1
            if item is _PARSE_FAILURE:
                self._failed += 1
                continue
            self._parsed += 1
            yield item

    def get_statistics(self):
        return {
            "records_fetched": self._fetched,
            "records_parsed": self._parsed,
            "records_failed": self._failed,
        }


def _chunking_processor(records):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter(records)
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": len(records),
        "records_parsed": len(records),
        "records_failed": 0,
    }
    processor.importer = _RecordingImporter()
    return processor


def _transaction_calls(database):
    return [name for name, _args, _kwargs in database.mock_calls]


# 以下の option=4 テスト群は「1回のオープン内のコミット間隔」契約を固定する。
# 日付範囲の長短にかかわらずprovider setup tailは1回だけopenする。
def test_option_4_commits_once_per_interval(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    processor = _chunking_processor([_record(i) for i in range(5)])

    processor.process_date_range(
        "RACE", "19860101", "20221231", option=4, ensure_tables=False
    )

    assert [len(batch) for batch in processor.importer.calls] == [2, 2, 1]
    assert _transaction_calls(processor.database).count("commit") == 3


def test_option_4_shorter_than_the_interval_commits_once(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 10)
    processor = _chunking_processor([_record(0)])

    processor.process_date_range(
        "RACE", "19860101", "20221231", option=4, ensure_tables=False
    )

    assert [len(batch) for batch in processor.importer.calls] == [1]
    assert _transaction_calls(processor.database).count("commit") == 1


def test_option_4_empty_stream_still_commits_once(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    processor = _chunking_processor([])

    processor.process_date_range(
        "RACE", "19860101", "20221231", option=4, ensure_tables=False
    )

    assert [len(batch) for batch in processor.importer.calls] == [0]
    assert _transaction_calls(processor.database).count("commit") == 1


@pytest.mark.parametrize("option", [1, 2])
def test_diff_options_keep_a_single_transaction(monkeypatch, option):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    processor = _chunking_processor([_record(i) for i in range(5)])

    processor.process_date_range(
        "RACE", "20260101", "20260131", option=option, ensure_tables=False
    )

    assert [len(batch) for batch in processor.importer.calls] == [5]
    assert _transaction_calls(processor.database).count("commit") == 1


def test_option_4_caller_managed_transaction_keeps_a_single_commit_point(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    processor = _chunking_processor([_record(i) for i in range(5)])

    processor.process_date_range(
        "RACE",
        "19860101",
        "20221231",
        option=4,
        auto_commit=False,
        ensure_tables=False,
    )

    assert [len(batch) for batch in processor.importer.calls] == [5]
    assert "commit" not in _transaction_calls(processor.database)


def test_option_4_sums_statistics_across_chunks(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    processor = _chunking_processor([_record(i) for i in range(5)])

    stats = processor.process_date_range(
        "RACE", "19860101", "20221231", option=4, ensure_tables=False
    )

    assert stats["records_imported"] == 5
    assert stats["records_fetched"] == 5
    assert stats["batches_processed"] == 3


def test_option_4_fetch_failure_blocks_commit_of_the_consuming_chunk(monkeypatch):
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 1)
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = _ParseSkippingFetcher(
        [_record(0), _PARSE_FAILURE, _record(1)]
    )
    processor.importer = _RecordingImporter()

    with pytest.raises(ImporterError, match="rejected 1 record"):
        processor.process_date_range(
            "RACE", "19860101", "20221231", option=4, ensure_tables=False
        )

    # The clean first chunk commits; the chunk consumed alongside the parse
    # failure raises before its commit and is rolled back instead.
    assert _transaction_calls(processor.database) == [
        "begin_transaction",
        "commit",
        "begin_transaction",
        "rollback",
    ]


def test_option_4_rejection_rolls_back_only_its_own_chunk(tmp_path, monkeypatch):
    # The counterpart of test_import_rejection_rolls_back_earlier_successful_batch,
    # which pins the single-transaction path losing everything. The rejected
    # chunk mixes an importable record with the rejected one, so the rollback
    # must discard the whole chunk, not just the bad record.
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 2)
    database = SQLiteDatabase({"path": str(tmp_path / "chunked.db")})
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor.cache_manager = None

    def _ra_record(race_num):
        return {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "MakeDate": "20260714",
            "Year": "2026",
            "MonthDay": "0714",
            "JyoCD": "05",
            "Kaiji": "01",
            "Nichiji": "01",
            "RaceNum": race_num,
        }

    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter(
        [
            _ra_record("01"),
            _ra_record("02"),
            _ra_record("03"),
            {"RecordSpec": "RA", "DataKubun": "Z"},
        ]
    )
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 4,
        "records_parsed": 4,
        "records_failed": 0,
    }

    with database:
        database.execute(SCHEMAS["NL_RA"])
        database.commit()
        processor.importer = DataImporter(database, batch_size=1)

        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            processor.process_date_range(
                "RACE", "19860101", "20221231", option=4, ensure_tables=False
            )

        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"]

    # Chunk 1 (races 01, 02) stays committed; chunk 2 loses race 03 along
    # with the rejected record.
    assert row_count == 2


def test_option_4_long_range_uses_one_provider_open_and_keeps_group_commits(
    tmp_path, monkeypatch
):
    """長期間setupもprovider tailは1回だけopenし、group単位で耐久化する。"""
    monkeypatch.setattr("src.importer.batch.SETUP_COMMIT_INTERVAL", 1)

    def _valid_ra(race_num):
        return {
            "RecordSpec": "RA",
            "DataKubun": "1",
            "MakeDate": "20260714",
            "Year": "2026",
            "MonthDay": "0714",
            "JyoCD": "05",
            "Kaiji": "01",
            "Nichiji": "01",
            "RaceNum": race_num,
        }

    database = SQLiteDatabase({"path": str(tmp_path / "option4-single-open.db")})
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = database
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.fetcher.fetch.return_value = iter([_valid_ra("01"), _valid_ra("02")])
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 2,
        "records_parsed": 2,
        "records_failed": 0,
    }

    with database:
        database.execute(SCHEMAS["NL_RA"])
        database.commit()
        processor.importer = DataImporter(database, batch_size=1)
        stats = processor.process_date_range(
            "RACE", "20240820", "20260819", option=4, ensure_tables=False
        )
        row_count = database.fetch_one("SELECT COUNT(*) AS count FROM NL_RA")["count"]

    processor.fetcher.fetch.assert_called_once_with(
        "RACE", "20240820", "20260819", 4
    )
    assert stats["records_imported"] == 2
    assert row_count == 2


def test_option_4_long_range_uses_one_full_scope_cache_request():
    """cache付きでも年窓へ分割せず、同一scopeのresume単位を維持する。"""
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    cache = MagicMock()
    processor.cache_manager = cache
    processor.fetcher = MagicMock()
    processor.fetcher.fetch_with_cache.return_value = iter([])
    processor.fetcher.get_statistics.return_value = {
        "records_fetched": 0,
        "records_parsed": 0,
        "records_failed": 0,
    }
    processor.importer = _RecordingImporter()

    processor.process_date_range(
        "RACE", "20240820", "20260819", option=4, ensure_tables=False
    )

    processor.fetcher.fetch_with_cache.assert_called_once_with(
        cache, "RACE", "20240820", "20260819", 4
    )


@pytest.mark.parametrize(
    ("bad_from", "bad_to"),
    [
        ("2025-08-20", "20260819"),  # 区切り文字入り
        ("20250820", "20260832"),    # 実在しない暦日
        (None, "20260819"),          # 欠落
        ("20260819", "20250820"),    # 逆転した範囲
    ],
)
def test_invalid_dates_stop_before_schema_transaction_or_fetch(
    monkeypatch, bad_from, bad_to
):
    processor = BatchProcessor.__new__(BatchProcessor)
    processor.database = MagicMock()
    processor.cache_manager = None
    processor.fetcher = MagicMock()
    processor.importer = MagicMock()
    prepare_schema = MagicMock()
    monkeypatch.setattr("src.importer.batch.create_all_tables", prepare_schema)

    with pytest.raises(ValueError):
        processor.process_date_range("RACE", bad_from, bad_to, option=4)

    prepare_schema.assert_not_called()
    processor.fetcher.fetch.assert_not_called()
    processor.fetcher.fetch_with_cache.assert_not_called()
    assert "begin_transaction" not in [
        name for name, _args, _kwargs in processor.database.mock_calls
    ]
