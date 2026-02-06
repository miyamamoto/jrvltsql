"""Base data fetcher for JLTSQL.

This module provides the base class for fetching JV-Data from JV-Link.
"""

import time
from abc import ABC, abstractmethod
from typing import Iterator, Optional, Union

from src.jvlink.constants import JV_READ_NO_MORE_DATA, JV_READ_SUCCESS
from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.utils.data_source import DataSource
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
        initialization_key: Optional[str] = None,
        show_progress: bool = True,
        data_source: DataSource = DataSource.JRA,
    ):
        """Initialize base fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "UNKNOWN")
            service_key: Optional JV-Link service key. If provided, it will be set
                        programmatically without requiring registry configuration.
                        If not provided, the service key must be configured in
                        JRA-VAN DataLab application or registry.
            initialization_key: Optional NV-Link initialization key (software ID)
                        used for NVInit when data_source is NAR.
            show_progress: Show stylish progress display (default: True)
            data_source: Data source (DataSource.JRA or DataSource.NAR)
        """
        self.data_source = data_source

        # Select wrapper based on data source
        if data_source == DataSource.NAR:
            from src.nvlink.wrapper import NVLinkWrapper
            self.jvlink = NVLinkWrapper(sid, initialization_key=initialization_key)
        else:
            self.jvlink = JVLinkWrapper(sid)

        self.parser_factory = ParserFactory()
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0
        self._files_processed = 0
        self._total_files = 0
        self._service_key = service_key
        self._initialization_key = initialization_key
        self.show_progress = show_progress
        self.progress_display: Optional[JVLinkProgressDisplay] = None
        self._start_time = None

        logger.info(f"{self.__class__.__name__} initialized", sid=sid,
                   has_service_key=service_key is not None,
                   has_initialization_key=initialization_key is not None,
                   data_source=data_source.value)

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
        update_interval = 2.0  # 更新間隔を増やして高速化  # Update progress every 0.5 seconds (reduced to prevent flickering)

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
                        # Explicitly set to 100% complete
                        elapsed = time.time() - self._start_time
                        speed = self._records_fetched / elapsed if elapsed > 0 else 0
                        self.progress_display.update(
                            task_id,
                            completed=self._total_files if self._total_files > 0 else 100,
                            total=self._total_files if self._total_files > 0 else 100,
                            status="完了",
                        )
                        self.progress_display.update_stats(
                            fetched=self._records_fetched,
                            parsed=self._records_parsed,
                            failed=self._records_failed,
                            speed=speed,
                        )
                    break

                elif ret_code == JV_READ_NO_MORE_DATA:
                    # File switch (-1) - ファイル処理完了
                    self._files_processed += 1
                    # Update progress based on files processed (not records)
                    if self.progress_display and task_id is not None and self._total_files > 0:
                        self.progress_display.update(
                            task_id,
                            completed=self._files_processed,
                            status=f"ファイル {self._files_processed}/{self._total_files}",
                        )
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
                            # Include raw buffer for callers that need it (e.g., RealtimeUpdater)
                            data["_raw"] = buff
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

                    # Update progress display (stats only - progress updated on file switch)
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

                        if self.progress_display:
                            # Update stats display (progress bar updated on file switch)
                            self.progress_display.update_stats(
                                fetched=self._records_fetched,
                                parsed=self._records_parsed,
                                failed=self._records_failed,
                                speed=speed,
                            )
                        last_update_time = current_time

                elif ret_code in (-201, -202, -203, -402, -403, -502, -503):
                    # Recoverable errors - delete corrupted file and continue
                    # Based on kmy-keiba's JVLinkReader.cs error handling:
                    # -201: Database busy (リトライ可能)
                    # -202: File busy (リトライ可能)
                    # -203: Setup not complete or file corruption (セットアップ未完了またはファイル破損)
                    # -402, -403: Database errors (データベースエラー)
                    # -502, -503: File errors (ファイルエラー)

                    # Error-specific guidance
                    error_messages = {
                        -201: "データベースビジー状態です。一時的なエラーのため続行します。",
                        -202: "ファイルビジー状態です。一時的なエラーのため続行します。",
                        -203: "セットアップ未完了またはファイル破損が検出されました。ファイルを削除して続行します。",
                        -402: "データベースエラーが発生しました。破損ファイルを削除して続行します。",
                        -403: "データベースエラーが発生しました。破損ファイルを削除して続行します。",
                        -502: "ファイルエラーが発生しました。破損ファイルを削除して続行します。",
                        -503: "ファイルエラーが発生しました。破損ファイルを削除して続行します。",
                    }

                    error_msg = error_messages.get(ret_code, "リカバリー可能なエラーが発生しました。")
                    logger.warning(
                        f"Recoverable JVRead error: {error_msg}",
                        ret_code=ret_code,
                        filename=filename,
                        recommended_action="Deleting corrupted file and continuing",
                    )

                    # Delete corrupted file for file-related errors
                    if ret_code in (-203, -402, -403, -502, -503) and filename and hasattr(self.jvlink, 'jv_file_delete'):
                        try:
                            self.jvlink.jv_file_delete(filename)
                            logger.info(f"Deleted corrupted file: {filename}")
                        except Exception as e:
                            logger.warning(f"Failed to delete file {filename}: {e}")
                    continue

                else:
                    # Fatal error (< -1, other codes)
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
