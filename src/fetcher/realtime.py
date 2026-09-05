"""Realtime data fetcher for JLTSQL.

This module provides realtime data fetching from JV-Link.
"""

from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.fetcher.base import BaseFetcher, FetcherError
from src.jvlink.constants import (
    JYO_CODES,
    JV_RT_SUCCESS,
    JVRTOPEN_SPEED_REPORT_SPECS,
    JVRTOPEN_TIME_SERIES_SPECS,
    generate_time_series_key,
    is_time_series_spec,
)
from src.parser.status_domain import DataKubunContext, validate_data_kubun
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Japan has observed UTC+09:00 year-round since 1951.  A fixed offset avoids
# making the base/SQLite installation depend on an IANA tzdata package, which
# is not present by default on Windows.
JST = timezone(timedelta(hours=9), name="JST")


def _now_jst() -> datetime:
    """Return the race-window reference clock in Japan time."""
    return datetime.now(JST)


def _filter_race_rows_by_post_time(
    race_rows: list[tuple],
    *,
    post_time_within_minutes: Optional[int],
    post_time_not_past_minutes: Optional[int],
) -> tuple[list[tuple], dict[str, int]]:
    """Date-filter, validate, de-duplicate, and post-time-filter race rows."""
    now = _now_jst()
    if now.tzinfo is None or now.utcoffset() is None:
        raise FetcherError("Race post-time window clock must be timezone-aware")
    now = now.astimezone(JST)

    grouped: dict[str, list[tuple]] = {}
    race_dates: dict[str, datetime] = {}
    for row in race_rows:
        if len(row) != 7:
            raise FetcherError(
                "Race post-time window requires Year, MonthDay, JyoCD, "
                "Kaiji, Nichiji, RaceNum, and HassoTime"
            )
        year, monthday, jyo_cd, _kaiji, _nichiji, race_num, _post_time = row
        try:
            date_str = f"{int(year):04d}{int(monthday):04d}"
            race_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=JST)
            jyo_cd_text = str(jyo_cd).strip().zfill(2)
            key = generate_time_series_key(date_str, jyo_cd_text, int(race_num))
        except (TypeError, ValueError) as exc:
            raise FetcherError(
                "Race post-time window cannot name invalid race identity " f"{row[:6]!r}: {exc}"
            ) from exc
        grouped.setdefault(key, []).append(row)
        race_dates.setdefault(key, race_date)

    latest_allowed = (
        now + timedelta(minutes=post_time_within_minutes)
        if post_time_within_minutes is not None
        else None
    )
    earliest_allowed = (
        now - timedelta(minutes=post_time_not_past_minutes)
        if post_time_not_past_minutes is not None
        else None
    )
    candidates: dict[str, list[tuple]] = {}
    dropped_too_far_future = 0
    dropped_too_far_past = 0
    skipped_out_of_window_by_date = 0
    for key, rows in grouped.items():
        race_date_start = race_dates[key]
        race_date_end = race_date_start + timedelta(days=1) - timedelta(minutes=1)
        if latest_allowed is not None and race_date_start > latest_allowed:
            dropped_too_far_future += 1
            skipped_out_of_window_by_date += 1
        elif earliest_allowed is not None and race_date_end < earliest_allowed:
            dropped_too_far_past += 1
            skipped_out_of_window_by_date += 1
        else:
            candidates[key] = rows

    validated: list[tuple[tuple, datetime]] = []
    problems: list[str] = []
    for key, rows in candidates.items():
        raw_post_times = [row[6] for row in rows]
        normalized_post_times = {
            str(value).strip()
            for value in raw_post_times
            if value is not None and str(value).strip()
        }
        if any(value is None or not str(value).strip() for value in raw_post_times):
            problems.append(f"{key}: missing HassoTime")
            continue
        if len(normalized_post_times) != 1:
            values = ", ".join(sorted(normalized_post_times))
            problems.append(f"{key}: ambiguous HassoTime values [{values}]")
            continue

        post_time_text = next(iter(normalized_post_times))
        if (
            len(post_time_text) != 4
            or not post_time_text.isascii()
            or not post_time_text.isdigit()
            or int(post_time_text[:2]) > 23
            or int(post_time_text[2:]) > 59
        ):
            problems.append(f"{key}: unparsable HassoTime {post_time_text!r}")
            continue

        post_time = datetime.strptime(f"{key[:8]}{post_time_text}", "%Y%m%d%H%M").replace(
            tzinfo=JST
        )
        validated.append((rows[0][:6], post_time))

    if problems:
        raise FetcherError("Race post-time window rejected keys: " + "; ".join(problems))

    kept: list[tuple] = []
    for row, post_time in validated:
        minutes_until_post = (post_time - now).total_seconds() / 60
        if post_time_within_minutes is not None and minutes_until_post > post_time_within_minutes:
            dropped_too_far_future += 1
        elif (
            post_time_not_past_minutes is not None
            and minutes_until_post < -post_time_not_past_minutes
        ):
            dropped_too_far_past += 1
        else:
            kept.append(row)

    stats = {
        "considered_keys": len(grouped),
        "window_candidate_keys": len(candidates),
        "window_kept_keys": len(kept),
        "dropped_too_far_future": dropped_too_far_future,
        "dropped_too_far_past": dropped_too_far_past,
        "skipped_out_of_window_by_date": skipped_out_of_window_by_date,
    }
    return kept, stats


