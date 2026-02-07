"""NAR (地方競馬) database schema definitions.

NAR tables use the same schema structure as JRA tables but with _NAR suffix.
This module provides schema definitions for NAR racing data.

Generated from: src/database/schema.py (JRA schemas)
NAR tables follow the same structure as JRA with _NAR suffix as per table_mappings.py
"""

from typing import Dict

from src.database.schema import SCHEMAS


def get_nar_schemas() -> Dict[str, str]:
    """Generate NAR table schemas from JRA schemas.

    Creates NAR-specific table schemas by:
    1. Taking JRA table schemas from SCHEMAS
    2. Appending _NAR suffix to table names
    3. Updating CREATE TABLE statements accordingly

    Returns:
        Dictionary mapping NAR table names to their CREATE TABLE SQL statements

    Examples:
        >>> schemas = get_nar_schemas()
        >>> 'NL_RA_NAR' in schemas
        True
        >>> 'RT_RA_NAR' in schemas
        True
    """
    nar_schemas = {}

    for table_name, schema_sql in SCHEMAS.items():
        # Generate NAR table name by adding _NAR suffix
        nar_table_name = f"{table_name}_NAR"

        # Replace table name in CREATE TABLE statement
        # Example: "CREATE TABLE IF NOT EXISTS NL_RA" -> "CREATE TABLE IF NOT EXISTS NL_RA_NAR"
        nar_schema_sql = schema_sql.replace(
            f"CREATE TABLE IF NOT EXISTS {table_name} ",
            f"CREATE TABLE IF NOT EXISTS {nar_table_name} "
        )

        nar_schemas[nar_table_name] = nar_schema_sql

    return nar_schemas


# Pre-generate NAR schemas for easy access
NAR_SCHEMAS = get_nar_schemas()


def get_nar_table_names() -> list:
    """Get list of all NAR table names.

    Returns:
        List of NAR table names (with _NAR suffix)
    """
    return list(NAR_SCHEMAS.keys())


def create_all_nar_tables(db) -> None:
    """Create all NAR tables in the database.

    Args:
        db: Database instance (BaseDatabase)

    Raises:
        Exception: If table creation fails
    """
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Creating NAR tables...")

    for table_name, schema_sql in NAR_SCHEMAS.items():
        try:
            db.execute(schema_sql)
            logger.debug(f"Created NAR table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to create NAR table {table_name}: {e}")
            raise

    logger.info(f"Successfully created {len(NAR_SCHEMAS)} NAR tables")
