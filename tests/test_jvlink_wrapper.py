"""Unit tests for JV-Link wrapper."""

import pytest
from unittest.mock import MagicMock, Mock, patch

from src.jvlink.constants import (
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

        wrapper = JVLinkWrapper(service_key="TEST_KEY")

        assert wrapper.service_key == "TEST_KEY"
        assert wrapper._jvlink == mock_com
        assert not wrapper.is_open()
        mock_dispatch.assert_called_once_with("JVDTLab.JVLink")

    @patch("win32com.client.Dispatch")
    def test_init_failure(self, mock_dispatch):
        """Test initialization failure."""
        mock_dispatch.side_effect = Exception("COM object creation failed")

        with pytest.raises(JVLinkError) as exc_info:
            JVLinkWrapper(service_key="TEST_KEY")

        assert "Failed to create JV-Link COM object" in str(exc_info.value)

    @patch("win32com.client.Dispatch")
    def test_jv_init_success(self, mock_dispatch):
        """Test JVInit success."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        result = wrapper.jv_init()

        assert result == JV_RT_SUCCESS
        mock_com.JVInit.assert_called_once_with("TEST_KEY")

    @patch("win32com.client.Dispatch")
    def test_jv_init_failure(self, mock_dispatch):
        """Test JVInit failure."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_ERROR
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_init()

        assert exc_info.value.error_code == JV_RT_ERROR

    @patch("win32com.client.Dispatch")
    def test_jv_open_success(self, mock_dispatch):
        """Test JVOpen success."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = 1000  # 1000 records to read
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        result, count = wrapper.jv_open("RACE", "20240101", "20241231")

        assert result == JV_RT_SUCCESS
        assert count == 1000
        assert wrapper.is_open()
        mock_com.JVOpen.assert_called_once_with("RACE", "20240101", "20241231", 0)

    @patch("win32com.client.Dispatch")
    def test_jv_open_with_option(self, mock_dispatch):
        """Test JVOpen with option parameter."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = 500
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        result, count = wrapper.jv_open("DIFF", "20240101", "20241231", option=1)

        assert result == JV_RT_SUCCESS
        assert count == 500
        mock_com.JVOpen.assert_called_once_with("DIFF", "20240101", "20241231", 1)

    @patch("win32com.client.Dispatch")
    def test_jv_open_failure(self, mock_dispatch):
        """Test JVOpen failure."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = JV_RT_ERROR
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_open("RACE", "20240101", "20241231")

        assert exc_info.value.error_code == JV_RT_ERROR

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_success(self, mock_dispatch):
        """Test JVRTOpen success."""
        mock_com = MagicMock()
        mock_com.JVRTOpen.return_value = 10
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        result, count = wrapper.jv_rt_open("0B12")

        assert result == JV_RT_SUCCESS
        assert count == 10
        assert wrapper.is_open()
        mock_com.JVRTOpen.assert_called_once_with("0B12", "")

    @patch("win32com.client.Dispatch")
    def test_jv_rt_open_failure(self, mock_dispatch):
        """Test JVRTOpen failure."""
        mock_com = MagicMock()
        mock_com.JVRTOpen.return_value = JV_RT_ERROR
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_rt_open("0B12")

        assert exc_info.value.error_code == JV_RT_ERROR

    @patch("win32com.client.Dispatch")
    def test_jv_read_success(self, mock_dispatch):
        """Test JVRead success."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = 1
        mock_com.JVRead.return_value = JV_READ_SUCCESS
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        wrapper.jv_open("RACE", "20240101", "20241231")

        # Mock pythoncom module inside the jv_read method
        with patch("builtins.__import__", side_effect=self._mock_import_pythoncom):
            ret_code, buff, filename = wrapper.jv_read()

        assert ret_code == JV_READ_SUCCESS
        assert buff == b"RA1202406010603081"
        assert filename == "test.jvd"

    def _mock_import_pythoncom(self, name, *args, **kwargs):
        """Mock import for pythoncom."""
        if name == "pythoncom":
            mock_pythoncom = MagicMock()
            # Mock buffer
            test_data = b"RA1202406010603081" + b"\x00" * 100
            mock_data_buffer = bytearray(test_data)
            mock_filename_buffer = bytearray(b"test.jvd" + b"\x00" * 200)
            mock_pythoncom.AllocateBuffer.side_effect = [mock_data_buffer, mock_filename_buffer]
            return mock_pythoncom
        # For other imports, use real import
        return __import__(name, *args, **kwargs)

    @patch("win32com.client.Dispatch")
    def test_jv_read_no_more_data(self, mock_dispatch):
        """Test JVRead when no more data."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = 1
        mock_com.JVRead.return_value = JV_READ_NO_MORE_DATA
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        wrapper.jv_open("RACE", "20240101", "20241231")

        # Mock pythoncom module
        with patch("builtins.__import__") as mock_import:
            def import_side_effect(name, *args, **kwargs):
                if name == "pythoncom":
                    return MagicMock()
                return __import__(name, *args, **kwargs)
            mock_import.side_effect = import_side_effect

            ret_code, buff, filename = wrapper.jv_read()

        assert ret_code == JV_READ_NO_MORE_DATA
        assert buff is None
        assert filename is None

    @patch("win32com.client.Dispatch")
    def test_jv_read_without_open(self, mock_dispatch):
        """Test JVRead without opening stream."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")

        with pytest.raises(JVLinkError) as exc_info:
            wrapper.jv_read()

        assert "stream not open" in str(exc_info.value).lower()

    @patch("win32com.client.Dispatch")
    def test_jv_close(self, mock_dispatch):
        """Test JVClose."""
        mock_com = MagicMock()
        mock_com.JVOpen.return_value = 1
        mock_com.JVClose.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        wrapper.jv_open("RACE", "20240101", "20241231")

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

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        status = wrapper.jv_status()

        assert status == 0
        mock_com.JVStatus.assert_called_once()

    @patch("win32com.client.Dispatch")
    def test_context_manager(self, mock_dispatch):
        """Test context manager protocol."""
        mock_com = MagicMock()
        mock_com.JVInit.return_value = JV_RT_SUCCESS
        mock_com.JVOpen.return_value = 1
        mock_com.JVClose.return_value = JV_RT_SUCCESS
        mock_dispatch.return_value = mock_com

        with JVLinkWrapper(service_key="TEST_KEY") as wrapper:
            wrapper.jv_open("RACE", "20240101", "20241231")
            assert wrapper.is_open()

        mock_com.JVInit.assert_called_once()
        mock_com.JVClose.assert_called_once()

    @patch("win32com.client.Dispatch")
    def test_repr(self, mock_dispatch):
        """Test string representation."""
        mock_com = MagicMock()
        mock_dispatch.return_value = mock_com

        wrapper = JVLinkWrapper(service_key="TEST_KEY")
        repr_str = repr(wrapper)

        assert "JVLinkWrapper" in repr_str
        assert "closed" in repr_str


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
