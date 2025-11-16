"""Base data fetcher for JLTSQL.

This module provides the base class for fetching JV-Data from JV-Link.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional

from src.jvlink.constants import JV_READ_NO_MORE_DATA, JV_READ_SUCCESS
from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.utils.logger import get_logger

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

    def __init__(self, sid: str = "UNKNOWN", service_key: Optional[str] = None):
        """Initialize base fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "UNKNOWN")
            service_key: Optional JV-Link service key. If provided, it will be set
                        programmatically without requiring registry configuration.
                        If not provided, the service key must be configured in
                        JRA-VAN DataLab application or registry.
        """
        self.jvlink = JVLinkWrapper(sid)
        self.parser_factory = ParserFactory()
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0
        self._service_key = service_key

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

    def _fetch_and_parse(self) -> Iterator[dict]:
        """Internal method to fetch and parse records.

        Yields:
            Dictionary of parsed record data
        """
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
                    break

                elif ret_code == JV_READ_NO_MORE_DATA:
                    # File switch (-1)
                    logger.debug("File switch")
                    continue

                elif ret_code > 0:
                    # Success with data (ret_code is data length)
                    self._records_fetched += 1

                    # Parse record
                    try:
                        data = self.parser_factory.parse(buff)
                        if data:
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

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<{self.__class__.__name__} "
            f"fetched={self._records_fetched} "
            f"parsed={self._records_parsed} "
            f"failed={self._records_failed}>"
        )
