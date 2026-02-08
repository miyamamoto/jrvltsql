"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

import time
from datetime import datetime
from typing import Iterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

            # NAR (NV-Link) downloads can fail with -502 intermittently.
            # kmy-keiba handles this by restarting the entire program.
            # We implement retry at the Open+Download level instead.
            max_open_retries = 3
            for open_attempt in range(max_open_retries):
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
                    attempt=open_attempt + 1,
                )

                # Check if data is empty
                if result == -1 or (read_count == 0 and download_count == 0):
                    logger.info(
                        "No data available from specified timestamp",
                        data_spec=data_spec,
                        fromtime=fromtime,
                        note="No data on server for this spec/period",
                    )
                    if self.progress_display:
                        self.progress_display.print_info(
                            f"{data_spec}: サーバーにデータなし"
                        )
                    return  # No data to fetch

                # Wait for download to complete if needed (download_count > 0)
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
                    try:
                        self._wait_for_download(download_task_id)
                        break  # Download succeeded
                    except FetcherError as dl_err:
                        # Check if this is a -502 retry situation
                        if "-502" in str(dl_err) and open_attempt < max_open_retries - 1:
                            logger.warning(
                                "Download failed with -502, retrying with NVClose/NVOpen",
                                attempt=open_attempt + 1,
                                max_retries=max_open_retries,
                            )
                            if self.progress_display:
                                self.progress_display.print_warning(
                                    f"-502エラー: リトライ中 ({open_attempt + 2}/{max_open_retries})"
                                )
                            try:
                                self.jvlink.jv_close()
                            except Exception:
                                pass
                            import time as _time
                            _time.sleep(5)  # Wait before retry
                            continue
                        raise  # Re-raise if not retryable or max retries reached
                else:
                    break  # No download needed

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
                if self.jvlink.is_open():
                    self.jvlink.jv_close()
                    logger.info("Data stream closed")
            except Exception as e:
                logger.warning(f"Failed to close stream: {e}")

            # Explicitly cleanup COM resources (prevents "Win32 exception releasing IUnknown")
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
        self, download_task_id: Optional[int] = None, timeout: int = 1800, interval: float = 0.5
    ):
        """Wait for JV-Link download to complete.

        Args:
            download_task_id: Progress task ID for download (optional)
            timeout: Maximum wait time in seconds (default: 1800 = 30 minutes, increased for large data specs)
            interval: Status check interval in seconds (default: 0.5)

        Raises:
            FetcherError: If download fails or times out
        """
        start_time = time.time()
        last_status = None
        retry_count = 0
        max_retries = 10  # Maximum retries for temporary errors (NAR -502 is flaky)

        # Retryable error codes (temporary errors that may resolve)
        # -201: Database error (might be busy)
        # -202: File error (might be busy)
        # -203: Other error (NAR: often indicates incomplete NVDTLab setup or cache issue)
        #       For NV-Link (NAR), -203 typically means:
        #       1. Initial NVDTLab setup not completed
        #       2. Cache corruption
        #       3. option=1 (differential mode) not working properly
        #       Best practice: Use option=4 (setup mode) for NAR data
        # -502: Download failed (NAR/NV-Link known issue - kmy-keiba comment:
        #       "地方競馬では、きちんとネットにつながってるはずなのにこのようなエラーが出ることがある")
        # -503: Similar download error
        retryable_errors = {-201, -202, -203, -502, -503}
        download_started = False  # NVStatus > 0 を確認してから 0 を「完了」と判定

        while True:
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise FetcherError(f"Download timeout after {elapsed:.1f} seconds")

            try:
                # Get download status
                # JVStatus/NVStatus returns:
                # > 0: Download in progress (percentage * 100)
                # 0: Download complete
                # < 0: Error
                status = self.jvlink.jv_status()

                if status != last_status:
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
                        logger.debug("Waiting for download to start", elapsed=f"{elapsed:.1f}s")
                    last_status = status

                if status == 0 and download_started:
                    logger.info("Download completed", elapsed_seconds=int(elapsed))
                    if self.progress_display and download_task_id is not None:
                        self.progress_display.update_download(
                            download_task_id,
                            completed=100,
                            status="完了",
                        )
                    # Wait for file system write completion
                    # JV-Link reports download complete but files may not be written to disk yet
                    wait_time = 2  # 2秒に短縮（元は10秒）
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
                            # NAR (NV-Link) の -203 エラーは通常、キャッシュまたはセットアップの問題
                            if status == -203:
                                raise FetcherError(
                                    f"NV-Linkダウンロードエラー (code: {status}): "
                                    "地方競馬DATAのセットアップが完了していないか、キャッシュに問題があります。\n"
                                    "対処方法:\n"
                                    "1. NVDTLab設定ツールを起動し、「データダウンロード」タブで初回セットアップを実行\n"
                                    "2. セットアップ完了後も問題が続く場合は、キャッシュをクリアして再試行\n"
                                    "3. アプリケーション(UmaConn/地方競馬DATA)を再起動\n"
                                    "注: NAR データ取得には option=4 (セットアップモード) の使用が推奨されます"
                                )
                            else:
                                raise FetcherError(
                                    f"Download failed after {max_retries} retries with status code: {status}"
                                )
                    else:
                        # -502/-503: NAR download failures may resolve with NVClose/NVOpen retry
                        if status in (-502, -503):
                            raise FetcherError(
                                f"Download failed with status code: {status}",
                            )
                        # Fatal error (e.g., -100 series: setup/auth errors)
                        raise FetcherError(f"Download failed with status code: {status}")

                # Wait before next status check
                time.sleep(interval)

            except Exception as e:
                if isinstance(e, FetcherError):
                    raise

                # Check for COM catastrophic errors that require reinitialization
                # E_UNEXPECTED: -2147418113 (0x8000FFFF)
                error_code = getattr(e, 'error_code', None)
                error_str = str(e)

                # COM catastrophic errors or "catastrophic failure" in message
                if (error_code == -2147418113 or
                    'E_UNEXPECTED' in error_str or
                    'catastrophic' in error_str.lower() or
                    '0x8000FFFF' in error_str):

                    logger.warning("COM catastrophic error detected, attempting reinitialization", error=error_str)

                    # Attempt COM reinitialization if method exists
                    if hasattr(self.jvlink, 'reinitialize_com'):
                        try:
                            self.jvlink.reinitialize_com()
                            # After reinitialization, may need to restart download
                            logger.info("COM reinitialized successfully, you may need to retry the download")
                        except Exception as reinit_error:
                            logger.error("COM reinitialization failed", error=str(reinit_error))

                raise FetcherError(f"Failed to check download status: {e}")
