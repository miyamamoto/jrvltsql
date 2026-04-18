"""JLTSQL Command Line Interface."""

import sys
import os
from pathlib import Path

import click
from rich.console import Console

from src.utils.config import ConfigError, load_config
from src.utils.logger import get_logger, setup_logging_from_config
from src.utils.updater import (
    auto_update_check_notice,
    check_for_updates,
    get_current_commit,
    get_current_version,
    perform_update,
)

# Version - single source of truth from pyproject.toml
def _read_version():
    """Read version from pyproject.toml."""
    try:
        from importlib.metadata import version as _get_version
        return _get_version("jrvltsql")
    except Exception:
        pass
    try:
        from pathlib import Path
        import re
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.M)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "unknown"

__version__ = _read_version()

# Console for rich output (Windows cp932-safe)
console = Console(legacy_windows=True)
logger = get_logger(__name__)


def _normalize_service_key(value: str | None) -> str | None:
    """Normalize service key values from config/env."""
    if not value:
        return None
    v = str(value).strip()
    if not v:
        return None
    # Unresolved env placeholders should be treated as missing.
    if v.startswith("${") and v.endswith("}"):
        return None
    return v


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
    """JRVLTSQL - JRA-VAN Link To SQL

    JRA-VAN DataLabの競馬データをSQLite/PostgreSQLに
    リアルタイムインポートするツール（32-bit Python対応）

    \b
    使用例:
      jltsql init                     # プロジェクト初期化
      jltsql fetch --from 2024-01-01  # データ取得
      jltsql monitor --daemon         # リアルタイム監視開始

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

            # Auto-update check (if enabled in config)
            auto_check = cfg.get("auto_update_check", True)
            if auto_check and ctx.invoked_subcommand not in ("update", "version"):
                notice = auto_update_check_notice()
                if notice:
                    console.print(f"[dim yellow]{notice}[/dim yellow]")
                    console.print()

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
    """Show JLTSQL status.

    \b
    Examples:
      jltsql status
    """
    console.print("[bold cyan]JLTSQL Status[/bold cyan]")
    console.print(f"Version: {__version__}")
    console.print()
    console.print("[bold]JRA-VAN DataLab:[/bold]")
    try:
        from src.jvlink import JVLinkWrapper
        console.print("  状態: [green]利用可能[/green]")
    except ImportError:
        console.print("  状態: [red]利用不可[/red]")
    console.print("Status: [green]Ready[/green]")


@cli.command()
@click.option("--check", is_flag=True, help="最新版の確認")
def version(check):
    """Show version information and check for updates."""
    current = get_current_version()
    commit = get_current_commit()
    commit_str = f" ({commit})" if commit else ""

    console.print(f"[bold]JLTSQL[/bold] version {current}{commit_str}")
    console.print(f"Python: {sys.version.split()[0]} ({'32-bit' if sys.maxsize <= 2**31 else '64-bit'})")

    console.print()
    console.print("[bold]対応データソース:[/bold]")
    try:
        from src.jvlink import JVLinkWrapper
        console.print("  - JRA-VAN DataLab (JV-Link): [green]利用可能[/green]")
    except ImportError:
        console.print("  - JRA-VAN DataLab (JV-Link): [red]未インストール[/red]")

    if check:
        console.print()
        console.print("[dim]Checking for updates...[/dim]")
        info = check_for_updates()
        if info is None:
            console.print("[yellow]Could not check for updates.[/yellow]")
        elif info["update_available"]:
            console.print(
                f"[bold yellow]Update available:[/bold yellow] "
                f"{info['current_version']} → {info['latest_version']}"
            )
            console.print(f"Run [bold]jltsql update[/bold] to update.")
            if info.get("html_url"):
                console.print(f"[dim]{info['html_url']}[/dim]")
        else:
            console.print("[green]You are on the latest version.[/green]")


@cli.command()
@click.option("--force", is_flag=True, help="Force update even if already up to date")
@click.pass_context
def update(ctx, force):
    """Update JLTSQL to the latest version.

    Pulls the latest code from GitHub and updates dependencies.

    \b
    Examples:
      jltsql update          # Update to latest version
      jltsql update --force  # Force reinstall dependencies
    """
    current = get_current_version()
    console.print(f"[bold cyan]JLTSQL Update[/bold cyan]")
    console.print(f"Current version: {current}")
    console.print()

    console.print("[dim]Checking for updates...[/dim]")
    info = check_for_updates()

    if info and not info["update_available"] and not force:
        console.print("[green]Already up to date.[/green]")
        return

    if info and info["update_available"]:
        console.print(
            f"[yellow]New version available:[/yellow] {info['latest_version']}"
        )
        console.print()

    console.print("[bold]Updating...[/bold]")
    success = perform_update(verbose=True)

    if success:
        new_version = get_current_version()
        console.print()
        console.print(f"[bold green]✓ Update complete![/bold green]")
        console.print(f"  Version: {new_version}")
    else:
        console.print()
        console.print("[bold red]✗ Update failed.[/bold red]")
        console.print("Try manually: git pull && pip install -e .")
        sys.exit(1)


@cli.command()
@click.option("--from", "date_from", required=True, help="Start date (YYYYMMDD)")
@click.option("--to", "date_to", required=True, help="End date (YYYYMMDD) - filters records up to this date")
@click.option("--spec", "data_spec", required=True, help="Data specification (RACE, DIFF, etc.)")
@click.option(
    "--option",
    "jv_option",
    type=int,
    default=1,
    help="JVOpen option: 1=通常データ（差分）, 2=今週データ, 3=セットアップ（ダイアログ）, 4=分割セットアップ (default: 1)"
)
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None, help="Database type (default: from config)")
@click.option("--batch-size", default=1000, help="Batch size for imports (default: 1000)")
@click.option("--progress/--no-progress", default=True, help="Show progress display (default: enabled)")
@click.option("--use-cache/--no-cache", default=True, show_default=True, help="Use local cache if available")
@click.pass_context
def fetch(ctx, date_from, date_to, data_spec, jv_option, db, batch_size, progress, use_cache):
    """Fetch historical data from JRA-VAN DataLab.

    JVOpen option meanings:
      - option=1 (通常データ): 差分データ取得（蓄積系メンテナンス用）
      - option=2 (今週データ): 直近のレースに関するデータのみ
      - option=3 (セットアップ): 全データ取得（ダイアログ表示あり）
      - option=4 (分割セットアップ): 全データ取得（初回のみダイアログ）

    \b
    Examples:
      jltsql fetch --from 20240101 --to 20241231 --spec RACE
      jltsql fetch --from 20240101 --to 20241231 --spec DIFF --option 3
    """
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

    option_names = {1: "通常データ", 2: "今週データ", 3: "セットアップ", 4: "分割セットアップ"}
    console.print(f"[bold cyan]Fetching historical data from JRA-VAN DataLab...[/bold cyan]\n")
    console.print(f"  Data source: JRA (中央競馬)")
    console.print(f"  Date range: {date_from} -- {date_to}")
    console.print(f"  Data spec:  {data_spec}")
    console.print(f"  Option:     {jv_option} ({option_names.get(jv_option, '不明')})")
    console.print(f"  Database:   {db_type}")

    # Warn if setup mode (3 or 4) is used
    if jv_option in (3, 4):
        console.print()
        console.print("[yellow]Note:[/yellow] セットアップモード - 全データ取得（ダイアログが表示されます）")

    # Validate data_spec and option combination
    from src.jvlink.constants import is_valid_jvopen_combination, JVOPEN_VALID_COMBINATIONS
    if not is_valid_jvopen_combination(data_spec, jv_option):
        console.print()
        console.print(f"[red]Error:[/red] データ種別 '{data_spec}' は option={jv_option} では取得できません")
        valid_specs = JVOPEN_VALID_COMBINATIONS.get(jv_option, [])
        console.print(f"       option={jv_option} で取得可能: {', '.join(valid_specs)}")
        sys.exit(1)

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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
            sys.exit(1)

        # Connect to database
        with database:
            # Ensure tables exist
            try:
                create_all_tables(database)
            except Exception:
                # Tables might already exist, that's OK
                pass

            sid = config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL"
            service_key = config.get("jvlink.service_key") if config else None

            cache_mgr = None
            if use_cache:
                from src.cache import CacheManager
                cache_dir = config.get("cache.directory", "data/cache") if config else "data/cache"
                cache_mgr = CacheManager(Path(cache_dir))

            processor = BatchProcessor(
                database=database,
                sid=sid,
                batch_size=batch_size,
                service_key=service_key,
                show_progress=progress,
                cache_manager=cache_mgr,
            )

            if not progress:
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


# ---------------------------------------------------------------------------
# cache command group
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def cache(ctx):
    """Manage local JV-Data cache.

    The cache stores raw JV-Data binary records locally so subsequent
    fetch calls can skip JV-Link API calls entirely.

    Cache location: data/cache/ (configurable in config.yaml)

    Examples:
      jltsql cache info
      jltsql cache build --spec RACE --from 20260101 --to 20260328
      jltsql cache clear --spec RACE
    """
    pass


@cache.command("info")
@click.option("--cache-dir", default="data/cache", show_default=True, help="Cache directory")
@click.pass_context
def cache_info(ctx, cache_dir):
    """Show cache statistics."""
    from src.cache import CacheManager
    import json

    mgr = CacheManager(Path(cache_dir))
    info = mgr.info()

    click.echo(f"\nCache directory: {Path(cache_dir).resolve()}")
    click.echo(f"Total size: {info['total_size_bytes'] / 1024 / 1024:.1f} MB\n")

    if info["nl"]:
        click.echo("NL_ (蓄積系) cache:")
        for spec, s in info["nl"].items():
            click.echo(f"  {spec:8s}  {s['complete_dates']:4}/{s['cached_dates']:4} dates complete"
                       f"  {s['date_range']:22s}  {s['size_bytes']/1024:.0f} KB")
    else:
        click.echo("NL_ cache: (empty)")

    if info["rt"]:
        click.echo("\nRT_ (速報系) cache:")
        for spec, s in info["rt"].items():
            click.echo(f"  {spec:6s}  {s['cached_dates']:4} dates"
                       f"  {s['date_range']:22s}  {s['size_bytes']/1024:.0f} KB")
    else:
        click.echo("\nRT_ cache: (empty)")


@cache.command("build")
@click.option("--spec", "data_spec", required=True, help="Data spec (RACE, DIFF, DIFFU, etc.)")
@click.option("--from", "date_from", required=True, help="Start date YYYYMMDD")
@click.option("--to", "date_to", required=True, help="End date YYYYMMDD")
@click.option("--option", "jv_option", type=int, default=1, show_default=True,
              help="JVOpen option: 1=通常, 2=今週, 3=setup, 4=split-setup")
@click.option("--also-import", is_flag=True, default=False,
              help="Also import records into DB (default: cache only)")
@click.option("--db", type=click.Choice(["sqlite", "postgresql"]), default=None)
@click.option("--cache-dir", default="data/cache", show_default=True)
@click.pass_context
def cache_build(ctx, data_spec, date_from, date_to, jv_option, also_import, db, cache_dir):
    """Fetch from JV-Link and save to local cache.

    By default only saves to cache (no DB write). Use --also-import to
    also write to the database.

    Examples:
      jltsql cache build --spec RACE --from 20260101 --to 20260328
      jltsql cache build --spec DIFF --from 20260101 --to 20260328 --also-import
    """
    from src.cache import CacheManager
    from src.fetcher.historical import HistoricalFetcher

    config = ctx.obj.get("config", {}) if ctx.obj else {}
    service_key = config.get("jvlink", {}).get("service_key") or os.environ.get("JVLINK_SERVICE_KEY")

    mgr = CacheManager(Path(cache_dir))

    # Check if already cached
    if mgr.has_nl_range(data_spec, date_from, date_to):
        click.echo(f"[CACHED] {data_spec} {date_from}..{date_to} already in cache.")
        click.echo("Use 'cache rebuild' to re-fetch.")
        return

    click.echo(f"Building cache: {data_spec} {date_from}..{date_to} (option={jv_option})")

    fetcher = HistoricalFetcher(sid="UNKNOWN", service_key=service_key, show_progress=True)
    fetcher.cache_manager = mgr

    if also_import:
        # Use BatchProcessor with cache
        from src.importer.batch import BatchProcessor
        from src.database.sqlite_handler import SQLiteDatabase
        from src.database.postgresql_handler import PostgreSQLDatabase

        if db:
            db_type = db
        else:
            db_type = config.get("database.type", "sqlite") if config else "sqlite"

        if db_type == "sqlite":
            db_config = config.get("databases.sqlite") if config else {"path": "data/keiba.db"}
            database = SQLiteDatabase(db_config)
        elif db_type == "postgresql":
            if not config:
                click.echo("Error: PostgreSQL requires configuration file.")
                sys.exit(1)
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            click.echo(f"Error: Unsupported database type: {db_type}")
            sys.exit(1)

        with database:
            processor = BatchProcessor(
                database=database,
                service_key=service_key,
                show_progress=True,
                cache_manager=mgr,
            )
            stats = processor.process_date_range(data_spec, date_from, date_to, jv_option)
            click.echo(f"\nImported: {stats.get('records_imported', 0):,} records")
    else:
        # Cache-only: fetch but don't import to DB
        count = 0
        for record in fetcher.fetch(data_spec, date_from, date_to, jv_option):
            count += 1
        fetcher.cache_manager = None
        click.echo(f"\nCached: {count:,} records for {data_spec} {date_from}..{date_to}")

    # Show updated cache info
    info = mgr.info()
    nl_info = info["nl"].get(data_spec.upper(), {})
    click.echo(f"Cache: {nl_info.get('complete_dates', 0)} dates, "
               f"{nl_info.get('size_bytes', 0)/1024:.0f} KB")


@cache.command("clear")
@click.option("--spec", default=None, help="Spec to clear (default: all)")
@click.option("--date", "date_str", default=None, help="Specific date YYYYMMDD to clear")
@click.option("--rt", is_flag=True, help="Clear RT_ (速報系) cache instead of NL_")
@click.option("--cache-dir", default="data/cache", show_default=True)
@click.confirmation_option(prompt="Clear cache data?")
@click.pass_context
def cache_clear(ctx, spec, date_str, rt, cache_dir):
    """Clear local cache files.

    Examples:
      jltsql cache clear                   # clear all NL_ cache
      jltsql cache clear --spec RACE       # clear RACE only
      jltsql cache clear --rt              # clear all RT_ cache
      jltsql cache clear --spec RACE --date 20260328
    """
    from src.cache import CacheManager
    mgr = CacheManager(Path(cache_dir))
    deleted = mgr.clear(spec=spec, date_str=date_str, rt=rt)
    target = "RT_" if rt else "NL_"
    click.echo(f"Cleared {deleted} cache file(s) from {target} cache.")


@cache.command("rebuild")
@click.option("--spec", "data_spec", required=True)
@click.option("--from", "date_from", required=True)
@click.option("--to", "date_to", required=True)
@click.option("--option", "jv_option", type=int, default=1)
@click.option("--cache-dir", default="data/cache", show_default=True)
@click.pass_context
def cache_rebuild(ctx, data_spec, date_from, date_to, jv_option, cache_dir):
    """Clear then rebuild cache for a spec/date range.

    Example:
      jltsql cache rebuild --spec RACE --from 20260301 --to 20260328
    """
    from src.cache import CacheManager
    mgr = CacheManager(Path(cache_dir))

    # Clear first
    from datetime import datetime, timedelta
    d = datetime.strptime(date_from, "%Y%m%d").date()
    end = datetime.strptime(date_to, "%Y%m%d").date()
    deleted = 0
    while d <= end:
        deleted += mgr.clear(spec=data_spec, date_str=d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    click.echo(f"Cleared {deleted} existing cache files.")

    # Rebuild via cache build
    ctx.invoke(cache_build, data_spec=data_spec, date_from=date_from,
               date_to=date_to, jv_option=jv_option, also_import=False,
               db=None, cache_dir=cache_dir)


# ---------------------------------------------------------------------------
# cache s3-setup: configure encrypted S3 credentials
# ---------------------------------------------------------------------------

@cache.command("s3-setup")
@click.option("--cred-file", default="config/s3_credentials.enc", show_default=True,
              help="Path to store encrypted credentials")
@click.pass_context
def cache_s3_setup(ctx, cred_file):
    """Configure and store encrypted S3/R2 credentials.

    Credentials are encrypted with AES-256-GCM using a master password
    you choose. The encrypted file is safe to check into version control.

    Supported backends:
      - AWS S3: leave endpoint_url blank
      - Cloudflare R2: endpoint_url = https://<account>.r2.cloudflarestorage.com

    Example:
      jltsql cache s3-setup
    """
    from src.cache.credentials import CredentialManager

    click.echo("=== S3 / Cloudflare R2 Credential Setup ===\n")
    click.echo("Leave endpoint_url blank for AWS S3.")
    click.echo("For Cloudflare R2: https://<account_id>.r2.cloudflarestorage.com\n")

    endpoint_url = click.prompt("endpoint_url (blank for AWS S3)", default="", show_default=False)
    access_key_id = click.prompt("aws_access_key_id")
    secret_key = click.prompt("aws_secret_access_key", hide_input=True)
    bucket = click.prompt("bucket_name")
    region = click.prompt("region_name", default="auto")
    prefix = click.prompt("S3 key prefix", default="jrvltsql-cache")

    credentials = {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_key,
        "bucket_name": bucket,
        "region_name": region,
        "prefix": prefix,
    }
    if endpoint_url:
        credentials["endpoint_url"] = endpoint_url

    click.echo("\nChoose a master password to protect your credentials.")
    password = click.prompt("Master password", hide_input=True, confirmation_prompt=True)

    mgr = CredentialManager(Path(cred_file))
    mgr.save(credentials, password)

    click.echo(f"\n[OK] Credentials saved (encrypted): {Path(cred_file).resolve()}")
    click.echo("Use this password whenever you run 'jltsql cache sync'.")

    # Quick connection test
    if click.confirm("\nTest connection now?", default=True):
        try:
            from src.cache.s3_sync import S3Syncer
            syncer = S3Syncer(cache_dir=Path("data/cache"), credentials=credentials)
            syncer.test_connection()
            click.echo("[OK] Connection successful!")
        except Exception as e:
            click.echo(f"[WARN] Connection test failed: {e}")
            click.echo("Credentials saved. Check endpoint/keys and retry.")


# ---------------------------------------------------------------------------
# cache sync: upload / download / bidirectional sync with S3
# ---------------------------------------------------------------------------

@cache.command("sync")
@click.option("--upload", "direction", flag_value="upload", help="Local → S3 only")
@click.option("--download", "direction", flag_value="download", help="S3 → local only")
@click.option("--both", "direction", flag_value="both", default=True,
              help="Bidirectional sync (default)")
@click.option("--dry-run", is_flag=True, help="Show what would be transferred (no actual transfer)")
@click.option("--cache-dir", default="data/cache", show_default=True)
@click.option("--cred-file", default="config/s3_credentials.enc", show_default=True)
@click.pass_context
def cache_sync(ctx, direction, dry_run, cache_dir, cred_file):
    """Sync local cache with S3 / Cloudflare R2.

    Uses encrypted credentials from s3-setup. You will be prompted for
    the master password each time (never stored in plaintext).

    Examples:
      jltsql cache sync                  # bidirectional
      jltsql cache sync --upload         # local → S3
      jltsql cache sync --download       # S3 → local
      jltsql cache sync --dry-run        # preview only
    """
    from src.cache.credentials import CredentialManager
    from src.cache.s3_sync import S3Syncer, S3SyncError

    cred_mgr = CredentialManager(Path(cred_file))
    if not cred_mgr.exists():
        click.echo("[ERROR] S3 credentials not found. Run: jltsql cache s3-setup")
        raise SystemExit(1)

    password = click.prompt("Master password", hide_input=True)
    try:
        credentials = cred_mgr.load(password)
    except ValueError as e:
        click.echo(f"[ERROR] {e}")
        raise SystemExit(1)

    if dry_run:
        click.echo("[DRY RUN] No files will be transferred.\n")

    def on_progress(action, key, size):
        rel = key.split("/", 1)[-1] if "/" in key else key
        click.echo(f"  {action:8s}  {rel}  ({size/1024:.0f} KB)")

    try:
        syncer = S3Syncer(
            cache_dir=Path(cache_dir),
            credentials=credentials,
            on_progress=on_progress,
        )

        click.echo(f"Bucket: {credentials['bucket_name']}  "
                   f"Prefix: {credentials.get('prefix', 'jrvltsql-cache')}\n")

        if direction == "upload":
            stats = syncer.upload(dry_run=dry_run)
            click.echo(f"\nUploaded: {stats['uploaded']:,} files "
                       f"({stats['bytes']/1024/1024:.1f} MB)  "
                       f"Skipped: {stats['skipped']:,}  Errors: {stats['errors']:,}")

        elif direction == "download":
            stats = syncer.download(dry_run=dry_run)
            click.echo(f"\nDownloaded: {stats['downloaded']:,} files "
                       f"({stats['bytes']/1024/1024:.1f} MB)  "
                       f"Skipped: {stats['skipped']:,}  Errors: {stats['errors']:,}")

        else:  # both
            stats = syncer.sync(dry_run=dry_run)
            click.echo(
                f"\nSync complete:\n"
                f"  Uploaded:   {stats['uploaded']:,} files "
                f"({stats['bytes_up']/1024/1024:.1f} MB)\n"
                f"  Downloaded: {stats['downloaded']:,} files "
                f"({stats['bytes_down']/1024/1024:.1f} MB)\n"
                f"  Skipped:    {stats['skipped']:,} files (same size)\n"
                f"  Errors:     {stats['errors']:,}"
            )
            if stats["errors"] > 0:
                raise SystemExit(1)

    except S3SyncError as e:
        click.echo(f"[ERROR] {e}")
        raise SystemExit(1)


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
      jltsql monitor                        # 中央競馬監視
      jltsql monitor --daemon               # バックグラウンド実行
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

    console.print(f"[bold cyan]Starting real-time monitoring (JRA/中央競馬)...[/bold cyan]\n")
    console.print(f"  Data source: JRA (中央競馬)")
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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
            sys.exit(1)

        # Connect to database
        with database:
            # Ensure tables exist
            try:
                create_all_tables(database)
            except Exception:
                # Tables might already exist, that's OK
                pass

            sid = config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL"
            monitor_obj = RealtimeMonitor(
                database=database,
                data_spec=data_spec,
                polling_interval=interval,
                sid=sid,
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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
            sys.exit(1)

        # Connect and export
        with database:
            # Check table exists
            if not database.table_exists(table):
                console.print(f"[red]Error:[/red] Table '{table}' does not exist.")
                sys.exit(1)

            # Validate table name to prevent SQL injection
            # Only allow alphanumeric characters and underscores
            import re
            if not re.match(r'^[A-Za-z0-9_]+$', table):
                console.print(f"[red]Error:[/red] Invalid table name '{table}'. Only alphanumeric characters and underscores are allowed.")
                sys.exit(1)

            # Build query
            sql = f"SELECT * FROM {table}"
            if where:
                # WARNING: The WHERE clause is not parameterized and may be vulnerable to SQL injection.
                # This feature is intended for CLI/internal use only.
                # DO NOT expose this to untrusted input or web interfaces.
                console.print("[yellow]Warning:[/yellow] WHERE clause is not parameterized. Use only with trusted input.")
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
            console.print("[bold green][OK] Export complete![/bold green]")
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
      jltsql realtime start                     # 中央競馬監視
      jltsql realtime start --specs 0B12,0B15   # 複数データ種別
      jltsql realtime start --db sqlite         # データベース指定
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
            console.print("[yellow]Note:[/yellow] Supported types: sqlite, postgresql")
            sys.exit(1)

        # Create monitor
        monitor = RealtimeMonitor(
            database=database,
            data_specs=data_specs,
            sid=config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL",
            batch_size=batch_size,
            auto_create_tables=not no_create_tables
        )

        # Start monitoring
        if monitor.start():
            console.print("[bold green][OK] Monitoring service started![/bold green]\n")

            # Write PID lock file so raceday_verify can detect the running process
            lock_dir = Path(".locks")
            lock_dir.mkdir(exist_ok=True)
            lock_file = lock_dir / "realtime_updater.lock"
            lock_file.write_text(str(os.getpid()))

            status = monitor.get_status()
            console.print("[bold]Status:[/bold]")
            console.print("  Running:        Yes")
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
            finally:
                lock_file.unlink(missing_ok=True)

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


@realtime.command("status")
@click.pass_context
def realtime_status(ctx):
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


@realtime.command("stop")
@click.pass_context
def realtime_stop(ctx):
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
@click.option(
    "--spec",
    "-s",
    default="0B30",
    help="Data spec code (0B30-0B36, default: 0B30 for 単勝オッズ)",
)
@click.option(
    "--from-date",
    "-f",
    type=str,
    default=None,
    help="Start date in YYYYMMDD format (default: 1 year ago)",
)
@click.option(
    "--to-date",
    "-t",
    type=str,
    default=None,
    help="End date in YYYYMMDD format (default: today)",
)
@click.option(
    "--db",
    type=click.Choice(["sqlite", "postgresql"]),
    default=None,
    help="Database type (overrides config)",
)
@click.option(
    "--db-path",
    type=str,
    default=None,
    help="SQLite database path (overrides config)",
)
@click.pass_context
def timeseries(ctx, spec, from_date, to_date, db, db_path):
    """Fetch time series odds data from JV-Link.

    Fetches historical time series odds data for races already in the database.
    JV-Link provides up to 1 year of historical odds data.

    \b
    Data specs:
      0B30 - 単勝オッズ (Win odds)
      0B31 - 複勝・枠連オッズ (Place/Bracket quinella odds)
      0B32 - 馬連オッズ (Quinella odds)
      0B33 - ワイドオッズ (Wide odds)
      0B34 - 馬単オッズ (Exacta odds)
      0B35 - 3連複オッズ (Trio odds)
      0B36 - 3連単オッズ (Trifecta odds)

    \b
    Examples:
      jltsql realtime timeseries
      jltsql realtime timeseries --spec 0B30 --from-date 20241201
      jltsql realtime timeseries --spec 0B31,0B32 --db-path data/keiba.db
    """
    from datetime import datetime, timedelta
    from src.database.sqlite_handler import SQLiteDatabase
    from src.fetcher.realtime import RealtimeFetcher
    from src.realtime.updater import RealtimeUpdater

    config = ctx.obj.get("config")

    # Determine database type and path
    if db:
        db_type = db
    else:
        db_type = config.get("database.type", "sqlite") if config else "sqlite"

    # Determine database path
    if db_path:
        database_path = db_path
    elif config:
        database_path = config.get("databases.sqlite.path", "data/keiba.db")
    else:
        database_path = "data/keiba.db"

    # Resolve path
    database_path = str(Path(database_path).resolve())

    # Default date range (1 year for JVRTOpen)
    if not from_date:
        one_year_ago = datetime.now() - timedelta(days=365)
        from_date = one_year_ago.strftime("%Y%m%d")
    if not to_date:
        to_date = datetime.now().strftime("%Y%m%d")

    # Parse multiple specs
    specs_list = [s.strip() for s in spec.split(",")]

    console.print("[bold cyan]Fetching time series odds data...[/bold cyan]\n")
    console.print(f"  Data specs:    {', '.join(specs_list)}")
    console.print(f"  Database:      {database_path} ({db_type})")
    console.print(f"  Date range:    {from_date} - {to_date}")
    console.print()

    try:
        # Initialize database for saving
        if db_type == "postgresql":
            from src.database.postgresql_handler import PostgreSQLDatabase
            database = PostgreSQLDatabase(config.get("databases.postgresql"))
        else:
            db_config = {"path": database_path}
            database = SQLiteDatabase(db_config)

        with database:
            # Ensure TS_O* tables exist
            from src.database.schema import SCHEMAS
            schema_registry = SCHEMAS
            for spec_code in specs_list:
                # Map spec to table name
                table_map = {
                    "0B30": "TS_O1",
                    "0B31": "TS_O1",  # Also has O2 data
                    "0B32": "TS_O2",
                    "0B33": "TS_O3",
                    "0B34": "TS_O4",
                    "0B35": "TS_O5",
                    "0B36": "TS_O6",
                }
                table_name = table_map.get(spec_code)
                if table_name and table_name in schema_registry:
                    database.create_table(table_name, schema_registry[table_name])
                    console.print(f"  [green]✓[/green] Table {table_name} ready")

            # Initialize fetcher and updater
            sid = config.get("jvlink.sid", "JLTSQL") if config else "JLTSQL"
            fetcher = RealtimeFetcher(sid=sid)
            updater = RealtimeUpdater(database)

            total_records = 0
            total_success = 0
            total_errors = 0

            for spec_code in specs_list:
                console.print(f"\n[bold]Processing {spec_code}...[/bold]")

                try:
                    record_count = 0
                    for record in fetcher.fetch_time_series_batch_from_db(
                        data_spec=spec_code,
                        db_path=database_path,
                        from_date=from_date,
                        to_date=to_date,
                    ):
                        # Save with timeseries=True to use TS_O* tables
                        raw_buff = record.get("_raw")
                        if raw_buff:
                            result = updater.process_record(raw_buff, timeseries=True)
                            if result and result.get("success"):
                                total_success += 1
                            else:
                                total_errors += 1
                        record_count += 1
                        total_records += 1

                        # Progress indicator
                        if record_count % 100 == 0:
                            console.print(f"\r  Processed: {record_count:,} records", end="")

                    console.print(f"\r  [green]✓[/green] {spec_code}: {record_count:,} records processed")

                except Exception as e:
                    console.print(f"  [red]✗[/red] {spec_code}: Error - {e}")
                    logger.error(f"Error processing {spec_code}", error=str(e), exc_info=True)

            console.print()
            console.print("[bold green]Complete![/bold green]")
            console.print(f"  Total records:  {total_records:,}")
            console.print(f"  Saved:          {total_success:,}")
            console.print(f"  Errors:         {total_errors:,}")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}", style="bold")
        logger.error("Failed to fetch time series data", error=str(e), exc_info=True)
        sys.exit(1)


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
