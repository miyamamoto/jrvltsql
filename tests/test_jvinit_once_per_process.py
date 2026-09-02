"""JVInit lifecycle contract: one JV-Link session per process.

公式仕様の JVInit はアプリケーションの初期化であって JVOpen ごとの前処理では
ない。ここでは COM を差し替えた ``JVLinkWrapper`` 越しに、同一プロセスで fetch を
何度呼んでも JVInit は 1 回きりで、JVOpen と JVClose だけが fetch ごとに 1 組ずつ
回ることを固定する。単一 dataspec・option=1（日次差分）の既存契約も併せて固定し、
この lifecycle refactor が取得挙動を動かしていないことを示す。
"""

from unittest.mock import MagicMock, patch

import pytest

from src.fetcher.base import FetcherError
from src.fetcher.historical import HistoricalFetcher
from src.jvlink.bridge import JVLinkBridge, JVLinkBridgeError
from src.jvlink.wrapper import JVLinkError, JVLinkWrapper


class RecordingJVLinkCom:
    """固定シグネチャの COM ダブル。公式の呼び出し順をそのまま記録する。

    ``MagicMock`` と違い、引数を落とした呼び出しはテスト失敗になる。
    """

    def __init__(self, *, init_result=0, records=("RA-RECORD",), open_result=None):
        self.init_result = init_result
        self.records = list(records)
        self.open_result = open_result
        self.calls = []
        self._pending = []

    # --- 公式 API -------------------------------------------------------
    def JVInit(self, sid):
        self.calls.append(("JVInit", sid))
        return self.init_result

    def JVOpen(
        self,
        data_spec,
        fromtime,
        option,
        read_count,
        download_count,
        last_file_timestamp,
    ):
        self.calls.append(("JVOpen", data_spec, fromtime, option))
        if self.open_result is not None:
            self._pending = []
            return self.open_result
        self._pending = list(self.records)
        return (0, len(self.records), 0, "20260820120000")

    def JVRead(self, buff, size, filename):
        if self._pending:
            payload = self._pending.pop(0)
            return (len(payload), payload, len(payload), "RACE.jvd")
        return (0, "", 0, "")

    def JVClose(self):
        self.calls.append(("JVClose",))
        return 0

    # --- 参照用 ---------------------------------------------------------
    def names(self):
        return [call[0] for call in self.calls]

    def count(self, name):
        return self.names().count(name)

    def opens(self):
        return [call[1:] for call in self.calls if call[0] == "JVOpen"]


def _record(index):
    # to_date フィルタを通す実在日付を持たせる（日付なしレコードは常に通るため、
    # フィルタ経路そのものを素通りさせない）。
    return {"Year": "2026", "MonthDay": "0820", "headRecordSpec": "RA", "seq": index}


def _wrapper(com):
    """COM だけを差し替えた本物の ``JVLinkWrapper``（``__init__`` は通さない）。"""
    wrapper = JVLinkWrapper.__new__(JVLinkWrapper)
    wrapper.sid = "TEST"
    wrapper._jvlink = com
    wrapper._is_open = False
    wrapper._needs_close = False
    wrapper._com_initialized = False
    wrapper._initialized = False
    return wrapper


def _historical_fetcher(com):
    """その wrapper を掴んだ fetcher を組む。"""
    wrapper = _wrapper(com)

    counter = {"n": 0}

    def _parse(raw):
        counter["n"] += 1
        return _record(counter["n"])

    factory = MagicMock()
    factory.parse.side_effect = _parse

    with (
        patch("src.jvlink.bridge.find_bridge_executable", return_value=None),
        patch("src.fetcher.base.JVLinkWrapper", return_value=wrapper),
        patch("src.fetcher.base.ParserFactory", return_value=factory),
    ):
        return HistoricalFetcher(sid="TEST", show_progress=False)


def test_three_fetches_in_one_process_share_a_single_jvinit():
    com = RecordingJVLinkCom()
    fetcher = _historical_fetcher(com)

    for _ in range(3):
        assert len(list(fetcher.fetch("RACE", "20260820", "20260820", option=1))) == 1

    assert com.count("JVInit") == 1
    assert com.count("JVOpen") == 3
    assert com.count("JVClose") == 3
    # JVInit は最初の 1 回だけで、以降は JVOpen/JVClose の対が並ぶ。
    assert com.names() == [
        "JVInit",
        "JVOpen",
        "JVClose",
        "JVOpen",
        "JVClose",
        "JVOpen",
        "JVClose",
    ]


def test_jvclose_still_pairs_with_every_jvopen_that_reports_no_data():
    com = RecordingJVLinkCom(open_result=(-1, 0, 0, ""))
    fetcher = _historical_fetcher(com)

    for _ in range(3):
        assert list(fetcher.fetch("RACE", "20260820", "20260820", option=1)) == []

    assert com.count("JVInit") == 1
    assert com.count("JVOpen") == 3
    assert com.count("JVClose") == 3


def test_a_failing_jvinit_never_reaches_jvopen():
    # -101 は JVInit の sid 書式エラー（公式コード表）。
    com = RecordingJVLinkCom(init_result=-101)

    with pytest.raises(JVLinkError):
        _historical_fetcher(com)

    assert com.names() == ["JVInit"]
    assert com.count("JVOpen") == 0


