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
        """Set JV-Link service key via Windows registry.

        This method sets the service key directly in the Windows registry,
        bypassing the unreliable JVSetServiceKey API which returns error -100.

        Args:
            service_key: JV-Link service key (format: XXXX-XXXX-XXXX-XXXX-X)

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            JVLinkError: If service key setting fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_set_service_key("5UJC-VRFM-448X-F3V4-4")
            0
            >>> wrapper.jv_init()
        """
        try:
            import subprocess
            import time

            # Set service key in Windows registry
            # IMPORTANT: JVSetServiceKey API is unreliable (returns -100), use registry instead
            reg_key = r"HKLM\SOFTWARE\JRA-VAN\JV-Link"
            result = subprocess.run(
                ['reg', 'add', reg_key, '/v', 'ServiceKey', '/t', 'REG_SZ', '/d', service_key, '/f'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info("Service key set successfully via registry")
                # Wait a bit for registry to be flushed
                time.sleep(0.5)
                return JV_RT_SUCCESS
            else:
                logger.error("Failed to set service key in registry", error=result.stderr)
                raise JVLinkError(f"Failed to set service key in registry: {result.stderr}")
        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVSetServiceKey failed: {e}")

    def jv_init(self) -> int:
        """Initialize JV-Link.

        Must be called before any other JV-Link operations.

        Note:
            Service key must be configured in JRA-VAN DataLab application
            or Windows registry before calling this method. This method only
            initializes the API connection using the session ID (sid).

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            JVLinkError: If initialization fails

        Examples:
            >>> wrapper = JVLinkWrapper()  # sid="UNKNOWN"
            >>> result = wrapper.jv_init()
            >>> assert result == 0
        """
        try:
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
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        """Open JV-Link data stream for historical data.

        Args:
            data_spec: Data specification code (e.g., "RACE", "DIFF")
            fromtime: Start time in YYYYMMDDhhmmss format (14 digits)
                     Example: "20241103000000"
                     Retrieves data from this timestamp onwards
            option: Option flag:
                    1=通常データ（差分データ取得）
                    2=今週データ（直近のレースのみ）
                    3=セットアップ（ダイアログ表示あり）
                    4=分割セットアップ（初回のみダイアログ）

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

            # Handle return value
            if isinstance(jv_result, tuple):
                if len(jv_result) == 4:
                    result, read_count, download_count, last_file_timestamp = jv_result
                else:
                    raise ValueError(f"Unexpected JVOpen return tuple length: {len(jv_result)}, expected 4")
            else:
                # Unexpected single value
                raise ValueError(f"Unexpected JVOpen return type: {type(jv_result)}, expected tuple")

            # Handle result codes for JVOpen:
            # 0 (JV_RT_SUCCESS): Success with data
            # -1: No data available (NOT an error - normal when no new data)
            # -2: No data available (alternative code)
            # < -100: Actual errors (e.g., -100=setup required, -101=auth error, etc.)
            if result < -2:
                # Real errors are typically -100 or below
                logger.error(
                    "JVOpen failed",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option,
                    error_code=result,
                )
                raise JVLinkError("JVOpen failed", error_code=result)
            elif result in (-1, -2):
                # -1 and -2 both mean "no data available" - NOT an error
                logger.info(
                    "JVOpen: No data available",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    result_code=result,
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
                # Single value: if negative, it's an error code; if positive/zero, it's read_count
                if jv_result < 0:
                    result = jv_result
                    read_count = 0
                else:
                    result = JV_RT_SUCCESS
                    read_count = jv_result

            if result < 0:
                # -1: 該当データなし（正常系 - 指定キーにデータが存在しない）
                if result == -1:
                    logger.debug("JVRTOpen: no data available", data_spec=data_spec, key=key, error_code=result)
                    # データなしは例外にせず、結果をそのまま返す
                    return result, read_count
                # -114: 契約外データ種別（警告レベル、ユーザーには問題なし）
                elif result == -114:
                    logger.debug("JVRTOpen: data spec not subscribed", data_spec=data_spec, error_code=result)
                    raise JVLinkError("JVRTOpen failed", error_code=result)
                else:
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
            ...         data = buff.decode('cp932')
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
                # JV-Link COM returns data as a BSTR (COM string type).
                # The original data is Shift-JIS encoded.
                #
                # JV-Link stores Shift-JIS bytes directly in BSTR, with each byte
                # becoming a UTF-16 code unit (zero-extended to 16 bits).
                # pywin32 then decodes this to Python str, where each original byte
                # becomes a Unicode codepoint in range U+0000-U+00FF.
                #
                # To extract raw Shift-JIS bytes:
                # - Use 'latin-1' encoding which has 1:1 mapping for bytes 0-255
                # - This perfectly recovers the original Shift-JIS bytes
                # - The parsers will then decode from Shift-JIS correctly
                #
                # Note: Previous 'shift_jis' encoding was WRONG because:
                # - The string contains raw bytes (U+0000-U+00FF), not Japanese text
                # - Bytes 0x80-0x9F are C1 control characters in Unicode
                # - These cannot be encoded as Shift-JIS, causing 'replace' to fail
                # - This caused 99.7% of Japanese text data to be corrupted with '?'
                if buff_str:
                    # JV-Link COM returns Shift-JIS encoded data.
                    # pywin32 may handle this in different ways:
                    #
                    # 1. Raw bytes as code points (0x00-0xFF) - ideal case
                    #    -> Use latin-1 to extract bytes directly
                    #
                    # 2. Some bytes interpreted as CP1252 by Windows/pywin32
                    #    -> Bytes 0x80-0x9F become Unicode chars like U+201C
                    #    -> Need to convert these back to original bytes
                    #
                    # 3. Proper Unicode (Japanese chars as U+3000+)
                    #    -> Encode to cp932 for parsers
                    #
                    # CP1252 to byte mapping for 0x80-0x9F range:
                    CP1252_TO_BYTE = {
                        0x20AC: 0x80,  # €
                        0x201A: 0x82,  # ‚
                        0x0192: 0x83,  # ƒ
                        0x201E: 0x84,  # „
                        0x2026: 0x85,  # …
                        0x2020: 0x86,  # †
                        0x2021: 0x87,  # ‡
                        0x02C6: 0x88,  # ˆ
                        0x2030: 0x89,  # ‰
                        0x0160: 0x8A,  # Š
                        0x2039: 0x8B,  # ‹
                        0x0152: 0x8C,  # Œ
                        0x017D: 0x8E,  # Ž
                        0x2018: 0x91,  # '
                        0x2019: 0x92,  # '
                        0x201C: 0x93,  # "
                        0x201D: 0x94,  # "
                        0x2022: 0x95,  # •
                        0x2013: 0x96,  # –
                        0x2014: 0x97,  # —
                        0x02DC: 0x98,  # ˜
                        0x2122: 0x99,  # ™
                        0x0161: 0x9A,  # š
                        0x203A: 0x9B,  # ›
                        0x0153: 0x9C,  # œ
                        0x017E: 0x9E,  # ž
                        0x0178: 0x9F,  # Ÿ
                    }

                    # 高速変換: 3段階のエンコード戦略
                    # 1. Latin-1（ASCII + 拡張ASCII）- 最速
                    # 2. CP932（日本語）- 高速
                    # 3. 個別処理（CP1252変換が必要な場合）- 低速だが稀
                    try:
                        data_bytes = buff_str.encode('latin-1')
                    except UnicodeEncodeError:
                        try:
                            # 日本語を含む場合はcp932で一括変換
                            data_bytes = buff_str.encode('cp932')
                        except UnicodeEncodeError:
                            # CP1252変換が必要な文字が含まれる場合のみ個別処理
                            result_bytes = bytearray()
                            for c in buff_str:
                                cp = ord(c)
                                if cp <= 0xFF:
                                    result_bytes.append(cp)
                                elif cp in CP1252_TO_BYTE:
                                    result_bytes.append(CP1252_TO_BYTE[cp])
                                elif cp == 0xFFFD:
                                    # Unicode replacement character - データ破損
                                    # 数値フィールドでエラーを避けるため'0'に置換
                                    result_bytes.append(0x30)  # '0'
                                else:
                                    try:
                                        result_bytes.extend(c.encode('cp932'))
                                    except UnicodeEncodeError:
                                        result_bytes.append(0x3F)  # '?'
                            data_bytes = bytes(result_bytes)
                else:
                    data_bytes = b""

                # Note: Per-record debug logging removed to reduce verbosity
                return result, data_bytes, filename_str

            elif result == JV_READ_SUCCESS:
                # Read complete (0)
                # Note: Debug log removed - this is logged at higher level in fetcher
                return result, None, None

            elif result == JV_READ_NO_MORE_DATA:
                # File switch (-1)
                # Note: Debug log removed - this is very frequent during data fetching
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
