from datetime import datetime

import pytest

from scripts.daily_update import (
    _effective_option,
    _error_code_from_exception,
    _force_incremental_options,
    _parse_ignored_error_codes,
    _select_update_specs,
)


def test_daily_update_escalates_old_difn_to_setup_option():
    old_year = datetime.now().year - 2

    assert _effective_option("DIFN", 1, f"{old_year}0101") == 4


def test_daily_update_keeps_recent_difn_incremental():
    today = datetime.now().strftime("%Y%m%d")

    assert _effective_option("DIFN", 1, today) == 1
    assert _effective_option("RACE", 2, today) == 2


def test_daily_update_selects_requested_specs():
    assert _select_update_specs("race,difn") == [("RACE", 2), ("DIFN", 1)]


def test_daily_update_rejects_unknown_specs():
    with pytest.raises(ValueError):
        _select_update_specs("RACE,NOPE")


def test_daily_update_can_force_incremental_options():
    assert _force_incremental_options([("RACE", 2), ("DIFN", 1)]) == [("RACE", 1), ("DIFN", 1)]


def test_daily_update_parses_ignored_error_codes():
    assert _parse_ignored_error_codes("-303,-2") == {-303, -2}
    assert _error_code_from_exception(Exception("JVOpen failed (code: -303)")) == -303
