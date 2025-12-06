@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Setup

REM Move to batch file directory
cd /d "%~dp0"

REM Check if 64bit DLL Surrogate is configured
REM This allows 64bit Python to use 32bit JV-Link
reg query "HKCR\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v AppID >nul 2>&1
if errorlevel 1 (
    echo 64bit Python用のDLLサロゲート設定を登録しています...
    echo （管理者権限が必要な場合はUACダイアログが表示されます）

    REM Try to register without elevation first
    regedit /s "%~dp0tools\JV-Link_DllSurrogate.reg" >nul 2>&1

    REM Check if it worked
    reg query "HKCR\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v AppID >nul 2>&1
    if errorlevel 1 (
        REM Need elevation - use PowerShell to elevate
        powershell -Command "Start-Process regedit -ArgumentList '/s', '%~dp0tools\JV-Link_DllSurrogate.reg' -Verb RunAs -Wait" >nul 2>&1

        REM Final check
        reg query "HKCR\CLSID\{2AB1774D-0C41-11D7-916F-0003479BEB3F}" /v AppID >nul 2>&1
        if errorlevel 1 (
            echo [警告] DLLサロゲート設定の登録に失敗しました。
            echo         64bit Pythonを使用する場合は、管理者権限で
            echo         tools\enable_64bit_python.bat を実行してください。
            echo.
        ) else (
            echo [完了] 64bit Python対応設定を登録しました。
            echo.
        )
    ) else (
        echo [完了] 64bit Python対応設定を登録しました。
        echo.
    )
)

REM Try to find any Python (prefer 64bit now that surrogate is configured)
set PYTHON_EXE=

REM First try: explicit PYTHON environment variable
if defined PYTHON (
    set PYTHON_EXE=%PYTHON%
    goto :check_python
)

REM Second try: py launcher (prefers highest version)
for /f "delims=" %%i in ('py -c "import sys; print(sys.executable)" 2^>nul') do set PYTHON_EXE=%%i
if defined PYTHON_EXE goto :check_python

REM Third try: python in PATH
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set PYTHON_EXE=%%i
if defined PYTHON_EXE goto :check_python

:check_python
if not defined PYTHON_EXE (
    echo ERROR: Python not found
    echo Please install Python 3.10+
    pause
    exit /b 1
)

:run_python
"%PYTHON_EXE%" scripts/quickstart.py %*

echo.
echo ============================================================
echo   Setup Complete
echo ============================================================
echo.
echo   Database file: data\keiba.db (SQLite)
echo.
echo   To view data:
echo     - Use DB Browser for SQLite
echo     - Python: sqlite3.connect('data/keiba.db')
echo.
echo   CLI commands:
echo     jltsql status   - Check database status
echo     jltsql fetch    - Fetch additional data
echo     jltsql --help   - Other commands
echo.
echo   For Claude Code / Claude Desktop users:
echo     Install MCP Server to access DB directly from AI
echo     https://github.com/miyamamoto/jvlink-mcp-server
echo.
echo   Press Enter to close...
set /p dummy=
