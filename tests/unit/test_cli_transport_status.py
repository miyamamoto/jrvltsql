"""CLI availability reporting must follow the actual JV-Link transport.

`from src.jvlink import JVLinkWrapper` always raised ImportError because the
package never re-exported that name, so `status` / `version` reported JV-Link as
unavailable on every platform, including a Windows host with a working COM
install and a Wine host with a usable bridge executable.
"""

from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli


def _invoke(command: str, available: bool):
    with patch("src.jvlink.is_jvlink_available", return_value=available):
        return CliRunner().invoke(cli, [command])


def _strip_markup(text: str) -> str:
    return " ".join(text.split())


def test_status_reports_available_transport() -> None:
    result = _invoke("status", True)
    assert result.exit_code == 0
    output = _strip_markup(result.output)
    assert "JV-Link transport: 利用可能" in output
    assert "利用不可" not in output
    # A usable transport is not a registration or subscription claim.
    assert "利用登録状態: 未確認" in output


def test_status_reports_missing_transport() -> None:
    result = _invoke("status", False)
    assert result.exit_code == 0
    assert "JV-Link transport: 利用不可" in _strip_markup(result.output)


def test_version_reports_available_transport() -> None:
    result = _invoke("version", True)
    assert result.exit_code == 0
    assert (
        "JRA-VAN DataLab (JV-Link transport): 利用可能"
        in _strip_markup(result.output)
    )


def test_version_reports_missing_transport() -> None:
    result = _invoke("version", False)
    assert result.exit_code == 0
    assert (
        "JRA-VAN DataLab (JV-Link transport): 未インストール"
        in _strip_markup(result.output)
    )


def test_transport_availability_follows_bridge_discovery(monkeypatch) -> None:
    import src.jvlink as jvlink

    monkeypatch.setattr(jvlink.sys, "platform", "linux")
    with patch(
        "src.jvlink.bridge.find_bridge_executable", return_value=None
    ):
        assert jvlink.is_jvlink_available() is False
    with patch(
        "src.jvlink.bridge.find_bridge_executable", return_value="/bin/bridge"
    ):
        assert jvlink.is_jvlink_available() is True
