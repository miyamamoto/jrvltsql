"""Tests for batch processor setup-range splitting decisions."""

from src.importer.batch import BatchProcessor


def test_option_3_setup_range_splits_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 3) is True


def test_option_4_setup_range_does_not_split_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 4) is False


def test_diff_options_do_not_split_long_periods():
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 1) is False
    assert BatchProcessor._should_split_setup_range("20200101", "20220101", 2) is False
