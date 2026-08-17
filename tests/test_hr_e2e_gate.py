"""Regression contract for the HR payout E2E release gate."""

from __future__ import annotations

import runpy
import sqlite3
from pathlib import Path

import pytest

EDGE_CASE_SCRIPT = Path(__file__).parent / "e2e" / "e2e_edge_cases.py"


def _run_hr_payout_check(*, rows: list[tuple[object, ...]]) -> str:
    namespace = runpy.run_path(str(EDGE_CASE_SCRIPT), run_name="hr_edge_case_contract")
    assert "results" in namespace
    assert callable(namespace.get("test_null_zero_values"))
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
        connection.execute(
            "CREATE TABLE NL_HR (DataKubun TEXT, TanUmaban TEXT, TanPay, "
            "FuseirituFlag1 INTEGER, TokubaraiFlag1 INTEGER)"
        )
        connection.executemany("INSERT INTO NL_HR VALUES (?, ?, ?, ?, ?)", rows)
        namespace["results"].clear()
        namespace["test_null_zero_values"](connection)
        matches = [
            status for name, status, _ in namespace["results"] if name.startswith("E-5 ")
        ]
        assert len(matches) == 1
        return matches[0]
    finally:
        connection.close()


@pytest.mark.parametrize(
    "rows,expected",
    (
        ([], "FAIL"),
        ([("1", "01", 100, 0, 0)], "PASS"),
        ([("1", "01", None, 0, 0)], "FAIL"),
        ([("1", "01", "", 0, 0)], "FAIL"),
        ([("1", "01", 0, 0, 0)], "FAIL"),
        ([("1", "01", -1, 0, 0)], "FAIL"),
        ([("1", "01", 0, 1, 0)], "FAIL"),
        ([("1", "00", "", 0, 0)], "FAIL"),
        (
            [
                ("1", "01", 100, 0, 0),
                ("1", "01", 0, 1, 0),
                ("2", "01", 0, 0, 1),
            ],
            "PASS",
        ),
    ),
)
def test_hr_payout_e2e_gate_uses_a_nonempty_normal_win_pool_scope(
    rows: list[tuple[object, ...]], expected: str
) -> None:
    assert _run_hr_payout_check(rows=rows) == expected
