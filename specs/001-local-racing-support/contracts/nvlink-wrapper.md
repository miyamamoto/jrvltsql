# NVLinkWrapper Contract: UmaConn API Wrapper

**Feature**: 001-local-racing-support
**Date**: 2025-12-15

## Overview

NVLinkWrapperはUmaConn COM API（NVDTLabLib.NVLink）のPythonラッパー。
JVLinkWrapperと同一インターフェースを提供。

## Class Definition

```python
class NVLinkWrapper:
    """Wrapper class for UmaConn (地方競馬DATA) COM API.

    Mirrors JVLinkWrapper interface with 'JV' -> 'NV' method naming.
    Works with 64-bit Python (same as JVLinkWrapper).

    Examples:
        >>> wrapper = NVLinkWrapper()
        >>> wrapper.nv_init()
        0
        >>> result, count, dl_count, ts = wrapper.nv_open("RACE", "20240101000000", 1)
        >>> while True:
        ...     ret_code, buff = wrapper.nv_gets()
        ...     if ret_code == 0:
        ...         break
        ...     # Process data
        >>> wrapper.nv_close()
    """
```

---

## Constructor

### `__init__(sid: str = "UNKNOWN")`

**Parameters**:
- `sid`: Session ID for NV-Link API (default: "UNKNOWN")

**Raises**:
- `NVLinkError`: If COM object creation fails

**Pre-conditions**:
- UmaConn installed (地方競馬DATA software)

**Post-conditions**:
- `self._nvlink` contains COM object
- `self._is_open` is False

---

## Methods

### `nv_init() -> int`

Initialize NVLink connection.

**Returns**: Result code (0 = success)

**Raises**: `NVLinkError` if initialization fails

**Pre-conditions**: Service key configured in registry

**Post-conditions**: API ready for open/read operations

---

### `nv_open(data_spec: str, fromtime: str, option: int = 1) -> Tuple[int, int, int, str]`

Open data stream for historical data.

**Parameters**:
- `data_spec`: Data specification code (e.g., "RACE", "DIFF")
- `fromtime`: Start time in YYYYMMDDhhmmss format
- `option`: 1=通常, 2=今週, 3=セットアップ, 4=分割セットアップ

**Returns**: Tuple of (result_code, read_count, download_count, last_file_timestamp)

**Raises**: `NVLinkError` if open fails

**Post-conditions**: `self._is_open` is True

---

### `nv_rt_open(data_spec: str, key: str = "") -> Tuple[int, int]`

Open data stream for real-time data.

**Parameters**:
- `data_spec`: Real-time data specification
- `key`: Key parameter

**Returns**: Tuple of (result_code, read_count)

**Raises**: `NVLinkError` if open fails

---

### `nv_read() -> Tuple[int, Optional[bytes], Optional[str]]`

Read one record from data stream.

**Returns**: Tuple of (return_code, buffer, filename)
- `return_code > 0`: Success with data length
- `return_code == 0`: Read complete
- `return_code == -1`: File switch
- `return_code < -1`: Error

**Raises**: `NVLinkError` if stream not open

**Pre-conditions**: `nv_open()` or `nv_rt_open()` called

---

### `nv_gets() -> Tuple[int, Optional[bytes]]`

Read one record using fast method.

**Returns**: Tuple of (return_code, buffer)

**Raises**: `NVLinkError` if stream not open

**Note**: Faster than `nv_read()`, recommended for batch processing

---

### `nv_close() -> int`

Close data stream.

**Returns**: Result code (0 = success)

**Post-conditions**: `self._is_open` is False

---

### `nv_status() -> int`

Get NVLink status.

**Returns**: Status code

---

### `is_open() -> bool`

Check if stream is open.

**Returns**: True if stream is open

---

## Error Codes

Same as JV-Link error codes:

| Code | Meaning |
|------|---------|
| 0 | 成功 |
| -1 | データなし |
| -2 | エラー |
| -100 | サービスキー未設定 |
| -101 | サービスキー無効 |
| -102 | サービスキー期限切れ |
| -111 | 契約外データ種別 |
| -114 | 契約外データ種別（警告） |

---

## NVLinkError

```python
class NVLinkError(Exception):
    """NV-Link (UmaConn) related error.

    Attributes:
        error_code: Optional NV-Link error code
    """

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        if error_code is not None:
            message = f"{message} (code: {error_code}, {get_error_message(error_code)})"
        super().__init__(message)
```

---

## Usage Example

```python
from src.nvlink.wrapper import NVLinkWrapper, NVLinkError
from src.nvlink.constants import NV_READ_SUCCESS, NV_READ_NO_MORE_DATA

try:
    with NVLinkWrapper() as wrapper:
        result, read_count, dl_count, ts = wrapper.nv_open("RACE", "20240101000000", 1)

        while True:
            ret_code, buff = wrapper.nv_gets()

            if ret_code == NV_READ_SUCCESS:
                break  # Complete
            elif ret_code == NV_READ_NO_MORE_DATA:
                continue  # File switch
            elif ret_code < -1:
                raise NVLinkError("Read error", ret_code)
            else:
                # Process data
                data = buff.decode('cp932')
                record_type = data[:2]
                # ... parse and store

except NVLinkError as e:
    if e.error_code == -100:
        print("サービスキーを設定してください")
    else:
        print(f"エラー: {e}")
```

---

## Comparison with JVLinkWrapper

| JVLinkWrapper | NVLinkWrapper | Notes |
|---------------|---------------|-------|
| `jv_init()` | `nv_init()` | Same behavior |
| `jv_open()` | `nv_open()` | Same behavior |
| `jv_rt_open()` | `nv_rt_open()` | Same behavior |
| `jv_read()` | `nv_read()` | Same behavior |
| `jv_gets()` | `nv_gets()` | Same behavior |
| `jv_close()` | `nv_close()` | Same behavior |
| `JVLinkError` | `NVLinkError` | Same structure |

The interface is intentionally identical to allow polymorphic usage.
