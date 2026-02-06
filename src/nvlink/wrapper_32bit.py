"""NV-Link COM API Wrapper - Optimized for 32-bit Python.

This module provides a Python wrapper for the NV-Link COM API,
optimized specifically for 32-bit Python environments where direct
COM object access is available without DllSurrogate.

Key optimizations for 32-bit:
- Removed DllSurrogate/COM apartment threading setup (not needed)
- Simplified COM initialization (direct dispatch)
- Streamlined error handling
- Maintained full compatibility with BaseFetcher interface
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
# Moved to module level for performance
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
    """Wrapper class for NV-Link COM API - 32-bit Python optimized.

    This version is optimized for 32-bit Python where direct COM object
    access is available without DllSurrogate configuration.

    Important:
        - Requires 32-bit Python (py.exe -3-32)
        - Service key must be configured in UmaConn application
        - NV-Link service must be running on Windows

    Examples:
        >>> wrapper = NVLinkWrapper()  # Uses default sid="UNKNOWN"
        >>> wrapper.nv_init()
        0
        >>> result, count, dl, ts = wrapper.nv_open("RACE", "20240101000000", 1)
        >>> while True:
        ...     ret_code, buff = wrapper.nv_gets()
        ...     if ret_code == NV_READ_SUCCESS:
        ...         break
        ...     elif ret_code == NV_READ_NO_MORE_DATA:
        ...         continue
        ...     elif ret_code > 0:
        ...         # Process data (ret_code is data length)
        ...         data = buff.decode('cp932')
        >>> wrapper.nv_close()
    """

    def __init__(self, sid: str = "UNKNOWN", initialization_key: Optional[str] = None):
        """Initialize NVLinkWrapper for 32-bit Python.

        Args:
            sid: Session ID for NV-Link API (default: "UNKNOWN")
            initialization_key: Optional NV-Link initialization key (software ID)
                used for NVInit. If provided, this value is used instead of sid.

        Raises:
            NVLinkError: If COM object creation fails
        """
        self.sid = sid
        self.initialization_key = initialization_key
        self._nvlink = None
        self._is_open = False

        try:
            import win32com.client
            import win32com.client.dynamic

            # 32-bit Python: Direct COM object creation (no DllSurrogate needed)
            # Use dynamic dispatch (late binding) to avoid gen_py cache issues
            self._nvlink = win32com.client.dynamic.Dispatch("NVDTLabLib.NVLink")
            logger.info("NV-Link COM object created (32-bit direct)", sid=sid)
        except Exception as e:
            raise NVLinkError(
                f"UmaConn (地方競馬DATA) がインストールされていません。"
                f"32-bit環境でNVDTLab.dllにアクセスできません。詳細: {e}"
            )

    def nv_set_service_key(self, service_key: str) -> int:
        """Set NV-Link service key via Windows registry.

        Args:
            service_key: NV-Link service key (format: XXXX-XXXX-XXXX-XXXX-X)

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            NVLinkError: If service key setting fails
        """
        try:
            import subprocess
            import time

            # Set service key in Windows registry
            reg_key = r"HKLM\SOFTWARE\NAR\NVDTLabLib"
            result = subprocess.run(
                ['reg', 'add', reg_key, '/v', 'ServiceKey', '/t', 'REG_SZ', '/d', service_key, '/f'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info("Service key set successfully via registry")
                time.sleep(0.5)
                return NV_RT_SUCCESS
            else:
                logger.error("Failed to set service key in registry", error=result.stderr)
                raise NVLinkError(f"Failed to set service key in registry: {result.stderr}")
        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVSetServiceKey failed: {e}")

    def nv_init(self) -> int:
        """Initialize NV-Link.

        Returns:
            Result code (0 = success, non-zero = error)

        Raises:
            NVLinkError: If initialization fails
        """
        try:
            init_key = self.initialization_key or self.sid
            result = self._nvlink.NVInit(init_key)
            if result == NV_RT_SUCCESS:
                logger.info(
                    "NV-Link initialized successfully",
                    sid=self.sid,
                    init_key=init_key if init_key != self.sid else None,
                )
            else:
                if result == -100:
                    error_msg = "地方競馬DATAのサービスキーが設定されていません。"
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
            fromtime: Start time in YYYYMMDDhhmmss format
            option: Option flag (1=通常, 2=今週, 3=セットアップ, 4=分割セットアップ)

        Returns:
            Tuple of (result_code, read_count, download_count, last_file_timestamp)

        Raises:
            NVLinkError: If open operation fails
        """
        try:
            nv_result = self._nvlink.NVOpen(data_spec, fromtime, option)

            if isinstance(nv_result, tuple):
                if len(nv_result) == 4:
                    result, read_count, download_count, last_file_timestamp = nv_result
                else:
                    raise ValueError(f"Unexpected NVOpen return tuple length: {len(nv_result)}")
            else:
                raise ValueError(f"Unexpected NVOpen return type: {type(nv_result)}")

            # Handle download in progress
            if result == -301 or result == -302:
                self._is_open = True
                if download_count == 0:
                    download_count = 1
                logger.info(
                    "NVOpen: Download pending",
                    data_spec=data_spec,
                    status_code=result,
                )
                return result, read_count, download_count, last_file_timestamp

            # Handle errors
            if result < -2:
                if result == -111 or result == -114:
                    error_msg = "このデータ種別は契約に含まれていません。"
                else:
                    error_msg = "NVOpen failed"
                logger.error(error_msg, error_code=result)
                raise NVLinkError(error_msg, error_code=result)
            elif result in (-1, -2):
                logger.info("NVOpen: No data available", result_code=result)

            self._is_open = True
            logger.info(
                "NVOpen successful",
                data_spec=data_spec,
                read_count=read_count,
                download_count=download_count,
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
        """
        try:
            nv_result = self._nvlink.NVRTOpen(data_spec, key)

            if isinstance(nv_result, tuple):
                result, read_count = nv_result
            else:
                if nv_result < 0:
                    result = nv_result
                    read_count = 0
                else:
                    result = NV_RT_SUCCESS
                    read_count = nv_result

            if result < 0:
                if result == -1:
                    logger.debug("NVRTOpen: no data available", error_code=result)
                    return result, read_count
                elif result == -111 or result == -114:
                    logger.debug("NVRTOpen: data spec not subscribed", error_code=result)
                    return result, read_count
                else:
                    logger.error("NVRTOpen failed", error_code=result)
                    raise NVLinkError("NVRTOpen failed", error_code=result)

            self._is_open = True
            logger.info("NVRTOpen successful", data_spec=data_spec, read_count=read_count)
            return result, read_count

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVRTOpen failed: {e}")

    def nv_read(self) -> Tuple[int, Optional[bytes], Optional[str]]:
        """Read one record from NV-Link data stream using NVRead.

        Returns:
            Tuple of (return_code, buffer, filename)
            - return_code: >0=data length, 0=complete, -1=file switch, <-1=error
            - buffer: Data buffer (bytes) if success, None otherwise
            - filename: Filename if applicable, None otherwise

        Raises:
            NVLinkError: If read operation fails
        """
        if not self._is_open:
            raise NVLinkError("NV-Link stream not open. Call nv_open() or nv_rt_open() first.")

        try:
            # 32-bit Python: Direct call with proper parameter types
            nv_result = self._nvlink.NVRead("", BUFFER_SIZE_NVREAD, "")

            if isinstance(nv_result, tuple) and len(nv_result) >= 4:
                result = nv_result[0]
                buff_str = nv_result[1]
                filename_str = nv_result[3]
            else:
                raise NVLinkError(f"Unexpected NVRead return format: {type(nv_result)}")

            if result > 0:
                # Successfully read data
                if buff_str:
                    data_bytes = self._convert_com_string_to_bytes(buff_str)
                else:
                    data_bytes = b""
                return result, data_bytes, filename_str

            elif result == NV_READ_SUCCESS:
                return result, None, None

            elif result == NV_READ_NO_MORE_DATA:
                return result, None, None

            else:
                logger.error("NVRead failed", error_code=result)
                raise NVLinkError("NVRead failed", error_code=result)

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVRead failed: {e}")

    def nv_gets(self) -> Tuple[int, Optional[bytes]]:
        """Read one record from NV-Link data stream using NVGets (faster).

        NVGets returns data directly as bytes, which is faster than NVRead.

        Returns:
            Tuple of (return_code, buffer)
            - return_code: >0=data length, 0=complete, -1=file switch, <-1=error
            - buffer: Shift-JIS encoded data buffer (bytes) if success, None otherwise

        Raises:
            NVLinkError: If read operation fails
        """
        if not self._is_open:
            raise NVLinkError("NV-Link stream not open. Call nv_open() or nv_rt_open() first.")

        try:
            # 32-bit Python: Direct call with proper parameter types
            nv_result = self._nvlink.NVGets("", BUFFER_SIZE_NVREAD)

            if isinstance(nv_result, tuple) and len(nv_result) >= 2:
                result = nv_result[0]
                buff_str = nv_result[1]
            else:
                raise NVLinkError(f"Unexpected NVGets return format: {type(nv_result)}")

            if result > 0:
                # Successfully read data
                if buff_str:
                    data_bytes = self._convert_com_string_to_bytes(buff_str)
                else:
                    data_bytes = b""
                return result, data_bytes

            elif result == NV_READ_SUCCESS:
                return result, None

            elif result == NV_READ_NO_MORE_DATA:
                return result, None

            else:
                logger.error("NVGets failed", error_code=result)
                raise NVLinkError("NVGets failed", error_code=result)

        except Exception as e:
            if isinstance(e, NVLinkError):
                raise
            raise NVLinkError(f"NVGets failed: {e}")

    def _convert_com_string_to_bytes(self, buff_str: str) -> bytes:
        """Convert COM BSTR string to Shift-JIS bytes.

        NV-Link COM returns Shift-JIS encoded data in a BSTR.
        This method handles the conversion efficiently.

        Args:
            buff_str: String from COM API

        Returns:
            Shift-JIS encoded bytes
        """
        # Fast path: Try latin-1 first (handles most cases)
        try:
            return buff_str.encode('latin-1')
        except UnicodeEncodeError:
            # Medium path: Try cp932 (Japanese)
            try:
                return buff_str.encode('cp932')
            except UnicodeEncodeError:
                # Slow path: Character-by-character conversion with CP1252 handling
                result_bytes = bytearray()
                for c in buff_str:
                    cp = ord(c)
                    if cp <= 0xFF:
                        result_bytes.append(cp)
                    elif cp in CP1252_TO_BYTE:
                        result_bytes.append(CP1252_TO_BYTE[cp])
                    elif cp == 0xFFFD:
                        result_bytes.append(0x30)  # '0'
                    else:
                        try:
                            result_bytes.extend(c.encode('cp932'))
                        except UnicodeEncodeError:
                            result_bytes.append(0x3F)  # '?'
                return bytes(result_bytes)

    def nv_close(self) -> int:
        """Close NV-Link data stream.

        Returns:
            Result code (0 = success)
        """
        try:
            result = self._nvlink.NVClose()
            self._is_open = False
            logger.info("NV-Link stream closed")
            return result
        except Exception as e:
            raise NVLinkError(f"NVClose failed: {e}")

    def nv_status(self) -> int:
        """Get NV-Link status.

        Returns:
            Status code
        """
        try:
            result = self._nvlink.NVStatus()
            logger.debug("NVStatus", status=result)
            return result
        except Exception as e:
            raise NVLinkError(f"NVStatus failed: {e}")

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
        # Release COM object reference to prevent memory leaks
        if hasattr(self, '_nvlink') and self._nvlink is not None:
            try:
                del self._nvlink
                self._nvlink = None
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
                del self._nvlink
                self._nvlink = None
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

    def __repr__(self) -> str:
        """String representation."""
        status = "open" if self._is_open else "closed"
        return f"<NVLinkWrapper(32-bit) status={status}>"

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

    def jv_gets(self) -> Tuple[int, Optional[bytes]]:
        """Alias for nv_gets() for JVLinkWrapper compatibility."""
        return self.nv_gets()

    def jv_close(self) -> int:
        """Alias for nv_close() for JVLinkWrapper compatibility."""
        return self.nv_close()

    def jv_status(self) -> int:
        """Alias for nv_status() for JVLinkWrapper compatibility."""
        return self.nv_status()
