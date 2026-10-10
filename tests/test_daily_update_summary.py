"""daily_update の取得結果サマリ・ログ・exit code の契約.

本番の JRA collector で RACE(option=1) が空のまま全 job が緑だった
（JVOpen の戻り値も件数も残らず、0 件は「データなし」として成功扱い）。
ここでは JV-Link を模した fake で JVOpen の戻り値ごとに、

  - spec 単位のサマリ JSON（--summary-json）に何が返ったかが残ること
  - ファイルログに戻り値が残ること
  - --require-records 指定の spec が 0 件なら非 0 exit になること
  - エラー（-2 / -301 等）は従来どおり伝播し、サマリにもコードが残ること

を確かめる。戻り値の意味は JV-Link インターフェース仕様書 4.9.0.1 に従う:
JVOpen 0=正常 / -1=該当データ無し（又は最新バージョン DL 選択）/
-2=セットアップダイアログでキャンセル（p.54）、readcount/downloadcount/
lastfiletimestamp は p.19、JVStatus は p.24、JVRead は p.25/p.56。

レコードは tests/fixtures/record_factory の合成 RA のみを使い、実データは
入れない。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import pytest
import structlog

import scripts.daily_update as daily_update
from src.database.sqlite_handler import SQLiteDatabase
from src.fetcher.summary import SUMMARY_SCHEMA_VERSION
from src.jvlink.wrapper import JVLinkError
from tests.fixtures.record_factory import make_ra_record

TODAY = datetime.now().strftime("%Y%m%d")


class FakeHistoricalJVLink:
    """JVOpen/JVStatus/JVRead/JVClose を仕様どおりの戻り値で返す fake."""

    def __init__(self, open_result, records=(), open_error=None):
        self.open_result = open_result
        self.records = list(records)
        self.open_error = open_error
        self.opened = []
        self._pending = []

    def jv_init(self):
        return 0

    def jv_open(self, data_spec, fromtime, option=1):
        self.opened.append((data_spec, fromtime, option))
        if self.open_error is not None:
            raise self.open_error
        code, read_count, download_count, last_ts = self.open_result
        self._pending = list(self.records) if code == 0 else []
        self._download_count = download_count
        return code, read_count, download_count, last_ts

    def jv_status(self):
        return self._download_count

    def jv_read(self):
        if self._pending:
            buff = self._pending.pop(0)
            return len(buff), buff, "RAVM20261010.jvd"
        if self._pending is not None:
            # 物理ファイル末尾で -1、次の呼び出しで 0 (IF p.25)。
            self._pending = None
            return -1, None, "RAVM20261010.jvd"
        return 0, None, None

    def jv_close(self):
        return 0

    def jv_file_delete(self, filename):
        return 0

    def cleanup(self):
        return None


class FakeRealtimeJVLink:
    """全キーで JVRTOpen -1（該当データ無し）を返す fake."""

    def __init__(self):
        self.opened = []

    def jv_init(self):
        return 0

    def jv_rt_open(self, data_spec, key):
        self.opened.append((data_spec, key))
        return -1, 0

    def jv_read(self):
        return 0, None, None

    def jv_close(self):
        return 0


class _Config:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


@pytest.fixture(autouse=True)
def _restore_logging(monkeypatch):
    """main() reconfigures stdlib logging and structlog; undo both afterwards.

    The test session runs with structlog unconfigured (conftest skips the
    import-time setup), and later tests use structlog.testing.capture_logs,
    which cannot see loggers cached on first use. So the run here must not
    cache loggers, and structlog gets its previous configuration back.
    """
    real_setup_logging = daily_update.setup_logging

    def _setup_logging_without_cache(**kwargs):
        real_setup_logging(**kwargs)
        structlog.configure(cache_logger_on_first_use=False)

    monkeypatch.setattr(daily_update, "setup_logging", _setup_logging_without_cache)
    structlog_config = structlog.get_config()
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.configure(**structlog_config)


@pytest.fixture
def run_daily(tmp_path, monkeypatch):
    """daily_update.main を fake JV-Link と一時 SQLite で走らせる."""

    db_path = tmp_path / "daily.db"
    log_path = tmp_path / "logs" / "daily.log"

    def _run(fake, *extra_args, realtime_fake=None):
        monkeypatch.setattr(
            "src.jvlink.bridge.find_bridge_executable", lambda *a, **k: None
        )
        monkeypatch.setattr("src.fetcher.base.JVLinkWrapper", lambda sid: fake)
        if realtime_fake is not None:

            class _RealtimeFetcher:
                def __init__(self, sid):
                    self.jvlink = realtime_fake

            monkeypatch.setattr("src.fetcher.realtime.RealtimeFetcher", _RealtimeFetcher)
        monkeypatch.setattr(
            daily_update, "load_config", lambda path: _Config({"jvlink.sid": "TEST"})
        )
        monkeypatch.setattr(
            daily_update,
            "create_database_from_config",
            lambda config, db_type_override=None: SQLiteDatabase({"path": str(db_path)}),
        )
        argv = ["--days-back", "1", "--log-file", str(log_path), *extra_args]
        return daily_update.main(argv)

    _run.log_path = log_path
    return _run


def _read_summary(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _race_record():
    return make_ra_record(
        make_date=TODAY, year=TODAY[:4], month_day=TODAY[4:], race_num="01"
    )


class TestSuccessfulOpen:
    def test_summary_records_what_jvopen_returned_and_what_was_imported(
        self, run_daily, tmp_path
    ):
        fake = FakeHistoricalJVLink((0, 1, 1, "20261010123456"), records=[_race_record()])
        summary_path = tmp_path / "summary.json"

        exit_code = run_daily(
            fake,
            "--specs", "RACE",
            "--force-incremental",
            "--summary-json", str(summary_path),
        )

        assert exit_code == 0
        doc = _read_summary(summary_path)
        assert doc["schema_version"] == SUMMARY_SCHEMA_VERSION
        assert doc["outcome"] == "ok"
        assert doc["exit_code"] == 0
        [spec] = doc["specs"]
        assert spec["dataspec"] == "RACE"
        assert spec["option"] == 1
        assert spec["status"] == "ok"
        assert spec["jvopen_code"] == 0
        assert spec["read_count"] == 1
        assert spec["download_count"] == 1
        assert spec["lastfiletimestamp"] == "20261010123456"
        assert spec["records_read"] == 1
        assert spec["records_parsed"] == 1
        assert spec["records_imported"] == 1
        assert spec["records_failed"] == 0
        assert spec["records_out_of_range"] == 0
        assert spec["elapsed_seconds"] >= 0
        # 送った fromtime をそのまま残す（実際に JV-Link へ渡った値）。
        assert spec["fromtimes"] == [fromtime for _, fromtime, _ in fake.opened]
        assert spec["opens"] == [
            {
                "fromtime": fake.opened[0][1],
                "jvopen_code": 0,
                "read_count": 1,
                "download_count": 1,
                "lastfiletimestamp": "20261010123456",
                "recovery": False,
            }
        ]

    def test_require_records_passes_when_files_were_listed(self, run_daily, tmp_path):
        fake = FakeHistoricalJVLink((0, 1, 0, "20261010123456"), records=[_race_record()])

        exit_code = run_daily(
            fake, "--specs", "RACE", "--force-incremental", "--require-records", "RACE"
        )

        assert exit_code == 0

    def test_jvopen_result_is_written_to_the_log_file(self, run_daily):
        fake = FakeHistoricalJVLink((0, 1, 0, "20261010123456"), records=[_race_record()])

        run_daily(fake, "--specs", "RACE", "--force-incremental")

        log_text = run_daily.log_path.read_text(encoding="utf-8")
        assert "Data stream opened" in log_text
        assert "20261010123456" in log_text
        assert "daily_update spec finished" in log_text

    def test_stdout_count_line_is_unchanged(self, run_daily, capsys):
        """下流 scheduler が正規表現で読む行の形は変えない."""
        fake = FakeHistoricalJVLink((0, 1, 0, "20261010123456"), records=[_race_record()])

        run_daily(fake, "--specs", "RACE", "--force-incremental")

        out = capsys.readouterr().out
        assert "[daily-sync] RACE fetched=1 parsed=1 imported=1 failed=0" in out


class TestNoData:
    @pytest.mark.parametrize(
        "open_result",
        [
            pytest.param((-1, 0, 0, ""), id="jvopen-minus-1"),
            pytest.param((0, 0, 0, ""), id="jvopen-0-with-zero-files"),
        ],
    )
    def test_no_data_is_recorded_not_silenced(self, run_daily, tmp_path, open_result):
        summary_path = tmp_path / "summary.json"

        exit_code = run_daily(
            FakeHistoricalJVLink(open_result),
            "--specs", "RACE",
            "--force-incremental",
            "--summary-json", str(summary_path),
        )

        # 既定動作は後方互換（0 件でも exit 0）。
        assert exit_code == 0
        [spec] = _read_summary(summary_path)["specs"]
        assert spec["status"] == "no_data"
        assert spec["jvopen_code"] == open_result[0]
        assert spec["read_count"] == 0
        assert spec["records_read"] == 0
        log_text = run_daily.log_path.read_text(encoding="utf-8")
        assert "[warning" in log_text.lower()
        assert "no data" in log_text.lower()

    def test_no_data_without_requirement_keeps_stdout_and_stderr_quiet(
        self, run_daily, capsys
    ):
        """TOKU や非開催日の 0Bxx は正当に空になる。空を失敗にするのは --require-records."""
        run_daily(FakeHistoricalJVLink((-1, 0, 0, "")), "--specs", "RACE", "--force-incremental")

        captured = capsys.readouterr()
        assert captured.err == ""
        assert "[daily-sync] RACE fetched=0 parsed=0 imported=0 failed=0" in captured.out

    @pytest.mark.parametrize("open_result", [(-1, 0, 0, ""), (0, 0, 0, "")])
    def test_require_records_fails_when_spec_read_nothing(
        self, run_daily, tmp_path, open_result
    ):
        summary_path = tmp_path / "summary.json"

        exit_code = run_daily(
            FakeHistoricalJVLink(open_result),
            "--specs", "RACE",
            "--force-incremental",
            "--require-records", "race",
            "--summary-json", str(summary_path),
        )

        assert exit_code == daily_update.EXIT_REQUIRED_RECORDS_MISSING
        doc = _read_summary(summary_path)
        assert doc["outcome"] == "required_records_missing"
        assert doc["exit_code"] == daily_update.EXIT_REQUIRED_RECORDS_MISSING
        assert doc["required_specs"] == ["RACE"]
        assert doc["requirement_failures"] == [
            {"dataspec": "RACE", "status": "no_data", "read_count": 0}
        ]

    def test_realtime_spec_with_no_data_for_every_key_is_required(
        self, run_daily, tmp_path
    ):
        summary_path = tmp_path / "summary.json"
        realtime = FakeRealtimeJVLink()

        exit_code = run_daily(
            FakeHistoricalJVLink((-1, 0, 0, "")),
            "--specs", "0B12",
            "--require-records", "0B12",
            "--summary-json", str(summary_path),
            realtime_fake=realtime,
        )

        assert exit_code == daily_update.EXIT_REQUIRED_RECORDS_MISSING
        [spec] = _read_summary(summary_path)["specs"]
        assert spec["kind"] == "jvrtopen"
        assert spec["status"] == "no_data"
        assert spec["read_count"] is None
        assert spec["records_read"] == 0
        assert [o["jvrtopen_code"] for o in spec["opens"]] == [-1] * len(realtime.opened)
        assert [o["key"] for o in spec["opens"]] == [key for _, key in realtime.opened]


class TestErrors:
    def test_setup_dialog_cancel_minus_2_propagates_with_code_in_summary(
        self, run_daily, tmp_path
    ):
        summary_path = tmp_path / "summary.json"

        with pytest.raises(Exception, match="cancel"):
            run_daily(
                FakeHistoricalJVLink((-2, 0, 0, "")),
                "--specs", "RACE",
                "--force-incremental",
                "--summary-json", str(summary_path),
            )

        doc = _read_summary(summary_path)
        assert doc["outcome"] == "error"
        assert doc["exit_code"] == 1
        [spec] = doc["specs"]
        assert spec["status"] == "error"
        assert spec["jvopen_code"] == -2
        assert "cancel" in spec["error"]

    def test_jvopen_error_code_is_captured_from_the_raised_error(
        self, run_daily, tmp_path
    ):
        summary_path = tmp_path / "summary.json"
        fake = FakeHistoricalJVLink(
            None, open_error=JVLinkError("JVOpen failed", error_code=-301)
        )

        with pytest.raises(Exception, match="-301"):
            run_daily(
                fake,
                "--specs", "RACE",
                "--force-incremental",
                "--summary-json", str(summary_path),
            )

        [spec] = _read_summary(summary_path)["specs"]
        assert spec["status"] == "error"
        assert spec["jvopen_code"] == -301
        assert spec["opens"] == [
            {
                "fromtime": fake.opened[0][1],
                "jvopen_code": -301,
                "read_count": None,
                "download_count": None,
                "lastfiletimestamp": None,
                "recovery": False,
            }
        ]

    def test_ignored_code_is_recorded_as_skipped(self, run_daily, tmp_path):
        summary_path = tmp_path / "summary.json"
        fake = FakeHistoricalJVLink(
            None, open_error=JVLinkError("JVOpen failed", error_code=-303)
        )

        exit_code = run_daily(
            fake,
            "--specs", "RACE",
            "--force-incremental",
            "--ignore-jvopen-error-codes", "-303",
            "--summary-json", str(summary_path),
        )

        assert exit_code == 0
        [spec] = _read_summary(summary_path)["specs"]
        assert spec["status"] == "skipped"
        assert spec["jvopen_code"] == -303

    def test_required_spec_that_was_skipped_fails(self, run_daily):
        fake = FakeHistoricalJVLink(
            None, open_error=JVLinkError("JVOpen failed", error_code=-303)
        )

        exit_code = run_daily(
            fake,
            "--specs", "RACE",
            "--force-incremental",
            "--ignore-jvopen-error-codes", "-303",
            "--require-records", "RACE",
        )

        assert exit_code == daily_update.EXIT_REQUIRED_RECORDS_MISSING


class TestArguments:
    def test_usage_error_still_writes_the_summary(self, run_daily, tmp_path):
        summary_path = tmp_path / "summary.json"

        exit_code = run_daily(
            FakeHistoricalJVLink((0, 0, 0, "")),
            "--specs", "RACE",
            "--require-records", "NOPE",
            "--summary-json", str(summary_path),
        )

        assert exit_code == 2
        doc = _read_summary(summary_path)
        assert doc["outcome"] == "usage_error"
        assert doc["exit_code"] == 2
        assert doc["specs"] == []

    def test_unwritable_log_file_falls_back_to_console(self, run_daily, tmp_path, capsys):
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("x", encoding="utf-8")
        fake = FakeHistoricalJVLink((0, 1, 0, "20261010123456"), records=[_race_record()])

        exit_code = run_daily(
            fake,
            "--specs", "RACE",
            "--force-incremental",
            "--log-file", str(blocker / "daily.log"),
        )

        assert exit_code == 0
        assert "file logging disabled" in capsys.readouterr().err

    def test_required_spec_must_be_selected(self, run_daily):
        exit_code = run_daily(
            FakeHistoricalJVLink((0, 0, 0, "")),
            "--specs", "MING",
            "--require-records", "RACE",
        )

        assert exit_code == 2

    def test_unknown_required_spec_is_rejected(self, run_daily):
        exit_code = run_daily(
            FakeHistoricalJVLink((0, 0, 0, "")),
            "--specs", "RACE",
            "--require-records", "NOPE",
        )

        assert exit_code == 2


def test_failure_before_jvopen_does_not_inherit_previous_spec_opens(
    run_daily, tmp_path, monkeypatch
):
    """RACE の open 結果を、JVOpen 前に落ちた次の spec のものとして報告しない."""
    import src.importer.batch as batch

    real_create_all_tables = batch.create_all_tables
    calls = []

    def _create_all_tables(database):
        calls.append(database)
        if len(calls) > 1:
            raise RuntimeError("schema setup failed")
        return real_create_all_tables(database)

    monkeypatch.setattr(batch, "create_all_tables", _create_all_tables)
    summary_path = tmp_path / "summary.json"
    fake = FakeHistoricalJVLink((0, 1, 0, "20261010123456"), records=[_race_record()])

    with pytest.raises(RuntimeError, match="schema setup failed"):
        run_daily(
            fake,
            "--specs", "RACE,DIFN",
            "--summary-json", str(summary_path),
        )

    race, difn = _read_summary(summary_path)["specs"]
    assert race["read_count"] == 1
    assert difn["status"] == "error"
    assert difn["opens"] == []
    assert difn["jvopen_code"] is None
    assert difn["records_read"] == 0


def test_config_log_path_is_anchored_at_the_project_root(monkeypatch):
    """スケジューラの cwd（読み取り専用でありうる）ではなく PROJECT_ROOT 基準."""
    seen = {}
    monkeypatch.setattr(daily_update, "setup_logging", lambda **kwargs: seen.update(kwargs))

    daily_update._configure_logging(_Config({"logging.file.path": "./logs/x.log"}), None)
    assert seen["log_file"] == str(daily_update.PROJECT_ROOT / "logs" / "x.log")

    daily_update._configure_logging(_Config({}), None)
    assert seen["log_file"] == str(daily_update.PROJECT_ROOT / "logs" / "jltsql.log")

    daily_update._configure_logging(_Config({}), "/abs/explicit.log")
    assert seen["log_file"] == "/abs/explicit.log"
