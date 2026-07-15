import inspect

from scripts.background_updater import (
    BackgroundUpdater,
    _is_no_data_error,
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
    assert _is_no_data_error(no_data)
    assert not _is_subscription_error(unrelated)
    assert not _is_no_data_error(unrelated)


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
