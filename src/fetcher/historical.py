"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

from datetime import datetime
from typing import Iterator, Optional

from src.fetcher.base import BaseFetcher, FetcherError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HistoricalFetcher(BaseFetcher):
    """Fetcher for historical JV-Data.

    Fetches accumulated (蓄積) data from JV-Link for a specified date range
    and data specification.

    Examples:
        >>> fetcher = HistoricalFetcher(service_key="YOUR_KEY")
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
            >>> fetcher = HistoricalFetcher("YOUR_KEY")
            >>> for record in fetcher.fetch("RACE", "20240601", "20240630"):
            ...     # Process record
            ...     pass
        """
        try:
            # Initialize JV-Link
            logger.info("Initializing JV-Link")
            self.jvlink.jv_init()

            # Open data stream
            logger.info(
                "Opening data stream",
                data_spec=data_spec,
                from_date=from_date,
                to_date=to_date,
                option=option,
            )

            result, count = self.jvlink.jv_open(
                data_spec,
                from_date,
                to_date,
                option,
            )

            logger.info(
                f"Data stream opened",
                expected_count=count,
            )

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
            >>> fetcher = HistoricalFetcher("YOUR_KEY")
            >>> start = datetime(2024, 6, 1)
            >>> end = datetime(2024, 6, 30)
            >>> for record in fetcher.fetch_with_date_range("RACE", start, end):
            ...     pass
        """
        from_date = start_date.strftime("%Y%m%d")
        to_date = end_date.strftime("%Y%m%d")

        yield from self.fetch(data_spec, from_date, to_date, option)
