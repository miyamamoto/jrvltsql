"""Tests for the configurable JVOpen response timeout."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.jvlink.bridge import JVLinkBridge, JVLinkBridgeError


@pytest.fixture
def bridge(tmp_path) -> JVLinkBridge:
    exe = tmp_path / "JVLinkBridge.exe"
    exe.touch()
    return JVLinkBridge(sid="TEST", bridge_path=exe)


def _open(bridge: JVLinkBridge) -> float:
    recorded: dict[str, float | None] = {}

    def fake_send(cmd: dict, timeout: float | None = None) -> dict:
        recorded["timeout"] = timeout
        return {"status": "ok", "code": 0, "readcount": 1, "downloadcount": 0, "lastfiletimestamp": "20260817133705"}

    with patch.object(bridge, "_send_command", side_effect=fake_send):
        bridge.jv_open("RACE", "20260810000000", 1)
    assert recorded["timeout"] is not None
    return recorded["timeout"]


def test_open_timeout_defaults_to_two_minutes(monkeypatch, bridge) -> None:
    monkeypatch.delenv("JVLINK_OPEN_TIMEOUT_SECONDS", raising=False)
    assert _open(bridge) == 120.0


def test_open_timeout_follows_the_environment(monkeypatch, bridge) -> None:
    # A JVOpen that has to answer a JV-Link dialog was measured at 1,008s
    # against a real provider, so a deployment must be able to wait longer
    # than the default.
    monkeypatch.setenv("JVLINK_OPEN_TIMEOUT_SECONDS", "7200")
    assert _open(bridge) == 7200.0


def test_open_timeout_treats_an_unset_compose_variable_as_default(monkeypatch, bridge) -> None:
    # `JVLINK_OPEN_TIMEOUT_SECONDS: ${...:-}` renders as an empty string.
    monkeypatch.setenv("JVLINK_OPEN_TIMEOUT_SECONDS", "")
    assert _open(bridge) == 120.0


@pytest.mark.parametrize("value", ["0", "-1", "7201", "later", "1e400", "nan"])
def test_open_refuses_an_unusable_timeout(monkeypatch, bridge, value: str) -> None:
    monkeypatch.setenv("JVLINK_OPEN_TIMEOUT_SECONDS", value)
    with patch.object(bridge, "_send_command") as send:
        with pytest.raises(JVLinkBridgeError, match="JVLINK_OPEN_TIMEOUT_SECONDS"):
            bridge.jv_open("RACE", "20260810000000", 1)
    send.assert_not_called()
