// JVLinkBridge Native - C-based COM host for JV-Link ActiveX control
// Compiles with MinGW: i686-w64-mingw32-gcc -o JVLinkBridge.exe bridge_native.c -lole32 -loleaut32 -luuid
// Provides JSON protocol over stdin/stdout for communication with Python

#define _WIN32_WINNT 0x0501
#define COBJMACROS
#include <windows.h>
#include <ole2.h>
#include <oleauto.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// JVLink ProgID and CLSID
static const CLSID CLSID_JVLink = {0x2AB1774D, 0x0C41, 0x11D7, {0x91, 0x6F, 0x00, 0x03, 0x47, 0x9B, 0xEB, 0x3F}};
static IDispatch* g_jvlink = NULL;
static int g_is_open = 0;

// Helper: Get DISPID for a method name
static HRESULT GetDispId(IDispatch* disp, const wchar_t* name, DISPID* id) {
    return IDispatch_GetIDsOfNames(disp, &IID_NULL, (LPOLESTR*)&name, 1, LOCALE_USER_DEFAULT, id);
}

static HRESULT EnsureJVLink(void) {
    if (g_jvlink) return S_OK;
    return CoCreateInstance(&CLSID_JVLink, NULL, CLSCTX_INPROC_SERVER,
                            &IID_IDispatch, (void**)&g_jvlink);
}

// Helper: Call a method with a single string argument, return int result
static int CallMethodStr(IDispatch* disp, const wchar_t* method, const char* arg) {
    DISPID id;
    if (FAILED(GetDispId(disp, method, &id))) return -9999;

    BSTR bstr = NULL;
    if (arg) {
        int wlen = MultiByteToWideChar(CP_ACP, 0, arg, -1, NULL, 0);
        wchar_t* warg = (wchar_t*)malloc(wlen * sizeof(wchar_t));
        MultiByteToWideChar(CP_ACP, 0, arg, -1, warg, wlen);
        bstr = SysAllocString(warg);
        free(warg);
    }

    DISPPARAMS params = {0};
    VARIANTARG varg;
    VariantInit(&varg);
    V_VT(&varg) = VT_BSTR;
    V_BSTR(&varg) = bstr;
    params.rgvarg = &varg;
    params.cArgs = 1;

    VARIANT result;
    VariantInit(&result);
    EXCEPINFO excep = {0};

    HRESULT hr = IDispatch_Invoke(disp, id, &IID_NULL, LOCALE_USER_DEFAULT,
                                   DISPATCH_METHOD, &params, &result, &excep, NULL);

    SysFreeString(bstr);

    if (FAILED(hr)) return -9998;
    if (V_VT(&result) == VT_I4) return V_I4(&result);
    if (V_VT(&result) == VT_I2) return V_I2(&result);
    return 0;
}

// Helper: Call a method with two string arguments, return int result
static int CallMethodStrStr(IDispatch* disp, const wchar_t* method, const char* arg1, const char* arg2) {
    DISPID id;
    if (FAILED(GetDispId(disp, method, &id))) return -9999;

    wchar_t wbuf1[512];
    wchar_t wbuf2[512];
    MultiByteToWideChar(CP_ACP, 0, arg1 ? arg1 : "", -1, wbuf1, 512);
    MultiByteToWideChar(CP_ACP, 0, arg2 ? arg2 : "", -1, wbuf2, 512);

    BSTR bArg1 = SysAllocString(wbuf1);
    BSTR bArg2 = SysAllocString(wbuf2);

    VARIANTARG args[2];
    DISPPARAMS params = {args, NULL, 2, 0};

    // Args are in reverse order for IDispatch
    VariantInit(&args[1]); V_VT(&args[1]) = VT_BSTR; V_BSTR(&args[1]) = bArg1;
    VariantInit(&args[0]); V_VT(&args[0]) = VT_BSTR; V_BSTR(&args[0]) = bArg2;

    VARIANT result;
    VariantInit(&result);
    EXCEPINFO excep = {0};

    HRESULT hr = IDispatch_Invoke(disp, id, &IID_NULL, LOCALE_USER_DEFAULT,
                                   DISPATCH_METHOD, &params, &result, &excep, NULL);

    SysFreeString(bArg1);
    SysFreeString(bArg2);

    if (FAILED(hr)) return -9998;
    if (V_VT(&result) == VT_I4) return V_I4(&result);
    if (V_VT(&result) == VT_I2) return V_I2(&result);
    return 0;
}

