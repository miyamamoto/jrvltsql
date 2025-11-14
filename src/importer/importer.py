"""Data importer for JLTSQL.

This module imports parsed JV-Data records into database.
"""

from typing import Dict, Iterator, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImporterError(Exception):
    """Data importer error."""

    pass


class DataImporter:
    """Importer for JV-Data records.

    Handles batch insertion of parsed records into database with
    error handling and statistics tracking.

    Attributes:
        database: Database handler instance
        batch_size: Number of records to insert per batch
    """

    def __init__(
        self,
        database: BaseDatabase,
        batch_size: int = 1000,
    ):
        """Initialize data importer.

        Args:
            database: Database handler instance
            batch_size: Records per batch (default: 1000)
        """
        self.database = database
        self.batch_size = batch_size

        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Map record types to table names
        self._table_map = {
            "RA": "NL_RA_RACE",
            "SE": "NL_SE_RACE_UMA",
            "HR": "NL_HR_PAY",
        }

        logger.info(
            "DataImporter initialized",
            batch_size=batch_size,
        )

    def import_records(
        self,
        records: Iterator[dict],
        auto_commit: bool = True,
    ) -> Dict[str, int]:
        """Import records into database.

        Args:
            records: Iterator of parsed record dictionaries
            auto_commit: Whether to auto-commit after each batch

        Returns:
            Dictionary with import statistics

        Raises:
            ImporterError: If import fails

        Examples:
            >>> from src.database.sqlite_handler import SQLiteDatabase
            >>> db = SQLiteDatabase({"path": "./test.db"})
            >>> importer = DataImporter(db)
            >>> with db:
            ...     stats = importer.import_records(records)
            ...     print(f"Imported {stats['records_imported']} records")
        """
        # Reset statistics
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

        # Group records by type for batch insertion
        batch_buffers: Dict[str, List[dict]] = {}

        try:
            for record in records:
                # Get record type and table name
                record_type = record.get("headRecordSpec")
                if not record_type:
                    logger.warning("Record missing headRecordSpec")
                    self._records_failed += 1
                    continue

                table_name = self._table_map.get(record_type)
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
                    self._flush_batch(
                        table_name,
                        batch_buffers[table_name],
                        auto_commit,
                    )
                    batch_buffers[table_name] = []

            # Flush remaining batches
            for table_name, batch in batch_buffers.items():
                if batch:
                    self._flush_batch(table_name, batch, auto_commit)

            # Log summary
            stats = self.get_statistics()
            logger.info("Import completed", **stats)

            return stats

        except Exception as e:
            logger.error("Import failed", error=str(e))
            raise ImporterError(f"Failed to import records: {e}")

    def _flush_batch(
        self,
        table_name: str,
        batch: List[dict],
        auto_commit: bool,
    ):
        """Flush a batch of records to database.

        Args:
            table_name: Target table name
            batch: List of record dictionaries
            auto_commit: Whether to commit after insertion
        """
        if not batch:
            return

        try:
            # Insert batch
            rows = self.database.insert_many(table_name, batch)

            self._records_imported += rows
            self._batches_processed += 1

            if auto_commit:
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

                    if auto_commit:
                        self.database.commit()

                except DatabaseError as e:
                    self._records_failed += 1
                    logger.error(
                        "Failed to insert record",
                        table=table_name,
                        error=str(e),
                    )

    def import_single_record(
        self,
        record: dict,
        auto_commit: bool = True,
    ) -> bool:
        """Import single record.

        Args:
            record: Parsed record dictionary
            auto_commit: Whether to commit after insertion

        Returns:
            True if successful, False otherwise
        """
        record_type = record.get("headRecordSpec")
        if not record_type:
            logger.warning("Record missing headRecordSpec")
            return False

        table_name = self._table_map.get(record_type)
        if not table_name:
            logger.warning(f"Unknown record type: {record_type}")
            return False

        try:
            self.database.insert(table_name, record)
            self._records_imported += 1

            if auto_commit:
                self.database.commit()

            return True

        except DatabaseError as e:
            self._records_failed += 1
            logger.error("Failed to insert record", error=str(e))
            return False

    def get_statistics(self) -> Dict[str, int]:
        """Get import statistics.

        Returns:
            Dictionary with import statistics
        """
        return {
            "records_imported": self._records_imported,
            "records_failed": self._records_failed,
            "batches_processed": self._batches_processed,
        }

    def reset_statistics(self):
        """Reset import statistics."""
        self._records_imported = 0
        self._records_failed = 0
        self._batches_processed = 0

    def add_table_mapping(self, record_type: str, table_name: str):
        """Add custom table mapping.

        Args:
            record_type: Record type code (e.g., "RA")
            table_name: Target table name
        """
        self._table_map[record_type] = table_name
        logger.info(f"Added table mapping: {record_type} -> {table_name}")

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DataImporter "
            f"imported={self._records_imported} "
            f"failed={self._records_failed} "
            f"batches={self._batches_processed}>"
        )
