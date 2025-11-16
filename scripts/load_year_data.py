#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Load one year of JRA-VAN data into databases.

This script fetches race data from JRA-VAN DataLab for a full year
and imports it into SQLite, DuckDB, and optionally PostgreSQL databases.

Usage:
    python scripts/load_year_data.py --year 2024 --db sqlite
    python scripts/load_year_data.py --year 2024 --db duckdb
    python scripts/load_year_data.py --year 2024 --db all
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.database.sqlite_handler import SQLiteDatabase
from src.database.duckdb_handler import DuckDBDatabase
from src.database.schema import create_all_tables
from src.database.indexes import IndexManager
from src.importer.batch import BatchProcessor
from src.utils.logger import get_logger, setup_logging

console = Console()
logger = get_logger(__name__)


def format_date(year, month, day):
    """Format date as YYYYMMDD string."""
    return f"{year:04d}{month:02d}{day:02d}"


def load_data_to_database(db_type, year, data_spec, create_indexes_flag, batch_size):
    """Load data into specified database.

    Args:
        db_type: Database type (sqlite, duckdb)
        year: Year to fetch data for
        data_spec: Data specification (RACE, DIFF, etc.)
        create_indexes_flag: Whether to create indexes
        batch_size: Batch size for imports

    Returns:
        Dictionary with statistics
    """
    start_time = time.time()

    # Database configuration
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    if db_type == "sqlite":
        db_path = data_dir / f"keiba_{year}.db"
        database = SQLiteDatabase({"path": str(db_path)})
    elif db_type == "duckdb":
        db_path = data_dir / f"keiba_{year}.duckdb"
        database = DuckDBDatabase({"path": str(db_path)})
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

    console.print(f"\n[bold cyan]Loading {year} data into {db_type.upper()}[/bold cyan]")
    console.print(f"Database: {db_path}")
    console.print(f"Data spec: {data_spec}")
    console.print()

    statistics = {
        "database": db_type,
        "year": year,
        "db_path": str(db_path),
        "tables_created": 0,
        "indexes_created": 0,
        "fetched": 0,
        "parsed": 0,
        "imported": 0,
        "failed": 0,
        "batches": 0,
        "duration_seconds": 0,
    }

    try:
        with database:
            # Step 1: Create tables
            console.print("[bold]Step 1: Creating tables...[/bold]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Creating tables...", total=None)
                create_all_tables(database)
                progress.update(task, description="[green]Tables created!")

            statistics["tables_created"] = 57  # 38 NL_* + 19 RT_*
            console.print(f"[green]OK[/green] Created {statistics['tables_created']} tables\n")

            # Step 2: Create indexes (if requested)
            if create_indexes_flag:
                console.print("[bold]Step 2: Creating indexes...[/bold]")
                index_manager = IndexManager(database)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Creating indexes...", total=None)
                    index_results = index_manager.create_all_indexes()
                    progress.update(task, description="[green]Indexes created!")

                statistics["indexes_created"] = sum(index_results.values())
                console.print(f"[green]OK[/green] Created {statistics['indexes_created']} indexes\n")
            else:
                console.print("[yellow]Skipping index creation (use --create-indexes to enable)[/yellow]\n")

            # Step 3: Fetch and import data
            console.print("[bold]Step 3: Fetching and importing data...[/bold]")
            console.print(f"Date range: {year}/01/01 → {year}/12/31")
            console.print()

            # Load service key from .env
            import os
            from dotenv import load_dotenv
            load_dotenv()

            sid = os.getenv("JVLINK_SID")
            if not sid:
                console.print("[yellow]Warning: JVLINK_SID not found in .env file[/yellow]")
                console.print("[yellow]Using default 'JLTSQL' as session ID[/yellow]")
                sid = "JLTSQL"

            # Create batch processor
            processor = BatchProcessor(
                database=database,
                sid=sid,
                batch_size=batch_size
            )

            # Process date range
            from_date = format_date(year, 1, 1)
            to_date = format_date(year, 12, 31)

            console.print("[bold cyan]Processing...[/bold cyan]")
            try:
                result = processor.process_date_range(
                    data_spec=data_spec,
                    from_date=from_date,
                    to_date=to_date
                )

                statistics.update({
                    "fetched": result.get("fetched", 0),
                    "parsed": result.get("parsed", 0),
                    "imported": result.get("imported", 0),
                    "failed": result.get("failed", 0),
                    "batches": result.get("batches", 0),
                })

                console.print()
                console.print("[bold green]OK - Import complete![/bold green]")

            except Exception as e:
                console.print(f"\n[red]Error during import:[/red] {e}")
                logger.error(f"Import failed: {e}", exc_info=True)
                statistics["error"] = str(e)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error(f"Failed to load data: {e}", exc_info=True)
        statistics["error"] = str(e)

    statistics["duration_seconds"] = time.time() - start_time

    return statistics


