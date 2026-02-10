"""Tests for NVOpen -202 (AlreadyOpen) recovery.

NVOpen returns -202 when a previous stream was not properly closed.
The wrapper should auto-close and retry.
"""

import pytest
from unittest.mock import MagicMock, patch, call


class TestNVOpen202Recovery:
    """Test -202 AlreadyOpen auto-recovery in wrapper.py."""

    @pytest.fixture
    def mock_nvlink_com(self):
        """Create a mock NV-Link COM object."""
        mock = MagicMock()
        mock.NVInit.return_value = 0
        mock.NVClose.return_value = 0
        mock.ParentHWnd = 0
        return mock

    @patch("sys.platform", "win32")
    def test_nv_open_202_retry_succeeds(self, mock_nvlink_com):
        """NVOpen returns -202, then succeeds after NVClose + retry."""
        # First call returns -202, second succeeds
        mock_nvlink_com.NVOpen.side_effect = [
            (-202, 0, 0, ""),  # First: AlreadyOpen
            (0, 10, 0, "20260209"),  # Retry: success
        ]

        with patch("src.nvlink.wrapper.NVLinkWrapper.__init__", return_value=None):
            from src.nvlink.wrapper import NVLinkWrapper
            wrapper = NVLinkWrapper.__new__(NVLinkWrapper)
            wrapper._nvlink = mock_nvlink_com
            wrapper._bridge = None
            wrapper._use_bridge = False
            wrapper._is_open = False
            wrapper._com_initialized = True
            wrapper.sid = "TEST"

            result = wrapper.nv_open("RACE", "20260101000000", option=1)

            # Should have called NVClose between the two NVOpen calls
            assert mock_nvlink_com.NVClose.called
            assert mock_nvlink_com.NVOpen.call_count == 2
            assert wrapper._is_open is True

    @patch("sys.platform", "win32")
    def test_nv_open_202_retry_still_202_raises(self, mock_nvlink_com):
        """NVOpen returns -202 twice → should raise NVLinkError."""
        mock_nvlink_com.NVOpen.side_effect = [
            (-202, 0, 0, ""),
            (-202, 0, 0, ""),
        ]

        with patch("src.nvlink.wrapper.NVLinkWrapper.__init__", return_value=None):
            from src.nvlink.wrapper import NVLinkWrapper, NVLinkError
            wrapper = NVLinkWrapper.__new__(NVLinkWrapper)
            wrapper._nvlink = mock_nvlink_com
            wrapper._bridge = None
            wrapper._use_bridge = False
            wrapper._is_open = False
            wrapper._com_initialized = True
            wrapper.sid = "TEST"

            with pytest.raises(NVLinkError, match="-202"):
                wrapper.nv_open("RACE", "20260101000000", option=1)

    @patch("sys.platform", "win32")
    def test_nv_open_202_nvclose_fails_still_retries(self, mock_nvlink_com):
        """Even if NVClose throws during -202 recovery, retry should still happen."""
        mock_nvlink_com.NVOpen.side_effect = [
            (-202, 0, 0, ""),
            (0, 5, 0, "20260209"),
        ]
        mock_nvlink_com.NVClose.side_effect = Exception("COM error")

        with patch("src.nvlink.wrapper.NVLinkWrapper.__init__", return_value=None):
            from src.nvlink.wrapper import NVLinkWrapper
            wrapper = NVLinkWrapper.__new__(NVLinkWrapper)
            wrapper._nvlink = mock_nvlink_com
            wrapper._bridge = None
            wrapper._use_bridge = False
            wrapper._is_open = False
            wrapper._com_initialized = True
            wrapper.sid = "TEST"

            result = wrapper.nv_open("RACE", "20260101000000", option=1)
            assert wrapper._is_open is True


class TestQuickstartSetupCode202:
    """Test that quickstart inline scripts handle -202."""

    def test_setup_code_has_nvclose_guard(self):
        """Verify quickstart.py setup_code includes NVClose guard."""
        import os
        quickstart_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'scripts', 'quickstart.py'
        )
        with open(quickstart_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # _run_nar_initial_setup's setup_code should have NVClose before NVOpen
        assert "Safety: close any previously open stream" in content
        # _check_nar_initial_setup's check_code should also have NVClose guard
        assert content.count("prevents -202 AlreadyOpen") >= 2

    def test_setup_code_has_202_retry(self):
        """Verify quickstart.py setup_code handles -202 retry."""
        import os
        quickstart_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'scripts', 'quickstart.py'
        )
        with open(quickstart_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Both inline scripts should handle -202
        assert content.count("if rc == -202:") >= 2
