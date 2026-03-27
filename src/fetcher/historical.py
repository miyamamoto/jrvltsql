"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

import time
from datetime import datetime
from typing import Iterator, Optional

from src.fetcher.base import BaseFetcher, FetcherError
from src.utils.logger import get_logger
from src.utils.progress import JVLinkProgressDisplay

logger = get_logger(__name__)


class HistoricalFetcher(BaseFetcher):
    """Fetcher for historical JV-Data.

    Fetches accumulated (蓄積) data from JV-Link for a specified date range
    and data specification. The JV-Link API retrieves all data from the
    start date onwards, then filters records client-side based on the end date.

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
        option: int = 1,
    ) -> Iterator[dict]:
        """Fetch historical data.

        Args:
            data_spec: Data specification code (e.g., "RACE", "DIFF")
            from_date: Start date in YYYYMMDD format
            to_date: End date in YYYYMMDD format (filters records up to this date)
            option: JVOpen option:
                    1=通常データ（差分データ取得、蓄積系メンテナンス用）
                    2=今週データ（直近のレースのみ、非蓄積系用）
                    3=セットアップ（全データ取得、ダイアログ表示あり）
                    4=分割セットアップ（全データ取得、初回のみダイアログ）

        Yields:
            Dictionary of parsed record data with dates <= to_date

        Raises:
            FetcherError: If fetching fails

        Note:
            Records are filtered client-side to include only those with
            dates up to and including to_date. Records without date fields
            (Year/MonthDay) are always included.

        Examples:
            >>> fetcher = HistoricalFetcher()  # Uses default sid="UNKNOWN"
            >>> # 通常データ取得（差分データ）
            >>> for record in fetcher.fetch("RACE", "20240601", "20240630", option=1):
            ...     # Process record (only records with dates <= 20240630)
            ...     pass
            >>> # セットアップ（全データ取得）
            >>> for record in fetcher.fetch("RACE", "20000101", "20240630", option=3):
            ...     # Process all records up to 20240630
            ...     pass
        """
        # Create progress display if enabled
        if self.show_progress:
            self.progress_display = JVLinkProgressDisplay()
            self.progress_display.start()

        download_task_id = None
        fetch_task_id = None

        try:
            # Info for setup mode (option 3 or 4) - ログのみ、画面表示はしない
            if option in (3, 4):
                logger.info(
                    "セットアップモード - 全データを取得します",
                    option=option,
                )

            # Initialize JV-Link
            logger.info("Initializing JV-Link", has_service_key=self._service_key is not None)
            if self.progress_display:
                # スペックヘッダーを表示（日付範囲付き）
                self.progress_display.print_spec_header(data_spec, from_date, to_date)

            # Note: Service key must be pre-configured in Windows registry
            # jv_init() does not accept service_key parameter
            self.jvlink.jv_init()

            # Convert dates to fromtime format
            # fromtime format: "YYYYMMDDhhmmss" (single timestamp)
            # JV-Link retrieves data from this timestamp onwards
            # Option meanings: 1=通常データ, 2=今週データ, 3/4=セットアップ
            fromtime = f"{from_date}000000"

            # Open data stream
            logger.info(
                "Opening data stream",
                data_spec=data_spec,
                from_date=from_date,
                to_date=to_date,
                fromtime=fromtime,
                option=option,
                note=(
                    "option=1: 通常データ（差分）; "
                    "option=2: 今週データ; "
                    "option=3/4: セットアップ（全データ）"
                ),
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

            # Check if data is empty
            if result == -1 or (read_count == 0 and download_count == 0):
                logger.info(
                    "No data available from specified timestamp",
                    data_spec=data_spec,
                    fromtime=fromtime,
                )
                if self.progress_display:
                    self.progress_display.print_info(
                        f"{data_spec}: サーバーにデータなし"
                    )
                return  # No data to fetch

            # Wait for download to complete if needed
            if download_count > 0:
                logger.info(
                    "Download in progress, waiting for completion",
                    download_count=download_count,
                )
                if self.progress_display:
                    download_task_id = self.progress_display.add_download_task(
                        f"{data_spec} ダウンロード",
                        total=100,
                    )
                self._wait_for_download(download_task_id)

            # Reset statistics and set total files
            self.reset_statistics()
            self._total_files = read_count

            # Create fetch progress task
            if self.progress_display:
                fetch_task_id = self.progress_display.add_task(
                    f"{data_spec} レコード取得",
                    total=read_count,
                )

            # Fetch and parse records
            for data in self._fetch_and_parse(fetch_task_id, to_date=to_date):
                yield data

            # Log summary
            stats = self.get_statistics()
            logger.info(
                "Fetch completed",
                **stats,
            )

            if self.progress_display:
                self.progress_display.print_success(
                    f"完了: {data_spec} - "
                    f"{stats['records_parsed']:,}件取得 "
                    f"(失敗: {stats['records_failed']}件)"
                )

        except Exception as e:
            logger.error("Failed to fetch historical data", error=str(e))
            if self.progress_display:
                self.progress_display.print_error(f"エラー: {str(e)}")
            raise FetcherError(f"Historical fetch failed: {e}")

        finally:
            # Close stream
            try:
                self.jvlink.jv_close()
                logger.info("Data stream closed")
            except Exception as e:
                logger.warning(f"Failed to close stream: {e}")

            # Explicitly cleanup COM resources
            if hasattr(self.jvlink, 'cleanup'):
                try:
                    self.jvlink.cleanup()
                except Exception:
                    pass

            # Stop progress display
            if self.progress_display:
                self.progress_display.stop()

    def fetch_with_date_range(
        self,
        data_spec: str,
        start_date: datetime,
        end_date: datetime,
        option: int = 1,
    ) -> Iterator[dict]:
        """Fetch historical data using datetime objects.

        Args:
            data_spec: Data specification code
            start_date: Start date as datetime
            end_date: End date as datetime (filters records up to this date)
            option: JVOpen option:
                    1=通常データ（差分データ取得、蓄積系メンテナンス用）
                    2=今週データ（直近のレースのみ、非蓄積系用）
                    3=セットアップ（全データ取得、ダイアログ表示あり）
                    4=分割セットアップ（全データ取得、初回のみダイアログ）

        Yields:
            Dictionary of parsed record data with dates <= end_date

        Note:
            Records are filtered client-side to include only those with
            dates up to and including end_date.

        Examples:
            >>> from datetime import datetime
            >>> fetcher = HistoricalFetcher()
            >>> start = datetime(2024, 6, 1)
            >>> end = datetime(2024, 6, 30)
            >>> # 通常データ取得（差分データ）
            >>> for record in fetcher.fetch_with_date_range("RACE", start, end, option=1):
            ...     pass
            >>> # セットアップ（全データ取得）
            >>> for record in fetcher.fetch_with_date_range("RACE", start, end, option=3):
            ...     pass
        """
        from_date = start_date.strftime("%Y%m%d")
        to_date = end_date.strftime("%Y%m%d")

        yield from self.fetch(data_spec, from_date, to_date, option)

    def _wait_for_download(
        self, download_task_id: Optional[int] = None, timeout: int = 600, interval: float = 0.08
    ):
        """Wait for JV-Link download to complete.

        Args:
            download_task_id: Progress task ID for download (optional)
            timeout: Maximum wait time in seconds (default: 600 = 10 minutes).
            interval: Status check interval in seconds (default: 0.08).
                     kmy-keiba uses 80ms (Task.Delay(80)) for download polling.

        Raises:
            FetcherError: If download fails or times out
        """
        start_time = time.time()
        last_status = None
        retry_count = 0
        max_retries = 2  # Maximum retries for temporary errors
        last_progress_time = start_time  # Track when progress last changed (stall detection)
        stall_timeout = 300.0  # 5 minutes before stall abort
        # Count how many consecutive 0-status polls we get BEFORE download_started.
        # If download finishes before our first poll, status is immediately 0 and
        # download_started never becomes True → we'd loop forever.  After
        # IMMEDIATE_ZERO_THRESHOLD consecutive 0s we treat it as "already done".
        zero_before_start_count = 0
        IMMEDIATE_ZERO_THRESHOLD = 5  # ~0.4 seconds at 80ms interval

        # Retryable error codes (temporary errors that may resolve)
        # -201: Database error (might be busy)
        # -202: File error (might be busy)
        # -203: Other error (may indicate incomplete JVDTLab setup or cache issue)
        # -502: Download failed
        # -503: Similar download error
        retryable_errors = {-201, -202, -203, -502, -503}
        download_started = False  # JVStatus > 0 を確認してから 0 を「完了」と判定

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
                    last_progress_time = time.time()  # Reset stall timer on any change
                    if status > 0:
                        download_started = True
                        percentage = status / 100
                        logger.info(
                            "Download in progress",
                            progress_percent=percentage,
                            elapsed_seconds=int(elapsed),
                        )
                        # Update progress display
                        if self.progress_display and download_task_id is not None:
                            self.progress_display.update_download(
                                download_task_id,
                                completed=status,
                                status=f"{percentage:.1f}% - {int(elapsed)}秒経過",
                            )
                        # Reset retry count on progress
                        retry_count = 0
                    elif status == 0 and not download_started:
                        zero_before_start_count += 1
                        if zero_before_start_count >= IMMEDIATE_ZERO_THRESHOLD:
                            # Download already completed before we started polling.
                            logger.info(
                                "Download appears already complete (status 0 before download_started)",
                                elapsed=f"{elapsed:.1f}s",
                            )
                            if self.progress_display and download_task_id is not None:
                                self.progress_display.update_download(
                                    download_task_id,
                                    completed=100,
                                    status="完了",
                                )
                            return
                        logger.debug("Waiting for download to start", elapsed=f"{elapsed:.1f}s")
                    last_status = status
                else:
                    # Stall detection: kmy-keiba restarts if download progress
                    # doesn't change for 60 seconds
                    if download_started and status > 0:
                        stall_elapsed = time.time() - last_progress_time
                        if stall_elapsed >= stall_timeout:
                            logger.warning(
                                "Download stalled (no progress for 60s), treating as timeout",
                                last_status=status,
                                stall_seconds=stall_elapsed,
                            )
                            raise FetcherError(
                                f"Download stalled at {status}% for {stall_elapsed:.0f}s"
                            )

                if status == 0 and download_started:
                    logger.info("Download completed", elapsed_seconds=int(elapsed))
                    if self.progress_display and download_task_id is not None:
                        self.progress_display.update_download(
                            download_task_id,
                            completed=100,
                            status="完了",
                        )
                    # Wait for file system write completion
                    wait_time = 0.5
                    logger.info("Waiting for file write completion...", wait_seconds=wait_time)
                    time.sleep(wait_time)
                    logger.info("File write wait completed")
                    return  # Download complete

                if status < 0:
                    if status in retryable_errors:
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.warning(
                                "Retryable download error, will retry",
                                status_code=status,
                                retry_count=retry_count,
                                max_retries=max_retries,
                            )
                            time.sleep(interval * 2)  # Wait longer before retry
                            continue
                        else:
                            raise FetcherError(
                                f"Download failed after {max_retries} retries with status code: {status}"
                            )
                    else:
                        raise FetcherError(f"Download failed with status code: {status}")

                # Wait before next status check
                time.sleep(interval)

            except Exception as e:
                if isinstance(e, FetcherError):
                    raise

                raise FetcherError(f"Failed to check download status: {e}")
