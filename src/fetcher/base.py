"""Base data fetcher for JLTSQL.

This module provides the base class for fetching JV-Data from JV-Link.
"""

import time
from abc import ABC, abstractmethod
from typing import Iterator, Optional

from src.jvlink.constants import JV_READ_NO_MORE_DATA, JV_READ_SUCCESS
from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.utils.logger import get_logger
from src.utils.progress import JVLinkProgressDisplay

logger = get_logger(__name__)


class FetcherError(Exception):
    """Data fetcher error."""

    pass


class BaseFetcher(ABC):
    """Abstract base class for data fetchers.

    This class provides common functionality for fetching and parsing
    JV-Data records from JV-Link.

    Note:
        Service key can be provided programmatically or configured in
        JRA-VAN DataLab application/registry.

    Attributes:
        jvlink: JV-Link wrapper instance
        parser_factory: Parser factory instance
    """

    def __init__(
        self,
        sid: str = "UNKNOWN",
        service_key: Optional[str] = None,
        show_progress: bool = True,
    ):
        """Initialize base fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "UNKNOWN")
            service_key: Optional JV-Link service key. If provided, it will be set
                        programmatically without requiring registry configuration.
                        If not provided, the service key must be configured in
                        JRA-VAN DataLab application or registry.
            show_progress: Show stylish progress display (default: True)
        """
        self.jvlink = JVLinkWrapper(sid)
        self.parser_factory = ParserFactory()
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0
        self._files_processed = 0
        self._total_files = 0
        self._service_key = service_key
        self.show_progress = show_progress
        self.progress_display: Optional[JVLinkProgressDisplay] = None
        self._start_time = None

        logger.info(f"{self.__class__.__name__} initialized", sid=sid,
                   has_service_key=service_key is not None)

    @abstractmethod
    def fetch(self, **kwargs) -> Iterator[dict]:
        """Fetch and parse records.

        This method should be implemented by subclasses to fetch records
        from JV-Link and yield parsed data.

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If fetching fails
        """
        pass

    def _fetch_and_parse(self, task_id: Optional[int] = None, to_date: Optional[str] = None) -> Iterator[dict]:
        """Internal method to fetch and parse records.

        Args:
            task_id: Progress task ID (optional)
            to_date: End date in YYYYMMDD format (optional, for filtering records)

        Yields:
            Dictionary of parsed record data
        """
        self._start_time = time.time()
        last_update_time = self._start_time
        update_interval = 0.1  # Update progress every 0.1 seconds

        while True:
            try:
                # Read next record
                ret_code, buff, filename = self.jvlink.jv_read()

                # Return code meanings:
                # > 0: Success with data (value is data length)
                # 0: Read complete (no more data)
                # -1: File switch (continue reading)
                # < -1: Error

                if ret_code == JV_READ_SUCCESS:
                    # Complete (0)
                    logger.info("Read complete - no more data")
                    if self.progress_display and task_id is not None:
                        self.progress_display.update(task_id, status="読込完了")
                    break

                elif ret_code == JV_READ_NO_MORE_DATA:
                    # File switch (-1) - ファイル処理完了
                    self._files_processed += 1
                    # Note: File switch is very frequent, so no debug logging here
                    continue

                elif ret_code > 0:
                    # Success with data (ret_code is data length)
                    self._records_fetched += 1

                    # Parse record
                    try:
                        data = self.parser_factory.parse(buff)
                        if data:
                            # Filter by to_date if specified
                            if to_date and not self._is_within_date_range(data, to_date):
                                # Skip records after to_date
                                logger.debug(
                                    "Skipping record outside date range",
                                    record_num=self._records_fetched,
                                    to_date=to_date,
                                )
                                continue

                            self._records_parsed += 1
                            yield data
                        else:
                            self._records_failed += 1
                            logger.warning(
                                "Failed to parse record",
                                record_num=self._records_fetched,
                            )

                    except Exception as e:
                        self._records_failed += 1
                        logger.error(
                            "Error parsing record",
                            record_num=self._records_fetched,
                            error=str(e),
                        )

                    # Update progress display
                    current_time = time.time()
                    if (current_time - last_update_time) >= update_interval:
                        elapsed = current_time - self._start_time
                        speed = self._records_fetched / elapsed if elapsed > 0 else 0

                        # ログに進捗を出力（quickstart.pyで検出用）
                        logger.info(
                            "Processing records",
                            records_fetched=self._records_fetched,
                            records_parsed=self._records_parsed,
                            files_processed=self._files_processed,
                            total_files=self._total_files,
                            speed=f"{speed:.0f}",
                        )

                        if self.progress_display and task_id is not None:
                            self.progress_display.update(
                                task_id,
                                advance=1,
                                status=f"{self._records_fetched:,} 件処理中",
                            )
                            self.progress_display.update_stats(
                                fetched=self._records_fetched,
                                parsed=self._records_parsed,
                                failed=self._records_failed,
                                speed=speed,
                            )
                        last_update_time = current_time

                else:
                    # Error (< -1)
                    logger.error(
                        "JVRead error",
                        ret_code=ret_code,
                    )
                    raise FetcherError(f"JVRead returned error code: {ret_code}")

            except FetcherError:
                raise
            except Exception as e:
                logger.error("Error during fetch", error=str(e))
                raise FetcherError(f"Failed to fetch data: {e}")

    def get_statistics(self) -> dict:
        """Get fetching statistics.

        Returns:
            Dictionary with fetch statistics
        """
        return {
            "records_fetched": self._records_fetched,
            "records_parsed": self._records_parsed,
            "records_failed": self._records_failed,
        }

    def reset_statistics(self):
        """Reset fetching statistics."""
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0

    def _is_within_date_range(self, data: dict, to_date: str) -> bool:
        """Check if a record's date is within the specified range (up to to_date).

        Args:
            data: Parsed record data dictionary
            to_date: End date in YYYYMMDD format

        Returns:
            True if record date <= to_date, False otherwise
        """
        # Extract date from record
        # Most JV-Data records have Year and MonthDay fields
        year = data.get("Year")
        month_day = data.get("MonthDay")

        if not year or not month_day:
            # If date fields are not present, include the record
            # (don't filter records that don't have date information)
            return True

        try:
            # Construct record date as YYYYMMDD
            record_date = f"{year}{month_day}"

            # Compare as strings (YYYYMMDD format allows string comparison)
            return record_date <= to_date
        except Exception as e:
            logger.warning(
                "Failed to extract date from record",
                year=year,
                month_day=month_day,
                error=str(e),
            )
            # If we can't determine the date, include the record
            return True

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<{self.__class__.__name__} "
            f"fetched={self._records_fetched} "
            f"parsed={self._records_parsed} "
            f"failed={self._records_failed}>"
        )
