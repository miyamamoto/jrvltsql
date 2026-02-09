"""NV-Link (UmaConn) module for 地方競馬DATA.

This module provides Python wrappers for the UmaConn COM API,
which is used to access 地方競馬DATA (NAR - National Association of Racing).

The API mirrors JV-Link with 'JV' -> 'NV' naming convention.
"""

from src.nvlink.constants import (
    # Return codes
    NV_RT_SUCCESS,
    NV_RT_ERROR,
    NV_RT_NO_MORE_DATA,
    NV_RT_SERVICE_KEY_NOT_SET,
    NV_RT_SERVICE_KEY_INVALID,
    NV_RT_SERVICE_KEY_EXPIRED,
    NV_RT_UNSUBSCRIBED_DATA,
    NV_RT_UNSUBSCRIBED_DATA_WARNING,
    # Read codes
    NV_READ_SUCCESS,
    NV_READ_NO_MORE_DATA,
    NV_READ_ERROR,
    # Track codes
    NAR_JYO_CODES,
    NAR_ACTIVE_TRACKS,
    # Encoding/Buffer
    ENCODING_NVDATA,
    BUFFER_SIZE_NVREAD,
    # Helper functions
    get_error_message,
    get_nar_track_name,
    is_active_nar_track,
)

from src.nvlink.wrapper import (
    NVLinkWrapper,
    NVLinkError,
    COMBrokenError,
)

from src.nvlink.bridge import (
    NVLinkBridge,
    NVLinkBridgeError,
    find_bridge_executable,
)

__all__ = [
    # Main classes
    "NVLinkWrapper",
    "NVLinkBridge",
    "NVLinkError",
    "NVLinkBridgeError",
    # Return codes
    "NV_RT_SUCCESS",
    "NV_RT_ERROR",
    "NV_RT_NO_MORE_DATA",
    "NV_RT_SERVICE_KEY_NOT_SET",
    "NV_RT_SERVICE_KEY_INVALID",
    "NV_RT_SERVICE_KEY_EXPIRED",
    "NV_RT_UNSUBSCRIBED_DATA",
    "NV_RT_UNSUBSCRIBED_DATA_WARNING",
    # Read codes
    "NV_READ_SUCCESS",
    "NV_READ_NO_MORE_DATA",
    "NV_READ_ERROR",
    # Track codes
    "NAR_JYO_CODES",
    "NAR_ACTIVE_TRACKS",
    # Encoding/Buffer
    "ENCODING_NVDATA",
    "BUFFER_SIZE_NVREAD",
    # Helper functions
    "get_error_message",
    "get_nar_track_name",
    "is_active_nar_track",
]
