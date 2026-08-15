"""Optimized data importer for JLTSQL.

This module provides optimized import strategies for different database backends.
Key optimizations:
- Single transaction for entire import
- Uses database-specific bulk insert APIs
- Adaptive batch sizing based on performance
"""

from typing import Dict, Iterator, List, Optional, Union

from src.database.base import BaseDatabase, DatabaseError
from src.database.migration import SchemaMigrationError
from src.importer.importer import (
    _PREPARED_CH_SEISEKI_ROWS_KEY,
    _PREPARED_KS_SEISEKI_ROWS_KEY,
    _delete_mining_race_rows,
    _expanded_record_fingerprint,
    _is_mining_race_delete,
    _is_mining_snapshot_follower,
    _mining_native_snapshot_rows,
    _record_type_from_record,
    insert_ch_coupled_batch,
    insert_ks_coupled_batch,
    prepare_ch_coupled_rows,
    prepare_ks_coupled_rows,
    replace_mining_native_snapshot,
    resolve_standard_table_name,
    verify_ch_coupled_table,
    verify_ks_coupled_table,
    verify_mining_native_schema,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizedDataImporter:
    """Optimized importer for JV-Data records.

    Handles batch insertion with database-specific optimizations:
    - PostgreSQL: Uses autocommit mode (already optimized)
    - SQLite: Uses transaction batching

    Attributes:
        database: Database handler instance
        batch_size: Number of records to insert per batch
        use_jravan_schema: Whether to use JRA-VAN standard table names
    """

    def __init__(
        self,
        database: BaseDatabase,
        batch_size: int = 1000,
        use_jravan_schema: bool = False,
    ):
        """Initialize optimized data importer."""
        self.database = database
        self.batch_size = batch_size
        self.use_jravan_schema = use_jravan_schema

        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0
        self._jravan_tables_ready = not use_jravan_schema
        self._verified_mining_native_tables: set[str] = set()

        # Detect database type for optimization
        self.db_type = self._detect_database_type()

        # Map record types to table names (same as original)
        self._table_map = {
            "RA": "NL_RA",
            "SE": "NL_SE",
            "HR": "NL_HR",
            "JG": "NL_JG",
            "H1": "NL_H1",
            "H6": "NL_H6",
            "O1": "NL_O1",
            "O2": "NL_O2",
            "O3": "NL_O3",
            "O4": "NL_O4",
            "O5": "NL_O5",
            "O6": "NL_O6",
            "YS": "NL_YS",
            "UM": "NL_UM",
            "KS": "NL_KS",
            "CH": "NL_CH",
            "BR": "NL_BR",
            "BN": "NL_BN",
            "HN": "NL_HN",
            "SK": "NL_SK",
            "RC": "NL_RC",
            "CC": "NL_CC",
            "TC": "NL_TC",
            "CS": "NL_CS",
            "CK": "NL_CK",
            "WC": "NL_WC",
            "AV": "NL_AV",
            "JC": "NL_JC",
            "HC": "NL_HC",
            "HS": "NL_HS",
            "HY": "NL_HY",
            "WE": "NL_WE",
            "WF": "NL_WF",
            "WH": "NL_WH",
            "TM": "NL_TM",
            "TK": "NL_TK",
            "BT": "NL_BT",
            "DM": "NL_DM",
        }

        logger.info(
            "OptimizedDataImporter initialized",
            batch_size=batch_size,
            db_type=self.db_type,
            use_jravan_schema=use_jravan_schema,
        )

    def _migrate_existing_jravan_tables(self, *, commit: bool) -> None:
        """Add newly supported columns to existing standard-name tables."""
        from src.database.migration import migrate_table_if_needed, verify_table_schema
        from src.database.schema_jravan import JRAVAN_SCHEMAS
        from src.database.table_mappings import JLTSQL_TO_JRAVAN

        for native_name in set(self._table_map.values()):
            standard_name = JLTSQL_TO_JRAVAN.get(native_name, native_name)
            schema_sql = JRAVAN_SCHEMAS.get(standard_name)
            if schema_sql and self.database.table_exists(standard_name):
                migrate_table_if_needed(self.database, standard_name, schema_sql, commit=commit)
                verify_table_schema(self.database, standard_name, schema_sql)
        for child_table in ("CHOKYO_SEISEKI", "KISYU_SEISEKI"):
            child_schema = JRAVAN_SCHEMAS.get(child_table)
            if child_schema and self.database.table_exists(child_table):
                migrate_table_if_needed(
                    self.database,
                    child_table,
                    child_schema,
                    commit=commit,
                )
                verify_table_schema(self.database, child_table, child_schema)

    def _ensure_jravan_tables_ready(self, *, auto_commit: bool) -> None:
        """Migrate standard-name tables only after the DB is connected."""
        if self._jravan_tables_ready:
            return
        if not self.database.is_connected():
            from src.importer.importer import ImporterError

            raise ImporterError("JRA-VAN schema import requires a connected database")
        self._migrate_existing_jravan_tables(commit=auto_commit)
        if auto_commit:
            self._jravan_tables_ready = True

    def _detect_database_type(self) -> str:
        """Detect database type from handler class."""
        class_name = self.database.__class__.__name__
        if "PostgreSQL" in class_name:
            return "postgresql"
        elif "SQLite" in class_name:
            return "sqlite"
        else:
            return "unknown"

    def _get_table_name(self, record_type: str) -> Optional[str]:
        """Get table name for record type."""
        table_name = self._table_map.get(record_type)
        if not table_name:
            return None

        if self.use_jravan_schema:
            return resolve_standard_table_name(self.database, table_name)

        return table_name

    @staticmethod
    def _clean_record(record: dict) -> dict:
        metadata_fields = {
            "headRecordSpec",
            "レコード種別ID",
            "_raw_data",
            "_parse_errors",
            "RecordDelimiter",
            "RecordSeparator",
        }
        return {
            key: value
            for key, value in record.items()
            if key not in metadata_fields and not key.startswith("_")
        }

    @classmethod
    def _record_for_table(cls, record: dict, table_name: str) -> dict:
        """Return the parser representation required by the target schema."""
        if table_name in {"BATAIJYU", "MINING", "TAISENGATA_MINING"}:
            wide_record = record.get("_wide_record")
            if isinstance(wide_record, dict):
                return cls._clean_record(wide_record)
        from src.importer.importer import translate_standard_field_names

        return translate_standard_field_names(cls._clean_record(record), table_name)

    @staticmethod
    def _convert_record(record: dict, table_name: str) -> dict:
        from src.importer.importer import convert_record_types

        return convert_record_types(record, table_name)

    @staticmethod
    def _has_complete_primary_key(table_name: str, record: dict) -> bool:
        from src.database.schema_types import get_table_primary_key_columns
        from src.database.table_mappings import JRAVAN_TO_JLTSQL

        primary_keys = get_table_primary_key_columns(table_name)
        if not primary_keys:
            primary_keys = get_table_primary_key_columns(
                JRAVAN_TO_JLTSQL.get(table_name, table_name)
            )
        return not primary_keys or all(record.get(key) not in (None, "") for key in primary_keys)

    def import_records(
        self,
        records: Iterator[dict],
        auto_commit: bool = True,
    ) -> Dict[str, int]:
        """Import records with database-specific optimizations.

        For PostgreSQL: Already optimized with autocommit
        For SQLite: Uses transaction batching

        Args:
            records: Iterator of parsed record dictionaries
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with import statistics
        """
        if not auto_commit:
            self.database.begin_transaction()
        self._ensure_jravan_tables_ready(auto_commit=auto_commit)

        # Reset statistics
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}
        verified_ch_result_tables: Dict[str, str] = {}
        verified_ks_result_tables: Dict[str, str] = {}
        last_expanded_record_fingerprint = None

        try:
            for record in records:
                # Get record type and table name
                record_type = _record_type_from_record(record)
                if not record_type:
                    logger.warning(
                        "Record missing record type field",
                        record_keys=list(record.keys())[:5] if record else None,
                    )
                    self._records_failed += 1
                    continue

                table_name = self._get_table_name(record_type)
                if not table_name:
                    logger.warning(
                        f"Unknown record type: {record_type}",
                        record_type=record_type,
                    )
                    self._records_failed += 1
                    continue

                if table_name not in self._verified_mining_native_tables:
                    if verify_mining_native_schema(self.database, record, table_name):
                        self._verified_mining_native_tables.add(table_name)

                if _is_mining_race_delete(record, table_name):
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
                        batch_buffers[table_name] = []
                    _delete_mining_race_rows(self.database, record, table_name)
                    self._records_imported += 1
                    self._batches_processed += 1
                    if auto_commit:
                        self.database.commit()
                    last_expanded_record_fingerprint = None
                    continue

                if _is_mining_snapshot_follower(record, table_name):
                    continue

                mining_snapshot_rows = _mining_native_snapshot_rows(record, table_name)
                if mining_snapshot_rows is not None:
                    pending = batch_buffers.setdefault(table_name, [])
                    if pending:
                        self._flush_batch_optimized(
                            table_name,
                            pending,
                            commit_batch=auto_commit,
                        )
                        batch_buffers[table_name] = []
                    if auto_commit:
                        self.database.begin_transaction()
                    try:
                        rows = replace_mining_native_snapshot(
                            self.database, record, table_name
                        )
                        if auto_commit:
                            self.database.commit()
                    except Exception:
                        self.database.rollback()
                        raise
                    self._records_imported += rows
                    self._batches_processed += 1
                    continue

                fingerprint = _expanded_record_fingerprint(record, table_name)
                if fingerprint is not None:
                    if fingerprint == last_expanded_record_fingerprint:
                        continue
                    last_expanded_record_fingerprint = fingerprint

                # Add to batch buffer
                if table_name not in batch_buffers:
                    batch_buffers[table_name] = []

                clean_record = self._record_for_table(record, table_name)
                converted_record = self._convert_record(clean_record, table_name)
                if not self._has_complete_primary_key(table_name, converted_record):
                    logger.warning(
                        "Record has incomplete primary key after conversion",
                        table=table_name,
                    )
                    self._records_failed += 1
                    continue
                if (
                    table_name in ("NL_CH", "CHOKYO")
                    and table_name not in verified_ch_result_tables
                ):
                    try:
                        result_table = verify_ch_coupled_table(self.database, table_name)
                    except DatabaseError as error:
                        if not auto_commit:
                            raise
                        logger.warning(
                            "CH result schema verification failed, retrying coupled import",
                            table=table_name,
                            error=str(error),
                        )
                        self.database.rollback()
                        result_table = verify_ch_coupled_table(self.database, table_name)
                    if result_table is None:
                        raise SchemaMigrationError(
                            f"CH import could not resolve normalized table for {table_name}"
                        )
                    verified_ch_result_tables[table_name] = result_table
                if table_name in ("NL_KS", "KISYU") and table_name not in verified_ks_result_tables:
                    try:
                        result_table = verify_ks_coupled_table(self.database, table_name)
                    except DatabaseError as error:
                        if not auto_commit:
                            raise
                        logger.warning(
                            "KS result schema verification failed, retrying coupled import",
                            table=table_name,
                            error=str(error),
                        )
                        self.database.rollback()
                        result_table = verify_ks_coupled_table(self.database, table_name)
                    if result_table is None:
                        raise SchemaMigrationError(
                            f"KS import could not resolve normalized table for {table_name}"
                        )
                    verified_ks_result_tables[table_name] = result_table
                coupled = prepare_ch_coupled_rows(
                    self.database,
                    record,
                    table_name,
                    verified_result_table=verified_ch_result_tables.get(table_name),
                )
                if coupled is not None:
                    converted_record[_PREPARED_CH_SEISEKI_ROWS_KEY] = coupled
                ks_coupled = prepare_ks_coupled_rows(
                    self.database,
                    record,
                    table_name,
                    verified_result_table=verified_ks_result_tables.get(table_name),
                )
                if ks_coupled is not None:
                    converted_record[_PREPARED_KS_SEISEKI_ROWS_KEY] = ks_coupled
                batch_buffers[table_name].append(converted_record)

                # Check if any batch is full
                if len(batch_buffers[table_name]) >= self.batch_size:
                    self._flush_batch_optimized(
                        table_name,
                        batch_buffers[table_name],
                        commit_batch=auto_commit,
                    )
                    batch_buffers[table_name] = []

            # Flush remaining batches
            for table_name, batch in batch_buffers.items():
                if batch:
                    self._flush_batch_optimized(table_name, batch, commit_batch=auto_commit)

            # Log summary
            stats = self.get_statistics()
            logger.info("Import completed", **stats)

            return stats

        except SchemaMigrationError:
            raise
        except Exception as e:
            logger.error("Import failed", error=str(e))

            from src.importer.importer import ImporterError

            raise ImporterError(f"Failed to import records: {e}")

    def _flush_batch_optimized(
        self,
        table_name: str,
        batch: List[dict],
        commit_batch: bool,
    ):
        """Flush a batch with database-specific optimizations."""
        if not batch:
            return

        prepared_ch = []
        for record in batch:
            coupled = record.get(_PREPARED_CH_SEISEKI_ROWS_KEY)
            if coupled is None:
                continue
            result_table, result_rows = coupled
            main_row = {
                key: value for key, value in record.items() if key != _PREPARED_CH_SEISEKI_ROWS_KEY
            }
            prepared_ch.append((main_row, result_table, result_rows))
        if prepared_ch:
            if len(prepared_ch) != len(batch):
                raise SchemaMigrationError("CH batch lost its coupled result rows")
            succeeded, failed = insert_ch_coupled_batch(
                self.database,
                table_name,
                prepared_ch,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        prepared_ks = []
        for record in batch:
            coupled = record.get(_PREPARED_KS_SEISEKI_ROWS_KEY)
            if coupled is None:
                continue
            result_table, result_rows = coupled
            main_row = {
                key: value for key, value in record.items() if key != _PREPARED_KS_SEISEKI_ROWS_KEY
            }
            prepared_ks.append((main_row, result_table, result_rows))
        if prepared_ks:
            if len(prepared_ks) != len(batch):
                raise SchemaMigrationError("KS batch lost its coupled result rows")
            succeeded, failed = insert_ks_coupled_batch(
                self.database,
                table_name,
                prepared_ks,
                commit_batch=commit_batch,
                optimized=True,
            )
            self._records_imported += succeeded
            self._records_failed += failed
            if succeeded:
                self._batches_processed += 1
            return

        try:
            # Use optimized insert if available
            if hasattr(self.database, "insert_many_optimized"):
                # Optimized path
                rows = self.database.insert_many_optimized(table_name, batch)
            else:
                # Standard insert_many
                rows = self.database.insert_many(table_name, batch)

            self._records_imported += rows
            self._batches_processed += 1

            # Only commit if not in a larger transaction
            if commit_batch:
                self.database.commit()

            logger.debug(
                "Batch inserted",
                table=table_name,
                records=rows,
                batch_num=self._batches_processed,
            )

        except DatabaseError as e:
            if not commit_batch:
                # The backend may already have rolled back the caller-owned
                # transaction. Retrying rows here would create a partial import
                # and make the reported statistics diverge from persisted data.
                raise

            # Try inserting one by one on batch failure
            logger.warning(
                "Batch insert failed, trying individual inserts",
                table=table_name,
                error=str(e),
            )

            for record in batch:
                try:
                    self.database.insert(table_name, record)
                    self._records_imported += 1

                    if commit_batch:
                        self.database.commit()

                except DatabaseError as e:
                    self._records_failed += 1
                    logger.error(
                        "Failed to insert record",
                        table=table_name,
                        error=str(e),
                    )

    def get_statistics(self) -> Dict[str, Union[int, float]]:
        """Get import statistics."""
        return {
            "records_imported": self._records_imported,
            "records_failed": self._records_failed,
            "batches_processed": self._batches_processed,
            "success_rate": (
                self._records_imported * 100 / (self._records_imported + self._records_failed)
                if (self._records_imported + self._records_failed) > 0
                else 0
            ),
        }
