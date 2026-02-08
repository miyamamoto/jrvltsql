"""Tests for installer/updater utilities (src/utils/updater.py).

Covers version comparison, path resolution, update check timing,
and update flow with mocked subprocess/network calls.
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.utils.updater import (
    _version_newer,
    should_check_updates,
    save_update_check_time,
    get_current_version,
    _find_pip,
    perform_update,
    check_for_updates,
    auto_update_check_notice,
    UPDATE_CHECK_FILE,
    PROJECT_ROOT,
)


class TestVersionNewer:
    """Comprehensive tests for _version_newer comparison."""

    def test_newer_major(self):
        assert _version_newer("3.0.0", "2.0.0") is True

    def test_newer_minor(self):
        assert _version_newer("2.3.0", "2.2.0") is True

    def test_newer_patch(self):
        assert _version_newer("2.2.1", "2.2.0") is True

    def test_same_version(self):
        assert _version_newer("2.2.0", "2.2.0") is False

    def test_older_version(self):
        assert _version_newer("2.1.0", "2.2.0") is False

    def test_v_prefix_latest(self):
        assert _version_newer("v2.3.0", "2.2.0") is True

    def test_v_prefix_current(self):
        assert _version_newer("2.3.0", "v2.2.0") is True

    def test_v_prefix_both(self):
        assert _version_newer("v2.3.0", "v2.2.0") is True

    def test_v_prefix_same(self):
        assert _version_newer("v2.2.0", "v2.2.0") is False

    def test_two_part_version(self):
        assert _version_newer("2.3", "2.2") is True

    def test_single_part_version(self):
        assert _version_newer("3", "2") is True

    def test_non_numeric_part_treated_as_zero(self):
        # "beta" → 0, so "2.0.beta" → [2, 0, 0]
        assert _version_newer("2.0.1", "2.0.beta") is True


class TestShouldCheckUpdates:
    """Tests for update check timing logic."""

    def test_no_file_should_check(self, tmp_path):
        with patch("src.utils.updater.UPDATE_CHECK_FILE", tmp_path / "nonexistent.json"):
            assert should_check_updates() is True

    def test_recent_check_should_skip(self, tmp_path):
        check_file = tmp_path / "check.json"
        check_file.write_text(json.dumps({"last_check": time.time()}))
        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            assert should_check_updates(interval_hours=24) is False

    def test_old_check_should_check(self, tmp_path):
        check_file = tmp_path / "check.json"
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        check_file.write_text(json.dumps({"last_check": old_time}))
        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            assert should_check_updates(interval_hours=24) is True

    def test_corrupt_file_should_check(self, tmp_path):
        check_file = tmp_path / "check.json"
        check_file.write_text("not json")
        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            assert should_check_updates() is True


class TestSaveUpdateCheckTime:
    """Tests for save_update_check_time."""

    def test_creates_file(self, tmp_path):
        check_file = tmp_path / "data" / "check.json"
        with patch("src.utils.updater.UPDATE_CHECK_FILE", check_file):
            save_update_check_time()
            assert check_file.exists()
            data = json.loads(check_file.read_text())
            assert "last_check" in data
            assert "checked_at" in data


class TestGetCurrentVersion:
    """Tests for get_current_version."""

    @patch("subprocess.run")
    def test_from_git_tag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="v2.5.0\n")
        version = get_current_version()
        assert version == "v2.5.0"

    @patch("subprocess.run")
    def test_fallback_to_pyproject(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        pyproject = PROJECT_ROOT / "pyproject.toml"
        # Only test fallback if pyproject exists
        if pyproject.exists():
            version = get_current_version()
            assert version != "unknown"


class TestFindPip:
    """Tests for _find_pip path resolution."""

    def test_returns_path_string(self):
        result = _find_pip()
        assert isinstance(result, str)
        assert "pip" in result

    def test_pip_next_to_python(self):
        """pip should be in same directory as sys.executable."""
        import sys
        result = _find_pip()
        expected_dir = str(Path(sys.executable).parent)
        assert result.startswith(expected_dir)


class TestPerformUpdate:
    """Tests for perform_update."""

    @patch("subprocess.run")
    def test_successful_update(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n")
        result = perform_update(verbose=False)
        assert result is True
        assert mock_run.call_count == 2  # git pull + pip install

    @patch("subprocess.run")
    def test_git_pull_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="merge conflict")
        result = perform_update(verbose=False)
        assert result is False

    @patch("subprocess.run")
    def test_pip_install_failure(self, mock_run):
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "git" in cmd:
                return MagicMock(returncode=0, stdout="Updated\n")
            else:
                return MagicMock(returncode=1, stderr="install error")
        mock_run.side_effect = side_effect
        result = perform_update(verbose=False)
        assert result is False

    @patch("subprocess.run", side_effect=Exception("no git"))
    def test_exception_returns_false(self, mock_run):
        result = perform_update(verbose=False)
        assert result is False


class TestCheckForUpdates:
    """Tests for check_for_updates with mocked network."""

    @patch("urllib.request.urlopen")
    @patch("src.utils.updater.get_current_version", return_value="v2.0.0")
    def test_update_available(self, mock_ver, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "tag_name": "v2.1.0",
            "html_url": "https://github.com/test/releases/v2.1.0",
        }).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        result = check_for_updates()
        assert result is not None
        assert result["update_available"] is True
        assert result["latest_version"] == "v2.1.0"

    @patch("urllib.request.urlopen", side_effect=Exception("network error"))
    @patch("src.utils.updater.get_current_version", return_value="v2.0.0")
    def test_network_error_returns_none(self, mock_ver, mock_urlopen):
        result = check_for_updates()
        assert result is None


class TestAutoUpdateCheckNotice:
    """Tests for auto_update_check_notice."""

    @patch("src.utils.updater.should_check_updates", return_value=False)
    def test_skip_if_recent(self, mock_should):
        result = auto_update_check_notice()
        assert result is None

    @patch("src.utils.updater.save_update_check_time")
    @patch("src.utils.updater.check_for_updates", return_value={
        "update_available": True,
        "latest_version": "v3.0.0",
        "current_version": "v2.0.0",
    })
    @patch("src.utils.updater.should_check_updates", return_value=True)
    def test_returns_notice(self, mock_should, mock_check, mock_save):
        result = auto_update_check_notice()
        assert result is not None
        assert "v3.0.0" in result
        assert "v2.0.0" in result
