"""Real-time monitoring for JLTSQL.

This module provides real-time monitoring of JV-Data updates.
"""

import signal
import threading
import time
from datetime import datetime
from typing import Optional

from src.jvlink.constants import JV_RT_SUCCESS, JV_READ_SUCCESS
from src.realtime.updater import RealtimeUpdater
from src.utils.data_source import DataSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RealtimeMonitor:
    """Real-time monitor for JV-Data updates.

    Monitors JV-Link real-time data stream and processes updates
    to the database.

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>> from src.realtime.monitor import RealtimeMonitor
        >>>
        >>> db = SQLiteDatabase({"path": "./keiba.db"})
        >>> with db:
        ...     monitor = RealtimeMonitor(database=db)
        ...     monitor.start()
    """

    def __init__(
        self,
        database,
        data_spec: str = "RACE",
        polling_interval: int = 60,
        sid: str = "REALTIME",
        initialization_key: Optional[str] = None,
        data_source: DataSource = DataSource.JRA,
    ):
        """Initialize real-time monitor.

        Args:
            database: Database handler instance
            data_spec: Data specification code (default: "RACE")
            polling_interval: Polling interval in seconds (default: 60)
            sid: Session ID for JV-Link API (default: "REALTIME")
            initialization_key: Optional NV-Link initialization key (software ID)
                used for NVInit when data_source is NAR.
            data_source: Data source (DataSource.JRA or DataSource.NAR, default: JRA)
        """
        self.database = database
        self.data_spec = data_spec
        self.polling_interval = polling_interval
        self.sid = sid
        self.initialization_key = initialization_key
        self.data_source = data_source

        # Select wrapper based on data source
        if data_source == DataSource.ALL:
            raise ValueError(
                "DataSource.ALL is not supported for realtime monitoring. "
                "Please run separate monitors for JRA and NAR (--source jra / --source nar)."
            )
        elif data_source == DataSource.NAR:
            from src.nvlink.wrapper import NVLinkWrapper
            self.jvlink = NVLinkWrapper(sid=sid, initialization_key=initialization_key)
        else:
            from src.jvlink.wrapper import JVLinkWrapper
            self.jvlink = JVLinkWrapper(sid=sid)

        self.updater = RealtimeUpdater(database, data_source=data_source)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Statistics
        self._stats = {
            "started_at": None,
            "last_update": None,
            "records_processed": 0,
            "records_inserted": 0,
            "records_updated": 0,
            "records_deleted": 0,
            "errors": 0,
        }

        logger.info(
            "RealtimeMonitor initialized",
            data_spec=data_spec,
            polling_interval=polling_interval,
            data_source=data_source.value,
        )

    def start(self, daemon: bool = False) -> None:
        """Start real-time monitoring.

        Args:
            daemon: Run in background daemon mode (default: False)

        Raises:
            RuntimeError: If monitor is already running
        """
        if self._running:
            raise RuntimeError("Monitor is already running")

        logger.info("Starting real-time monitor", daemon=daemon)

        # Initialize JV-Link
        self.jvlink.jv_init()

        # Open real-time stream
        ret_code = self.jvlink.jv_rt_open(self.data_spec)
        if ret_code != JV_RT_SUCCESS:
            logger.error(f"Failed to open real-time stream: {ret_code}")
            raise RuntimeError(f"JVRTOpen failed with code {ret_code}")

        self._running = True
        self._stats["started_at"] = datetime.now()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        if daemon:
            # Run in background thread
            self._thread = threading.Thread(target=self._polling_loop, daemon=True)
            self._thread.start()
            logger.info("Real-time monitor started in background")
        else:
            # Run in foreground
            self._polling_loop()

    def stop(self) -> None:
        """Stop real-time monitoring."""
        if not self._running:
            logger.warning("Monitor is not running")
            return

        logger.info("Stopping real-time monitor")

        self._running = False
        self._stop_event.set()

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        # Close real-time stream
        try:
            self.jvlink.jv_close()
        except Exception as e:
            logger.error(f"Error closing JV-Link stream: {e}")

        logger.info("Real-time monitor stopped", **self._stats)

    def get_status(self) -> dict:
        """Get monitor status and statistics.

        Returns:
            Dictionary with status and statistics
        """
        status = {
            "running": self._running,
            "data_spec": self.data_spec,
            "polling_interval": self.polling_interval,
            **self._stats,
        }

        if self._stats["started_at"]:
            uptime = datetime.now() - self._stats["started_at"]
            status["uptime_seconds"] = int(uptime.total_seconds())

        return status

    def _polling_loop(self) -> None:
        """Main polling loop for real-time data."""
        logger.info("Polling loop started")

        try:
            while self._running and not self._stop_event.is_set():
                try:
                    self._poll_once()
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}", exc_info=True)
                    self._stats["errors"] += 1

                # Wait for next polling interval
                if not self._stop_event.wait(timeout=self.polling_interval):
                    continue
                else:
                    break

        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt")
        finally:
            logger.info("Polling loop ended")

    def _poll_once(self) -> None:
        """Poll JV-Link once for new data."""
        logger.debug("Polling JV-Link for updates")

        records_in_poll = 0

        while True:
            # Read next record
            ret_code, buff, filename = self.jvlink.jv_read()

            if ret_code == 0:  # JV_READ_COMPLETE
                logger.debug(f"Poll complete: processed {records_in_poll} records")
                break

            elif ret_code == -1:  # JV_READ_FILE_SWITCH
                logger.debug("File switch")
                continue

            elif ret_code > 0:  # JV_READ_SUCCESS (has data)
                try:
                    # Process record
                    result = self.updater.process_record(buff)

                    if result:
                        self._stats["records_processed"] += 1
                        records_in_poll += 1

                        # Update statistics based on operation
                        if result.get("operation") == "insert":
                            self._stats["records_inserted"] += 1
                        elif result.get("operation") == "update":
                            self._stats["records_updated"] += 1
                        elif result.get("operation") == "delete":
                            self._stats["records_deleted"] += 1

                        self._stats["last_update"] = datetime.now()

                except Exception as e:
                    logger.error(f"Error processing record: {e}", exc_info=True)
                    self._stats["errors"] += 1

            else:  # Error
                logger.error(f"JVRead error: {ret_code}")
                self._stats["errors"] += 1
                break

        if records_in_poll > 0:
            logger.info(
                f"Processed {records_in_poll} records in this poll",
                total_processed=self._stats["records_processed"],
            )

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down gracefully")
        self.stop()

    def _get_track_name(self, track_code: str) -> str:
        """Get track name based on data source.

        Args:
            track_code: Track code (e.g., "05", "30")

        Returns:
            Track name in Japanese
        """
        if self.data_source == DataSource.NAR:
            from src.nvlink.constants import get_nar_track_name
            return get_nar_track_name(track_code)
        else:
            from src.jvlink.constants import get_track_name
            return get_track_name(track_code)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._running:
            self.stop()
