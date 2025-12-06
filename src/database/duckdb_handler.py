"""DuckDB database handler.

This module provides DuckDB database operations for JLTSQL.
DuckDB is an in-process analytical database optimized for OLAP workloads,
making it ideal for complex queries and analytics on JRA-VAN data.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DuckDBDatabase(BaseDatabase):
    """DuckDB database handler.

    Provides DuckDB-specific database operations for storing and analyzing JV-Data.
    DuckDB is optimized for analytical queries and can efficiently handle
    large-scale data analysis tasks.

    Configuration keys:
        - path: Path to DuckDB database file
        - read_only: Open in read-only mode (default: False)
        - memory_limit: Memory limit for DuckDB (e.g., "2GB", default: None)
        - threads: Number of threads to use (default: None, auto-detect)

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
        self.memory_limit = config.get("memory_limit", None)
        self.threads = config.get("threads", None)

    def _quote_identifier(self, identifier: str) -> str:
        """Quote SQL identifier (column/table name).

        DuckDB uses double quotes for identifiers (SQL standard).

        Args:
            identifier: Column or table name to quote

        Returns:
            Quoted identifier string
        """
        return f'"{identifier}"'

    def get_db_type(self) -> str:
        """Get database type identifier.

        Returns:
            Database type string ('duckdb')
        """
        return "duckdb"

    def connect(self) -> None:
        """Establish DuckDB database connection.

        Creates database file and parent directories if they don't exist.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            import duckdb
        except ImportError:
            raise DatabaseError(
                "DuckDB not installed. Please install with: pip install duckdb"
            )

        try:
            # Create parent directories if needed
            if not self.read_only:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to DuckDB
            self._connection = duckdb.connect(
                str(self.db_path),
                read_only=self.read_only,
            )

            # Set memory limit if configured
            if self.memory_limit:
                self._connection.execute(f"SET memory_limit='{self.memory_limit}'")

            # Set thread count if configured
            if self.threads:
                self._connection.execute(f"SET threads={self.threads}")

            # Performance optimizations
            self._connection.execute("SET preserve_insertion_order=false")

            # Get cursor
            self._cursor = self._connection.cursor()

            logger.info(f"Connected to DuckDB database: {self.db_path}")

        except Exception as e:
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

            # DuckDB doesn't always provide rowcount for DDL statements
            try:
                return self._cursor.rowcount if self._cursor.rowcount >= 0 else 0
            except Exception:
                return 0

        except Exception as e:
            logger.error(f"SQL execution failed: {sql[:100]}", error=str(e))
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
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
            try:
                return self._cursor.rowcount if self._cursor.rowcount >= 0 else 0
            except Exception:
                return len(parameters_list)

        except Exception as e:
            logger.error(f"SQL executemany failed: {sql[:100]}", error=str(e))
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
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

        except Exception as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
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
            if rows:
                # Get column names
                columns = [desc[0] for desc in self._cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []

        except Exception as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
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
            sql = "SELECT table_name FROM information_schema.tables WHERE table_name = ?"
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

        Note: DuckDB automatically manages space, but this can force
        a checkpoint to flush WAL to disk.

        Raises:
            DatabaseError: If operation fails
        """
        try:
            self.execute("CHECKPOINT")
            logger.info("Database checkpoint executed")

        except DatabaseError:
            raise

    def analyze(self) -> None:
        """Analyze database to update statistics.

        DuckDB automatically maintains statistics, but this can force
        an update for better query planning.

        Raises:
            DatabaseError: If operation fails
        """
        try:
            self.execute("ANALYZE")
            logger.info("Database analyzed")

        except DatabaseError:
            raise
    def insert(self, table_name: str, data: Dict[str, Any], use_replace: bool = True) -> int:
        """Insert a single row into a table.

        DuckDB uses INSERT INTO ... ON CONFLICT DO UPDATE for UPSERT.

        Args:
            table_name: Target table name
            data: Dictionary of column names to values
            use_replace: If True, update on conflict (UPSERT)

        Returns:
            Number of inserted rows (1 on success, 0 on failure)

        Raises:
            DatabaseError: If insert fails
        """
        if not data:
            return 0

        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["?" for _ in columns])
        quoted_columns = [self._quote_identifier(col) for col in columns]

        if use_replace:
            # DuckDB: INSERT OR REPLACE is supported in newer versions
            # Use INSERT INTO ... ON CONFLICT DO UPDATE SET for compatibility
            update_clause = ", ".join([f'{self._quote_identifier(col)} = EXCLUDED.{self._quote_identifier(col)}' for col in columns])
            sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT DO UPDATE SET {update_clause}'
        else:
            sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders})'

        try:
            return self.execute(sql, tuple(values))
        except DatabaseError:
            # If ON CONFLICT fails (no PK defined), try simple INSERT
            if use_replace:
                sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders})'
                try:
                    return self.execute(sql, tuple(values))
                except DatabaseError:
                    pass
            raise

    def insert_many(self, table_name: str, data_list: List[Dict[str, Any]], use_replace: bool = True) -> int:
        """Insert multiple rows into a table.

        DuckDB uses INSERT INTO ... ON CONFLICT DO UPDATE for UPSERT.

        Args:
            table_name: Target table name
            data_list: List of dictionaries
            use_replace: If True, update on conflict (UPSERT)

        Returns:
            Number of inserted rows

        Raises:
            DatabaseError: If insert fails
        """
        if not data_list:
            return 0

        columns = list(data_list[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        quoted_columns = [self._quote_identifier(col) for col in columns]

        if use_replace:
            update_clause = ", ".join([f'{self._quote_identifier(col)} = EXCLUDED.{self._quote_identifier(col)}' for col in columns])
            sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT DO UPDATE SET {update_clause}'
        else:
            sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders})'

        values_list = [tuple(d.get(col) for col in columns) for d in data_list]

        try:
            return self.executemany(sql, values_list)
        except DatabaseError as e:
            # If ON CONFLICT fails, try simple INSERT or individual inserts
            if use_replace and "ON CONFLICT" in str(e):
                sql = f'INSERT INTO {table_name} ({", ".join(quoted_columns)}) VALUES ({placeholders})'
                try:
                    return self.executemany(sql, values_list)
                except DatabaseError:
                    pass
            
            # Fallback to individual inserts
            logger.warning(f"Batch insert failed, trying individual inserts", table=table_name, error=str(e))
            success_count = 0
            for data in data_list:
                try:
                    success_count += self.insert(table_name, data, use_replace=False)
                except DatabaseError as insert_error:
                    logger.error(f"Failed to insert record", table=table_name, error=str(insert_error))
            return success_count
