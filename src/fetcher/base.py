"""Base data fetcher for JLTSQL.

This module provides the base class for fetching JV-Data from JV-Link.
"""

import gc
import hashlib
import ntpath
import os
import posixpath
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Iterator, Optional

from src.jvlink.constants import JV_READ_NO_MORE_DATA, JV_READ_SUCCESS
from src.jvlink.wrapper import JVLinkWrapper
from src.parser.factory import ParserFactory
from src.utils.logger import get_logger
from src.utils.progress import JVLinkProgressDisplay

logger = get_logger(__name__)

JV_READ_DOWNLOAD_TIMEOUT_SECONDS = 300.0
JV_READ_DOWNLOAD_POLL_INTERVAL_SECONDS = 0.2


class FetcherError(Exception):
    """Data fetcher error."""

    pass


class BaseFetcher(ABC):
    """Abstract base class for data fetchers.

    This class provides common functionality for fetching and parsing
    JV-Data records from JV-Link.

    Note:
        JV-Link registration is configured in the JRA-VAN DataLab
        application before this fetcher is started.

    Attributes:
        jvlink: JV-Link wrapper instance
        parser_factory: Parser factory instance
    """

    FAILED_RECORD_DIR_ENV = "JLTSQL_FAILED_RECORD_DIR"

    def __init__(
        self,
        sid: str = "UNKNOWN",
        show_progress: bool = True,
    ):
        """Initialize base fetcher.

        Args:
            sid: Session ID for JV-Link API (default: "UNKNOWN")
            show_progress: Show stylish progress display (default: True)
        """
        # Prefer the configured subprocess bridge over in-process COM.
        # Runtime architecture support is established only by the release E2E.
        from src.jvlink.bridge import find_bridge_executable
        bridge_exe = find_bridge_executable()
        if bridge_exe is not None:
            from src.jvlink.bridge import JVLinkBridge
            logger.info("Using JVLinkBridge (C#) for JRA", bridge_path=str(bridge_exe))
            self.jvlink = JVLinkBridge(sid, bridge_path=bridge_exe)
        else:
            self.jvlink = JVLinkWrapper(sid)

        # JVInit is application initialization in the official JV-Link spec,
        # not per-JVOpen setup. Establishing the session here means fetch()
        # starts at JVOpen, and a process running many JVOpen/JVClose pairs
        # still holds a single JV-Link session.
        #
        # That single session is what makes a multi-dataspec setup usable:
        # under option=3/4 JV-Link shows its source-selection dialog once per
        # session, so a run covering several dataspecs asks the operator to
        # answer it once instead of once per dataspec.
        #
        # Both transports raise on a failed JVInit, so there is no result code
        # left to inspect here.
        self.jvlink.jv_init()

        self.parser_factory = ParserFactory()
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0
        self._recoverable_read_errors = 0
        self._repaired_read_errors = 0
        self._files_processed = 0
        self._total_files = 0
        self.show_progress = show_progress
        self.progress_display: Optional[JVLinkProgressDisplay] = None
        self._start_time = None

        logger.info(f"{self.__class__.__name__} initialized", sid=sid)

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

    def _fetch_and_parse(
        self,
        task_id: Optional[int] = None,
        to_date: Optional[str] = None,
        recover_file_error: Optional[Callable[[int, str], None]] = None,
        consume_replayed_record: Optional[Callable[[], bool]] = None,
    ) -> Iterator[dict]:
        """Internal method to fetch and parse records.

        Args:
            task_id: Progress task ID (optional)
            to_date: End date in YYYYMMDD format (optional, for filtering records)
            recover_file_error: Optional historical-stream recovery callback for
                corrupt downloaded files (-402/-403).
            consume_replayed_record: Optional callback that returns True when a
                record replayed after recovery must be skipped.

        Yields:
            Dictionary of parsed record data
        """
        if recover_file_error is None:
            recover_file_error = getattr(self, "_recover_file_error", None)

        self._start_time = time.time()
        last_update_time = self._start_time
        update_interval = 2.0  # Update progress every 2 seconds
        last_gc_time = self._start_time  # Periodic GC to free COM buffers
        download_wait_started: Optional[float] = None

        while True:
            try:
                # Read next record
                ret_code, buff, filename = self.jvlink.jv_read()

                if ret_code == -3:
                    now = time.monotonic()
                    if download_wait_started is None:
                        download_wait_started = now
                    elapsed = now - download_wait_started
                    if elapsed >= JV_READ_DOWNLOAD_TIMEOUT_SECONDS:
                        raise FetcherError(
                            "JVRead file-downloading wait timeout after "
                            f"{elapsed:.1f} seconds"
                        )
                    logger.debug(
                        "JVRead waiting for file download",
                        filename=filename,
                        elapsed_seconds=elapsed,
                    )
                    time.sleep(JV_READ_DOWNLOAD_POLL_INTERVAL_SECONDS)
                    continue

                download_wait_started = None

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
                    # Replayed records still hold COM buffers. Run the normal
                    # periodic collection before a replay skip so a long setup
                    # import cannot bypass the E_UNEXPECTED mitigation.
                    current_time = time.time()
                    if (current_time - last_gc_time) >= 10.0:
                        gc.collect()
                        last_gc_time = current_time

                    if consume_replayed_record is not None and consume_replayed_record():
                        if (current_time - last_update_time) >= update_interval:
                            logger.info(
                                "Replaying records after historical recovery",
                                records_previously_emitted=self._records_fetched,
                                files_processed=self._files_processed,
                                total_files=self._total_files,
                            )
                            last_update_time = current_time
                        continue
                    self._records_fetched += 1

                    # Parse record. Any rejection is fatal: continuing would
                    # let callers consume an incomplete provider stream and
                    # could emit an unbounded failure log on a corrupt feed.
                    try:
                        data = self.parser_factory.parse(buff)
                    except Exception as error:
                        self._raise_failed_record(buff, filename, error=error)
                    if not data:
                        self._raise_failed_record(buff, filename, error=None)

                    # Full-struct parsers (H1, H6) return List[Dict]
                    records_list = data if isinstance(data, list) else [data]

                    for record_item in records_list:
                        # Filter by to_date if specified
                        if to_date and not self._is_within_date_range(record_item, to_date):
                            logger.debug(
                                "Skipping record outside date range",
                                record_num=self._records_fetched,
                                to_date=to_date,
                            )
                            continue

                        self._records_parsed += 1
                        # Include raw buffer for callers that need it (e.g., RealtimeUpdater)
                        record_item["_raw"] = buff
                        yield record_item

                    # Periodic GC to free COM buffer references (every 10s).
                    # kmy-keiba frees COM buffers with Array.Resize(ref buff, 0) after each read.
                    # In Python, COM BSTR data may accumulate and cause E_UNEXPECTED.
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

                elif ret_code in (-402, -403):
                    # Only the two official corrupt-downloaded-file statuses
                    # enter targeted file recovery. Call-order errors
                    # (-201/-202/-203), download failure (-502), and missing
                    # file (-503) cannot be repaired by repeating JVRead or by
                    # deleting the returned path.
                    logger.warning(
                        "JVRead returned a corrupt downloaded file",
                        ret_code=ret_code,
                        filename=filename,
                    )
                    if recover_file_error is not None:
                        recover_file_error(ret_code, filename or "")
                        self._repaired_read_errors += 1
                    else:
                        self._recoverable_read_errors += 1
                        raise FetcherError(
                            "JVRead corrupt-file recovery is unavailable for "
                            f"error code {ret_code} ({filename or 'unknown file'})"
                        )
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
                raise FetcherError(f"Failed to fetch data: {e}") from e

    def _delete_corrupt_file_best_effort(self, error_code: int, filename: str) -> None:
        """Remove a corrupt JV-Link file for the next run without masking failure."""
        if not filename:
            logger.warning(
                "Cannot delete corrupt JV-Link file without a filename",
                error_code=error_code,
            )
            return
        try:
            result = self.jvlink.jv_file_delete(filename)
        except Exception as exc:
            logger.warning(
                "Best-effort JVFiledelete failed",
                error_code=error_code,
                filename=filename,
                error=str(exc),
            )
            return
        if result not in (None, 0):
            logger.warning(
                "Best-effort JVFiledelete returned an error",
                error_code=error_code,
                filename=filename,
                result=result,
            )

    @classmethod
    def _failed_record_directory(cls) -> Path:
        configured = os.environ.get(cls.FAILED_RECORD_DIR_ENV)
        if configured:
            return Path(configured).expanduser()
        if os.name == "nt":
            state_root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        else:
            state_root = Path(
                os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")
            )
        return state_root / "jltsql" / "failed-records"

    @staticmethod
    def _safe_jvd_filename(filename: object) -> str:
        """Keep only a bounded provider filename, never a credential-bearing path."""

        value = str(filename or "unknown")
        value = posixpath.basename(ntpath.basename(value))
        return value[:255] or "unknown"

    def _write_failed_record_artifact(self, record: bytes) -> tuple[str, str]:
        """Atomically preserve one complete record under its SHA-256 identity."""

        digest = hashlib.sha256(record).hexdigest()
        artifact_dir = self._failed_record_directory()
        artifact_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = artifact_dir / f"{digest}.jvd"
        if target.exists():
            if target.read_bytes() != record:
                raise FetcherError("Existing failed-record artifact does not match its SHA-256")
            return f"sha256:{digest}", digest

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.", suffix=".tmp", dir=artifact_dir
        )
        temporary = Path(temporary_name)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as artifact:
                artifact.write(record)
                artifact.flush()
                os.fsync(artifact.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return f"sha256:{digest}", digest

    def _log_failed_record(self, buff, filename, *, error) -> str:
        """Persist the complete rejected record and emit only bounded metadata."""

        record = bytes(buff) if buff else b""
        artifact_id, digest = self._write_failed_record_artifact(record)
        record_spec = record[:2].decode("ascii", errors="replace")
        if not record_spec.isprintable():
            record_spec = record[:2].hex()
        logger.error(
            "Failed to parse record",
            jvd_file=self._safe_jvd_filename(filename),
            record_num=self._records_fetched,
            record_spec=record_spec,
            error_type=type(error).__name__[:128] if error is not None else None,
            record_len=len(record),
            record_sha256=digest,
            artifact_id=artifact_id,
        )
        return artifact_id

    def _raise_failed_record(self, buff, filename, *, error) -> None:
        """Record one bounded diagnostic and stop the provider stream."""

        self._records_failed += 1
        try:
            artifact_id = self._log_failed_record(buff, filename, error=error)
        except Exception as artifact_error:
            logger.error(
                "Failed to preserve rejected record artifact",
                jvd_file=self._safe_jvd_filename(filename),
                record_num=self._records_fetched,
                record_len=len(bytes(buff)) if buff else 0,
                error_type=type(artifact_error).__name__[:128],
            )
            raise FetcherError(
                "Parser rejected a record and artifact preservation failed"
            ) from artifact_error
        raise FetcherError(
            f"Parser rejected record {self._records_fetched}; artifact {artifact_id}"
        ) from error

    def get_statistics(self) -> dict:
        """Get fetching statistics.

        Returns:
            Dictionary with fetch statistics
        """
        return {
            "records_fetched": self._records_fetched,
            "records_parsed": self._records_parsed,
            "records_failed": self._records_failed,
            "recoverable_read_errors": self._recoverable_read_errors,
            "repaired_read_errors": self._repaired_read_errors,
        }

    def reset_statistics(self):
        """Reset fetching statistics."""
        self._records_fetched = 0
        self._records_parsed = 0
        self._records_failed = 0
        self._recoverable_read_errors = 0
        self._repaired_read_errors = 0

    def _is_within_date_range(self, data: dict, to_date: str) -> bool:
        """Check if a record's date is within the specified range (up to to_date).

        Args:
            data: Parsed record data dictionary
            to_date: End date in YYYYMMDD format

        Returns:
            True if record date <= to_date, False otherwise
        """
        # Most JV-Data records have Year and MonthDay fields. HC/WC training
        # records instead carry their event date in ChokyoDate.
        year = data.get("Year")
        month_day = data.get("MonthDay")

        if year and month_day:
            record_date = f"{year}{month_day}"
        else:
            chokyo_date = data.get("ChokyoDate")
            record_date = str(chokyo_date) if chokyo_date else None

        if not record_date:
            # If date fields are not present, include the record
            # (don't filter records that don't have date information)
            return True

        try:
            # Compare as strings (YYYYMMDD format allows string comparison)
            return record_date <= to_date
        except Exception as e:
            logger.warning(
                "Failed to extract date from record",
                year=year,
                month_day=month_day,
                chokyo_date=data.get("ChokyoDate"),
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
