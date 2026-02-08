"""Unit tests for JV-Link wrapper."""

import sys
import pytest
from unittest.mock import MagicMock, Mock, patch

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason="Requires Windows COM")

from src.jvlink.constants import (
    DATA_SPEC_DIFN,
    DATA_SPEC_BLDN,
    DATA_SPEC_HOSN,
    DATA_SPEC_MING,
    DATA_SPEC_WOOD,
    DATA_SPEC_COMM,
    DATA_SPEC_TCVN,
    DATA_SPEC_RCVN,
    JV_READ_NO_MORE_DATA,
    JV_READ_SUCCESS,
    JV_RT_ERROR,
    JV_RT_SUCCESS,
)
from src.jvlink.wrapper import JVLinkError, JVLinkWrapper


class TestJVLinkWrapper:
    """Test cases for JVLinkWrapper class."""

    @patch("win32com.client.Dispatch")
    def test_init_success(self, mock_dispatch):
        """Test successful initialization."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        assert wrapper.sid == "TEST"
        assert wrapper._jvlink == mock_com
        assert not wrapper.is_open()
        mock_dispatch.assert_called_once_with("JVDTLab.JVLink")

    @patch("win32com.client.Dispatch")
    def test_init_failure(self, mock_dispatch):
        """Test initialization failure."""
        mock_dispatch.side_effect = Exception("COM object creation failed")

        with pytest.raises(JVLinkError) as exc_info:
            JVLinkWrapper(sid="TEST")

        assert "Failed to create JV-Link COM object" in str(exc_info.value)

    @patch("win32com.client.Dispatch")
    def test_jv_init_success(self, mock_dispatch):
        """Test JVInit success."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        result = wrapper.jv_init()

        assert result == JV_RT_SUCCESS
        mock_com.JVInit.assert_called_once_with("TEST")

    @patch("win32com.client.Dispatch")
    def test_jv_init_failure(self, mock_dispatch):
        """Test JVInit failure."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_ERROR
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_init()

        assert exc_info.value.error_code == JV_RT_ERROR

    @patch("win32com.client.Dispatch")
    def test_jv_open_success(self, mock_dispatch):
        """Test JVOpen success."""
        mock_com = MagicMock()
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 1000, 0, "20241231235959")
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        result, read_count, download_count, last_file_timestamp = wrapper.jv_open(
            "RACE", "20240101000000", option=1
        )

        assert result == JV_RT_SUCCESS
        assert read_count == 1000
        assert download_count == 0
        assert last_file_timestamp == "20241231235959"
        assert wrapper.is_open()
        mock_com.JVOpen.assert_called_once_with("RACE", "20240101000000", 1)

    @patch("win32com.client.Dispatch")
    def test_jv_open_with_option(self, mock_dispatch):
        """Test JVOpen with option parameter."""
        mock_com = MagicMock()
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 500, 100, "20241231235959")
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        result, read_count, download_count, last_file_timestamp = wrapper.jv_open(
            "DIFF", "20240101000000", option=2
        )

        assert result == JV_RT_SUCCESS
        assert read_count == 500
        assert download_count == 100
        assert last_file_timestamp == "20241231235959"
        mock_com.JVOpen.assert_called_once_with("DIFF", "20240101000000", 2)

    @patch("win32com.client.Dispatch")
    def test_jv_open_failure(self, mock_dispatch):
        """Test JVOpen failure with actual error code (<-2)."""
        mock_com = MagicMock()
        # JVOpen: -1/-2 are "no data" (not errors), -100 is setup required (real error)
        mock_com.JVOpen.return_value = (-100, 0, 0, "")
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_open("RACE", "20240101000000")

        assert exc_info.value.error_code == -100

    @patch("win32com.client.Dispatch")
    def test_jv_open_no_data(self, mock_dispatch):
        """Test JVOpen with no data available (-1) does NOT raise."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = (JV_RT_ERROR, 0, 0, "")  # -1 = no data
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        # Should NOT raise - -1 means no data, not an error
        wrapper.jv_open("RACE", "20240101000000")

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_success(self, mock_dispatch):
        """Test JVRTOpen success."""
        mock_com = MagicMock()
        # JVRTOpen can return either (result, read_count) or single value
        mock_com.JVRTOpen.return_value = (0, 10)
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        result, count = wrapper.jv_rt_open("0B12")

        assert result == JV_RT_SUCCESS
        assert count == 10
        assert wrapper.is_open()
        mock_com.JVRTOpen.assert_called_once_with("0B12", "")

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_failure(self, mock_dispatch):
        """Test JVRTOpen failure with actual error code."""
        mock_com = MagicMock()
        # -114 = data spec not subscribed (real error that raises)
        mock_com.JVRTOpen.return_value = (-114, 0)
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_rt_open("0B12")

        assert exc_info.value.error_code == -114

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_no_data(self, mock_dispatch):
        """Test JVRTOpen with no data (-1) does NOT raise."""
        mock_com = MagicMock()
        mock_com.JVRTOpen.return_value = (JV_RT_ERROR, 0)  # -1 = no data
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        result, count = wrapper.jv_rt_open("0B12")
        assert result == -1
        assert count == 0

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_with_new_specs(self, mock_dispatch):
        """Test JVRTOpen with newly added spec codes (0B41, 0B42)."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        # Test 0B41 (騎手変更情報)
        mock_com.JVRTOpen.return_value = (0, 5)
        result, count = wrapper.jv_rt_open("0B41")
        assert result == JV_RT_SUCCESS
        assert count == 5

        # Test 0B42 (調教師変更情報)
        mock_com.JVRTOpen.return_value = (0, 3)
        result, count = wrapper.jv_rt_open("0B42")
        assert result == JV_RT_SUCCESS
        assert count == 3

    @patch("win32com.client.Dispatch")
    def test_jv_read_success(self, mock_dispatch):
        """Test JVRead success."""
        mock_com = MagicMock()
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 1, 0, "20241231235959")
        # JVRead returns (return_code, buff_str, size, filename_str)
        test_data = "RA1202406010603081"
        mock_com.JVRead.return_value = (len(test_data), test_data, len(test_data), "test.jvd")
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        wrapper.jv_open("RACE", "20240101000000")

        ret_code, buff, filename = wrapper.jv_read()

        assert ret_code == len(test_data)
        assert buff == test_data.encode("cp932")
        assert filename == "test.jvd"

    @patch("win32com.client.Dispatch")
    def test_jv_read_no_more_data(self, mock_dispatch):
        """Test JVRead when no more data."""
        mock_com = MagicMock()
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 1, 0, "20241231235959")
        # JVRead returns (return_code, buff_str, size, filename_str)
        mock_com.JVRead.return_value = (JV_READ_NO_MORE_DATA, "", 0, "")
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        wrapper.jv_open("RACE", "20240101000000")

        ret_code, buff, filename = wrapper.jv_read()

        assert ret_code == JV_READ_NO_MORE_DATA
        assert buff is None
        assert filename is None

    @patch("win32com.client.Dispatch")
    def test_jv_read_without_open(self, mock_dispatch):
        """Test JVRead without opening stream."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_read()

        assert "stream not open" in str(exc_info.value).lower()

    @patch("win32com.client.Dispatch")
    def test_jv_close(self, mock_dispatch):
        """Test JVClose."""
        mock_com = MagicMock()
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 1, 0, "20241231235959")
        mock_com.JVClose.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        wrapper.jv_open("RACE", "20240101000000")

        assert wrapper.is_open()

        result = wrapper.jv_close()

        assert result == JV_RT_SUCCESS
        assert not wrapper.is_open()
        mock_com.JVClose.assert_called_once()

    @patch("win32com.client.Dispatch")
    def test_jv_status(self, mock_dispatch):
        """Test JVStatus."""
        mock_com = MagicMock()
        mock_com.JVStatus.return_value = 0
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        status = wrapper.jv_status()

        assert status == 0
        mock_com.JVStatus.assert_called_once()

    @patch("win32com.client.Dispatch")
    def test_context_manager(self, mock_dispatch):
        """Test context manager protocol."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_SUCCESS
        # JVOpen returns (result, read_count, download_count, last_file_timestamp)
        mock_com.JVOpen.return_value = (0, 1, 0, "20241231235959")
        mock_com.JVClose.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        with JVLinkWrapper(sid="TEST") as wrapper:
            wrapper.jv_open("RACE", "20240101000000")
            assert wrapper.is_open()

        mock_com.JVInit.assert_called_once()
        mock_com.JVClose.assert_called_once()

    @patch("win32com.client.Dispatch")
    def test_repr(self, mock_dispatch):
        """Test string representation."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")
        repr_str = repr(wrapper)

        assert "JVLinkWrapper" in repr_str
        assert "closed" in repr_str


    @patch("win32com.client.Dispatch")
    def test_jv_open_with_new_data_specs(self, mock_dispatch):
        """Test JVOpen with newly added data specification codes."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(sid="TEST")

        # Test DIFN (マスタデータ - DIFF の別名)
        mock_com.JVOpen.return_value = (0, 100, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_DIFN, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 100

        # Test BLDN (血統情報 - BLOD の別名)
        mock_com.JVOpen.return_value = (0, 50, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_BLDN, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 50

        # Test HOSN (競走馬市場取引価格 - HOSE の別名)
        mock_com.JVOpen.return_value = (0, 30, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_HOSN, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 30

        # Test MING (データマイニング予想)
        mock_com.JVOpen.return_value = (0, 200, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_MING, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 200

        # Test WOOD (ウッドチップ調教)
        mock_com.JVOpen.return_value = (0, 80, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_WOOD, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 80

        # Test COMM (コメント情報)
        mock_com.JVOpen.return_value = (0, 120, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_COMM, "20240101000000", option=1)
        assert result == JV_RT_SUCCESS
        assert read_count == 120

        # Test TCVN (調教師変更情報) - option 2 only
        mock_com.JVOpen.return_value = (0, 10, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_TCVN, "20240101000000", option=2)
        assert result == JV_RT_SUCCESS
        assert read_count == 10

        # Test RCVN (騎手変更情報) - option 2 only
        mock_com.JVOpen.return_value = (0, 15, 0, "20241231235959")
        result, read_count, _, _ = wrapper.jv_open(DATA_SPEC_RCVN, "20240101000000", option=2)
        assert result == JV_RT_SUCCESS
        assert read_count == 15


class TestJVLinkError:
    """Test cases for JVLinkError class."""

    def test_error_without_code(self):
        """Test error without error code."""
        error = JVLinkError("Test error")
        assert str(error) == "Test error"
        assert error.error_code is None

    def test_error_with_code(self):
        """Test error with error code."""
        error = JVLinkError("Test error", error_code=JV_RT_ERROR)
        assert "Test error" in str(error)
        assert str(JV_RT_ERROR) in str(error)
        assert error.error_code == JV_RT_ERROR
