"""Batch processing utilities for JLTSQL.

This module provides utilities for batch processing of JV-Data.
"""

from datetime import datetime, timedelta
from typing import Iterator, List, Optional, Tuple

from src.database.base import BaseDatabase
from src.database.schema import create_all_tables
from src.fetcher.historical import HistoricalFetcher
from src.importer.importer import DataImporter
from src.utils.data_source import DataSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BatchProcessor:
    """Batch processor for JV-Data import.

    Coordinates fetching, parsing, and importing of JV-Data in batches.
    Fetches data from JV-Link starting from the specified date and filters
    records client-side based on the end date.

    Note:
        Service key must be configured in JRA-VAN DataLab application
        before using this class.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> processor = BatchProcessor(database=db)
        >>> with db:
        ...     # Fetches from 20240601 onwards, imports records <= 20240630
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
        service_key: Optional[str] = None,
        initialization_key: Optional[str] = None,
        show_progress: bool = True,
        data_source: DataSource = DataSource.JRA,
    ):
        """Initialize batch processor.

        Args:
            database: Database handler instance
            batch_size: Records per batch
            sid: Session ID for JV-Link/NV-Link API (default: "UNKNOWN")
            service_key: Optional service key. If provided, it will be set
                        programmatically without requiring registry configuration.
            initialization_key: Optional NV-Link initialization key (software ID)
                        used for NVInit when data_source is NAR.
            show_progress: Show stylish progress display (default: True)
            data_source: Data source selection (JRA or NAR, default: JRA)
        """
        self.data_source = data_source
        self.fetcher = HistoricalFetcher(
            sid,
            service_key=service_key,
            initialization_key=initialization_key,
            show_progress=show_progress,
            data_source=data_source,
        )
        self.importer = DataImporter(database, batch_size, data_source=data_source)
        self.database = database

        logger.info(
            "BatchProcessor initialized",
            sid=sid,
            has_service_key=service_key is not None,
            has_initialization_key=initialization_key is not None,
            show_progress=show_progress,
            data_source=data_source.value,
        )

    def process_date_range(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int = 1,
        auto_commit: bool = True,
        ensure_tables: bool = True,
    ) -> dict:
        """Process data for a date range.

        Args:
            data_spec: Data specification code
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD) - records are filtered to this date
            option: JVOpen option:
                    1=通常データ（差分データ取得）
                    2=今週データ（直近のレースのみ）
                    3=セットアップ（全データ取得、ダイアログ表示）
                    4=分割セットアップ（初回のみダイアログ）
            auto_commit: Whether to auto-commit
            ensure_tables: Whether to ensure tables exist

        Returns:
            Dictionary with processing statistics

        Note:
            JV-Link fetches all data from from_date onwards, then filters
            records client-side to only import those with dates <= to_date.

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
            logger.info("Ensuring all tables exist", data_source=self.data_source.value)
            try:
                if self.data_source == DataSource.NAR:
                    # Create NAR tables
                    from src.database.schema_nar import get_nar_schemas
                    nar_schemas = get_nar_schemas()
                    for table_name, schema_sql in nar_schemas.items():
                        try:
                            self.database.execute(schema_sql)
                        except Exception:
                            pass  # Table might already exist
                else:
                    # Create JRA tables (default)
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
        successful_specs = []
        failed_specs = []

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
                successful_specs.append(data_spec)

            except Exception as e:
                logger.error(
                    f"Failed to process {data_spec}",
                    data_spec=data_spec,
                    error=str(e),
                )
                results[data_spec] = {"error": str(e)}
                failed_specs.append(data_spec)

        # Add partial success summary
        total_specs = len(data_specs)
        success_count = len(successful_specs)
        failure_count = len(failed_specs)

        results["_summary"] = {
            "total_specs": total_specs,
            "successful": success_count,
            "failed": failure_count,
            "success_rate": f"{success_count}/{total_specs}",
            "successful_specs": successful_specs,
            "failed_specs": failed_specs,
        }

        # Log partial success summary
        if failure_count > 0:
            logger.warning(
                f"Partial success: {success_count}/{total_specs} specs completed successfully",
                successful=success_count,
                failed=failure_count,
                successful_specs=successful_specs,
                failed_specs=failed_specs,
            )
        else:
            logger.info(
                f"All specs completed successfully: {success_count}/{total_specs}",
                successful_specs=successful_specs,
            )

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