// Call JVOpen: JVOpen(dataspec, fromtime, option, ref readcount, ref downloadcount, ref lastfiletimestamp)
static int CallJVOpen(const char* dataspec, const char* fromtime, int option,
                       int* readcount, int* downloadcount, char* lastts, int lastts_size) {
    DISPID id;
    if (FAILED(GetDispId(g_jvlink, L"JVOpen", &id))) return -9999;

    // Convert strings to BSTR
    wchar_t wbuf[512];
    
    MultiByteToWideChar(CP_ACP, 0, dataspec, -1, wbuf, 512);
    BSTR bDataspec = SysAllocString(wbuf);
    
    MultiByteToWideChar(CP_ACP, 0, fromtime, -1, wbuf, 512);
    BSTR bFromtime = SysAllocString(wbuf);

    // JVOpen args: dataspec, fromtime, option, readcount, downloadcount, lastfiletimestamp
    VARIANTARG args[6];
    DISPPARAMS params = {args, NULL, 6, 0};

    // Args are in reverse order for IDispatch
    VariantInit(&args[5]); V_VT(&args[5]) = VT_BSTR; V_BSTR(&args[5]) = bDataspec;
    VariantInit(&args[4]); V_VT(&args[4]) = VT_BSTR; V_BSTR(&args[4]) = bFromtime;
    VariantInit(&args[3]); V_VT(&args[3]) = VT_I4; V_I4(&args[3]) = option;
    
    long rc = 0, dc = 0;
    BSTR bLastts = SysAllocString(L"");
    VariantInit(&args[2]); V_VT(&args[2]) = VT_I4 | VT_BYREF; V_I4REF(&args[2]) = &rc;
    VariantInit(&args[1]); V_VT(&args[1]) = VT_I4 | VT_BYREF; V_I4REF(&args[1]) = &dc;
    VariantInit(&args[0]); V_VT(&args[0]) = VT_BSTR | VT_BYREF; V_BSTRREF(&args[0]) = &bLastts;

    VARIANT result;
    VariantInit(&result);
    EXCEPINFO excep = {0};

    HRESULT hr = IDispatch_Invoke(g_jvlink, id, &IID_NULL, LOCALE_USER_DEFAULT,
                                   DISPATCH_METHOD, &params, &result, &excep, NULL);

    *readcount = (int)rc;
    *downloadcount = (int)dc;

    if (bLastts) {
        WideCharToMultiByte(CP_ACP, 0, bLastts, -1, lastts, lastts_size, NULL, NULL);
        SysFreeString(bLastts);
    }

    SysFreeString(bDataspec);
    SysFreeString(bFromtime);

    if (FAILED(hr)) return -9998;
    if (V_VT(&result) == VT_I4) return V_I4(&result);
    return 0;
}

// Call JVRead: int JVRead(ref string buff, int size, ref string filename)
static int CallJVRead(char* buff, int buff_size, char* filename, int fn_size) {
    DISPID id;
    if (FAILED(GetDispId(g_jvlink, L"JVRead", &id))) return -9999;

    BSTR bBuff = SysAllocString(L"");
    long lSize = (long)buff_size;
    BSTR bFilename = SysAllocString(L"");

    VARIANTARG args[3];
    DISPPARAMS params = {args, NULL, 3, 0};

    VariantInit(&args[2]); V_VT(&args[2]) = VT_BSTR | VT_BYREF; V_BSTRREF(&args[2]) = &bBuff;
    VariantInit(&args[1]); V_VT(&args[1]) = VT_I4; V_I4(&args[1]) = lSize;
    VariantInit(&args[0]); V_VT(&args[0]) = VT_BSTR | VT_BYREF; V_BSTRREF(&args[0]) = &bFilename;

    VARIANT result;
    VariantInit(&result);
    EXCEPINFO excep = {0};

    HRESULT hr = IDispatch_Invoke(g_jvlink, id, &IID_NULL, LOCALE_USER_DEFAULT,
                                   DISPATCH_METHOD, &params, &result, &excep, NULL);

    if (bBuff) {
        WideCharToMultiByte(932, 0, bBuff, -1, buff, buff_size, NULL, NULL);
        SysFreeString(bBuff);
    }
    if (bFilename) {
        WideCharToMultiByte(CP_ACP, 0, bFilename, -1, filename, fn_size, NULL, NULL);
        SysFreeString(bFilename);
    }

    if (FAILED(hr)) return -9998;
    if (V_VT(&result) == VT_I4) return V_I4(&result);
    return 0;
}

