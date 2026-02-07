"""NV-Link COM API Wrapper.

This module provides a Python wrapper for the NV-Link COM API,
which is used to access UmaConn (地方競馬DATA) horse racing data.
"""

from typing import Optional, Tuple

from src.nvlink.constants import (
    BUFFER_SIZE_NVREAD,
    ENCODING_NVDATA,
    NV_READ_ERROR,
    NV_READ_NO_MORE_DATA,
    NV_READ_SUCCESS,
    NV_RT_ERROR,
    NV_RT_SUCCESS,
    get_error_message,
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


class NVLinkError(Exception):
    """NV-Link related error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        """Initialize NVLinkError.

        Args:
            message: Error message
            error_code: NV-Link error code
        """
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code}, {get_error_message(error_code)})"
        super().__init__(message)


class NVLinkWrapper:
    """Wrapper class for NV-Link COM API.

    This class provides a Pythonic interface to the NV-Link COM API,
    handling Windows COM object creation and method calls.

    Important:
        - Service key must be configured in UmaConn (地方競馬DATA) application
        - NV-Link service must be running on Windows
        - Session ID (sid) is used for API tracking, not authentication

    Examples:
        >>> wrapper = NVLinkWrapper()  # Uses default sid="UNKNOWN"
        >>> wrapper.nv_init()
        0
        >>> result, count = wrapper.nv_open("RACE", "20240101", "20241231")
        >>> while True:
        ...     ret_code, buff, filename = wrapper.nv_read()
        ...     if ret_code == NV_READ_NO_MORE_DATA:
        ...         break
        ...     # Process data
        >>> wrapper.nv_close()
    """

    def __init__(self, sid: str = "UNKNOWN", initialization_key: Optional[str] = None):
        """Initialize NVLinkWrapper.

        Args:
            sid: Session ID for NV-Link API (default: "UNKNOWN")
                 Common values: "UNKNOWN", "Test"
                 Note: This is NOT the service key. Service key must be
                 configured separately in UmaConn (地方競馬DATA) application.
            initialization_key: Optional NV-Link initialization key (software ID)
                used for NVInit. If provided, this value is used instead of sid.

        Raises:
            NVLinkError: If COM object creation fails
        """
        self.sid = sid
        self.initialization_key = initialization_key
        self._nvlink = None
        self._is_open = False
        self._com_initialized = False

        try:
            import sys
            # Set COM threading model to Apartment Threaded (STA)
            # This is critical for 64-bit Python to communicate with 32-bit UmaConn (ActiveX/GUI)
            sys.coinit_flags = 2
            
            import pythoncom
            import win32com.client
            import win32com.client.dynamic

            # Initialize COM apartment (STA mode for compatibility with UI components)
            # This prevents "Window handle is invalid" (error 1400) errors
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception as e:
                # S_FALSE (already initialized) is safe; log other errors
                if "already" not in str(e).lower():
                    logger.warning("COM initialization issue", error=str(e))

            # Use CLSID directly instead of ProgID
            # ProgID "NVDTLab.NVLink" may not be registered, but CLSID always works
            # after regsvr32 NVDTLab.dll
            NVLINK_CLSID = "{F726BBA6-5784-4529-8C67-26E152D49D73}"
            try:
                # Try NVDTLabLib.NVLink first (matches quickstart.py and seems correct for this environment)
                self._nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
                logger.info("NV-Link COM object created using NVDTLabLib.NVLink", sid=sid)
            except Exception:
                try:
                    # Try ProgID first (faster if registered)
                    self._nvlink = win32com.client.Dispatch("NVDTLab.NVLink")
                    logger.info("NV-Link COM object created using NVDTLab.NVLink", sid=sid)
                except Exception:
                    # Fallback to CLSID
                    self._nvlink = win32com.client.Dispatch(NVLINK_CLSID)
                    logger.info("NV-Link COM object created using CLSID", sid=sid)
        except Exception as e:
            raise NVLinkError(
                f"UmaConn (地方競馬DATA) がインストールされていません。地方競馬DATAのセットアップを完了してください。詳細: {e}"
            )

    def nv_set_service_key(self, service_key: str) -> int:
        """Set NV-Link service key.

        Args:
            service_key: NV-Link service key (format: XXXX-XXXX-XXXX-XXXX-X)

        Returns:
            Result code (0 = success)

        Raises:
            NVLinkError: If service key setting fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_set_service_key("5UJC-VRFM-448X-F3V4-4")
            0
            >>> wrapper.nv_init()
        """
        try:
            result = int(self._nvlink.NVSetServiceKey(service_key))
            if result == NV_RT_SUCCESS:
                logger.info("Service key set successfully")
            else:
                logger.warning("Failed to set service key", error_code=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVSetServiceKey failed: {e}")

    def nv_set_ui_properties(self) -> int:
        """Open NV-Link UI configuration dialog.

        Opens the NVDTLab configuration tool UI where users can configure
        service key, data paths, and other settings.

        Returns:
            Result code (0 = success)

        Raises:
            NVLinkError: If opening UI fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_set_ui_properties()  # Opens config dialog
            0
        """
        try:
            result = int(self._nvlink.NVSetUIProperties())
            logger.info("NVSetUIProperties called", result=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVSetUIProperties failed: {e}")

    def nv_set_save_path(self, save_path: str) -> int:
        """Set NV-Link data save path.

        Args:
            save_path: Directory path to save downloaded data

        Returns:
            Result code (0 = success)

        Raises:
            NVLinkError: If setting save path fails
        """
        try:
            result = int(self._nvlink.NVSetSavePath(save_path))
            if result == NV_RT_SUCCESS:
                logger.info("Save path set successfully", save_path=save_path)
            else:
                logger.warning("Failed to set save path", error_code=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVSetSavePath failed: {e}")

    def nv_set_save_flag(self, save_flag: int) -> int:
        """Set NV-Link save flag.

        Args:
            save_flag: Save flag (0=don't save, 1=save)

        Returns:
            Result code (0 = success)

        Raises:
            NVLinkError: If setting save flag fails
        """
        try:
            result = int(self._nvlink.NVSetSaveFlag(save_flag))
            if result == NV_RT_SUCCESS:
                logger.info("Save flag set successfully", save_flag=save_flag)
            else:
                logger.warning("Failed to set save flag", error_code=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVSetSaveFlag failed: {e}")

    def nv_cancel(self) -> None:
        """Cancel current NV-Link download operation.

        Cancels any ongoing download operation.

        Raises:
            NVLinkError: If cancel fails
        """
        try:
            self._nvlink.NVCancel()
            logger.info("NVCancel called")
        except Exception as e:
            raise NVLinkError(f"NVCancel failed: {e}")

    def get_version(self) -> str:
        """Get NV-Link version.

        Returns:
            NV-Link version string

        Raises:
            NVLinkError: If getting version fails
        """
        try:
            version = self._nvlink.m_NVLinkVersion
            logger.debug("NVLink version", version=version)
            return version
        except Exception as e:
            raise NVLinkError(f"Failed to get NVLink version: {e}")

    def get_service_key(self) -> str:
        """Get configured service key.

        Returns:
            Service key string (may be empty if not configured)

        Raises:
            NVLinkError: If getting service key fails
        """
        try:
            service_key = self._nvlink.m_servicekey
            return service_key if service_key else ""
        except Exception as e:
            raise NVLinkError(f"Failed to get service key: {e}")

    def nv_init(self) -> int:
        """Initialize NV-Link.

        Must be called before any other NV-Link operations.

        Note:
            Service key must be configured in UmaConn (地方競馬DATA) application
            or Windows registry before calling this method. This method only
            initializes the API connection using the session ID (sid).

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            NVLinkError: If initialization fails

        Examples:
            >>> wrapper = NVLinkWrapper()  # sid="UNKNOWN"
            >>> result = wrapper.nv_init()
            >>> assert result == 0
        """
        try:
            init_key = self.initialization_key or self.sid
            result = int(self._nvlink.NVInit(init_key))
            if result == NV_RT_SUCCESS:
                logger.info(
                    "NV-Link initialized successfully",
                    sid=self.sid,
                    init_key=init_key if init_key != self.sid else None,
                )
            else:
                # エラーコード別の詳細メッセージ
                if result == -100:
                    error_msg = "地方競馬DATAのサービスキーが設定されていません。NVDTLab設定ツールで設定してください。"
                else:
                    error_msg = "NV-Link initialization failed"
                logger.error(error_msg, error_code=result, sid=self.sid, init_key=init_key)
                raise NVLinkError(error_msg, error_code=result)
            return result
        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVInit failed: {e}")

    def nv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        """Open NV-Link data stream for historical data.

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
            NVLinkError: If open operation fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> result, read_count, dl_count, timestamp = wrapper.nv_open(
            ...     "RACE", "20240101000000-20241231235959")
            >>> print(f"Will read {read_count} records")
        """
        try:
            # NVOpen signature: (dataspec, fromtime, option, ref readCount, ref downloadCount, out lastFileTimestamp)
            # The COM interface requires all parameters including in/out parameters
            # readcount and downloadcount are in/out ref parameters - must pass integer values
            # gen_py wrapper with _ApplyTypes_ will handle byref conversion automatically
            #
            # Parameter types from gen_py:
            # - dataspec: VT_BSTR (8, 1) - input string
            # - fromdate: VT_BSTR (8, 1) - input string
            # - option: VT_I4 (3, 1) - input integer
            # - readcount: VT_I4|VT_BYREF (16387, 3) - in/out reference
            # - downloadcount: VT_I4|VT_BYREF (16387, 3) - in/out reference
            # - lastfiletimestamp: VT_BSTR|VT_BYREF (16392, 2) - out reference (optional)
            nv_result = self._nvlink.NVOpen(data_spec, fromtime, option, 0, 0)

            # Handle return value
            if isinstance(nv_result, tuple):
                if len(nv_result) == 4:
                    result, read_count, download_count, last_file_timestamp = nv_result
                else:
                    raise ValueError(f"Unexpected NVOpen return tuple length: {len(nv_result)}, expected 4")
            else:
                # Unexpected single value
                raise ValueError(f"Unexpected NVOpen return type: {type(nv_result)}, expected tuple")

            # Handle result codes for NVOpen (based on kmy-keiba JVLinkLoadResult):
            # 0 (NV_RT_SUCCESS): Success with data
            # -1: No data available (NOT an error - normal when no new data)
            # -2: SetupCanceled (セットアップダイアログでキャンセル)
            # -111/-114: Data spec not subscribed (契約外データ)
            # -201: Not initialized (NVInitが呼ばれていない)
            # -202: Already open (NVCloseが必要)
            # -203: Not opened (接続が開かれていない)
            # -301: Authentication error (認証エラー)
            # -302: Licence key expired (利用キー不正)
            # -303: Licence key not set (利用キー未設定)
            # -5xx: Download/server errors

            # Check for authentication errors first (-301, -302, -303)
            if result in (-301, -302, -303):
                if result == -301:
                    error_msg = "認証エラー: サーバー認証に失敗しました。サービスキーを確認してください。"
                elif result == -302:
                    error_msg = "認証エラー: 利用キーが不正または有効期限切れです。"
                else:
                    error_msg = "認証エラー: 利用キーが設定されていません。地方競馬DATAセットアップツールで設定してください。"
                logger.error(
                    error_msg,
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option,
                    error_code=result,
                )
                raise NVLinkError(error_msg, error_code=result)

            if result < -2:
                # Real errors are typically -100 or below
                # エラーコード別の詳細メッセージ
                if result == -111 or result == -114:
                    error_msg = "このデータ種別は地方競馬DATAの契約に含まれていません。"
                else:
                    error_msg = "NVOpen failed"
                logger.error(
                    error_msg,
                    data_spec=data_spec,
                    fromtime=fromtime,
                    option=option,
                    error_code=result,
                )
                raise NVLinkError(error_msg, error_code=result)
            elif result in (-1, -2):
                # -1 and -2 both mean "no data available" - NOT an error
                logger.info(
                    "NVOpen: No data available",
                    data_spec=data_spec,
                    fromtime=fromtime,
                    result_code=result,
                )

            self._is_open = True

            logger.info(
                "NVOpen successful",
                data_spec=data_spec,
                fromtime=fromtime,
                option=option,
                read_count=read_count,
                download_count=download_count,
                last_file_timestamp=last_file_timestamp,
            )

            return result, read_count, download_count, last_file_timestamp

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVOpen failed: {e}")

    def nv_rt_open(self, data_spec: str, key: str = "") -> Tuple[int, int]:
        """Open NV-Link data stream for real-time data.

        Args:
            data_spec: Real-time data specification (e.g., "0B12", "0B15")
            key: Key parameter (usually empty string)

        Returns:
            Tuple of (result_code, read_count)

        Raises:
            NVLinkError: If open operation fails

        Examples:
            >>> wrapper = NVLinkWrapper("YOUR_KEY")
            >>> wrapper.nv_init()
            >>> result, count = wrapper.nv_rt_open("0B12")  # Race results
        """
        try:
            # NVRTOpen returns (return_code, read_count) as a tuple in pywin32
            nv_result = self._nvlink.NVRTOpen(data_spec, key)

            # Handle both tuple and single value returns
            if isinstance(nv_result, tuple):
                result, read_count = nv_result
            else:
                # Single value: if negative, it's an error code; if positive/zero, it's read_count
                if nv_result < 0:
                    result = nv_result
                    read_count = 0
                else:
                    result = NV_RT_SUCCESS
                    read_count = nv_result

            if result < 0:
                # -1: 該当データなし（正常系 - 指定キーにデータが存在しない）
                if result == -1:
                    logger.debug("NVRTOpen: no data available", data_spec=data_spec, key=key, error_code=result)
                    # データなしは例外にせず、結果をそのまま返す
                    return result, read_count
                # -111/-114: 契約外データ種別（警告レベル - 例外にせず返す）
                elif result == -111 or result == -114:
                    logger.debug("NVRTOpen: data spec not subscribed", data_spec=data_spec, error_code=result)
                    # 契約外データは例外にせず、結果を返す（呼び出し側で判断）
                    return result, read_count
                else:
                    logger.error("NVRTOpen failed", data_spec=data_spec, error_code=result)
                    raise NVLinkError("NVRTOpen failed", error_code=result)

            self._is_open = True

            logger.info(
                "NVRTOpen successful",
                data_spec=data_spec,
                read_count=read_count,
            )

            return result, read_count

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVRTOpen failed: {e}")

    def nv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record from NV-Link data stream.

        Must be called after nv_open() or nv_rt_open().

        Returns:
            Tuple of (return_code, buffer, filename)
            - return_code: >0=success with data length, 0=complete, -1=file switch, <-1=error
            - buffer: Data buffer (bytes) if success, None otherwise
            - filename: Filename if applicable, None otherwise

        Raises:
            NVLinkError: If read operation fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> wrapper.nv_open("RACE", "20240101000000", 0)
            >>> while True:
            ...     ret_code, buff, filename = wrapper.nv_read()
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
            raise NVLinkError("NV-Link stream not open. Call nv_open() or nv_rt_open() first.")

        try:
            # NVRead signature: NVRead(String buff, Long size, String filename)
            # Call with empty strings and buffer size
            # pywin32 returns 4-tuple: (return_code, buff_str, size_int, filename_str)
            nv_result = self._nvlink.NVRead("", BUFFER_SIZE_NVREAD, "")

            # Handle result - pywin32 returns (return_code, buff_str, size, filename_str)
            if isinstance(nv_result, tuple) and len(nv_result) >= 4:
                result = nv_result[0]
                buff_str = nv_result[1]
                # nv_result[2] is size (int) - not needed
                filename_str = nv_result[3]
            else:
                # Unexpected return format
                raise NVLinkError(f"Unexpected NVRead return format: {type(nv_result)}, length={len(nv_result) if isinstance(nv_result, tuple) else 'N/A'}")

            # Return code meanings:
            # > 0: Success, value is data length in bytes
            # 0: Read complete (no more data)
            # -1: File switch (continue reading)
            # < -1: Error
            if result > 0:
                # Successfully read data (result is data length)
                # NV-Link COM returns data as a BSTR (COM string type).
                # The original data is Shift-JIS encoded.
                #
                # NV-Link stores Shift-JIS bytes directly in BSTR, with each byte
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
                    # NV-Link COM returns Shift-JIS encoded data.
                    # pywin32 may handle this in different ways:
                    #
                    # 1. Raw bytes as code points (0x00-0xFF) - ideal case
                    #    -> Use latin-1 to extract bytes directly
                    #
                    # 2. Some bytes interpreted as CP1252 by Windows/pywin32
                    #    -> Bytes 0x80-0x9F become Unicode chars like U+201C
                    #    -> Need to convert these back to original bytes
                    #    -> Use module-level CP1252_TO_BYTE mapping
                    #
                    # 3. Proper Unicode (Japanese chars as U+3000+)
                    #    -> Encode to cp932 for parsers

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

            elif result == NV_READ_SUCCESS:
                # Read complete (0)
                # Note: Debug log removed - this is logged at higher level in fetcher
                return result, None, None

            elif result == NV_READ_NO_MORE_DATA:
                # File switch (-1)
                # Note: Debug log removed - this is very frequent during data fetching
                return result, None, None

            else:
                # Error (< -1)
                logger.error("NVRead failed", error_code=result)
                raise NVLinkError("NVRead failed", error_code=result)

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            # Check for E_UNEXPECTED COM error (-2147418113)
            # This happens due to NV-Link memory leak / dialog popups
            # COM object is broken - cannot continue reading
            error_str = str(e)
            if "-2147418113" in error_str or "E_UNEXPECTED" in error_str:
                logger.error("COM E_UNEXPECTED error in NVRead - COM object is broken, stopping read", error=error_str)
                # Return 0 (read complete) to stop the read loop gracefully
                # The data read so far will be saved
                self._is_open = False
                return 0, None, None
            raise NVLinkError(f"NVRead failed: {e}")

    def nv_gets(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record from NV-Link data stream using NVGets (faster than NVRead).

        NVGets returns Shift-JIS encoded byte array directly, which is faster than
        NVRead that returns Unicode string. This method is recommended for high-performance
        data fetching.

        Must be called after nv_open() or nv_rt_open().

        Returns:
            Tuple of (return_code, buffer, filename)
            - return_code: >0=success with data length, 0=complete, -1=file switch, <-1=error
            - buffer: Shift-JIS encoded data buffer (bytes) if success, None otherwise
            - filename: Current filename being read (useful for error recovery with nv_file_delete)

        Note:
            Based on kmy-keiba's error handling, when return_code is -203, -402, -403, -502, or -503,
            call nv_file_delete(filename) and continue reading to skip corrupted files.

        Raises:
            NVLinkError: If read operation fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> wrapper.nv_open("RACE", "20240101000000", 1)
            >>> while True:
            ...     ret_code, buff, filename = wrapper.nv_gets()
            ...     if ret_code == 0:  # Complete
            ...         break
            ...     elif ret_code == -1:  # File switch
            ...         continue
            ...     elif ret_code in (-203, -402, -403, -502, -503):  # Recoverable error
            ...         if filename:
            ...             wrapper.nv_file_delete(filename)
            ...         continue
            ...     elif ret_code < -1:  # Fatal error
            ...         raise Exception(f"Error: {ret_code}")
            ...     else:  # ret_code > 0 (data length)
            ...         data = buff.decode('cp932')
            ...         print(data[:100])
        """
        if not self._is_open:
            raise NVLinkError("NV-Link stream not open. Call nv_open() or nv_rt_open() first.")

        try:
            # NVGets signature from gen_py: NVGets(buff, size, filename)
            # - buff: VT_VARIANT|VT_BYREF (16396, 3) - in/out ref, required
            # - size: VT_I4 (3, 1) - input integer, required
            # - filename: VT_BSTR|VT_BYREF (16392, 2) - out ref, optional
            #
            # Pass empty byte array as initial buffer value for VARIANT ref
            # The _ApplyTypes_ wrapper will handle byref conversion
            nv_result = self._nvlink.NVGets(b"", BUFFER_SIZE_NVREAD)

            # Handle result - gen_py returns (return_code, buff, filename)
            if isinstance(nv_result, tuple) and len(nv_result) >= 2:
                result = nv_result[0]
                buff_str = nv_result[1]
                # nv_result[2] is filename (str) - needed for error recovery
                filename = nv_result[2] if len(nv_result) > 2 else None
            else:
                # Unexpected return format
                raise NVLinkError(f"Unexpected NVGets return format: {type(nv_result)}, length={len(nv_result) if isinstance(nv_result, tuple) else 'N/A'}")

            # Return code meanings:
            # > 0: Success, value is data length in bytes
            # 0: Read complete (no more data)
            # -1: File switch (continue reading)
            # -203, -402, -403, -502, -503: Recoverable errors (delete file and continue)
            # < -1 (other): Fatal error
            if result > 0:
                # Successfully read data (result is data length)
                # NVGets returns Shift-JIS encoded byte array directly
                # pywin32 may represent this as:
                # - bytes: direct byte data
                # - memoryview: view of byte data (need to convert to bytes)
                # - str: string where each byte is a character
                if buff_str:
                    # Handle bytes, memoryview, and string types
                    if isinstance(buff_str, (bytes, bytearray)):
                        data_bytes = bytes(buff_str)
                    elif isinstance(buff_str, memoryview):
                        # memoryview - convert to bytes
                        data_bytes = bytes(buff_str)
                    else:
                        # Convert string to Shift-JIS bytes
                        # NVGets stores Shift-JIS bytes in a BSTR, similar to NVRead
                        # Use latin-1 encoding to extract raw bytes (1:1 mapping for 0x00-0xFF)
                        # 高速変換: 3段階のエンコード戦略
                        # 1. Latin-1（ASCII + 拡張ASCII）- 最速
                        # 2. CP932（日本語）- 高速
                        # 3. 個別処理（CP1252変換が必要な場合）- 低速だが稀
                        try:
                            data_bytes = buff_str.encode('latin-1')
                        except UnicodeEncodeError:
                            # If latin-1 fails, try cp932 encoding
                            try:
                                data_bytes = buff_str.encode('cp932')
                            except UnicodeEncodeError:
                                # Fallback: character-by-character conversion with CP1252 handling
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

                return result, data_bytes, filename

            elif result == NV_READ_SUCCESS:
                # Read complete (0)
                return result, None, filename

            elif result == NV_READ_NO_MORE_DATA:
                # File switch (-1)
                return result, None, filename

            elif result in (-203, -402, -403, -502, -503):
                # Recoverable errors - caller should delete file and continue
                # Based on kmy-keiba's JVLinkReader.cs error handling
                logger.warning("NVGets recoverable error", error_code=result, filename=filename)
                return result, None, filename

            else:
                # Fatal error (< -1, other codes)
                logger.error("NVGets failed", error_code=result, filename=filename)
                return result, None, filename

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVGets failed: {e}")

    def nv_close(self) -> int:
        """Close NV-Link data stream.

        Should be called after finishing reading data.

        Returns:
            Result code (0 = success)

        Examples:
            >>> wrapper = NVLinkWrapper("YOUR_KEY")
            >>> wrapper.nv_init()
            >>> wrapper.nv_open("RACE", "20240101", "20241231")
            >>> # ... read data ...
            >>> wrapper.nv_close()
        """
        try:
            result = int(self._nvlink.NVClose())
            self._is_open = False
            logger.info("NV-Link stream closed")
            return result
        except Exception as e:
            raise NVLinkError(f"NVClose failed: {e}")

    def nv_status(self) -> int:
        """Get NV-Link download status.

        Returns:
            Status code:
            - > 0: Download in progress (percentage 1-100)
            - 0: No download in progress (either before download starts, or after complete)
            - < 0: Error (e.g., -502 = download failure)

        Note:
            Status 0 is ambiguous - it can mean either:
            1. Download hasn't started yet (initial state)
            2. Download has completed

            To distinguish, use wait_for_download() which tracks state transitions.

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> status = wrapper.nv_status()
        """
        try:
            result = int(self._nvlink.NVStatus())
            logger.debug("NVStatus", status=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVStatus failed: {e}")

    def wait_for_download(self, timeout: float = 120.0, poll_interval: float = 0.5) -> bool:
        """Wait for download to complete after nv_open().

        This method properly handles the NVStatus return values:
        - Waits for status to become > 0 (download started)
        - Then waits for status to return to 0 (download complete)

        Args:
            timeout: Maximum time to wait in seconds (default: 120)
            poll_interval: Time between status checks in seconds (default: 0.5)

        Returns:
            True if download completed successfully, False if timeout or error

        Note:
            If nv_open() returned download_count == 0, this method returns True immediately
            since no download is needed.

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> result, read_count, download_count, ts = wrapper.nv_open("RACE", "20241201000000", 1)
            >>> if download_count > 0:
            ...     if wrapper.wait_for_download():
            ...         # Download complete, now read data
            ...         ret_code, data, fname = wrapper.nv_read()
        """
        import time

        start_time = time.time()
        download_started = False
        last_status = None

        while time.time() - start_time < timeout:
            try:
                status = self.nv_status()
            except Exception as e:
                logger.error("Error checking download status", error=str(e))
                return False

            if status != last_status:
                elapsed = time.time() - start_time
                if status > 0:
                    download_started = True
                    logger.debug("Download in progress", progress=status, elapsed=f"{elapsed:.1f}s")
                elif status == 0:
                    if download_started:
                        logger.info("Download completed", elapsed=f"{elapsed:.1f}s")
                        return True
                    # status == 0 before download started - keep waiting
                    logger.debug("Waiting for download to start", elapsed=f"{elapsed:.1f}s")
                else:
                    # Error status (< 0)
                    logger.error("Download error", status=status)
                    return False
                last_status = status

            time.sleep(poll_interval)

        logger.warning("Download timeout", timeout=timeout)
        return False

    def nv_file_delete(self, filename: str) -> int:
        """Delete a cached file from NV-Link cache.

        This method is used to handle recoverable errors (-203, -402, -403, -502, -503)
        during data reading. When these errors occur, the corrupted file should be
        deleted and the read operation retried.

        Based on kmy-keiba's JVLinkReader.cs error handling pattern:
        - -203: Setup not complete or file corruption
        - -402, -403: Database errors
        - -502, -503: File errors

        Args:
            filename: The filename to delete (as returned by NVGets/NVRead)

        Returns:
            Result code (0 = success)

        Raises:
            NVLinkError: If file deletion fails

        Examples:
            >>> wrapper = NVLinkWrapper()
            >>> wrapper.nv_init()
            >>> # During read loop, if NVGets returns -203:
            >>> ret_code, buff, filename = wrapper.nv_gets()
            >>> if ret_code == -203 and filename:
            ...     wrapper.nv_file_delete(filename)
            ...     # Continue reading
        """
        try:
            result = int(self._nvlink.NVFiledelete(filename))
            logger.info("NVFiledelete called", filename=filename, result=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVFiledelete failed: {e}")

    def is_open(self) -> bool:
        """Check if NV-Link stream is open.

        Returns:
            True if stream is open, False otherwise
        """
        return self._is_open

    def __enter__(self):
        """Context manager entry."""
        self.nv_init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._is_open:
            self.nv_close()
        # Uninitialize COM if we initialized it
        if self._com_initialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
                self._com_initialized = False
            except Exception:
                pass

    def reinitialize_com(self):
        """Reinitialize COM component to recover from catastrophic errors.

        This method should be called when encountering error -2147418113 (E_UNEXPECTED)
        or other catastrophic COM failures.
        """
        try:
            import sys
            sys.coinit_flags = 2
            
            import pythoncom
            import win32com.client
            import time

            logger.warning("Reinitializing COM component due to error...")

            # Close any open streams
            if self._is_open:
                try:
                    self.nv_close()
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

            # Recreate COM object using CLSID
            NVLINK_CLSID = "{F726BBA6-5784-4529-8C67-26E152D49D73}"
            try:
                self._nvlink = win32com.client.Dispatch("NVDTLab.NVLink")
            except Exception:
                self._nvlink = win32com.client.Dispatch(NVLINK_CLSID)
            self._is_open = False

            logger.info("COM component reinitialized successfully", sid=self.sid)

        except Exception as e:
            logger.error("Failed to reinitialize COM component", error=str(e))
            raise NVLinkError(f"COM reinitialization failed: {e}")

    def cleanup(self):
        """Explicitly cleanup COM resources. Call this before the object goes out of scope."""
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
        if hasattr(self, '_is_open') and self._is_open:
            try:
                self.nv_close()
            except Exception:
                pass

        # Release COM object reference BEFORE CoUninitialize
        # This prevents "Win32 exception occurred releasing IUnknown" warnings
        if hasattr(self, '_nvlink') and self._nvlink is not None:
            try:
                # Set to None first to break reference
                nvlink_ref = self._nvlink
                self._nvlink = None
                # Force garbage collection while COM is still initialized
                del nvlink_ref
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
        return f"<NVLinkWrapper status={status}>"

    # =========================================================================
    # JVLinkWrapper互換エイリアス（BaseFetcherでポリモーフィックに使用するため）
    # =========================================================================

    def jv_init(self) -> int:
        """Alias for nv_init() for JVLinkWrapper compatibility."""
        return self.nv_init()

    def jv_set_service_key(self, service_key: str) -> int:
        """Alias for nv_set_service_key() for JVLinkWrapper compatibility."""
        return self.nv_set_service_key(service_key)

    def jv_open(
        self,
        data_spec: str,
        fromtime: str,
        option: int = 1,
    ) -> Tuple[int, int, int, str]:
        """Alias for nv_open() for JVLinkWrapper compatibility."""
        return self.nv_open(data_spec, fromtime, option)

    def jv_rt_open(self, data_spec: str, key: str = "") -> Tuple[int, int]:
        """Alias for nv_rt_open() for JVLinkWrapper compatibility."""
        return self.nv_rt_open(data_spec, key)

    def jv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Alias for nv_read() for JVLinkWrapper compatibility."""
        return self.nv_read()

    def jv_gets(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Alias for nv_gets() for JVLinkWrapper compatibility."""
        return self.nv_gets()

    def jv_file_delete(self, filename: str) -> int:
        """Alias for nv_file_delete() for JVLinkWrapper compatibility."""
        return self.nv_file_delete(filename)

    def jv_close(self) -> int:
        """Alias for nv_close() for JVLinkWrapper compatibility."""
        return self.nv_close()

    def jv_status(self) -> int:
        """Alias for nv_status() for JVLinkWrapper compatibility."""
        return self.nv_status()

    def jv_wait_for_download(self, timeout: float = 120.0, poll_interval: float = 0.5) -> bool:
        """Alias for wait_for_download() for JVLinkWrapper compatibility."""
        return self.wait_for_download(timeout, poll_interval)
