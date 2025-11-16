#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick database statistics check"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.duckdb_handler import DuckDBDatabase
from src.database.schema import SCHEMAS

db = DuckDBDatabase({'path': './data/jltsql.duckdb'})
db.connect()

try:
    print('=' * 80)
    print('データベース統計')
    print('=' * 80)
    print(f"{'Table':30} {'Records':>10}")
    print('-' * 42)

    total = 0
    tables_with_data = 0

    for table_name in sorted(SCHEMAS.keys()):
        result = db.fetch_one(f'SELECT COUNT(*) as count FROM "{table_name}"')
        count = result['count'] if result else 0
        if count > 0:
            print(f'{table_name:30} {count:10,}')
            total += count
            tables_with_data += 1

    print('-' * 42)
    print(f"{'合計':30} {total:10,}")
    print(f'\nデータを持つテーブル: {tables_with_data}/{len(SCHEMAS)}')
finally:
    db.disconnect()
