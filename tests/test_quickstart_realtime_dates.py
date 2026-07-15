"""Regression tests for quickstart realtime speed-report date/spec coverage.

速報系(0B1x)は当日発表・過去 backfill 不能。開催日を曜日で絞ると祝日月曜など
土日以外の開催日で WE(天候馬場)等が永久欠損するため、全日付を照会する。
また日付指定で WE を供給する 0B14 が SPEED_REPORT_SPECS に含まれ、
JVWatchEvent のイベントキー専用 0B16 が含まれないことを保証する。
"""

import inspect
from datetime import datetime, timedelta

from scripts.quickstart import (
    QuickstartRunner,
    _is_no_data_error,
    _is_subscription_error,
    _jvlink_error_code,
)


def _runner() -> QuickstartRunner:
    return QuickstartRunner({})


def test_recent_race_dates_covers_every_day_not_only_weekends():
    dates = _runner()._get_recent_race_dates(days=7)
    assert len(dates) == 7
    expected = [
        (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(7)
    ]
    assert dates == expected


def test_speed_report_specs_use_date_keyed_weather_dataspec_only():
    codes = [spec for spec, _ in QuickstartRunner.SPEED_REPORT_SPECS]
    # 0B16 requires a JVWatchEvent event key, not a YYYYMMDD key.
    assert "0B14" in codes
    assert "0B16" not in codes


def test_speed_report_specs_dataspec_codes_are_unique():
    codes = [spec for spec, _ in QuickstartRunner.SPEED_REPORT_SPECS]
    assert len(codes) == len(set(codes))


def test_speed_report_specs_include_win5_route():
    codes = [spec for spec, _ in QuickstartRunner.SPEED_REPORT_SPECS]
    assert "0B51" in codes


def test_wrapped_jvlink_errors_are_classified_by_exact_code():
    wrapped = RuntimeError("Historical fetch failed: JVOpen failed (code: -115)")
    assert _jvlink_error_code(wrapped) == -115
    assert _is_subscription_error(wrapped)
    assert not _is_no_data_error(wrapped)

    no_data = RuntimeError("JVRTOpen failed (code: -1)")
    assert _is_no_data_error(no_data)
    assert not _is_subscription_error(no_data)

    assert _is_no_data_error(RuntimeError("No data returned"))
    assert not _is_no_data_error(RuntimeError("No database connection"))


def test_quickstart_does_not_reparse_expanded_realtime_rows():
    rich_source = inspect.getsource(QuickstartRunner._run_fetch_timeseries_rich)
    single_source = inspect.getsource(QuickstartRunner._fetch_single_realtime_spec)

    assert "process_parsed_record" in rich_source
    assert "process_record(" not in rich_source
    assert "process_parsed_record" in single_source
    assert "process_record(" not in single_source
    assert "replace_date_snapshot" in single_source
