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

    Important:
        - Service key must be configured in JRA-VAN DataLab application
        - JV-Link service must be running on Windows
        - Session ID (sid) is used for API tracking, not authentication

    Examples:
        >>> wrapper = JVLinkWrapper()  # Uses default sid="UNKNOWN"
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

    def __init__(self, sid: str = "UNKNOWN"):
        """Initialize JVLinkWrapper.

        Args:
            sid: Session ID for JV-Link API (default: "UNKNOWN")
                 Common values: "UNKNOWN", "Test"
                 Note: This is NOT the service key. Service key must be
                 configured separately in JRA-VAN DataLab application.

        Raises:
            JVLinkError: If COM object creation fails
        """
        self.sid = sid
        self._jvlink = None
        self._is_open = False

        try:
            import win32com.client

            self._jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
            logger.info("JV-Link COM object created", sid=sid)
        except Exception as e:
            raise JVLinkError(f"Failed to create JV-Link COM object: {e}")

    def jv_set_service_key(self, service_key: str) -> int:
        """Set JV-Link service key programmatically.

        This method allows setting the service key from the application
        without requiring registry configuration or JRA-VAN DataLab application.

        Args:
            service_key: JV-Link service key (format: XXXX-XXXX-XXXX-XXXX-X)

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            JVLinkError: If service key setting fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_set_service_key("1UJC-VRFM-24YD-K2W4-4")
            0
            >>> wrapper.jv_init()
        """
        try:
            result = self._jvlink.JVSetServiceKey(service_key)
            if result == JV_RT_SUCCESS:
                logger.info("Service key set successfully")
            else:
                logger.error("Failed to set service key", error_code=result)
                raise JVLinkError("Failed to set service key", error_code=result)
            return result
        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVSetServiceKey failed: {e}")

    def jv_init(self, service_key: Optional[str] = None) -> int:
        """Initialize JV-Link.

        Must be called before any other JV-Link operations.

        Args:
            service_key: Optional JV-Link service key. If provided, it will be set
                        before initialization. If not provided, the service key must
                        be configured in JRA-VAN DataLab application or registry.

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            JVLinkError: If initialization fails

        Examples:
            >>> # Method 1: Set service key programmatically (recommended)
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init(service_key="1UJC-VRFM-24YD-K2W4-4")

            >>> # Method 2: Use pre-configured service key from registry
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
        """
        try:
            # Set service key if provided
            if service_key is not None:
                self.jv_set_service_key(service_key)

            result = self._jvlink.JVInit(self.sid)
            if result == JV_RT_SUCCESS:
                logger.info("JV-Link initialized successfully", sid=self.sid)
            else:
                logger.error("JV-Link initialization failed", error_code=result, sid=self.sid)
                raise JVLinkError("JV-Link initialization failed", error_code=result)
            return result
        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVInit failed: {e}")

    def jv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 0,
    ) -> Tuple[int, int, int, str]:
        """Open JV-Link data stream for historical data.

        Args:
            data_spec: Data specification code (e.g., "RACE", "DIFF")
            fromtime: Start time in YYYYMMDDhhmmss format (14 digits)
                     Example: "20241103000000"
                     Retrieves data from this timestamp onwards
            option: Option flag (0=normal, 1=setup, 2=update)

        Returns:
            Tuple of (result_code, read_count, download_count, last_file_timestamp)
            - result_code: 0=success, negative=error
            - read_count: Number of records to read
            - download_count: Number of records to download
            - last_file_timestamp: Last file timestamp

        Raises:
            JVLinkError: If open operation fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> result, read_count, dl_count, timestamp = wrapper.jv_open(
            ...     "RACE", "20240101000000-20241231235959")
            >>> print(f"Will read {read_count} records")
        """
        try:
            # JVOpen signature: (dataspec, fromtime, option, ref readCount, ref downloadCount, out lastFileTimestamp)
            # pywin32: COM methods with ref/out parameters return them as tuple
            # Call with only IN parameters (dataspec, fromtime, option)
            jv_result = self._jvlink.JVOpen(data_spec, fromtime, option)

            # Debug: log the actual return value
            logger.debug(
                "JVOpen raw result",
                jv_result=jv_result,
                type=type(jv_result).__name__,
                length=len(jv_result) if isinstance(jv_result, tuple) else "N/A",
            )

            # Handle return value
            if isinstance(jv_result, tuple):
                if len(jv_result) == 4:
                    result, read_count, download_count, last_file_timestamp = jv_result
                else:
                    raise ValueError(f"Unexpected JVOpen return tuple length: {len(jv_result)}, expected 4")
            else:
                # Unexpected single value
                raise ValueError(f"Unexpected JVOpen return type: {type(jv_result)}, expected tuple")

            # Handle result codes:
            # 0: Success
            # -1: No data (not an error)
            # -2: Setup dialog cancelled (not an error)
            # < -100: Actual errors
            if result < 0 and result not in [-1, -2]:
                logger.error(
                    "JVOpen failed",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option,
                    error_code=result,
                )
                raise JVLinkError("JVOpen failed", error_code=result)
            elif result == -1:
                logger.info(
                    "JVOpen: No data available",
                    data_spec=data_spec,
                    fromtime=fromtime,
                )
            elif result == -2:
                logger.info(
                    "JVOpen: Setup dialog cancelled",
                    data_spec=data_spec,
                    fromtime=fromtime,
                )

            self._is_open = True

            logger.info(
                "JVOpen successful",
                data_spec=data_spec,
                fromtime=fromtime,
                option=option,
                read_count=read_count,
                download_count=download_count,
                last_file_timestamp=last_file_timestamp,
            )

            return result, read_count, download_count, last_file_timestamp

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
            # JVRTOpen returns (return_code, read_count) as a tuple in pywin32
            jv_result = self._jvlink.JVRTOpen(data_spec, key)

            # Handle both tuple and single value returns
            if isinstance(jv_result, tuple):
                result, read_count = jv_result
            else:
                # Single value means the read count (success case)
                result = JV_RT_SUCCESS
                read_count = jv_result

            if result < 0:
                logger.error("JVRTOpen failed", data_spec=data_spec, error_code=result)
                raise JVLinkError("JVRTOpen failed", error_code=result)

            self._is_open = True

            logger.info(
                "JVRTOpen successful",
                data_spec=data_spec,
                read_count=read_count,
            )

            return result, read_count

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVRTOpen failed: {e}")

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record from JV-Link data stream.

        Must be called after jv_open() or jv_rt_open().

        Returns:
            Tuple of (return_code, buffer, filename)
            - return_code: >0=success with data length, 0=complete, -1=file switch, <-1=error
            - buffer: Data buffer (bytes) if success, None otherwise
            - filename: Filename if applicable, None otherwise

        Raises:
            JVLinkError: If read operation fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> wrapper.jv_open("RACE", "20240101000000", 0)
            >>> while True:
            ...     ret_code, buff, filename = wrapper.jv_read()
            ...     if ret_code == 0:  # Complete
            ...         break
            ...     elif ret_code == -1:  # File switch
            ...         continue
            ...     elif ret_code < -1:  # Error
            ...         raise Exception(f"Error: {ret_code}")
            ...     else:  # ret_code > 0 (data length)
            ...         data = buff.decode('shift_jis')
            ...         print(data[:100])
        """
        if not self._is_open:
            raise JVLinkError("JV-Link stream not open. Call jv_open() or jv_rt_open() first.")

        try:
            # JVRead signature: JVRead(String buff, Long size, String filename)
            # Call with empty strings and buffer size
            # pywin32 returns 4-tuple: (return_code, buff_str, size_int, filename_str)
            jv_result = self._jvlink.JVRead("", BUFFER_SIZE_JVREAD, "")

            # Handle result - pywin32 returns (return_code, buff_str, size, filename_str)
            if isinstance(jv_result, tuple) and len(jv_result) >= 4:
                result = jv_result[0]
                buff_str = jv_result[1]
                # jv_result[2] is size (int) - not needed
                filename_str = jv_result[3]
            else:
                # Unexpected return format
                raise JVLinkError(f"Unexpected JVRead return format: {type(jv_result)}, length={len(jv_result) if isinstance(jv_result, tuple) else 'N/A'}")

            # Return code meanings:
            # > 0: Success, value is data length in bytes
            # 0: Read complete (no more data)
            # -1: File switch (continue reading)
            # < -1: Error
            if result > 0:
                # Successfully read data (result is data length)
                # buff_str is already in Shift_JIS encoding (Unicode string from COM)
                # Convert to bytes for consistent handling
                try:
                    data_bytes = buff_str.encode(ENCODING_JVDATA) if buff_str else b""
                except Exception:
                    # If encoding fails, try with error handling
                    data_bytes = buff_str.encode('shift_jis', errors='ignore') if buff_str else b""

                logger.debug("JVRead success", data_len=result, actual_len=len(data_bytes), filename=filename_str)
                return result, data_bytes, filename_str

            elif result == JV_READ_SUCCESS:
                # Read complete (0)
                logger.debug("JVRead: Complete")
                return result, None, None

            elif result == JV_READ_NO_MORE_DATA:
                # File switch (-1)
                logger.debug("JVRead: File switch")
                return result, None, None

            else:
                # Error (< -1)
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
