"""The manual all-databases diagnostic counts imports per `import_records` call.

`import_records` resets its statistics on entry, so the tool has to read the
dictionary returned by the current call; comparing `get_statistics()` before and
after compares the previous call with this one. A raised import must also clear
any failed transaction before the next record reuses the connection.
"""

import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "manual" / "all_databases.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("manual_all_databases", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeDatabase:
    def __init__(self):
        self.rollbacks = 0
        self.pending = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def has_pending_transaction(self):
        return self.pending

    def rollback(self):
        self.rollbacks += 1
        self.pending = False

    def fetch_all(self, sql):
        return [{"cnt": 0}]


class _FakeJV:
    def __init__(self, records):
        self._records = list(records)

    def jv_init(self):
        return 0

    def jv_open(self, **kwargs):
        return 0, len(self._records), 0, ""

    def jv_read(self):
        if not self._records:
            return 0, b"", ""
        return 1, self._records.pop(0), "file"

    def jv_close(self):
        return 0


class _FakeFactory:
    def parse(self, data):
        return {"レコード種別ID": "YS", "raw": data}


def _zero():
    return {"records_imported": 0, "records_failed": 0, "batches_processed": 0}


def test_success_is_read_from_the_current_call_and_failures_roll_back(monkeypatch):
    tool = _load_tool()
    database = _FakeDatabase()
    outcomes = [
        {"records_imported": 0, "records_failed": 1, "batches_processed": 1},
        {"records_imported": 1, "records_failed": 0, "batches_processed": 1},
        RuntimeError("simulated import failure"),
        {"records_imported": 1, "records_failed": 0, "batches_processed": 1},
    ]

    class _FakeImporter:
        def __init__(self, db, batch_size=100):
            self.database = db
            self._stats = _zero()

        def import_records(self, records, **kwargs):
            list(records)
            self._stats = _zero()  # like DataImporter: a fresh interval per call
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                database.pending = True
                raise outcome
            self._stats = dict(outcome)
            return dict(outcome)

        def get_statistics(self):
            return dict(self._stats)

    monkeypatch.setattr(tool, "SQLiteDatabase", lambda config: database)
    monkeypatch.setattr(tool, "DataImporter", _FakeImporter)
    monkeypatch.setattr(tool, "JVLinkWrapper", lambda sid: _FakeJV([b"a", b"b", b"c", b"d"]))
    monkeypatch.setattr(tool, "ParserFactory", _FakeFactory)

    tester = tool.DatabaseTester("sqlite", {"path": ":memory:"})
    assert tester.test_data_import(test_data_count=10) is True

    assert tester.results["data_imported"] == 2
    assert database.rollbacks == 1
    assert outcomes == []
