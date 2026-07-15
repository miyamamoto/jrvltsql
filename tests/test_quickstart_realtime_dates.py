"""Regression tests for quickstart realtime speed-report date/spec coverage.

速報系(0B1x)は当日発表・過去 backfill 不能。開催日を曜日で絞ると祝日月曜など
土日以外の開催日で WE(天候馬場)等が永久欠損するため、全日付を照会する。
また WE を供給する 0B14/0B16 が SPEED_REPORT_SPECS に含まれることを保証する。
"""

from datetime import datetime, timedelta

from scripts.quickstart import QuickstartRunner


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


def test_speed_report_specs_include_both_we_dataspecs():
    codes = [spec for spec, _ in QuickstartRunner.SPEED_REPORT_SPECS]
    # WE(天候馬場状態) is delivered only by 0B14 (一括) and 0B16 (指定).
    assert "0B14" in codes
    assert "0B16" in codes


def test_speed_report_specs_dataspec_codes_are_unique():
    codes = [spec for spec, _ in QuickstartRunner.SPEED_REPORT_SPECS]
    assert len(codes) == len(set(codes))