@click.command()
@click.option("--year", type=int, required=True, help="Year to fetch data for (e.g., 2024)")
@click.option(
    "--db",
    type=click.Choice(["sqlite", "duckdb", "all"]),
    default="duckdb",
    help="Database type to use (default: duckdb)"
)
@click.option(
    "--spec",
    "data_spec",
    default="RACE",
    help="Data specification (default: RACE)"
)
@click.option(
    "--create-indexes/--no-indexes",
    default=True,
    help="Create indexes after table creation (default: True)"
)
@click.option(
    "--batch-size",
    default=1000,
    help="Batch size for imports (default: 1000)"
)
def main(year, db, data_spec, create_indexes, batch_size):
    """Load one year of JRA-VAN data into database(s).

    \b
    Examples:
        python scripts/load_year_data.py --year 2024 --db sqlite
        python scripts/load_year_data.py --year 2024 --db duckdb
        python scripts/load_year_data.py --year 2024 --db all
        python scripts/load_year_data.py --year 2024 --db sqlite --no-indexes
    """
    setup_logging(level="INFO")

    console.print("\n[bold cyan]═══════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  JRA-VAN Data Import - Full Year Load   [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]\n")

    # Determine databases to process
    if db == "all":
        databases = ["sqlite", "duckdb"]
    else:
        databases = [db]

    all_statistics = []

    # Process each database
    for db_type in databases:
        try:
            stats = load_data_to_database(
                db_type=db_type,
                year=year,
                data_spec=data_spec,
                create_indexes_flag=create_indexes,
                batch_size=batch_size
            )
            all_statistics.append(stats)

            # Show individual database results
            console.print()
            console.print(f"[bold]Results for {db_type.upper()}:[/bold]")
            console.print(f"  Database:     {stats['db_path']}")
            console.print(f"  Tables:       {stats['tables_created']}")
            console.print(f"  Indexes:      {stats['indexes_created']}")
            console.print(f"  Fetched:      {stats['fetched']:,}")
            console.print(f"  Parsed:       {stats['parsed']:,}")
            console.print(f"  Imported:     {stats['imported']:,}")
            console.print(f"  Failed:       {stats['failed']:,}")
            console.print(f"  Batches:      {stats['batches']:,}")
            console.print(f"  Duration:     {stats['duration_seconds']:.1f}s")

            if "error" in stats:
                console.print(f"  [red]Error: {stats['error']}[/red]")

        except Exception as e:
            console.print(f"\n[red]Failed to process {db_type}:[/red] {e}")
            logger.error(f"Failed to process {db_type}: {e}", exc_info=True)

        console.print()

    # Summary table
    if len(all_statistics) > 1:
        console.print("\n[bold cyan]═══════════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]            Summary Report                 [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Database", style="cyan")
        table.add_column("Tables", justify="right")
        table.add_column("Indexes", justify="right")
        table.add_column("Imported", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Duration", justify="right")

        for stats in all_statistics:
            table.add_row(
                stats["database"].upper(),
                str(stats["tables_created"]),
                str(stats["indexes_created"]),
                f"{stats['imported']:,}",
                str(stats["failed"]),
                f"{stats['duration_seconds']:.1f}s"
            )

        console.print(table)

    console.print("\n[bold green]OK - All operations complete![/bold green]\n")


if __name__ == "__main__":
    main()