// Call JVClose
static void CallJVClose(void) {
    DISPID id;
    if (FAILED(GetDispId(g_jvlink, L"JVClose", &id))) return;

    DISPPARAMS params = {NULL, NULL, 0, 0};
    VARIANT result;
    VariantInit(&result);
    IDispatch_Invoke(g_jvlink, id, &IID_NULL, LOCALE_USER_DEFAULT,
                     DISPATCH_METHOD, &params, &result, NULL, NULL);
}

// Simple JSON output helpers
static void json_response(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
    fflush(stdout);
}

// Base64 encoding
static const char b64chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static char* base64_encode(const unsigned char* data, int len) {
    int olen = 4 * ((len + 2) / 3);
    char* out = (char*)malloc(olen + 1);
    if (!out) return NULL;
    int i, j;
    for (i = 0, j = 0; i < len;) {
        unsigned int a = i < len ? data[i++] : 0;
        unsigned int b = i < len ? data[i++] : 0;
        unsigned int c = i < len ? data[i++] : 0;
        unsigned int triple = (a << 16) | (b << 8) | c;
        out[j++] = b64chars[(triple >> 18) & 0x3F];
        out[j++] = b64chars[(triple >> 12) & 0x3F];
        out[j++] = b64chars[(triple >> 6) & 0x3F];
        out[j++] = b64chars[triple & 0x3F];
    }
    // Padding
    int mod = len % 3;
    if (mod == 1) { out[olen-1] = '='; out[olen-2] = '='; }
    else if (mod == 2) { out[olen-1] = '='; }
    out[olen] = '\0';
    return out;
}

// Parse simple JSON value (handles optional whitespace after colon)
static char* json_get_string(const char* json, const char* key) {
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);
    char* p = strstr(json, search);
    if (!p) return NULL;
    p += strlen(search);
    // Skip optional whitespace and colon
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') return NULL;
    p++;
    while (*p == ' ' || *p == '\t') p++;
    if (*p != '"') return NULL;
    p++;
    char* end = strchr(p, '"');
    if (!end) return NULL;
    int len = (int)(end - p);
    char* val = (char*)malloc(len + 1);
    memcpy(val, p, len);
    val[len] = '\0';
    return val;
}

static int json_get_int(const char* json, const char* key, int defval) {
    char search[256];
    snprintf(search, sizeof(search), "\"%s\"", key);
    char* p = strstr(json, search);
    if (!p) return defval;
    p += strlen(search);
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') return defval;
    p++;
    while (*p == ' ' || *p == '\t') p++;
    return atoi(p);
}

// Window procedure (for message pump)
static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    return DefWindowProcW(hwnd, msg, wp, lp);
}