def _race_key_label(key_fields: tuple) -> str:
    """Name a race by its 12-digit JVRTOpen key, or raw fields when malformed."""
    year, monthday, jyo_cd, _kaiji, _nichiji, race_num = key_fields
    try:
        date_str = f"{int(year):04d}{int(monthday):04d}"
        return str(generate_time_series_key(date_str, str(jyo_cd).strip().zfill(2), int(race_num)))
    except (TypeError, ValueError):
        return repr(key_fields)


def _overlay_current_lifecycle_rows(
    race_rows: list[tuple],
) -> tuple[list[tuple], set[str]]:
    """Select the current lifecycle source for each exact full race key.

    Rows carry (LifecycleSource, DataKubun, Year, MonthDay, JyoCD, Kaiji,
    Nichiji, RaceNum, HassoTime). A same-day RT_RA row supersedes the
    historical NL_RA row for the identical full key before lifecycle-state
    validation, including cancellation status 9; NL_RA rows are used only for
    full keys absent from RT_RA. Duplicates from the selected source are
    preserved so a genuine 12-digit-key post-time conflict still fails closed
    downstream.

    Because DataKubun decides whether a selected row is active or canceled,
    every selected row must carry an officially valid current RA DataKubun
    (``src.parser.status_domain``); an undecidable status fails closed with
    the 12-digit race key named, and nothing is opened. DataKubun 0 is an
    erase instruction which the normal updater physically removes, so finding
    one persisted here is an inconsistent state and also fails closed.

    The selected full keys are also grouped by their normalized 12-digit
    JVRTOpen key. If one such key is both active and canceled, its state cannot
    be represented by JVRTOpen and the batch fails closed independent of row
    order. Returns the selected 7-column rows and the 12-digit keys whose
    selected rows all report cancellation (DataKubun 9) — from RT or NL alike,
    since selection already happened and RT 9 never exposes the NL row.
    Cancellations are not removed here: their rows stay subject to
    fail-closed post-time validation first.
    """
    rt_full_keys: set[tuple] = set()
    for row in race_rows:
        if len(row) != 9:
            raise FetcherError(
                "Race lifecycle overlay requires LifecycleSource, DataKubun, "
                "Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, and HassoTime"
            )
        if row[0] == "RT":
            rt_full_keys.add(tuple(row[2:8]))
        elif row[0] != "NL":
            raise FetcherError(f"Race lifecycle overlay cannot classify source {row[0]!r}")

    selected: list[tuple] = []
    lifecycle_states: dict[str, set[str]] = {}
    canceled_race_keys: set[str] = set()
    for row in race_rows:
        source, data_kubun = row[0], row[1]
        full_key = tuple(row[2:8])
        if source == "NL" and full_key in rt_full_keys:
            continue
        try:
            validated_kubun = validate_data_kubun(
                "RA",
                data_kubun,
                context=(
                    DataKubunContext.REALTIME if source == "RT" else DataKubunContext.ACCUMULATED
                ),
            )
        except ValueError as exc:
            raise FetcherError(
                f"Race lifecycle selection rejected {_race_key_label(row[2:8])}: {exc}"
            ) from exc
        race_key = _race_key_label(row[2:8])
        if validated_kubun == "0":
            raise FetcherError(
                f"Race lifecycle selection rejected {race_key}: "
                "persisted RA DataKubun '0' erase marker"
            )
        selected.append(tuple(row[2:]))
        lifecycle_state = "canceled" if validated_kubun == "9" else "active"
        lifecycle_states.setdefault(race_key, set()).add(lifecycle_state)
        if validated_kubun == "9":
            canceled_race_keys.add(race_key)

    mixed_state_keys = [key for key, states in lifecycle_states.items() if len(states) > 1]
    if mixed_state_keys:
        problems = "; ".join(
            f"{key}: ambiguous active/canceled lifecycle states" for key in mixed_state_keys
        )
        raise FetcherError("Race lifecycle selection rejected keys: " + problems)
    return selected, canceled_race_keys


