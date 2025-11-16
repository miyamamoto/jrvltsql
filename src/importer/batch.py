"""Batch processing utilities for JLTSQL.

This module provides utilities for batch processing of JV-Data.
"""

from datetime import datetime, timedelta
from typing import Iterator, List, Optional, Tuple

from src.database.base import BaseDatabase
from src.database.schema import create_all_tables
from src.fetcher.historical import HistoricalFetcher
from src.importer.importer import DataImporter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for JV-Data import.

    Coordinates fetching, parsing, and importing of JV-Data in batches.

    Note:
        Service key must be configured in JRA-VAN DataLab application
        before using this class.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> processor = BatchProcessor(database=db)
        >>> with db:
        ...     processor.process_date_range(
        ...         data_spec="RACE",
        ...         from_date="20240601",
        ...         to_date="20240630",
        ...     )
    """

    def __init__(
        self,
        database: BaseDatabase,
        batch_size: int = 1000,
        sid: str = "UNKNOWN",
    ):
        """Initialize batch processor.

        Args:
            database: Database handler instance
            batch_size: Records per batch
            sid: Session ID for JV-Link API (default: "UNKNOWN")
                 Note: This is NOT the service key. Service key must be
                 configured in JRA-VAN DataLab application.
        """
        self.fetcher = HistoricalFetcher(sid)
        self.importer = DataImporter(database, batch_size)
        self.database = database

        logger.info("BatchProcessor initialized", sid=sid)

    def process_date_range(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int = 0,
        auto_commit: bool = True,
        ensure_tables: bool = True,
    ) -> dict:
        """Process data for a date range.

        Args:
            data_spec: Data specification code
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            option: JVOpen option (0=normal, 1=setup, 2=update)
            auto_commit: Whether to auto-commit
            ensure_tables: Whether to ensure tables exist

        Returns:
            Dictionary with processing statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_date_range("RACE", "20240601", "20240630")
            >>> print(f"Imported {stats['records_imported']} records")
        """
        logger.info(
            "Starting batch processing",
            data_spec=data_spec,
            from_date=from_date,
            to_date=to_date,
            option=option,
        )

        # Ensure tables exist
        if ensure_tables:
            logger.info("Ensuring all tables exist")
            try:
                create_all_tables(self.database)
            except Exception as e:
                logger.debug(f"Tables might already exist: {e}")

        # Fetch and import records
        try:
            records = self.fetcher.fetch(data_spec, from_date, to_date, option)
            import_stats = self.importer.import_records(records, auto_commit)

            # Combine statistics
            fetch_stats = self.fetcher.get_statistics()
            combined_stats = {
                **fetch_stats,
                **import_stats,
            }

            logger.info("Batch processing completed", **combined_stats)

            return combined_stats

        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise

    def process_month(
        self,
        year: int,
        month: int,
        data_spec: str = "RACE",
        auto_commit: bool = True,
    ) -> dict:
        """Process data for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            data_spec: Data specification code
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with processing statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_month(2024, 6, "RACE")
        """
        # Calculate date range
        start = datetime(year, month, 1)

        # Last day of month
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)

        from_date = start.strftime("%Y%m%d")
        to_date = end.strftime("%Y%m%d")

        logger.info(f"Processing month: {year}/{month:02d}")

        return self.process_date_range(data_spec, from_date, to_date, auto_commit)

    def process_year(
        self,
        year: int,
        data_spec: str = "RACE",
        auto_commit: bool = True,
    ) -> dict:
        """Process data for a specific year.

        Args:
            year: Year (e.g., 2024)
            data_spec: Data specification code
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary with processing statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> stats = processor.process_year(2024, "RACE")
        """
        from_date = f"{year}0101"
        to_date = f"{year}1231"

        logger.info(f"Processing year: {year}")

        return self.process_date_range(data_spec, from_date, to_date, auto_commit)

    def process_multiple_specs(
        self,
        data_specs: List[str],
        from_date: str,
        to_date: str,
        auto_commit: bool = True,
    ) -> dict:
        """Process multiple data specifications.

        Args:
            data_specs: List of data specification codes
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            auto_commit: Whether to auto-commit

        Returns:
            Dictionary mapping data_spec to statistics

        Examples:
            >>> processor = BatchProcessor(database=db)
            >>> specs = ["RACE", "DIFF"]
            >>> results = processor.process_multiple_specs(
            ...     specs, "20240601", "20240630"
            ... )
        """
        results = {}

        for data_spec in data_specs:
            logger.info(f"Processing data spec: {data_spec}")

            try:
                stats = self.process_date_range(
                    data_spec,
                    from_date,
                    to_date,
                    auto_commit,
                    ensure_tables=False,  # Only check once
                )
                results[data_spec] = stats

            except Exception as e:
                logger.error(
                    f"Failed to process {data_spec}",
                    data_spec=data_spec,
                    error=str(e),
                )
                results[data_spec] = {"error": str(e)}

        return results

    def get_combined_statistics(self) -> dict:
        """Get combined statistics from fetcher and importer.

        Returns:
            Dictionary with combined statistics
        """
        return {
            **self.fetcher.get_statistics(),
            **self.importer.get_statistics(),
        }

    def reset_statistics(self):
        """Reset all statistics."""
        self.fetcher.reset_statistics()
        self.importer.reset_statistics()