int main(int argc, char* argv[]) {
    (void)argc;
    (void)argv;

    // Initialize COM (STA for ActiveX)
    CoInitialize(NULL);
    OleInitialize(NULL);

    // Create a hidden window (needed for COM message pump and as container)
    WNDCLASSW wc = {0};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.lpszClassName = L"JVLinkBridgeWnd";
    RegisterClassW(&wc);

    HWND hwnd = CreateWindowW(L"JVLinkBridgeWnd", L"JVLinkBridge", 0,
                               0, 0, 1, 1, NULL, NULL, wc.hInstance, NULL);

    // Output ready message
    json_response("{\"status\":\"ready\",\"version\":\"c-1.0\",\"pid\":%d}", GetCurrentProcessId());

    // Main command loop
    char line[65536];
    while (fgets(line, sizeof(line), stdin)) {
        // Trim newline
        int len = (int)strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) line[--len] = '\0';
        if (len == 0) continue;

        // Parse command
        char* cmd = json_get_string(line, "cmd");
        if (!cmd) { json_response("{\"status\":\"error\",\"error\":\"no cmd\"}"); continue; }

        // Process messages (COM needs message pump)
        MSG msg;
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }

        if (strcmp(cmd, "init") == 0) {
            char* key = json_get_string(line, "key");
            HRESULT hr = EnsureJVLink();
            if (FAILED(hr) || !g_jvlink) {
                json_response("{\"status\":\"error\",\"error\":\"CoCreateInstance failed\",\"hr\":\"0x%08X\"}", (unsigned)hr);
                free(key); free(cmd); continue;
            }
            // Call JVInit
            int code = CallMethodStr(g_jvlink, L"JVInit", key ? key : "");
            json_response("{\"status\":\"%s\",\"code\":%d}", code == 0 ? "ok" : "error", code);
            free(key);
        }
        else if (strcmp(cmd, "setservicekey") == 0) {
            HRESULT hr = EnsureJVLink();
            if (FAILED(hr) || !g_jvlink) {
                json_response("{\"status\":\"error\",\"error\":\"CoCreateInstance failed\",\"hr\":\"0x%08X\"}", (unsigned)hr);
                free(cmd); continue;
            }
            char* skey = json_get_string(line, "servicekey");
            int code = CallMethodStr(g_jvlink, L"JVSetServiceKey", skey ? skey : "");
            json_response("{\"status\":\"%s\",\"code\":%d}", code == 0 ? "ok" : "error", code);
            free(skey);
        }
        else if (strcmp(cmd, "setsavepath") == 0) {
            HRESULT hr = EnsureJVLink();
            if (FAILED(hr) || !g_jvlink) {
                json_response("{\"status\":\"error\",\"error\":\"CoCreateInstance failed\",\"hr\":\"0x%08X\"}", (unsigned)hr);
                free(cmd); continue;
            }
            char* spath = json_get_string(line, "path");
            int code = CallMethodStr(g_jvlink, L"JVSetSavePath", spath ? spath : "C:\\JV-Data\\");
            json_response("{\"status\":\"%s\",\"code\":%d}", code == 0 ? "ok" : "error", code);
            free(spath);
        }
        else if (strcmp(cmd, "open") == 0) {
            if (!g_jvlink) { json_response("{\"status\":\"error\",\"error\":\"not init\"}"); free(cmd); continue; }
            char* dataspec = json_get_string(line, "dataspec");
            char* fromtime = json_get_string(line, "fromtime");
            int option = json_get_int(line, "option", 1);
            int readcount = 0, downloadcount = 0;
            char lastts[64] = "";
            int code = CallJVOpen(dataspec ? dataspec : "", fromtime ? fromtime : "",
                                   option, &readcount, &downloadcount, lastts, sizeof(lastts));
            if (code >= -2) g_is_open = 1;
            json_response("{\"status\":\"%s\",\"code\":%d,\"readcount\":%d,\"downloadcount\":%d,\"lastfiletimestamp\":\"%s\"}",
                         code >= -2 ? "ok" : "error", code, readcount, downloadcount, lastts);
            free(dataspec); free(fromtime);
        }
        else if (strcmp(cmd, "rtopen") == 0) {
            if (!g_jvlink) { json_response("{\"status\":\"error\",\"error\":\"not init\"}"); free(cmd); continue; }
            char* dataspec = json_get_string(line, "dataspec");
            char* key = json_get_string(line, "key");
            int code = CallMethodStrStr(g_jvlink, L"JVRTOpen", dataspec ? dataspec : "", key ? key : "");
            if (code >= 0) g_is_open = 1;
            json_response("{\"status\":\"%s\",\"code\":%d,\"readcount\":%d}",
                         code >= 0 ? "ok" : "error", code, code >= 0 ? code : 0);
            free(dataspec); free(key);
        }
        else if (strcmp(cmd, "read") == 0) {
            if (!g_jvlink || !g_is_open) { json_response("{\"status\":\"error\",\"error\":\"not open\"}"); free(cmd); continue; }
            int size = json_get_int(line, "size", 110000);
            char* buff = (char*)calloc(size + 1, 1);
            char filename[512] = "";
            int code = CallJVRead(buff, size, filename, sizeof(filename));
            if (code > 0 && buff[0]) {
                int dlen = (int)strlen(buff);
                if (dlen > code) dlen = code;
                char* b64 = base64_encode((unsigned char*)buff, dlen);
                json_response("{\"status\":\"ok\",\"code\":%d,\"data\":\"%s\",\"filename\":\"%s\",\"size\":%d}",
                             code, b64 ? b64 : "", filename, dlen);
                free(b64);
            } else {
                json_response("{\"status\":\"ok\",\"code\":%d,\"data\":null,\"filename\":\"%s\",\"size\":0}", code, filename);
            }
            free(buff);
        }
        else if (strcmp(cmd, "skip") == 0) {
            if (!g_jvlink || !g_is_open) { json_response("{\"status\":\"error\",\"error\":\"not open\"}"); free(cmd); continue; }
            DISPID id;
            GetDispId(g_jvlink, L"JVSkip", &id);
            DISPPARAMS params = {NULL, NULL, 0, 0};
            VARIANT result; VariantInit(&result);
            IDispatch_Invoke(g_jvlink, id, &IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_METHOD, &params, &result, NULL, NULL);
            int code = (V_VT(&result) == VT_I4) ? V_I4(&result) : 0;
            json_response("{\"status\":\"ok\",\"code\":%d}", code);
        }
        else if (strcmp(cmd, "close") == 0) {
            if (g_jvlink && g_is_open) CallJVClose();
            g_is_open = 0;
            json_response("{\"status\":\"ok\"}");
        }
        else if (strcmp(cmd, "filedelete") == 0) {
            if (!g_jvlink) { json_response("{\"status\":\"error\",\"error\":\"not init\"}"); free(cmd); continue; }
            char* filename = json_get_string(line, "filename");
            int code = CallMethodStr(g_jvlink, L"JVFiledelete", filename ? filename : "");
            if (code == -9999) {
                code = CallMethodStr(g_jvlink, L"JVFileDelete", filename ? filename : "");
            }
            json_response("{\"status\":\"%s\",\"code\":%d}", code == 0 ? "ok" : "error", code);
            free(filename);
        }
        else if (strcmp(cmd, "status") == 0) {
            if (!g_jvlink) { json_response("{\"status\":\"error\",\"error\":\"not init\"}"); free(cmd); continue; }
            DISPID id;
            GetDispId(g_jvlink, L"JVStatus", &id);
            DISPPARAMS params = {NULL, NULL, 0, 0};
            VARIANT result; VariantInit(&result);
            IDispatch_Invoke(g_jvlink, id, &IID_NULL, LOCALE_USER_DEFAULT, DISPATCH_METHOD, &params, &result, NULL, NULL);
            int code = (V_VT(&result) == VT_I4) ? V_I4(&result) : 0;
            json_response("{\"status\":\"ok\",\"code\":%d}", code);
        }
        else if (strcmp(cmd, "quit") == 0) {
            if (g_jvlink && g_is_open) CallJVClose();
            if (g_jvlink) { IDispatch_Release(g_jvlink); g_jvlink = NULL; }
            json_response("{\"status\":\"ok\",\"message\":\"bye\"}");
            break;
        }
        else {
            json_response("{\"status\":\"error\",\"error\":\"unknown cmd: %s\"}", cmd);
        }
        free(cmd);
    }

    if (g_jvlink) IDispatch_Release(g_jvlink);
    DestroyWindow(hwnd);
    OleUninitialize();
    CoUninitialize();
    return 0;
}
