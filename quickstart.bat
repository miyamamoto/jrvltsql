@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
title JLTSQL Setup

REM Move to batch file directory
cd /d "%~dp0"

echo ============================================================
echo   JLTSQL Quickstart
echo ============================================================
echo.

REM Store exit code for later
set SCRIPT_EXIT_CODE=0

REM ============================================================
REM   Python Detection (32-bit preferred for UmaConn/NAR)
REM ============================================================

REM First try: explicit PYTHON environment variable
if defined PYTHON (
    echo Using PYTHON environment variable: %PYTHON%
    "%PYTHON%" scripts/quickstart.py %*
    set SCRIPT_EXIT_CODE=%errorlevel%
    goto :check_result
)

REM Second try: py launcher with 32-bit Python 3.12
py -3.12-32 --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python 3.12 (32-bit)
    py -3.12-32 scripts/quickstart.py %*
    set SCRIPT_EXIT_CODE=%errorlevel%
    goto :check_result
)

REM Third try: py launcher with any 32-bit Python
py -32 --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (32-bit)
    py -32 scripts/quickstart.py %*
    set SCRIPT_EXIT_CODE=%errorlevel%
    goto :check_result
)

REM Fourth try: py launcher (any version)
py --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (py launcher)
    echo [WARNING] 64-bit Python may not support NAR/UmaConn
    py scripts/quickstart.py %*
    set SCRIPT_EXIT_CODE=%errorlevel%
    goto :check_result
)

REM Fifth try: python in PATH
python --version >nul 2>&1
if %errorlevel%==0 (
    echo Using: Python (PATH)
    echo [WARNING] 64-bit Python may not support NAR/UmaConn
    python scripts/quickstart.py %*
    set SCRIPT_EXIT_CODE=%errorlevel%
    goto :check_result
)

REM No Python found
echo ERROR: Python not found
echo Please install Python 3.12 (32-bit) for full NAR/UmaConn support
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:check_result
echo.
if %SCRIPT_EXIT_CODE% neq 0 (
    echo ============================================================
    echo   Setup Failed (Exit Code: %SCRIPT_EXIT_CODE%)
    echo ============================================================
    echo.
    echo   Please check the error messages above.
    echo   Common issues:
    echo     - Missing config/config.yaml
    echo     - Invalid service key
    echo     - No data available for the specified date range
    echo.
    echo   Press Enter to close...
    set /p dummy=
    exit /b %SCRIPT_EXIT_CODE%
)

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
exit /b 0
