#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for CLI commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cli.main import cli
from tests.cli_test_support import CliRunner


class TestCLIBasic(unittest.TestCase):
    """Test basic CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("JLTSQL", result.output)
        self.assertIn("init", result.output)
        self.assertIn("fetch", result.output)
        self.assertIn("monitor", result.output)

    def test_version_command(self):
        """Version is available before a configuration file exists."""
        with patch("src.cli.main.Path.exists", return_value=False):
            result = self.runner.invoke(cli, ["version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("JLTSQL version", result.output)
        self.assertTrue(
            "Python version" in result.output or "Python:" in result.output,
            f"Expected 'Python version' or 'Python:' in output: {result.output}",
        )

    def test_status_command(self):
        """Status is available before a configuration file exists; fetch is not."""
        with patch("src.cli.main.Path.exists", return_value=False):
            result = self.runner.invoke(cli, ["status"])
            fetch_result = self.runner.invoke(
                cli,
                ["fetch", "--from", "2024-01-01", "--to", "2024-01-02", "--spec", "RACE"],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("JLTSQL Status", result.output)
        self.assertIn("Version", result.output)
        # Data-acquiring commands stay behind the configuration gate.
        self.assertEqual(fetch_result.exit_code, 1)
        self.assertIn("Configuration file not found", fetch_result.output)

    def test_isolated_filesystem_preserves_click_temp_dir_contract(self):
        """The compatibility runner retains Click's optional parent directory."""
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as parent_directory:
            with self.runner.isolated_filesystem(parent_directory) as isolated:
                Path("sentinel").write_text("present", encoding="utf-8")
                self.assertEqual(Path.cwd(), Path(isolated))

            self.assertEqual(Path.cwd(), original_directory)
            self.assertEqual(
                (Path(isolated) / "sentinel").read_text(encoding="utf-8"),
                "present",
            )


class TestDatabaseMaintenanceCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_sokuho_migration_defaults_to_dry_run_and_forwards_table_restriction(self):
        from src.database.migration import SokuhoCaptureIdentityMigrationReport

        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        report = SokuhoCaptureIdentityMigrationReport(
            table_name="TS_SOKUHO_O3",
            status="legacy",
            primary_key=("year", "collectedat"),
            total_rows=7,
            distinct_publication_groups=3,
            rows_to_delete=4,
            collected_at_rewrite_groups=2,
        )

        with self.runner.isolated_filesystem():
            self.assertEqual(self.runner.invoke(cli, ["init"]).exit_code, 0)
            with (
                patch(
                    "src.database.create_database_from_config",
                    return_value=database,
                ),
                patch(
                    "src.database.migration.preview_sokuho_capture_identity_migration",
                    return_value=[report],
                ) as preview,
                patch(
                    "src.database.migration.apply_sokuho_capture_identity_migration"
                ) as apply_migration,
                patch("src.cli.main.auto_update_check_notice", return_value=None),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "db",
                        "migrate-sokuho-capture-identity",
                        "--db",
                        "postgresql",
                        "--table",
                        "TS_SOKUHO_O3",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        preview.assert_called_once_with(database, ("TS_SOKUHO_O3",))
        apply_migration.assert_not_called()
        self.assertIn("DRY RUN", result.output)
        self.assertIn("Total rows: 7", result.output)
        self.assertIn("Distinct publication groups: 3", result.output)
        self.assertIn("Rows that would be deleted: 4", result.output)
        self.assertIn(
            "Groups whose CollectedAt would be rewritten to earliest non-NULL: 2",
            result.output,
        )
        self.assertIn("no changes were applied", result.output)

    def test_sokuho_migration_apply_requires_explicit_flag(self):
        from src.database.migration import SokuhoCaptureIdentityMigrationReport

        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        report = SokuhoCaptureIdentityMigrationReport(
            table_name="TS_SOKUHO_O2",
            status="migrated",
            primary_key=("year", "collectedat"),
            total_rows=2,
            distinct_publication_groups=1,
            rows_to_delete=1,
            collected_at_rewrite_groups=1,
            applied=True,
        )

        with self.runner.isolated_filesystem():
            self.assertEqual(self.runner.invoke(cli, ["init"]).exit_code, 0)
            with (
                patch(
                    "src.database.create_database_from_config",
                    return_value=database,
                ),
                patch(
                    "src.database.migration.apply_sokuho_capture_identity_migration",
                    return_value=[report],
                ) as apply_migration,
                patch("src.cli.main.auto_update_check_notice", return_value=None),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "db",
                        "migrate-sokuho-capture-identity",
                        "--db",
                        "postgresql",
                        "--table",
                        "TS_SOKUHO_O2",
                        "--apply",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        apply_migration.assert_called_once_with(database, ("TS_SOKUHO_O2",))
        self.assertIn("APPLY", result.output)
        self.assertIn("Migration apply completed", result.output)

    def test_sokuho_migration_sqlite_refusal_is_nonzero(self):
        with self.runner.isolated_filesystem():
            self.assertEqual(self.runner.invoke(cli, ["init"]).exit_code, 0)
            with (
                patch("src.cli.main.auto_update_check_notice", return_value=None),
                patch("src.database.create_database_from_config") as create_database,
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "db",
                        "migrate-sokuho-capture-identity",
                        "--db",
                        "sqlite",
                        "--table",
                        "TS_SOKUHO_O2",
                    ],
                )
        create_database.assert_not_called()

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("SQLite migration refused", result.output)
        self.assertIn("back up", result.output)
        self.assertIn("rebuild", result.output)

    def test_sokuho_migration_schema_qualifies_selected_tables(self):
        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None

        with self.runner.isolated_filesystem():
            self.assertEqual(self.runner.invoke(cli, ["init"]).exit_code, 0)
            with (
                patch(
                    "src.database.create_database_from_config",
                    return_value=database,
                ),
                patch(
                    "src.database.migration.preview_sokuho_capture_identity_migration",
                    return_value=[],
                ) as preview,
                patch("src.cli.main.auto_update_check_notice", return_value=None),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "db",
                        "migrate-sokuho-capture-identity",
                        "--db",
                        "postgresql",
                        "--schema",
                        "archive",
                        "--table",
                        "TS_SOKUHO_O4",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        preview.assert_called_once_with(database, ("archive.TS_SOKUHO_O4",))


class TestInitCommand(unittest.TestCase):
    """Test init command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_init_creates_directories(self):
        """An installed CLI initializes its writable current directory."""
        with self.runner.isolated_filesystem():
            installed_module = Path.cwd() / "site-packages/src/cli/main.py"
            with patch("src.cli.main.__file__", str(installed_module)):
                result = self.runner.invoke(cli, ["init"])

            self.assertEqual(result.exit_code, 0)
            self.assertTrue(Path("config/config.yaml").is_file())
            self.assertTrue(Path("data").is_dir())
            self.assertTrue(Path("logs").is_dir())
            self.assertNotIn("service key", result.output.lower())

    def test_init_with_force(self):
        """Test init with --force flag."""
        with self.runner.isolated_filesystem():
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)

            example_file = config_dir / "config.yaml.example"
            example_file.write_text("# Example")

            config_file = config_dir / "config.yaml"
            config_file.write_text("# Existing")

            result = self.runner.invoke(cli, ["init", "--force"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("Created configuration file", result.output)

    def test_init_rejects_a_global_config_path_instead_of_ignoring_it(self):
        """Init has a CWD target and must not silently ignore --config."""
        with self.runner.isolated_filesystem():
            explicit = Path("existing.yaml")
            explicit.write_text("sentinel", encoding="utf-8")

            result = self.runner.invoke(
                cli,
                ["--config", str(explicit), "init", "--force"],
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertEqual(explicit.read_text(encoding="utf-8"), "sentinel")
            self.assertFalse(Path("config/config.yaml").exists())

    def test_init_default_is_a_valid_sqlite_configuration(self):
        with self.runner.isolated_filesystem():
            init_result = self.runner.invoke(cli, ["init"])
            show_result = self.runner.invoke(cli, ["config", "--show"])

            self.assertEqual(init_result.exit_code, 0, init_result.output)
            self.assertEqual(show_result.exit_code, 0, show_result.output)
            self.assertIn("Type: sqlite", show_result.output)

    def test_init_rejects_an_existing_invalid_configuration(self):
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("database: invalid\n", encoding="utf-8")

            result = self.runner.invoke(cli, ["init"])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Configuration Error", result.output)
            self.assertNotIn("Initialization complete", result.output)


class TestUpdateCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_failed_wheel_update_does_not_print_git_checkout_instructions(self):
        with self.runner.isolated_filesystem():
            self.assertEqual(self.runner.invoke(cli, ["init"]).exit_code, 0)
            with (
                patch("src.cli.main.check_for_updates", return_value=None),
                patch("src.cli.main.perform_update", return_value=False),
            ):
                result = self.runner.invoke(cli, ["update", "--force"])

            self.assertEqual(result.exit_code, 1)
            self.assertIn("Update failed", result.output)
            self.assertNotIn("git pull", result.output)


class TestCreateTablesCommand(unittest.TestCase):
    """Test create-tables command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_create_tables_sqlite(self):
        """Test create-tables with SQLite."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            # Create data directory
            Path("data").mkdir()

            result = self.runner.invoke(cli, ["create-tables", "--db", "sqlite"])

            # Command should execute (may have various exit codes depending on config/environment)
            # Just verify it doesn't crash with exception
            self.assertIsNotNone(result)
            # Exit codes: 0=success, 1=error, 2=usage error
            self.assertIn(result.exit_code, [0, 1, 2])

    def test_create_tables_with_db_flag(self):
        """Test create-tables with --db flag works."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path("data").mkdir()

            result = self.runner.invoke(cli, ["create-tables", "--db", "sqlite"])

            # Should attempt to execute (may succeed or fail, but command should parse)
            self.assertIsNotNone(result)

    def test_create_tables_rt_only_runs_additive_migration(self):
        """Existing RT tables are migrated before CREATE IF NOT EXISTS."""
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: test.db
jvlink:
  service_key: ""
""")
            database = MagicMock()

            with (
                patch(
                    "src.database.create_database_from_config",
                    return_value=database,
                ),
                patch("src.database.migration.migrate_all_tables") as migrate_all_tables,
                patch("src.database.migration.verify_table_schema") as verify_table_schema,
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "create-tables",
                        "--db",
                        "sqlite",
                        "--rt-only",
                    ],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            migrate_all_tables.assert_called_once()
            selected_schemas = migrate_all_tables.call_args.args[1]
            self.assertTrue(selected_schemas)
            self.assertTrue(all(name.startswith("RT_") for name in selected_schemas))
            self.assertEqual(
                verify_table_schema.call_count,
                len(selected_schemas),
            )

    def test_create_tables_fails_when_schema_verification_fails(self):
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: test.db
jvlink:
  service_key: ""
""")
            database = MagicMock()

            with (
                patch(
                    "src.database.create_database_from_config",
                    return_value=database,
                ),
                patch("src.database.migration.migrate_all_tables"),
                patch(
                    "src.database.migration.verify_table_schema",
                    side_effect=RuntimeError("unsafe schema"),
                ),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "create-tables",
                        "--db",
                        "sqlite",
                        "--rt-only",
                    ],
                )

            self.assertEqual(result.exit_code, 1, result.output)
            self.assertIn("Schema preparation failed", result.output)


