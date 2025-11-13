"""JV-Link COM API Wrapper.

This module provides a Python wrapper for the JV-Link COM API,
which is used to access JRA-VAN DataLab horse racing data.
"""

from typing import Optional, Tuple

from src.jvlink.constants import (
    BUFFER_SIZE_JVREAD,
    ENCODING_JVDATA,
    JV_READ_ERROR,
    JV_READ_NO_MORE_DATA,
    JV_READ_SUCCESS,
    JV_RT_ERROR,
    JV_RT_SUCCESS,
    get_error_message,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JVLinkError(Exception):
    """JV-Link related error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        """Initialize JVLinkError.

        Args:
            message: Error message
            error_code: JV-Link error code
        """
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code}, {get_error_message(error_code)})"
        super().__init__(message)


class JVLinkWrapper:
    """Wrapper class for JV-Link COM API.

    This class provides a Pythonic interface to the JV-Link COM API,
    handling Windows COM object creation and method calls.

    Examples:
        >>> wrapper = JVLinkWrapper(service_key="YOUR_KEY")
        >>> wrapper.jv_init()
        0
        >>> result, count = wrapper.jv_open("RACE", "20240101", "20241231")
        >>> while True:
        ...     ret_code, buff, filename = wrapper.jv_read()
        ...     if ret_code == JV_READ_NO_MORE_DATA:
        ...         break
        ...     # Process data
        >>> wrapper.jv_close()
    """

    def __init__(self, service_key: str):
        """Initialize JVLinkWrapper.

        Args:
            service_key: JRA-VAN service key

        Raises:
            JVLinkError: If COM object creation fails
        """
        self.service_key = service_key
        self._jvlink = None
        self._is_open = False

        try:
            import win32com.client

            self._jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
            logger.info("JV-Link COM object created")
        except Exception as e:
            raise JVLinkError(f"Failed to create JV-Link COM object: {e}")

    def jv_init(self) -> int:
        """Initialize JV-Link.

        Must be called before any other JV-Link operations.

        Returns:
            Result code (0 = success, -1 = error)

        Raises:
            JVLinkError: If initialization fails

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> result = wrapper.jv_init()
            >>> assert result == 0
        """
        try:
            result = self._jvlink.JVInit(self.service_key)
            if result == JV_RT_SUCCESS:
                logger.info("JV-Link initialized successfully")
            else:
                logger.error("JV-Link initialization failed", error_code=result)
                raise JVLinkError("JV-Link initialization failed", error_code=result)
            return result
        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVInit failed: {e}")

    def jv_open(
        self,
        data_spec: str,
        from_date: str,
        to_date: str,
        option: int = 0,
    ) -> Tuple[int, int]:
        """Open JV-Link data stream for historical data.

        Args:
            data_spec: Data specification code (e.g., "RACE", "DIFF")
            from_date: Start date in YYYYMMDD format
            to_date: End date in YYYYMMDD format
            option: Option flag (0=normal, 1=setup, 2=update)

        Returns:
            Tuple of (result_code, read_count)
            - result_code: 0=success, negative=error
            - read_count: Number of records to read (for setup mode)

        Raises:
            JVLinkError: If open operation fails

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> wrapper.jv_init()
            >>> result, count = wrapper.jv_open("RACE", "20240101", "20241231")
            >>> print(f"Will read {count} records")
        """
        try:
            result = self._jvlink.JVOpen(data_spec, from_date, to_date, option)

            if result < 0:
                logger.error(
                    "JVOpen failed",
                    data_spec=data_spec,
                    from_date=from_date,
                    to_date=to_date,
                    error_code=result,
                )
                raise JVLinkError("JVOpen failed", error_code=result)

            read_count = result
            self._is_open = True

            logger.info(
                "JVOpen successful",
                data_spec=data_spec,
                from_date=from_date,
                to_date=to_date,
                read_count=read_count,
            )

            return JV_RT_SUCCESS, read_count

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVOpen failed: {e}")

    def jv_rt_open(self, data_spec: str, key: str = "") -> Tuple[int, int]:
        """Open JV-Link data stream for real-time data.

        Args:
            data_spec: Real-time data specification (e.g., "0B12", "0B15")
            key: Key parameter (usually empty string)

        Returns:
            Tuple of (result_code, read_count)

        Raises:
            JVLinkError: If open operation fails

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> wrapper.jv_init()
            >>> result, count = wrapper.jv_rt_open("0B12")  # Race results
        """
        try:
            result = self._jvlink.JVRTOpen(data_spec, key)

            if result < 0:
                logger.error("JVRTOpen failed", data_spec=data_spec, error_code=result)
                raise JVLinkError("JVRTOpen failed", error_code=result)

            read_count = result
            self._is_open = True

            logger.info(
                "JVRTOpen successful",
                data_spec=data_spec,
                read_count=read_count,
            )

            return JV_RT_SUCCESS, read_count

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVRTOpen failed: {e}")

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record from JV-Link data stream.

        Must be called after jv_open() or jv_rt_open().

        Returns:
            Tuple of (return_code, buffer, filename)
            - return_code: 0=success, -1=no more data, -2=error
            - buffer: Data buffer (bytes) if success, None otherwise
            - filename: Filename if applicable, None otherwise

        Raises:
            JVLinkError: If read operation fails

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> wrapper.jv_init()
            >>> wrapper.jv_open("RACE", "20240101", "20241231")
            >>> ret_code, buff, filename = wrapper.jv_read()
            >>> if ret_code == 0:
            ...     data = buff.decode('shift_jis')
            ...     print(data[:100])
        """
        if not self._is_open:
            raise JVLinkError("JV-Link stream not open. Call jv_open() or jv_rt_open() first.")

        try:
            import pythoncom

            # Create buffer for data
            buff = pythoncom.AllocateBuffer(BUFFER_SIZE_JVREAD)
            filename = pythoncom.AllocateBuffer(256)

            result = self._jvlink.JVRead(buff, BUFFER_SIZE_JVREAD, filename)

            if result == JV_READ_SUCCESS:
                # Successfully read data
                data_bytes = bytes(buff[: buff.find(b"\x00")])
                filename_str = filename[: filename.find(b"\x00")].decode("ascii", errors="ignore")
                return result, data_bytes, filename_str

            elif result == JV_READ_NO_MORE_DATA:
                # No more data
                logger.debug("JVRead: No more data")
                return result, None, None

            else:
                # Error
                logger.error("JVRead failed", error_code=result)
                raise JVLinkError("JVRead failed", error_code=result)

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVRead failed: {e}")

    def jv_close(self) -> int:
        """Close JV-Link data stream.

        Should be called after finishing reading data.

        Returns:
            Result code (0 = success)

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> wrapper.jv_init()
            >>> wrapper.jv_open("RACE", "20240101", "20241231")
            >>> # ... read data ...
            >>> wrapper.jv_close()
        """
        try:
            result = self._jvlink.JVClose()
            self._is_open = False
            logger.info("JV-Link stream closed")
            return result
        except Exception as e:
            raise JVLinkError(f"JVClose failed: {e}")

    def jv_status(self) -> int:
        """Get JV-Link status.

        Returns:
            Status code

        Examples:
            >>> wrapper = JVLinkWrapper("YOUR_KEY")
            >>> wrapper.jv_init()
            >>> status = wrapper.jv_status()
        """
        try:
            result = self._jvlink.JVStatus()
            logger.debug("JVStatus", status=result)
            return result
        except Exception as e:
            raise JVLinkError(f"JVStatus failed: {e}")

    def is_open(self) -> bool:
        """Check if JV-Link stream is open.

        Returns:
            True if stream is open, False otherwise
        """
        return self._is_open

    def __enter__(self):
        """Context manager entry."""
        self.jv_init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._is_open:
            self.jv_close()

    def __repr__(self) -> str:
        """String representation."""
        status = "open" if self._is_open else "closed"
        return f"<JVLinkWrapper status={status}>"
