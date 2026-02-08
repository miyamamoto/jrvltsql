#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract real JRA records from SQLite DB and reconstruct raw cp932 byte fixtures.

Reads parsed field values from keiba.db, places them back at their byte positions
to reconstruct raw records suitable for parser testing.

Usage (on A6):
    venv32\\Scripts\\python.exe scripts/extract_fixtures_from_db.py --db data/keiba.db --output tests/fixtures/jra
"""

import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_parser_info(parser_file):
    """Extract field definitions and record length from parser source."""
    with open(parser_file, 'r', encoding='utf-8') as f:
        content = f.read()

    fields = []
    for m in re.finditer(r'result\["(\w+)"\]\s*=\s*self\.decode_field\(data\[(\d+):(\d+)\]\)', content):
        fields.append((m.group(1), int(m.group(2)), int(m.group(3))))

    m = re.search(r'RECORD_LENGTH\s*=\s*(\d+)', content)
    record_length = int(m.group(1)) if m else None

    return fields, record_length


def get_column_types(conn, table):
    """Get column name -> type mapping from table schema."""
    rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
    return {r[1]: r[2] for r in rows}


def format_value(value, field_width, col_type):
    """Format a value for placement in raw record, respecting original encoding."""
    if value is None:
        return ' ' * field_width

    if col_type == 'INTEGER':
        # Zero-pad integers to field width
        return str(int(value)).zfill(field_width)
    elif col_type in ('REAL', 'NUMERIC'):
        return str(value).rjust(field_width)
    else:
        return str(value)


def reconstruct_record(row, fields, record_length, col_types):
    """Reconstruct a raw cp932 record from parsed field values."""
    buf = bytearray(b' ' * record_length)

    for name, start, end in fields:
        field_len = end - start
        col_type = col_types.get(name, 'TEXT')
        value = format_value(row.get(name, ''), field_len, col_type)

        try:
            encoded = value.encode('cp932')
        except (UnicodeEncodeError, UnicodeDecodeError):
            encoded = value.encode('cp932', errors='replace')

        # For TEXT fields, right-pad; for numeric, left-pad (already handled by format_value)
        if len(encoded) > field_len:
            encoded = encoded[:field_len]
        elif len(encoded) < field_len:
            encoded = encoded + b' ' * (field_len - len(encoded))

        buf[start:end] = encoded

    # CRLF at end
    if record_length >= 2:
        buf[-2:] = b'\r\n'

    return bytes(buf)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='data/keiba.db')
    parser.add_argument('--output', default='tests/fixtures/jra')
    parser.add_argument('--count', type=int, default=3)
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    parsers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'parser')
    skip_types = {'HA', 'NC', 'NU', 'RT_RC'}
    results = {}

    for fname in sorted(os.listdir(parsers_dir)):
        if not fname.endswith('_parser.py') or fname == 'base.py':
            continue

        rt = fname.replace('_parser.py', '').upper()
        if rt in skip_types:
            continue

        fields, record_length = extract_parser_info(os.path.join(parsers_dir, fname))
        if not fields or not record_length:
            print(f"  SKIP {rt}: no extractable fields or record_length")
            continue

        # Find table
        table = None
        for prefix in ['NL_', 'RT_']:
            try:
                conn.execute(f'SELECT 1 FROM {prefix}{rt} LIMIT 1')
                table = f'{prefix}{rt}'
                break
            except sqlite3.OperationalError:
                continue
        if not table:
            print(f"  SKIP {rt}: no table found")
            continue

        col_types = get_column_types(conn, table)

        # Get recent data preferentially
        cols = list(col_types.keys())
        if 'Year' in cols:
            rows = [dict(r) for r in conn.execute(
                f'SELECT * FROM {table} WHERE Year >= 2024 LIMIT {args.count}').fetchall()]
            if not rows:
                rows = [dict(r) for r in conn.execute(
                    f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT {args.count}').fetchall()]
        elif 'MakeDate' in cols:
            rows = [dict(r) for r in conn.execute(
                f'SELECT * FROM {table} WHERE MakeDate >= "20240101" LIMIT {args.count}').fetchall()]
            if not rows:
                rows = [dict(r) for r in conn.execute(
                    f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT {args.count}').fetchall()]
        else:
            rows = [dict(r) for r in conn.execute(
                f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT {args.count}').fetchall()]

        if not rows:
            print(f"  SKIP {rt}: no data")
            continue

        outfile = os.path.join(args.output, f'{rt.lower()}_records.bin')
        with open(outfile, 'wb') as f:
            for row in rows:
                raw = reconstruct_record(row, fields, record_length, col_types)
                f.write(raw)

        results[rt] = len(rows)
        # Show a sample field for verification
        sample = rows[0]
        info = f"Year={sample.get('Year','?')}" if 'Year' in sample else f"MakeDate={sample.get('MakeDate','?')}"
        print(f"  {rt}: {len(rows)} records ({info}) -> {outfile}")

    conn.close()
    print(f"\nExtracted {len(results)} types, {sum(results.values())} records total")


if __name__ == '__main__':
    main()
