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
    is_time_series_spec,
    generate_time_series_key,
    generate_time_series_full_key,
    JYO_CODES,
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

            # -1は「該当データなし」（正常系）- 空のジェネレータとして返す
            if ret == -1:
                logger.debug("No data available for this key", data_spec=data_spec, key=key)
                return  # yieldなしで終了

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

    def fetch_time_series(
        self,
        data_spec: str,
        jyo_code: str,
        race_num: int,
        date: Optional[str] = None,
    ) -> Iterator[dict]:
        """Fetch time series data (時系列データ).

        Convenience method for fetching time series data (0B20, 0B30-0B36).
        Automatically generates the required YYYYMMDDJJRR format key.

        Args:
            data_spec: Time series data spec code
                      - 0B20: 票数情報
                      - 0B30: 単勝オッズ
                      - 0B31: 複勝・枠連オッズ
                      - 0B32: 馬連オッズ
                      - 0B33: ワイドオッズ
                      - 0B34: 馬単オッズ
                      - 0B35: 3連複オッズ
                      - 0B36: 3連単オッズ
            jyo_code: Track code (01-10)
                      01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京,
                      06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
            race_num: Race number (1-12)
            date: Date in YYYYMMDD format. If None, uses today's date.

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If data_spec is not time series or parameters invalid

        Examples:
            >>> # Fetch odds for race 11 at Tokyo (track 05)
            >>> for record in fetcher.fetch_time_series("0B30", "05", 11):
            ...     print(record)

            >>> # Fetch with specific date
            >>> for record in fetcher.fetch_time_series("0B31", "06", 1, "20251130"):
            ...     print(record)
        """
        # Validate data_spec
        if not is_time_series_spec(data_spec):
            raise FetcherError(
                f"Data spec {data_spec} is not a time series spec. "
                f"Time series specs: {', '.join(sorted(JVRTOPEN_TIME_SERIES_SPECS.keys()))}"
            )

        # Validate jyo_code
        if jyo_code not in JYO_CODES:
            raise FetcherError(
                f"Invalid jyo_code: {jyo_code}. "
                f"Available: {', '.join(f'{k}={v}' for k, v in sorted(JYO_CODES.items()))}"
            )

        # Validate race_num
        if not isinstance(race_num, int) or not (1 <= race_num <= 12):
            raise FetcherError(f"Invalid race_num: {race_num}. Must be 1-12.")

        # Generate date if not provided
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")

        # Generate key: YYYYMMDDJJRR
        key = generate_time_series_key(date, jyo_code, race_num)

        logger.info(
            "Fetching time series data",
            data_spec=data_spec,
            spec_name=JVRTOPEN_TIME_SERIES_SPECS.get(data_spec, "Unknown"),
            track=JYO_CODES[jyo_code],
            jyo_code=jyo_code,
            race_num=race_num,
            date=date,
            key=key,
        )

        # Use existing fetch method with generated key
        yield from self.fetch(data_spec=data_spec, key=key, continuous=False)

    @staticmethod
    def list_data_specs() -> dict:
        """Get available realtime data specification codes.

        Returns:
            Dictionary mapping data spec codes to descriptions
        """
        return RT_DATA_SPECS.copy()

    @staticmethod
    def list_time_series_specs() -> dict:
        """Get available time series data specification codes.

        Returns:
            Dictionary mapping time series spec codes to descriptions
        """
        return JVRTOPEN_TIME_SERIES_SPECS.copy()

    @staticmethod
    def list_tracks() -> dict:
        """Get available track codes.

        Returns:
            Dictionary mapping track codes to names
        """
        return JYO_CODES.copy()

    def fetch_time_series_batch_from_db(
        self,
        data_spec: str,
        db_path: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Iterator[dict]:
        """Fetch time series odds for races registered in the database.

        Based on JVLinkToSQLite implementation: JVRTOpen requires a full key
        with Kaiji (回次) and Nichiji (日次), which can only be obtained from
        previously fetched race data in NL_RA table.

        Key format: YYYYMMDD + JyoCD + Kaiji + Nichiji + RaceNum (16 digits)
        Example: 2025113005050811

        公式情報:
        - 提供期間: 過去1年間
        - データ提供開始: 2003年10月4日以降（保証外）

        Args:
            data_spec: Time series data spec code
                      - 0B30: 単勝オッズ (O1)
                      - 0B31: 複勝・枠連オッズ (O1, O2)
                      - 0B32: 馬連オッズ (O2)
                      - 0B33: ワイドオッズ (O3)
                      - 0B34: 馬単オッズ (O4)
                      - 0B35: 3連複オッズ (O5)
                      - 0B36: 3連単オッズ (O6)
            db_path: Path to SQLite database with NL_RA table
            from_date: Start date in YYYYMMDD format (optional)
            to_date: End date in YYYYMMDD format (optional)

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If data_spec is not time series or db not accessible

        Examples:
            >>> # Fetch odds for all races in the database
            >>> for record in fetcher.fetch_time_series_batch_from_db(
            ...     "0B30", "data/keiba.db"
            ... ):
            ...     print(record)

            >>> # Fetch for specific date range
            >>> for record in fetcher.fetch_time_series_batch_from_db(
            ...     "0B31", "data/keiba.db",
            ...     from_date="20251101", to_date="20251130"
            ... ):
            ...     print(record)
        """
        import sqlite3
        from pathlib import Path

        # Validate data_spec
        if not is_time_series_spec(data_spec):
            raise FetcherError(
                f"Data spec {data_spec} is not a time series spec. "
                f"Time series specs: {', '.join(sorted(JVRTOPEN_TIME_SERIES_SPECS.keys()))}"
            )

        # Validate database path
        db_file = Path(db_path)
        if not db_file.exists():
            raise FetcherError(f"Database not found: {db_path}")

        # Build query for race keys from NL_RA
        query = """
            SELECT DISTINCT
                Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
            FROM NL_RA
            WHERE 1=1
        """
        params = []

        if from_date:
            # Convert YYYYMMDD to Year and MonthDay
            year = from_date[:4]
            monthday = from_date[4:]
            query += " AND (Year > ? OR (Year = ? AND MonthDay >= ?))"
            params.extend([year, year, monthday])

        if to_date:
            year = to_date[:4]
            monthday = to_date[4:]
            query += " AND (Year < ? OR (Year = ? AND MonthDay <= ?))"
            params.extend([year, year, monthday])

        query += " ORDER BY Year, MonthDay, JyoCD, RaceNum"

        logger.info(
            "Starting batch time series fetch from database",
            data_spec=data_spec,
            spec_name=JVRTOPEN_TIME_SERIES_SPECS.get(data_spec, "Unknown"),
            db_path=db_path,
            from_date=from_date,
            to_date=to_date,
        )

        # Get race keys from database
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            race_rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            raise FetcherError(f"Database query failed: {e}")

        if not race_rows:
            logger.warning("No races found in database for the specified criteria")
            return

        logger.info(f"Found {len(race_rows)} races in database")

        # Initialize JV-Link
        ret = self.jvlink.jv_init()
        if ret != JV_RT_SUCCESS:
            raise FetcherError(f"JV-Link initialization failed: {ret}")

        # Statistics
        total_keys = len(race_rows)
        success_keys = 0
        no_data_keys = 0
        error_keys = 0
        total_records = 0

        try:
            for row in race_rows:
                year, monthday, jyo_cd, kaiji, nichiji, race_num = row

                # Build date string: YYYYMMDD
                date_str = f"{year}{monthday:04d}" if isinstance(monthday, int) else f"{year}{monthday}"

                # Convert values to proper types
                kaiji_int = int(kaiji) if kaiji else 1
                nichiji_int = int(nichiji) if nichiji else 1
                race_num_int = int(race_num) if race_num else 1

                # Generate full 16-digit key
                try:
                    key = generate_time_series_full_key(
                        date_str, jyo_cd, kaiji_int, nichiji_int, race_num_int
                    )
                except ValueError as e:
                    logger.warning(f"Invalid key parameters: {e}")
                    error_keys += 1
                    continue

                try:
                    ret, read_count = self.jvlink.jv_rt_open(data_spec, key)

                    if ret == -1:
                        no_data_keys += 1
                        logger.debug(
                            "No data for key",
                            key=key,
                            track=JYO_CODES.get(jyo_cd, jyo_cd),
                            race=race_num_int,
                        )
                        continue

                    if ret != JV_RT_SUCCESS:
                        error_keys += 1
                        logger.warning(
                            "JVRTOpen error",
                            key=key,
                            error_code=ret,
                        )
                        continue

                    # Read all records for this key
                    success_keys += 1
                    records_for_key = 0

                    for record in self._fetch_and_parse():
                        records_for_key += 1
                        total_records += 1
                        yield record

                    logger.debug(
                        "Fetched records for key",
                        key=key,
                        track=JYO_CODES.get(jyo_cd, jyo_cd),
                        race=race_num_int,
                        records=records_for_key,
                    )

                    # Close stream before opening next
                    self.jvlink.jv_close()

                except Exception as e:
                    error_keys += 1
                    if '-114' in str(e):
                        logger.debug("Not subscribed for key", key=key, error=str(e))
                    else:
                        logger.warning("Error fetching key", key=key, error=str(e))
                    try:
                        self.jvlink.jv_close()
                    except:
                        pass

        finally:
            try:
                self.jvlink.jv_close()
            except:
                pass

        logger.info(
            "Batch time series fetch completed",
            data_spec=data_spec,
            total_keys=total_keys,
            success_keys=success_keys,
            no_data_keys=no_data_keys,
            error_keys=error_keys,
            total_records=total_records,
        )

    def fetch_time_series_batch(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        jyo_codes: Optional[List[str]] = None,
        race_nums: Optional[List[int]] = None,
    ) -> Iterator[dict]:
        """Fetch time series data for multiple races in a date range.

        NOTE: This method uses the simplified 12-digit key format (YYYYMMDDJJRR)
        which may not work for batch retrieval. For reliable batch retrieval,
        use fetch_time_series_batch_from_db() which uses the full 16-digit key
        format with Kaiji and Nichiji from the database.

        Based on JVLinkToSQLite implementation pattern: JVRTOpen does NOT
        support date range queries, so this method loops through individual
        race keys (YYYYMMDDJJRR format).

        公式情報 (https://developer.jra-van.jp/t/topic/112):
        - 公式提供期間: 過去1年間
        - 実際の遡及可能期間: 2003年10月4日まで（保証外）
        - JV-Link速報系データ: 1週間分のみ保存
        - 多くのユーザーは独自に蓄積している

        時系列オッズの蓄積について:
        - TS_O1-O6テーブル（HassoTimeをPKに含む）を使用して蓄積可能
        - RealtimeUpdater.process_record(buff, timeseries=True) で保存
        - 蓄積系オッズ(O1-O6)は最終確定オッズのみ、時系列オッズは推移を記録

        Args:
            data_spec: Time series data spec code
                      - 0B20: 票数情報 (H1, H6)
                      - 0B30: 単勝オッズ (O1)
                      - 0B31: 複勝・枠連オッズ (O1, O2)
                      - 0B32: 馬連オッズ (O2)
                      - 0B33: ワイドオッズ (O3)
                      - 0B34: 馬単オッズ (O4)
                      - 0B35: 3連複オッズ (O5)
                      - 0B36: 3連単オッズ (O6)
            from_date: Start date in YYYYMMDD format
            to_date: End date in YYYYMMDD format
            jyo_codes: List of track codes to fetch. If None, fetches all 10 tracks.
                      01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京,
                      06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉
            race_nums: List of race numbers to fetch. If None, fetches all 12 races.

        Yields:
            Dictionary of parsed record data

        Raises:
            FetcherError: If data_spec is not time series

        Note:
            - JVRTOpen returns -1 for "no data" (race not held), which is normal
            - Data availability depends on JRA-VAN server, not local setup
            - For best results, use dates with known race events
            - 提供期間外（1年以上前）のデータは取得できない可能性があります

        Examples:
            >>> # Fetch Win odds for all tracks on a specific day
            >>> for record in fetcher.fetch_time_series_batch("0B30", "20251130", "20251130"):
            ...     print(record)

            >>> # Fetch for specific tracks and races over a week
            >>> for record in fetcher.fetch_time_series_batch(
            ...     "0B31",
            ...     "20251124",
            ...     "20251130",
            ...     jyo_codes=["05", "06", "09"],  # Tokyo, Nakayama, Hanshin
            ...     race_nums=[11, 12]  # Main races only
            ... ):
            ...     print(record)
        """
        from datetime import datetime, timedelta

        # Validate data_spec
        if not is_time_series_spec(data_spec):
            raise FetcherError(
                f"Data spec {data_spec} is not a time series spec. "
                f"Time series specs: {', '.join(sorted(JVRTOPEN_TIME_SERIES_SPECS.keys()))}"
            )

        # Default to all tracks if not specified
        if jyo_codes is None:
            jyo_codes = list(JYO_CODES.keys())  # ["01", "02", ..., "10"]

        # Validate jyo_codes
        for jyo in jyo_codes:
            if jyo not in JYO_CODES:
                raise FetcherError(
                    f"Invalid jyo_code: {jyo}. "
                    f"Available: {', '.join(f'{k}={v}' for k, v in sorted(JYO_CODES.items()))}"
                )

        # Default to all 12 races if not specified
        if race_nums is None:
            race_nums = list(range(1, 13))  # [1, 2, ..., 12]

        # Validate race_nums
        for race in race_nums:
            if not isinstance(race, int) or not (1 <= race <= 12):
                raise FetcherError(f"Invalid race_num: {race}. Must be 1-12.")

        # Parse dates
        try:
            start = datetime.strptime(from_date, "%Y%m%d")
            end = datetime.strptime(to_date, "%Y%m%d")
        except ValueError as e:
            raise FetcherError(f"Invalid date format: {e}")

        if start > end:
            raise FetcherError(f"from_date ({from_date}) must be <= to_date ({to_date})")

        logger.info(
            "Starting batch time series fetch",
            data_spec=data_spec,
            spec_name=JVRTOPEN_TIME_SERIES_SPECS.get(data_spec, "Unknown"),
            from_date=from_date,
            to_date=to_date,
            tracks=len(jyo_codes),
            races=len(race_nums),
        )

        # Initialize JV-Link once for the entire batch
        ret = self.jvlink.jv_init()
        if ret != JV_RT_SUCCESS:
            raise FetcherError(f"JV-Link initialization failed: {ret}")

        # Statistics
        total_keys = 0
        success_keys = 0
        no_data_keys = 0
        error_keys = 0
        total_records = 0

        try:
            # Loop through date range
            current_date = start
            while current_date <= end:
                date_str = current_date.strftime("%Y%m%d")

                # Loop through tracks
                for jyo_code in jyo_codes:
                    # Loop through races
                    for race_num in race_nums:
                        total_keys += 1

                        # Generate key: YYYYMMDDJJRR
                        key = generate_time_series_key(date_str, jyo_code, race_num)

                        try:
                            ret, read_count = self.jvlink.jv_rt_open(data_spec, key)

                            if ret == -1:
                                # No data for this race (not held or not available)
                                no_data_keys += 1
                                logger.debug(
                                    "No data for key",
                                    key=key,
                                    track=JYO_CODES[jyo_code],
                                    race=race_num,
                                )
                                continue

                            if ret != JV_RT_SUCCESS:
                                error_keys += 1
                                logger.warning(
                                    "JVRTOpen error",
                                    key=key,
                                    error_code=ret,
                                )
                                continue

                            # Read all records for this key
                            success_keys += 1
                            records_for_key = 0

                            for record in self._fetch_and_parse():
                                records_for_key += 1
                                total_records += 1
                                yield record

                            logger.debug(
                                "Fetched records for key",
                                key=key,
                                track=JYO_CODES[jyo_code],
                                race=race_num,
                                records=records_for_key,
                            )

                            # Close stream for this key before opening next
                            self.jvlink.jv_close()

                        except Exception as e:
                            error_keys += 1
                            # -114: 契約外エラーは警告として処理
                            if '-114' in str(e):
                                logger.debug("Not subscribed for key", key=key, error=str(e))
                            else:
                                logger.warning("Error fetching key", key=key, error=str(e))
                            try:
                                self.jvlink.jv_close()
                            except:
                                pass

                # Move to next date
                current_date += timedelta(days=1)

        finally:
            # Ensure stream is closed
            try:
                self.jvlink.jv_close()
            except:
                pass

        logger.info(
            "Batch time series fetch completed",
            data_spec=data_spec,
            total_keys=total_keys,
            success_keys=success_keys,
            no_data_keys=no_data_keys,
            error_keys=error_keys,
            total_records=total_records,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._close_stream()
        return False
