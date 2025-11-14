"""PostgreSQL database handler.

This module provides PostgreSQL database operations for JLTSQL.
"""

from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

from src.database.base import BaseDatabase, DatabaseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PostgreSQLDatabase(BaseDatabase):
    """PostgreSQL database handler.

    Provides PostgreSQL-specific database operations for enterprise-grade
    storage of JV-Data.

    Configuration keys:
        - host: Database host (default: localhost)
        - port: Database port (default: 5432)
        - database: Database name
        - user: Database user
        - password: Database password
        - sslmode: SSL mode (default: prefer)
        - connect_timeout: Connection timeout in seconds (default: 10)

    Examples:
        >>> config = {
        ...     "host": "localhost",
        ...     "database": "keiba",
        ...     "user": "postgres",
        ...     "password": "secret"
        ... }
        >>> db = PostgreSQLDatabase(config)
        >>> with db:
        ...     db.create_table("test", "CREATE TABLE test (id SERIAL PRIMARY KEY)")
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize PostgreSQL database handler.

        Args:
            config: Database configuration
        """
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.database = config.get("database", "keiba")
        self.user = config.get("user", "postgres")
        self.password = config.get("password", "")
        self.sslmode = config.get("sslmode", "prefer")
        self.connect_timeout = config.get("connect_timeout", 10)

    def connect(self) -> None:
        """Establish PostgreSQL database connection.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            # Build connection string
            conn_str = (
                f"host={self.host} "
                f"port={self.port} "
                f"dbname={self.database} "
                f"user={self.user} "
                f"password={self.password} "
                f"sslmode={self.sslmode} "
                f"connect_timeout={self.connect_timeout}"
            )

            self._connection = psycopg.connect(
                conn_str,
                row_factory=dict_row,
            )
            self._cursor = self._connection.cursor()

            logger.info(
                f"Connected to PostgreSQL database: {self.host}:{self.port}/{self.database}"
            )

        except psycopg.Error as e:
            raise DatabaseError(f"Failed to connect to PostgreSQL database: {e}")

    def disconnect(self) -> None:
        """Close PostgreSQL database connection."""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._connection:
            self._connection.close()
            self._connection = None

        logger.info("Disconnected from PostgreSQL database")

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

        except psycopg.Error as e:
            logger.error(f"SQL execution failed: {sql[:100]}", error=str(e))
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

        except psycopg.Error as e:
            logger.error(f"SQL executemany failed: {sql[:100]}", error=str(e))
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
            return row if row else None

        except psycopg.Error as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
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
            return rows if rows else []

        except psycopg.Error as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
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
                SELECT tablename
                FROM pg_tables
                WHERE tablename = %s
            """
            row = self.fetch_one(sql, (table_name,))
            return row is not None

        except DatabaseError:
            return False

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table column information.

        Args:
            table_name: Name of table

        Returns:
            List of column information dictionaries

        Raises:
            DatabaseError: If query fails
        """
        try:
            sql = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """
            return self.fetch_all(sql, (table_name,))

        except DatabaseError:
            raise

    def analyze(self, table_name: Optional[str] = None) -> None:
        """Analyze table(s) to update statistics.

        Args:
            table_name: Optional table name (analyzes all tables if None)

        Raises:
            DatabaseError: If analyze fails
        """
        try:
            if table_name:
                self.execute(f"ANALYZE {table_name}")
                logger.info(f"Analyzed table: {table_name}")
            else:
                self.execute("ANALYZE")
                logger.info("Analyzed all tables")

        except DatabaseError:
            raise

    def vacuum(self, table_name: Optional[str] = None) -> None:
        """Vacuum table(s) to reclaim space.

        Args:
            table_name: Optional table name (vacuums all tables if None)

        Raises:
            DatabaseError: If vacuum fails
        """
        try:
            # Vacuum requires autocommit mode
            old_autocommit = self._connection.autocommit
            self._connection.autocommit = True

            if table_name:
                self.execute(f"VACUUM {table_name}")
                logger.info(f"Vacuumed table: {table_name}")
            else:
                self.execute("VACUUM")
                logger.info("Vacuumed all tables")

            self._connection.autocommit = old_autocommit

        except DatabaseError:
            raise
