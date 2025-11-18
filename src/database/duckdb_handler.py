"""DuckDB database handler.

This module provides DuckDB database operations for JLTSQL.
"""

import duckdb
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DuckDBDatabase(BaseDatabase):
    """DuckDB database handler.

    Provides DuckDB-specific database operations for analytical queries
    on JV-Data. DuckDB is optimized for OLAP workloads and analytics.

    Configuration keys:
        - path: Path to DuckDB database file
        - read_only: Open in read-only mode (default: False)
        - memory_limit: Memory limit in GB (default: None)

    Examples:
        >>> config = {"path": "./data/keiba.duckdb"}
        >>> db = DuckDBDatabase(config)
        >>> with db:
        ...     db.create_table("test", "CREATE TABLE test (id INTEGER PRIMARY KEY)")
        ...     db.insert("test", {"id": 1})
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize DuckDB database handler.

        Args:
            config: Database configuration
        """
        super().__init__(config)
        self.db_path = Path(config.get("path", "./data/keiba.duckdb"))
        self.read_only = config.get("read_only", False)
        self.memory_limit = config.get("memory_limit")

    def _quote_identifier(self, identifier: str) -> str:
        """Quote SQL identifier using double quotes (DuckDB style).

        Args:
            identifier: Column or table name to quote

        Returns:
            Quoted identifier string
        """
        return f'"{identifier}"'

    def connect(self) -> None:
        """Establish DuckDB database connection.

        Creates database file and parent directories if they don't exist.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            # Create parent directories if needed
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self._connection = duckdb.connect(
                str(self.db_path),
                read_only=self.read_only,
            )

            # Set memory limit if specified
            if self.memory_limit:
                self._connection.execute(f"SET memory_limit='{self.memory_limit}'")

            self._cursor = self._connection.cursor()

            logger.info(f"Connected to DuckDB database: {self.db_path}")

        except duckdb.Error as e:
            raise DatabaseError(f"Failed to connect to DuckDB database: {e}")

    def disconnect(self) -> None:
        """Close DuckDB database connection."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._connection:
            self._connection.close()
            self._connection = None

        logger.info("Disconnected from DuckDB database")

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

            # DuckDB returns affected rows differently
            return self._cursor.rowcount if hasattr(self._cursor, 'rowcount') else 0

        except duckdb.Error as e:
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
            return len(parameters_list)

        except duckdb.Error as e:
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
                # Get column names
                columns = [desc[0] for desc in self._cursor.description]
                return dict(zip(columns, row))
            return None

        except duckdb.Error as e:
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
            if not rows:
                return []

            # Get column names
            columns = [desc[0] for desc in self._cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        except duckdb.Error as e:
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
            sql = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = ?
            """
            row = self.fetch_one(sql, (table_name,))
            return row is not None

        except DatabaseError:
            return False

    def export_to_parquet(self, table_name: str, output_path: str) -> None:
        """Export table to Parquet format.

        DuckDB can efficiently export to Parquet for archival or sharing.

        Args:
            table_name: Name of table to export
            output_path: Path to output Parquet file

        Raises:
            DatabaseError: If export fails
        """
        try:
            sql = f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)"
            self.execute(sql)
            logger.info(f"Exported {table_name} to {output_path}")

        except DatabaseError:
            raise

    def import_from_parquet(self, table_name: str, input_path: str) -> None:
        """Import table from Parquet format.

        Args:
            table_name: Name of table to import into
            input_path: Path to input Parquet file

        Raises:
            DatabaseError: If import fails
        """
        try:
            sql = f"COPY {table_name} FROM '{input_path}' (FORMAT PARQUET)"
            self.execute(sql)
            logger.info(f"Imported {input_path} to {table_name}")

        except DatabaseError:
            raise
