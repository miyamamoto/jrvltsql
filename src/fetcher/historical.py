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


def _extract_record_date(record: dict) -> Optional[str]:
    """Extract YYYYMMDD from a parsed record dict."""
    year = record.get("Year") or record.get("headYear") or record.get("KaisaiNen")
    monthday = record.get("MonthDay") or record.get("headMonthDay") or record.get("KaisaiTsukihi")
    if year and monthday and len(str(year)) == 4 and len(str(monthday)) == 4:
        return str(year) + str(monthday)
    chokyo_date = record.get("ChokyoDate")
    if chokyo_date and len(str(chokyo_date)) == 8:
        return str(chokyo_date)
    return None


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

    JVD_SELF_REPAIR_MAX_RETRIES = 2

    def __init__(self, sid: str = "UNKNOWN", service_key: Optional[str] = None, show_progress: bool = True):
        super().__init__(sid, service_key=service_key, show_progress=show_progress)
        self.cache_manager = None
        self._jvd_self_repair_attempts = 0
        self._jvd_replay_records_remaining = 0
        self._jv_open_context: Optional[tuple[str, str, int]] = None
        self._jv_open_last_file_timestamp: Optional[str] = None
        self._fetch_task_id: Optional[int] = None

    def _consume_replayed_record(self) -> bool:
        """Skip records already emitted before a close/reopen recovery.

        Reopening with the identical JVOpen context replays the stream from its
        beginning. Historical cache output is append-only, so emitting that
        prefix again would duplicate raw records as well as caller-visible
        records.
        """
        if self._jvd_replay_records_remaining <= 0:
            return False
        self._jvd_replay_records_remaining -= 1
        return True

    def _recover_historical_read_error(self, error_code: int, filename: str) -> None:
        """Delete the exact corrupt file and reopen the historical stream."""
        if error_code != -402:
            self._delete_corrupt_file_best_effort(error_code, filename)
            raise FetcherError(
                f"JVRead returned {error_code} for {filename or 'an unknown file'}; "
                "automatic replay is limited to zero-byte files (-402)"
            )
        if not filename:
            raise FetcherError(
                f"JVRead returned {error_code} without a filename; cannot self-repair safely"
            )
        if self._jv_open_context is None:
            raise FetcherError("JVRead self-repair has no JVOpen context")
        if self._jvd_self_repair_attempts >= self.JVD_SELF_REPAIR_MAX_RETRIES:
            self._delete_corrupt_file_best_effort(error_code, filename)
            raise FetcherError(
                f"JVRead returned {error_code} for {filename} after "
                f"{self._jvd_self_repair_attempts} self-repair retries"
            )

        try:
            delete_result = self.jvlink.jv_file_delete(filename)
        except Exception as exc:
            raise FetcherError(
                f"JVFiledelete failed for {filename} after JVRead {error_code}"
            ) from exc
        if delete_result not in (None, 0):
            raise FetcherError(
                f"JVFiledelete returned {delete_result} for {filename} "
                f"after JVRead {error_code}"
            )

        # The same JVOpen context restarts at the beginning of the stream.
        # Remember the successfully emitted prefix so _fetch_and_parse can
        # drain it without parsing, yielding, or appending it to raw cache.
        self._jvd_replay_records_remaining = self._records_fetched
        expected_read_count = self._total_files
        expected_last_file_timestamp = self._jv_open_last_file_timestamp
        try:
            self.jvlink.jv_close()
            data_spec, fromtime, option = self._jv_open_context
            result, read_count, download_count, last_file_timestamp = self.jvlink.jv_open(
                data_spec,
                fromtime,
                option,
            )
            if result == -1 or (read_count == 0 and download_count == 0):
                raise FetcherError(
                    "JVOpen returned no data while recovering "
                    f"{filename} after JVRead {error_code}"
                )
            if download_count == 0 or read_count != expected_read_count:
                raise FetcherError(
                    f"JVOpen did not restore {filename} after JVRead {error_code}: "
                    f"read_count={read_count}, expected_exactly={expected_read_count}, "
                    f"download_count={download_count}"
                )
            if last_file_timestamp != expected_last_file_timestamp:
                raise FetcherError(
                    f"JVOpen stream changed while recovering {filename} after "
                    f"JVRead {error_code}: last_file_timestamp="
                    f"{last_file_timestamp!r}, expected="
                    f"{expected_last_file_timestamp!r}"
                )
            if download_count > 0:
                self._wait_for_download(download_count=download_count)
        except Exception as exc:
            raise FetcherError(
                f"Failed to reopen JVOpen after deleting {filename} "
                f"for JVRead {error_code}"
            ) from exc

        self._jvd_self_repair_attempts += 1
        self._files_processed = 0
        self._total_files = read_count
        if self.progress_display is not None and self._fetch_task_id is not None:
            self.progress_display.update(
                self._fetch_task_id,
                completed=0,
                total=read_count,
                status=f"再取得 0/{read_count}",
            )
        logger.warning(
            "Recovered historical JVRead file error by targeted delete and reopen",
            error_code=error_code,
            filename=filename,
            attempt=self._jvd_self_repair_attempts,
            result_code=result,
            read_count=read_count,
            download_count=download_count,
            replay_records=self._jvd_replay_records_remaining,
            last_file_timestamp=last_file_timestamp,
        )

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
        # Fetcher instances are reused across data specs and setup chunks.
        # Reset before JVOpen so no-data/error early exits cannot expose
        # statistics left over from the preceding invocation.
        self.reset_statistics()

        # Create progress display if enabled
        if self.show_progress:
            self.progress_display = JVLinkProgressDisplay()
            self.progress_display.start()

        download_task_id = None
        fetch_task_id = None
        # option=2 uses fromtime only for continuity within current race-cycle
        # data; it cannot prove an arbitrary requested historical range
        # complete. Bypass both existing NL cache markers and write-through
        # caching for that mode.
        active_cache_manager = self.cache_manager if option != 2 else None
        cache_checkpoints: dict[str, Optional[int]] = {}
        cache_write_committed = active_cache_manager is None
        cache_range_complete = True

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
            self._jvd_self_repair_attempts = 0
            self._jvd_replay_records_remaining = 0
            self._jv_open_context = (data_spec, fromtime, option)
            self._jv_open_last_file_timestamp = None

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
            self._jv_open_last_file_timestamp = last_file_timestamp

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
                        total=download_count,
                    )
                self._wait_for_download(download_task_id, download_count=download_count)

            # Set total files after JVOpen reports the stream size.
            self._total_files = read_count

            # Create fetch progress task
            if self.progress_display:
                fetch_task_id = self.progress_display.add_task(
                    f"{data_spec} レコード取得",
                    total=read_count,
                )
                self._fetch_task_id = fetch_task_id

            # Fetch and parse records (with optional cache write-through).
            # The cache stores raw jv_read buffers, so write once per buffer, not
            # once per parsed record: full-struct parsers (H1/H6) expand one
            # buffer into thousands of rows that all carry the same `_raw`. Rows
            # from one buffer share a header, hence the same record date, so the
            # first surviving row stands in for all of them. Identity is a safe
            # "same buffer" test because each jv_read() returns a new bytes
            # object and last_cached_raw keeps it alive.
            last_cached_raw = None
            for data in self._fetch_and_parse(
                fetch_task_id,
                to_date=to_date,
                recover_file_error=self._recover_historical_read_error,
                consume_replayed_record=self._consume_replayed_record,
                replay_pending=lambda: self._jvd_replay_records_remaining > 0,
            ):
                raw = data.get("_raw") if active_cache_manager else None
                if raw is not None and raw is not last_cached_raw:
                    last_cached_raw = raw
                    rec_date = _extract_record_date(data)
                    if rec_date:
                        if rec_date not in cache_checkpoints:
                            cache_checkpoints[rec_date] = active_cache_manager.checkpoint_nl(
                                data_spec,
                                rec_date,
                            )
                        active_cache_manager.write_nl_record(data_spec, rec_date, raw)
                    else:
                        # The record is yielded/imported, but cannot be replayed
                        # from this date-keyed cache. Keep the range incomplete;
                        # the finally block rolls back any partial appends.
                        cache_range_complete = False
                yield data

            if self._jvd_replay_records_remaining > 0:
                raise FetcherError(
                    "Historical stream ended before recovery replay caught up; "
                    f"{self._jvd_replay_records_remaining} record(s) remain"
                )
            if self._recoverable_read_errors > 0:
                raise FetcherError(
                    "Historical stream completed with "
                    f"{self._recoverable_read_errors} unrepaired JVRead error(s); "
                    "refusing to commit incomplete output"
                )

            # Mark cached dates as complete
            if active_cache_manager and cache_range_complete:
                from datetime import timedelta
                d = datetime.strptime(from_date, "%Y%m%d").date()
                end = datetime.strptime(to_date, "%Y%m%d").date()
                completed_dates = []
                while d <= end:
                    completed_dates.append(d.strftime("%Y%m%d"))
                    d += timedelta(days=1)
                active_cache_manager.mark_nl_range_complete(
                    data_spec,
                    completed_dates,
                )
                cache_write_committed = True
            elif active_cache_manager:
                logger.warning(
                    "NL cache range left incomplete because records lacked a supported event date",
                    data_spec=data_spec,
                    from_date=from_date,
                    to_date=to_date,
                )

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
            raise FetcherError(f"Historical fetch failed: {e}") from e

        finally:
            if not cache_write_committed and active_cache_manager:
                for rec_date, checkpoint in cache_checkpoints.items():
                    try:
                        active_cache_manager.restore_nl(
                            data_spec,
                            rec_date,
                            checkpoint,
                        )
                    except Exception as rollback_error:
                        logger.error(
                            "Failed to roll back incomplete NL cache append",
                            data_spec=data_spec,
                            record_date=rec_date,
                            error=str(rollback_error),
                        )
            self._jv_open_context = None
            self._jv_open_last_file_timestamp = None
            self._fetch_task_id = None
            # Close stream (JVClose) — releases the current open session so
            # the next jv_init()/jv_open() call in a subsequent chunk works.
            try:
                self.jvlink.jv_close()
                logger.info("Data stream closed")
            except Exception as e:
                logger.warning(f"Failed to close stream: {e}")

            # Do NOT call cleanup() here: cleanup() destroys the COM object
            # (self._jvlink = None + CoUninitialize), so subsequent chunks
            # would hit 'NoneType' object has no attribute 'JVInit'.
            # cleanup() is called by BatchProcessor.__del__ / explicit close.

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

    def fetch_with_cache(self, cache_manager, data_spec: str, from_date: str, to_date: str, option: int = 1) -> Iterator[dict]:
        """Fetch records: use cache if complete, else fetch from JV-Link and populate cache.

        Args:
            cache_manager: CacheManager instance
            data_spec: Data specification code (e.g., "RACE")
            from_date: Start date in YYYYMMDD format
            to_date: End date in YYYYMMDD format
            option: JVOpen option (default: 1)

        Yields:
            Dictionary of parsed record data
        """
        if option == 2:
            # Do not trust old false-complete markers created by earlier
            # versions, and do not attach a manager that could create new ones.
            yield from self.fetch(data_spec, from_date, to_date, option)
        elif cache_manager.has_nl_range(data_spec, from_date, to_date):
            # Full cache hit: yield from cache
            self.reset_statistics()
            for raw in cache_manager.read_nl(data_spec, from_date, to_date):
                self._records_fetched += 1
                try:
                    parsed = self.parser_factory.parse(raw)
                    if not parsed:
                        self._records_failed += 1
                        logger.warning(
                            "Failed to parse cached record",
                            record_num=self._records_fetched,
                            data_spec=data_spec,
                        )
                        continue

                    records = parsed if isinstance(parsed, list) else [parsed]
                    for record in records:
                        self._records_parsed += 1
                        record["_raw"] = raw
                        yield record
                except Exception as error:
                    self._records_failed += 1
                    logger.error(
                        "Error parsing cached record",
                        record_num=self._records_fetched,
                        data_spec=data_spec,
                        error=str(error),
                    )
        else:
            # Cache miss: fetch from JV-Link, write to cache
            self.cache_manager = cache_manager
            try:
                yield from self.fetch(data_spec, from_date, to_date, option)
            finally:
                self.cache_manager = None

    def _wait_for_download(
        self,
        download_task_id: Optional[int] = None,
        *,
        download_count: int,
        timeout: int = 600,
        interval: float = 0.08,
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
        if download_count <= 0:
            return

        last_progress_time = start_time  # Track when downloaded-file count last changed.
        stall_timeout = 300.0  # 5 minutes before stall abort

        # Retryable error codes (temporary errors that may resolve)
        #
        # Official meanings (JV-Link "3. コード表", JVStatus section) differ
        # from the labels below:
        # -201: JVInit not called (not "database busy")
        # -202: previous JVOpen/JVRTOpen/JVMVOpen not JVClose'd (not "file busy")
        # -203: JVOpen not called (not "incomplete setup/cache issue")
        # -502: download failed (communication/disk error)
        # -503: (JVStatus doesn't define -503; kept here for the bounded
        #        max_retries=2 safety net below in case JVRead's -503,
        #        file not found, surfaces through this status poll)
        #
        # -201/-203 indicate a call-order bug (JVInit/JVOpen genuinely not
        # called), which polling jv_status() again cannot fix -- it will keep
        # returning the same code. They remain in this retryable set
        # unchanged (bounded by max_retries=2 below) pending a decision on
        # whether that's still the right classification.
        retryable_errors = {-201, -202, -203, -502, -503}

        while True:
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise FetcherError(f"Download timeout after {elapsed:.1f} seconds")

            try:
                # Get download status
                # JVStatus returns the number of downloaded files, not a
                # percentage.  Download is complete when the count reaches the
                # JVOpen download_count value.
                status = self.jvlink.jv_status()

                if status >= download_count:
                    logger.info(
                        "Download completed",
                        elapsed_seconds=int(elapsed),
                        downloaded_files=status,
                        download_count=download_count,
                    )
                    if self.progress_display and download_task_id is not None:
                        self.progress_display.update_download(
                            download_task_id,
                            completed=download_count,
                            status="完了",
                        )
                    # Wait for file system write completion
                    wait_time = 0.5
                    logger.info("Waiting for file write completion...", wait_seconds=wait_time)
                    time.sleep(wait_time)
                    logger.info("File write wait completed")
                    return

                if status != last_status:
                    last_progress_time = time.time()  # Reset stall timer on any change
                    if status >= 0:
                        progress_percent = min(100.0, (status / download_count) * 100.0)
                        logger.info(
                            "Download in progress",
                            downloaded_files=status,
                            download_count=download_count,
                            progress_percent=progress_percent,
                            elapsed_seconds=int(elapsed),
                        )
                        # Update progress display
                        if self.progress_display and download_task_id is not None:
                            self.progress_display.update_download(
                                download_task_id,
                                completed=status,
                                status=f"{status}/{download_count} - {int(elapsed)}秒経過",
                            )
                        # Reset retry count on progress
                        retry_count = 0
                    last_status = status
                else:
                    # Stall detection: abort if downloaded-file count does not
                    # change for a long time before all files are downloaded.
                    if status >= 0:
                        stall_elapsed = time.time() - last_progress_time
                        if stall_elapsed >= stall_timeout:
                            logger.warning(
                                "Download stalled (downloaded file count did not change), treating as timeout",
                                last_status=status,
                                download_count=download_count,
                                stall_seconds=stall_elapsed,
                            )
                            raise FetcherError(
                                f"Download stalled at {status}/{download_count} files for {stall_elapsed:.0f}s"
                            )

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
