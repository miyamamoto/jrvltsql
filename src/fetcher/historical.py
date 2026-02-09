"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

import time
from datetime import datetime, timedelta
from typing import Iterator, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.fetcher.base import BaseFetcher, FetcherError
from src.nvlink.wrapper import COMBrokenError as _WrapperCOMBrokenError
from src.nvlink.bridge import COMBrokenError as _BridgeCOMBrokenError
from src.utils.data_source import DataSource
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
        # NAR (NV-Link): split date range into daily chunks to avoid -502 errors.
        # NV-Link server rejects large downloads; 1-day chunks keep file counts small.
        if self._should_chunk_by_day(from_date, to_date, option):
            yield from self._fetch_nar_daily(data_spec, from_date, to_date, option)
            return

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
            # kmy-keiba handles this by restarting the entire program (up to 16 times).
            # We reduce to 3 retries because COM reinit often causes Win32 exceptions
            # and crashes anyway. Better to skip the day quickly and move on.
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
                    try:
                        self._wait_for_download(download_task_id)
                        break  # Download succeeded
                    except FetcherError as dl_err:
                        # -502/-503: Don't retry with COM reinit — it rarely helps and
                        # causes Win32 crashes. Let _fetch_nar_daily skip the day instead.
                        raise
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

        except (_WrapperCOMBrokenError, _BridgeCOMBrokenError):
            # Let COMBrokenError propagate to _fetch_nar_daily for retry
            logger.warning("COM broken error during fetch, propagating for retry")
            raise
        except Exception as e:
            logger.error("Failed to fetch historical data", error=str(e))
            if self.progress_display:
                self.progress_display.print_error(f"エラー: {str(e)}")
            raise FetcherError(f"Historical fetch failed: {e}")

        finally:
            # Close stream
            try:
                # Always try to close, even if _is_open is False
                # This prevents -202 (AlreadyOpen) on next NVOpen call
                self.jvlink.jv_close()
                logger.info("Data stream closed")
            except Exception as e:
                logger.warning(f"Failed to close stream: {e}")

            # Explicitly cleanup COM resources (prevents "Win32 exception releasing IUnknown")
            # Skip cleanup when called from _fetch_nar_daily loop (cleanup on final day only)
            if not getattr(self, '_skip_cleanup', False) and hasattr(self.jvlink, 'cleanup'):
                try:
                    self.jvlink.cleanup()
                except Exception:
                    pass

            # Stop progress display
            if self.progress_display:
                self.progress_display.stop()

    def _should_chunk_by_day(self, from_date: str, to_date: str, option: int) -> bool:
        """Check if NAR date range should be split into daily chunks.

        Returns True if data_source is NAR, the range spans more than 1 day,
        and we are NOT in setup mode (option 3/4).
        """
        # Setup mode (option=3/4) downloads all data; daily chunking is unnecessary
        if option in (3, 4):
            return False
        if self.data_source != DataSource.NAR:
            return False
        return from_date != to_date

    def _fetch_nar_daily(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int,
    ) -> Iterator[dict]:
        """Fetch NAR data by iterating one day at a time.

        NV-Link server cannot handle large downloads (e.g., 289 files for a week).
        Splitting into daily chunks (typically ~3 files/day) avoids -502 errors.

        When a day fails with -502, the day is skipped and recorded.
        If -502 occurs on 3 consecutive days, all remaining days are skipped
        (the server likely doesn't have the data cached).

        Args:
            data_spec: Data specification code
            from_date: Start date (YYYYMMDD)
            to_date: End date (YYYYMMDD)
            option: NVOpen option
        """
        start = datetime.strptime(from_date, "%Y%m%d")
        end = datetime.strptime(to_date, "%Y%m%d")

        total_days = (end - start).days + 1
        logger.info(
            "NAR daily chunking: splitting date range",
            from_date=from_date,
            to_date=to_date,
            total_days=total_days,
            data_spec=data_spec,
        )

        current = start
        day_num = 0
        skipped_dates: list[str] = []
        consecutive_502_count = 0
        max_consecutive_502 = 5  # 5日連続-502で残りをスキップ（ウェイト有り）

        try:
            self._skip_cleanup = True
            while current <= end:
                day_num += 1
                day_str = current.strftime("%Y%m%d")
                is_last_day = (current + timedelta(days=1)) > end
                if is_last_day:
                    self._skip_cleanup = False  # Allow cleanup on final day

                # 連続-502チェック: 3日連続なら残り全スキップ
                if consecutive_502_count >= max_consecutive_502:
                    remaining_days = []
                    while current <= end:
                        remaining_days.append(current.strftime("%Y%m%d"))
                        current += timedelta(days=1)
                    skipped_dates.extend(remaining_days)
                    logger.warning(
                        f"-502エラーが{max_consecutive_502}日連続で発生したため、残り{len(remaining_days)}日をスキップします",
                        data_spec=data_spec,
                        skipped_dates=remaining_days,
                    )
                    break

                logger.info(
                    "Processing NAR daily chunk",
                    day_num=day_num,
                    total_days=total_days,
                    date=day_str,
                    data_spec=data_spec,
                )

                try:
                    # fetch() will see same from/to date → _should_chunk_by_day returns False
                    yield from self.fetch(data_spec, day_str, day_str, option)
                    consecutive_502_count = 0  # Reset on success
                except (_WrapperCOMBrokenError, _BridgeCOMBrokenError) as e:
                    # COM E_UNEXPECTED: NVClose→reinit→retry once for this day
                    logger.warning(
                        "COM E_UNEXPECTED during fetch, attempting recovery",
                        date=day_str,
                        data_spec=data_spec,
                        error=str(e),
                    )
                    if self.progress_display:
                        self.progress_display.print_warning(
                            f"⚠️  COM broken on {day_str}, recovering..."
                        )

                    # Recovery: close → reinitialize COM → retry
                    try:
                        self.jvlink.jv_close()
                    except Exception:
                        pass

                    if hasattr(self.jvlink, 'reinitialize_com'):
                        try:
                            self.jvlink.reinitialize_com()
                            self.jvlink.jv_init()
                            logger.info("COM recovery successful, retrying day", date=day_str)
                        except Exception as reinit_err:
                            logger.error("COM reinit failed, skipping day", date=day_str, error=str(reinit_err))
                            skipped_dates.append(day_str)
                            current += timedelta(days=1)
                            continue

                    # Retry the day once after recovery
                    try:
                        yield from self.fetch(data_spec, day_str, day_str, option)
                        consecutive_502_count = 0
                        logger.info("Retry after COM recovery succeeded", date=day_str)
                    except (_WrapperCOMBrokenError, _BridgeCOMBrokenError, FetcherError) as retry_err:
                        logger.warning(
                            "Retry after COM recovery also failed, skipping day",
                            date=day_str,
                            error=str(retry_err),
                        )
                        skipped_dates.append(day_str)
                        if self.progress_display:
                            self.progress_display.print_warning(
                                f"⚠️  {day_str} skipped after COM recovery failure"
                            )

                except FetcherError as e:
                    error_str = str(e)
                    # NAR server errors that should be retried/skipped:
                    # -502/-503: Download failures
                    # -421: Invalid server response (temporary server issue)
                    # -431: Invalid server application response
                    # "timeout": Download timeout
                    is_server_error = any(code in error_str for code in ["-502", "-503", "-421", "-431"])
                    is_timeout = "timeout" in error_str.lower()
                    if is_server_error or is_timeout:
                        error_type = "timeout" if is_timeout else "server error"
                        # option=1でサーバーエラーが発生した場合、option=2（差分モード）でフォールバック
                        fallback_succeeded = False
                        if option == 1 and is_server_error:
                            logger.info(
                                f"{error_type}発生、option=2（差分モード）で再試行します",
                                data_spec=data_spec,
                                date=day_str,
                            )
                            if self.progress_display:
                                self.progress_display.print_warning(
                                    f"{error_type}: {day_str} option=2で再試行中..."
                                )
                            try:
                                yield from self.fetch(data_spec, day_str, day_str, 2)
                                consecutive_502_count = 0  # Reset on success
                                fallback_succeeded = True
                            except FetcherError as e2:
                                error_str2 = str(e2)
                                is_server_error2 = any(code in error_str2 for code in ["-502", "-503", "-421", "-431"])
                                is_timeout2 = "timeout" in error_str2.lower()
                                if not is_server_error2 and not is_timeout2:
                                    raise  # サーバーエラー/タイムアウト以外は再送出
                                logger.warning(
                                    f"option=2でも{error_type}、{day_str}をスキップします",
                                    data_spec=data_spec,
                                    date=day_str,
                                )

                        if not fallback_succeeded:
                            consecutive_502_count += 1
                            skipped_dates.append(day_str)
                            # エラー後は長めにバックオフ（サーバー回復待ち）
                            backoff = min(5.0 * consecutive_502_count, 30.0)
                            logger.warning(
                                f"{error_type}で{day_str}をスキップします "
                                f"(連続{consecutive_502_count}日目, {backoff}秒待機)",
                                data_spec=data_spec,
                                date=day_str,
                            )
                            if self.progress_display:
                                self.progress_display.print_warning(
                                    f"{error_type}: {day_str}をスキップ (連続{consecutive_502_count}日目)"
                                )
                            time.sleep(backoff)
                    else:
                        raise  # サーバーエラー/タイムアウト以外は再送出

                current += timedelta(days=1)

                # NARサーバーへの負荷軽減: 日次チャンク間にウェイトを入れる
                # 連続リクエストはサーバー側でレートリミット(-502)の原因になる
                # kmy-keiba doesn't chunk by day, but since we do, we need a small gap.
                # Reduced from 2s: the GC + NVClose already adds ~0.5s.
                if current <= end:
                    delay = 1.0
                    logger.debug("NAR daily chunk delay", delay_seconds=delay)
                    time.sleep(delay)
        finally:
            self._skip_cleanup = False

        # スキップした日付のサマリーを表示
        if skipped_dates:
            logger.warning(
                f"NAR -502エラーにより{len(skipped_dates)}日分のデータをスキップしました",
                data_spec=data_spec,
                skipped_dates=skipped_dates,
            )
            if self.progress_display:
                self.progress_display.print_warning(
                    f"⚠️  {data_spec}: {len(skipped_dates)}日分のデータをスキップしました"
                )
                for d in skipped_dates:
                    self.progress_display.print_warning(f"  スキップ: {d}")
                self.progress_display.print_warning(
                    "💡 UmaConn設定ツールでデータをダウンロードしてから再実行してください"
                )
            # Store skipped dates for callers to inspect
            self._nar_skipped_dates = skipped_dates
        else:
            self._nar_skipped_dates = []

        logger.info(
            "NAR daily chunking completed",
            data_spec=data_spec,
            total_days=total_days,
            skipped_days=len(skipped_dates),
        )

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
        max_retries = 2  # Maximum retries for temporary errors (reduced from 5: -502 rarely resolves with retry)
        last_progress_time = start_time  # Track when progress last changed (stall detection)
        stall_timeout = 60.0  # kmy-keiba: 60s stall = restart program

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
                    # kmy-keiba has no explicit wait after download, reads immediately.
                    # Keep a minimal wait for safety.
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
