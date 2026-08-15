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
    is_retired_data_spec,
    retired_data_spec_message,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# CP1252 to byte mapping for 0x80-0x9F range
# Moved to module level for performance (避けたい: ホットループ内での辞書再作成)
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


def _recover_com_buffer(value, expected_size: int, method_name: str) -> bytes:
    """Recover the exact JV-Data bytes from a pywin32 out buffer.

    Depending on the COM marshaling path, pywin32 can expose the buffer as a
    byte array, a BSTR containing one Unicode code point per byte, or decoded
    CP932 text.  Recovery must be lossless: replacement characters and unknown
    code points are protocol failures, never plausible ``0``/``?`` data.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        recovered = bytes(value)
    elif isinstance(value, str):
        if "\ufffd" in value:
            raise JVLinkError(
                f"{method_name} buffer contains an irreversible Unicode replacement character"
            )

        try:
            recovered = value.encode("latin-1")
        except UnicodeEncodeError:
            if any(ord(char) in CP1252_TO_BYTE for char in value):
                result = bytearray()
                for char in value:
                    codepoint = ord(char)
                    if codepoint <= 0xFF:
                        result.append(codepoint)
                    elif codepoint in CP1252_TO_BYTE:
                        result.append(CP1252_TO_BYTE[codepoint])
                    else:
                        try:
                            result.extend(char.encode("cp932"))
                        except UnicodeEncodeError as exc:
                            raise JVLinkError(
                                f"{method_name} buffer contains an unrecoverable "
                                f"character U+{codepoint:04X}"
                            ) from exc
                recovered = bytes(result)
            else:
                try:
                    recovered = value.encode("cp932")
                except UnicodeEncodeError as exc:
                    bad = exc.object[exc.start]
                    raise JVLinkError(
                        f"{method_name} buffer contains an unrecoverable "
                        f"character U+{ord(bad):04X}"
                    ) from exc
    else:
        raise JVLinkError(
            f"{method_name} returned unsupported buffer type {type(value).__name__}"
        )

    if len(recovered) < expected_size:
        raise JVLinkError(
            f"{method_name} buffer is shorter than its return byte count: "
            f"{len(recovered)} < {expected_size}"
        )
    return recovered[:expected_size]


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
        self._needs_close = False
        self._com_initialized = False

        try:
            import sys
            # Set COM threading model to Apartment Threaded (STA)
            sys.coinit_flags = 2  # type: ignore[attr-defined]

            import pythoncom
            import win32com.client

            # Initialize COM
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception:
                # COM may already be initialized in this thread
                pass

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
            data_spec: Data specification code (e.g., "RACE", "DIFN")
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
            ValueError: If data_spec selects an unsupported legacy layout
            JVLinkError: If open operation fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> result, read_count, dl_count, timestamp = wrapper.jv_open(
            ...     "RACE", "20240101000000-20241231235959")
            >>> print(f"Will read {read_count} records")
        """
        # 非対応の旧仕様 dataspec は COM の JVOpen に渡す前に弾く。fetcher を経由
        # しない直接利用も同じ境界で fail-closed にする。try の外に置くのは、
        # 下の except が ValueError を JVLinkError に包んでしまうため。
        if is_retired_data_spec(data_spec):
            raise ValueError(retired_data_spec_message(data_spec))

        try:
            # JVOpen signature: (dataspec, fromtime, option, ref readCount, ref downloadCount, out lastFileTimestamp)
            # Dynamic pywin32 dispatch still requires placeholders for all
            # official ref/out parameters and returns their values as a tuple.
            jv_result = self._jvlink.JVOpen(
                data_spec,
                fromtime,
                option,
                0,
                0,
                "",
            )

            # JVOpen has already changed COM state before pywin32 marshals its
            # out values. Preserve the close obligation even when that
            # marshaled response is malformed and cannot be returned.
            possible_result = (
                jv_result[0]
                if isinstance(jv_result, tuple) and jv_result
                else jv_result
            )
            if type(possible_result) is int and possible_result in (
                0,
                -1,
                -2,
                -202,
            ):
                self._needs_close = True
                self._is_open = possible_result == 0

            # Handle return value
            if isinstance(jv_result, tuple):
                if len(jv_result) == 4:
                    result, read_count, download_count, last_file_timestamp = jv_result
                else:
                    raise ValueError(f"Unexpected JVOpen return tuple length: {len(jv_result)}, expected 4")
            else:
                # Unexpected single value
                raise ValueError(f"Unexpected JVOpen return type: {type(jv_result)}, expected tuple")

            if type(result) is not int:
                raise JVLinkError(
                    f"JVOpen returned a non-integer result code: {result!r}"
                )

            # Handle result codes for JVOpen (per official spec "3. コード表",
            # JVOpen/JVRTOpen never returns -100/-101/-102/-103 -- those are
            # JVSetUIProperties/JVSetServiceKey/JVInit codes; JVOpen's actual
            # errors start at -111):
            # 0 (JV_RT_SUCCESS): Success with data
            # -1: No data available (NOT an error - normal when no new data)
            # -2: Setup dialog cancelled by the user
            # <= -111: Actual errors (e.g., -111=dataspec invalid, -301=auth error, etc.)
            if result not in (0, -1, -2):
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
                    result_code=result,
                )
            elif result == -2:
                logger.warning(
                    "JVOpen: setup dialog cancelled",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    result_code=result,
                )

            malformed_fields = []
            if type(read_count) is not int or read_count < 0:
                malformed_fields.append(f"invalid read_count={read_count!r}")
            if type(download_count) is not int or download_count < 0:
                malformed_fields.append(
                    f"invalid download_count={download_count!r}"
                )
            if (
                type(read_count) is int
                and type(download_count) is int
                and download_count > read_count
            ):
                malformed_fields.append(
                    "download_count exceeds read_count: "
                    f"{download_count} > {read_count}"
                )
            if not isinstance(last_file_timestamp, str):
                malformed_fields.append(
                    "invalid last_file_timestamp="
                    f"{last_file_timestamp!r}"
                )
            if malformed_fields:
                raise JVLinkError(
                    "Malformed JVOpen response: " + ", ".join(malformed_fields)
                )

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
            # The official JVRTOpen return value is the result code only. Keep
            # accepting the historical two-item wrapper shape for API
            # compatibility, but never reinterpret a positive result code as
            # a read count.
            jv_result = self._jvlink.JVRTOpen(data_spec, key)

            possible_result = (
                jv_result[0]
                if isinstance(jv_result, tuple) and jv_result
                else jv_result
            )
            if type(possible_result) is int and possible_result in (
                0,
                -1,
                -2,
                -202,
            ):
                self._needs_close = True
                if possible_result != -202:
                    self._is_open = possible_result == 0

            if isinstance(jv_result, tuple):
                if len(jv_result) != 2:
                    raise JVLinkError(
                        "Unexpected JVRTOpen return tuple length: "
                        f"{len(jv_result)}, expected 2"
                    )
                result, read_count = jv_result
            else:
                result = jv_result
                read_count = 0

            if type(result) is not int:
                raise JVLinkError(
                    f"Unexpected JVRTOpen result code: {result!r}"
                )
            if type(read_count) is not int or read_count < 0:
                raise JVLinkError(
                    f"Unexpected JVRTOpen compatibility read count: {read_count!r}"
                )

            if result in (0, -1) and read_count != 0:
                raise JVLinkError(
                    "JVRTOpen compatibility read count must be 0, "
                    f"got {read_count}"
                )

            if result != JV_RT_SUCCESS:
                # -1: 該当データなし（正常系 - 指定キーにデータが存在しない）
                if result == -1:
                    logger.debug("JVRTOpen: no data available", data_spec=data_spec, key=key, error_code=result)
                    # データなしは例外にせず、結果をそのまま返す
                    return result, read_count
                if result in (-2, -202):
                    # The shared official return-code table requires JVClose
                    # after setup cancellation or an already-open result.
                    self._needs_close = True
                # -114: 契約外データ種別（警告レベル、ユーザーには問題なし）
                if result == -114:
                    logger.debug("JVRTOpen: data spec not subscribed", data_spec=data_spec, error_code=result)
                    raise JVLinkError("JVRTOpen failed", error_code=result)
                else:
                    logger.error("JVRTOpen failed", data_spec=data_spec, error_code=result)
                    raise JVLinkError("JVRTOpen failed", error_code=result)

            self._is_open = True
            self._needs_close = True

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
            # Official signature: JVRead(String buff, Long size, String
            # filename). bytearray placeholders avoid unstable pywin32 out-
            # parameter marshaling observed with empty strings.
            jv_result = self._jvlink.JVRead(
                bytearray(),
                BUFFER_SIZE_JVREAD,
                bytearray(),
            )

            # Handle result - pywin32 returns (return_code, buff_str, size, filename_str)
            if isinstance(jv_result, tuple) and len(jv_result) == 4:
                result = jv_result[0]
                buff_str = jv_result[1]
                # jv_result[2] is size (int) - not needed
                filename_str = jv_result[3]
            elif isinstance(jv_result, tuple) and len(jv_result) == 3:
                # Some pywin32 dispatch paths omit the input-only size from
                # the returned out-parameter tuple.
                result, buff_str, filename_str = jv_result
            else:
                # Unexpected return format
                result_length = (
                    len(jv_result) if isinstance(jv_result, tuple) else "N/A"
                )
                raise JVLinkError(
                    "Unexpected JVRead return format: "
                    f"{type(jv_result)}, length={result_length}"
                )

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
                data_bytes = _recover_com_buffer(buff_str, result, "JVRead")

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

            elif result == -3:
                logger.debug(
                    "JVRead waiting for file download",
                    filename=filename_str,
                )
                return result, None, filename_str

            elif result in (-402, -403):
                # Preserve the filename returned by JVRead so the fetcher can
                # apply its recovery policy without inspecting cache paths.
                logger.warning(
                    "JVRead returned recoverable file error",
                    error_code=result,
                    filename=filename_str,
                )
                return result, None, filename_str

            else:
                # Error (< -1)
                logger.error("JVRead failed", error_code=result)
                raise JVLinkError("JVRead failed", error_code=result)

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVRead failed: {e}")

    def jv_gets(self) -> Tuple[int, Optional[bytes]]:
        """Read one record from JV-Link data stream using JVGets (faster than JVRead).

        JVGets returns Shift-JIS encoded byte array directly, which is faster than
        JVRead that returns Unicode string. This method is recommended for high-performance
        data fetching.

        Must be called after jv_open() or jv_rt_open().

        Returns:
            Tuple of (return_code, buffer)
            - return_code: >0=success with data length, 0=complete, -1=file switch, <-1=error
            - buffer: Shift-JIS encoded data buffer (bytes) if success, None otherwise

        Raises:
            JVLinkError: If read operation fails

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> wrapper.jv_open("RACE", "20240101000000", 1)
            >>> while True:
            ...     ret_code, buff = wrapper.jv_gets()
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
            # Official signature: JVGets(Byte Array buff, Long size,
            # String filename). Dynamic dispatch requires all placeholders.
            jv_result = self._jvlink.JVGets(
                bytearray(),
                BUFFER_SIZE_JVREAD,
                bytearray(),
            )

            # Working dynamic-dispatch paths return (return_code, memoryview,
            # filename). Accept a four-item variant as well for compatibility
            # with type libraries that echo the input size.
            if isinstance(jv_result, tuple) and len(jv_result) in (3, 4):
                result = jv_result[0]
                buff_str = jv_result[1]
            else:
                # Unexpected return format
                result_length = (
                    len(jv_result) if isinstance(jv_result, tuple) else "N/A"
                )
                raise JVLinkError(
                    "Unexpected JVGets return format: "
                    f"{type(jv_result)}, length={result_length}"
                )

            # Return code meanings:
            # > 0: Success, value is data length in bytes
            # 0: Read complete (no more data)
            # -1: File switch (continue reading)
            # < -1: Error
            if result > 0:
                return result, _recover_com_buffer(buff_str, result, "JVGets")

            elif result == JV_READ_SUCCESS:
                # Read complete (0)
                return result, None

            elif result == JV_READ_NO_MORE_DATA:
                # File switch (-1)
                return result, None

            elif result == -3:
                logger.debug("JVGets waiting for file download")
                return result, None

            else:
                # Error (< -1)
                logger.error("JVGets failed", error_code=result)
                raise JVLinkError("JVGets failed", error_code=result)

        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVGets failed: {e}")

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
            if type(result) is not int or result != 0:
                raise JVLinkError(
                    f"JVClose returned an invalid result code: {result!r}",
                    error_code=result if type(result) is int else None,
                )
            self._is_open = False
            self._needs_close = False
            logger.info("JV-Link stream closed")
            return result
        except Exception as e:
            if isinstance(e, JVLinkError):
                raise
            raise JVLinkError(f"JVClose failed: {e}")

    def jv_file_delete(self, filename: str) -> int:
        """Delete a cached file from JV-Link cache.

        This method is used for the official corrupt-downloaded-file errors
        (-402 and -403). After deleting the exact filename returned by
        JVRead/JVGets, callers must restart from JVOpen. Other call-order,
        download, or missing-file errors are not repaired by blind deletion.

        Args:
            filename: The filename to delete (as returned by JVRead)

        Returns:
            Result code (0 = success)

        Raises:
            JVLinkError: If file deletion fails
        """
        try:
            result = self._jvlink.JVFiledelete(filename)
            logger.info("JVFiledelete called", filename=filename, result=result)
            return result
        except Exception as e:
            raise JVLinkError(f"JVFiledelete failed: {e}")

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
        if self._is_open or getattr(self, "_needs_close", False):
            self.jv_close()

    def reinitialize_com(self):
        """Reinitialize COM component to recover from catastrophic errors.

        This method should be called when encountering error -2147418113 (E_UNEXPECTED)
        or other catastrophic COM failures during JV-Link operations.

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> try:
            ...     wrapper.jv_open("RACE", "20240101000000", 1)
            ... except Exception as e:
            ...     if "E_UNEXPECTED" in str(e):
            ...         wrapper.reinitialize_com()
            ...         wrapper.jv_init()  # Re-initialize after recovery
        """
        try:
            import sys
            sys.coinit_flags = 2  # type: ignore[attr-defined]

            import pythoncom
            import win32com.client
            import time

            logger.warning("Reinitializing COM component due to error...")

            # Close any open streams
            if self._is_open or getattr(self, "_needs_close", False):
                try:
                    self.jv_close()
                except Exception:
                    pass

            # Uninitialize and reinitialize COM
            if self._com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

            # Wait for COM cleanup
            time.sleep(1)

            # Reinitialize COM
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception:
                pass

            # Recreate COM object
            # JV-Link ProgID: JVDTLab.JVLink
            try:
                self._jvlink = win32com.client.Dispatch("JVDTLab.JVLink")
            except Exception as e:
                # If ProgID fails, try with CLSID (if known)
                logger.error("Failed to recreate JV-Link COM object", error=str(e))
                raise

            self._is_open = False
            self._needs_close = False

            logger.info("COM component reinitialized successfully", sid=self.sid)

        except Exception as e:
            logger.error("Failed to reinitialize COM component", error=str(e))
            raise JVLinkError(f"COM reinitialization failed: {e}")

    def cleanup(self):
        """Explicitly cleanup COM resources. Call this before the object goes out of scope.

        This prevents "Win32 exception occurred releasing IUnknown" warnings
        that occur when COM objects are released during Python shutdown.

        Examples:
            >>> wrapper = JVLinkWrapper()
            >>> wrapper.jv_init()
            >>> # ... use wrapper ...
            >>> wrapper.cleanup()  # Explicit cleanup before deletion
        """
        # Check if Python is shutting down
        # During shutdown, imports may fail or sys.meta_path becomes None
        try:
            import sys
            if sys.meta_path is None:
                return
        except (ImportError, ModuleNotFoundError):
            return

        try:
            import gc
        except (ImportError, ModuleNotFoundError):
            gc = None

        # Close stream if still open
        if hasattr(self, '_is_open') and (
            self._is_open or getattr(self, '_needs_close', False)
        ):
            try:
                self.jv_close()
            except Exception:
                pass

        # Release COM object reference BEFORE CoUninitialize
        # This prevents "Win32 exception occurred releasing IUnknown" warnings
        if hasattr(self, '_jvlink') and self._jvlink is not None:
            try:
                # Set to None first to break reference
                jvlink_ref = self._jvlink
                self._jvlink = None
                # Force garbage collection while COM is still initialized
                del jvlink_ref
                if gc is not None:
                    gc.collect()
            except Exception:
                pass

        # Uninitialize COM if we initialized it
        if hasattr(self, '_com_initialized') and self._com_initialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
                self._com_initialized = False
            except Exception:
                pass

    def __del__(self):
        """Destructor to ensure proper cleanup."""
        self.cleanup()

    def __repr__(self) -> str:
        """String representation."""
        status = "open" if self._is_open else "closed"
        return f"<JVLinkWrapper status={status}>"
