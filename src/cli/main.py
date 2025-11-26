"""JLTSQL Command Line Interface."""

import sys
from pathlib import Path

import click
from rich.console import Console

from src.utils.config import ConfigError, load_config
from src.utils.logger import get_logger, setup_logging_from_config

# Version
__version__ = "0.1.0-alpha"

# Console for rich output (Windows cp932-safe)
console = Console(legacy_windows=True)
logger = get_logger(__name__)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file (default: config/config.yaml)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
@click.version_option(version=__version__, prog_name="jrvltsql")
@click.pass_context
def cli(ctx, config, verbose):
    """JRVLTSQL - JRA-VAN Link To SQL

    JRA-VAN DataLabの競馬データをSQLite/PostgreSQLに
    リアルタイムインポートするツール

    \b
    使用例:
      jrvltsql init                     # プロジェクト初期化
      jrvltsql fetch --from 2024-01-01  # データ取得
      jrvltsql monitor --daemon         # リアルタイム監視開始

    詳細: https://github.com/miyamamoto/jrvltsql
    """
    # Store context
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        config_path = config
    else:
        # Try default path
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"

        if not config_path.exists():
            # Config not found, use default for init command
            if ctx.invoked_subcommand != "init":
                console.print(
                    "[red]Error:[/red] Configuration file not found. "
                    "Run 'jltsql init' first.",
                    style="bold",
                )
                sys.exit(1)
            else:
                config_path = None

    if config_path:
        try:
            cfg = load_config(str(config_path))
            ctx.obj["config"] = cfg

            # Setup logging from config
            setup_logging_from_config(cfg.to_dict())

            # Override log level if verbose
            if verbose:
                from src.utils.logger import setup_logging

                setup_logging(level="DEBUG")

            logger.info("Configuration loaded", config_path=str(config_path))

        except ConfigError as e:
            console.print(f"[red]Configuration Error:[/red] {e}", style="bold")
            sys.exit(1)
    else:
        ctx.obj["config"] = None


@cli.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force overwrite existing configuration",
)
@click.pass_context
def init(ctx, force):
    """Initialize JLTSQL project.

    Creates configuration files and database directories.
    """
    console.print("[bold cyan]Initializing JLTSQL project...[/bold cyan]")

    project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "config"
    data_dir = project_root / "data"
    logs_dir = project_root / "logs"

    # Create directories
    for directory in [config_dir, data_dir, logs_dir]:
        if not directory.exists():
            directory.mkdir(parents=True)
            console.print(f"[green]+[/green] Created directory: {directory}")
        else:
            console.print(f"  Directory exists: {directory}")

    # Create config.yaml from example
    config_example = config_dir / "config.yaml.example"
    config_yaml = config_dir / "config.yaml"

    if config_yaml.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] {config_yaml} already exists. "
            "Use --force to overwrite."
        )
    else:
        if config_example.exists():
            import shutil

            shutil.copy(config_example, config_yaml)
            console.print(f"[green]+[/green] Created configuration file: {config_yaml}")
        else:
            console.print(
                f"[red]Error:[/red] {config_example} not found.",
                style="bold",
            )
            sys.exit(1)

    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Edit config/config.yaml and set your JV-Link service key")
    console.print("  2. Run: jltsql fetch --help")


@cli.command()
def status():
    """Show JLTSQL status."""
    console.print("[bold cyan]JLTSQL Status[/bold cyan]")
    console.print(f"Version: {__version__}")
    console.print("Status: [green]Ready[/green]")


@cli.command()
def version():
    """Show version information."""
    console.print(f"JLTSQL version {__version__}")
    console.print("Python version: " + sys.version.split()[0])