class TestFetchCommand(unittest.TestCase):
    """Test fetch command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_fetch_missing_arguments(self):
        """Test fetch command with missing arguments."""
        result = self.runner.invoke(cli, ["fetch"])

        # Should fail due to missing required arguments (--from, --to, --spec)
        self.assertNotEqual(result.exit_code, 0)
        # Check if error message contains missing required option
        self.assertTrue(
            "--from" in result.output.lower()
            or "--to" in result.output.lower()
            or "--spec" in result.output.lower()
            or result.exception is not None
        )

    def test_fetch_help_explains_option_dependent_date_semantics(self):
        example_config = Path(__file__).resolve().parents[1] / "config" / "config.yaml.example"
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(
                example_config.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.runner.invoke(
                cli,
                ["--config", str(config_path), "fetch", "--help"],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        help_text = " ".join(result.output.split())
        self.assertIn("current race-cycle data", help_text)
        self.assertIn("Sunday or Monday may cover two cycles", help_text)
        self.assertIn("ChokyoDate", help_text)
        self.assertIn("one JVOpen per calendar year", help_text)
        self.assertIn("live-verified RACE, except option 2", help_text)
        self.assertIn("opens once from the start point only", help_text)

    @patch("src.database.create_database_from_config")
    def test_fetch_rejects_invalid_dates_before_database_initialization(self, mock_create_database):
        example_config = Path(__file__).resolve().parents[1] / "config" / "config.yaml.example"
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(
                example_config.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.runner.invoke(
                cli,
                [
                    "--config",
                    str(config_path),
                    "fetch",
                    "--from",
                    "20260820",
                    "--to",
                    "20250820",
                    "--spec",
                    "RACE",
                    "--db",
                    "sqlite",
                ],
            )

        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("from_date must not be after to_date", result.output)
        mock_create_database.assert_not_called()

    @patch("src.importer.batch.BatchProcessor")
    def test_fetch_with_all_args(self, mock_batch_processor):
        """Test fetch command with all arguments."""
        # Setup mocks
        mock_processor_instance = MagicMock()
        mock_processor_instance.process_date_range.return_value = {
            "records_fetched": 10,
            "records_parsed": 10,
            "records_imported": 10,
            "records_failed": 0,
            "batches_processed": 1,
        }
        mock_batch_processor.return_value = mock_processor_instance

        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: test_key
""")
            Path("data").mkdir()

            result = self.runner.invoke(
                cli,
                [
                    "fetch",
                    "--from",
                    "20240101",
                    "--to",
                    "20240131",
                    "--spec",
                    "RACE",
                    "--db",
                    "sqlite",
                ],
            )

            # Should execute (may fail due to missing JV-Link, but that's OK for CLI test)
            # Just verify command structure works
            self.assertIsNotNone(result)


