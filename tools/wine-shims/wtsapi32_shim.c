// Minimal WTSAPI32 shim for Wine/JV-Link.
//
// Wine 8's builtin WTSAPI32 session enumeration is a stub.  JVDTLab.dll calls
// it during JVInit and may dereference the returned session pointer.  This shim
// returns a single active Console session so old JV-Link code can proceed.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wtsapi32.h>

static char g_console_a[] = "Console";
static wchar_t g_console_w[] = L"Console";

HANDLE WINAPI WTSOpenServerA(LPSTR pServerName) {
    (void)pServerName;
    return (HANDLE)1;
}

HANDLE WINAPI WTSOpenServerW(LPWSTR pServerName) {
    (void)pServerName;
    return (HANDLE)1;
}

VOID WINAPI WTSCloseServer(HANDLE hServer) {
    (void)hServer;
}

BOOL WINAPI WTSEnumerateSessionsA(
    HANDLE hServer,
    DWORD Reserved,
    DWORD Version,
    PWTS_SESSION_INFOA *ppSessionInfo,
    DWORD *pCount
) {
    (void)hServer;
    (void)Reserved;
    (void)Version;
    if (!ppSessionInfo || !pCount) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    PWTS_SESSION_INFOA info = (PWTS_SESSION_INFOA)LocalAlloc(LMEM_FIXED | LMEM_ZEROINIT, sizeof(WTS_SESSION_INFOA));
    if (!info) {
        SetLastError(ERROR_OUTOFMEMORY);
        return FALSE;
    }
    info[0].SessionId = 0;
    info[0].pWinStationName = g_console_a;
    info[0].State = WTSActive;
    *ppSessionInfo = info;
    *pCount = 1;
    return TRUE;
}

BOOL WINAPI WTSEnumerateSessionsW(
    HANDLE hServer,
    DWORD Reserved,
    DWORD Version,
    PWTS_SESSION_INFOW *ppSessionInfo,
    DWORD *pCount
) {
    (void)hServer;
    (void)Reserved;
    (void)Version;
    if (!ppSessionInfo || !pCount) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    PWTS_SESSION_INFOW info = (PWTS_SESSION_INFOW)LocalAlloc(LMEM_FIXED | LMEM_ZEROINIT, sizeof(WTS_SESSION_INFOW));
    if (!info) {
        SetLastError(ERROR_OUTOFMEMORY);
        return FALSE;
    }
    info[0].SessionId = 0;
    info[0].pWinStationName = g_console_w;
    info[0].State = WTSActive;
    *ppSessionInfo = info;
    *pCount = 1;
    return TRUE;
}

VOID WINAPI WTSFreeMemory(PVOID pMemory) {
    if (pMemory) {
        LocalFree((HLOCAL)pMemory);
    }
}

DWORD WINAPI WTSGetActiveConsoleSessionId(void) {
    return 0;
}

BOOL WINAPI WTSQuerySessionInformationA(
    HANDLE hServer,
    DWORD SessionId,
    WTS_INFO_CLASS WTSInfoClass,
    LPSTR *ppBuffer,
    DWORD *pBytesReturned
) {
    (void)hServer;
    (void)SessionId;
    if (!ppBuffer || !pBytesReturned) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    if (WTSInfoClass == WTSWinStationName) {
        size_t len = lstrlenA(g_console_a) + 1;
        char *buffer = (char *)LocalAlloc(LMEM_FIXED, len);
        if (!buffer) {
            SetLastError(ERROR_OUTOFMEMORY);
            return FALSE;
        }
        CopyMemory(buffer, g_console_a, len);
        *ppBuffer = buffer;
        *pBytesReturned = (DWORD)len;
        return TRUE;
    }
    *ppBuffer = NULL;
    *pBytesReturned = 0;
    SetLastError(ERROR_NOT_SUPPORTED);
    return FALSE;
}

BOOL WINAPI WTSQuerySessionInformationW(
    HANDLE hServer,
    DWORD SessionId,
    WTS_INFO_CLASS WTSInfoClass,
    LPWSTR *ppBuffer,
    DWORD *pBytesReturned
) {
    (void)hServer;
    (void)SessionId;
    if (!ppBuffer || !pBytesReturned) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    if (WTSInfoClass == WTSWinStationName) {
        size_t len = (lstrlenW(g_console_w) + 1) * sizeof(wchar_t);
        wchar_t *buffer = (wchar_t *)LocalAlloc(LMEM_FIXED, len);
        if (!buffer) {
            SetLastError(ERROR_OUTOFMEMORY);
            return FALSE;
        }
        CopyMemory(buffer, g_console_w, len);
        *ppBuffer = buffer;
        *pBytesReturned = (DWORD)len;
        return TRUE;
    }
    *ppBuffer = NULL;
    *pBytesReturned = 0;
    SetLastError(ERROR_NOT_SUPPORTED);
    return FALSE;
}
