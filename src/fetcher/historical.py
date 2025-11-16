"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

import time
from datetime import datetime
from typing import Iterator, Optional

from src.fetcher.base import BaseFetcher, FetcherError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HistoricalFetcher(BaseFetcher):
    """Fetcher for historical JV-Data.

    Fetches accumulated (蓄積) data from JV-Link for a specified date range
    and data specification.

    Note:
        Service key must be configured in JRA-VAN DataLab application
        before using this class.

    Examples:
        >>> fetcher = HistoricalFetcher()  # Uses default sid="UNKNOWN"
        >>> for record in fetcher.fetch(
        ...     data_spec="RACE",
        ...     from_date="20240101",
        ...     to_date="20241231"
        ... ):
        ...     print(record['headRecordSpec'])
    """

    def fetch(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int = 0,
    ) -> Iterator[dict]:
        """Fetch historical data.

        Args:
            data_spec: Data specification code (e.g., "RACE", "DIFF")
            from_date: Start date in YYYYMMDD format
            to_date: End date in YYYYMMDD format
            option: JVOpen option (0=normal, 1=setup, 2=update)

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If fetching fails

        Examples:
            >>> fetcher = HistoricalFetcher()  # Uses default sid="UNKNOWN"
            >>> for record in fetcher.fetch("RACE", "20240601", "20240630"):
            ...     # Process record
            ...     pass
        """
        try:
            # Initialize JV-Link
            logger.info("Initializing JV-Link", has_service_key=self._service_key is not None)
            self.jvlink.jv_init(service_key=self._service_key)

            # Convert dates to fromtime format
            # fromtime format: "YYYYMMDDhhmmss" (single timestamp)
            # JV-Link retrieves data from this timestamp onwards
            fromtime = f"{from_date}000000"

            # Open data stream
            logger.info(
                "Opening data stream",
                data_spec=data_spec,
                from_date=from_date,
                fromtime=fromtime,
                option=option,
                note="Retrieves data from fromtime onwards (not a range)",
            )

            result, read_count, download_count, last_file_timestamp = self.jvlink.jv_open(
                data_spec,
                fromtime,
                option,
            )

            logger.info(
                "Data stream opened",
                result_code=result,
                read_count=read_count,
                download_count=download_count,
                last_file_timestamp=last_file_timestamp,
            )

            # Check if data is empty (result=-1 or read_count=0)
            if result == -1 or read_count == 0:
                logger.info(
                    "No data available from specified timestamp",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    note="No new data since this timestamp",
                )
                return  # No data to fetch

            # Wait for download to complete if needed (download_count > 0)
            if download_count > 0:
                logger.info(
                    "Download in progress, waiting for completion",
                    download_count=download_count,
                )
                self._wait_for_download()

            # Reset statistics
            self.reset_statistics()

            # Fetch and parse records
            for data in self._fetch_and_parse():
                yield data

            # Log summary
            stats = self.get_statistics()
            logger.info(
                "Fetch completed",
                **stats,
            )

        except Exception as e:
            logger.error("Failed to fetch historical data", error=str(e))
            raise FetcherError(f"Historical fetch failed: {e}")

        finally:
            # Close stream
            try:
                if self.jvlink.is_open():
                    self.jvlink.jv_close()
                    logger.info("Data stream closed")
            except Exception as e:
                logger.warning(f"Failed to close stream: {e}")

    def fetch_with_date_range(
        self,
        data_spec: str,
        start_date: datetime,
        end_date: datetime,
        option: int = 0,
    ) -> Iterator[dict]:
        """Fetch historical data using datetime objects.

        Args:
            data_spec: Data specification code
            start_date: Start date as datetime
            end_date: End date as datetime
            option: JVOpen option

        Yields:
            Dictionary of parsed record data

        Examples:
            >>> from datetime import datetime
            >>> fetcher = HistoricalFetcher()
            >>> start = datetime(2024, 6, 1)
            >>> end = datetime(2024, 6, 30)
            >>> for record in fetcher.fetch_with_date_range("RACE", start, end):
            ...     pass
        """
        from_date = start_date.strftime("%Y%m%d")
        to_date = end_date.strftime("%Y%m%d")

        yield from self.fetch(data_spec, from_date, to_date, option)

    def _wait_for_download(self, timeout: int = 600, interval: float = 1.0):
        """Wait for JV-Link download to complete.

        Args:
            timeout: Maximum wait time in seconds (default: 600 = 10 minutes)
            interval: Status check interval in seconds (default: 1.0)

        Raises:
            FetcherError: If download fails or times out
        """
        start_time = time.time()
        last_status = None

        while True:
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise FetcherError(f"Download timeout after {elapsed:.1f} seconds")

            try:
                # Get download status
                # JVStatus returns:
                # > 0: Download in progress (percentage * 100)
                # 0: Download complete
                # < 0: Error
                status = self.jvlink.jv_status()

                if status != last_status:
                    if status > 0:
                        logger.info(
                            "Download in progress",
                            progress_percent=status / 100,
                            elapsed_seconds=int(elapsed),
                        )
                    last_status = status

                if status == 0:
                    logger.info("Download completed", elapsed_seconds=int(elapsed))
                    return  # Download complete

                if status < 0:
                    raise FetcherError(f"Download failed with status code: {status}")

                # Wait before next status check
                time.sleep(interval)

            except Exception as e:
                if isinstance(e, FetcherError):
                    raise
                raise FetcherError(f"Failed to check download status: {e}")
