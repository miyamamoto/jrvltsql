"""Mutation-boundary tests for the official JV-Data DataKubun contract."""

from collections.abc import Callable

import pytest

from src.database.base import DatabaseError
from src.database.migration import SchemaMigrationError
from src.database.schema import SCHEMAS
from src.database.schema_jravan import JRAVAN_SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from src.importer.importer import DataImporter, TransactionRecoveryError
from src.importer.importer_optimized import OptimizedDataImporter
from src.parser.status_domain import validate_record_header


def _tc_record(**overrides) -> dict:
    record = {
        "RecordSpec": "TC",
        "DataKubun": "1",
        "MakeDate": "20260817",
        "Year": "2026",
        "MonthDay": "0817",
        "JyoCD": "05",
        "Kaiji": "03",
        "Nichiji": "08",
        "RaceNum": "11",
        "HappyoTime": "08171234",
        "AtoJi": "15",
        "AtoFun": "10",
        "MaeJi": "15",
        "MaeFun": "00",
    }
    record.update(overrides)
    return record


ENTRY_POINTS: tuple[tuple[str, type, bool], ...] = (
    ("data-batch", DataImporter, False),
    ("optimized-batch", OptimizedDataImporter, False),
    ("data-single", DataImporter, True),
)


class _PendingInspectionFailureSQLite(SQLiteDatabase):
    """Inject one physical-transaction inspection failure after a real write."""

    fail_next_pending_inspection = False
    fail_next_invalidation = False

    def has_pending_transaction(self) -> bool:
        if self.fail_next_pending_inspection:
            self.fail_next_pending_inspection = False
            raise DatabaseError("injected transaction-state inspection failure")
        return super().has_pending_transaction()

    def invalidate_connection(self) -> None:
        if self.fail_next_invalidation:
            self.fail_next_invalidation = False
            raise DatabaseError("injected connection invalidation failure")
        super().invalidate_connection()


@pytest.mark.parametrize(("entry_name", "importer_class", "single"), ENTRY_POINTS)
@pytest.mark.parametrize("auto_commit", (True, False))
def test_import_entries_reject_invalid_or_missing_status_before_mutation(
    tmp_path,
    entry_name: str,
    importer_class: type,
    single: bool,
    auto_commit: bool,
) -> None:
    variants: tuple[tuple[str, Callable[[dict], None]], ...] = (
        ("missing", lambda row: row.pop("DataKubun")),
        ("blank", lambda row: row.update(DataKubun="")),
        ("unknown", lambda row: row.update(DataKubun="Z")),
        ("non-current-zero", lambda row: row.update(DataKubun="0")),
        (
            "conflict",
            lambda row: row.update(DataKubun="1", headDataKubun="0"),
        ),
    )

    for variant_name, mutate in variants:
        database = SQLiteDatabase(
            {"path": str(tmp_path / f"{entry_name}-{auto_commit}-{variant_name}.db")}
        )
        with database:
            database.execute(SCHEMAS["NL_TC"])
            database.commit()
            record = _tc_record()
            mutate(record)
            importer = importer_class(database)
            with pytest.raises(SchemaMigrationError, match="DataKubun"):
                if single:
                    importer.import_single_record(record, auto_commit=auto_commit)
                else:
                    importer.import_records(iter([record]), auto_commit=auto_commit)
            assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TC")["count"] == 0
            assert database.has_pending_transaction() is False


