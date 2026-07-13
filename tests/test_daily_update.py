from datetime import datetime

import pytest

from scripts.daily_update import (
    UPDATE_SPECS,
    _effective_option,
    _error_code_from_exception,
    _force_incremental_options,
    _is_realtime_spec,
    _iter_date_keys,
    _parse_ignored_error_codes,
    _select_update_specs,
    _sync_realtime_spec,
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


def test_daily_update_includes_speed_report_specs():
    specs = [spec for spec, _ in UPDATE_SPECS]

    assert "0B12" in specs
    assert "0B15" in specs


def test_daily_update_selects_speed_report_specs_case_insensitively():
    assert _select_update_specs("0b12,0b15") == [("0B12", 1), ("0B15", 1)]


def test_is_realtime_spec_detects_jvrtopen_specs():
    assert _is_realtime_spec("0B12")
    assert _is_realtime_spec("0b15")
    assert not _is_realtime_spec("RACE")
    assert not _is_realtime_spec("DIFN")


def test_iter_date_keys_is_inclusive_and_ordered():
    assert _iter_date_keys("20260606", "20260608") == [
        "20260606",
        "20260607",
        "20260608",
    ]
    assert _iter_date_keys("20260607", "20260607") == ["20260607"]
    assert _iter_date_keys("20260608", "20260607") == []


class FakeJVLink:
    """Minimal JV-Link double for the speed-report drain loop."""

    def __init__(self, records_by_key):
        self.records_by_key = records_by_key
        self.opened_keys = []
        self.close_count = 0
        self.init_count = 0
        self._pending = []

    def jv_init(self):
        self.init_count += 1
        return 0

    def jv_rt_open(self, data_spec, key):
        self.opened_keys.append((data_spec, key))
        self._pending = list(self.records_by_key.get(key, []))
        if not self._pending:
            return -1, 0
        return 0, len(self._pending)

    def jv_read(self):
        if self._pending:
            buff = self._pending.pop(0)
            return len(buff), buff, "RT"
        return 0, None, None

    def jv_close(self):
        self.close_count += 1
        return 0


def _build_rt_ra_record() -> bytes:
    """Full-layout RA record with corner data for RT_RA import tests."""
    data = bytearray(b" " * 1272)
    data[0:2] = b"RA"
    data[2:3] = b"1"  # DataKubun: new
    data[3:11] = b"20260607"
    data[11:15] = b"2026"
    data[15:19] = b"0607"
    data[19:21] = b"05"
    data[21:23] = b"03"
    data[23:25] = b"01"
    data[25:27] = b"11"
    data[873:877] = b"1545"  # extended-layout HassoTime
    corner_sets = [
        (b"1", b"1", b"02,04,06"),
        (b"2", b"1", b"04,02,06"),
        (b"3", b"1", b"06,02,04"),
        (b"4", b"1", b"01,02,03"),
    ]
    for idx, (corner, syukaisu, jyuni) in enumerate(corner_sets):
        base = 981 + idx * 72
        data[base:base + 1] = corner
        data[base + 1:base + 2] = syukaisu
        data[base + 2:base + 2 + len(jyuni)] = jyuni
    return bytes(data)


@pytest.fixture
def rt_database(tmp_path):
    from src.database.schema import SCHEMAS
    from src.database.sqlite_handler import SQLiteDatabase

    database = SQLiteDatabase({"path": str(tmp_path / "daily_rt.db")})
    with database:
        database.execute(SCHEMAS["RT_RA"])
        database.commit()
        yield database


def test_sync_realtime_spec_imports_speed_report_records(rt_database):
    record = _build_rt_ra_record()
    jvlink = FakeJVLink({"20260607": [record]})

    stats = _sync_realtime_spec(
        database=rt_database,
        spec="0B12",
        from_date="20260606",
        to_date="20260608",
        sid="JLTSQL",
        jvlink=jvlink,
    )

    assert stats["records_fetched"] == 1
    assert stats["records_imported"] == 1
    assert stats["records_failed"] == 0
    assert [key for _, key in jvlink.opened_keys] == [
        "20260606",
        "20260607",
        "20260608",
    ]

    rows = rt_database.fetch_all("SELECT * FROM RT_RA")
    assert len(rows) == 1
    row = rows[0]
    assert row["TsukaJyuni"] == "02,04,06"
    assert row["Corner4"] == "4"
    assert row["TsukaJyuni4"] == "01,02,03"
    assert row["HassoTime"] == "1545"


def test_sync_realtime_spec_is_idempotent_across_reruns(rt_database):
    record = _build_rt_ra_record()

    for _ in range(2):
        jvlink = FakeJVLink({"20260607": [record]})
        stats = _sync_realtime_spec(
            database=rt_database,
            spec="0B12",
            from_date="20260607",
            to_date="20260607",
            sid="JLTSQL",
            jvlink=jvlink,
        )
        assert stats["records_imported"] == 1

    rows = rt_database.fetch_all("SELECT COUNT(*) AS cnt FROM RT_RA")
    assert rows[0]["cnt"] == 1


def test_sync_realtime_spec_stops_before_open_when_schema_setup_fails(
    rt_database, monkeypatch
):
    jvlink = FakeJVLink({"20260607": [_build_rt_ra_record()]})

    def fail_schema_setup(_database):
        raise RuntimeError("unsafe RT_SE schema")

    monkeypatch.setattr(
        "src.database.schema.create_all_tables",
        fail_schema_setup,
    )

    with pytest.raises(RuntimeError, match="unsafe RT_SE schema"):
        _sync_realtime_spec(
            database=rt_database,
            spec="0B12",
            from_date="20260607",
            to_date="20260607",
            sid="JLTSQL",
            jvlink=jvlink,
        )

    assert jvlink.opened_keys == []


def test_sync_realtime_spec_fails_when_any_record_is_rejected(rt_database):
    jvlink = FakeJVLink({"20260607": [_build_rt_ra_record()]})

    class RejectingUpdater:
        def process_record(self, _record):
            return {
                "operation": "insert",
                "table": "RT_SE",
                "success": False,
                "error": "obsolete schema",
            }

    with pytest.raises(RuntimeError, match="rejected 1 record"):
        _sync_realtime_spec(
            database=rt_database,
            spec="0B12",
            from_date="20260607",
            to_date="20260607",
            sid="JLTSQL",
            jvlink=jvlink,
            updater=RejectingUpdater(),
        )


def test_sync_realtime_spec_fails_on_transport_error(rt_database):
    class ReadFailingJVLink(FakeJVLink):
        def jv_read(self):
            return -202, None, None

    jvlink = ReadFailingJVLink({"20260607": [b"placeholder"]})

    with pytest.raises(RuntimeError, match="JVRead failed: -202"):
        _sync_realtime_spec(
            database=rt_database,
            spec="0B12",
            from_date="20260607",
            to_date="20260607",
            sid="JLTSQL",
            jvlink=jvlink,
        )
