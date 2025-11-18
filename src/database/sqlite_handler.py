"""SQLite database handler.

This module provides SQLite database operations for JLTSQL.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SQLiteDatabase(BaseDatabase):
    """SQLite database handler.

    Provides SQLite-specific database operations for storing JV-Data.

    Configuration keys:
        - path: Path to SQLite database file
        - timeout: Connection timeout in seconds (default: 30)
        - check_same_thread: Check same thread (default: False)

    Examples:
        >>> config = {"path": "./data/keiba.db"}
        >>> db = SQLiteDatabase(config)
        >>> with db:
        ...     db.create_table("test", "CREATE TABLE test (id INTEGER PRIMARY KEY)")
        ...     db.insert("test", {"id": 1})
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize SQLite database handler.

        Args:
            config: Database configuration
        """
        super().__init__(config)
        self.db_path = Path(config.get("path", "./data/keiba.db"))
        self.timeout = config.get("timeout", 30.0)
        self.check_same_thread = config.get("check_same_thread", False)

    def connect(self) -> None:
        """Establish SQLite database connection.

        Creates database file and parent directories if they don't exist.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            # Create parent directories if needed
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            self._connection = sqlite3.connect(
                str(self.db_path),
                timeout=self.timeout,
                check_same_thread=self.check_same_thread,
            )
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use Row factory for dict-like access
            self._connection.row_factory = sqlite3.Row
            self._cursor = self._connection.cursor()

            logger.info(f"Connected to SQLite database: {self.db_path}")

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to SQLite database: {e}")

    def disconnect(self) -> None:
        """Close SQLite database connection."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._connection:
            self._connection.close()
            self._connection = None

        logger.info("Disconnected from SQLite database")

    def execute(self, sql: str, parameters: Optional[tuple] = None) -> int:
        """Execute SQL statement.

        Args:
            sql: SQL statement
            parameters: Optional parameters

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If execution fails
        """
        if not self._cursor:
            raise DatabaseError("Database not connected")

        try:
            if parameters:
                self._cursor.execute(sql, parameters)
            else:
                self._cursor.execute(sql)

            return self._cursor.rowcount

        except sqlite3.Error as e:
            logger.error(f"SQL execution failed: {sql[:100]}", error=str(e))
            if self._connection:
                self._connection.rollback()
            raise DatabaseError(f"SQL execution failed: {e}")

    def executemany(self, sql: str, parameters_list: List[tuple]) -> int:
        """Execute SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            parameters_list: List of parameter tuples

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If execution fails
        """
        if not self._cursor:
            raise DatabaseError("Database not connected")

        try:
            self._cursor.executemany(sql, parameters_list)
            return self._cursor.rowcount

        except sqlite3.Error as e:
            logger.error(f"SQL executemany failed: {sql[:100]}", error=str(e))
            if self._connection:
                self._connection.rollback()
            raise DatabaseError(f"SQL executemany failed: {e}")

    def fetch_one(self, sql: str, parameters: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch single row.

        Args:
            sql: SQL query
            parameters: Optional parameters

        Returns:
            Dictionary mapping column names to values, or None

        Raises:
            DatabaseError: If query fails
        """
        if not self._cursor:
            raise DatabaseError("Database not connected")

        try:
            if parameters:
                self._cursor.execute(sql, parameters)
            else:
                self._cursor.execute(sql)

            row = self._cursor.fetchone()
            if row:
                return dict(row)
            return None

        except sqlite3.Error as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                self._connection.rollback()
            raise DatabaseError(f"SQL query failed: {e}")

    def fetch_all(self, sql: str, parameters: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows.

        Args:
            sql: SQL query
            parameters: Optional parameters

        Returns:
            List of dictionaries

        Raises:
            DatabaseError: If query fails
        """
        if not self._cursor:
            raise DatabaseError("Database not connected")

        try:
            if parameters:
                self._cursor.execute(sql, parameters)
            else:
                self._cursor.execute(sql)

            rows = self._cursor.fetchall()
            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                self._connection.rollback()
            raise DatabaseError(f"SQL query failed: {e}")

    def create_table(self, table_name: str, schema: str) -> None:
        """Create table from SQL schema.

        Args:
            table_name: Name of table to create
            schema: SQL CREATE TABLE statement

        Raises:
            DatabaseError: If creation fails
        """
        try:
            self.execute(schema)
            logger.info(f"Created table: {table_name}")

        except DatabaseError:
            raise

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
            row = self.fetch_one(sql, (table_name,))
            return row is not None

        except DatabaseError:
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information.

        Args:
            table_name: Name of table

        Returns:
            List of column information dictionaries

        Raises:
            DatabaseError: If query fails
        """
        try:
            sql = f"PRAGMA table_info({table_name})"
            return self.fetch_all(sql)

        except DatabaseError:
            raise

    def vacuum(self) -> None:
        """Vacuum database to reclaim space.

        Raises:
            DatabaseError: If vacuum fails
        """
        try:
            self.execute("VACUUM")
            logger.info("Database vacuumed")

        except DatabaseError:
            raise