@pytest.mark.parametrize(("entry_name", "importer_class", "single"), ENTRY_POINTS)
def test_import_entries_accept_equal_legacy_aliases_and_store_canonical_header(
    tmp_path,
    entry_name: str,
    importer_class: type,
    single: bool,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / f"valid-{entry_name}.db")})
    with database:
        database.execute(SCHEMAS["NL_TC"])
        database.commit()
        record = _tc_record()
        record["headRecordSpec"] = record.pop("RecordSpec")
        record["headDataKubun"] = record.pop("DataKubun")
        importer = importer_class(database)
        if single:
            assert importer.import_single_record(record) is True
        else:
            stats = importer.import_records(iter([record]))
            assert stats["records_imported"] == 1
            assert stats["records_failed"] == 0
        assert database.fetch_one("SELECT RecordSpec, DataKubun FROM NL_TC") == {
            "RecordSpec": "TC",
            "DataKubun": "1",
        }


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_invalid_first_status_precedes_standard_schema_migration(
    tmp_path,
    importer_class,
) -> None:
    """An invalid first row cannot authorize an unrelated additive ALTER."""

    race_without_youbi = JRAVAN_SCHEMAS["RACE"].replace(
        "            YoubiCD                        VARCHAR(1)          ,  -- 文字列(1)\n",
        "",
    )
    assert race_without_youbi != JRAVAN_SCHEMAS["RACE"], (
        "RACE schema text changed; update the YoubiCD removal fixture"
    )
    database = SQLiteDatabase({"path": str(tmp_path / "standard-preflight.db")})
    with database:
        database.execute(race_without_youbi)
        database.commit()
        before = database.fetch_all('PRAGMA table_info("RACE")')
        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            importer_class(database, use_jravan_schema=True).import_records(
                iter([_tc_record(DataKubun="0")])
            )
        after = database.fetch_all('PRAGMA table_info("RACE")')

    assert after == before


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_caller_owned_batch_rolls_back_an_earlier_flush_on_later_invalid_status(
    tmp_path,
    importer_class,
) -> None:
    database = SQLiteDatabase({"path": str(tmp_path / "later-invalid.db")})
    with database:
        database.execute(SCHEMAS["NL_TC"])
        database.commit()
        importer = importer_class(database, batch_size=1)
        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            importer.import_records(
                iter([_tc_record(), _tc_record(DataKubun="0")]),
                auto_commit=False,
            )
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TC")["count"] == 0
        assert database.has_pending_transaction() is False
        assert importer.get_statistics()["records_imported"] == 0
        assert importer.get_statistics()["batches_processed"] == 0


@pytest.mark.parametrize(("entry_name", "importer_class", "single"), ENTRY_POINTS)
def test_first_header_failure_rolls_back_an_existing_caller_owned_sequence(
    tmp_path,
    entry_name: str,
    importer_class: type,
    single: bool,
) -> None:
    """Validation before setup must still unwind an already-active sequence."""

    database = SQLiteDatabase({"path": str(tmp_path / f"existing-{entry_name}.db")})
    with database:
        database.execute(SCHEMAS["NL_TC"])
        database.commit()
        importer = importer_class(database)
        if single:
            assert importer.import_single_record(_tc_record(), auto_commit=False) is True
        else:
            stats = importer.import_records(iter([_tc_record()]), auto_commit=False)
            assert stats["records_imported"] == 1
        assert database.has_pending_transaction() is True

        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            if single:
                importer.import_single_record(
                    _tc_record(DataKubun="0"),
                    auto_commit=False,
                )
            else:
                importer.import_records(
                    iter([_tc_record(DataKubun="0")]),
                    auto_commit=False,
                )

        assert database.has_pending_transaction() is False
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TC")["count"] == 0
        assert importer.get_statistics()["records_imported"] == 0
        assert importer.get_statistics()["batches_processed"] == 0


