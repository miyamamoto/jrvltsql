"""Regression tests for race-day operational recovery paths."""

import sqlite3
from types import SimpleNamespace

from scripts import raceday_verify


def _master_connection(
    *,
    include_results: bool,
    complete_results: bool = False,
    orphan_result: bool = False,
    include_parent: bool = True,
    parent_row: bool = True,
    extra_null_result: bool = False,
    result_count: int | None = None,
):
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE NL_UM (KettoNum TEXT PRIMARY KEY);
        CREATE TABLE NL_KS (KisyuCode TEXT PRIMARY KEY);
        INSERT INTO NL_UM VALUES ('H1');
        INSERT INTO NL_KS VALUES ('J1');
        """
    )
    if include_parent:
        connection.execute(
            "CREATE TABLE NL_CH (MakeDate TEXT, ChokyosiCode TEXT PRIMARY KEY)"
        )
        if parent_row:
            connection.execute("INSERT INTO NL_CH VALUES ('20260815', 'C1')")
    if include_results:
        connection.execute(
            "CREATE TABLE NL_CH_SEISEKI ("
            "MakeDate TEXT, ChokyosiCode TEXT, Num INTEGER, "
            "PRIMARY KEY (ChokyosiCode, Num))"
        )
        stored_result_count = (
            result_count if result_count is not None else (3 if complete_results else 2)
        )
        connection.executemany(
            "INSERT INTO NL_CH_SEISEKI VALUES (?, ?, ?)",
            [("20260815", "C1", number) for number in range(1, stored_result_count + 1)],
        )
        if orphan_result:
            connection.execute(
                "INSERT INTO NL_CH_SEISEKI VALUES (?, ?, ?)",
                ("20260815", "ORPHAN", 1),
            )
        if extra_null_result:
            connection.execute(
                "INSERT INTO NL_CH_SEISEKI VALUES (?, ?, ?)",
                ("20260815", "C1", None),
            )
    return connection


def test_result_completion_issue_recommends_race_fetch(monkeypatch):
    """Missing central results must direct operators to the RACE data spec."""
    counts = iter((12, 0, 0))
    monkeypatch.setattr(raceday_verify, "q", lambda *args, **kwargs: next(counts))
    monkeypatch.setattr(
        raceday_verify,
        "datetime",
        type("AfterRacing", (), {"now": staticmethod(lambda: SimpleNamespace(hour=17))}),
    )
    issues = []

    raceday_verify.check_se_results(None, "2026", "0815", issues)

    assert issues == ["Race results only 0% complete after 17:00 -- fetch RACE"]

    counts = iter((12, 12, 0))
    issues = []
    raceday_verify.check_se_results(None, "2026", "0815", issues)

    assert issues == []


def test_schema_check_requires_normalized_ch_results(monkeypatch):
    monkeypatch.setattr(
        raceday_verify,
        "table_exists",
        lambda _connection, table_name: table_name != "NL_CH_SEISEKI",
    )
    issues = []

    raceday_verify.check_schema(None, issues)

    assert issues == ["Missing NL_ tables: ['NL_CH_SEISEKI']"]


def test_master_check_rejects_missing_or_incomplete_ch_results_and_accepts_complete():
    missing = _master_connection(include_results=False)
    missing_issues = []
    raceday_verify.check_master_data(missing, missing_issues)
    missing.close()

    incomplete = _master_connection(include_results=True, complete_results=False)
    incomplete_issues = []
    raceday_verify.check_master_data(incomplete, incomplete_issues)
    incomplete.close()

    complete = _master_connection(include_results=True, complete_results=True)
    complete_issues = []
    raceday_verify.check_master_data(complete, complete_issues)
    complete.close()

    orphan = _master_connection(include_results=True, complete_results=True, orphan_result=True)
    orphan_issues = []
    raceday_verify.check_master_data(orphan, orphan_issues)
    orphan.close()

    absent = _master_connection(
        include_parent=False,
        include_results=True,
        complete_results=True,
    )
    absent_issues = []
    raceday_verify.check_master_data(absent, absent_issues)
    absent.close()

    empty = _master_connection(
        include_parent=True,
        parent_row=False,
        include_results=True,
        result_count=0,
    )
    empty_issues = []
    raceday_verify.check_master_data(empty, empty_issues)
    empty.close()

    extra = _master_connection(
        include_results=True,
        complete_results=True,
        extra_null_result=True,
    )
    extra_issues = []
    raceday_verify.check_master_data(extra, extra_issues)
    extra.close()

    assert missing_issues == ["NL_CH_SEISEKI missing -- run create-tables and full DIFN reimport"]
    assert incomplete_issues == [
        "NL_CH_SEISEKI incomplete for 1 trainer(s) -- run full DIFN reimport"
    ]
    assert complete_issues == []
    assert orphan_issues == ["NL_CH_SEISEKI has 1 orphan row(s) -- run full DIFN reimport"]
    assert absent_issues == ["NL_CH missing -- run create-tables and full DIFN reimport"]
    assert empty_issues == ["NL_CH empty -- run full DIFN reimport"]
    assert extra_issues == [
        "NL_CH_SEISEKI incomplete for 1 trainer(s) -- run full DIFN reimport"
    ]


def test_master_check_reports_unreadable_ch_result_schema_instead_of_crashing():
    connection = _master_connection(include_results=False)
    connection.execute("CREATE TABLE NL_CH_SEISEKI (ChokyosiCode TEXT)")
    issues = []

    raceday_verify.check_master_data(connection, issues)
    connection.close()

    assert issues == ["NL_CH_SEISEKI completeness could not be verified -- inspect schema"]


def test_post_phase_uses_race_once_to_recover_missing_payouts(monkeypatch):
    """H1 is carried by RACE, so payout recovery must not request DIFN."""
    no_op_checks = (
        "check_schema",
        "check_rt_data_freshness",
        "check_race_count_by_venue",
        "check_se_results",
        "check_payout_completeness",
        "check_nl_rt_consistency",
        "check_master_data",
        "check_duplicate_race_ids",
    )
    for name in no_op_checks:
        monkeypatch.setattr(raceday_verify, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(raceday_verify, "check_nl_today", lambda *args, **kwargs: {})
    monkeypatch.setattr(raceday_verify, "check_rt_today", lambda *args, **kwargs: {})

    calls = []
    monkeypatch.setattr(
        raceday_verify,
        "run_fetch",
        lambda *args: calls.append(args) or True,
    )
    args = SimpleNamespace(date="20260815", fetch=True, db="data/test.db")
    nl_checks = {
        "NL_H1  (payouts)     ": 0,
        "NL_RA  (race header) ": 12,
    }

    raceday_verify.run_phase_post(None, args, "2026", "0815", [], nl_checks, {})

    assert calls == [("RACE", "20260815", "20260815", 1, "data/test.db")]
