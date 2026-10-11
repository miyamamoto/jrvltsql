"""速報 0B11/0B14 の取得ログ（追記型）と RT_WH の発表時刻キーの契約.

JV-Data 仕様書 4.9.0.1「データ提供タイミング・提供単位」:

- 0B11 速報馬体重: 発走約 1 時間前から「馬体重が発表される毎にレコード追加・更新」。
  WH レコードは発表月日時分（HappyoTime）を持つ（フォーマット 101）。
- 0B14 速報開催情報(一括): WE/AV/JC/TC/CC を開催日単位で提供し、取り消された
  変更は以後の応答から消える（※1）。「取得する度に前回取得の情報を破棄し、
  データ取得時点で含まれている情報のみを利用」する。

RT_* は現在状態（0B14 は日付単位の全置換、RT_WH は発表ごとの行）として残し、
「いつ何を持っていたか」は取得ログ（RT_CAPTURE_FETCH / RT_CAPTURE_RECORD）に
追記する。レコードは公式レイアウトから組み立てた合成データのみを使う。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

import scripts.daily_update as daily_update
from scripts.daily_update import UPDATE_SPECS, _select_update_specs, _sync_realtime_spec
from src.database.schema import SCHEMAS, create_all_tables
from src.database.sqlite_handler import SQLiteDatabase
from tests.test_av_official_contract import build_av_record
from tests.test_cc_official_contract import build_cc_record
from tests.test_daily_update import FakeJVLink, _build_rt_ra_record
from tests.test_jc_official_contract import build_jc_record
from tests.test_tc_official_contract import build_tc_record
from tests.test_we_official_contract import build_we_record

# The disposable-schema PostgreSQL fixture; skipped unless
# JLTSQL_RUN_POSTGRESQL_INTEGRATION=1.
from tests.test_wh_official_contract import (
    _primary_key,
    _wh_record,
    postgresql_db,  # noqa: F401
)

RACE_DATE = "20260818"


def _wh(announcement: str, weight: str = "480") -> bytes:
    return _wh_record(
        announcement=announcement,
        weight=weight,
        make_date=RACE_DATE,
        year=RACE_DATE[:4],
        month_day=RACE_DATE[4:],
    )


@pytest.fixture
def database(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "capture.db")})
    with database:
        create_all_tables(database)
        database.commit()
        yield database


def _fetches(database):
    return [
        dict(row)
        for row in database.fetch_all(
            "SELECT * FROM RT_CAPTURE_FETCH ORDER BY RequestedAt, FetchId"
        )
    ]


def _records(database):
    return [
        dict(row)
        for row in database.fetch_all(
            "SELECT * FROM RT_CAPTURE_RECORD ORDER BY CollectedAt, FetchId, Seq"
        )
    ]


def _is_utc_iso(value: str) -> bool:
    parsed = datetime.fromisoformat(value)
    return parsed.utcoffset() == UTC.utcoffset(None) and value.endswith("+00:00")


# --- 0B11 は daily_update の spec ------------------------------------------------


def test_daily_update_allows_0b11():
    specs = [spec for spec, _ in UPDATE_SPECS]

    assert "0B11" in specs
    assert _select_update_specs("0b11,0b14") == [("0B11", 1), ("0B14", 1)]


# --- RT_WH は発表ごとに行を持つ -------------------------------------------------


def test_rt_wh_primary_key_includes_happyo_time():
    assert _primary_key(SCHEMAS["RT_WH"]) == [
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
        "HappyoTime",
        "Umaban",
    ]
    # 蓄積系 NL_WH は従来どおり馬ごとの最新行。
    assert _primary_key(SCHEMAS["NL_WH"]) == [
        "Year",
        "MonthDay",
        "JyoCD",
        "Kaiji",
        "Nichiji",
        "RaceNum",
        "Umaban",
    ]


def test_0b11_keeps_every_announcement_in_rt_wh(database):
    first = _wh("08180930", weight="480")
    corrected = _wh("08180935", weight="486")

    stats = _sync_realtime_spec(
        database=database,
        spec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({RACE_DATE: [first, corrected]}),
        ensure_tables=False,
    )

    assert stats["records_fetched"] == 2
    assert stats["records_failed"] == 0
    rows = database.fetch_all(
        "SELECT Umaban, HappyoTime, BaTaijyu FROM RT_WH ORDER BY HappyoTime, Umaban"
    )
    assert [dict(row) for row in rows] == [
        {"Umaban": 1, "HappyoTime": "08180930", "BaTaijyu": 480},
        {"Umaban": 18, "HappyoTime": "08180930", "BaTaijyu": 999},
        {"Umaban": 1, "HappyoTime": "08180935", "BaTaijyu": 486},
        {"Umaban": 18, "HappyoTime": "08180935", "BaTaijyu": 999},
    ]


def test_0b11_same_announcement_refetch_is_idempotent(database):
    record = _wh("08180930")
    for _ in range(2):
        _sync_realtime_spec(
            database=database,
            spec="0B11",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: [record]}),
            ensure_tables=False,
        )

    assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WH")["n"] == 2
    # 取得ログは追記型なので 2 回分を持つ。
    assert len(_fetches(database)) == 2
    assert len(_records(database)) == 2


# --- 取得ログ --------------------------------------------------------------------


def test_0b11_capture_log_keeps_raw_and_normalized_rows(database):
    first = _wh("08180930", weight="480")
    corrected = _wh("08180935", weight="486")

    _sync_realtime_spec(
        database=database,
        spec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({RACE_DATE: [first, corrected]}),
        ensure_tables=False,
    )

    [fetch] = _fetches(database)
    assert fetch["DataSpec"] == "0B11"
    assert fetch["RequestKey"] == RACE_DATE
    assert fetch["JVRTOpenCode"] == 0
    assert fetch["RecordCount"] == 2
    assert fetch["Status"] == "complete"
    for column in ("RequestedAt", "OpenedAt", "CompletedAt"):
        assert _is_utc_iso(fetch[column]), column
    assert fetch["RequestedAt"] <= fetch["OpenedAt"] <= fetch["CompletedAt"]
    assert fetch["JltsqlVersion"]

    records = _records(database)
    assert [record["Seq"] for record in records] == [1, 2]
    assert {record["FetchId"] for record in records} == {fetch["FetchId"]}
    for record, raw in zip(records, (first, corrected), strict=True):
        assert record["DataSpec"] == "0B11"
        assert record["RequestKey"] == RACE_DATE
        assert record["RecordSpec"] == "WH"
        assert record["DataKubun"] == "1"
        assert _is_utc_iso(record["CollectedAt"])
        assert fetch["OpenedAt"] <= record["CollectedAt"] <= fetch["CompletedAt"]
        assert record["RawEncoding"] == "cp932"
        assert record["RawRecord"].encode("cp932") == raw
        assert record["RawSha256"] == hashlib.sha256(raw).hexdigest()
        # レコード単位で一意なキーだけを列に持つ（WH の馬番は行ごとに違うので NULL）。
        assert (
            record["Year"],
            record["MonthDay"],
            record["JyoCD"],
            record["Kaiji"],
            record["Nichiji"],
            record["RaceNum"],
        ) == ("2026", "0818", "05", "03", "08", "11")
        assert record["Umaban"] is None
    assert [record["HappyoTime"] for record in records] == ["08180930", "08180935"]

    rows = json.loads(records[1]["RowsJson"])
    assert [row["Umaban"] for row in rows] == ["01", "18"]
    assert rows[0]["BaTaijyu"] == "486"
    assert all(not key.startswith("_") for row in rows for key in row)


def test_0b14_capture_log_keeps_every_record_type_and_snapshot(database):
    snapshot = [
        build_we_record(),
        build_av_record(),
        build_jc_record(),
        build_tc_record(),
        build_cc_record(),
    ]

    _sync_realtime_spec(
        database=database,
        spec="0B14",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({RACE_DATE: snapshot}),
        ensure_tables=False,
    )

    [fetch] = _fetches(database)
    assert fetch["DataSpec"] == "0B14"
    assert fetch["RecordCount"] == 5
    records = _records(database)
    assert [record["RecordSpec"] for record in records] == ["WE", "AV", "JC", "TC", "CC"]
    by_type = {record["RecordSpec"]: record for record in records}
    assert by_type["WE"]["RaceNum"] is None
    assert by_type["WE"]["HenkoID"] == "1"
    assert by_type["AV"]["Umaban"] == "01"
    assert by_type["JC"]["Umaban"] == "01"
    assert by_type["TC"]["HappyoTime"] == "08181200"
    for record, raw in zip(records, snapshot, strict=True):
        assert record["RawRecord"].encode("cp932") == raw


def test_0b14_withdrawn_change_leaves_current_state_but_not_the_log(database):
    """※1: 取り消された変更は RT_* から消えるが、取得ログには前回取得分が残る."""
    jc = build_jc_record()
    we = build_we_record()

    for records in ([we, jc], [we]):
        _sync_realtime_spec(
            database=database,
            spec="0B14",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: records}),
            ensure_tables=False,
        )

    # 現在状態: 2 回目の応答に JC が無いので RT_JC は空（日付単位の全置換）。
    assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_JC")["n"] == 0
    assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WE")["n"] == 1

    fetches = _fetches(database)
    assert [fetch["RecordCount"] for fetch in fetches] == [2, 1]
    jc_rows = [record for record in _records(database) if record["RecordSpec"] == "JC"]
    assert len(jc_rows) == 1
    assert jc_rows[0]["FetchId"] == fetches[0]["FetchId"]


def test_0b14_empty_snapshot_is_logged_as_a_complete_fetch(database):
    class EmptySnapshotJVLink(FakeJVLink):
        def jv_rt_open(self, data_spec, key):
            self.opened_keys.append((data_spec, key))
            self._pending = []
            return 0, 0

    _sync_realtime_spec(
        database=database,
        spec="0B14",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=EmptySnapshotJVLink({}),
        ensure_tables=False,
    )

    [fetch] = _fetches(database)
    assert (fetch["JVRTOpenCode"], fetch["RecordCount"], fetch["Status"]) == (0, 0, "complete")
    assert _records(database) == []


def test_no_data_open_is_logged_without_records(database):
    _sync_realtime_spec(
        database=database,
        spec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({}),
        ensure_tables=False,
    )

    [fetch] = _fetches(database)
    assert (fetch["JVRTOpenCode"], fetch["RecordCount"], fetch["Status"]) == (-1, 0, "no_data")
    assert _records(database) == []


def test_specs_outside_the_capture_scope_are_not_logged(database):
    _sync_realtime_spec(
        database=database,
        spec="0B12",
        from_date="20260607",
        to_date="20260607",
        sid="TEST",
        jvlink=FakeJVLink({"20260607": [_build_rt_ra_record()]}),
        ensure_tables=False,
    )

    assert _fetches(database) == []
    assert _records(database) == []


def test_rejected_record_rolls_back_the_log_with_the_import(database):
    with pytest.raises(RuntimeError, match="rejected"):
        _sync_realtime_spec(
            database=database,
            spec="0B11",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: [_wh("08180930"), b"WH1" + b"0" * 37]}),
            ensure_tables=False,
        )

    assert _fetches(database) == []
    assert _records(database) == []
    assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WH")["n"] == 0


# --- summary JSON ----------------------------------------------------------------


def test_summary_json_reports_0b11_with_fetch_ids(tmp_path, monkeypatch):
    from tests.test_daily_update_summary import FakeHistoricalJVLink, _Config

    today = datetime.now().strftime("%Y%m%d")
    record = _wh_record(
        announcement=today[4:] + "0930",
        make_date=today,
        year=today[:4],
        month_day=today[4:],
    )
    realtime = FakeJVLink({today: [record]})
    db_path = tmp_path / "daily.db"

    class _RealtimeFetcher:
        def __init__(self, sid):
            self.jvlink = realtime

    monkeypatch.setattr("src.jvlink.bridge.find_bridge_executable", lambda *a, **k: None)
    monkeypatch.setattr(
        "src.fetcher.base.JVLinkWrapper", lambda sid: FakeHistoricalJVLink((-1, 0, 0, ""))
    )
    monkeypatch.setattr("src.fetcher.realtime.RealtimeFetcher", _RealtimeFetcher)
    monkeypatch.setattr(daily_update, "load_config", lambda path: _Config({"jvlink.sid": "TEST"}))
    monkeypatch.setattr(
        daily_update,
        "create_database_from_config",
        lambda config, db_type_override=None: SQLiteDatabase({"path": str(db_path)}),
    )
    monkeypatch.setattr(daily_update, "setup_logging", lambda **kwargs: None)
    summary_path = tmp_path / "summary.json"

    exit_code = daily_update.main(
        [
            "--days-back",
            "1",
            "--specs",
            "0B11",
            "--require-records",
            "0B11",
            "--summary-json",
            str(summary_path),
        ]
    )

    assert exit_code == 0
    [spec] = json.loads(summary_path.read_text(encoding="utf-8"))["specs"]
    assert spec["dataspec"] == "0B11"
    assert spec["kind"] == "jvrtopen"
    assert spec["status"] == "ok"
    assert spec["records_read"] == 1
    assert spec["records_imported"] == 2
    opened = [open_ for open_ in spec["opens"] if open_["jvrtopen_code"] == 0]
    assert [open_["key"] for open_ in opened] == [today]

    database = SQLiteDatabase({"path": str(db_path)})
    with database:
        fetch_ids = {
            row["FetchId"]: row["RequestKey"]
            for row in database.fetch_all("SELECT FetchId, RequestKey FROM RT_CAPTURE_FETCH")
        }
    assert {open_["fetch_id"]: open_["key"] for open_ in spec["opens"]} == fetch_ids


# --- 既存 DB の RT_WH 移行 -------------------------------------------------------

# The 2.2.0 table: race + horse key, HappyoTime nullable.
_LEGACY_RT_WH = (
    SCHEMAS["RT_WH"]
    .replace(
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, HappyoTime, Umaban)",
        "PRIMARY KEY (Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, Umaban)",
    )
    .replace("HappyoTime TEXT NOT NULL,", "HappyoTime TEXT,")
)


_LEGACY_ROW = (
    "INSERT INTO RT_WH (RecordSpec, DataKubun, MakeDate, Year, MonthDay, JyoCD, "
    "Kaiji, Nichiji, RaceNum, HappyoTime, Umaban, Bamei, BaTaijyu, ZogenFugo, ZogenSa) "
    "VALUES ('WH', '1', '20260818', 2026, 818, '05', 3, 8, 11, '08180930', 1, "
    "'日本馬', 480, '+', 5)"
)

# The operator procedures documented in RELEASE_NOTES.md / record_contracts.md.
_RT_WH_COLUMNS = (
    "RecordSpec, DataKubun, MakeDate, Year, MonthDay, JyoCD, Kaiji, Nichiji, RaceNum, "
    "HappyoTime, Umaban, Bamei, BaTaijyu, ZogenFugo, ZogenSa"
)
SQLITE_RT_WH_MIGRATION = [
    "ALTER TABLE RT_WH RENAME TO RT_WH_legacy_2_2",
    SCHEMAS["RT_WH"],
    f"INSERT INTO RT_WH ({_RT_WH_COLUMNS}) SELECT {_RT_WH_COLUMNS} FROM RT_WH_legacy_2_2",
    "DROP TABLE RT_WH_legacy_2_2",
]
POSTGRESQL_RT_WH_MIGRATION = [
    "LOCK TABLE rt_wh IN ACCESS EXCLUSIVE MODE",
    "ALTER TABLE rt_wh DROP CONSTRAINT rt_wh_pkey, ADD PRIMARY KEY "
    "(year, monthday, jyocd, kaiji, nichiji, racenum, happyotime, umaban)",
]


def _legacy_database(tmp_path):
    database = SQLiteDatabase({"path": str(tmp_path / "legacy.db")})
    database.connect()
    database.execute(_LEGACY_RT_WH)
    database.execute(_LEGACY_ROW)
    database.commit()
    return database


def test_startup_leaves_legacy_rt_wh_alone_and_other_feeds_run(tmp_path):
    """The key migration is an operator step: never run automatically."""
    from src.database.migration import _get_existing_primary_key_columns

    assert _LEGACY_RT_WH != SCHEMAS["RT_WH"]
    database = _legacy_database(tmp_path)
    try:
        create_all_tables(database)

        assert _get_existing_primary_key_columns(database, "RT_WH")[-2:] == [
            "RaceNum",
            "Umaban",
        ]
        assert database.fetch_one("SELECT COUNT(*) AS n FROM RT_WH")["n"] == 1
        # 0B14 (and every other feed) still runs and is captured.
        _sync_realtime_spec(
            database=database,
            spec="0B14",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: [build_we_record()]}),
            ensure_tables=False,
        )
        assert len(_fetches(database)) == 1
    finally:
        database.disconnect()


@pytest.mark.parametrize("ensure_tables", [True, False])
def test_0b11_refuses_a_legacy_rt_wh_before_opening(tmp_path, ensure_tables):
    from src.database.migration import SchemaMigrationError

    database = _legacy_database(tmp_path)
    try:
        if not ensure_tables:
            create_all_tables(database)
        jvlink = FakeJVLink({RACE_DATE: [_wh("08180935", weight="486")]})
        with pytest.raises(SchemaMigrationError, match="RT_WH primary key"):
            _sync_realtime_spec(
                database=database,
                spec="0B11",
                from_date=RACE_DATE,
                to_date=RACE_DATE,
                sid="TEST",
                jvlink=jvlink,
                ensure_tables=ensure_tables,
            )
        assert jvlink.opened_keys == []
        assert database.fetch_one("SELECT BaTaijyu FROM RT_WH")["BaTaijyu"] == 480
    finally:
        database.disconnect()


def test_realtime_updater_refuses_wh_writes_to_a_legacy_rt_wh(tmp_path):
    """Other writers (jltsql realtime start) fail closed too."""
    from src.realtime.updater import RealtimeUpdater

    database = _legacy_database(tmp_path)
    try:
        result = RealtimeUpdater(database).process_record(_wh("08180935", weight="486"))
        results = result if isinstance(result, list) else [result]
        assert results and all(item["success"] is False for item in results)
        assert "RT_WH primary key" in results[0]["error"]
        assert database.fetch_one("SELECT BaTaijyu FROM RT_WH")["BaTaijyu"] == 480
    finally:
        database.disconnect()


def test_documented_sqlite_procedure_migrates_rt_wh_without_losing_rows(tmp_path):
    from src.database.migration import _get_existing_primary_key_columns

    database = _legacy_database(tmp_path)
    try:
        assert (
            database.fetch_one("SELECT COUNT(*) AS n FROM RT_WH WHERE HappyoTime IS NULL")["n"] == 0
        )
        database.execute("BEGIN IMMEDIATE")
        for statement in SQLITE_RT_WH_MIGRATION:
            database.execute(statement)
        database.commit()
        create_all_tables(database)

        assert "HappyoTime" in _get_existing_primary_key_columns(database, "RT_WH")
        _sync_realtime_spec(
            database=database,
            spec="0B11",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: [_wh("08180935", weight="486")]}),
            ensure_tables=False,
        )
        rows = database.fetch_all(
            "SELECT HappyoTime, BaTaijyu, Bamei FROM RT_WH WHERE Umaban = 1 ORDER BY HappyoTime"
        )
        assert [dict(row) for row in rows] == [
            {"HappyoTime": "08180930", "BaTaijyu": 480, "Bamei": "日本馬"},
            {"HappyoTime": "08180935", "BaTaijyu": 486, "Bamei": "日本馬"},
        ]
    finally:
        database.disconnect()


# --- PostgreSQL ------------------------------------------------------------------


def test_postgresql_documented_procedure_and_capture_log(postgresql_db):  # noqa: F811
    from src.database.migration import SchemaMigrationError

    database = postgresql_db
    database.execute(_LEGACY_RT_WH)
    database.execute(_LEGACY_ROW)
    database.commit()

    create_all_tables(database)
    database.commit()
    with pytest.raises(SchemaMigrationError, match="RT_WH primary key"):
        _sync_realtime_spec(
            database=database,
            spec="0B11",
            from_date=RACE_DATE,
            to_date=RACE_DATE,
            sid="TEST",
            jvlink=FakeJVLink({RACE_DATE: [_wh("08180935", weight="486")]}),
            ensure_tables=False,
        )
    database.rollback()

    assert (
        database.fetch_one(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'rt_wh'::regclass AND contype = 'p'"
        )["conname"]
        == "rt_wh_pkey"
    )
    database.begin_transaction()
    for statement in POSTGRESQL_RT_WH_MIGRATION:
        database.execute(statement)
    database.commit()

    _sync_realtime_spec(
        database=database,
        spec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({RACE_DATE: [_wh("08180935", weight="486")]}),
        ensure_tables=False,
    )
    _sync_realtime_spec(
        database=database,
        spec="0B14",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        sid="TEST",
        jvlink=FakeJVLink({RACE_DATE: [build_we_record(), build_jc_record()]}),
        ensure_tables=False,
    )

    assert database.fetch_one("SELECT COUNT(*) AS n FROM rt_wh WHERE umaban = 1")["n"] == 2
    fetches = database.fetch_all(
        "SELECT dataspec, recordcount, status FROM rt_capture_fetch ORDER BY requestedat"
    )
    assert [tuple(row.values()) for row in fetches] == [
        ("0B11", 1, "complete"),
        ("0B14", 2, "complete"),
    ]
    records = database.fetch_all(
        "SELECT recordspec, rawrecord FROM rt_capture_record ORDER BY collectedat, seq"
    )
    assert [row["recordspec"] for row in records] == ["WH", "WE", "JC"]
    assert records[0]["rawrecord"].encode("cp932") == _wh("08180935", weight="486")


def test_postgresql_accepts_raw_records_with_nul_bytes(postgresql_db):  # noqa: F811
    from src.realtime.capture_log import begin_capture

    database = postgresql_db
    create_all_tables(database)
    database.begin_transaction()
    raw = b"WH1" + b"\x00" * 40
    capture = begin_capture(database, "0B11", RACE_DATE, producer="test")
    capture.opened(0)
    capture.append(raw)
    capture.complete()
    database.commit()

    row = database.fetch_one("SELECT rawencoding, rawrecord FROM rt_capture_record")
    assert row["rawencoding"] == "hex"
    assert bytes.fromhex(row["rawrecord"]) == raw


# --- review follow-ups -----------------------------------------------------------


def test_rt_wh_rejects_a_row_without_happyo_time(database):
    """SQLite allows NULL in composite keys; NOT NULL keeps the history unique."""
    from src.database.base import DatabaseError

    with pytest.raises(DatabaseError):
        database.execute(
            "INSERT INTO RT_WH (RecordSpec, Year, MonthDay, JyoCD, Kaiji, Nichiji, "
            "RaceNum, HappyoTime, Umaban) VALUES ('WH', 2026, 818, '05', 3, 8, 11, NULL, 1)"
        )


def test_raw_record_round_trips_cp932_duplicate_code_points(database):
    """0x8790 (NEC) and 0x81E0 (JIS) both decode to the same character."""
    from src.realtime.capture_log import begin_capture

    raw = _wh("08180930")
    raw = raw[:37] + b"\x87\x90" + raw[39:]
    assert raw.decode("cp932").encode("cp932") != raw

    capture = begin_capture(database, "0B11", RACE_DATE, producer="test")
    capture.opened(0)
    capture.append(raw)
    capture.complete()

    [record] = _records(database)
    assert record["RawEncoding"] == "hex"
    assert bytes.fromhex(record["RawRecord"]) == raw
    assert record["RawSha256"] == hashlib.sha256(raw).hexdigest()


def test_error_summary_does_not_name_rolled_back_fetch_ids():
    from src.fetcher.summary import jvrtopen_entry, summarize_jvrtopen_spec

    opens = [jvrtopen_entry(key=RACE_DATE, jvrtopen_code=0, fetch_id="abc")]
    failed = summarize_jvrtopen_spec(
        dataspec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        opens=opens,
        stats={"records_fetched": 1},
        elapsed_seconds=0.0,
        error=RuntimeError("rejected"),
    )
    ok = summarize_jvrtopen_spec(
        dataspec="0B11",
        from_date=RACE_DATE,
        to_date=RACE_DATE,
        opens=opens,
        stats={"records_fetched": 1},
        elapsed_seconds=0.0,
    )

    assert failed["opens"] == [{"key": RACE_DATE, "jvrtopen_code": 0, "fetch_id": None}]
    assert ok["opens"][0]["fetch_id"] == "abc"


def test_summary_json_clears_fetch_ids_when_the_spec_rolls_back(tmp_path, monkeypatch):
    from tests.test_daily_update_summary import FakeHistoricalJVLink, _Config

    today = datetime.now().strftime("%Y%m%d")
    record = _wh_record(
        announcement=today[4:] + "0930", make_date=today, year=today[:4], month_day=today[4:]
    )
    realtime = FakeJVLink({today: [record, b"WH1" + b"0" * 37]})
    db_path = tmp_path / "daily.db"

    class _RealtimeFetcher:
        def __init__(self, sid):
            self.jvlink = realtime

    monkeypatch.setattr("src.jvlink.bridge.find_bridge_executable", lambda *a, **k: None)
    monkeypatch.setattr(
        "src.fetcher.base.JVLinkWrapper", lambda sid: FakeHistoricalJVLink((-1, 0, 0, ""))
    )
    monkeypatch.setattr("src.fetcher.realtime.RealtimeFetcher", _RealtimeFetcher)
    monkeypatch.setattr(daily_update, "load_config", lambda path: _Config({"jvlink.sid": "TEST"}))
    monkeypatch.setattr(
        daily_update,
        "create_database_from_config",
        lambda config, db_type_override=None: SQLiteDatabase({"path": str(db_path)}),
    )
    monkeypatch.setattr(daily_update, "setup_logging", lambda **kwargs: None)
    summary_path = tmp_path / "summary.json"

    with pytest.raises(RuntimeError, match="rejected"):
        daily_update.main(
            ["--days-back", "1", "--specs", "0B11", "--summary-json", str(summary_path)]
        )

    [spec] = json.loads(summary_path.read_text(encoding="utf-8"))["specs"]
    assert spec["status"] == "error"
    assert [open_["fetch_id"] for open_ in spec["opens"]] == [None] * len(spec["opens"])