def test_fetch_does_not_reissue_jvinit_after_a_stream_error():
    com = RecordingJVLinkCom(open_result=(-203, 0, 0, ""))
    fetcher = _historical_fetcher(com)

    with pytest.raises(FetcherError):
        list(fetcher.fetch("RACE", "20260820", "20260820", option=1))

    assert com.count("JVInit") == 1


def test_single_dataspec_daily_diff_keeps_its_option1_jvopen_contract():
    """単一 dataspec の option=1 は JVOpen 1 回。fromtime は master の形のまま。

    RACE は範囲形式を使う dataspec なので、要求は暦年で刻まれた
    ``{from}000000-{to}235959`` として届く（#246）。この hoist は JVOpen へ
    渡す引数を動かさない。
    """
    com = RecordingJVLinkCom(records=("RA-1", "RA-2"))
    fetcher = _historical_fetcher(com)

    records = list(fetcher.fetch("RACE", "20260820", "20260821", option=1))

    assert len(records) == 2
    assert com.opens() == [("RACE", "20260820000000-20260821235959", 1)]
    assert com.count("JVClose") == 1
    assert fetcher.get_statistics()["records_parsed"] == 2


def test_repeated_daily_diff_fetches_send_one_jvopen_per_request():
    """日次差分を回し続けても、セッションは 1 本で JVOpen だけが増える。"""
    com = RecordingJVLinkCom()
    fetcher = _historical_fetcher(com)

    list(fetcher.fetch("RACE", "20260820", "20260820", option=1))
    list(fetcher.fetch("RACE", "20260821", "20260821", option=1))

    assert com.count("JVInit") == 1
    assert com.opens() == [
        ("RACE", "20260820000000-20260820235959", 1),
        ("RACE", "20260821000000-20260821235959", 1),
    ]


def test_wrapper_jv_init_reuses_the_established_session():
    com = RecordingJVLinkCom()
    wrapper = _wrapper(com)

    assert wrapper.jv_init() == 0
    assert wrapper.jv_init() == 0
    assert wrapper.jv_init() == 0

    assert com.count("JVInit") == 1


def test_wrapper_jv_init_recreates_com_after_cleanup_released_it():
    """A cleaned-up wrapper must establish a new, explicit JV-Link session."""

    first_com = RecordingJVLinkCom()
    second_com = RecordingJVLinkCom()
    wrapper = _wrapper(first_com)
    wrapper.cleanup()

    assert wrapper._jvlink is None

    def recreate_com():
        wrapper._jvlink = second_com
        wrapper._initialized = False

    wrapper.reinitialize_com = MagicMock(side_effect=recreate_com)

    assert wrapper.jv_init() == 0

    wrapper.reinitialize_com.assert_called_once_with()
    assert first_com.count("JVInit") == 0
    assert second_com.count("JVInit") == 1


def _bridge(*, init_code=0):
    """``__init__`` を通さない bridge。プロセスは生きている扱いで組む。"""
    bridge = JVLinkBridge.__new__(JVLinkBridge)
    bridge.sid = "TEST"
    bridge._is_open = False
    bridge._needs_close = False
    bridge._initialized = False
    bridge._download_count = None
    bridge._process = MagicMock()
    bridge._process.poll.return_value = None
    bridge._start_process = MagicMock()
    bridge._send_command = MagicMock(
        return_value={"status": "ok", "code": init_code}
    )
    return bridge


def _bridge_commands(bridge):
    return [call.args[0]["cmd"] for call in bridge._send_command.call_args_list]


def test_bridge_jv_init_is_issued_once_per_bridge_process():
    bridge = _bridge()

    assert bridge.jv_init() == 0
    assert bridge.jv_init() == 0

    assert _bridge_commands(bridge) == ["init"]


def test_bridge_jvinit_failure_never_reaches_jvopen():
    bridge = _bridge(init_code=-101)

    with pytest.raises(JVLinkBridgeError):
        bridge.jv_init()

    assert _bridge_commands(bridge) == ["init"]


def test_bridge_reopens_its_session_when_the_process_died_mid_run():
    """タイムアウトで bridge が落ちても、次の JVOpen がセッションを張り直す。

    hoist 前は fetch ごとの JVInit がプロセスを起こし直していた。JVOpen 側に
    復旧点を残さないと、一度落ちたプロセスで残りの取得が全滅する。
    """
    bridge = _bridge()
    assert bridge.jv_init() == 0

    commands = []

    def _send(cmd, timeout=None):
        # 本物の _send_command と同じ生存判定。落ちたプロセスでは送れない。
        if bridge._process.poll() is not None:
            raise JVLinkBridgeError("Bridge process is not running")
        commands.append(cmd["cmd"])
        if cmd["cmd"] == "init":
            return {"status": "ok", "code": 0}
        return {
            "status": "ok",
            "code": 0,
            "readcount": 3,
            "downloadcount": 0,
            "lastfiletimestamp": "20260820120000",
        }

    def _restart():
        bridge._process.poll.return_value = None

    bridge._send_command = _send
    bridge._start_process = _restart

    # レスポンスタイムアウト相当: _abort_process がプロセスを落とした状態
    bridge._process.poll.return_value = 1

    assert bridge.jv_open("RACE", "20260820000000", 1)[0] == 0

    assert commands == ["init", "open"]
