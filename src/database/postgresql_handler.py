"""PostgreSQL database handler.

This module provides PostgreSQL database operations for JLTSQL.
"""

from typing import Any, Dict, List, Optional

try:
    import pg8000.native
    DRIVER = "pg8000"
except ImportError:
    try:
        import psycopg
        from psycopg.rows import dict_row
        DRIVER = "psycopg"
    except ImportError:
        raise ImportError(
            "No PostgreSQL driver available. "
            "Install pg8000 (pure Python, works on Win32): pip install pg8000 "
            "Or install psycopg (requires libpq): pip install psycopg"
        )

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

    def get_db_type(self) -> str:
        """Get database type identifier.

        Returns:
            Database type string ('postgresql')
        """
        return "postgresql"

    def _quote_identifier(self, identifier: str) -> str:
        """Convert identifier to PostgreSQL-compatible form (lowercase, unquoted).

        PostgreSQL lowercases unquoted identifiers. To ensure compatibility
        with schemas that don't quote column names, we use lowercase unquoted
        identifiers instead of quoting them.

        Args:
            identifier: Column or table name

        Returns:
            Lowercase identifier (unquoted)
        """
        return identifier.lower()

    def _get_primary_key_columns(self, table_name: str) -> List[str]:
        """Extract PRIMARY KEY columns from table schema.

        Queries the information_schema to get primary key columns for a table.

        Args:
            table_name: Name of table

        Returns:
            List of primary key column names (lowercase)
        """
        try:
            sql = """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = ?::regclass
                AND i.indisprimary
                ORDER BY array_position(i.indkey, a.attnum)
            """
            rows = self.fetch_all(sql, (table_name.lower(),))
            # Handle both dict rows (psycopg) and list rows (pg8000.native)
            result = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(row.get('attname', '').lower())
                elif isinstance(row, (list, tuple)):
                    # pg8000.native returns list of lists
                    result.append(str(row[0]).lower() if row else '')
                else:
                    result.append(str(row).lower())
            return result
        except Exception as e:
            logger.warning(f"Could not get primary key for {table_name}: {e}")
            return []

    def _convert_placeholders_and_params(self, sql: str, parameters: Optional[tuple] = None):
        """Convert ? placeholders and parameters for PostgreSQL driver compatibility.

        pg8000.native uses :param1, :param2, :param3 named parameters with dict.
        psycopg uses %s placeholders with tuple.

        Args:
            sql: SQL string with ? placeholders
            parameters: Optional parameters tuple

        Returns:
            Tuple of (converted_sql, converted_parameters)
        """
        if DRIVER == "pg8000":
            # Convert ? to :param1, :param2, :param3, ... for pg8000.native
            parts = sql.split("?")
            if len(parts) == 1:
                return (sql, parameters or ())  # No placeholders

            result = parts[0]
            for i in range(1, len(parts)):
                result += f":param{i}" + parts[i]

            # Convert tuple to dict
            if parameters:
                params_dict = {f"param{i+1}": val for i, val in enumerate(parameters)}
                return (result, params_dict)
            else:
                return (result, {})
        else:  # psycopg
            # Convert ? to %s for psycopg
            converted_sql = sql.replace("?", "%s")
            return (converted_sql, parameters or ())

    def connect(self) -> None:
        """Establish PostgreSQL database connection.

        Raises:
            DatabaseError: If connection fails
        """
        try:
            if DRIVER == "pg8000":
                # pg8000.native returns dict-like results by default
                self._connection = pg8000.native.Connection(
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    timeout=self.connect_timeout,  # Add timeout parameter
                )
                self._cursor = None  # pg8000.native doesn't use cursors

            else:  # psycopg
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
                f"Connected to PostgreSQL database: {self.host}:{self.port}/{self.database}",
                driver=DRIVER
            )

        except Exception as e:
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
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            # Convert SQL and parameters for PostgreSQL driver compatibility
            sql, params = self._convert_placeholders_and_params(sql, parameters)

            if DRIVER == "pg8000":
                # pg8000.native uses connection.run() for execution with dict params
                self._connection.run(sql, **params) if isinstance(params, dict) else self._connection.run(sql)
                return self._connection.row_count
            else:  # psycopg
                if params:
                    self._cursor.execute(sql, params)
                else:
                    self._cursor.execute(sql)
                return self._cursor.rowcount

        except Exception as e:
            logger.error(f"SQL execution failed: {sql[:100]}", error=str(e))
            if self._connection:
                self.rollback()
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
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            if DRIVER == "pg8000":
                # pg8000 doesn't have executemany, execute individually
                total_rows = 0
                for params in parameters_list:
                    # Convert SQL and parameters for each execution
                    converted_sql, converted_params = self._convert_placeholders_and_params(sql, params)
                    if isinstance(converted_params, dict):
                        self._connection.run(converted_sql, **converted_params)
                    else:
                        self._connection.run(converted_sql)
                    total_rows += self._connection.row_count
                return total_rows
            else:  # psycopg
                # Convert once for psycopg
                converted_sql, _ = self._convert_placeholders_and_params(sql, ())
                self._cursor.executemany(converted_sql, parameters_list)
                return self._cursor.rowcount

        except Exception as e:
            logger.error(f"SQL executemany failed: {sql[:100]}", error=str(e))
            if self._connection:
                self.rollback()
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
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            # Convert SQL and parameters for PostgreSQL driver compatibility
            sql, params = self._convert_placeholders_and_params(sql, parameters)

            if DRIVER == "pg8000":
                # pg8000.native returns list of lists, need to convert to dict
                if isinstance(params, dict):
                    rows = self._connection.run(sql, **params)
                else:
                    rows = self._connection.run(sql)
                if not rows:
                    return None
                # Get column names from connection.columns
                columns = [col['name'] for col in self._connection.columns] if self._connection.columns else []
                if columns and rows:
                    return dict(zip(columns, rows[0]))
                return rows[0] if rows else None
            else:  # psycopg
                if params:
                    self._cursor.execute(sql, params)
                else:
                    self._cursor.execute(sql)
                row = self._cursor.fetchone()
                return row if row else None

        except Exception as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                self.rollback()
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
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            # Convert SQL and parameters for PostgreSQL driver compatibility
            sql, params = self._convert_placeholders_and_params(sql, parameters)

            if DRIVER == "pg8000":
                # pg8000.native returns list of lists, need to convert to dicts
                if isinstance(params, dict):
                    rows = self._connection.run(sql, **params)
                else:
                    rows = self._connection.run(sql)
                if not rows:
                    return []
                # Get column names from connection.columns
                columns = [col['name'] for col in self._connection.columns] if self._connection.columns else []
                if columns:
                    return [dict(zip(columns, row)) for row in rows]
                return rows  # Return as-is if no column info
            else:  # psycopg
                if params:
                    self._cursor.execute(sql, params)
                else:
                    self._cursor.execute(sql)
                rows = self._cursor.fetchall()
                return rows if rows else []

        except Exception as e:
            logger.error(f"SQL query failed: {sql[:100]}", error=str(e))
            if self._connection:
                self.rollback()
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
                WHERE tablename = ?
            """
            row = self.fetch_one(sql, (table_name.lower(),))
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
                WHERE table_name = ?
                ORDER BY ordinal_position
            """
            return self.fetch_all(sql, (table_name.lower(),))

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
            if DRIVER == "pg8000":
                # pg8000.native is always in autocommit mode
                if table_name:
                    self.execute(f"VACUUM {table_name}")
                    logger.info(f"Vacuumed table: {table_name}")
                else:
                    self.execute("VACUUM")
                    logger.info("Vacuumed all tables")
            else:  # psycopg
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

    def commit(self) -> None:
        """Commit current transaction.

        pg8000.native is always in autocommit mode and doesn't require explicit commits.
        psycopg requires explicit commits.

        Raises:
            DatabaseError: If commit fails
        """
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            if DRIVER == "pg8000":
                # pg8000.native is in autocommit mode, no commit needed
                pass
            else:  # psycopg
                self._connection.commit()
                logger.debug("Transaction committed")

        except Exception as e:
            raise DatabaseError(f"Failed to commit transaction: {e}")

    def rollback(self) -> None:
        """Rollback current transaction.

        pg8000.native is always in autocommit mode and doesn't support rollback.
        psycopg supports rollback.

        Raises:
            DatabaseError: If rollback fails
        """
        if not self._connection:
            raise DatabaseError("Database not connected")

        try:
            if DRIVER == "pg8000":
                # pg8000.native is in autocommit mode, no rollback possible
                logger.warning("pg8000.native doesn't support rollback (autocommit mode)")
            else:  # psycopg
                self._connection.rollback()
                logger.debug("Transaction rolled back")

        except Exception as e:
            raise DatabaseError(f"Failed to rollback transaction: {e}")

    def insert(self, table_name: str, data: Dict[str, Any], use_replace: bool = True) -> int:
        """Insert single row into table.

        PostgreSQL uses INSERT ... ON CONFLICT ... DO UPDATE instead of INSERT OR REPLACE.

        Args:
            table_name: Name of table
            data: Dictionary mapping column names to values
            use_replace: If True, use ON CONFLICT DO UPDATE (default: True)

        Returns:
            Number of rows inserted/updated (1 on success)

        Raises:
            DatabaseError: If insert fails
        """
        if not data:
            raise DatabaseError("No data provided for insert")

        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["?" for _ in columns])
        # Quote column names (lowercase for PostgreSQL)
        quoted_columns = [self._quote_identifier(col) for col in columns]

        if use_replace:
            # Get primary key columns for this table
            pk_columns = self._get_primary_key_columns(table_name)

            if pk_columns:
                # Build ON CONFLICT DO UPDATE clause
                # UPDATE all columns except primary key columns
                update_columns = [col for col in quoted_columns if col.lower() not in pk_columns]
                if update_columns:
                    update_set = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
                    pk_list = ", ".join(pk_columns)
                    sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT ({pk_list}) DO UPDATE SET {update_set}"
                else:
                    # All columns are primary keys, just use DO NOTHING
                    pk_list = ", ".join(pk_columns)
                    sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT ({pk_list}) DO NOTHING"
            else:
                # No primary key found, fall back to DO NOTHING to avoid errors
                logger.warning(f"No primary key found for {table_name}, using DO NOTHING")
                sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        else:
            sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

        return self.execute(sql, tuple(values))

    def insert_many(self, table_name: str, data_list: List[Dict[str, Any]], use_replace: bool = True) -> int:
        """Insert multiple rows into table.

        PostgreSQL uses INSERT ... ON CONFLICT ... DO UPDATE instead of INSERT OR REPLACE.

        Args:
            table_name: Name of table
            data_list: List of dictionaries with same keys
            use_replace: If True, use ON CONFLICT DO UPDATE (default: True)

        Returns:
            Number of rows inserted/updated

        Raises:
            DatabaseError: If insert fails
        """
        if not data_list:
            raise DatabaseError("No data provided for insert")

        # Use first row to determine columns
        columns = list(data_list[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        # Quote column names (lowercase for PostgreSQL)
        quoted_columns = [self._quote_identifier(col) for col in columns]

        if use_replace:
            # Get primary key columns for this table
            pk_columns = self._get_primary_key_columns(table_name)

            if pk_columns:
                # Build ON CONFLICT DO UPDATE clause
                # UPDATE all columns except primary key columns
                update_columns = [col for col in quoted_columns if col.lower() not in pk_columns]
                if update_columns:
                    update_set = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_columns])
                    pk_list = ", ".join(pk_columns)
                    sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT ({pk_list}) DO UPDATE SET {update_set}"
                else:
                    # All columns are primary keys, just use DO NOTHING
                    pk_list = ", ".join(pk_columns)
                    sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT ({pk_list}) DO NOTHING"
            else:
                # No primary key found, fall back to DO NOTHING to avoid errors
                logger.warning(f"No primary key found for {table_name}, using DO NOTHING")
                sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        else:
            sql = f"INSERT INTO {table_name} ({', '.join(quoted_columns)}) VALUES ({placeholders})"

        # Extract values in correct order for each row
        parameters_list = [
            tuple(row.get(col) for col in columns) for row in data_list
        ]

        return self.executemany(sql, parameters_list)