@cli.command()
@click.option("--from", "date_from", required=True, help="Start date (YYYYMMDD)")
@click.option("--to", "date_to", required=True, help="End date (YYYYMMDD)")
@click.option("--spec", "data_spec", required=True, help="Data specification (RACE, DIFF, etc.)")
@click.option("--option", "jv_option", type=int, default=1, help="JVOpen option: 0=normal, 1=setup (default), 2=update")
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.option("--batch-size", default=1000, help="Batch size for imports (default: 1000)")
@click.pass_context
def fetch(ctx, date_from, date_to, data_spec, jv_option, db, batch_size):
    """Fetch historical data from JRA-VAN DataLab.

    \b
    Examples:
      jltsql fetch --from 20240101 --to 20241231 --spec RACE
      jltsql fetch --from 20240101 --to 20241231 --spec DIFF
    """
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase
    from src.database.schema import create_all_tables
    from src.importer.batch import BatchProcessor

    config = ctx.obj.get("config")
    if not config and not db:
        console.print("[red]Error:[/red] No configuration found. Run 'jltsql init' first or use --db option.")
        sys.exit(1)

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print(f"[bold cyan]Fetching historical data from JRA-VAN...[/bold cyan]\n")
    console.print(f"  Date range: {date_from} -- {date_to}")
    console.print(f"  Data spec:  {data_spec}")
    console.print(f"  Database:   {db_type}")
    console.print()

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Connect to database
        with database:
            # Ensure tables exist
            try:
                create_all_tables(database)
            except Exception:
                # Tables might already exist, that's OK
                pass

            # Process data
            processor = BatchProcessor(
                database=database,
                sid=config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL",
                batch_size=batch_size,
                service_key=config.get("jvlink.service_key") if config else None
            )

            console.print("[bold]Processing data...[/bold]")

            result = processor.process_date_range(
                data_spec=data_spec,
                from_date=date_from,
                to_date=date_to,
                option=jv_option
            )

            # Show results
            console.print()
            console.print("[bold green][OK] Fetch complete![/bold green]")
            console.print()
            console.print("[bold]Statistics:[/bold]")
            console.print(f"  Fetched:  {result['records_fetched']}")
            console.print(f"  Parsed:   {result['records_parsed']}")
            console.print(f"  Imported: {result['records_imported']}")
            console.print(f"  Failed:   {result['records_failed']}")
            console.print(f"  Batches:  {result.get('batches_processed', 0)}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to fetch data", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--daemon", is_flag=True, help="Run in background")
@click.option("--spec", "data_spec", default="RACE", help="Data specification (default: RACE)")
@click.option("--interval", default=60, help="Polling interval in seconds (default: 60)")
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.pass_context
def monitor(ctx, daemon, data_spec, interval, db):
    """Start real-time monitoring.

    \b
    Examples:
      jltsql monitor                        # Run in foreground
      jltsql monitor --daemon               # Run in background
      jltsql monitor --spec RACE --interval 30
    """
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase
    from src.database.schema import create_all_tables
    from src.realtime.monitor import RealtimeMonitor

    config = ctx.obj.get("config")
    if not config and not db:
        console.print("[red]Error:[/red] No configuration found. Run 'jltsql init' first or use --db option.")
        sys.exit(1)

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print(f"[bold cyan]Starting real-time monitoring...[/bold cyan]\n")
    console.print(f"  Data spec:  {data_spec}")
    console.print(f"  Interval:   {interval}s")
    console.print(f"  Database:   {db_type}")
    console.print(f"  Mode:       {'daemon' if daemon else 'foreground'}")
    console.print()

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Connect to database
        with database:
            # Ensure tables exist
            try:
                create_all_tables(database)
            except Exception:
                # Tables might already exist, that's OK
                pass

            # Start monitoring
            monitor_obj = RealtimeMonitor(
                database=database,
                data_spec=data_spec,
                polling_interval=interval,
                sid=config.jvlink.get("sid", "JLTSQL") if config else "JLTSQL"
            )

            console.print("[bold green]Monitoring started![/bold green]")
            console.print("Press Ctrl+C to stop.\n")

            # Start in daemon or foreground mode
            monitor_obj.start(daemon=daemon)

            if daemon:
                console.print("\n[bold green]Monitoring running in background[/bold green]")
                status = monitor_obj.get_status()
                console.print(f"Started at: {status['started_at']}")
            else:
                # Foreground mode - wait for Ctrl+C
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopping monitor...[/yellow]")
                    monitor_obj.stop()
                    console.print("[green]Monitor stopped.[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to start monitoring", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop real-time monitoring."""
    console.print("[yellow]Note: This command is not yet implemented.[/yellow]")
    console.print("Would stop monitoring")


@cli.command()
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.option("--all", "create_all", is_flag=True, help="Create both NL_ and RT_ tables")
@click.option("--nl-only", is_flag=True, help="Create only NL_ (Normal Load) tables")
@click.option("--rt-only", is_flag=True, help="Create only RT_ (Real-Time) tables")
@click.pass_context
def create_tables(ctx, db, create_all, nl_only, rt_only):
    """Create database tables.

    \b
    Examples:
      jltsql create-tables                # Create all tables (from config)
      jltsql create-tables --db sqlite    # Create all tables in SQLite
      jltsql create-tables --nl-only      # Create only NL_* tables
      jltsql create-tables --rt-only      # Create only RT_* tables
    """
    from rich.progress import Progress, TextColumn
    from src.database.schema import SCHEMAS, create_all_tables
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase

    config = ctx.obj.get("config")
    if not config and not db:
        console.print("[red]Error:[/red] No configuration found. Run 'jltsql init' first or use --db option.")
        sys.exit(1)

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print(f"[bold cyan]Creating database tables ({db_type})...[/bold cyan]\n")

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Connect to database
        with database:
            # Determine which tables to create
            if nl_only:
                tables_to_create = {name: sql for name, sql in SCHEMAS.items() if name.startswith("NL_")}
            elif rt_only:
                tables_to_create = {name: sql for name, sql in SCHEMAS.items() if name.startswith("RT_")}
            else:
                tables_to_create = SCHEMAS

            # Create tables with progress bar
            created_count = 0
            failed_count = 0

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Creating {len(tables_to_create)} tables...", total=len(tables_to_create))

                for table_name, schema_sql in tables_to_create.items():
                    progress.update(task, description=f"[cyan]Creating {table_name}...")

                    try:
                        database.execute(schema_sql)
                        created_count += 1
                    except Exception as e:
                        console.print(f"[yellow]Warning:[/yellow] Failed to create {table_name}: {e}")
                        failed_count += 1

                    progress.advance(task)

            # Show results
            console.print()
            console.print(f"[green][OK][/green] Created {created_count} tables")
            if failed_count > 0:
                console.print(f"[yellow][!!][/yellow] Failed to create {failed_count} tables")

            # Show table statistics
            nl_tables = len([n for n in tables_to_create if n.startswith("NL_")])
            rt_tables = len([n for n in tables_to_create if n.startswith("RT_")])

            console.print()
            console.print("[bold]Table Statistics:[/bold]")
            console.print(f"  NL_* tables (Normal Load): {nl_tables}")
            console.print(f"  RT_* tables (Real-Time):   {rt_tables}")
            console.print(f"  Total:                     {len(tables_to_create)}")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to create tables", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.option("--table", help="Create indexes for specific table only")
@click.pass_context
def create_indexes(ctx, db, table):
    """Create database indexes for improved query performance.

    \b
    Creates optimized indexes on frequently queried columns:
    - Date fields (開催年月日, データ作成年月日)
    - Venue/Race fields (競馬場コード, レース番号)
    - Real-time fields (発表月日時分)
    - Composite indexes for JOIN optimization

    \b
    Examples:
      jltsql create-indexes                    # Create all indexes
      jltsql create-indexes --db sqlite        # Create indexes in SQLite
      jltsql create-indexes --table NL_RA      # Create indexes for NL_RA only
    """
    from src.database.indexes import IndexManager
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase

    config = ctx.obj.get("config")
    if not config and not db:
        console.print("[red]Error:[/red] No configuration found. Run 'jltsql init' first or use --db option.")
        sys.exit(1)

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print(f"[bold cyan]Creating database indexes ({db_type})...[/bold cyan]\n")

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Connect to database
        with database:
            index_manager = IndexManager(database)

            # Create indexes for specific table or all tables
            if table:
                console.print(f"Creating indexes for table: {table}")
                result = index_manager.create_indexes(table)

                if result:
                    index_count = index_manager.get_index_count(table)
                    console.print(f"[green][OK][/green] Created {index_count} indexes for {table}")
                else:
                    console.print(f"[red][NG][/red] Failed to create indexes for {table}")
                    sys.exit(1)
            else:
                console.print("Creating indexes for all tables...")
                console.print("[cyan]Creating indexes...[/cyan]")

                results = index_manager.create_all_indexes()

                console.print("[green]Indexes created![/green]")

                # Show results
                total_indexes = sum(results.values())
                total_tables = len(results)

                console.print()
                console.print(f"[green][OK][/green] Created {total_indexes} indexes across {total_tables} tables")

                # Show breakdown
                console.print()
                console.print("[bold]Index Statistics:[/bold]")
                nl_indexes = sum(count for table, count in results.items() if table.startswith("NL_"))
                rt_indexes = sum(count for table, count in results.items() if table.startswith("RT_"))

                console.print(f"  NL_* tables: {nl_indexes} indexes")
                console.print(f"  RT_* tables: {rt_indexes} indexes")
                console.print(f"  Total:       {total_indexes} indexes")

                console.print()
                console.print("[dim]Note: Indexes improve query performance for date ranges,[/dim]")
                console.print("[dim]      venue/race searches, and real-time data queries.[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to create indexes", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--table", required=True, help="Table name to export")
@click.option("--format", "output_format", type=click.Choice(["csv", "json", "parquet"]), default="csv", help="Output format (default: csv)")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path")
@click.option("--where", help="SQL WHERE clause (e.g., '開催年月日 >= 20240101')")
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.pass_context
def export(ctx, table, output_format, output, where, db):
    """Export data from database to file.

    \b
    Supports multiple output formats:
    - CSV: Comma-separated values
    - JSON: JSON array of records
    - Parquet: Apache Parquet columnar format

    \b
    Examples:
      jltsql export --table NL_RA --output races.csv
      jltsql export --table NL_SE --format json --output horses.json
      jltsql export --table NL_RA --where "開催年月日 >= 20240101" --output 2024_races.csv
      jltsql export --table NL_HR --format parquet --output payouts.parquet
    """
    from pathlib import Path
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase

    config = ctx.obj.get("config")
    if not config and not db:
        console.print("[red]Error:[/red] No configuration found. Run 'jltsql init' first or use --db option.")
        sys.exit(1)

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print(f"[bold cyan]Exporting data from {table}...[/bold cyan]\n")
    console.print(f"  Database:      {db_type}")
    console.print(f"  Format:        {output_format}")
    console.print(f"  Output:        {output}")
    if where:
        console.print(f"  WHERE clause:  {where}")
    console.print()

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Connect and export
        with database:
            # Check table exists
            if not database.table_exists(table):
                console.print(f"[red]Error:[/red] Table '{table}' does not exist.")
                sys.exit(1)

            # Build query
            sql = f"SELECT * FROM {table}"
            if where:
                sql += f" WHERE {where}"

            console.print(f"[dim]Executing: {sql}[/dim]\n")

            # Fetch data
            from rich.progress import Progress, TextColumn
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Fetching data...", total=None)
                rows = database.fetch_all(sql)
                progress.update(task, description=f"[green]Fetched {len(rows)} rows")

            if not rows:
                console.print("[yellow]Warning:[/yellow] No data found.")
                sys.exit(0)

            # Export based on format
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_format == "csv":
                import csv
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    if rows:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)

            elif output_format == "json":
                import json
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False, indent=2)

            elif output_format == "parquet":
                try:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    df.to_parquet(output_path, index=False)
                except ImportError:
                    console.print("[red]Error:[/red] Parquet export requires pandas and pyarrow.")
                    console.print("Install with: pip install pandas pyarrow")
                    sys.exit(1)

            # Show results
            console.print()
            console.print(f"[bold green][OK] Export complete![/bold green]")
            console.print()
            console.print(f"  Records exported: {len(rows):,}")
            console.print(f"  Output file:      {output_path.absolute()}")
            console.print(f"  File size:        {output_path.stat().st_size:,} bytes")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to export data", error=str(e), exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--set", "set_value", help="Set configuration value (format: key=value)")
@click.option("--get", "get_key", help="Get configuration value")
@click.pass_context
def config(ctx, show, set_value, get_key):
    """Manage JLTSQL configuration.

    \b
    Examples:
      jltsql config --show                       # Show all settings
      jltsql config --get database.type          # Get specific value
      jltsql config --set database.type=sqlite    # Set value (not implemented yet)
    """
    from pathlib import Path
    import yaml

    # Find config file
    if ctx.obj.get("config"):
        config_obj = ctx.obj["config"]
        config_dict = config_obj.to_dict()
        config_path = Path(ctx.params.get("config", "config/config.yaml"))
    else:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"

        if not config_path.exists():
            console.print("[red]Error:[/red] Configuration file not found.")
            console.print("Run 'jltsql init' first.")
            sys.exit(1)

        # Load config manually
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

    # Show all configuration
    if show or (not set_value and not get_key):
        console.print(f"[bold cyan]Configuration ({config_path})[/bold cyan]\n")

        # Pretty print config
        from rich.tree import Tree
        tree = Tree("JLTSQL Configuration")

        # JV-Link section
        jvlink_tree = tree.add("JV-Link")
        jvlink_config = config_dict.get("jvlink", {})
        jvlink_tree.add(f"SID: {jvlink_config.get('sid', 'N/A')}")
        jvlink_tree.add(f"Service Key: {'*' * 20 if jvlink_config.get('service_key') else 'Not set'}")

        # Database section
        db_tree = tree.add("Database")
        db_config = config_dict.get("database", {})
        db_tree.add(f"Type: {db_config.get('type', 'N/A')}")
        if db_config.get("path"):
            db_tree.add(f"Path: {db_config.get('path')}")
        if db_config.get("host"):
            db_tree.add(f"Host: {db_config.get('host')}")
            db_tree.add(f"Port: {db_config.get('port', 5432)}")
            db_tree.add(f"Database: {db_config.get('database', 'N/A')}")
            db_tree.add(f"User: {db_config.get('user', 'N/A')}")

        # Logging section
        log_tree = tree.add("Logging")
        log_config = config_dict.get("logging", {})
        log_tree.add(f"Level: {log_config.get('level', 'INFO')}")
        log_tree.add(f"File: {log_config.get('file', 'logs/jltsql.log')}")

        console.print(tree)
        console.print()

    # Get specific value
    elif get_key:
        keys = get_key.split(".")
        value = config_dict
        try:
            for key in keys:
                value = value[key]
            console.print(f"{get_key}: {value}")
        except KeyError:
            console.print(f"[red]Error:[/red] Key '{get_key}' not found in configuration.")
            sys.exit(1)

    # Set value (future implementation)
    elif set_value:
        console.print("[yellow]Note:[/yellow] Configuration modification via CLI is not yet implemented.")
        console.print(f"Please edit {config_path} manually.")
        console.print()
        console.print(f"You wanted to set: {set_value}")


@cli.group()
def realtime():
    """Realtime data monitoring commands.

    \b
    Manage realtime data streams from JV-Link for up-to-the-minute
    race results, odds, payouts, and other breaking news data.

    \b
    Examples:
      jltsql realtime start --specs 0B12,0B15    # Monitor race results and payouts
      jltsql realtime status                      # Check monitoring status
      jltsql realtime stop                        # Stop monitoring
      jltsql realtime specs                       # List available data specs
    """
    pass


@realtime.command()
@click.option(
    "--specs",
    default="0B12",
    help="Comma-separated data specs to monitor (default: 0B12)"
)
@click.option(
    "--db",
    type=click.Choice(["sqlite", "postgresql"]),
    default=None,
    help="Database type (default: from config)"
)
@click.option(
    "--batch-size",
    default=100,
    help="Batch size for imports (default: 100)"
)
@click.option(
    "--no-create-tables",
    is_flag=True,
    help="Don't auto-create missing tables"
)
@click.pass_context
def start(ctx, specs, db, batch_size, no_create_tables):
    """Start realtime monitoring service.

    \b
    This command starts background threads that continuously monitor
    JV-Link realtime data streams and automatically import new data
    as it arrives.

    \b
    Common data specs:
      0B12 - Race results (default)
      0B15 - Payouts
      0B31 - Odds
      0B33 - Horse numbers
      0B35 - Weather/track conditions

    \b
    Examples:
      jltsql realtime start
      jltsql realtime start --specs 0B12,0B15
      jltsql realtime start --specs 0B12 --db sqlite
    """
    from src.database.sqlite_handler import SQLiteDatabase
    from src.database.postgresql_handler import PostgreSQLDatabase
    from src.services.realtime_monitor import RealtimeMonitor

    config = ctx.obj.get("config")
    if not config and not db:
        console.print(
            "[red]Error:[/red] No configuration found. "
            "Run 'jltsql init' first or use --db option."
        )
        sys.exit(1)

    # Parse data specs
    data_specs = [spec.strip() for spec in specs.split(",")]

    # Determine database type
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite")

    console.print("[bold cyan]Starting realtime monitoring service...[/bold cyan]\n")
    console.print(f"  Data specs:    {', '.join(data_specs)}")
    console.print(f"  Database:      {db_type}")
    console.print(f"  Batch size:    {batch_size}")
    console.print(f"  Auto-create:   {'No' if no_create_tables else 'Yes'}")
    console.print()

    try:
        # Initialize database
        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                console.print("[red]Error:[/red] PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            console.print(f"[red]Error:[/red] Unsupported database type: {db_type}")
            sys.exit(1)

        # Create monitor
        monitor = RealtimeMonitor(
            database=database,
            data_specs=data_specs,
            sid=config.jvlink.get("sid", "JLTSQL") if config else "JLTSQL",
            batch_size=batch_size,
            auto_create_tables=not no_create_tables
        )

        # Start monitoring
        if monitor.start():
            console.print("[bold green][OK] Monitoring service started![/bold green]\n")

            status = monitor.get_status()
            console.print("[bold]Status:[/bold]")
            console.print(f"  Running:        Yes")
            console.print(f"  Started at:     {status['started_at']}")
            console.print(f"  Monitored specs: {', '.join(status['monitored_specs'])}")
            console.print()
            console.print("[dim]Use 'jltsql realtime status' to check progress[/dim]")
            console.print("[dim]Use 'jltsql realtime stop' to stop monitoring[/dim]")

            # Keep monitoring in foreground
            console.print("\nPress Ctrl+C to stop...\n")
            try:
                import time
                while monitor.status.is_running:
                    time.sleep(2)
                    # Periodically show stats
                    status = monitor.get_status()
                    console.print(
                        f"\rImported: {status['records_imported']:,} | "
                        f"Failed: {status['records_failed']:,} | "
                        f"Uptime: {status['uptime_seconds']:.0f}s",
                        end=""
                    )
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Stopping monitoring...[/yellow]")
                monitor.stop()
                console.print("[green][OK] Monitoring stopped[/green]")

        else:
            console.print("[red][NG] Failed to start monitoring service[/red]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to start realtime monitoring", error=str(e), exc_info=True)
        sys.exit(1)


@realtime.command()
@click.pass_context
def status(ctx):
    """Show realtime monitoring status.

    Displays current status of the monitoring service including:
    - Running state
    - Uptime
    - Records imported
    - Errors
    - Monitored data specs
    """
    console.print("[yellow]Note:[/yellow] Status tracking not yet implemented.")
    console.print()
    console.print("To implement persistent status tracking, the monitor needs to:")
    console.print("  1. Save status to a shared location (e.g., file or Redis)")
    console.print("  2. Support inter-process communication")
    console.print()
    console.print("For now, check the logs at: logs/jltsql.log")


@realtime.command()
@click.pass_context
def stop(ctx):
    """Stop realtime monitoring service.

    Gracefully stops all monitoring threads and closes database connections.
    """
    console.print("[yellow]Note:[/yellow] Stop command not yet implemented.")
    console.print()
    console.print("To implement stop functionality, the monitor needs to:")
    console.print("  1. Save process ID (PID) when starting")
    console.print("  2. Support inter-process signaling")
    console.print()
    console.print("For now, use Ctrl+C to stop the monitoring process.")


@realtime.command()
def specs():
    """List available realtime data specification codes.

    Shows all JV-Link realtime data specs with descriptions.
    """
    from src.fetcher.realtime import RealtimeFetcher

    specs_dict = RealtimeFetcher.list_data_specs()

    console.print("[bold cyan]Available Realtime Data Specs[/bold cyan]\n")

    # Group by category
    race_specs = {}
    master_specs = {}
    odds_specs = {}
    other_specs = {}

    for code, desc in specs_dict.items():
        if "レース" in desc or "払戻" in desc:
            race_specs[code] = desc
        elif "マスタ" in desc:
            master_specs[code] = desc
        elif "オッズ" in desc:
            odds_specs[code] = desc
        else:
            other_specs[code] = desc

    # Display grouped
    if race_specs:
        console.print("[bold]Race Data:[/bold]")
        for code, desc in sorted(race_specs.items()):
            console.print(f"  [cyan]{code}[/cyan] - {desc}")
        console.print()

    if odds_specs:
        console.print("[bold]Odds Data:[/bold]")
        for code, desc in sorted(odds_specs.items()):
            console.print(f"  [cyan]{code}[/cyan] - {desc}")
        console.print()

    if master_specs:
        console.print("[bold]Master Data:[/bold]")
        for code, desc in sorted(master_specs.items()):
            console.print(f"  [cyan]{code}[/cyan] - {desc}")
        console.print()

    if other_specs:
        console.print("[bold]Other Data:[/bold]")
        for code, desc in sorted(other_specs.items()):
            console.print(f"  [cyan]{code}[/cyan] - {desc}")
        console.print()

    console.print("[dim]Use these codes with: jltsql realtime start --specs <code>[/dim]")


if __name__ == "__main__":
    cli(obj={})
