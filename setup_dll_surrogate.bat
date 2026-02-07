@echo off
REM ============================================================
REM   DLL Surrogate Setup for 64-bit Python
REM   JV-Link / NV-Link COM components (32-bit) を
REM   64-bit Python から使えるようにする
REM ============================================================
REM
REM 参考: https://zenn.dev/hraps/articles/fb6ce9b1151ced
REM
REM 管理者権限が必要です。右クリック→管理者として実行

echo ============================================================
echo   DLL Surrogate Setup
echo   64-bit Python で JV-Link / NV-Link を使う設定
echo ============================================================
echo.

REM Check admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 管理者権限が必要です
    echo   右クリック → 管理者として実行 してください
    pause
    exit /b 1
)

echo JV-Link DLL Surrogate を設定中...
reg add "HKCR\Wow6432Node\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v AppID /t REG_SZ /d "{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /f >nul 2>&1
reg add "HKCR\Wow6432Node\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v DllSurrogate /t REG_SZ /d "" /f >nul 2>&1
reg add "HKCR\AppID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v DllSurrogate /t REG_SZ /d "" /f >nul 2>&1
echo   [OK] JV-Link (CLSID: 2AB1774D-0C41-11D7-916F-0003479BEB3F)

echo NV-Link DLL Surrogate を設定中...
reg add "HKCR\Wow6432Node\CLSID\{F726BBA6-5784-4529-8C67-26E152D49D73}" /v AppID /t REG_SZ /d "{F726BBA6-5784-4529-8C67-26E152D49D73}" /f >nul 2>&1
reg add "HKCR\Wow6432Node\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}" /v DllSurrogate /t REG_SZ /d "" /f >nul 2>&1
reg add "HKCR\AppID\{F726BBA6-5784-4529-8C67-26E152D49D73}" /v DllSurrogate /t REG_SZ /d "" /f >nul 2>&1
echo   [OK] NV-Link (CLSID: F726BBA6-5784-4529-8C67-26E152D49D73)

echo.
echo ============================================================
echo   設定完了！
echo   64-bit Python から JV-Link / NV-Link が使えます
echo ============================================================
echo.
pause
