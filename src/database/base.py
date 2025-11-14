"""Base database handler for JLTSQL.

This module provides the abstract base class for database operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Database operation error."""

    pass


class BaseDatabase(ABC):
    """Abstract base class for database handlers.

    This class defines the interface for all database implementations
    (SQLite, DuckDB, PostgreSQL).

    Subclasses must implement:
        - connect(): Establish database connection
        - disconnect(): Close database connection
        - execute(): Execute SQL statement
        - executemany(): Execute SQL statement with multiple parameter sets
        - fetch_one(): Fetch single row
        - fetch_all(): Fetch all rows
        - create_table(): Create table from schema
        - table_exists(): Check if table exists

    Examples:
        >>> class MySQLiteDB(BaseDatabase):
        ...     def connect(self):
        ...         # Implementation
        ...         pass
        ...     # ... implement other methods
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize database handler.

        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self._connection = None
        self._cursor = None
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection.

        Raises:
            DatabaseError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def execute(
        self, sql: str, parameters: Optional[tuple] = None
    ) -> int:
        """Execute SQL statement.

        Args:
            sql: SQL statement
            parameters: Optional parameters for parameterized query

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If execution fails
        """
        pass

    @abstractmethod
    def executemany(
        self, sql: str, parameters_list: List[tuple]
    ) -> int:
        """Execute SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            parameters_list: List of parameter tuples

        Returns:
            Number of affected rows

        Raises:
            DatabaseError: If execution fails
        """
        pass

    @abstractmethod
    def fetch_one(self, sql: str, parameters: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """Fetch single row.

        Args:
            sql: SQL query
            parameters: Optional parameters

        Returns:
            Dictionary mapping column names to values, or None if no row

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    def fetch_all(self, sql: str, parameters: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Fetch all rows.

        Args:
            sql: SQL query
            parameters: Optional parameters

        Returns:
            List of dictionaries mapping column names to values

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    def create_table(self, table_name: str, schema: str) -> None:
        """Create table from SQL schema.

        Args:
            table_name: Name of table to create
            schema: SQL CREATE TABLE statement

        Raises:
            DatabaseError: If creation fails
        """
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        pass

    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert single row into table.

        Args:
            table_name: Name of table
            data: Dictionary mapping column names to values

        Returns:
            Number of rows inserted (1 on success)

        Raises:
            DatabaseError: If insert fails
        """
        if not data:
            raise DatabaseError("No data provided for insert")

        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["?" for _ in columns])
        # Quote column names with backticks to support names starting with digits
        quoted_columns = [f"`{col}`" for col in columns]

        sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

        return self.execute(sql, tuple(values))

    def insert_many(self, table_name: str, data_list: List[Dict[str, Any]]) -> int:
        """Insert multiple rows into table.

        Args:
            table_name: Name of table
            data_list: List of dictionaries with same keys

        Returns:
            Number of rows inserted

        Raises:
            DatabaseError: If insert fails
        """
        if not data_list:
            raise DatabaseError("No data provided for insert")

        # Use first row to determine columns
        columns = list(data_list[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        # Quote column names with backticks to support names starting with digits
        quoted_columns = [f"`{col}`" for col in columns]

        sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

        # Extract values in correct order for each row
        parameters_list = [
            tuple(row.get(col) for col in columns) for row in data_list
        ]

        return self.executemany(sql, parameters_list)

    def commit(self) -> None:
        """Commit current transaction.

        Raises:
            DatabaseError: If commit fails
        """
        if self._connection:
            try:
                self._connection.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                raise DatabaseError(f"Failed to commit transaction: {e}")
        else:
            raise DatabaseError("No active connection")

    def rollback(self) -> None:
        """Rollback current transaction.

        Raises:
            DatabaseError: If rollback fails
        """
        if self._connection:
            try:
                self._connection.rollback()
                logger.debug("Transaction rolled back")
            except Exception as e:
                raise DatabaseError(f"Failed to rollback transaction: {e}")
        else:
            raise DatabaseError("No active connection")

    def is_connected(self) -> bool:
        """Check if database is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connection is not None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"<{self.__class__.__name__} status={status}>"
