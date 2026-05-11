from datetime import datetime

from scripts.daily_update import _effective_option


def test_daily_update_escalates_old_difn_to_setup_option():
    old_year = datetime.now().year - 2

    assert _effective_option("DIFN", 1, f"{old_year}0101") == 4


def test_daily_update_keeps_recent_difn_incremental():
    today = datetime.now().strftime("%Y%m%d")

    assert _effective_option("DIFN", 1, today) == 1
    assert _effective_option("RACE", 2, today) == 2
