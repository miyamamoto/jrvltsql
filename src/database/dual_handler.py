"""Dual-write database handler.

Wraps a primary and a secondary BaseDatabase so every DDL / INSERT / COMMIT
is issued against both. Reads are served by the primary only.

Typical use: primary=SQLiteDatabase (authoritative, fast local ingestion),
secondary=PostgreSQLDatabase (mirror for analytics / cross-host consumers).

Failure policy
--------------
The primary is the source of truth. A caller-owned transaction prevents
partial writes before commit, but SQLite and PostgreSQL cannot be committed as
one distributed transaction. If the secondary commit fails after the primary
commit, the primary remains authoritative and ``secondary_in_sync`` becomes
false. Production collectors should use PostgreSQL directly; dual mode exists
only as a best-effort migration aid.
"""

import re
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

from .base import BaseDatabase, DatabaseError

logger = get_logger(__name__)

# Regex identifying DDL statements that must be mirrored to the secondary
# when routed through ``execute()``. We intentionally match the common
# forms used throughout jrvltsql (CREATE / DROP / ALTER + TABLE / INDEX /
# VIEW / SEQUENCE / SCHEMA). Pattern is case-insensitive and skips leading
# whitespace or comment lines. Parameterised DML (INSERT / UPDATE / DELETE)
# is handled via the dedicated ``insert`` / ``insert_many`` entry points
# and therefore not mirrored here.
_DDL_RE = re.compile(
    r"""^\s*
        (?:--[^\n]*\n\s*)*              # skip line comments
        (?:CREATE|DROP|ALTER)           # DDL verbs
        \s+
        (?:UNIQUE\s+|IF\s+(?:NOT\s+)?EXISTS\s+|VIRTUAL\s+|TEMPORARY\s+|TEMP\s+|\s)*
        (?:TABLE|INDEX|VIEW|SEQUENCE|SCHEMA)
        \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DML_RE = re.compile(
    r"""^\s*
        (?:--[^\n]*\n\s*)*              # skip line comments
        (?:INSERT|UPDATE|DELETE)         # data mutation verbs
        \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _is_ddl(sql: str) -> bool:
    """Return True if the SQL looks like a CREATE / DROP / ALTER DDL.

    Used to decide whether a raw ``execute()`` call should also be mirrored
    to the secondary database.
    """
    if not sql:
        return False
    return bool(_DDL_RE.match(sql))


def _is_dml(sql: str) -> bool:
    """Return True for raw INSERT / UPDATE / DELETE statements."""
    if not sql:
        return False
    return bool(_DML_RE.match(sql))


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
        self._secondary_in_sync = True
        self._transaction_active = False
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
            self._secondary_in_sync = False

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

    def get_migration_targets(self) -> tuple[BaseDatabase, ...]:
        """Return connected backends for backend-specific schema migration."""
        targets = [self._primary]
        if self._secondary.is_connected():
            targets.append(self._secondary)
        return tuple(targets)

    # ------------------------------------------------------------------
    # Reads: primary only
    # ------------------------------------------------------------------

    def execute(self, sql: str, parameters: Optional[tuple] = None) -> Any:
        """Execute SQL on primary, and mirror schema/data mutations.

        - DDL (CREATE / DROP / ALTER of TABLE / INDEX / VIEW / SEQUENCE /
          SCHEMA) is issued against both backends so schema migrations and
          ``create-tables`` / ``create-indexes`` commands work transparently
          in dual mode.
        - INSERT / UPDATE / DELETE are issued against both backends. This is
          required for realtime physical deletions, which use raw SQL instead
          of :meth:`insert`.
        - Everything else (SELECT, PRAGMA, VACUUM, etc.) is executed on the
          primary only. Mirroring arbitrary SQL is unsafe because it may be
          engine-specific
          (``PRAGMA journal_mode`` on SQLite, ``VACUUM FULL`` on PostgreSQL,
          etc.) and because primary-only reads do not need to round-trip to
          the secondary.

        Parameterised data writes should go through :meth:`insert` or
        :meth:`insert_many`, which always mirror to both.
        """
        result = self._primary.execute(sql, parameters)
        mirrored_write = _is_ddl(sql) or _is_dml(sql)
        if mirrored_write:
            try:
                self._secondary.execute(sql, parameters)
            except Exception as e:
                logger.warning(
                    f"DualDatabase: secondary execute failed: {e} "
                    f"(sql={sql[:80]!r})"
                )
                self._secondary_errors += 1
                self._secondary_in_sync = False
                if self._transaction_active:
                    raise DatabaseError(
                        f"DualDatabase: secondary execute failed: {e}"
                    ) from e
        return result

    def executemany(self, sql: str, parameters_list: List[tuple]) -> Any:
        result = self._primary.executemany(sql, parameters_list)
        if _is_dml(sql):
            try:
                self._secondary.executemany(sql, parameters_list)
            except Exception as e:
                logger.warning(
                    f"DualDatabase: secondary executemany failed: {e} "
                    f"(sql={sql[:80]!r})"
                )
                self._secondary_errors += 1
                self._secondary_in_sync = False
                if self._transaction_active:
                    raise DatabaseError(
                        f"DualDatabase: secondary executemany failed: {e}"
                    ) from e
        return result

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

    def begin_transaction(self) -> None:
        """Start the same caller-owned transaction on both backends."""
        if self._transaction_active:
            return
        self._primary.begin_transaction()
        try:
            self._secondary.begin_transaction()
        except Exception as e:
            self._secondary_errors += 1
            self._secondary_in_sync = False
            try:
                self._primary.rollback()
            except Exception:
                pass
            raise DatabaseError(f"DualDatabase: secondary begin failed: {e}") from e
        self._transaction_active = True

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
            self._secondary_in_sync = False

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
            self._secondary_in_sync = False
            if self._transaction_active:
                raise DatabaseError(
                    f"DualDatabase: secondary insert failed for {table_name}: {e}"
                ) from e
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
            self._secondary_in_sync = False
            if self._transaction_active:
                raise DatabaseError(
                    f"DualDatabase: secondary insert_many failed for {table_name}: {e}"
                ) from e
        return rows

    def commit(self) -> None:
        """Commit primary then the best-effort secondary mirror.

        Once the primary commit succeeds it cannot be rolled back if the
        secondary commit subsequently fails. In that case the primary remains
        authoritative and callers can detect the required mirror rebuild via
        :attr:`secondary_in_sync`.
        """
        self._primary.commit()
        try:
            self._secondary.commit()
            self._transaction_active = False
        except Exception as e:
            logger.warning(f"DualDatabase: secondary commit failed: {e}")
            self._secondary_errors += 1
            self._secondary_in_sync = False
            self._transaction_active = False

    def rollback(self) -> None:
        """Rollback the caller-owned transaction on both backends."""
        errors = []
        try:
            self._primary.rollback()
        except Exception as e:
            errors.append(f"primary: {e}")
        try:
            self._secondary.rollback()
        except Exception as e:
            self._secondary_errors += 1
            self._secondary_in_sync = False
            errors.append(f"secondary: {e}")
        self._transaction_active = False
        if errors:
            raise DatabaseError("DualDatabase rollback failed (" + "; ".join(errors) + ")")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def secondary_error_count(self) -> int:
        """Number of secondary-side failures since startup (read-only)."""
        return self._secondary_errors

    @property
    def secondary_in_sync(self) -> bool:
        """Whether every secondary operation has succeeded since startup."""
        return self._secondary_in_sync

    def __repr__(self) -> str:
        return (
            f"DualDatabase(primary={self._primary!r}, "
            f"secondary={self._secondary!r}, "
            f"secondary_errors={self._secondary_errors})"
        )
