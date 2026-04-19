"""Dual-write database handler.

Wraps a primary and a secondary BaseDatabase so every DDL / INSERT / COMMIT
is issued against both. Reads are served by the primary only.

Typical use: primary=SQLiteDatabase (authoritative, fast local ingestion),
secondary=PostgreSQLDatabase (mirror for analytics / cross-host consumers).

Failure policy
--------------
The primary is the source of truth. Secondary failures (connect, create_table,
insert, insert_many, commit) are logged as warnings and tracked via
``self._secondary_errors`` but **do NOT raise**, preserving ingestion
throughput if the secondary is unavailable.
"""

from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

from .base import BaseDatabase, DatabaseError

logger = get_logger(__name__)


class DualDatabase(BaseDatabase):
    """BaseDatabase implementation that forwards writes to two backends.

    The primary is treated as the source of truth; secondary failures are
    logged but do not propagate. This mirrors the ``PgWriter`` dual-write
    pattern used by the sibling ``jrvltsql-nar`` project, but here the
    BaseDatabase interface itself is the abstraction boundary.
    """

    def __init__(self, primary: BaseDatabase, secondary: BaseDatabase):
        # NOTE: we intentionally skip ``super().__init__`` because our
        # configuration is the pair of backends themselves. The ABC requires
        # the abstract methods to be implemented (they are, below).
        self.config = {
            "primary_type": primary.get_db_type(),
            "secondary_type": secondary.get_db_type(),
        }
        self._connection = None  # BaseDatabase.is_connected() reads this
        self._cursor = None
        self._primary = primary
        self._secondary = secondary
        self._secondary_errors = 0
        logger.info(
            f"DualDatabase initialized: primary={primary.get_db_type()}, "
            f"secondary={secondary.get_db_type()}"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect both backends. Secondary failure is logged, not raised."""
        self._primary.connect()
        # Surface primary's connection so BaseDatabase.is_connected() works.
        self._connection = getattr(self._primary, "_connection", None)
        try:
            self._secondary.connect()
        except Exception as e:
            logger.warning(
                f"DualDatabase: secondary connect failed ({self._secondary.get_db_type()}): {e}"
            )
            self._secondary_errors += 1

    def disconnect(self) -> None:
        """Disconnect both backends."""
        try:
            self._primary.disconnect()
        finally:
            try:
                self._secondary.disconnect()
            except Exception as e:
                logger.warning(
                    f"DualDatabase: secondary disconnect failed: {e}"
                )
        self._connection = None

    def is_connected(self) -> bool:
        """Report connection status of the primary backend."""
        return self._primary.is_connected()

    def get_db_type(self) -> str:
        """Report the primary's type.

        The caller side uses ``get_db_type()`` to decide behavior such as
        whether to attempt rollback. Preserving the primary's semantics keeps
        the rest of the codebase unchanged.
        """
        return self._primary.get_db_type()

    # ------------------------------------------------------------------
    # Reads: primary only
    # ------------------------------------------------------------------

    def execute(self, sql: str, parameters: Optional[tuple] = None) -> Any:
        """Execute SQL on primary (reads + non-idempotent writes).

        NOTE: arbitrary ``execute()`` calls are NOT mirrored to secondary
        because the SQL may be reads or primary-specific statements
        (PRAGMA, VACUUM, etc.). Use ``insert`` / ``insert_many`` /
        ``create_table`` / ``commit`` for dual-write paths.
        """
        return self._primary.execute(sql, parameters)

    def executemany(self, sql: str, parameters_list: List[tuple]) -> Any:
        return self._primary.executemany(sql, parameters_list)

    def fetch_one(
        self, sql: str, parameters: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        return self._primary.fetch_one(sql, parameters)

    def fetch_all(
        self, sql: str, parameters: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        return self._primary.fetch_all(sql, parameters)

    def table_exists(self, table_name: str) -> bool:
        return self._primary.table_exists(table_name)

    # ------------------------------------------------------------------
    # Writes: dual
    # ------------------------------------------------------------------

    def create_table(self, table_name: str, schema: str) -> None:
        """Create table in both backends.

        The shared DDL in :mod:`src.database.schema` is deliberately written
        in a subset of SQL compatible with both SQLite and PostgreSQL, so
        the same schema string works on each side.
        """
        self._primary.create_table(table_name, schema)
        try:
            self._secondary.create_table(table_name, schema)
        except Exception as e:
            logger.warning(
                f"DualDatabase: secondary create_table failed for {table_name}: {e}"
            )
            self._secondary_errors += 1

    def insert(
        self,
        table_name: str,
        data: Dict[str, Any],
        use_replace: bool = True,
    ) -> int:
        rows = self._primary.insert(table_name, data, use_replace)
        try:
            self._secondary.insert(table_name, data, use_replace)
        except Exception as e:
            logger.warning(
                f"DualDatabase: secondary insert failed for {table_name}: {e}"
            )
            self._secondary_errors += 1
        return rows

    def insert_many(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        use_replace: bool = True,
    ) -> int:
        rows = self._primary.insert_many(table_name, data_list, use_replace)
        try:
            self._secondary.insert_many(table_name, data_list, use_replace)
        except Exception as e:
            logger.warning(
                f"DualDatabase: secondary insert_many failed for {table_name} "
                f"({len(data_list)} rows): {e}"
            )
            self._secondary_errors += 1
        return rows

    def commit(self) -> None:
        self._primary.commit()
        try:
            self._secondary.commit()
        except Exception as e:
            logger.warning(f"DualDatabase: secondary commit failed: {e}")
            self._secondary_errors += 1

    def rollback(self) -> None:
        """Rollback primary only.

        The secondary (typically PostgreSQL) may run in autocommit mode and
        not support rollback. Callers that care about atomicity across both
        stores must manage at a higher level; dual-write is a best-effort
        mirror, not a distributed transaction.
        """
        try:
            self._primary.rollback()
        except DatabaseError:
            # Primary already raised; don't double-report.
            raise

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def secondary_error_count(self) -> int:
        """Number of secondary-side failures since startup (read-only)."""
        return self._secondary_errors

    def __repr__(self) -> str:
        return (
            f"DualDatabase(primary={self._primary!r}, "
            f"secondary={self._secondary!r}, "
            f"secondary_errors={self._secondary_errors})"
        )
