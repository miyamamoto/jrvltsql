"""JLTSQL Command Line Interface."""

import sys
from pathlib import Path

import click
from rich.console import Console

from src.utils.config import ConfigError, load_config
from src.utils.logger import get_logger, setup_logging_from_config

# Version
__version__ = "0.1.0-alpha"

# Console for rich output
console = Console()
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
@click.version_option(version=__version__, prog_name="jltsql")
@click.pass_context
def cli(ctx, config, verbose):
    """JLTSQL - JRA-VAN Link To SQL

    JRA-VAN DataLabの競馬データをSQLite/DuckDB/PostgreSQLに
    リアルタイムインポートするツール

    \b
    使用例:
      jltsql init                     # プロジェクト初期化
      jltsql fetch --from 2024-01-01  # データ取得
      jltsql monitor --daemon         # リアルタイム監視開始

    詳細: https://github.com/yourusername/jltsql
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


# Placeholder commands for future implementation
@cli.command()
@click.option("--from", "date_from", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--to", "date_to", required=True, help="End date (YYYY-MM-DD)")
@click.option("--data-spec", required=True, help="Data specification (RACE, DIFF, etc.)")
@click.pass_context
def fetch(ctx, date_from, date_to, data_spec):
    """Fetch historical data from JRA-VAN DataLab.

    \b
    Examples:
      jltsql fetch --from 2024-01-01 --to 2024-12-31 --data-spec RACE
      jltsql fetch --from 2024-01-01 --to 2024-12-31 --data-spec DIFF
    """
    console.print("[yellow]Note: This command is not yet implemented.[/yellow]")
    console.print(f"Would fetch data from {date_from} to {date_to}, spec: {data_spec}")
    logger.info("Fetch command called", date_from=date_from, date_to=date_to, data_spec=data_spec)


@cli.command()
@click.option("--daemon", is_flag=True, help="Run in background")
@click.pass_context
def monitor(ctx, daemon):
    """Start real-time monitoring.

    \b
    Examples:
      jltsql monitor             # Run in foreground
      jltsql monitor --daemon    # Run in background
    """
    console.print("[yellow]Note: This command is not yet implemented.[/yellow]")
    console.print(f"Would start monitoring (daemon: {daemon})")
    logger.info("Monitor command called", daemon=daemon)


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop real-time monitoring."""
    console.print("[yellow]Note: This command is not yet implemented.[/yellow]")
    console.print("Would stop monitoring")


@cli.command()
@click.option("--db", type=click.Choice(["sqlite", "duckdb", "postgresql"]), default="sqlite")
@click.pass_context
def create_tables(ctx, db):
    """Create database tables.

    \b
    Examples:
      jltsql create-tables              # Create SQLite tables
      jltsql create-tables --db duckdb  # Create DuckDB tables
    """
    console.print("[yellow]Note: This command is not yet implemented.[/yellow]")
    console.print(f"Would create tables for {db}")


if __name__ == "__main__":
    cli(obj={})