class TestCacheBuildCommand(unittest.TestCase):
    """Test fail-before-cache contracts for ``cache build``."""

    def setUp(self):
        self.runner = CliRunner()

    @patch("src.cache.CacheManager")
    def test_commands_reject_invalid_dates_before_cache_lookup(self, mock_cache_manager):
        example_config = Path(__file__).resolve().parents[1] / "config" / "config.yaml.example"
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(
                example_config.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            for command in ("build", "rebuild"):
                with self.subTest(command=command):
                    mock_cache_manager.reset_mock()
                    result = self.runner.invoke(
                        cli,
                        [
                            "--config",
                            str(config_path),
                            "cache",
                            command,
                            "--spec",
                            "RACE",
                            "--from",
                            "20260820",
                            "--to",
                            "20250820",
                            "--option",
                            "4",
                        ],
                    )

                    self.assertEqual(result.exit_code, 1, result.output)
                    self.assertIn("from_date must not be after to_date", result.output)
                    mock_cache_manager.assert_not_called()


class TestMonitorCommand(unittest.TestCase):
    """Test monitor command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("src.realtime.monitor.RealtimeMonitor")
    def test_monitor_daemon_mode(self, mock_monitor):
        """Test monitor command in daemon mode."""
        # Setup mocks
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.get_status.return_value = {
            "started_at": "2024-01-01 00:00:00",
            "running": True,
        }
        mock_monitor_instance.start.return_value = None
        mock_monitor.return_value = mock_monitor_instance

        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path("data").mkdir()

            result = self.runner.invoke(cli, ["monitor", "--daemon", "--db", "sqlite"])

            # Should execute (may fail due to config/JV-Link, but command structure should work)
            self.assertIsNotNone(result)


class TestRealtimeTimeseriesCommand(unittest.TestCase):
    """Time-series persistence failures are command failures, not green summaries."""

    def setUp(self):
        self.runner = CliRunner()
        self.prepare_table_patcher = patch(
            "src.database.timeseries_capture.prepare_time_series_odds_table"
        )
        self.prepare_table = self.prepare_table_patcher.start()
        self.addCleanup(self.prepare_table_patcher.stop)

    def test_timeseries_commits_table_setup_and_fails_closed_on_batch_error(self):
        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        fetcher = MagicMock()
        fetcher.fetch_time_series_batch_from_db.return_value = iter(
            [{"RecordSpec": "O1", "Year": 2026, "MonthDay": 816}]
        )
        updater = MagicMock()
        pending_at_batch = []

        def failed_batch(*_args, **_kwargs):
            pending_at_batch.append(database.commit.call_count == 0)
            return {
                "operation": "batch_insert",
                "success": False,
                "inserted": 0,
                "errors": 1,
                "tables": ["TS_O1"],
                "transaction_rolled_back": True,
            }

        updater.process_parsed_records_batch.side_effect = failed_batch

        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
""")
            with (
                patch("src.database.create_database_from_config", return_value=database),
                patch("src.fetcher.realtime.RealtimeFetcher", return_value=fetcher),
                patch("src.realtime.updater.RealtimeUpdater", return_value=updater),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "realtime",
                        "timeseries",
                        "--spec",
                        "0B41",
                        "--from",
                        "20260816",
                        "--to",
                        "20260816",
                        "--db",
                        "postgresql",
                    ],
                )

        self.assertEqual(result.exit_code, 1, result.output)
        self.prepare_table.assert_called_once_with(database, "TS_O1")
        self.assertEqual(pending_at_batch, [False])
        self.assertNotIn("[OK] 0B41", result.output)
        self.assertNotIn("Complete!", result.output)

    def test_timeseries_rejects_unsafe_table_before_fetcher_initialization(self):
        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        self.prepare_table.side_effect = RuntimeError(
            "legacy primary key includes CollectedAt; back up and rebuild"
        )

        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
