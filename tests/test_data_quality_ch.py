"""Normalized CH completeness contracts for the data-quality checker."""

import pytest

from scripts import check_data_quality
from src.database.schema import SCHEMAS
from src.database.sqlite_handler import SQLiteDatabase
from scripts.check_data_quality import DataQualityChecker


def _create_ch_database(
    path,
    *,
    include_results: bool,
    complete_results: bool = False,
    orphan_result: bool = False,
    include_parent: bool = True,
    parent_row: bool = True,
    extra_null_result: bool = False,
    stale_result_revision: bool = False,
    result_count: int | None = None,
) -> None:
    database = SQLiteDatabase({"path": str(path)})
    with database:
        if include_parent:
            database.create_table("NL_CH", SCHEMAS["NL_CH"])
            if parent_row:
                database.execute(
                    "INSERT INTO NL_CH (RecordSpec, DataKubun, MakeDate, ChokyosiCode, "
                    "ChokyosiName) VALUES (?, ?, ?, ?, ?)",
                    ("CH", "1", "20260815", "C1", "Trainer"),
                )
        if include_results:
            database.create_table("NL_CH_SEISEKI", SCHEMAS["NL_CH_SEISEKI"])
            stored_result_count = (
                result_count if result_count is not None else (3 if complete_results else 2)
            )
            database.executemany(
                "INSERT INTO NL_CH_SEISEKI (MakeDate, ChokyosiCode, Num, SetYear) "
                "VALUES (?, ?, ?, ?)",
                [
                    (
                        "20260814" if stale_result_revision else "20260815",
                        "C1",
                        number,
                        2026 - number,
                    )
                    for number in range(1, stored_result_count + 1)
                ],
            )
            if orphan_result:
                database.execute(
                    "INSERT INTO NL_CH_SEISEKI "
                    "(MakeDate, ChokyosiCode, Num, SetYear) VALUES (?, ?, ?, ?)",
                    ("20260815", "ORPHAN", 1, 2026),
                )
            if extra_null_result:
                database.execute(
                    "INSERT INTO NL_CH_SEISEKI "
                    "(MakeDate, ChokyosiCode, Num, SetYear) VALUES (?, ?, ?, ?)",
                    ("20260815", "C1", None, 2026),
                )
        database.commit()


def _ch_issues(report: dict) -> list[dict]:
    return [issue for issue in report["issues"] if issue["table"].startswith("NL_CH")]


def _issue_signatures(issues: list[dict]) -> list[tuple[str, str, str]]:
    return [(issue["table"], issue["message"], issue["severity"]) for issue in issues]


def test_data_quality_rejects_missing_or_incomplete_ch_results_and_accepts_complete(
    tmp_path,
) -> None:
    missing_path = tmp_path / "missing.db"
    _create_ch_database(missing_path, include_results=False)
    missing = _ch_issues(DataQualityChecker(str(missing_path)).check_all())

    incomplete_path = tmp_path / "incomplete.db"
    _create_ch_database(incomplete_path, include_results=True, complete_results=False)
    incomplete = _ch_issues(DataQualityChecker(str(incomplete_path)).check_all())

    complete_path = tmp_path / "complete.db"
    _create_ch_database(complete_path, include_results=True, complete_results=True)
    complete = _ch_issues(DataQualityChecker(str(complete_path)).check_all())

    orphan_path = tmp_path / "orphan.db"
    _create_ch_database(
        orphan_path,
        include_results=True,
        complete_results=True,
        orphan_result=True,
    )
    orphan = _ch_issues(DataQualityChecker(str(orphan_path)).check_all())

    absent_path = tmp_path / "absent-parent.db"
    _create_ch_database(
        absent_path,
        include_parent=False,
        include_results=True,
        complete_results=True,
    )
    absent = _ch_issues(DataQualityChecker(str(absent_path)).check_all())

    empty_path = tmp_path / "empty-parent.db"
    _create_ch_database(
        empty_path,
        include_parent=True,
        parent_row=False,
        include_results=True,
        result_count=0,
    )
    empty = _ch_issues(DataQualityChecker(str(empty_path)).check_all())

    extra_path = tmp_path / "extra-null.db"
    _create_ch_database(
        extra_path,
        include_results=True,
        complete_results=True,
        extra_null_result=True,
    )
    extra = _ch_issues(DataQualityChecker(str(extra_path)).check_all())

    stale_path = tmp_path / "stale-result-revision.db"
    _create_ch_database(
        stale_path,
        include_results=True,
        complete_results=True,
        stale_result_revision=True,
    )
    stale = _ch_issues(DataQualityChecker(str(stale_path)).check_all())

    assert _issue_signatures(missing) == [
        (
            "NL_CH_SEISEKI",
            "normalized trainer results table is missing",
            "CRITICAL",
        )
    ]
    assert _issue_signatures(incomplete) == [
        (
            "NL_CH_SEISEKI",
            "1 trainer(s) do not have exactly result rows Num=1,2,3",
            "CRITICAL",
        )
    ]
    assert complete == []
    assert _issue_signatures(orphan) == [
        (
            "NL_CH_SEISEKI",
            "1 normalized trainer result row(s) have no parent",
            "CRITICAL",
        )
    ]
    assert _issue_signatures(absent) == [
        ("NL_CH", "normalized trainer parent table is missing", "CRITICAL"),
        (
            "NL_CH_SEISEKI",
            "3 normalized trainer result row(s) have no parent",
            "CRITICAL",
        ),
    ]
    assert _issue_signatures(empty) == [
        ("NL_CH", "normalized trainer parent table is empty", "CRITICAL"),
    ]
    assert _issue_signatures(extra) == [
        (
            "NL_CH_SEISEKI",
            "1 trainer(s) do not have exactly result rows Num=1,2,3",
            "CRITICAL",
        )
    ]
    assert _issue_signatures(stale) == [
        (
            "NL_CH_SEISEKI",
            "3 normalized trainer result row(s) have a different MakeDate than parent",
            "CRITICAL",
        )
    ]


def test_data_quality_reports_unreadable_ch_result_schema_instead_of_crashing(
    tmp_path,
) -> None:
    database_path = tmp_path / "unreadable.db"
    _create_ch_database(database_path, include_results=False)
    database = SQLiteDatabase({"path": str(database_path)})
    with database:
        database.execute("CREATE TABLE NL_CH_SEISEKI (ChokyosiCode TEXT)")
        database.commit()

    issues = _ch_issues(DataQualityChecker(str(database_path)).check_all())

    assert _issue_signatures(issues) == [
        (
            "NL_CH_SEISEKI",
            "normalized trainer results could not be verified",
            "CRITICAL",
        )
    ]


def test_data_quality_cli_rejects_critical_ch_issues_and_accepts_complete(
    tmp_path,
    monkeypatch,
) -> None:
    stale_path = tmp_path / "cli-stale.db"
    _create_ch_database(
        stale_path,
        include_results=True,
        complete_results=True,
        stale_result_revision=True,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["check_data_quality.py", "--db-path", str(stale_path)],
    )
    with pytest.raises(SystemExit) as stale_exit:
        check_data_quality.main()

    complete_path = tmp_path / "cli-complete.db"
    _create_ch_database(complete_path, include_results=True, complete_results=True)
    monkeypatch.setattr(
        "sys.argv",
        ["check_data_quality.py", "--db-path", str(complete_path)],
    )
    with pytest.raises(SystemExit) as complete_exit:
        check_data_quality.main()

    assert stale_exit.value.code == 1
    assert complete_exit.value.code == 0
