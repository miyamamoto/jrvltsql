"""Regression contract for the HR payout E2E release gate."""

from __future__ import annotations

import runpy
import sqlite3
from pathlib import Path

EDGE_CASE_SCRIPT = Path(__file__).parent / "e2e" / "e2e_edge_cases.py"


def _run_hr_payout_check(*, with_eligible_row: bool) -> str:
    namespace = runpy.run_path(str(EDGE_CASE_SCRIPT), run_name="hr_edge_case_contract")
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE NL_SE (DataKubun TEXT, IJyoCD TEXT, Odds INTEGER, "
            "KakuteiJyuni INTEGER, Time INTEGER, Umaban INTEGER)"
        )
        connection.execute(
            "CREATE TABLE NL_RA (JyoCD TEXT, Year INTEGER, MonthDay INTEGER, "
            "RaceNum INTEGER, Kyori INTEGER, DataKubun TEXT)"
        )
        connection.execute("CREATE TABLE NL_HR (DataKubun TEXT, TanPay INTEGER)")
        if with_eligible_row:
            connection.execute("INSERT INTO NL_HR VALUES ('1', 100)")
        namespace["results"].clear()
        namespace["test_null_zero_values"](connection)
        return next(
            status for name, status, _ in namespace["results"] if name.startswith("E-5 ")
        )
    finally:
        connection.close()


def test_hr_payout_e2e_gate_rejects_an_empty_scope_and_accepts_valid_data() -> None:
    assert [_run_hr_payout_check(with_eligible_row=value) for value in (False, True)] == [
        "FAIL",
        "PASS",
    ]
