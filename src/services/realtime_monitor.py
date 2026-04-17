"""Realtime data monitoring service for JLTSQL.

This module provides a background service that continuously monitors
JV-Link realtime data streams and imports updates into the database.
"""

from typing import Dict, List, Optional, Set
import threading
import time
from datetime import datetime

from src.fetcher.realtime import RealtimeFetcher
from src.jvlink.wrapper import JVLinkError
from src.realtime.updater import RealtimeUpdater
from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MonitorStatus:
    """Monitor status tracking."""

    def __init__(self):
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.is_running: bool = False
        self.records_imported: int = 0
        self.records_failed: int = 0
        self.errors: List[Dict[str, str]] = []
        self.monitored_specs: Set[str] = set()

    def to_dict(self) -> Dict:
        """Convert status to dictionary."""
        return {
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "uptime_seconds": (
                (datetime.now() - self.started_at).total_seconds()
                if self.started_at and self.is_running
                else 0
            ),
            "records_imported": self.records_imported,
            "records_failed": self.records_failed,
            "error_count": len(self.errors),
            "monitored_specs": sorted(self.monitored_specs),
        }


class RealtimeMonitor:
    """Realtime data monitoring service.

    This service continuously monitors JV-Link realtime data streams
    and automatically imports new data into the database as it arrives.

    JV-Link is a single-connection COM object — only one JVRTOpen call
    can be active at a time. This monitor uses a single thread that
    round-robins through all specs sequentially (open → drain → close → next).

    Examples:
        >>> from src.database.sqlite_handler import SQLiteDatabase
        >>>
        >>> db_config = {"path": "data/keiba.db"}
        >>> database = SQLiteDatabase(db_config)
        >>>
        >>> monitor = RealtimeMonitor(
        ...     database=database,
        ...     data_specs=["0B12", "0B15", "0B30"],
        ...     sid="JLTSQL"
        ... )
        >>>
        >>> monitor.start()
        >>> status = monitor.get_status()
        >>> print(f"Imported: {status['records_imported']}")
        >>> monitor.stop()
    """

    def __init__(
        self,
        database: BaseDatabase,
        data_specs: Optional[List[str]] = None,
        sid: str = "JLTSQL",
        batch_size: int = 100,
        auto_create_tables: bool = True,
    ):
        """Initialize realtime monitor.

        Args:
            database: Database instance for storing data
            data_specs: List of data specs to monitor (default: ["0B12"])
            sid: JV-Link session ID
            batch_size: Batch size for database imports
            auto_create_tables: Automatically create missing tables
        """
        self.database = database
        self.data_specs = list(data_specs or ["0B12"])
        self.sid = sid
        self.batch_size = batch_size
        self.auto_create_tables = auto_create_tables

        self.status = MonitorStatus()
        self.status.monitored_specs = set(self.data_specs)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start monitoring service.

        Returns:
            True if started successfully, False otherwise
        """
        if self.status.is_running:
            logger.warning("Monitor is already running")
            return False

        try:
            if not self.database._connection:
                self.database.connect()

            if self.auto_create_tables:
                self._ensure_tables()

            self._stop_event.clear()

            # Single thread round-robins through all specs sequentially.
            # JV-Link allows only one JVRTOpen connection at a time.
            self._thread = threading.Thread(
                target=self._monitor_sequential,
                daemon=True,
                name="Monitor-Sequential",
            )
            self._thread.start()

            self.status.is_running = True
            self.status.started_at = datetime.now()
            self.status.stopped_at = None

            logger.info(
                "Realtime monitor started",
                data_specs=self.data_specs,
            )
            return True

        except Exception as e:
            logger.error("Failed to start monitor", error=str(e))
            self._add_error("start", str(e))
            return False

    def stop(self, timeout: float = 10.0) -> bool:
        """Stop monitoring service.

        Args:
            timeout: Maximum time to wait for thread to stop (seconds)

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.status.is_running:
            logger.warning("Monitor is not running")
            return False

        try:
            logger.info("Stopping realtime monitor...")
            self._stop_event.set()

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                if self._thread.is_alive():
                    logger.warning("Monitor thread did not stop gracefully")

            self.status.is_running = False
            self.status.stopped_at = datetime.now()

            logger.info(
                "Realtime monitor stopped",
                records_imported=self.status.records_imported,
                records_failed=self.status.records_failed,
            )
            return True

        except Exception as e:
            logger.error("Failed to stop monitor", error=str(e))
            self._add_error("stop", str(e))
            return False

    def get_status(self) -> Dict:
        """Get current monitor status."""
        with self._lock:
            return self.status.to_dict()

    def add_data_spec(self, data_spec: str) -> bool:
        """Add a new data spec to monitor at runtime.

        The sequential loop picks it up on the next cycle.

        Args:
            data_spec: Data specification code to add

        Returns:
            True if added, False if already present or not running
        """
        if not self.status.is_running:
            logger.warning("Cannot add data spec - monitor is not running")
            return False

        if data_spec in self.status.monitored_specs:
            logger.warning(f"Data spec {data_spec} is already being monitored")
            return False

        with self._lock:
            self.data_specs.append(data_spec)
            self.status.monitored_specs.add(data_spec)

        logger.info(f"Added {data_spec} to monitored specs")
        return True

    def _monitor_sequential(self):
        """Single-thread sequential round-robin over all data specs.

        For each spec: JVRTOpen → drain raw records via JVRead → JVClose → next.
        Raw buffers go to RealtimeUpdater which routes to RT_ tables (not NL_).

        A single RealtimeFetcher (and its COM object) is reused throughout to
        avoid win32com threading issues from creating multiple COM objects in a
        background thread.
        """
        fetcher = RealtimeFetcher(sid=self.sid)
        jvlink = fetcher.jvlink
        updater = RealtimeUpdater(database=self.database)

        # Initialize JV-Link once for the session
        try:
            jvlink.jv_init()
        except Exception as e:
            logger.error(f"JV-Link init failed: {e}")
            return

        logger.info("Sequential RT monitoring loop started", specs=self.data_specs)

        while not self._stop_event.is_set():
            any_data = False
            key = datetime.now().strftime("%Y%m%d")

            for data_spec in list(self.data_specs):
                if self._stop_event.is_set():
                    break

                try:
                    ret, _read_count = jvlink.jv_rt_open(data_spec, key)

                    # ret == -1 means no data for this spec/date — not an error
                    if ret == -1:
                        logger.debug(f"No RT data for {data_spec} on {key}")
                        jvlink.jv_close()
                        continue

                    # Drain all available records
                    spec_records = 0
                    while not self._stop_event.is_set():
                        ret_code, buff, _filename = jvlink.jv_read()
                        if ret_code == 0:  # complete
                            break
                        if ret_code == -1:  # file switch
                            continue
                        if ret_code > 0 and buff:
                            try:
                                result = updater.process_record(buff)
                                with self._lock:
                                    if result:
                                        self.status.records_imported += 1
                                        spec_records += 1
                                    else:
                                        self.status.records_failed += 1
                            except Exception as e:
                                logger.error(f"process_record error ({data_spec}): {e}")
                                with self._lock:
                                    self.status.records_failed += 1
                        else:
                            logger.debug(f"JVRead {ret_code} for {data_spec}, stopping drain")
                            break

                    jvlink.jv_close()

                    if spec_records > 0:
                        any_data = True
                        try:
                            self.database.commit()
                        except Exception as e:
                            logger.error(f"Commit failed after {data_spec}: {e}")

                except JVLinkError as e:
                    code = getattr(e, "error_code", None)
                    if code == -114:
                        logger.debug(f"Spec {data_spec} not subscribed")
                    elif code == -202:
                        logger.warning(f"JV-Link busy for {data_spec}, will retry next cycle")
                    else:
                        logger.error(f"JVLink error for {data_spec}: {e}")
                        self._add_error(data_spec, str(e))
                    try:
                        jvlink.jv_close()
                    except Exception:
                        pass

                except Exception as e:
                    logger.error(f"Unexpected error for {data_spec}: {e}")
                    self._add_error(data_spec, str(e))
                    try:
                        jvlink.jv_close()
                    except Exception:
                        pass

            # Cycle faster when new data was seen (race events), slower when idle
            wait = 0.5 if any_data else 2.0
            self._stop_event.wait(timeout=wait)

        logger.info("Sequential RT monitoring loop stopped")
        try:
            jvlink.jv_close()
        except Exception:
            pass

    def _ensure_tables(self):
        """Ensure required database tables exist."""
        try:
            from src.database.schema import SchemaManager

            schema_mgr = SchemaManager(self.database)
            missing_tables = schema_mgr.get_missing_tables()

            if missing_tables:
                logger.info(
                    f"Creating {len(missing_tables)} missing tables",
                    tables=missing_tables,
                )
                schema_mgr.create_all_tables()

        except Exception as e:
            logger.warning(f"Could not create tables: {e}")

    def _add_error(self, context: str, error: str):
        """Add error to status tracking."""
        with self._lock:
            self.status.errors.append({
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "error": error,
            })
            if len(self.status.errors) > 100:
                self.status.errors = self.status.errors[-100:]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