def materialize_complete_records(
    fetcher,
    records: Iterable[dict],
    *,
    data_spec: str,
    key: str,
) -> list[dict]:
    """Materialize one realtime response and reject parser or transport loss."""
    materialized = list(records)
    statistics = fetcher.get_statistics()
    parser_failed = int(statistics.get("records_failed", 0) or 0)
    read_errors = int(statistics.get("recoverable_read_errors", 0) or 0)
    if parser_failed or read_errors:
        raise FetcherError(
            f"{data_spec} {key} response incomplete: "
            f"parser_failed={parser_failed}, recoverable_read_errors={read_errors}"
        )
    return materialized


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

    def __init__(
        self,
        sid: str = "JLTSQL",
    ):
        """Initialize realtime fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "JLTSQL")
        """
        super().__init__(sid)
        self._stream_open = False
        self.last_open_result: Optional[int] = None
        self.last_open_key: Optional[str] = None

    def _recover_file_error(self, error_code: int, filename: str) -> None:
        """Keep realtime snapshots fail-fast on corrupt JV-Link files."""
        self._delete_corrupt_file_best_effort(error_code, filename)
        raise FetcherError(
            f"Realtime JVRead returned {error_code} for " f"{filename or 'an unknown file'}"
        )

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
        # One fetcher may process several date/spec keys. Statistics must be
        # scoped to this response so snapshot completeness checks cannot see
        # failures left over from an earlier key.
        self.reset_statistics()
        self.last_open_result = None
        self.last_open_key = None

        if data_spec not in RT_DATA_SPECS:
            logger.warning(
                f"Unknown data spec: {data_spec}. " "Proceeding anyway, but this may not be valid."
            )

        # Default key to today's date if not specified
        # JVRTOpen requires a date key (YYYYMMDD) to function properly
        if key is None:
            from datetime import datetime

            key = datetime.now().strftime("%Y%m%d")
            logger.debug("Using today's date as key", key=key)

        try:
            # The session was established in BaseFetcher.__init__ and spans
            # every JVRTOpen below.
            logger.info(
                "Starting realtime data fetch",
                data_spec=data_spec,
                key=key,
                spec_name=RT_DATA_SPECS.get(data_spec, "Unknown"),
                continuous=continuous,
            )

            # Open realtime stream
            ret, read_count = self.jvlink.jv_rt_open(data_spec, key)
            self.last_open_result = ret
            self.last_open_key = key

            # Mark stream as potentially open (will be closed in finally block)
            # This ensures jv_close() is called even if an error occurs
            self._stream_open = True

            # -1は「該当データなし」（正常系）- 空のジェネレータとして返す
            if ret == -1:
                logger.debug("No data available for this key", data_spec=data_spec, key=key)
                return  # yieldなしで終了

            if ret != JV_RT_SUCCESS:
                raise FetcherError(f"JVRTOpen failed: {ret}")
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
            if "-114" in str(e):
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
                      - 0B30: 速報オッズ全賭式
                      - 0B31: 速報オッズ単複枠
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
        pg_config: Optional[dict] = None,
        progress_callback: Optional[Callable[[dict], None]] = None,
        post_time_within_minutes: Optional[int] = None,
        post_time_not_past_minutes: Optional[int] = None,
    ) -> Iterator[dict]:
        """Fetch time series odds for races registered in the database.

        Race targets are loaded from NL_RA so only actual races are queried.
        JVRTOpen odds time-series retrieval uses a 12-digit key.

        Key format: YYYYMMDD + JyoCD + RaceNum (12 digits)
        Example: 202511300511

        公式仕様:
        - 0B30〜0B36 は速報オッズで、提供単位はレース毎、保存期間は1週間
        - 0B41/0B42 は時系列オッズで、単複枠/馬連のみ、保存期間は1年間
        - ワイド以降の長期時系列は、開催週に0B30をTS_SOKUHO_O3〜TS_SOKUHO_O6へ蓄積する

        Args:
            data_spec: Time series data spec code
                      - 0B30: 速報オッズ全賭式 (O1-O6, 1週間)
                      - 0B31: 速報オッズ単複枠 (O1, 1週間)
                      - 0B32: 速報オッズ馬連 (O2, 1週間)
                      - 0B33: 速報オッズワイド (O3, 1週間)
                      - 0B34: 速報オッズ馬単 (O4, 1週間)
                      - 0B35: 速報オッズ3連複 (O5, 1週間)
                      - 0B36: 速報オッズ3連単 (O6, 1週間)
                      - 0B41: 時系列オッズ単複枠 (O1, 1年間)
                      - 0B42: 時系列オッズ馬連 (O2, 1年間)
            db_path: Path to SQLite database with NL_RA (and optionally
                     RT_RA) tables. Ignored when pg_config is supplied.
            from_date: Start date in YYYYMMDD format (optional)
            to_date: End date in YYYYMMDD format (optional)
            pg_config: PostgreSQL connection config. When supplied, race keys
                       are read from public.nl_ra and public.rt_ra instead
                       of SQLite.
            progress_callback: Optional callback called after each race key is
                               attempted. Receives counters and key status.
                               When a post-time window is requested, the
                               initial ``window_filter`` entry carries the
                               window statistics, including
                               ``omitted_canceled_keys``: the number of
                               normalized JVRTOpen keys whose selected
                               lifecycle rows all report DataKubun 9, passed
                               validation, and otherwise fell inside the
                               requested window. It is always present (0 when
                               none), and
                               ``window_kept_keys`` is reduced by the same
                               amount so it equals total_keys and the keys
                               actually opened.
            post_time_within_minutes: Keep keys no more than this many minutes
                                      before their race-record post time.
            post_time_not_past_minutes: Drop keys more than this many minutes
                                        after their race-record post time.

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
        from pathlib import Path

        # Validate data_spec
        if not is_time_series_spec(data_spec):
            raise FetcherError(
                f"Data spec {data_spec} is not a time series spec. "
                f"Time series specs: {', '.join(sorted(JVRTOPEN_TIME_SERIES_SPECS.keys()))}"
            )

        for option_name, option_value in (
            ("post_time_within_minutes", post_time_within_minutes),
            ("post_time_not_past_minutes", post_time_not_past_minutes),
        ):
            if option_value is not None and option_value < 0:
                raise FetcherError(f"{option_name} must be zero or greater")
        window_filter_requested = (
            post_time_within_minutes is not None or post_time_not_past_minutes is not None
        )

        # Forward-only 0B15 cards are stored in RT_RA, while historical RACE
        # records are stored in NL_RA. Without a post-time window both sources
        # are merged and de-duplicated on the key-bearing columns. With a
        # window, rows always keep their source and DataKubun so the selected
        # current lifecycle row is validated and can cancel its key: a current
        # RT_RA row supersedes the stale NL_RA row for the same full race key,
        # and when RT_RA is absent NL_RA owns every full key. This exposes no
        # result fields: only the race identity is used to construct the
        # JVRTOpen request key.
        if pg_config:
            if window_filter_requested:
                if self._postgres_table_exists(pg_config, "rt_ra"):
                    # UNION ALL: duplicates inside the selected source must
                    # survive the overlay so a genuine 12-digit-key post-time
                    # conflict still fails closed.
                    query = """
                        WITH race_targets AS (
                            SELECT 'RT' AS lifecycle_source, datakubun,
                                   year, monthday, jyocd, kaiji, nichiji, racenum, hassotime
                            FROM rt_ra
                            UNION ALL
                            SELECT 'NL', datakubun,
                                   year, monthday, jyocd, kaiji, nichiji, racenum, hassotime
                            FROM nl_ra
                        )
                        SELECT
                            lifecycle_source, datakubun,
                            year, monthday, jyocd, kaiji, nichiji, racenum, hassotime
                        FROM race_targets
                        WHERE 1=1
                    """
                else:
                    query = """
                        WITH race_targets AS (
                            SELECT 'NL' AS lifecycle_source, datakubun,
                                   year, monthday, jyocd, kaiji, nichiji, racenum, hassotime
                            FROM nl_ra
                        )
                        SELECT
                            lifecycle_source, datakubun,
                            year, monthday, jyocd, kaiji, nichiji, racenum, hassotime
                        FROM race_targets
                        WHERE 1=1
                    """
            else:
                rt_union = (
                    """
                    UNION
                    SELECT year, monthday, jyocd, kaiji, nichiji, racenum
                    FROM rt_ra
                """
                    if self._postgres_table_exists(pg_config, "rt_ra")
                    else ""
                )
                distinct = "" if rt_union else " DISTINCT"
                query = f"""
                WITH race_targets AS (
                    SELECT year, monthday, jyocd, kaiji, nichiji, racenum
                    FROM nl_ra
                    {rt_union}
                )
                SELECT{distinct}
                    year, monthday, jyocd, kaiji, nichiji, racenum
                FROM race_targets
                WHERE 1=1
            """
            params = []
            placeholder = "%s"
        else:
            # Validate database path
            db_file = Path(db_path)
            if not db_file.exists():
                raise FetcherError(f"Database not found: {db_path}")
            import sqlite3
            from contextlib import closing

            with closing(sqlite3.connect(db_path)) as conn:
                has_rt_ra = conn.execute("""
                        SELECT 1
                        FROM sqlite_master
                        WHERE type = 'table' AND lower(name) = lower('RT_RA')
                        """).fetchone() is not None
            if window_filter_requested:
                if has_rt_ra:
                    # UNION ALL: duplicates inside the selected source must
                    # survive the overlay so a genuine 12-digit-key post-time
                    # conflict still fails closed.
                    query = """
                        WITH race_targets AS (
                            SELECT 'RT' AS LifecycleSource, DataKubun,
                                   Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HassoTime
                            FROM RT_RA
                            UNION ALL
                            SELECT 'NL', DataKubun,
                                   Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HassoTime
                            FROM NL_RA
                        )
                        SELECT
                            LifecycleSource, DataKubun,
                            Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HassoTime
                        FROM race_targets
                        WHERE 1=1
                    """
                else:
                    query = """
                        WITH race_targets AS (
                            SELECT 'NL' AS LifecycleSource, DataKubun,
                                   Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HassoTime
                            FROM NL_RA
                        )
                        SELECT
                            LifecycleSource, DataKubun,
                            Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HassoTime
                        FROM race_targets
                        WHERE 1=1
                    """
            else:
                rt_union = (
                    """
                    UNION
                    SELECT Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
                    FROM RT_RA
                """
                    if has_rt_ra
                    else ""
                )
                distinct = "" if rt_union else " DISTINCT"
                query = f"""
                WITH race_targets AS (
                    SELECT Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
                    FROM NL_RA
                    {rt_union}
                )
                SELECT{distinct}
                    Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum
                FROM race_targets
                WHERE 1=1
            """
            params = []
            placeholder = "?"

        if from_date:
            # Convert YYYYMMDD to Year and MonthDay
            year = from_date[:4]
            monthday = from_date[4:]
            if pg_config:
                query += (
                    f" AND (year > {placeholder} OR "
                    f"(year = {placeholder} AND monthday >= {placeholder}))"
                )
                params.extend([int(year), int(year), int(monthday)])
            else:
                query += f" AND (Year > {placeholder} OR (Year = {placeholder} AND MonthDay >= {placeholder}))"
                params.extend([year, year, monthday])

        if to_date:
            year = to_date[:4]
            monthday = to_date[4:]
            if pg_config:
                query += (
                    f" AND (year < {placeholder} OR "
                    f"(year = {placeholder} AND monthday <= {placeholder}))"
                )
                params.extend([int(year), int(year), int(monthday)])
            else:
                query += f" AND (Year < {placeholder} OR (Year = {placeholder} AND MonthDay <= {placeholder}))"
                params.extend([year, year, monthday])

        if pg_config:
            query += (
                " AND LPAD(CAST(jyocd AS TEXT), 2, '0') "
                "IN ('01','02','03','04','05','06','07','08','09','10')"
            )
        else:
            query += (
                " AND printf('%02d', CAST(JyoCD AS INTEGER)) "
                "IN ('01','02','03','04','05','06','07','08','09','10')"
            )

        if pg_config:
            query += " ORDER BY year, monthday, jyocd, racenum"
        else:
            query += " ORDER BY Year, MonthDay, JyoCD, RaceNum"

        log_context = {}
        if window_filter_requested:
            log_context = {
                "post_time_within_minutes": post_time_within_minutes,
                "post_time_not_past_minutes": post_time_not_past_minutes,
            }
        logger.info(
            "Starting batch time series fetch from database",
            data_spec=data_spec,
            spec_name=JVRTOPEN_TIME_SERIES_SPECS.get(data_spec, "Unknown"),
            db_path="postgresql" if pg_config else db_path,
            from_date=from_date,
            to_date=to_date,
            **log_context,
        )

        # Get race keys from database
        try:
            if pg_config:
                race_rows = self._fetch_time_series_race_rows_from_postgres(
                    query, params, pg_config
                )
            else:
                import sqlite3
                from contextlib import closing

                with closing(sqlite3.connect(db_path)) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    race_rows = cursor.fetchall()
        except Exception as e:
            raise FetcherError(f"Database query failed: {e}")

        window_stats: Optional[dict[str, int]] = None
        if window_filter_requested:
            race_rows, canceled_race_keys = _overlay_current_lifecycle_rows(race_rows)
            race_rows, window_stats = _filter_race_rows_by_post_time(
                race_rows,
                post_time_within_minutes=post_time_within_minutes,
                post_time_not_past_minutes=post_time_not_past_minutes,
            )
            if canceled_race_keys:
                # A validated cancellation owns its normalized JVRTOpen key in
                # whichever source was selected: omit it without opening and
                # without falling back to the shadowed row. Mixed active and
                # canceled state for one 12-digit key was rejected above.
                race_rows = [
                    row
                    for row in race_rows
                    if _race_key_label(tuple(row[:6])) not in canceled_race_keys
                ]
            # omitted_canceled_keys counts normalized JVRTOpen keys whose
            # selected rows all report cancellation, passed validation, and
            # otherwise fell inside the requested window. It is always
            # reported (0 when none), and window_kept_keys shrinks by the same
            # amount so it equals total_keys/opened targets.
            omitted_canceled_keys = window_stats["window_kept_keys"] - len(race_rows)
            window_stats["window_kept_keys"] = len(race_rows)
            window_stats["omitted_canceled_keys"] = omitted_canceled_keys
            if omitted_canceled_keys:
                logger.info(
                    "Omitted canceled races after post-time validation",
                    omitted_canceled_keys=omitted_canceled_keys,
                )
            logger.info("Applied race post-time window", **window_stats)
            if progress_callback:
                progress_callback(
                    {
                        "status": "window_filter",
                        "key": None,
                        "processed_keys": 0,
                        "total_keys": len(race_rows),
                        **window_stats,
                        "success_keys": 0,
                        "nonempty_keys": 0,
                        "no_data_keys": 0,
                        "error_keys": 0,
                        "total_records": 0,
                    }
                )

        if not race_rows:
            logger.warning("No races found in database for the specified criteria")
            return

        logger.info(f"Found {len(race_rows)} races in database")

        # Statistics. nonempty_keys counts only keys whose complete buffered
        # response materialized at least one record: success_keys alone is not
        # evidence of nonempty capture.
        total_keys = len(race_rows)
        success_keys = 0
        nonempty_keys = 0
        no_data_keys = 0
        error_keys = 0
        total_records = 0

        try:
            processed_keys = 0

            for row in race_rows:
                processed_keys += 1
                year, monthday, jyo_cd, kaiji, nichiji, race_num = row

                # Build date string: YYYYMMDD
                date_str = (
                    f"{year}{monthday:04d}" if isinstance(monthday, int) else f"{year}{monthday}"
                )

                # Convert values to proper types. Kaiji/Nichiji are selected
                # from NL_RA for auditability, but JVRTOpen odds time-series
                # keys use the 12-digit YYYYMMDDJJRR form.
                race_num_int = int(race_num) if race_num else 1

                try:
                    key = generate_time_series_key(date_str, jyo_cd, race_num_int)
                except ValueError as e:
                    logger.warning(f"Invalid key parameters: {e}")
                    error_keys += 1
                    if progress_callback:
                        progress = {
                            "status": "invalid_key",
                            "key": None,
                            "processed_keys": processed_keys,
                            "total_keys": total_keys,
                            "success_keys": success_keys,
                            "nonempty_keys": nonempty_keys,
                            "no_data_keys": no_data_keys,
                            "error_keys": error_keys,
                            "records_for_key": 0,
                            "total_records": total_records,
                        }
                        if window_stats:
                            progress.update(window_stats)
                        progress_callback(progress)
                    continue

                records_for_key = 0
                key_status = "error"
                try:
                    ret, read_count = self.jvlink.jv_rt_open(data_spec, key)

                    if ret == -1:
                        no_data_keys += 1
                        key_status = "no_data"
                        logger.debug(
                            "No data for key",
                            key=key,
                            track=JYO_CODES.get(jyo_cd, jyo_cd),
                            race=race_num_int,
                        )
                        continue

                    if ret != JV_RT_SUCCESS:
                        error_keys += 1
                        key_status = f"error:{ret}"
                        logger.warning(
                            "JVRTOpen error",
                            key=key,
                            error_code=ret,
                        )
                        continue

                    # Buffer one complete race key before yielding.  A later
                    # JVRead error must not leave a partial key persisted by
                    # callers while this batch continues with the next key.
                    key_records = list(self._fetch_and_parse())
                    records_for_key = len(key_records)
                    success_keys += 1
                    if records_for_key:
                        nonempty_keys += 1
                    key_status = "success"
                    total_records += records_for_key
                    yield from key_records

                    logger.debug(
                        "Fetched records for key",
                        key=key,
                        track=JYO_CODES.get(jyo_cd, jyo_cd),
                        race=race_num_int,
                        records=records_for_key,
                    )

                except Exception as e:
                    error_keys += 1
                    key_status = "exception"
                    if "-114" in str(e):
                        logger.debug("Not subscribed for key", key=key, error=str(e))
                    else:
                        logger.warning("Error fetching key", key=key, error=str(e))
                finally:
                    try:
                        self.jvlink.jv_close()
                    except Exception:
                        pass
                    if progress_callback:
                        progress = {
                            "status": key_status,
                            "key": key,
                            "processed_keys": processed_keys,
                            "total_keys": total_keys,
                            "success_keys": success_keys,
                            "nonempty_keys": nonempty_keys,
                            "no_data_keys": no_data_keys,
                            "error_keys": error_keys,
                            "records_for_key": records_for_key,
                            "total_records": total_records,
                        }
                        if window_stats:
                            progress.update(window_stats)
                        progress_callback(progress)

        finally:
            try:
                self.jvlink.jv_close()
            except Exception:
                pass

        summary_context = window_stats or {}
        logger.info(
            "Batch time series fetch completed",
            data_spec=data_spec,
            total_keys=total_keys,
            success_keys=success_keys,
            nonempty_keys=nonempty_keys,
            no_data_keys=no_data_keys,
            error_keys=error_keys,
            total_records=total_records,
            **summary_context,
        )

    @staticmethod
    def _fetch_time_series_race_rows_from_postgres(
        query: str,
        params: list,
        pg_config: dict,
    ) -> list:
        """Fetch NL_RA race keys from PostgreSQL for time-series odds retrieval."""
        try:
            import psycopg

            conn = psycopg.connect(
                host=pg_config.get("host", "localhost"),
                port=int(pg_config.get("port", 5432)),
                dbname=pg_config.get("database", "keiba"),
                user=pg_config.get("user", "postgres"),
                password=pg_config.get("password", ""),
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
            finally:
                conn.close()
        except ImportError:
            try:
                import pg8000.dbapi as pgdb

                conn = pgdb.connect(
                    host=pg_config.get("host", "localhost"),
                    port=int(pg_config.get("port", 5432)),
                    database=pg_config.get("database", "keiba"),
                    user=pg_config.get("user", "postgres"),
                    password=pg_config.get("password", ""),
                )
                try:
                    cur = conn.cursor()
                    cur.execute(query, params)
                    return cur.fetchall()
                finally:
                    conn.close()
            except ImportError as exc:
                raise FetcherError(
                    "PostgreSQL driver not installed. Install psycopg[binary]."
                ) from exc

    def fetch_time_series_batch(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        jyo_codes: Optional[list[str]] = None,
        race_nums: Optional[list[int]] = None,
    ) -> Iterator[dict]:
        """Fetch time series data for multiple races in a date range.

        NOTE: This method uses the simplified 12-digit key format (YYYYMMDDJJRR)
        which may not work for batch retrieval. For reliable batch retrieval,
        use fetch_time_series_batch_from_db() which uses the full 16-digit key
        format with Kaiji and Nichiji from the database.

        Based on JVLinkToSQLite implementation pattern: JVRTOpen does NOT
        support date range queries, so this method loops through individual
        race keys (YYYYMMDDJJRR format).

        公式仕様:
        - 0B30〜0B36 は速報オッズで、提供単位はレース毎、保存期間は1週間
        - 0B41/0B42 は時系列オッズで、単複枠/馬連のみ、保存期間は1年間
        - ワイド以降の長期時系列は、開催週に0B30をTS_SOKUHO_O3〜TS_SOKUHO_O6へ蓄積する

        時系列オッズの蓄積について:
        - TS_SOKUHO_O1-O6テーブル（HassoTimeをPKに含む）を使用して蓄積可能
        - RealtimeUpdater.process_record(buff, timeseries=True) で保存
        - 蓄積系オッズ(O1-O6)は最終確定オッズのみ、時系列オッズは推移を記録

        Args:
            data_spec: Time series data spec code
                      - 0B20: 票数情報 (H1, H6)
                      - 0B30: 速報オッズ全賭式 (O1-O6, 1週間)
                      - 0B31: 速報オッズ単複枠 (O1, 1週間)
                      - 0B32: 速報オッズ馬連 (O2, 1週間)
                      - 0B33: 速報オッズワイド (O3, 1週間)
                      - 0B34: 速報オッズ馬単 (O4, 1週間)
                      - 0B35: 速報オッズ3連複 (O5, 1週間)
                      - 0B36: 速報オッズ3連単 (O6, 1週間)
                      - 0B41: 時系列オッズ単複枠 (O1, 1年間)
                      - 0B42: 時系列オッズ馬連 (O2, 1年間)
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
            - 保存期間外の時系列データは取得できない可能性があります

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
                                # No data for this race (not held or not
                                # available). JVRTOpen still opened the stream,
                                # so it must be closed before the next key or
                                # that key fails with -202.
                                no_data_keys += 1
                                logger.debug(
                                    "No data for key",
                                    key=key,
                                    track=JYO_CODES[jyo_code],
                                    race=race_num,
                                )
                                self.jvlink.jv_close()
                                continue

                            if ret != JV_RT_SUCCESS:
                                error_keys += 1
                                logger.warning(
                                    "JVRTOpen error",
                                    key=key,
                                    error_code=ret,
                                )
                                try:
                                    self.jvlink.jv_close()
                                except Exception:
                                    pass
                                continue

                            # Do not expose a partial key when a later JVRead
                            # fails and this loop continues with another key.
                            key_records = list(self._fetch_and_parse())
                            records_for_key = len(key_records)
                            success_keys += 1
                            total_records += records_for_key
                            yield from key_records

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
                            if "-114" in str(e):
                                logger.debug("Not subscribed for key", key=key, error=str(e))
                            else:
                                logger.warning("Error fetching key", key=key, error=str(e))
                            try:
                                self.jvlink.jv_close()
                            except Exception:
                                pass

                # Move to next date
                current_date += timedelta(days=1)

        finally:
            # Ensure stream is closed
            try:
                self.jvlink.jv_close()
            except Exception:
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

    @staticmethod
    def _postgres_table_exists(pg_config: dict, table_name: str) -> bool:
        """Return whether the query would resolve ``table_name`` to a table.

        ``to_regclass`` follows the session ``search_path``, so the probe and
        the unqualified query below always agree on which table is meant.
        """
        query = "SELECT to_regclass(%s) IS NOT NULL"
        try:
            import psycopg

            conn = psycopg.connect(
                host=pg_config.get("host", "localhost"),
                port=int(pg_config.get("port", 5432)),
                dbname=pg_config.get("database", "keiba"),
                user=pg_config.get("user", "postgres"),
                password=pg_config.get("password", ""),
            )
            try:
                with conn.cursor() as cur:
                    cur.execute(query, [table_name])
                    return bool(cur.fetchone()[0])
            finally:
                conn.close()
        except ImportError:
            try:
                import pg8000.dbapi as pgdb

                conn = pgdb.connect(
                    host=pg_config.get("host", "localhost"),
                    port=int(pg_config.get("port", 5432)),
                    database=pg_config.get("database", "keiba"),
                    user=pg_config.get("user", "postgres"),
                    password=pg_config.get("password", ""),
                )
                try:
                    cur = conn.cursor()
                    cur.execute(query, [table_name])
                    return bool(cur.fetchone()[0])
                finally:
                    conn.close()
            except ImportError as exc:
                raise FetcherError(
                    "PostgreSQL driver not installed. Install psycopg[binary]."
                ) from exc
            except Exception as exc:
                raise FetcherError(f"Could not check whether {table_name} exists: {exc}") from exc
        except FetcherError:
            raise
        except Exception as exc:
            raise FetcherError(f"Could not check whether {table_name} exists: {exc}") from exc

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._close_stream()
        return False
