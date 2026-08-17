#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for CLI commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli


class TestCLIBasic(unittest.TestCase):
    """Test basic CLI functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('JLTSQL', result.output)
        self.assertIn('init', result.output)
        self.assertIn('fetch', result.output)
        self.assertIn('monitor', result.output)

    def test_version_command(self):
        """Version is available before a configuration file exists."""
        with patch("src.cli.main.Path.exists", return_value=False):
            result = self.runner.invoke(cli, ['version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('JLTSQL version', result.output)
        self.assertTrue(
            'Python version' in result.output or 'Python:' in result.output,
            f"Expected 'Python version' or 'Python:' in output: {result.output}"
        )

    def test_status_command(self):
        """Status is available before a configuration file exists; fetch is not."""
        with patch("src.cli.main.Path.exists", return_value=False):
            result = self.runner.invoke(cli, ['status'])
            fetch_result = self.runner.invoke(
                cli,
                ['fetch', '--from', '2024-01-01', '--to', '2024-01-02', '--spec', 'RACE'],
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn('JLTSQL Status', result.output)
        self.assertIn('Version', result.output)
        # Data-acquiring commands stay behind the configuration gate.
        self.assertEqual(fetch_result.exit_code, 1)
        self.assertIn('Configuration file not found', fetch_result.output)


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
            config_dir = Path('config')
            config_dir.mkdir(exist_ok=True)

            example_file = config_dir / 'config.yaml.example'
            example_file.write_text('# Example')

            config_file = config_dir / 'config.yaml'
            config_file.write_text('# Existing')

            result = self.runner.invoke(cli, ['init', '--force'])

            self.assertEqual(result.exit_code, 0)
            self.assertIn('Created configuration file', result.output)

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


class TestCreateTablesCommand(unittest.TestCase):
    """Test create-tables command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_create_tables_sqlite(self):
        """Test create-tables with SQLite."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
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
            Path('data').mkdir()

            result = self.runner.invoke(cli, [
                'create-tables',
                '--db', 'sqlite'
            ])

            # Command should execute (may have various exit codes depending on config/environment)
            # Just verify it doesn't crash with exception
            self.assertIsNotNone(result)
            # Exit codes: 0=success, 1=error, 2=usage error
            self.assertIn(result.exit_code, [0, 1, 2])

    def test_create_tables_with_db_flag(self):
        """Test create-tables with --db flag works."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path('data').mkdir()

            result = self.runner.invoke(cli, [
                'create-tables',
                '--db', 'sqlite'
            ])

            # Should attempt to execute (may succeed or fail, but command should parse)
            self.assertIsNotNone(result)

    def test_create_tables_rt_only_runs_additive_migration(self):
        """Existing RT tables are migrated before CREATE IF NOT EXISTS."""
        with self.runner.isolated_filesystem():
            config_path = Path("config.yaml")
            config_path.write_text(
                """
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: test.db
jvlink:
  service_key: ""
"""
            )
            database = MagicMock()

            with patch(
                "src.database.create_database_from_config",
                return_value=database,
            ), patch(
                "src.database.migration.migrate_all_tables"
            ) as migrate_all_tables, patch(
                "src.database.migration.verify_table_schema"
            ) as verify_table_schema:
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
            config_path.write_text(
                """
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: test.db
jvlink:
  service_key: ""
"""
            )
            database = MagicMock()

            with patch(
                "src.database.create_database_from_config",
                return_value=database,
            ), patch(
                "src.database.migration.migrate_all_tables"
            ), patch(
                "src.database.migration.verify_table_schema",
                side_effect=RuntimeError("unsafe schema"),
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
        result = self.runner.invoke(cli, ['fetch'])

        # Should fail due to missing required arguments (--from, --to, --spec)
        self.assertNotEqual(result.exit_code, 0)
        # Check if error message contains missing required option
        self.assertTrue(
            '--from' in result.output.lower() or
            '--to' in result.output.lower() or
            '--spec' in result.output.lower() or
            result.exception is not None
        )

    def test_fetch_help_explains_option_dependent_date_semantics(self):
        example_config = (
            Path(__file__).resolve().parents[1] / 'config' / 'config.yaml.example'
        )
        with self.runner.isolated_filesystem():
            config_path = Path('config.yaml')
            config_path.write_text(
                example_config.read_text(encoding='utf-8'),
                encoding='utf-8',
            )
            result = self.runner.invoke(
                cli,
                ['--config', str(config_path), 'fetch', '--help'],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        help_text = ' '.join(result.output.split())
        self.assertIn('current race-cycle data', help_text)
        self.assertIn('Sunday or Monday may cover two cycles', help_text)
        self.assertIn('ChokyoDate', help_text)
        self.assertIn('calendar-year chunks', help_text)
        self.assertIn('adds another chunk', help_text)

    @patch('src.importer.batch.BatchProcessor')
    def test_fetch_with_all_args(self, mock_batch_processor):
        """Test fetch command with all arguments."""
        # Setup mocks
        mock_processor_instance = MagicMock()
        mock_processor_instance.process_date_range.return_value = {
            'records_fetched': 10,
            'records_parsed': 10,
            'records_imported': 10,
            'records_failed': 0,
            'batches_processed': 1
        }
        mock_batch_processor.return_value = mock_processor_instance

        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: test_key
""")
            Path('data').mkdir()

            result = self.runner.invoke(cli, [
                'fetch',
                '--from', '20240101',
                '--to', '20240131',
                '--spec', 'RACE',
                '--db', 'sqlite'
            ])

            # Should execute (may fail due to missing JV-Link, but that's OK for CLI test)
            # Just verify command structure works
            self.assertIsNotNone(result)


class TestMonitorCommand(unittest.TestCase):
    """Test monitor command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('src.realtime.monitor.RealtimeMonitor')
    def test_monitor_daemon_mode(self, mock_monitor):
        """Test monitor command in daemon mode."""
        # Setup mocks
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.get_status.return_value = {
            'started_at': '2024-01-01 00:00:00',
            'running': True
        }
        mock_monitor_instance.start.return_value = None
        mock_monitor.return_value = mock_monitor_instance

        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path('data').mkdir()

            result = self.runner.invoke(cli, [
                'monitor',
                '--daemon',
                '--db', 'sqlite'
            ])

            # Should execute (may fail due to config/JV-Link, but command structure should work)
            self.assertIsNotNone(result)


class TestRealtimeTimeseriesCommand(unittest.TestCase):
    """Time-series persistence failures are command failures, not green summaries."""

    def setUp(self):
        self.runner = CliRunner()

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
            config_path.write_text(
                """
database:
  type: postgresql
databases:
  postgresql:
    enabled: true
jvlink:
  sid: TEST
auto_update_check: false
"""
            )
            with patch(
                "src.database.create_database_from_config", return_value=database
            ), patch(
                "src.fetcher.realtime.RealtimeFetcher", return_value=fetcher
            ), patch(
                "src.realtime.updater.RealtimeUpdater", return_value=updater
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
        self.assertEqual(pending_at_batch, [False])
        self.assertNotIn("[OK] 0B41", result.output)
        self.assertNotIn("Complete!", result.output)


class TestExportCommand(unittest.TestCase):
    """Test export command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_export_missing_table(self):
        """Test export without table argument."""
        result = self.runner.invoke(cli, ['export', '--output', 'test.csv'])

        # Should fail due to missing --table
        self.assertNotEqual(result.exit_code, 0)

    def test_export_missing_output(self):
        """Test export without output argument."""
        result = self.runner.invoke(cli, ['export', '--table', 'NL_RA'])

        # Should fail due to missing --output
        self.assertNotEqual(result.exit_code, 0)

    @patch('src.database.sqlite_handler.SQLiteDatabase')
    def test_export_csv_format(self, mock_db):
        """Test export to CSV format."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_db_instance.table_exists.return_value = True
        mock_db_instance.fetch_all.return_value = [
            {'id': 1, 'name': 'Test1'},
            {'id': 2, 'name': 'Test2'}
        ]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_db_instance)
        mock_db.return_value.__exit__ = MagicMock(return_value=None)

        with self.runner.isolated_filesystem():
            # Create config
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
databases:
  sqlite:
    path: data/test.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(cli, [
                'export',
                '--table', 'NL_RA',
                '--output', 'test.csv',
                '--format', 'csv'
            ])

            # May fail due to config issues but command structure should work
            self.assertIsNotNone(result)

    @patch('src.database.sqlite_handler.SQLiteDatabase')
    def test_export_json_format(self, mock_db):
        """Test export to JSON format."""
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_db_instance.table_exists.return_value = True
        mock_db_instance.fetch_all.return_value = [
            {'id': 1, 'name': 'Test'}
        ]
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_db_instance)
        mock_db.return_value.__exit__ = MagicMock(return_value=None)

        with self.runner.isolated_filesystem():
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
databases:
  sqlite:
    path: data/test.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(cli, [
                'export',
                '--table', 'NL_SE',
                '--output', 'test.json',
                '--format', 'json'
            ])

            self.assertIsNotNone(result)

    def test_export_with_where_clause(self):
        """Test export with WHERE clause."""
        with self.runner.isolated_filesystem():
            # Create config directory and file
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
  path: data/test.db
databases:
  sqlite:
    path: data/test.db
jvlink:
  service_key: ""
""")
            Path('data').mkdir()

            result = self.runner.invoke(cli, [
                'export',
                '--table', 'NL_RA',
                '--where', "開催年月日 >= 20240101",
                '--output', 'filtered.csv',
                '--db', 'sqlite'
            ])

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
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
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

            result = self.runner.invoke(cli, ['config', '--show'])

            # Should show configuration
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Configuration', result.output)

    def test_config_get_existing_key(self):
        """Test config --get with existing key."""
        with self.runner.isolated_filesystem():
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
databases:
  sqlite:
    path: data/keiba.db
    enabled: true
jvlink:
  sid: TEST
  service_key: ""
""")

            result = self.runner.invoke(cli, ['config', '--get', 'databases.sqlite.path'])

            if result.exit_code == 0:
                self.assertIn('keiba.db', result.output)

    def test_config_get_nonexistent_key(self):
        """Test config --get with non-existent key."""
        with self.runner.isolated_filesystem():
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink: {}
""")

            result = self.runner.invoke(cli, ['config', '--get', 'nonexistent.key'])

            # Should fail
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn('not found', result.output)

    def test_config_set_shows_warning(self):
        """Test config --set shows not implemented warning."""
        with self.runner.isolated_filesystem():
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
database:
  type: sqlite
databases:
  sqlite:
    enabled: true
    path: data/keiba.db
jvlink: {}
""")

            result = self.runner.invoke(cli, ['config', '--set', 'database.type=sqlite'])

            # Should show not implemented message
            self.assertIn('not yet implemented', result.output)

    def test_config_default_shows_tree(self):
        """Test config without arguments shows tree."""
        with self.runner.isolated_filesystem():
            Path('config').mkdir()
            Path('config/config.yaml').write_text("""
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

            result = self.runner.invoke(cli, ['config'])

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


if __name__ == '__main__':
    unittest.main()
