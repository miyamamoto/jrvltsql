"""Tests for quickstart.py CLI argument parsing.

Tests argument parser behaviour without running the full quickstart flow.
"""

import argparse
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

# We need to import just the argparse setup from quickstart.
# Since quickstart.py does heavy imports (rich, win32com etc.) at module level,
# we reconstruct the parser to test argument parsing in isolation.


def _build_parser() -> argparse.ArgumentParser:
    """Reconstruct the quickstart argument parser (mirrors scripts/quickstart.py main())."""
    parser = argparse.ArgumentParser(
        description="JLTSQL セットアップ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--mode", choices=["simple", "standard", "full", "update"], default=None)
    parser.add_argument("--include-timeseries", action="store_true")
    parser.add_argument("--timeseries-months", type=int, default=12)
    parser.add_argument("--include-realtime", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("-y", "--yes", action="store_true")
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--db-path", type=str, default=None)
    parser.add_argument("--db-type", type=str, choices=["sqlite", "postgresql"], default="sqlite")
    parser.add_argument("--pg-host", type=str, default="localhost")
    parser.add_argument("--pg-port", type=int, default=5432)
    parser.add_argument("--pg-database", type=str, default="keiba")
    parser.add_argument("--pg-user", type=str, default="postgres")
    parser.add_argument("--pg-password", type=str, default=None)
    parser.add_argument("--from-date", type=str, default=None)
    parser.add_argument("--to-date", type=str, default=None)
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--no-odds", action="store_true")
    parser.add_argument("--no-monitor", action="store_true")
    parser.add_argument("--log-file", type=str, default=None)
    parser.add_argument("--source", type=str, choices=["jra", "nar", "all"], default="jra")
    return parser


class TestQuickstartArgParsing:
    """Test argument parsing for quickstart CLI."""

    @pytest.fixture
    def parser(self):
        return _build_parser()

    def test_defaults(self, parser):
        args = parser.parse_args([])
        assert args.mode is None
        assert args.source == "jra"
        assert args.db_type == "sqlite"
        assert args.from_date is None
        assert args.yes is False
        assert args.interactive is False
        assert args.include_timeseries is False
        assert args.timeseries_months == 12

    def test_jra_only(self, parser):
        args = parser.parse_args(["--source", "jra"])
        assert args.source == "jra"

    def test_nar_only(self, parser):
        args = parser.parse_args(["--source", "nar"])
        assert args.source == "nar"

    def test_all_sources(self, parser):
        args = parser.parse_args(["--source", "all"])
        assert args.source == "all"

    def test_invalid_source_rejected(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["--source", "invalid"])

    def test_from_date(self, parser):
        args = parser.parse_args(["--from-date", "20200101"])
        assert args.from_date == "20200101"

    def test_to_date(self, parser):
        args = parser.parse_args(["--to-date", "20241231"])
        assert args.to_date == "20241231"

    def test_years_option(self, parser):
        args = parser.parse_args(["--years", "3"])
        assert args.years == 3

    def test_mode_simple(self, parser):
        args = parser.parse_args(["--mode", "simple"])
        assert args.mode == "simple"

    def test_mode_full(self, parser):
        args = parser.parse_args(["--mode", "full"])
        assert args.mode == "full"

    def test_invalid_mode_rejected(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["--mode", "ultra"])

    def test_postgresql_options(self, parser):
        args = parser.parse_args([
            "--db-type", "postgresql",
            "--pg-host", "db.example.com",
            "--pg-port", "5433",
            "--pg-database", "testdb",
            "--pg-user", "testuser",
            "--pg-password", "secret",
        ])
        assert args.db_type == "postgresql"
        assert args.pg_host == "db.example.com"
        assert args.pg_port == 5433
        assert args.pg_database == "testdb"
        assert args.pg_user == "testuser"
        assert args.pg_password == "secret"

    def test_invalid_db_type_rejected(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args(["--db-type", "mysql"])

    def test_yes_flag(self, parser):
        args = parser.parse_args(["-y"])
        assert args.yes is True

    def test_yes_long_flag(self, parser):
        args = parser.parse_args(["--yes"])
        assert args.yes is True

    def test_interactive_flag(self, parser):
        args = parser.parse_args(["-i"])
        assert args.interactive is True

    def test_combined_flags(self, parser):
        args = parser.parse_args([
            "--mode", "standard",
            "--source", "nar",
            "--from-date", "20230101",
            "-y",
            "--include-timeseries",
            "--timeseries-months", "6",
            "--no-odds",
            "--log-file", "/tmp/test.log",
        ])
        assert args.mode == "standard"
        assert args.source == "nar"
        assert args.from_date == "20230101"
        assert args.yes is True
        assert args.include_timeseries is True
        assert args.timeseries_months == 6
        assert args.no_odds is True
        assert args.log_file == "/tmp/test.log"

    def test_background_flag(self, parser):
        args = parser.parse_args(["--background"])
        assert args.background is True

    def test_no_monitor_flag(self, parser):
        args = parser.parse_args(["--no-monitor"])
        assert args.no_monitor is True

    def test_include_realtime(self, parser):
        args = parser.parse_args(["--include-realtime"])
        assert args.include_realtime is True


class TestQuickstartInteractiveDetection:
    """Test interactive mode detection logic (mirrors quickstart main())."""

    def test_no_args_is_interactive(self):
        """No arguments → interactive mode."""
        parser = _build_parser()
        args = parser.parse_args([])
        use_interactive = args.interactive or (args.mode is None and not args.yes)
        assert use_interactive is True

    def test_mode_specified_is_not_interactive(self):
        """--mode specified → not interactive (unless -i)."""
        parser = _build_parser()
        args = parser.parse_args(["--mode", "simple"])
        use_interactive = args.interactive or (args.mode is None and not args.yes)
        assert use_interactive is False

    def test_yes_flag_is_not_interactive(self):
        """--yes → not interactive."""
        parser = _build_parser()
        args = parser.parse_args(["-y"])
        use_interactive = args.interactive or (args.mode is None and not args.yes)
        assert use_interactive is False

    def test_interactive_flag_overrides(self):
        """-i forces interactive even with --mode."""
        parser = _build_parser()
        args = parser.parse_args(["-i", "--mode", "full"])
        use_interactive = args.interactive or (args.mode is None and not args.yes)
        assert use_interactive is True
