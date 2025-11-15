#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate all parsers and schemas from JV-Data format definitions.

This script reads jv_data_formats.json and generates:
1. Parser classes for all 38 record types
2. Schema definitions for all 38 record types (both NL_ and RT_ tables)
"""

import json
import os
from pathlib import Path


def load_format_definitions():
    """Load format definitions from JSON file."""
    with open('jv_data_formats.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_parser_class(record_id, format_data):
    """Generate parser class code for a record type."""
    format_no = format_data['format_no']
    name = format_data['name']
    fields = format_data['fields']

    # Generate field definitions
    field_defs = []
    for field in fields:
        field_name = field['name']
        position = field['position']
        length = field['length']

        # Sanitize field name for Python
        py_field_name = field_name.replace(' ', '_').replace('-', '_')
        # Remove special characters
        py_field_name = ''.join(c if c.isalnum() or c == '_' else '' for c in py_field_name)

        field_defs.append(f"            ({position}, {length}, '{py_field_name}'),  # {field_name}")

    field_defs_str = '\n'.join(field_defs)

    parser_code = f'''"""Parser for {record_id} record ({name})."""

from typing import List, Tuple

from src.parser.base import BaseParser


class {record_id}Parser(BaseParser):
    """Parser for {record_id} record (Format {format_no}).

    Record type: {name}
    Total fields: {len(fields)}
    """

    record_type = "{record_id}"

    def _define_fields(self) -> List[Tuple[int, int, str]]:
        """Define field positions and lengths.

        Returns:
            List of tuples: (position, length, field_name)
        """
        return [
{field_defs_str}
        ]
'''

    return parser_code


def generate_all_parsers(formats):
    """Generate all parser files."""
    parser_dir = Path('src/parser')
    parser_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for record_id, format_data in sorted(formats.items()):
        parser_code = generate_parser_class(record_id, format_data)

        # Write parser file
        filename = f'{record_id.lower()}_parser.py'
        filepath = parser_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(parser_code)

        generated_files.append(filename)
        print(f'Generated: {filepath}')

    return generated_files


def generate_schema_definitions(formats):
    """Generate schema definitions for all record types."""
    # Record types that are provided in real-time (JVRTOpen)
    # Based on JV-Data4901.xlsx specification
    REALTIME_RECORD_TYPES = [
        'AV', 'CC', 'DM', 'H1', 'H6', 'HR', 'JC',
        'O1', 'O2', 'O3', 'O4', 'O5', 'O6',
        'RA', 'SE', 'TC', 'TM', 'WE', 'WH'
    ]

    schemas = {}

    for record_id, format_data in sorted(formats.items()):
        fields = format_data['fields']

        # Generate CREATE TABLE statement
        column_defs = []
        key_columns = []

        for field in fields:
            field_name = field['name']
            # Sanitize field name for SQL
            sql_field_name = field_name.replace(' ', '_').replace('-', '_')
            sql_field_name = ''.join(c if c.isalnum() or c == '_' else '' for c in sql_field_name)

            column_defs.append(f"            {sql_field_name} TEXT,  -- {field_name}")

            if field['is_key']:
                key_columns.append(sql_field_name)

        column_defs_str = '\n'.join(column_defs)
        primary_key = f"PRIMARY KEY ({', '.join(key_columns)})" if key_columns else ""

        # NL_ table (Normal Load - historical data) - ALL record types
        nl_table_name = f"NL_{record_id}"
        nl_schema = f'''        CREATE TABLE IF NOT EXISTS {nl_table_name} (
{column_defs_str}

            {primary_key}
        )'''
        schemas[nl_table_name] = nl_schema

        # RT_ table (Real-Time data) - ONLY for real-time record types
        if record_id in REALTIME_RECORD_TYPES:
            rt_table_name = f"RT_{record_id}"
            rt_schema = f'''        CREATE TABLE IF NOT EXISTS {rt_table_name} (
{column_defs_str}

            {primary_key}
        )'''
            schemas[rt_table_name] = rt_schema

    return schemas


def update_schema_file(schemas):
    """Update src/database/schema.py with all schemas."""
    schema_code = '''"""Database schema manager for JLTSQL.

This module provides schema definitions and table creation management.
Auto-generated from JV-Data format definitions.
"""

from typing import Dict, List

from src.database.base import BaseDatabase
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Table schema definitions based on JV-Data specification
SCHEMAS = {
'''

    for table_name, create_sql in sorted(schemas.items()):
        schema_code += f'    "{table_name}": """\n{create_sql}\n    """,\n'

    schema_code += '''}


class SchemaManager:
    """Schema manager for database tables."""

    def __init__(self, database: BaseDatabase):
        """Initialize schema manager.

        Args:
            database: Database instance
        """
        self.database = database
        logger.info("SchemaManager initialized")

    def create_table(self, table_name: str) -> bool:
        """Create a single table.

        Args:
            table_name: Name of table to create

        Returns:
            True if successful, False otherwise
        """
        if table_name not in SCHEMAS:
            logger.error(f"Unknown table: {table_name}")
            return False

        try:
            self.database.execute(SCHEMAS[table_name])
            logger.info(f"Created table: {table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False

    def create_all_tables(self) -> Dict[str, bool]:
        """Create all tables.

        Returns:
            Dictionary mapping table names to creation status
        """
        results = {}
        for table_name in SCHEMAS.keys():
            results[table_name] = self.create_table(table_name)

        created_count = sum(1 for success in results.values() if success)
        logger.info(f"Created {created_count}/{len(SCHEMAS)} tables", results=results)

        return results

    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables.

        Returns:
            List of table names that exist in database
        """
        existing = []
        for table_name in SCHEMAS.keys():
            if self.database.table_exists(table_name):
                existing.append(table_name)
        return existing

    def get_missing_tables(self) -> List[str]:
        """Get list of missing tables.

        Returns:
            List of table names that don't exist in database
        """
        missing = []
        for table_name in SCHEMAS.keys():
            if not self.database.table_exists(table_name):
                missing.append(table_name)
        return missing
'''

    with open('src/database/schema.py', 'w', encoding='utf-8') as f:
        f.write(schema_code)

    print(f'Updated: src/database/schema.py with {len(schemas)} schemas')


def main():
    """Main function."""
    print('=' * 70)
    print('JV-Data Parser and Schema Generator')
    print('=' * 70)
    print()

    # Load format definitions
    print('Loading format definitions...')
    formats = load_format_definitions()
    print(f'Loaded {len(formats)} record types')
    print()

    # Generate parsers
    print('Generating parsers...')
    parser_files = generate_all_parsers(formats)
    print(f'Generated {len(parser_files)} parser files')
    print()

    # Generate schemas
    print('Generating schemas...')
    schemas = generate_schema_definitions(formats)
    print(f'Generated {len(schemas)} table schemas')
    print()

    # Update schema file
    print('Updating schema.py...')
    update_schema_file(schemas)
    print()

    print('=' * 70)
    print('Generation complete!')
    print('=' * 70)
    print()
    print(f'Generated files:')
    print(f'  - {len(parser_files)} parser files in src/parser/')
    print(f'  - Updated src/database/schema.py with {len(schemas)} schemas')
    print()


if __name__ == '__main__':
    main()
