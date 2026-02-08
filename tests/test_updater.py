"""Tests for the auto-update and version checking utilities."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVersionComparison:
    """Test version comparison logic."""

    def test_newer_version(self):
        from src.utils.updater import _version_newer

        assert _version_newer("2.3.0", "2.2.0") is True
        assert _version_newer("v2.3.0", "v2.2.0") is True
        assert _version_newer("v3.0.0", "2.2.0") is True

    def test_same_version(self):
        from src.utils.updater import _version_newer

        assert _version_newer("2.2.0", "2.2.0") is False
        assert _version_newer("v2.2.0", "v2.2.0") is False

    def test_older_version(self):
        from src.utils.updater import _version_newer

        assert _version_newer("2.1.0", "2.2.0") is False
        assert _version_newer("1.0.0", "2.2.0") is False

    def test_v_prefix_mixed(self):
        from src.utils.updater import _version_newer

        assert _version_newer("v2.3.0", "2.2.0") is True
        assert _version_newer("2.3.0", "v2.2.0") is True

    def test_patch_version(self):
        from src.utils.updater import _version_newer

        assert _version_newer("2.2.1", "2.2.0") is True
        assert _version_newer("2.2.0", "2.2.1") is False


class TestGetCurrentVersion:
    """Test getting current version."""

    @patch("subprocess.run")
    def test_from_git_tag(self, mock_run):
        from src.utils.updater import get_current_version

        mock_run.return_value = MagicMock(returncode=0, stdout="v2.2.0\n")
        version = get_current_version()
        assert version == "v2.2.0"

    @patch("subprocess.run")
    def test_fallback_to_pyproject(self, mock_run):
        from src.utils.updater import get_current_version

        mock_run.return_value = MagicMock(returncode=1, stdout="")
        version = get_current_version()
        # Should fall back to pyproject.toml
        assert version != "unknown"


class TestShouldCheckUpdates:
    """Test update check interval logic."""

    def test_no_file_should_check(self, tmp_path):
        from src.utils.updater import should_check_updates

        with patch("src.utils.updater.UPDATE_CHECK_FILE", tmp_path / "nonexistent.json"):
            assert should_check_updates() is True

    def test_recent_check_should_skip(self, tmp_path):
        from src.utils.updater import should_check_updates

        check_file = tmp_path / "check.json"
        check_file.write_text(json.dumps({"last_check": time.time()}))

        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            assert should_check_updates(interval_hours=24) is False

    def test_old_check_should_check(self, tmp_path):
        from src.utils.updater import should_check_updates

        check_file = tmp_path / "check.json"
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        check_file.write_text(json.dumps({"last_check": old_time}))

        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            assert should_check_updates(interval_hours=24) is True


class TestCheckForUpdates:
    """Test GitHub API update checking."""

    @patch("urllib.request.urlopen")
    def test_update_available(self, mock_urlopen):
        from src.utils.updater import check_for_updates

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "tag_name": "v99.0.0",
            "html_url": "https://github.com/miyamamoto/jrvltsql/releases/v99.0.0",
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = check_for_updates()
        assert result is not None
        assert result["update_available"] is True
        assert result["latest_version"] == "v99.0.0"

    @patch("urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        from src.utils.updater import check_for_updates

        mock_urlopen.side_effect = Exception("Network error")
        result = check_for_updates()
        assert result is None


class TestPerformUpdate:
    """Test update execution."""

    @patch("subprocess.run")
    def test_successful_update(self, mock_run):
        from src.utils.updater import perform_update

        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")
        result = perform_update(verbose=False)
        assert result is True
        assert mock_run.call_count == 2  # git pull + pip install

    @patch("subprocess.run")
    def test_git_pull_failure(self, mock_run):
        from src.utils.updater import perform_update

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = perform_update(verbose=False)
        assert result is False


class TestAutoUpdateNotice:
    """Test auto-update check notice."""

    @patch("src.utils.updater.should_check_updates", return_value=False)
    def test_skip_if_recent(self, mock_should):
        from src.utils.updater import auto_update_check_notice

        result = auto_update_check_notice()
        assert result is None

    @patch("src.utils.updater.save_update_check_time")
    @patch("src.utils.updater.check_for_updates")
    @patch("src.utils.updater.should_check_updates", return_value=True)
    def test_returns_notice_when_update_available(self, mock_should, mock_check, mock_save):
        from src.utils.updater import auto_update_check_notice

        mock_check.return_value = {
            "update_available": True,
            "current_version": "2.2.0",
            "latest_version": "v3.0.0",
        }

        result = auto_update_check_notice()
        assert result is not None
        assert "3.0.0" in result
        assert "jltsql update" in result
