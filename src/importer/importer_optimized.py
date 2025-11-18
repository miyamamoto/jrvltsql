"""Optimized data importer for JLTSQL.

This module provides optimized import strategies for different database backends.
Key optimizations:
- Single transaction for entire import
- Uses database-specific bulk insert APIs
- Adaptive batch sizing based on performance
"""

from typing import Dict, Iterator, List, Optional
from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizedDataImporter:
    """Optimized importer for JV-Data records.

    Handles batch insertion with database-specific optimizations:
    - DuckDB: Uses appender API with single transaction
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

        # Detect database type for optimization
        self.db_type = self._detect_database_type()

        # Map record types to table names (same as original)
        self._table_map = {
            "RA": "NL_RA", "SE": "NL_SE", "HR": "NL_HR", "JG": "NL_JG",
            "H1": "NL_H1", "H6": "NL_H6", "O1": "NL_O1", "O2": "NL_O2",
            "O3": "NL_O3", "O4": "NL_O4", "O5": "NL_O5", "O6": "NL_O6",
            "YS": "NL_YS", "UM": "NL_UM", "KS": "NL_KS", "CH": "NL_CH",
            "BR": "NL_BR", "BN": "NL_BN", "HN": "NL_HN", "SK": "NL_SK",
            "RC": "NL_RC", "CC": "NL_CC", "TC": "NL_TC", "CS": "NL_CS",
            "CK": "NL_CK", "WC": "NL_WC", "AV": "NL_AV", "JC": "NL_JC",
            "HC": "NL_HC", "HS": "NL_HS", "HY": "NL_HY", "WE": "NL_WE",
            "WF": "NL_WF", "WH": "NL_WH", "TM": "NL_TM", "TK": "NL_TK",
            "BT": "NL_BT", "DM": "NL_DM",
        }

        logger.info(
            "OptimizedDataImporter initialized",
            batch_size=batch_size,
            db_type=self.db_type,
            use_jravan_schema=use_jravan_schema,
        )

    def _detect_database_type(self) -> str:
        """Detect database type from handler class."""
        class_name = self.database.__class__.__name__
        if "DuckDB" in class_name:
            return "duckdb"
        elif "PostgreSQL" in class_name:
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
            from src.database.table_mappings import JLTSQL_TO_JRAVAN
            return JLTSQL_TO_JRAVAN.get(table_name, table_name)

        return table_name

    def import_records(
        self,
        records: Iterator[dict],
        auto_commit: bool = True,
    ) -> Dict[str, int]:
        """Import records with database-specific optimizations.

        For DuckDB: Uses single transaction for entire import
        For PostgreSQL: Already optimized with autocommit
        For SQLite: Uses transaction batching

        Args:
            records: Iterator of parsed record dictionaries
            auto_commit: Whether to auto-commit (entire import for DuckDB)

        Returns:
            Dictionary with import statistics
        """
        # Reset statistics
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}

        # Start transaction for entire import (DuckDB optimization)
        transaction_started = False
        if self.db_type == "duckdb" and auto_commit:
            try:
                # Check if database has begin_transaction method
                if hasattr(self.database, 'begin_transaction'):
                    self.database.begin_transaction()
                else:
                    self.database.execute("BEGIN TRANSACTION")
                transaction_started = True
                logger.info("Started single transaction for entire DuckDB import")
            except Exception as e:
                logger.warning(f"Could not start transaction: {e}")

        try:
            for record in records:
                # Get record type and table name
                record_type = (
                    record.get("レコード種別ID") or
                    record.get("RecordSpec") or
                    record.get("headRecordSpec")
                )
                if not record_type:
                    logger.warning(
                        "Record missing record type field",
                        record_keys=list(record.keys())[:5] if record else None
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

                # Add to batch buffer
                if table_name not in batch_buffers:
                    batch_buffers[table_name] = []

                batch_buffers[table_name].append(record)

                # Check if any batch is full
                if len(batch_buffers[table_name]) >= self.batch_size:
                    self._flush_batch_optimized(
                        table_name,
                        batch_buffers[table_name],
                        commit_batch=(not transaction_started)  # Only commit if not in transaction
                    )
                    batch_buffers[table_name] = []

            # Flush remaining batches
            for table_name, batch in batch_buffers.items():
                if batch:
                    self._flush_batch_optimized(
                        table_name,
                        batch,
                        commit_batch=(not transaction_started)
                    )

            # Single commit for entire import (DuckDB optimization)
            if transaction_started and auto_commit:
                self.database.commit()
                logger.info("Committed single transaction for entire import")

            # Log summary
            stats = self.get_statistics()
            logger.info("Import completed", **stats)

            return stats

        except Exception as e:
            logger.error("Import failed", error=str(e))

            # Rollback if in transaction
            if transaction_started:
                try:
                    self.database.rollback()
                    logger.info("Rolled back transaction due to error")
                except:
                    pass

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

        try:
            # Use optimized insert if available
            if hasattr(self.database, 'insert_many_optimized'):
                # DuckDB optimized path
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
                f"Batch inserted",
                table=table_name,
                records=rows,
                batch_num=self._batches_processed,
            )

        except DatabaseError as e:
            # Try inserting one by one on batch failure
            logger.warning(
                f"Batch insert failed, trying individual inserts",
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

    def get_statistics(self) -> Dict[str, int]:
        """Get import statistics."""
        return {
            "records_imported": self._records_imported,
            "records_failed": self._records_failed,
            "batches_processed": self._batches_processed,
            "success_rate": (
                self._records_imported * 100 /
                (self._records_imported + self._records_failed)
                if (self._records_imported + self._records_failed) > 0
                else 0
            ),
        }