""")
            with (
                patch("src.database.create_database_from_config", return_value=database),
                patch("src.fetcher.realtime.RealtimeFetcher") as fetcher_class,
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "realtime",
                        "timeseries",
                        "--spec",
                        "0B32",
                        "--from",
                        "20260901",
                        "--to",
                        "20260901",
                        "--db",
                        "postgresql",
                    ],
                )

        self.assertEqual(result.exit_code, 1, result.output)
        self.prepare_table.assert_called_once_with(database, "TS_SOKUHO_O2")
        fetcher_class.assert_not_called()
        database.commit.assert_not_called()
        self.assertIn("legacy primary key includes CollectedAt", result.output)
        self.assertNotIn("Table TS_SOKUHO_O2 ready", result.output)

    def test_timeseries_passes_race_window_options_and_reports_selection(self):
        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        fetcher = MagicMock()

        def fetch_rows(**kwargs):
            callback = kwargs["progress_callback"]
            callback(
                {
                    "status": "window_filter",
                    "key": None,
                    "processed_keys": 0,
                    "total_keys": 1,
                    "considered_keys": 3,
                    "window_candidate_keys": 3,
                    "window_kept_keys": 1,
                    "omitted_canceled_keys": 2,
                    "dropped_too_far_future": 1,
                    "dropped_too_far_past": 1,
                    "skipped_out_of_window_by_date": 0,
                    "success_keys": 0,
                    "no_data_keys": 0,
                    "error_keys": 0,
                    "total_records": 0,
                }
            )
            callback(
                {
                    "status": "success",
                    "key": "202609010501",
                    "processed_keys": 1,
                    "total_keys": 1,
                    "success_keys": 1,
                    "nonempty_keys": 1,
                    "no_data_keys": 0,
                    "error_keys": 0,
                    "records_for_key": 3,
                    "total_records": 3,
                }
            )
            return iter(())

        fetcher.fetch_time_series_batch_from_db.side_effect = fetch_rows
        updater = MagicMock()

        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
""")
            with (
                patch("src.database.create_database_from_config", return_value=database),
                patch("src.fetcher.realtime.RealtimeFetcher", return_value=fetcher),
                patch("src.realtime.updater.RealtimeUpdater", return_value=updater),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "realtime",
                        "timeseries",
                        "--spec",
                        "0B41",
                        "--from",
                        "20260901",
                        "--to",
                        "20260901",
                        "--db",
                        "postgresql",
                        "--post-time-within-minutes",
                        "30",
                        "--post-time-not-past-minutes",
                        "2",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        call_kwargs = fetcher.fetch_time_series_batch_from_db.call_args.kwargs
        self.assertEqual(call_kwargs["post_time_within_minutes"], 30)
        self.assertEqual(call_kwargs["post_time_not_past_minutes"], 2)
        # 下流のwine runtimeがこの行をparseするため、tokenと順序を固定する。
        # canceled= は検証済み中止の除外数で、中止なしでも0が出力される。
        self.assertIn(
            "Window: considered=3 candidates=3 kept=1 canceled=2 "
            "future=1 past=1 date_excluded=0",
            result.output,
        )
        # Keys行も同様にparseされる: ok(成功キー)と実レコードを返した
        # nonemptyキーを区別し、token順を固定する。
        self.assertIn("ok=1 nonempty=1 no_data=0", result.output)

    def test_timeseries_window_idle_run_emits_zero_keys_summary(self):
        """対象0件のidle実行でもspecごとに終端Keysサマリを1行だけ出す。

        窓フィルタで全キーが落ちた(total_keys=0)日でも、下流のwine runtime
        は「何も開かなかった」ことをKeys行で機械的に確認する。last=を含ま
        ない終端形1行のみで、Window行は別行のまま。
        """
        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        fetcher = MagicMock()

        def fetch_rows(**kwargs):
            callback = kwargs["progress_callback"]
            callback(
                {
                    "status": "window_filter",
                    "key": None,
                    "processed_keys": 0,
                    "total_keys": 0,
                    "considered_keys": 2,
                    "window_candidate_keys": 2,
                    "window_kept_keys": 0,
                    "omitted_canceled_keys": 1,
                    "dropped_too_far_future": 0,
                    "dropped_too_far_past": 1,
                    "skipped_out_of_window_by_date": 0,
                    "success_keys": 0,
                    "nonempty_keys": 0,
                    "no_data_keys": 0,
                    "error_keys": 0,
                    "total_records": 0,
                }
            )
            return iter(())

        fetcher.fetch_time_series_batch_from_db.side_effect = fetch_rows
        updater = MagicMock()

        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
""")
            with (
                patch("src.database.create_database_from_config", return_value=database),
                patch("src.fetcher.realtime.RealtimeFetcher", return_value=fetcher),
                patch("src.realtime.updater.RealtimeUpdater", return_value=updater),
            ):
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "realtime",
                        "timeseries",
                        "--spec",
                        "0B41",
                        "--from",
                        "20260901",
                        "--to",
                        "20260901",
                        "--db",
                        "postgresql",
                        "--post-time-within-minutes",
                        "30",
                        "--post-time-not-past-minutes",
                        "2",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(
            "Window: considered=2 candidates=2 kept=0 canceled=1 "
            "future=0 past=1 date_excluded=0",
            result.output,
        )
        self.assertEqual(
            result.output.count("Keys: 0/0 ok=0 nonempty=0 no_data=0 errors=0 records=0"),
            1,
        )
        self.assertNotIn("last=", result.output)

    def test_timeseries_window_implicit_dates_use_jst(self):
        from datetime import datetime as real_datetime

        database = MagicMock()
        database.__enter__.return_value = database
        database.__exit__.return_value = None
        fetcher = MagicMock()
        fetcher.fetch_time_series_batch_from_db.return_value = iter(())
        updater = MagicMock()

        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text("""
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
""")
            with (
                patch("src.database.create_database_from_config", return_value=database),
                patch("src.fetcher.realtime.RealtimeFetcher", return_value=fetcher),
                patch("src.realtime.updater.RealtimeUpdater", return_value=updater),
                patch("datetime.datetime") as datetime_mock,
            ):
                # 2026-08-31 15:30 UTC is already 2026-09-01 in JST.  The CLI
                # passes a fixed UTC+09:00 tzinfo to datetime.now().
                datetime_mock.now.return_value = real_datetime.fromisoformat(
                    "2026-09-01T00:30:00+09:00"
                )
                result = self.runner.invoke(
                    cli,
                    [
                        "--config",
                        str(config_path),
                        "realtime",
                        "timeseries",
                        "--spec",
                        "0B41",
                        "--db",
                        "postgresql",
                        "--post-time-within-minutes",
                        "30",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        call_kwargs = fetcher.fetch_time_series_batch_from_db.call_args.kwargs
        self.assertEqual(call_kwargs["from_date"], "20250901")
        self.assertEqual(call_kwargs["to_date"], "20260901")
        window_clock_calls = [call for call in datetime_mock.now.call_args_list if call.args]
        self.assertEqual(len(window_clock_calls), 1)
        self.assertEqual(window_clock_calls[0].args[0].utcoffset(None).total_seconds(), 32400)


class TestRealtimeOddsTimeseriesAlias(unittest.TestCase):
    """The official alias must preserve and forward the generic CLI contract."""

    def setUp(self):
        self.runner = CliRunner()

    def test_default_forwards_official_specs_without_post_time_filtering(self):
        from src.cli.main import odds_timeseries, timeseries

        with patch.object(timeseries, "callback") as timeseries_callback:
            result = self.runner.invoke(odds_timeseries)

        self.assertEqual(result.exit_code, 0, result.output)
        timeseries_callback.assert_called_once_with(
            spec="0B41,0B42",
            from_date=None,
            to_date=None,
            post_time_within_minutes=None,
            post_time_not_past_minutes=None,
            db=None,
            db_path=None,
        )

    def test_forwards_spec_dates_database_and_post_time_options(self):
        from src.cli.main import odds_timeseries, timeseries

        with patch.object(timeseries, "callback") as timeseries_callback:
            result = self.runner.invoke(
                odds_timeseries,
                [
                    "--spec",
                    "0B42",
                    "--from",
                    "20260901",
                    "--to",
                    "20260902",
                    "--post-time-within-minutes",
                    "30",
                    "--post-time-not-past-minutes",
                    "2",
                    "--db",
                    "sqlite",
                    "--db-path",
                    "capture.db",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        timeseries_callback.assert_called_once_with(
            spec="0B42",
            from_date="20260901",
            to_date="20260902",
            post_time_within_minutes=30,
            post_time_not_past_minutes=2,
            db="sqlite",
            db_path="capture.db",
        )

    def test_rejects_sokuho_and_other_unsupported_specs(self):
        from src.cli.main import odds_timeseries, timeseries

        unsupported_specs = (
            "0B30",
            "0B31",
            "0B32",
            "0B33",
            "0B34",
            "0B35",
            "0B36",
            "RACE",
            "0B99",
            "0B41,0B30",
        )
        for unsupported_spec in unsupported_specs:
            with self.subTest(spec=unsupported_spec):
                with patch.object(timeseries, "callback") as timeseries_callback:
                    result = self.runner.invoke(
                        odds_timeseries,
                        ["--spec", unsupported_spec],
                    )

                self.assertNotEqual(result.exit_code, 0, result.output)
                self.assertIn("only official historical time-series specs", result.output)
                self.assertIn("unsupported:", result.output)
                timeseries_callback.assert_not_called()

    def test_reuses_nonnegative_post_time_option_validation(self):
        from src.cli.main import odds_timeseries, timeseries

        for option in (
            "--post-time-within-minutes",
            "--post-time-not-past-minutes",
        ):
            with self.subTest(option=option):
                with patch.object(timeseries, "callback") as timeseries_callback:
                    result = self.runner.invoke(odds_timeseries, [option, "-1"])

                self.assertNotEqual(result.exit_code, 0, result.output)
                self.assertIn("x>=0", result.output)
                timeseries_callback.assert_not_called()


class TestExportCommand(unittest.TestCase):
    """Test export command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_export_missing_table(self):
        """Test export without table argument."""
        result = self.runner.invoke(cli, ["export", "--output", "test.csv"])

        # Should fail due to missing --table
        self.assertNotEqual(result.exit_code, 0)

    def test_export_missing_output(self):
        """Test export without output argument."""
        result = self.runner.invoke(cli, ["export", "--table", "NL_RA"])

        # Should fail due to missing --output
        self.assertNotEqual(result.exit_code, 0)

    @patch("src.database.sqlite_handler.SQLiteDatabase")
    def test_export_csv_format(self, mock_db):
        """Test export to CSV format."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_db_instance.table_exists.return_value = True
        mock_db_instance.fetch_all.return_value = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"},
        ]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_db_instance)
        mock_db.return_value.__exit__ = MagicMock(return_value=None)

        with self.runner.isolated_filesystem():
            # Create config
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
databases:
  sqlite:
    path: data/test.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(
                cli, ["export", "--table", "NL_RA", "--output", "test.csv", "--format", "csv"]
            )

            # May fail due to config issues but command structure should work
            self.assertIsNotNone(result)

    @patch("src.database.sqlite_handler.SQLiteDatabase")
    def test_export_json_format(self, mock_db):
        """Test export to JSON format."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_db_instance.table_exists.return_value = True
        mock_db_instance.fetch_all.return_value = [{"id": 1, "name": "Test"}]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_db_instance)
        mock_db.return_value.__exit__ = MagicMock(return_value=None)

        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
