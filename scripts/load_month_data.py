#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Load one month of JRA-VAN data into databases (test script).

Quick test script to load one month of data before running full year import.

Usage:
    python scripts/load_month_data.py --year 2024 --month 1 --db sqlite
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.database.sqlite_handler import SQLiteDatabase
from src.database.duckdb_handler import DuckDBDatabase
from src.database.schema import SchemaManager
from src.database.indexes import IndexManager
from src.importer.batch import BatchProcessor
from src.utils.logger import setup_logging
import os
from dotenv import load_dotenv

console = Console()


def format_date(year, month, day):
    """Format date as YYYYMMDD string."""
    return f"{year:04d}{month:02d}{day:02d}"


@click.command()
@click.option("--year", type=int, default=2024, help="Year (default: 2024)")
@click.option("--month", type=int, default=1, help="Month (default: 1)")
@click.option(
    "--db",
    type=click.Choice(["sqlite", "duckdb", "all"]),
    default="sqlite",
    help="Database type (default: sqlite)"
)
@click.option("--spec", "data_spec", default="RACE", help="Data spec (default: RACE)")
@click.option("--create-indexes/--no-indexes", default=True, help="Create indexes (default: True)")
def main(year, month, db, data_spec, create_indexes):
    """Load one month of data for testing."""
    setup_logging(level="INFO")
    load_dotenv()

    console.print(f"\n[bold cyan]Test Import: {year}/{month:02d} data[/bold cyan]\n")

    # Determine databases
    databases = ["sqlite", "duckdb"] if db == "all" else [db]

    for db_type in databases:
        console.print(f"\n[bold]Processing {db_type.upper()}...[/bold]")

        # Setup database
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        if db_type == "sqlite":
            db_path = data_dir / f"test_{year}{month:02d}.db"
            database = SQLiteDatabase({"path": str(db_path)})
        else:
            db_path = data_dir / f"test_{year}{month:02d}.duckdb"
            database = DuckDBDatabase({"path": str(db_path)})

        console.print(f"Database: {db_path}")

        try:
            with database:
                # Create tables
                console.print("Creating tables...")
                schema_mgr = SchemaManager(database)
                results = schema_mgr.create_all_tables()
                tables_created = sum(1 for success in results.values() if success)
                console.print(f"[green]OK[/green] Created {tables_created} tables")

                # Create indexes
                if create_indexes:
                    console.print("Creating indexes...")
                    index_mgr = IndexManager(database)
                    index_results = index_mgr.create_all_indexes()
                    indexes_created = sum(index_results.values())
                    console.print(f"[green]OK[/green] Created {indexes_created} indexes")

                # Import data
                console.print(f"Importing {year}/{month:02d} data...")

                sid = os.getenv("JVLINK_SID", "JLTSQL")
                processor = BatchProcessor(database=database, sid=sid, batch_size=1000)

                # Calculate date range for the month
                from_date = format_date(year, month, 1)
                # Last day of month
                if month == 12:
                    to_date = format_date(year, month, 31)
                else:
                    import calendar
                    last_day = calendar.monthrange(year, month)[1]
                    to_date = format_date(year, month, last_day)

                console.print(f"Date range: {from_date} → {to_date}")

                result = processor.process_date_range(
                    data_spec=data_spec,
                    from_date=from_date,
                    to_date=to_date,
                    option=1  # Setup mode to download initial data
                )

                console.print("\n[bold green]OK - Import complete![/bold green]")
                console.print(f"  Fetched:  {result.get('fetched', 0):,}")
                console.print(f"  Parsed:   {result.get('parsed', 0):,}")
                console.print(f"  Imported: {result.get('imported', 0):,}")
                console.print(f"  Failed:   {result.get('failed', 0):,}")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            import traceback
            console.print(traceback.format_exc())

    console.print("\n[bold green]Done![/bold green]\n")


if __name__ == "__main__":
    main()
