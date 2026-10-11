"""``jltsql realtime fetch``: one bounded speed-report fetch, then exit.

``realtime start`` is a resident loop, which does not fit a collector that
runs one command per request. ``realtime fetch`` opens each date key of the
selected date-keyed JVRTOpen specs once (JV-Link IF 4.9.0.1 p.22: key
``YYYYMMDD`` for 開催日単位), imports, appends 0B11/0B14 to the capture log
(docs/capture_log.md), writes the schema-1 summary (docs/fetch_summary.md)
and exits: 0 ok, 1 error, 2 usage, 3 a --require-records spec got nothing.
Records are synthetic, built from the official byte layout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.database.sqlite_handler import SQLiteDatabase
from tests.cli_test_support import CliRunner
from tests.test_daily_update import FakeJVLink
from tests.test_we_official_contract import build_we_record
from tests.test_wh_official_contract import _wh_record

RACE_DATE = "20260818"


class SpecJVLink(FakeJVLink):
    """Records by (spec, key); a plain key maps to every spec."""

    def jv_rt_open(self, data_spec, key):
        self.opened_keys.append((data_spec, key))
        records = self.records_by_key.get((data_spec, key), self.records_by_key.get(key, []))
        self._pending = list(records)
        return (0, len(self._pending)) if self._pending else (-1, 0)


EXAMPLE_CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.yaml.example"


def _wh(announcement: str = "08180930") -> bytes:
    return _wh_record(announcement=announcement, make_date=RACE_DATE, year="2026", month_day="0818")


@pytest.fixture
def run_fetch(tmp_path, monkeypatch):
    """Invoke the CLI against a temporary SQLite DB and a fake JV-Link."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        EXAMPLE_CONFIG.read_text(encoding="utf-8").replace(
            "auto_update_check: true", "auto_update_check: false"
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "fetch.db"
    opened: list = []

    def _run(records_by_key, *args, jvlink=None):
        fake = jvlink or SpecJVLink(records_by_key)
        opened.append(fake)

        class _RealtimeFetcher:
            def __init__(self, sid):
                self.jvlink = fake

        monkeypatch.setattr("src.fetcher.realtime.RealtimeFetcher", _RealtimeFetcher)
        monkeypatch.setattr(
            "src.database.create_database_from_config",
            lambda config, db_type_override=None: SQLiteDatabase({"path": str(db_path)}),
        )
        from src.cli.main import cli

        return CliRunner().invoke(cli, ["--config", str(config_path), "realtime", "fetch", *args])

    _run.db_path = db_path
    _run.opened = opened
    return _run


def _summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fetches_each_date_key_once_and_exits(run_fetch, tmp_path):
    summary_path = tmp_path / "summary.json"

    result = run_fetch(
        {("0B11", RACE_DATE): [_wh()]},
        "--specs",
        "0B11,0B14",
        "--date",
        RACE_DATE,
        "--summary-json",
        str(summary_path),
    )

    assert result.exit_code == 0, result.output
    fake = run_fetch.opened[0]
    assert fake.opened_keys == [("0B11", RACE_DATE), ("0B14", RACE_DATE)]
    document = _summary(summary_path)
    assert document["schema_version"] == 1
    assert document["generator"] == "jltsql realtime fetch"
    assert document["outcome"] == "ok"
    assert (document["from_date"], document["to_date"]) == (RACE_DATE, RACE_DATE)
    wh, we = document["specs"]
    assert (wh["dataspec"], wh["kind"], wh["status"], wh["records_imported"]) == (
        "0B11",
        "jvrtopen",
        "ok",
        2,
    )
    assert (we["dataspec"], we["status"]) == ("0B14", "no_data")

    database = SQLiteDatabase({"path": str(run_fetch.db_path)})
    with database:
        fetches = {
            row["FetchId"]: row["Producer"]
            for row in database.fetch_all("SELECT FetchId, Producer FROM RT_CAPTURE_FETCH")
        }
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WH")["n"] == 2
    assert set(fetches.values()) == {"jltsql realtime fetch"}
    assert {open_["fetch_id"] for spec in document["specs"] for open_ in spec["opens"]} == set(
        fetches
    )


def test_date_range_opens_every_key(run_fetch):
    result = run_fetch({}, "--specs", "0B14", "--from-date", "20260817", "--to-date", "20260818")

    assert result.exit_code == 0, result.output
    assert run_fetch.opened[0].opened_keys == [("0B14", "20260817"), ("0B14", "20260818")]


def test_required_spec_without_records_exits_3(run_fetch, tmp_path):
    summary_path = tmp_path / "summary.json"

    result = run_fetch(
        {("0B14", RACE_DATE): [build_we_record()]},
        "--specs",
        "0B11,0B14",
        "--date",
        RACE_DATE,
        "--require-records",
        "0B11",
        "--summary-json",
        str(summary_path),
    )

    assert result.exit_code == 3, result.output
    document = _summary(summary_path)
    assert document["outcome"] == "required_records_missing"
    assert document["requirement_failures"] == [
        {"dataspec": "0B11", "status": "no_data", "read_count": None}
    ]


@pytest.mark.parametrize(
    "args",
    [
        ("--specs", "0B30", "--date", RACE_DATE),  # race-keyed odds: own commands
        ("--specs", "0B16", "--date", RACE_DATE),  # event-keyed
        ("--specs", "RACE", "--date", RACE_DATE),  # JVOpen
        ("--specs", "0B14", "--date", "2026-08-18"),
        ("--specs", "0B14"),  # no window
        ("--specs", "0B14", "--date", RACE_DATE, "--from-date", RACE_DATE),
        ("--specs", "0B14", "--from-date", "20260819", "--to-date", "20260818"),
        ("--specs", "0B14", "--date", RACE_DATE, "--require-records", "0B11"),
    ],
)
def test_usage_errors_exit_2_without_opening(run_fetch, tmp_path, args):
    summary_path = tmp_path / "summary.json"

    result = run_fetch({}, *args, "--summary-json", str(summary_path))

    assert result.exit_code == 2, result.output
    assert run_fetch.opened[0].opened_keys == []
    assert _summary(summary_path)["outcome"] == "usage_error"


def test_failed_spec_exits_1_and_keeps_the_summary(run_fetch, tmp_path):
    summary_path = tmp_path / "summary.json"

    result = run_fetch(
        {RACE_DATE: [_wh(), b"WH1" + b"0" * 37]},
        "--specs",
        "0B11",
        "--date",
        RACE_DATE,
        "--summary-json",
        str(summary_path),
    )

    assert result.exit_code == 1
    document = _summary(summary_path)
    assert document["outcome"] == "error"
    [spec] = document["specs"]
    assert spec["status"] == "error"
    assert [open_["fetch_id"] for open_ in spec["opens"]] == [None]
    database = SQLiteDatabase({"path": str(run_fetch.db_path)})
    with database:
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_CAPTURE_FETCH")["n"] == 0
