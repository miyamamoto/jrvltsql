#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test parser fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.parser.factory import ParserFactory

def test_parser_fix():
    """Test that parsers can be created successfully."""
    factory = ParserFactory()

    test_types = ['RA', 'SE', 'HR', 'JG', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6']

    print("Testing parser creation...")
    print("-" * 60)

    success = 0
    failed = 0

    for record_type in test_types:
        try:
            parser = factory.get_parser(record_type)
            if parser:
                print(f"  {record_type}: OK - {len(parser._fields)} fields")
                success += 1
            else:
                print(f"  {record_type}: NOT FOUND")
                failed += 1
        except Exception as e:
            print(f"  {record_type}: ERROR - {e}")
            failed += 1

    print("-" * 60)
    print(f"Success: {success}/{len(test_types)}")
    print(f"Failed:  {failed}/{len(test_types)}")

    return success == len(test_types)

if __name__ == "__main__":
    success = test_parser_fix()
    sys.exit(0 if success else 1)
