"""Deterministic smoke contracts for parser dispatch and schema creation."""

from src.database.schema import SCHEMAS, SchemaManager
from src.database.sqlite_handler import SQLiteDatabase
from src.parser.factory import ALL_RECORD_TYPES, ParserFactory


def test_every_current_parser_is_loadable():
    factory = ParserFactory()

    assert set(factory.supported_types()) == set(ALL_RECORD_TYPES)
    for record_type in ALL_RECORD_TYPES:
        parser = factory.get_parser(record_type)
        assert parser is not None
        assert callable(parser.parse)


def test_every_executable_schema_is_created_in_isolated_sqlite(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "all-schemas.db")})

    with database:
        results = SchemaManager(database).create_all_tables()
        created_tables = {
            row["name"]
            for row in database.fetch_all(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert results == {table_name: True for table_name in SCHEMAS}
    assert set(SCHEMAS) <= created_tables