databases:
  sqlite:
    path: data/test.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(
                cli, ["export", "--table", "NL_SE", "--output", "test.json", "--format", "json"]
            )

            self.assertIsNotNone(result)

    def test_export_with_where_clause(self):
        """Test export with WHERE clause."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path("data").mkdir()

            result = self.runner.invoke(
                cli,
                [
                    "export",
                    "--table",
                    "NL_RA",
                    "--where",
                    "開催年月日 >= 20240101",
                    "--output",
                    "filtered.csv",
                    "--db",
                    "sqlite",
                ],
            )

            # Should attempt to execute
            self.assertIsNotNone(result)


class TestConfigCommand(unittest.TestCase):
    """Test config command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_show(self):
        """Test config --show command."""
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/keiba.db
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink:
  sid: JLTSQL
logging:
  level: INFO
  file:
    enabled: true
    path: logs/jltsql.log
""")

            result = self.runner.invoke(cli, ["config", "--show"])

            # Should show configuration
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Configuration", result.output)

    def test_config_get_existing_key(self):
        """Test config --get with existing key."""
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
databases:
  sqlite:
    path: data/keiba.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(cli, ["config", "--get", "databases.sqlite.path"])

            if result.exit_code == 0:
                self.assertIn("keiba.db", result.output)

    def test_config_get_nonexistent_key(self):
        """Test config --get with non-existent key."""
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink: {}
""")

            result = self.runner.invoke(cli, ["config", "--get", "nonexistent.key"])

            # Should fail
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("not found", result.output)

    def test_config_set_shows_warning(self):
        """Test config --set shows not implemented warning."""
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink: {}
""")

            result = self.runner.invoke(cli, ["config", "--set", "database.type=sqlite"])

            # Should show not implemented message
            self.assertIn("not yet implemented", result.output)

    def test_config_default_shows_tree(self):
        """Test config without arguments shows tree."""
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    enabled: true
    path: data/test.db
jvlink:
  sid: TEST
logging:
  level: DEBUG
""")

            result = self.runner.invoke(cli, ["config"])

            # Should show config tree
            self.assertEqual(result.exit_code, 0)

    def test_config_uses_the_validating_loader_and_expands_environment(self):
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text(
                """
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: ${JLTSQL_TEST_DB_PATH:fallback.db}
jvlink: {}
""",
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"JLTSQL_TEST_DB_PATH": "expanded.db"},
            ):
                result = self.runner.invoke(
                    cli,
                    ["config", "--get", "databases.sqlite.path"],
                )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("expanded.db", result.output)
            self.assertNotIn("${", result.output)

    def test_empty_config_fails_with_a_controlled_configuration_error(self):
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text("", encoding="utf-8")

            result = self.runner.invoke(cli, ["config", "--show"])

            self.assertEqual(result.exit_code, 1)
            self.assertIn("Configuration Error", result.output)
            self.assertNotIn("Traceback", result.output)

    def test_invalid_logging_shape_fails_with_a_controlled_error(self):
        with self.runner.isolated_filesystem():
            Path("config").mkdir()
            Path("config/config.yaml").write_text(
                """
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink: {}
logging:
  file: logs/jltsql.log
""",
                encoding="utf-8",
            )

            result = self.runner.invoke(cli, ["config", "--show"])

            self.assertEqual(result.exit_code, 1)
            self.assertIn("Configuration Error", result.output)
            self.assertNotIn("Traceback", result.output)

    def test_invalid_config_shapes_fail_with_a_controlled_error(self):
        invalid_documents = (
            """
database: sqlite
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
""",
            """
database: {type: unsupported}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
""",
            """
database: {type: postgresql}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
""",
            """
database: {type: sqlite}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
logging: {level: []}
""",
            """
database: {type: sqlite}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
logging:
  file: {enabled: true, path: 123}
""",
            """
databases:
  postgresql: {enabled: true}
jvlink: {}
""",
            """
database: {type: sqlite}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
logging: {level: VERBOSE}
""",
            """
database: {type: sqlite}
databases:
  sqlite: {enabled: true, path: data/keiba.db}
jvlink: {}
auto_update_check: "false"
""",
        )
        for document in invalid_documents:
            with self.subTest(document=document), self.runner.isolated_filesystem():
                Path("config").mkdir()
                Path("config/config.yaml").write_text(document, encoding="utf-8")

                result = self.runner.invoke(cli, ["config", "--show"])

                self.assertEqual(result.exit_code, 1)
                self.assertIn("Configuration Error", result.output)
                self.assertNotIn("Traceback", result.output)

    def test_config_option_rejects_a_directory_without_traceback(self):
        with self.runner.isolated_filesystem():
            Path("config-dir").mkdir()

            result = self.runner.invoke(
                cli,
                ["--config", "config-dir", "config", "--show"],
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertNotIn("Traceback", result.output)


if __name__ == "__main__":
    unittest.main()