@pytest.mark.parametrize(("entry_name", "importer_class", "single"), ENTRY_POINTS)
def test_first_header_state_inspection_failure_invalidates_the_connection(
    tmp_path,
    entry_name: str,
    importer_class: type,
    single: bool,
) -> None:
    """Unknown transaction state is unsafe, never permission to keep writing."""

    path = tmp_path / f"inspection-{entry_name}.db"
    database = _PendingInspectionFailureSQLite({"path": str(path)})
    with database:
        database.execute(SCHEMAS["NL_TC"])
        database.commit()
        importer = importer_class(database)
        if single:
            assert importer.import_single_record(_tc_record(), auto_commit=False) is True
        else:
            assert (
                importer.import_records(iter([_tc_record()]), auto_commit=False)["records_imported"]
                == 1
            )
        database.fail_next_pending_inspection = True

        with pytest.raises(TransactionRecoveryError, match="inspection"):
            if single:
                importer.import_single_record(
                    _tc_record(DataKubun="0"),
                    auto_commit=False,
                )
            else:
                importer.import_records(
                    iter([_tc_record(DataKubun="0")]),
                    auto_commit=False,
                )

        assert database.is_connected() is False
        assert importer.get_statistics()["records_imported"] == 0
        assert importer.get_statistics()["batches_processed"] == 0

    reopened = SQLiteDatabase({"path": str(path)})
    with reopened:
        assert reopened.fetch_one("SELECT COUNT(*) AS count FROM NL_TC")["count"] == 0

    failure_path = tmp_path / f"invalidation-failure-{entry_name}.db"
    recovery_failure = _PendingInspectionFailureSQLite(
        {"path": str(failure_path)}
    )
    with recovery_failure:
        recovery_failure.execute(SCHEMAS["NL_TC"])
        recovery_failure.commit()
        importer = importer_class(recovery_failure)
        if single:
            assert importer.import_single_record(_tc_record(), auto_commit=False) is True
        else:
            assert (
                importer.import_records(
                    iter([_tc_record()]), auto_commit=False
                )["records_imported"]
                == 1
            )
        recovery_failure.fail_next_pending_inspection = True
        recovery_failure.fail_next_invalidation = True

        with pytest.raises(TransactionRecoveryError, match="invalidation failed"):
            if single:
                importer.import_single_record(
                    _tc_record(DataKubun="0"), auto_commit=False
                )
            else:
                importer.import_records(
                    iter([_tc_record(DataKubun="0")]), auto_commit=False
                )

        assert recovery_failure.is_connected() is True
        assert recovery_failure.has_pending_transaction() is True
        assert importer.get_statistics()["records_imported"] == 1
        assert importer.get_statistics()["batches_processed"] == (0 if single else 1)
        recovery_failure.rollback()

    if single:
        committed_path = tmp_path / "inspection-single-committed.db"
        committed = _PendingInspectionFailureSQLite(
            {"path": str(committed_path)}
        )
        with committed:
            committed.execute(SCHEMAS["NL_TC"])
            committed.commit()
            importer = importer_class(committed)
            assert importer.import_single_record(
                _tc_record(), auto_commit=False
            ) is True
            committed.commit()
            assert importer.get_statistics()["records_imported"] == 1
            committed.fail_next_pending_inspection = True

            with pytest.raises(TransactionRecoveryError, match="inspection"):
                importer.import_single_record(
                    _tc_record(DataKubun="0"), auto_commit=False
                )

            assert committed.is_connected() is False
            assert importer.get_statistics()["records_imported"] == 1
            assert importer.get_statistics()["batches_processed"] == 0

        committed_reopened = SQLiteDatabase({"path": str(committed_path)})
        with committed_reopened:
            assert committed_reopened.fetch_one(
                "SELECT COUNT(*) AS count FROM NL_TC"
            )["count"] == 1


@pytest.mark.parametrize("importer_class", (DataImporter, OptimizedDataImporter))
def test_auto_commit_stream_keeps_an_earlier_valid_flush_on_later_rejection(
    tmp_path,
    importer_class,
) -> None:
    """Auto-commit is incremental; only an uncommitted call is atomic."""

    database = SQLiteDatabase({"path": str(tmp_path / "auto-commit-stream.db")})
    with database:
        database.execute(SCHEMAS["NL_TC"])
        database.commit()
        importer = importer_class(database, batch_size=1)
        with pytest.raises(SchemaMigrationError, match="DataKubun"):
            importer.import_records(iter([_tc_record(), _tc_record(DataKubun="0")]))
        assert database.fetch_one("SELECT COUNT(*) AS count FROM NL_TC")["count"] == 1
        assert database.has_pending_transaction() is False


@pytest.mark.parametrize(
    "record",
    (
        {"RecordSpec": "TC"},
        {"RecordSpec": "TC", "DataKubun": ""},
        {"RecordSpec": "TC", "DataKubun": None},
        {"RecordSpec": "TC", "DataKubun": 1},
        {"RecordSpec": "TC", "DataKubun": "11"},
        {"RecordSpec": "TC", "DataKubun": "1", "headDataKubun": "0"},
    ),
)
def test_mapping_header_rejects_missing_malformed_or_conflicting_status(record) -> None:
    with pytest.raises(ValueError, match="DataKubun"):
        validate_record_header(record)
