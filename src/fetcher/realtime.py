"""Realtime data fetcher for JLTSQL.

This module provides realtime data fetching from JV-Link.
"""

from typing import Iterator, Optional, List

from src.fetcher.base import BaseFetcher, FetcherError
from src.jvlink.constants import (
    JV_RT_SUCCESS,
    JVRTOPEN_SPEED_REPORT_SPECS,
    JVRTOPEN_TIME_SERIES_SPECS,
    is_valid_jvrtopen_spec,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Realtime data specification codes (速報系 + 時系列)
# Import from constants.py for consistency
RT_DATA_SPECS = {**JVRTOPEN_SPEED_REPORT_SPECS, **JVRTOPEN_TIME_SERIES_SPECS}


class RealtimeFetcher(BaseFetcher):
    """Realtime data fetcher.

    Fetches realtime data from JV-Link using JVRTOpen.
    This fetcher continuously monitors for new data updates.

    Examples:
        >>> from src.fetcher.realtime import RealtimeFetcher
        >>> fetcher = RealtimeFetcher(sid="JLTSQL")
        >>>
        >>> # Fetch race results (0B12)
        >>> for record in fetcher.fetch(data_spec="0B12"):
        ...     print(record['レコード種別ID'])
        ...     # Process record
        ...     if some_condition:
        ...         break  # Stop fetching
    """

    def __init__(self, sid: str = "JLTSQL"):
        """Initialize realtime fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "JLTSQL")
        """
        super().__init__(sid)
        self._stream_open = False

    def fetch(
        self,
        data_spec: str = "0B12",
        key: Optional[str] = None,
        continuous: bool = False,
    ) -> Iterator[dict]:
        """Fetch realtime data.

        Opens a realtime data stream and yields parsed records as they
        become available. The stream remains open for continuous updates
        if continuous=True.

        Args:
            data_spec: Realtime data specification code (default: "0B12")
                      See RT_DATA_SPECS for available codes.
            key: Search key for filtering data. Format depends on data type:
                 - Date format: YYYYMMDD (e.g., "20251130")
                 - Race format: YYYYMMDDJJRR (e.g., "202511300105")
                 If None, uses today's date.
            continuous: If True, keeps stream open for continuous updates.
                       If False, fetches current data then closes.

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If fetching fails

        Examples:
            >>> # Fetch race results once
            >>> for record in fetcher.fetch("0B12"):
            ...     print(record)

            >>> # Continuous monitoring
            >>> for record in fetcher.fetch("0B12", continuous=True):
            ...     print(record)  # Will keep running until stopped
        """
        if data_spec not in RT_DATA_SPECS:
            logger.warning(
                f"Unknown data spec: {data_spec}. "
                "Proceeding anyway, but this may not be valid."
            )

        # Default key to today's date if not specified
        # JVRTOpen requires a date key (YYYYMMDD) to function properly
        if key is None:
            from datetime import datetime
            key = datetime.now().strftime("%Y%m%d")
            logger.debug("Using today's date as key", key=key)

        try:
            # Initialize JV-Link
            logger.info("Initializing JV-Link", has_service_key=self._service_key is not None)
            ret = self.jvlink.jv_init()
            if ret != JV_RT_SUCCESS:
                raise FetcherError(f"JV-Link initialization failed: {ret}")

            logger.info(
                "Starting realtime data fetch",
                data_spec=data_spec,
                key=key,
                spec_name=RT_DATA_SPECS.get(data_spec, "Unknown"),
                continuous=continuous,
            )

            # Open realtime stream
            ret, read_count = self.jvlink.jv_rt_open(data_spec, key)

            if ret != JV_RT_SUCCESS:
                raise FetcherError(f"JVRTOpen failed: {ret}")

            self._stream_open = True
            logger.info(
                "Realtime stream opened",
                read_count=read_count,
                data_spec=data_spec,
            )

            # Fetch and parse records
            if continuous:
                # Continuous mode: keep fetching indefinitely
                logger.info("Continuous mode enabled - stream will remain open")
                yield from self._fetch_continuous()
            else:
                # Single batch mode: fetch current data then close
                logger.info("Fetching current realtime data (single batch)")
                yield from self._fetch_and_parse()

        except FetcherError:
            raise
        except Exception as e:
            # -114: 契約外エラーはdebugレベル
            if '-114' in str(e):
                logger.debug("Realtime fetch skipped (not subscribed)", error=str(e))
            else:
                logger.error("Realtime fetch error", error=str(e))
            raise FetcherError(f"Realtime fetch failed: {e}")
        finally:
            self._close_stream()

    def _fetch_continuous(self) -> Iterator[dict]:
        """Fetch data continuously.

        This mode keeps the stream open and continuously checks for
        new data. Suitable for long-running monitoring services.

        Yields:
            Dictionary of parsed record data
        """
        import time

        while self._stream_open:
            try:
                # Fetch available records
                record_count = 0
                for record in self._fetch_and_parse():
                    record_count += 1
                    yield record

                # If no records found, wait before checking again
                if record_count == 0:
                    logger.debug("No new data available, waiting...")
                    time.sleep(1)  # Poll every second
                else:
                    logger.debug(f"Processed {record_count} records")

            except StopIteration:
                # End of current batch
                logger.debug("Batch complete, waiting for new data...")
                time.sleep(1)
                continue
            except Exception as e:
                logger.error("Error in continuous fetch", error=str(e))
                # Continue monitoring despite errors
                time.sleep(5)  # Wait longer after error

    def _close_stream(self):
        """Close the realtime stream."""
        if self._stream_open:
            try:
                self.jvlink.jv_close()
                self._stream_open = False
                logger.info("Realtime stream closed")
            except Exception as e:
                logger.error("Error closing stream", error=str(e))

    def stop(self):
        """Stop continuous fetching.

        Call this method to gracefully stop a continuous fetch operation.
        """
        logger.info("Stopping realtime fetcher...")
        self._stream_open = False

    @staticmethod
    def list_data_specs() -> dict:
        """Get available realtime data specification codes.

        Returns:
            Dictionary mapping data spec codes to descriptions
        """
        return RT_DATA_SPECS.copy()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._close_stream()
        return False
