import inspect
from unittest.mock import MagicMock

from scripts.background_updater import (
    BackgroundUpdater,
    _is_realtime_no_data_error,
    _is_subscription_error,
    _jvlink_error_code,
)


def test_background_realtime_specs_include_date_keyed_win5_only():
    specs = {spec for spec, _ in BackgroundUpdater.REALTIME_SPECS}

    assert "0B14" in specs
    assert "0B51" in specs
    assert "0B16" not in specs


def test_background_error_classification_uses_exact_codes():
    wrapped = RuntimeError("Realtime fetch failed: JVRTOpen failed: -115")
    no_data = RuntimeError("Realtime fetch failed: JVRTOpen failed: -1")
    unrelated = RuntimeError("processed -1150 rows with no database connection")

    assert _jvlink_error_code(wrapped) == -115
    assert _is_subscription_error(wrapped)
    assert not _is_realtime_no_data_error(no_data)
    assert not _is_subscription_error(unrelated)
    assert not _is_realtime_no_data_error(unrelated)


def test_background_does_not_hide_jvread_minus_two():
    assert not _is_realtime_no_data_error(
        RuntimeError("Realtime fetch failed: JVRead failed (code: -2)")
    )


def test_background_does_not_hide_jvread_minus_one_exception():
    assert not _is_realtime_no_data_error(
        RuntimeError("Realtime fetch failed: JVRead failed: -1 (no data)")
    )


def test_background_realtime_paths_use_realtime_table_router():
    realtime_source = inspect.getsource(BackgroundUpdater._run_realtime_update)
    timeseries_source = inspect.getsource(BackgroundUpdater._run_time_series_update)

    assert "RealtimeUpdater" in realtime_source
    assert "DataImporter" not in realtime_source
    assert "process_parsed_record" in realtime_source
    assert "process_record(" not in realtime_source
    assert "replace_date_snapshot" in realtime_source
    assert "RealtimeUpdater" in timeseries_source
    assert "timeseries=True" in timeseries_source
    assert "DataImporter" not in timeseries_source
    assert "process_parsed_record" in timeseries_source
    assert "process_record(" not in timeseries_source
    assert "create_all_tables" not in realtime_source
    assert "create_all_tables" not in timeseries_source
    assert "create_all_tables" in inspect.getsource(
        BackgroundUpdater._ensure_realtime_schema
    )


def test_background_realtime_loop_survives_transient_poll_error():
    updater = BackgroundUpdater.__new__(BackgroundUpdater)
    updater._running = True
    updater._stop_event = MagicMock()
    updater._stop_event.is_set.return_value = False
    updater._stop_event.wait.return_value = False
    updater.schedule_manager = MagicMock()
    updater.schedule_manager.get_update_interval.return_value = (1, "test")
    updater._stats = {
        "realtime_errors": 0,
        "last_realtime_update": None,
    }

    calls = 0

    def run_poll(_reason):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary JV-Link failure")
        updater._running = False

    updater._run_realtime_update = run_poll

    updater._realtime_update_loop()

    assert calls == 2
    assert updater._stats["realtime_errors"] == 1
    assert updater._stats["last_realtime_update"] is not None
