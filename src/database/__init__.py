"""Database handlers for JLTSQL.

Exposes :func:`create_database_from_config` as the canonical way to build a
:class:`BaseDatabase` from the user's config. Supported ``database.type``
values:

- ``sqlite``      → :class:`SQLiteDatabase`
- ``postgresql``  → :class:`PostgreSQLDatabase`
- ``dual``        → :class:`DualDatabase` wrapping SQLite (primary) + PostgreSQL (secondary)

The ``dual`` mode lets ingestion keep writing to SQLite (historical
behavior) while also mirroring every write into PostgreSQL, which is the
recommended migration path when standing up a remote analytics PG alongside
an existing SQLite installation.
"""

from typing import Any, Optional

from .base import BaseDatabase, DatabaseError  # re-export for external callers

SUPPORTED_DB_TYPES = ("sqlite", "postgresql", "dual")


def create_database_from_config(
    config: Any,
    db_type_override: Optional[str] = None,
) -> BaseDatabase:
    """Build a :class:`BaseDatabase` from config.

    Args:
        config: Loaded configuration object exposing a ``get(key, default)``
            method (see :mod:`src.utils.config`).
        db_type_override: Optional explicit type (``sqlite`` / ``postgresql``
            / ``dual``). If ``None``, uses ``database.type`` from the config.

    Returns:
        Concrete BaseDatabase instance (not yet connected).

    Raises:
        ValueError: If the resolved db_type is not supported.
        DatabaseError: If PostgreSQL is requested without matching config.
    """
    # Local imports to avoid circular-import friction with base.py.
    from .sqlite_handler import SQLiteDatabase
    from .postgresql_handler import PostgreSQLDatabase
    from .dual_handler import DualDatabase

    if db_type_override:
        db_type = db_type_override
    elif config is not None:
        db_type = config.get("database.type", "sqlite")
    else:
        db_type = "sqlite"

    if db_type == "sqlite":
        sqlite_config = (
            config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
        )
        return SQLiteDatabase(sqlite_config)

    if db_type == "postgresql":
        if not config:
            raise DatabaseError(
                "PostgreSQL requires a configuration file with "
                "databases.postgresql settings"
            )
        return PostgreSQLDatabase(config.get("databases.postgresql"))

    if db_type == "dual":
        if not config:
            raise DatabaseError(
                "Dual-write requires a configuration file with both "
                "databases.sqlite and databases.postgresql settings"
            )
        sqlite_config = config.get("databases.sqlite") or {"path": "data/keiba.db"}
        pg_config = config.get("databases.postgresql")
        if not pg_config:
            raise DatabaseError(
                "Dual-write requires databases.postgresql to be configured"
            )
        primary = SQLiteDatabase(sqlite_config)
        secondary = PostgreSQLDatabase(pg_config)
        return DualDatabase(primary=primary, secondary=secondary)

    raise ValueError(
        f"Unsupported database type: {db_type!r}. "
        f"Supported: {', '.join(SUPPORTED_DB_TYPES)}"
    )


__all__ = [
    "BaseDatabase",
    "DatabaseError",
    "create_database_from_config",
    "SUPPORTED_DB_TYPES",
]
