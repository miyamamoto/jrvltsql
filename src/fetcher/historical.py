"""Historical data fetcher for JLTSQL.

This module fetches historical JV-Data from JV-Link.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterator, Optional

from src.fetcher.base import BaseFetcher, FetcherError
from src.jvlink.constants import (
    JVOPEN_OPTION_SETUP,
    JVOPEN_OPTION_SETUP_SPLIT,
    uses_range_fromtime,
    validate_jvopen_combination,
)
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


def validate_date_range(from_date: str, to_date: str) -> None:
    """Reject malformed, non-calendar, or inverted date ranges.

    JVOpen・キャッシュ・スキーマ作成のいずれに触れるよりも前に呼ぶこと。
    fromtime はここで検証済みの日付からしか組み立てない。
    """
    for label, value in (("from_date", from_date), ("to_date", to_date)):
        if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
            raise ValueError(
                f"{label} must be an 8-digit YYYYMMDD string, got {value!r}"
            )
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError:
            raise ValueError(
                f"{label} must be a real calendar date in YYYYMMDD format, "
                f"got {value!r}"
            ) from None
    if from_date > to_date:
        raise ValueError(
            f"from_date must not be after to_date: {from_date} > {to_date}"
        )


def _jvopen_fromtime(from_date: str, option: int) -> str:
    """Build the start point of one JVOpen request.

    公式仕様（4.9.0.1 p.17-20）の対象条件は開始時刻より大きいデータ。
    要求された from_date を包含させるため、セットアップ (option 3/4) では
    排他的開始点を前日23:59:59に符号化する。option 1 の差分カーソル
    （``{from_date}000000``）と option 2 の今週データ契約は変更しない。
    """
    if option not in (JVOPEN_OPTION_SETUP, JVOPEN_OPTION_SETUP_SPLIT):
        return f"{from_date}000000"
    return (
        datetime.strptime(from_date, "%Y%m%d") - timedelta(seconds=1)
    ).strftime("%Y%m%d%H%M%S")


def _jvopen_fromtimes(
    data_spec: str,
    from_date: str,
    to_date: str,
    option: int,
) -> list[str]:
    """Split one request into the fromtime of each JVOpen call.

    なぜ刻むかは RANGE_FROMTIME_DATA_SPECS のコメントを見ること。刻まない
    dataspec と option 2 は、従来どおり開始のみの 1 回になる。

    境界は隣り合う chunk で同じ値を共有する。JVOpen の対象は「開始時刻より
    大きく、終了時刻まで」なので、その値のファイルは前の chunk に入り次の
    chunk からは外れる。穴も重複も出ない。

    Returns:
        JVOpen に渡す fromtime のリスト。要素は開始のみ（14 桁）か
        ``開始-終了``（14 桁 + "-" + 14 桁）。
    """
    start = _jvopen_fromtime(from_date, option)
    if not uses_range_fromtime(data_spec, option):
        return [start]

    last_day = datetime.strptime(to_date, "%Y%m%d")
    fromtimes = []
    for year in range(int(from_date[:4]), last_day.year + 1):
        year_end = datetime(year, 12, 31)
        end = min(year_end, last_day)
        fromtimes.append(f"{start}-{end.strftime('%Y%m%d')}235959")
        # 次の chunk はこの chunk の終了時刻より大きいところから始まる。
        start = f"{year}1231235959"
    return fromtimes


@dataclass
class _NlCacheWriteState:
    """NL キャッシュへの write-through 中に chunk をまたいで持ち回す状態.

    manager が None ならキャッシュは使わない。range_complete は「この要求の
    範囲を取り切ったと言えるか」で、倒れていると fetch は完了マークを付けない。
    """

    # CacheManager 相当のオブジェクト（None ならキャッシュ無し）。型を固定しないのは
    # 呼び出し側が差し替え可能な形で渡すため。
    manager: Any
    checkpoints: dict[str, Optional[int]] = field(default_factory=dict)
    range_complete: bool = True


class HistoricalFetcher(BaseFetcher):
    """Fetcher for historical JV-Data.

    Fetches accumulated (蓄積) data from JV-Link for a specified date range
    and data specification. A dataspec that accepts a range fromtime
    (RANGE_FROMTIME_DATA_SPECS) is split into one JVOpen per calendar year,
    because the cost of a single JVRead grows with the number of files one
    JVOpen lists. Every other dataspec, and option 2, opens once from the
    start point only. For setup requests (option 3/4) the requested inclusive
    from_date is encoded as the exclusive start point (previous day 23:59:59,
    per the official strictly-greater rule); options 1/2 keep the
    ``{from_date}000000`` cursor. In every mode records are also filtered
    client-side based on the end date.

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

    def __init__(self, sid: str = "UNKNOWN", show_progress: bool = True):
        super().__init__(sid, show_progress=show_progress)
        self.cache_manager = None
        self._jvd_self_repair_attempts = 0
        self._jvd_replay_records_remaining = 0
        # 統計は fetch 全体で 1 本だが、リプレイ長は「いまの open で出したぶん」。
        # 暦年チャンクでは 1 回の fetch が JVOpen を何度も呼ぶので基準点を持つ。
        self._open_records_baseline = 0
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
        # 数えるのは「いまの open で出したぶん」。_records_fetched は fetch 全体の
        # 累計なので、この open が始まった時点の基準点を引く。
        self._jvd_replay_records_remaining = (
            self._records_fetched - self._open_records_baseline
        )
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

    def _fetch_one_open(
        self,
        *,
        data_spec: str,
        fromtime: str,
        option: int,
        to_date: str,
        chunk_label: str,
        cache: "_NlCacheWriteState",
    ) -> Iterator[dict]:
        """Run one JVOpen -> read -> JVClose cycle and yield its records.

        暦年チャンクの 1 個ぶん。統計・キャッシュ確定・進捗表示の寿命は呼び出し側
        (fetch) が持ち、ここは 1 回の open の中だけを見る。

        空の窓 (result -1) は刻んでいれば普通に起こるので、その chunk を終えて
        次へ進む。ただし「窓の中身が無い」ことを確かめられていない以上、この
        範囲を完全としてキャッシュに刻ませない (cache.range_complete を倒す)。
        """
        # 前の chunk の読み出し状態は持ち越さない。リプレイ長は「この open で
        # 出したぶん」なので、累計から基準点を引いて数える。self-repair の
        # リトライ上限は fetch 全体で 1 本のままにする (chunk 数ぶん増やさない)。
        self._jvd_replay_records_remaining = 0
        self._open_records_baseline = self._records_fetched
        self._files_processed = 0
        self._jv_open_context = (data_spec, fromtime, option)
        self._jv_open_last_file_timestamp = None
        download_task_id = None
        fetch_task_id = None

        logger.info(
            "Opening data stream",
            data_spec=data_spec,
            fromtime=fromtime,
            option=option,
            chunk=chunk_label,
            note=(
                "option=1: 通常データ（差分）; "
                "option=2: 今週データ; "
                "option=3/4: セットアップ"
                "（範囲形式が使える dataspec は暦年で刻む。to_date は client filter も兼ねる）"
            ),
        )

        # JVOpen 自体を try の中で呼ぶ。wrapper は -202 のように「開いたが
        # 例外で返る」経路で JVClose を要求するので、close の義務はこの
        # finally 1 箇所に集約する。
        primary_error = None
        try:
            result, read_count, download_count, last_file_timestamp = (
                self.jvlink.jv_open(data_spec, fromtime, option)
            )
            self._jv_open_last_file_timestamp = last_file_timestamp

            logger.info(
                "Data stream opened",
                result_code=result,
                read_count=read_count,
                download_count=download_count,
                last_file_timestamp=last_file_timestamp,
                chunk=chunk_label,
            )

            if result == -2:
                raise FetcherError("JVOpen setup dialog was cancelled")
            # 「データなし」判定より先にエラーコードを弾く。-113（読み出し終了
            # 時刻のパラメータ不正）のような失敗は read_count も download_count も
            # 0 で返るので、順序を逆にすると空の窓と見分けがつかなくなる。
            if result not in (0, -1):
                raise FetcherError(f"JVOpen returned unexpected result code: {result}")
            if result == -1 or (read_count == 0 and download_count == 0):
                # 窓に該当データが無いだけ。刻んでいる以上ふつうに起こるので
                # fetch は続ける。ただしこの範囲を「完全に取り切った」とは
                # 言えないので、NL キャッシュの完了マークは付けさせない。
                # (付けると has_nl_range が 0 件をこの範囲の答えとして返し続ける)
                cache.range_complete = False
                logger.info(
                    "No data available for this window",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    chunk=chunk_label,
                )
                if self.progress_display:
                    self.progress_display.print_info(
                        f"{data_spec}: サーバーにデータなし ({fromtime})"
                    )
                return

            # Wait for download to complete if needed
            if download_count > 0:
                logger.info(
                    "Download in progress, waiting for completion",
                    download_count=download_count,
                )
                if self.progress_display:
                    download_task_id = self.progress_display.add_download_task(
                        f"{data_spec} ダウンロード ({chunk_label})",
                        total=download_count,
                    )
                self._wait_for_download(download_task_id, download_count=download_count)

            # Set total files after JVOpen reports the stream size.
            self._total_files = read_count

            # Create fetch progress task
            if self.progress_display:
                fetch_task_id = self.progress_display.add_task(
                    f"{data_spec} レコード取得 ({chunk_label})",
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
            ):
                raw = data.get("_raw") if cache.manager else None
                if raw is not None and raw is not last_cached_raw:
                    last_cached_raw = raw
                    rec_date = _extract_record_date(data)
                    if rec_date:
                        if rec_date not in cache.checkpoints:
                            cache.checkpoints[rec_date] = cache.manager.checkpoint_nl(
                                data_spec,
                                rec_date,
                            )
                        cache.manager.write_nl_record(data_spec, rec_date, raw)
                    else:
                        # The record is yielded/imported, but cannot be replayed
                        # from this date-keyed cache. Keep the range incomplete;
                        # the finally block rolls back any partial appends.
                        cache.range_complete = False
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
        except BaseException as exc:
            # JVClose below is still mandatory, but a secondary close failure
            # must not replace the provider/read error that started unwinding.
            primary_error = exc
            raise
        finally:
            self._jv_open_context = None
            self._jv_open_last_file_timestamp = None
            self._fetch_task_id = None
            # 次の chunk が JVOpen できるよう、この open は必ず閉じる。
            try:
                self.jvlink.jv_close()
                logger.info("Data stream closed", chunk=chunk_label)
            except Exception as close_error:
                if primary_error is None:
                    raise FetcherError(
                        f"JVClose failed for chunk {chunk_label}: {close_error}"
                    ) from close_error
                logger.error(
                    "JVClose failed while preserving an earlier stream error",
                    chunk=chunk_label,
                    close_error=str(close_error),
                    primary_error=repr(primary_error),
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
            data_spec: Data specification code (e.g., "RACE", "DIFN")
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
            ValueError: If data_spec or option violates the JVOpen contract
            FetcherError: If fetching fails

        Note:
            Records are filtered client-side to include only those with
            dates up to and including to_date. Records without date fields
            (Year/MonthDay) are always included.

            For option 3/4 the requested inclusive from_date is encoded as
            the exclusive start point ``(from_date - 1 day)235959``. For a
            dataspec that accepts a range fromtime the request is split into
            one JVOpen per calendar year and ``to_date`` also bounds the last
            chunk; for every other dataspec it is a client-side filter only.

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
        # Validate every four-character component before JV-Link/cache state.
        validate_jvopen_combination(data_spec, option)
        # Reject malformed/inverted dates before JV-Link or cache mutation;
        # fromtime below is built from these validated values.
        validate_date_range(from_date, to_date)

        # Fetcher instances are reused across data specs and setup chunks.
        # Reset before JVOpen so no-data/error early exits cannot expose
        # statistics left over from the preceding invocation.
        self.reset_statistics()

        # Create progress display if enabled
        if self.show_progress:
            self.progress_display = JVLinkProgressDisplay()
            self.progress_display.start()

        # option=2 uses fromtime only for continuity within current race-cycle
        # data; it cannot prove an arbitrary requested historical range
        # complete. Bypass both existing NL cache markers and write-through
        # caching for that mode.
        active_cache_manager = self.cache_manager if option != 2 else None
        cache_write_committed = active_cache_manager is None
        cache = _NlCacheWriteState(manager=active_cache_manager)

        # 1 回の JVOpen に並ぶ対象ファイル数が JVRead 1 回の費用を決めるので、
        # 範囲形式を使える dataspec は暦年で刻む（_jvopen_fromtimes）。
        # 刻めない dataspec と option 2 は開始のみ 1 回になる。
        fromtimes = _jvopen_fromtimes(data_spec, from_date, to_date, option)

        try:
            # Info for setup mode (option 3 or 4) - ログのみ、画面表示はしない
            if option in (3, 4):
                logger.info(
                    "セットアップモード",
                    option=option,
                    chunks=len(fromtimes),
                )

            if self.progress_display:
                # スペックヘッダーを表示（日付範囲付き）
                self.progress_display.print_spec_header(data_spec, from_date, to_date)

            # The session was established in BaseFetcher.__init__, so this
            # method starts at JVOpen and never re-issues JVInit. Re-issuing it
            # would put the option=3/4 source dialog in front of the operator
            # again for every dataspec of a multi-spec setup run.
            # リトライ上限は fetch 全体で 1 本。chunk 数ぶんは増やさない。
            self._jvd_self_repair_attempts = 0

            for chunk_index, fromtime in enumerate(fromtimes, start=1):
                yield from self._fetch_one_open(
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option,
                    to_date=to_date,
                    chunk_label=f"{chunk_index}/{len(fromtimes)}",
                    cache=cache,
                )

            # Mark cached dates as complete
            if active_cache_manager and cache.range_complete:
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
                for rec_date, checkpoint in cache.checkpoints.items():
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
            # JVClose の義務は _fetch_one_open の finally が持つ（JVOpen と
            # 同じ try に入っている）。ここで二重に閉じない。JVInit はここでも
            # 張り直さない。セッションは JVClose より長く生きる。

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

        Raises:
            ValueError: If data_spec or option violates the JVOpen contract

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

        Raises:
            ValueError: If data_spec or option violates the JVOpen contract
        """
        # A cache hit bypasses fetch(), so validate before reading cache state.
        # 日付検証も同様: 逆転した範囲は has_nl_range が空の全日付走査で
        # True を返し「静かな空成功」になるため、ここで拒否する。
        validate_jvopen_combination(data_spec, option)
        validate_date_range(from_date, to_date)

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
                        self._raise_failed_record(raw, f"cache:{data_spec}", error=None)

                    records = parsed if isinstance(parsed, list) else [parsed]
                    for record in records:
                        self._records_parsed += 1
                        record["_raw"] = raw
                        yield record
                except FetcherError:
                    raise
                except Exception as error:
                    self._raise_failed_record(raw, f"cache:{data_spec}", error=error)
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
        if download_count < 0:
            raise FetcherError("download_count must not be negative")
        if download_count == 0:
            return

        last_progress_time = start_time  # Track when downloaded-file count last changed.
        stall_timeout = 300.0  # 5 minutes before stall abort

        while True:
            # Check if timeout exceeded
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise FetcherError(f"Download timeout after {elapsed:.1f} seconds")

            try:
                # Get download status
                # JVStatus returns the number of downloaded files, not a
                # percentage. Download is complete only when the count equals
                # the JVOpen download_count value retained until JVClose.
                status = self.jvlink.jv_status()

                if status == download_count:
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

                if status > download_count:
                    raise FetcherError(
                        "JVStatus downloaded-file count exceeded JVOpen "
                        f"download_count: {status} > {download_count}"
                    )

                if status < 0:
                    raise FetcherError(
                        f"Download failed with JVStatus code: {status}"
                    )

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

                # Wait before next status check
                time.sleep(interval)

            except Exception as e:
                if isinstance(e, FetcherError):
                    raise

                raise FetcherError(f"Failed to check download status: {e}")
